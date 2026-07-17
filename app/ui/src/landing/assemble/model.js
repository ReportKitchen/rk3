// Shared block model for the content-first Assemble UI. Mirrors the backend
// block vocabulary (rk3/landing/guidance.py `_BLOCK_KEYS`) and the length model
// (rk3/landing/templates.py `_select`) so the client can recompute the smart
// default set for a length without a round-trip, while /guided stays the
// authoritative config for preview/export.

// bucket → ordered block-library keys. This is also the canonical render order.
export const BUCKETS = [
  { id: "intro", keys: ["execSummary", "aiSummary"] },
  { id: "evidence", keys: ["highlights", "findings", "toc", "storytelling"] },
  { id: "cta", keys: ["download", "secondary", "share"] },
];

export const ALL_KEYS = BUCKETS.flatMap((b) => b.keys);
export const NEW_BLOCKS = new Set(["storytelling"]);

const EVIDENCE = new Set(["highlights", "findings", "toc", "storytelling"]);
const LENGTH_RULES = {
  short: { evidence: 0, dropCta: ["secondary"] },
  middle: { evidence: 1, dropCta: ["secondary"] },
  long: { evidence: null, dropCta: [] },
};

// Which recommended keys survive at a length (port of templates.py `_select`):
// short drops all evidence, middle keeps the single strongest, long keeps all;
// drop the secondary CTA below long. Preserves the engine's order.
export function selectKeys(order, length) {
  const rule = LENGTH_RULES[length] || LENGTH_RULES.middle;
  let ev = 0;
  const out = [];
  for (const key of order || []) {
    if (EVIDENCE.has(key)) {
      if (rule.evidence !== null && ev >= rule.evidence) continue;
      ev += 1;
    } else if (rule.dropCta.includes(key)) continue;
    out.push(key);
  }
  return out;
}

// canonical render order for a set of added keys
export function orderedKeys(addedSet) {
  return ALL_KEYS.filter((k) => addedSet.has(k));
}

// page length (short/middle/long) → AI-summary length axis (short/medium/long)
export const SUMMARY_LENGTH = { short: "short", middle: "medium", long: "long" };

export const LENGTHS = ["short", "middle", "long"];
export const COVERS = ["onTop", "beside", "inset", "textForward"];
