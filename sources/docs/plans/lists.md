# Plan: Lists — the second structure keystone

Status: proposed 2026-07-02 (researched during the owner's doc-by-doc column
review; same shape as plans/columns-reading-order.md). Goal: every list in
the corpus detected, whole, correctly nested, marker-clean, and addressable —
with the same gold-set discipline that closed columns.

## Where we are

**Seventeen list-related passes** (inventory: `_is_bullet_list`/
`_bullet_items`, `_ordinal_block`/`_ordinal_items_rich`, `_split_inline_bullets`,
`_group_tag_lists`, `_group_bullet_paragraphs`, `_group_ordinal_paragraphs`,
`_marker_lists`, `_definition_lists`, `_merge_crosspage_lists`,
`_merge_crosspage_bullet_lists`, `_parse_list_continuation`, `_join_list_tail`,
`_absorb_bullet_stragglers`, `_upgrade_lists`, plus `_ol_marker`/`_cut_item`
plumbing). Layered-techniques doctrine at work — each pass earned its place —
but no shared evidence model: each re-derives "is this a marker, what level is
it" from raw text. That's the same shape columns were in before the column
model, and the fix rhymes.

Working well (eval-pinned): bullet blocks, ordinal blocks with marker
stripping, tag-declared lists, cross-page continuation, bold lead-ins inside
items ([[first-class-content]]), refs in items, item containers with nids.

**What the field does** (grounding): tagged PDFs declare lists outright —
`L > LI > Lbl/LBody` per ISO 32000-2 §14.8.4.3.3, with nesting as nested `L`
elements; we already consume this (`_group_tag_lists`), and it remains the
authoritative tier exactly like the struct tree is for reading order. For
untagged content every serious extractor (unstructured, Docling, marker)
falls back to the same two signals we have: **leading-marker census**
(glyph/ordinal pattern) and **indentation profile** (marker-x vs wrap-x
clusters). Nobody has a third trick; quality comes from doing those two
systematically instead of per-heuristic.

## The defect classes (from the reviewer's notes, consolidated)

| # | class | examples | today |
|---|---|---|---|
| L1 | compound / stray markers — "•-" leaves a "-" in the item | clean-air p32 (`'•- Data was collected'`), chep p75/p105, clean-air p4 | `_strip_marker_item` strips ONE glyph |
| L2 | multi-level nesting | clean-air p32 "last item has 2nd-level items", p9 "level 3 UL under 'Build on Successes'" | only ordinal `sub` + cross-page continuation; no indent-driven nesting |
| L3 | ULs hiding inside paragraphs | clean-air p15 "there's UL hiding in here", p17 "UL starts within the paragraph", p16 | `_split_inline_bullets` catches some; misses block-interior starts |
| L4 | over-split lists (adjacent same-style ULs) | **GATES** p17 "should be one UL with 4 LIs; instead 2 ULs of 2" (mis-attributed to clean-air in v1 of this table — owner correction; clean-air p17 has no lists at all) | cross-PAGE merges exist; column-gutter splits don't merge |
| L5 | broken items | chep p105 "each li is broken multiple times", chep p51 | `_join_list_tail` fixed the tail case; interior breaks remain |
| L6 | missing initial bolds in items | ecp p4, clean-air p4 | VERIFIED fixed by container work; PINNED (freeze guards, census 48/8). Discovered alongside: missing spaces at bold boundaries (ecp "AfterArrears/Pre-Filing" vs source "After Arrears/Pre-Filing") — new defect class, not yet targeted |
| L7 | marker spacing | chep p51 "significant space after the bullet points" | unhandled (style-layer) |
| L8 | bold-lede list pattern (2-level design: prominent first phrase) | design-principles p14/p72, clean-air p36 | renders flat; the PATTERN isn't recognized |
| L9 | lists-in-columns | advancing p53, owner 2d answer (name/funder columns) | unhandled (offer as style option) |
| L10 | list-like FALSE POSITIVES | foia "#666 is a street address, not note 666"; survey questions (respond-to-crisis) that number sequentially but list nothing | citation gates exist for notes; lists need the same skepticism |
| L11 | TOC-list residue (drop the header with the list) | advancing p5, design-principles p6 | list dropped, header orphaned |

