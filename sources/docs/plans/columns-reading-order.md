# Plan: Columns / reading order — the keystone sprint

Status: proposed 2026-07-02 (owner asked for the plan; research already done in
docs/research/reading-order.md — this is the execution sequence). Goal: nail
multi-column reading order once and for all, with a strong manual escape hatch
for intractable docs. Doctrine: **always guess, flag below confidence; stop-
and-ask is reserved for capital crimes** (owner, open-questions 2c).

## Where we are

- **Tier 1 (tagged) shipped**: struct-tree order when tag coverage ≥ 0.6, with
  geometric interpolation for untagged blocks. Works (edf p3, oxfam p5/p11
  eval passes).
- **Tier 2 (untagged) is the gap**: `_reading_order` is a columns-first XY-cut
  patched by `_side_rows` (card rows) and `_heading_aside_rows`
  (heading-left/body-right). The research verdict: columns-first is backwards
  for spanning headers, and the three join passes (`_join_column_wrap`,
  `_join_broken_paragraphs`, `_join_pagebreak_sentences`) are downstream
  bandages on upstream ordering errors.
- **Standing failures** (the 4 red evals, 3 of them ordering): gates p8
  left-column body vs right column; atlantic p6 'Jason Marczak' signature
  ordering; edf p6 MethaneAIR trailing clause. (The 4th, edf running-footer-
  as-heading, is typing — fix rides along but isn't ordering.)
- **Two facts that scope the work** (from the column-fusion fix, assemble
  v40 / 50b000a): (1) assemble now emits the CORRECT order on all three
  failing pages — the layered diagnostics pass at assemble and fail only at
  analyze, so the XY-cut is actively scrambling good input; (2)
  `_reading_order_topo` is already implemented but PARKED — its first cut
  regressed eval (added an edf p5 failure, fixed none). Phase 2 is therefore
  a *revival with the phase-1 column model as its constraint source*, not a
  from-scratch build, and the gold set exists precisely to keep a second
  premature flip from happening.

## Phase 0 — the gold set arbitrates (before any engine change)

Encode ordering ground truth as eval `order:` checks so every subsequent step
is measured, not vibed:

1. The 3 failing cases (already encoded — they're the definition of done).
2. From the 89 structure notes: every note that names an order problem
   becomes a check on its doc/page (estimate 15–25 checks).
3. **Negative controls**: single-column docs and pages with figures/asides
   that must NOT be split into columns (foia, covid, race-to-lead samples) —
   a gutter detector that fires on whitespace inside a single column is the
   classic failure, and only negative controls catch it.
4. Per-page ambiguity labels for a handful of genuinely-hard pages (the
   residue candidates) so the confidence signal has ground truth too.

Deliverable: `eval/` additions only; current engine's pass/fail census as the
baseline scorecard.

**Phase 0 SHIPPED (2026-07-02).** New `split:` check kind (inverse of merge —
pins column fusion). Baseline census: **32 passed / 12 failed**, where the 12
= 4 pre-existing (gates p8, atlantic p6, edf p6 ordering + edf footer typing)
+ **8 GOLD(col) targets**: advancing p12 column weld (split), covid p4-5
cross-page break (merge), ecp p4 continuation (merge), ecp p6 box-vs-body
order ×2, ecp p10 list-item fragment (the magic-wand example, as a list
check), foia p20 body-tail-after-ENDNOTES (order), gates p9 stray
bullet-paragraph (list). 7 guards pass, incl. 4 single-column
negative-controls (race-to-lead p16, community-schools p107) that pin the
"gutter detector must not fire inside one column" failure mode. Definition of
done for phases 1-2: targets go green without any guard going red.

## Phase 1 — column evidence, root-caused (the keystone)

Replace implicit column inference with an explicit, logged, per-page **column
model** computed on the assemble blocks:

- **Gutter detection**: x-projection whitespace profile per horizontal band
  (not per page — bands bounded by full-width elements), Breuel
  whitespace-cover as the reference algorithm; Tesseract-style tab-stop
  alignment edges as the tiebreaker on noisy pages.
- **Spanning detection first**: full-width blocks (median-based adaptive
  threshold per XY-Cut++) partition the page into bands; columns are detected
  *within* bands. This is the band-first inversion the research calls the
  single highest-value change.
- Output: `ctx.columns[page] = {bands: [{y0, y1, cols: [x-ranges]}], conf}`,
  logged with rk provenance like every other decision. Nothing consumes it
  yet — phase 1 is measurement + logging, verified by eyeballing the logged
  models against ~10 known pages.

Distinguishers the detector must respect (owner answers, open-questions 2d):
- **True column flow** (text continues 1→2) → linearize.
- **Table masquerading as columns** (parallel compare, text stops at column
  bottom, header atop each column) → NOT flow; keep as table/columns node.
  Signal: no sentence continuation across gutter + per-column headers.
- **List-in-columns** (name/funder columns) → one list, offer columns as
  style later.
- **Sidebar** (aside width thresholds; already extracted as asides).

**Phase 1 SHIPPED (2026-07-02, analyze v141).** `_column_model` computes
band-first (spanning blocks bound bands; XY-Cut++ median-adaptive span
threshold), then LINE-level x-projection with bridge tolerance inside each
band — one fused cross-gutter line cannot hide a gutter, but many lines veto
it. Logged per page (`column-model` events: bands, cols, gutter widths,
bridged/lines) + `ctx.column_model`; consumed by nothing yet. Eyeballed
**10/10** on the known pages: 2-col detected on gates p8 (under 3 spanning
lede bands), oxfam p5/p10/**p11** (p11 was invisible to block-level
projection — 2 fused lines bridged the gutter; the model now both finds the
gutter AND counts the bridges, quantifying the fusion pathology per page),
ecp p4/p6, advancing p12 (the weld page: g=22pt, 0 bridges — the model knows
two columns exist where the join pass fused them), covid p4; and clean 1-col
conf=1.0 on both negative controls. Eval census unchanged (32/12), pytest
33/33.

## Phase 2 — topological order replaces the XY-cut

**Why the parked `_reading_order_topo` regressed, and why the column model
fixes it** (assessed 2026-07-02): (a) its cross-column `left_of` edges ignore
bands — a left-column block LOWER on the page asserts "before" a right block
in the band ABOVE it; (b) its same-column test is raw x-overlap, so a fused
cross-gutter line x-overlaps both columns and radiates wrong "higher→before"
edges into each. Both die when constraints come from the model: same-column
edges only within a model column, left→right edges only within a band,
band→band strictly top-down. That is the phase-2 rewrite — the topo machinery
itself (DAG + stable tie-break + cycle fallback) is sound and stays.

Per the research (Breuel/OCRopus): pairwise before-after constraints from the
column model —

- same column, A above B → A before B;
- same band, A's column left of B's → A before B (asserted only when no
  intervening block);
- spanning block before everything below its band, after everything above.

Topo-sort the DAG; **cycles = the ambiguity signal** (feeds phase 3). Ship
behind a per-doc config flag first (`structure.readingOrder: "topo"|"xycut"`),
corpus A/B'd against the phase-0 scorecard, then flip the default when the
scorecard says so. `_side_rows` / `_heading_aside_rows` become constraint
sources instead of pre-passes. The three join passes stay but should fire
less; their fire-rate per doc is a secondary metric (joins are bandages —
fewer is better).

## Phase 3 — confidence + flag (never silently wrong)

A per-page ordering confidence from: gutter clarity margin, DAG cycle count,
tag coverage agreement (when tags exist but weren't trusted), and
column-model stability across adjacent pages. Below threshold →

- a `flag` node at the top (same pattern as footnote-mismatch): "reading
  order uncertain on pages 8, 14" — the user's worklist;
- later, a `reading-order` **proposal** (plans/proposals-layer.md) carrying
  the alternative order as a one-click `reorder` op.

## Phase 4 — the manual escape hatches (strong, first-class)

For intractable docs the human is the design, not the failure:

1. **`reorder` op** (exists): doc-level and page-scoped permutation by nids —
   survives reconverts via recursive remap. Keep.
2. **`order-pin` op (new)**: a pairwise constraint — "nid A reads before nid
   B" — injected into the phase-2 DAG *before* the sort. One pin fixes a page
   without hand-permuting it, and it keeps working when the page's other
   content shifts. This is the high-leverage hatch: pins compose with the
   engine instead of replacing it.
3. **Per-page column override** (config): `structure.columns: {"8": 1}` —
   "page 8 is single-column, stop detecting" / `{"12": 2}` — force the
   two-column model. For the pages where detection is hopeless but the truth
   is trivial to state.
4. Viewer: the reading-order tool gains "pin A before B" (writes order-pin)
   alongside drag-to-reorder (writes reorder). Feedback `#order` marks flow
   to me as usual.

## Phase 5 — sanctioned residue tier (only if the scorecard demands)

If phases 1–4 leave a measured swampy slice: vision-model ordering for
FLAGGED PAGES ONLY (analysis tier — returns a proposal, never mutates;
pinned model + fixed decoding for reproducibility). The gold set decides
whether it ever beats deterministic + pins on our corpus; do not build ahead
of that evidence.

## Verification (every phase)

- Phase-0 scorecard delta (the arbiter) + full eval 25/4-or-better.
- Join-pass fire-rate per doc trending down (phase 2).
- Eyeball the known pages: gates p8, atlantic p6, edf p6, oxfam foreword,
  chep column-heavy pages, plus two negative-control single-column docs.
- Snapshot diff reviewed doc-by-doc on the flip-the-default commit.

## Non-goals

- Visual column *preservation* (except table-masquerade/list-in-columns nodes
  above) — linearize-for-web remains the default.
- Pagination, page-break policy (phase-contract territory).
- ML in the hot path — tier 3 stays gated behind the flag + gold-set
  evidence.
