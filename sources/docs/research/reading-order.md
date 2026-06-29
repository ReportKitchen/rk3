# Reading order — research synthesis (for the RK3 engine)

Goal: determine the correct reading order of a PDF page **deterministically**
(no ML inference), reading the document's own signals first and inferring only
where they're absent. Researched 2026-06 across the tagged-PDF/a11y world and
document-layout-analysis literature.

## 1. Tagged PDFs — the struct tree IS the reading order (authoritative)

- ISO 32000-2 §14.7: logical structure lives in the **StructTreeRoot**; each
  structure element's **`K` (Kids) array order, walked recursively (depth-first),
  is the reading sequence.** Standard block types: P, H1–H6, Span, Figure,
  Table/TR/TD/TH, L/LI/Lbl/LBody. Custom tags resolve via **RoleMap**.
- **MCIDs** tie a struct element to its drawn content: element → `(Pg, MCID)` →
  the `BDC … EMC` marked-content run in the content stream. **MCIDs are per-page
  (restart at 0).**
- **Structure order ≠ content-stream paint order — deliberately independent.**
  Never infer reading order from drawing order. Screen readers traverse the tag
  tree, full stop.
- **/Artifact** content (running heads, page numbers, decoration) is excluded
  from reading order — we already drop it.
- PDF/UA (ISO 14289) makes correct tag order a hard requirement (Matterhorn
  checkpoints 01-001..005 partition every glyph into tagged-content xor artifact;
  28-001 = annotation reading order).

**Trust gate (important):** tagged ≠ trustworthy. Use the struct tree only when
catalog `/MarkInfo /Marked true` AND not `/Suspects true` (the "suspect"/
auto-tagged flag). Cross-check struct order against a geometric sanity check;
fall back to geometry per-block where tags are missing (partial trees are
common — Matterhorn 01-005 "untagged content").

Sources: https://pdf-issues.pdfa.org/32000-2-2020/clause14.html (Tables 354/355,
§14.7–14.8) · https://pdfa.org/resource/tagged-pdf-q-a/ ·
https://www.pubcom.com/blog/2020_08-18_ReadingOrder/reading-orders.shtml ·
Matterhorn Protocol 1.1 (pdfa.org) · ISO 14289 (PDF/UA).

## 2. How tools treat the source of truth

- **Acrobat:** the Tags tree IS the reading order (Reading Order tool edits it);
  the "Order" panel is the separate physical/content order.
- **pdfplumber / unstructured / PDFBox:** geometric sort (top-to-bottom,
  left-to-right; XY-cut) — fall back used only when no/ignored tags. pdfplumber
  default merges columns (needs `x_tolerance` gutter tuning).
- **GROBID:** CRF sequence-labeling (deterministic Viterbi at inference).
- **marker/Surya, MinerU, Docling:** ML layout detection + algorithmic ordering
  — non-deterministic (checkpoint-dependent).

## 3. Untagged pages — deterministic geometry (what to build)

Naive **XY-cut** (Nagy & Seth 1984; recursive projection-profile cut at widest
whitespace valley) fails on: multi-column, **full-width spanning headers**,
**L-shaped** text-around-figure, bridged gutters — exactly our current bugs.
Our `_reading_order` cuts **columns-first**, which is backwards for spanning
headers.

**Best-practice deterministic engine = XY-Cut++** (arXiv 2504.10258, NO neural
nets; implemented in OpenDataLoader PDF). Three stages:
1. **Pre-mask cross-layout/spanning elements** (full-width titles, tables,
   figures) via a median-based adaptive threshold (β≈1.3) so they don't break
   XY-cut's connectivity — fixes ~16% of false splits.
2. **Density-adaptive recursive cut** on what remains (horizontal cuts in dense
   regions, vertical otherwise — not a rigid global threshold).
3. **Re-insert masked elements** by geometry + shallow semantic priority
   (title ≻ visuals ≻ text), with intersection/boundary/continuity constraints.
   Reported 0.988 BLEU-4 / 0.996 Kendall-τ, 514 FPS, no model.

The practical recipe (also unstructured/pdfplumber): **(a) extract full-width
spanning blocks first → horizontal bands; (b) whitespace-gutter column detection
within each band; (c) per-column top-to-bottom, columns left-to-right.** I.e.
**spanning/band-first, not columns-first** — the single change most likely to
fix several of our untagged failures.