**PROGRESS (2026-07-02):** Phase 0 partial (invest p51 L3 target + the
owner's self-minted assertions; negative controls for L10 still to encode).
Phase 1 SHIPPED (analyze v151: `_list_census` log-only; L1 compound-marker
strip rode along — clean-air's '•-' items start clean). Phase 2 SHIPPED
(v153: indent-driven nesting in `_bullet_items`, recursive; clean-air p32
renders a real second level. The A/B snapshot review caught a real
drop-lines-before-first-marker bug — advancing lost 5 label items under the
audit threshold; fixed, all recovered. Corpus snapshot byte-identical
otherwise). L3 SHIPPED (v154: _split_inline_ordinals + the not_list: control kind;
fired exactly once corpus-wide — its gold target). Page-number furniture
shipped alongside (v155). **L4 = the gates p17 cluster SHIPPED**
(v157-158, both gold targets green, census 44/8):
(a) the caption interleave was the `_reading_order_model` hit test
measuring column penetration only against the ITEM's width — now
`0.25 * min(item_w, col_w)` with a 3-gutter floor so sliver
pseudo-columns (nff p4 map-number soup) can't promote chart titles to
splitters; (b) new `_merge_crosscolumn_bullet_lists` pass — adjacent
unordered lists in adjacent columns of the same band, continuation
opening at band top, items concatenate (`list-continued-column`);
(c) `_split_inline_bullets` now splits a SINGLE interior bullet when
the lead ends with ":" and the segment carries ≥40 chars of prose
(the welded parent bullet; fired at 10 gates sites, 0 elsewhere,
p16+p51 verified vs source). Bonus from a weight guard added to
`_join_column_wrap` (a genuine wrap never flips bold→regular):
points-of-light pull-quotes de-welded, rock p16 kicker stays intact.
Enabler nesting (the 4 items as children of the "Turning…" parent
bullet, per source indent) NOT done — flat sibling lists for now.
**L2 level-3 nesting SHIPPED** (v163, census 46/8): the "p9 level-3 UL"
note (77bbd84c) was GOOD-FOOD's, not clean-air's (second mis-filed
attribution — feedback jsonl decides). `_group_bullet_paragraphs` now
captures a deeper-indented x-overlapping list as the preceding bullet's
sub-list and keeps the run open (good-food p9 ●/○, oxfam p54 Box 10 —
the only 2 fire sites, both verified vs source); `_absorb_bullet_stragglers`
gained the one decidable guard (same-page shallower straggler = parent
level). New eval kind `nested:` pins it; the cross-column-sibling trap
(gates p65) and the cross-page trap (gates p54→55) are both comment-
documented in the conditions. Remaining L2 residue: enabler nesting
under a SPLIT-OFF parent bullet (gates p17) — the sub-list arrives
BEFORE the parent's own list exists; different shape.

**Owner-note encodings (2026-07-02, post-compact):** tenure p31
hard-hyphen (4005009f) FIXED via layered caps dehyphenation
(`_caps_wrap_joins`, v164): in-doc vocabulary first (doc writes the
joined word elsewhere → join; writes the hyphenated compound mid-line →
keep), wordfreq morphology fallback (joined is a real word AND one
fragment isn't a common standalone word → broken word). 5 joins
corpus-wide (SUMMARISE, MULTIDIMENSIONAL ×2, PHILANTHROPIC,
DEVELOPMENT), zero false fires against the 14-case corpus census
(LONG-TERM/AIR-QUALITY class all kept). Tenure p54 caption-splice note
(9480e0a1) found already healed by v157-163 ordering — pinned with
split + merge guards. respond-to-crisis p24 Q&A-layout note (195a0316)
NOT encoded: the owner is musing (horizontal-rule signal idea), no
prescribed structure yet — needs a structure decision before a stake.

## Phase 0 — gold set first

Encode targets + guards before touching the engine (the columns lesson: the
gold set is why the flip was safe and the first topo attempt wasn't):

- Targets from the table above wherever the note names a page: L1 stray-char
  (a `freeze` or text_not_contains-style check on the item text), L2 nesting
  (needs a NEW `nested:` check kind — "item X has a child list whose items
  include Y"), L3 hidden ULs (`list:` checks), L4 over-split (`list:` with
  all four items in ONE list), L5 broken items (`merge`-in-item — the
  existing `list:` kind already proves item wholeness).
- Guards: the passing list checks stay; add L6 initial-bolds as a `freeze`
  on a bold-led item (verify against source first).
- **Negative controls** (L10): the foia street-address paragraph and a
  respond-to-crisis survey-question run must NOT become lists; two
  citation-styled numbered paragraphs likewise. The columns negative
  controls caught the gutter false-positive class; these catch the
  "everything numbered is a list" class.
- Viewer gap (cheap, do alongside): extend the assertion-save UI to mint
  `merge`/`split`/`list` so the owner's review can pin these directly.

## Phase 1 — the list-evidence model (mirrors the column model)

One pure function, per block (and per aside interior): a **marker census** —
for each line: leading marker (glyph / ordinal style+value / none, via the
existing `_line_marker`-adjacent plumbing), marker x-position, wrap-x. Output:

    {levels: [{x, marker_kind, style}], items: [(line-range, level)], conf}

- Indent LEVELS from x-clustering (the clean-air p32 probe: markers at
  115.8, wraps at 133.x — the signal is clean and cheap).
- **Compound-marker fix rides here** (L1): the census consumes ALL leading
  marker glyphs plus trailing space as one marker token, not one char.
- Log-only first (`list-model` events), eyeballed against the noted pages,
  then consumed by the detection passes phase by phase — never a big-bang
  replacement of the 17 passes.

## Phase 2 — nesting from the model (L2)

Indent level + marker-style change ⇒ child list. The container model already
holds arbitrary nesting (`item > [leaf, list]` — `_upgrade_lists` recurses);
what's missing is only the *builder*. Verify on clean-air p32/p9 (2- and
3-level) and design-principles. Ordinal `sub` unifies into the same
mechanism afterwards, not before.

## Phase 3 — detection completeness (L3, L4) + item integrity (L5, L6)

- Block-interior bullet starts: the census (phase 1) sees a marker mid-block
  where `_is_bullet_list` (first-line-only) doesn't — `_split_inline_bullets`
  extends to consume census output instead of its own scan.
- Same-page adjacent same-style lists merge (guarded by the L4 check; the
  clean-air p28 "two callout boxes wrongly joined" note is the OPPOSITE
  failure — the guard set must include a do-NOT-merge control where a
  heading/box boundary intervenes).
- L6: verify initial bolds now survive (post-container `_leaf` should have
  fixed this) — pin with a freeze either way.

## Phase 4 — per-item provenance (the container-model follow-up)

Item leaves currently inherit their LIST's bbox — fine for rendering, wrong
for sync-scroll (`data-yf` is the list top for every item), imprecise for
remap (all items in a list share page+bbox features), and unusable for
future per-item region ops. The builders have the item's line ranges; carry
the real bbox onto the leaf at construction. Contract change → bump
`irVersion` note in ir-contract.md; nids are text-hashed so they don't churn.

## Phase 5 — patterns & styling (deferred to the styles/proposals tracks)

- L8 bold-lede lists: recognize as a PATTERN (content: recommendations;
  design: 2-level list) — feeds the info-design pattern library and the
  proposals layer ("style this as a prominent-lede list"), not pipeline
  hard-coding.
- L9 lists-in-columns: a render/style option surfaced as a proposal
  ("display this 40-name list in 3 columns"), per the owner's 2d answer.
- L7 marker spacing + glyph preservation: styles-system territory (glyph
  choice is a role class, like emphasis).
- L11 TOC residue: fold into the TOC-drop pass (drop the adjacent header) —
  small, independent; can ship any time.

## Synergies (why lists now, the cross-domain payoffs)

- **Columns:** every list defect on a multi-column page compounds with
  ordering; the column model already feeds list continuation (`_join_list_tail`
  and stragglers came from column targets). Lists-in-columns (L9) NEEDS the
  column model to detect "this IS one list set in two columns" — the
  table-masquerade discriminator, reused.
- **Footnotes:** L10's skepticism gate is the SAME problem as note-marker
  false positives (foia's #666 street address literally sits in both
  domains) — one shared "is this number a marker, a citation, or prose"
  judgment, used by notes and lists, would replace two.
- **Container model:** phases 2 and 4 are the follow-ups predicted when the
  model landed (nesting = free; item bboxes = the known gap). No new shape
  needed — validation that the refactor paid.
- **Proposals:** L8/L9/L11 are proposal kinds, not pipeline rules — concrete
  early candidates for the `suggest` lane alongside alt-text.
- **Heading detection:** bold-lede lists (L8) and lead-heading promotion
  share the same signal (bold run-in) — the census should emit it once.

## Verification

Phase-0 census baseline first, then per phase: gold delta (targets green,
guards + negative controls hold), pytest snapshot review (list/item count
shifts must match the class being fixed), eyeball the noted pages against
source images (clean-air p32/p9, chep p105/p75, design-principles p14/p72,
advancing p53), audit lost = 0 throughout.

## Non-goals

- No list-styling engine here (glyphs/spacing → styles system).
- No pattern LIBRARY build (L8 recognition feeds it; the library is its own
  track).
- No unification-for-its-own-sake of the 17 passes: they consume the model
  one at a time, behind the gold set, or they stay as they are.
