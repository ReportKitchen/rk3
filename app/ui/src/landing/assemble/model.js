// Client model for the content-first Assemble UI (AI content-sections rebuild,
// BACKLOG/61). The sections engine (rk3/landing/sections.py) proposes the
// document's meaningful sections; this holds the small helpers the UI needs to
// present, filter, and assemble them into a render config.

export const LENGTHS = ["short", "middle", "long"];
export const COVERS = ["onTop", "beside", "inset", "textForward"];

// page length (short/middle/long) → AI-summary length axis (short/medium/long)
export const SUMMARY_LENGTH = { short: "short", middle: "medium", long: "long" };

// The AI Summary needs a natural page heading (the exec summary has the doc's own
// title; this one is ours). Pick an intro word the document doesn't already use.
const AI_HEADING_CANDIDATES = ["Summary", "Introduction", "Overview", "About"];
export function pickAiHeading(sections) {
  const used = (sections || []).map((s) => (s.heading || "").toLowerCase());
  const taken = (word) => used.some((h) => h.includes(word.toLowerCase()));
  return AI_HEADING_CANDIDATES.find((c) => !taken(c)) || "Summary";
}

// summary trimming + the page word-count zones
export const REC_WORDS = 120;                 // recommended summary length
export const AUTO_TRIM_OVER = 200;            // auto-trim a prose summary longer than this
export const WC_SHORT = 150, WC_LONG = 500;   // page word-count zones

