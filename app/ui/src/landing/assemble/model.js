// Client model for the content-first Assemble UI (AI content-sections rebuild,
// BACKLOG/61). The sections engine (rk3/landing/sections.py) proposes the
// document's meaningful sections; this holds the small helpers the UI needs to
// present, filter, and assemble them into a render config.

export const LENGTHS = ["short", "middle", "long"];
export const COVERS = ["onTop", "beside", "inset", "textForward"];

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

// Assemble the render config (title + cover + on-sections + CTA) from the section
// state — feeds the rough page, the Wordsmith render, and export.
export function buildSectionConfig({ title, cover, sections, cta }) {
  const blocks = [];
  if (title && (title.title || title.eyebrow || title.subtitle)) {
    blocks.push({ type: "title", id: "title", props: title });
  }
  // cover as a top block for every layout except text-forward (the beside/inset
  // float treatment is a later refinement — for now the cover leads the page)
  if (cover && cover.src && cover.layout !== "textForward") {
    blocks.push({ type: "cover", id: "cover", props: { src: cover.src, alt: cover.alt || "" } });
  }
  for (const s of sections) {
    if (!s.on) continue;
    blocks.push({
      type: "section", id: s.id,
      props: {
        heading: s.heading, presentation: s.presentation, prose: s.prose,
        bullets: s.bullets, cards: s.cards, quote: s.quote, steps: s.steps,
      },
    });
  }
  if (cta?.download) blocks.push({ type: "download", id: "download", props: { label: cta.downloadLabel || "" } });
  if (cta?.secondary) blocks.push({ type: "secondaryCta", id: "secondary", props: { label: cta.secondaryLabel || "" } });
  if (cta?.share) blocks.push({ type: "share", id: "share", props: {} });
  return { version: 1, template: "sections", blocks };
}
