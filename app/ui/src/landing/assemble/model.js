// Client model for the content-first Assemble UI (AI content-sections rebuild,
// BACKLOG/61). The sections engine (rk3/landing/sections.py) proposes the
// document's meaningful sections; this holds the small helpers the UI needs to
// present, filter, and assemble them into a render config.

export const LENGTHS = ["short", "middle", "long"];
// cover layouts (BACKLOG/45): the title always leads full-width — a cover floated
// NEXT to the title left trapped white space past the title's end. Instead the
// cover sits inside or after the first summary. floatRight = floats into the
// summary alone; floatBoxed = floats in a shaded card with a download button;
// band = a shaded detail band after the summary.
export const COVERS = ["floatRight", "floatBoxed", "band"];
// map the guidance engine's / older cover values onto the new set
export function normalizeCover(v) {
  const m = { floatRight: "floatRight", floatBoxed: "floatBoxed", band: "band",
    beside: "floatRight", onTop: "band", inset: "floatBoxed", textForward: "floatRight" };
  return m[v] || "floatRight";
}

// page length (short/middle/long) → AI-summary length axis (short/medium/long)
export const SUMMARY_LENGTH = { short: "short", middle: "medium", long: "long" };

// ---- persistence (BACKLOG/45): the assembled state saves next to the source and
// merges back over the regenerable AI section proposal on load ----

// a stable-ish key for a section: a slug of its own heading (the doc's framing),
// so saved overrides + Wordsmith edits survive a re-analysis when the heading does
const slugify = (s) =>
  String(s || "").toLowerCase().replace(/<[^>]+>/g, " ").replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "").slice(0, 60) || "section";

// assign each section a unique `key` (heading-slug, de-duped) — in place
export function assignKeys(sections) {
  const seen = {};
  for (const s of sections) {
    const base = slugify(s.heading);
    seen[base] = (seen[base] || 0) + 1;
    s.key = seen[base] > 1 ? `${base}-${seen[base]}` : base;
  }
  return sections;
}

// apply a saved assembled state's section overrides + order onto fresh sections
export function mergeSaved(sections, saved) {
  if (!saved || !saved.sections) return sections;
  const byKey = saved.sections;
  for (const s of sections) {
    const o = byKey[s.key];
    if (!o) continue;
    if (typeof o.on === "boolean") s.on = o.on;
    if (o.presentation) s.presentation = o.presentation;
    if ("treatment" in o) s.treatment = o.treatment;
    if (typeof o.trimmed === "boolean") s.trimmed = o.trimmed;
    if (o.quoteTreatment) s.quote = { ...s.quote, treatment: o.quoteTreatment };
  }
  if (Array.isArray(saved.order) && saved.order.length) {
    const rank = new Map(saved.order.map((k, i) => [k, i]));
    const at = (s) => (rank.has(s.key) ? rank.get(s.key) : Infinity);
    sections = sections.slice().sort((a, b) => at(a) - at(b));  // stable; new sections trail
  }
  return sections;
}

// the full assembled payload to persist
export function toAssembled({ sections, cover, accent, length, cta, ai, edits }) {
  const secOut = {};
  for (const s of sections) {
    secOut[s.key] = {
      on: !!s.on, presentation: s.presentation, treatment: s.treatment ?? null,
      trimmed: !!s.trimmed, quoteTreatment: s.quote?.treatment || null,
    };
  }
  return {
    version: 1, cover, accent, length,
    cta, ai: { on: !!ai?.on, voice: ai?.voice || "neutral" },
    order: sections.map((s) => s.key), sections: secOut, edits: edits || {},
  };
}

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
// so a screens-long verbatim summary shows just its opening — the block that
// crosses the target is kept, so we land at ~target rather than well under it.
// (The canTrim gate below decides whether trimming is even worth offering, so a
// section that only just exceeds the target is simply never trimmed, not trimmed
// to nothing.)
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

// how many words trimming would remove — 0 means the toggle would do nothing
export const trimSavings = (html) => wordCount(html) - wordCount(trimProse(html));

// worth offering a Full/Trimmed control? only when the section is genuinely long
// AND trimming visibly shortens it (a single un-splittable block can't be trimmed
// at a block boundary, so we don't pretend it can).
export const canTrim = (html) =>
  wordCount(html) > AUTO_TRIM_OVER && trimSavings(html) >= 30;

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