export const wordCount = (html) =>
  (String(html || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().match(/\S+/g) || []).length;

// Trim prose HTML to ~target words, cut at a block boundary (paragraph/heading),
// so a screens-long verbatim summary shows just its opening.
export function trimProse(html, target = REC_WORDS) {
  const parts = String(html || "").split(/(?=<(?:p|h[1-6]|ul|ol|blockquote|div)\b)/i).filter((x) => x.trim());
  if (parts.length <= 1) return html;
  const out = [];
  let words = 0;
  for (const part of parts) {
    out.push(part);
    words += wordCount(part);
    if (words >= target) break;
  }
  return out.join("");
}

// the effective (trimmed-if-asked) prose for a section
export const effectiveProse = (s) => (s.trimmed ? trimProse(s.prose) : s.prose);

export function sectionWords(s) {
  switch (s.presentation) {
    case "prose": return wordCount(effectiveProse(s));
    case "bullets": return (s.bullets || []).reduce((n, b) => n + wordCount(b), 0);
    case "statCards": return (s.cards || []).reduce((n, c) => n + wordCount(c.value) + wordCount(c.label), 0);
    case "quote": return wordCount(s.quote?.text) + wordCount(s.quote?.attribution);
    case "steps": return (s.steps || []).reduce((n, st) => n + wordCount(st.label) + wordCount(st.body), 0);
    default: return 0;
  }
}

// total words on the page (on-sections + AI summary if on)
export function pageWords(sections, ai) {
  let n = sections.filter((s) => s.on).reduce((sum, s) => sum + sectionWords(s), 0);
  if (ai && ai.on) n += wordCount(ai.prose);
  return n;
}

// The recommended default on/off set: keep the strongest sections (they come
// ordered) up to a word budget that lands the page squarely in the good zone —
// some on, some off — rather than dumping everything on. `sections` must already
// carry their `trimmed` flags so the counts match what's shown.
export function recommendOn(sections) {
  const target = Math.round(WC_LONG * 0.9);   // ~450 — headroom under the "a bit long" line
  const on = sections.map(() => false);
  let total = 0;
  sections.forEach((s, i) => {
    const w = sectionWords(s);
    if (i === 0 || total + w <= target) { on[i] = true; total += w; }
  });
  // clear the "a bit short" floor if we came in under it
  for (let i = 0; i < sections.length && total < WC_SHORT; i++) {
    if (!on[i]) { on[i] = true; total += sectionWords(sections[i]); }
  }
  return on;
}

// ---- AI content-sections model (BACKLOG/61) --------------------------------
// presentation primitive -> library icon + human label key
export const PRESENTATIONS = {
  prose: { icon: "file-text" },
  bullets: { icon: "list" },
  statCards: { icon: "chart-column" },
  quote: { icon: "quote" },
  steps: { icon: "list-ordered" },
};

// how many sections a length keeps on by default (sections come strongest-first)
export const LENGTH_KEEP = { short: 2, middle: 4, long: Infinity };

// which sections are on for a length: the first N (strongest) ones
export function defaultSectionOn(sections, length) {
  const keep = LENGTH_KEEP[length] ?? 4;
  return sections.map((_, i) => i < keep);
}

// The CTA scaffolding (fixed — not AI sections). Kept as its own small group.
export const CTA_KEYS = ["download", "secondary", "share"];

// Title-case a heading — normalize ALL-CAPS ("EXECUTIVE SUMMARY") to Title Case
// while preserving mixed-case acronyms/brands (SoLD, COVID-19) and short acronyms
// (US, STEM) inside an otherwise mixed-case heading. RK3 had only caps DETECTION,
// no reusable title-caser, so this is it.
const SMALL_WORDS = new Set([
  "a", "an", "the", "and", "but", "or", "nor", "for", "of", "to", "in", "on",
  "at", "by", "as", "per", "vs", "via", "from", "with", "into", "onto", "over",
]);
const bareLen = (w) => w.replace(/[^A-Za-z]/g, "").length;

export function titleCase(str) {
  if (!str) return str;
  const allCaps = /[A-Z]/.test(str) && str === str.toUpperCase();
  const words = str.trim().split(/\s+/);
  const last = words.length - 1;
  return words.map((w, i) => {
    // preserve a mixed-case brand/acronym (SoLD, COVID-19) — but not when the
    // whole heading is all-caps, where "acronyms" are just uppercased words
    if (!allCaps && /[a-z]/.test(w) && /[A-Z]/.test(w.slice(1))) return w;
    if (!allCaps && w === w.toUpperCase() && /[A-Z]/.test(w) && bareLen(w) <= 4) return w;
    const bare = w.toLowerCase().replace(/[^a-z0-9]/g, "");
    if (i !== 0 && i !== last && SMALL_WORDS.has(bare)) return w.toLowerCase();
    // capitalize the first letter and letters after a hyphen / slash / dash
    return w.toLowerCase().replace(/(^|[-–—/(])([a-z])/g, (m, p, c) => p + c.toUpperCase());
  }).join(" ");
}

// Split sections into the document's intro/summary (foreword, introduction, exec
// summary…) and the body, for the two left-column groups. Uses the AI's `role`
// tag when present; falls back to the leading run of prose sections for caches
// generated before `role` existed.
export function splitSections(sections) {
  if (sections.some((s) => s.role)) {
    return {
      intro: sections.filter((s) => s.role === "intro"),
      body: sections.filter((s) => s.role !== "intro"),
    };
  }
  let i = 0;
  while (i < sections.length && sections[i].presentation === "prose") i += 1;
  return { intro: sections.slice(0, i), body: sections.slice(i) };
}

// Assemble the render config (title + cover + on-sections + CTA) from the section
// state — feeds the rough page, the Wordsmith render, and export.
export function buildSectionConfig({ title, cover, sections, cta, ai }) {
  const blocks = [];
  if (title && (title.title || title.eyebrow || title.subtitle)) {
    blocks.push({ type: "title", id: "title", props: title });
  }
  // cover as a top block for every layout except text-forward (the beside/inset
  // float treatment is a later refinement — for now the cover leads the page)
  if (cover && cover.src && cover.layout !== "textForward") {
    blocks.push({ type: "cover", id: "cover", props: { src: cover.src, alt: cover.alt || "" } });
  }
  // the opt-in AI Summary leads the content, under a natural heading
  if (ai && ai.on && ai.prose) {
    blocks.push({ type: "section", id: "ai-summary",
      props: { heading: ai.heading || "", presentation: "prose", prose: ai.prose,
               bullets: [], cards: [], quote: {}, steps: [] } });
  }
  for (const s of sections) {
    if (!s.on) continue;
    blocks.push({
      type: "section", id: s.id,
      props: {
        heading: s.heading, presentation: s.presentation, prose: effectiveProse(s),
        bullets: s.bullets, cards: s.cards, quote: s.quote, steps: s.steps,
      },
    });
  }
  if (cta?.download) blocks.push({ type: "download", id: "download", props: {
    label: cta.downloadLabel || "", mode: cta.downloadUrl ? "url" : "bundle", url: cta.downloadUrl || "" } });
  if (cta?.secondary) blocks.push({ type: "secondaryCta", id: "secondary", props: {
    label: cta.secondaryLabel || "", url: cta.secondaryUrl || "" } });
  if (cta?.share) blocks.push({ type: "share", id: "share", props: {
    networks: cta.shareNetworks, style: cta.shareStyle || "plain" } });
  return { version: 1, template: "sections", blocks };
}