**Strongest match for replacing our XY-cut: Breuel / OCRopus topological-sort
reading order.** Instead of recursive cuts, assert *pairwise* before-after
constraints from x/y interval overlaps between lines/blocks:
- same column (x-overlap) and A above B → **A before B**;
- same y-band (y-overlap) and A left of B → **A before B**, asserted only for
  pairs with no intervening line (so cross-column edges don't force a wrong
  global order).
These form a DAG; **topological sort** extends the partial order to the total
reading order. No recursive cut (so a full-width element can't destroy column
separation), no single global threshold (the cause of our split-sentence/
over-seg errors), valid even with overlapping/L-shaped blocks. This is the
OCRopus production approach — verify the exact predicates against OCRopus
`ocrolib` reading-order before implementing. Cycles (genuinely conflicting
layouts) need a tie-break → the residue/manual-reorder case.

**Column detection to feed it:** Breuel **whitespace-cover** (maximal empty
rectangles, branch-and-bound, near parameter-free; DAS 2002) or **Tesseract
tab-stop detection** (Smith, ICDAR 2009 — alignment edges survive full-width
banners better than projection valleys). Both isolate columns; the topo-sort
then orders across them.

Segmentation-only (no ordering): area-Voronoi (Kise 1998, non-Manhattan/skew),
Docstrum (O'Gorman 1993).

ML (LayoutReader seq2seq, pointer-network/GNN relation models, VLMs) — NOT for
the core/hot path, but a **sanctioned escalation tier** for the residue of
genuinely-hard layouts IF deterministic #1+#2 leave a swampy slice (user
decision). Made reproducible by a **pinned checkpoint + greedy/fixed decoding**
(no sampling) and gated on an **ambiguity signal** from the topo-sort (cycles /
undecidable columns) so it only runs where needed. The **reading-order eval gold
set decides empirically** whether it actually beats the deterministic model on
OUR hard layouts — build the gold set regardless; it's the arbiter.

Sources: https://arxiv.org/abs/2504.10258 (XY-Cut++) · ICDAR2005 Optimized XY-cut
(Meunier) · Breuel 2003 / Aiello et al. (topological sort) ·
https://github.com/microsoft/unilm/tree/master/layoutreader (ML, rejected).

## 4. Hard cases & how the field handles them

| Case | Handling |
|---|---|
| Full-width header over columns | mask-then-restore (XY-Cut++); band-first cut |
| L-shape (text around figure) | mask the figure, restore after; or topo-sort |
| Multi-column flow | gutter detect → per-column; or reads-before topo-sort |
| Sidebars / pull-quotes | separate logical stream (we extract asides) |
| Footnotes | marker inline (Reference) + note at bottom; placement policy |
| Running head/footer/page-no | **Artifact** → excluded (we drop) |
| Figure + caption | associate by relation (we handle captions separately) |
| Newspaper "continued on p.X" | **unsolved geometrically** — needs linguistic cue/human |
| Multi-column tables | mask table as a unit; its own internal order |
| Residual ambiguity | field accepts it needs semantic/linguistic or **human** input |

**Implication:** a deterministic engine gets the common cases right; a residue
genuinely needs human input → the **manual `reorder` op** (single-axis drag in
the viewer, persisted in `<name>.ops.json`) is the principled escape hatch, not
a failure.

## 5. Recommended architecture for RK3

1. **Tier 1 (tagged & trustworthy):** read DFS struct-tree order per page; order
   blocks by it (struct-order where present, geometry to interleave untagged
   blocks). Gate on `/Marked && !/Suspects`.
2. **Tier 2 (untagged):** XY-Cut++-style — spanning/band-first, gutter columns,
   per-column top-to-bottom. Replaces the three join-passes, doesn't patch them.
3. **Measure:** a reading-order eval gold set (label correct order on N pages;
   score with edit-distance/Kendall-τ) so regressions are loud.
4. **Residue:** manual `reorder` op for the cases geometry can't decide.

Benchmarks with reading-order GT (for our gold-set design): DocBench-100
(XY-Cut++), OmniDocBench (Normalized Edit Distance), HRDoc/Comp-HRDoc, DocLayNet
(role labels). ReadingBank = ML training set (Word-order GT; not for us).
