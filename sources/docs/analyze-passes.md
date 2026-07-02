# Analyze pass manifest

The declared order of operations inside `rk3/engines/pdfium/analyze.py::run`.
This is the contract that makes the (future) mechanical module split safe: a
pass whose ordering constraint exists only in a comment is a defect — it
belongs here. No heuristic behavior is specified here, only *shape, mutation
rights, and order*. See sources/docs/ir-contract.md for the output schema and
sources/docs/phase-contract.md for the cross-stage constitution.

Input: the assemble artifact (blocks with lines carrying text + per-line runs:
sups/links/marks/colors/fontRuns; running headers already stripped by
assemble). Output: `ir.json` (irVersion 1).

Working shapes (internal only, never in ir.json):
- **runs-dict** `{text, emph, links, marks, colors, sups(, lineJoins)}` — the
  currency of everything between block-join and leaf construction.
- **items** (runs-dicts with optional `sub`) on list nodes — retired from the
  IR by pass 17; list passes still use them internally.

| # | pass | reads | produces / mutates | must follow | why there |
|---|------|-------|--------------------|-------------|-----------|
| 1 | setup: fonts, colors, page dims, `_link_colors` | assemble artifact | ctx.fonts/colors/page_*, link_colors | — | everything downstream |
| 2 | `_join_block` per block → `rich`, `texts` | blocks, link_colors | runs-dict per block (dehyphenation, emphasis, styled-links) | 1 | single source of block text+runs |
| 3 | `_body_size`, `_block_roles`, `_tag_heading_levels` | blocks, struct tags | body_size, per-block (role, coverage), tag→level map | 2 | thresholds + tag evidence for typing |
| 4 | skip building: `_toc_pages` drop, Artifact strip (noteish/edge guards), TOC-tag drop | blocks, roles, texts | `skip` set + audit_claimed | 3 | removals must be logged & claimed before anything consumes blocks |
| 5 | `_detect_regions` + `_merge_cross_page_callouts` | pages, blocks, texts, toc_bands | `regions` (figure/callout kinds), `absorbed` (block→region) | 4 | regions claim blocks before body building |
| 6 | `_find_captions` | regions, blocks, roles | reg.caption/title (+Idx), absorbs caption blocks | 5 | captions must be claimed before notes/body |
| 7 | note eligibility: `note_skip` = absorbed minus `_noteish_block` matches | absorbed, blocks, texts | note_skip | 6 | notes hide inside figures/asides ([[footnote-recovery]]) |
| 8 | `_find_notes` (body-note runs → candidacy → fragments → `_sequence_notes` incl. detached-marker inference + misread split) → absorb note blocks | blocks, texts, note_skip, body_size | fielded `notes`, note_idx, notes_place | 7 | note blocks must not become body paragraphs |
| 9 | `_heading_levels` over unclaimed blocks | main_idx blocks, body_size | size→level ranking | 8 | ranking must exclude claimed blocks |
| 10 | per-page reading order: struct-tree keys when tagged ≥0.6, else `_side_rows` / `_heading_aside_rows` / `_reading_order` XY-cut; collects `twocol_pages` | page_items (blocks+regions), struct tags | ordered page_items, twocol_pages | 5 (regions are items too) | THE ordering decision; everything after inherits it |
| 11 | node construction `_build_item`: `_block_node` (heading paths → lists → paragraph + `_leadHead` mark) / `_try_table` / `_figure_node` / `_aside_node`(+`_aside_images`) / columns rows | ordered items, rich, levels, roles | `nodes` (leaves via `_leaf`, containers via `_container`); figure regions claim their text | 9, 10 | — |
| 12 | `_promote_lead_headings` | nodes with `_leadHead` | heading + remainder paragraph (runs re-sliced) | 11 | consumes a construction-time mark |
| 13 | list formation & repair (exact order): `_split_inline_bullets`, `_group_tag_lists`, `_group_bullet_paragraphs`, `_join_pagebreak_sentences`, `_join_column_wrap`, `_join_broken_paragraphs`, `_merge_crosspage_lists`, `_merge_crosspage_bullet_lists`, `_marker_lists`, `_definition_lists` | nodes (paragraphs/lists, items as runs-dicts) | grouped/merged lists, joined paragraphs | 12 (a lead heading must not be swallowed into a join) | joins before merges; marker/def lists after plain merges |
| 14 | `_floating_pullquotes`, `_aside_layout_and_pullquotes` | nodes, body_size, twocol_pages | asides annotated/extracted, duplicates marked | 13 | needs settled paragraphs |
| 15 | second `_join_broken_paragraphs` | nodes | rejoins sentences a pullquote interrupted | 14 | the intruder is only now extracted |
| 16 | `_indents` (+ centered) | nodes | data.indent/align annotations | 15 | measure final paragraphs |
| 17 | `_assert_rich_items` then `_upgrade_lists` | nodes | items→item containers with leaf children (IR shape) | 13-15 (all item mutation done) | the working-shape→contract boundary |
| 18 | question flood guard, typed-lines question | ctx.questions, nodes | trimmed questions | 11+ | needs all questions raised |
| 19 | footnotes nodes: inline copy at notes_place (contiguous only) + end data copy | notes, notes_place, nodes | footnotes nodes inserted | 8, 17 | placement = where content was found; data copy last |
| 20 | `_attach_refs` | every dict with (text, sups) | refs attached, sups consumed | 17, 19 (leaves exist; notes list final) | the ONE ref attacher — never per-type |
| 21 | `_reconcile_notes` → flag node at top | refs anywhere, notes | flag node (or none) | 20 | the user's QA worklist |
| 22 | `_assert_nids` | whole tree | hard failure on missing nid / retired shape | 17-21 | the contract gate |
| 23 | `_audit` + `write_artifact` | blocks/texts vs nodes, audit_claimed/moved | audit (lost chars = failure), ir.json | everything | information-monotonicity ledger |

## Invariants the order encodes

- **Claiming precedes building**: TOC/artifact strips (4), regions (5),
  captions (6), notes (8) all claim blocks before node construction (11); a
  block is body only if nobody claimed it. Every claim is logged and
  audit-credited.
- **Ordering precedes typing**: reading order (10) is decided on
  blocks/regions, not nodes — the node list is born ordered.
- **Working shape has a hard boundary**: items-as-runs-dicts exist only
  between 11 and 17. Nothing after `_upgrade_lists` may touch `items`;
  nothing in the IR may contain them (`_assert_nids`).
- **Refs are attached exactly once, generically** (20) — after every text
  leaf that will ever exist, exists.
- **The audit is last** and counts the final tree; a pass that deletes text
  must claim it (`audit_claimed`) or the conversion fails the accounting
  test.

## Module split (deferred)

When the mechanical split happens, the groups are the table's phases:
regions+captions (5-6), notes (7-8, plus the `_find_notes` family),
reading-order (10 + `_side_rows`/`_heading_aside_rows`/`_reading_order`),
construction (11-12 + `_block_node` family), lists (13 + list helpers),
layout/asides (14-16), finalize (17-23). Rule for the split: move code, not
behavior; corpus + eval + snapshot must be byte-stable per move.