// default stat-treatment rotation: when a doc has several stat sections, each
// opens with a different treatment so browsing shows the range (bars is %-only,
// so it's offered but not in the default rotation).
export const STAT_TREATMENT_ORDER = ["cards", "icons", "band", "tiles", "list", "hero"];

// same idea for quotes (design-system/quotes 5a–5f): the first quote opens on the
// warm default "glyph", additional quotes rotate through the other looks so a
// multi-quote doc shows the range on browse.
export const QUOTE_TREATMENT_ORDER = ["glyph", "editorial", "tint", "poster", "framed", "dark"];

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
// state — feeds the rough page, the Wordsmith render, and export. The title
// always leads full-width; the cover is woven into (or set just after) the first
// summary so a title that runs past the cover can't trap white space beside it.
export function buildSectionConfig({ title, cover, sections, cta, ai }) {
  const hasTitle = title && (title.title || title.eyebrow || title.subtitle);
  const hasCover = cover && cover.src;
  const layout = normalizeCover(cover?.layout);
  const dl = cta?.download
    ? { label: cta.downloadLabel || "", mode: cta.downloadUrl ? "url" : "bundle", url: cta.downloadUrl || "" }
    : null;

  const head = hasTitle ? [{ type: "title", id: "title", props: { ...title, skey: "__title__" } }] : [];

  // ordered content: the opt-in AI Summary leads, then the on-sections. `skey` is
  // the stable per-block key Wordsmith uses to store/re-apply text edits.
  const content = [];
  if (ai && ai.on && ai.prose) {
    content.push({ type: "section", id: "ai-summary",
      props: { heading: ai.heading || "", presentation: "prose", prose: ai.prose,
               bullets: [], cards: [], quote: {}, steps: [], skey: "__ai__" } });
  }
  for (const s of sections) {
    if (!s.on) continue;
    content.push({ type: "section", id: s.id, props: {
      heading: s.heading, presentation: s.presentation, prose: effectiveProse(s),
      bullets: s.bullets, cards: s.cards, quote: s.quote, steps: s.steps, treatment: s.treatment,
      skey: s.key } });
  }
  // the "first summary" = the first prose block (else the first block of any kind)
  let sumIdx = content.findIndex((b) => b.props.presentation === "prose");
  if (sumIdx < 0 && content.length) sumIdx = 0;

  // a boxed/band cover carries its own download button — and the CTA download
  // still appears at the foot when it's on (a download at the top AND bottom is fine)
  const body = content.slice();
  if (hasCover && sumIdx >= 0 && (layout === "floatRight" || layout === "floatBoxed")) {
    // float the cover inside the first summary section
    const target = body[sumIdx];
    body[sumIdx] = { ...target, props: { ...target.props,
      cover: { src: cover.src, alt: cover.alt || "" }, coverLayout: layout,
      coverDownload: layout === "floatBoxed" ? dl : null } };
  } else if (hasCover && layout === "band") {
    // a detail band right after the first summary (or leading, if no content)
    const band = { type: "coverBand", id: "cover-band", props: {
      cover: { src: cover.src, alt: cover.alt || "" }, title, download: dl,
      date: title?.date || "", authors: title?.authors || "" } };
    body.splice(sumIdx >= 0 ? sumIdx + 1 : 0, 0, band);
  } else if (hasCover) {
    // nothing to attach to (empty page): a bare cover after the title
    body.unshift({ type: "cover", id: "cover", props: { src: cover.src, alt: cover.alt || "" } });
  }

  const blocks = [...head, ...body];
  // CTAs in the user's chosen order (cta.order)
  const ctaBlock = {
    download: () => cta?.download && { type: "download", id: "download", props: {
      label: cta.downloadLabel || "", mode: cta.downloadUrl ? "url" : "bundle", url: cta.downloadUrl || "" } },
    secondary: () => cta?.secondary && { type: "secondaryCta", id: "secondary", props: {
      label: cta.secondaryLabel || "", url: cta.secondaryUrl || "" } },
    share: () => cta?.share && { type: "share", id: "share", props: {
      networks: cta.shareNetworks, style: cta.shareStyle || "plain" } },
  };
  for (const key of (cta?.order || CTA_KEYS)) {
    const blk = ctaBlock[key] && ctaBlock[key]();
    if (blk) blocks.push(blk);
  }
  return { version: 1, template: "sections", blocks };
}
