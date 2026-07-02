# The IR contract

The shape of `ir.json` — what every producer must emit and every consumer may
assume. Introduced as `irVersion: 1` (analyze v139, 2026-07-02) with the
unified container model. Bump `IR_VERSION` (rk3/engines/pdfium/analyze.py) on
any breaking change to this contract and record it in the history at the
bottom.

## The one rule

**A node is a LEAF (text + inline runs) or a CONTAINER (children). Nothing
else.** A container never stores raw text of its own; text lives in a leaf
child. Any node can appear inside any container — a figure in a cell, an
aside in a caption, a video in a list item are all *renderer* problems, never
*schema* problems.

Enforced at the end of every conversion by `_assert_nids`: every typed node
at any depth carries a `nid`, and the retired shapes (`items`, `rows`, `sub`,
string cells/captions) are hard errors.

## Every node

| field | req | meaning |
|---|---|---|
| `type` | yes | node kind (see below) |
| `nid`  | yes | durable node id — the ONLY sanctioned address for ops/feedback/proposals ([[phase-contract]]: no positional addressing) |
| `page` | yes | source page number (1-based) |
| `bbox` | yes | `[left, bottom, right, top]` in PDF points on `page` |
| `rk`   | yes | provenance key into the analyze debug log (the decision that made this node) |
| `data` | opt | provenance/style hints consumed by the generated stylesheet (font, weight, size, color, role, align, marker, region, …). Only `_HTML_DATA_KEYS` reach the HTML as `data-*` |

Rendered provenance: `data-rk`, `data-page`, `data-nid`, and `data-yf`
(fractional vertical position on the page, for sync-scroll) on block
elements; slim `data-nid` only on `tr`/`td`/`th`/`li`/`figcaption` (their
page/rk provenance lives on the enclosing element).

## Leaf nodes

Carry `text` plus inline runs. All offsets are `[start, end)` into `text`.

| run | shape | meaning |
|---|---|---|
| `emph`   | `[s, e, "strong"\|"em"]` | glyph-derived bold/italic |
| `links`  | `[s, e, target]` — target `{uri}` / `{dest…}` / `{styled: true}` | annotations + link-styled text |
| `marks`  | `[s, e, "#rrggbb"]` | highlight fills |
| `colors` | `[s, e, "#rrggbb"]` | emphasis-by-color runs (non-link) |
| `refs`   | `[s, e, value]` | footnote references (value: int; letters at 1000+ , 'a'=1001) |
| `breaks` | `[offset, …]` | preserved hard line breaks |
| `sups`   | `[s, e]` | raw superscripts — **transient**: consumed into `refs` by `_attach_refs` and absent from the final IR |

Leaf types: `paragraph`, `heading` (adds `level`, `id`, optional
`sectionNum`), deflist entries (paragraph-shaped, with `dl: "dt"|"dd"`).

Construction: **only** via `_leaf(ctx, type, runs, page, bbox, rk, …)` — the
single funnel that attaches every `_RUN_KEYS` run, so no builder can drop a
field ([[first-class-content]]).

## Container nodes

Carry `children`: an ordered list of nodes. Construction only via
`_container(...)`.

| type | children | extra fields |
|---|---|---|
| `list` | `item`* | `ordered` (style), `start` |
| `item` | lead leaf, then any nodes (nested `list` today) | |
| `table` | `row`* | `header` (bool: first row is `<thead>`), `style` (headBg/colFg/…) |
| `row` | `cell`* | |
| `cell` | any nodes (one paragraph leaf today; may be empty) | |
| `figure` | `caption`* | `src`, `alt`, `width`, `height` (leaf-less allowed) |
| `caption` | one paragraph leaf | `variant`: `"title"` (above) or `"caption"` (source line below) |
| `aside` | any nodes | `quote`, `pullQuote`, `borders` |
| `columns` | any nodes (each carries `cell`: column index) | |
| `deflist` | dt/dd leaves | |
| `footnotes` | — (carries `notes`: fielded records, not nodes) | `variant`: `"inline"` \| `"data"` |
| `flag` | — | QA banner (footnote-mismatch) |

`footnotes.notes[*]` are fielded records `{n, marker, page, text, rk,
emph?/links?/marks?/colors?}` — index separate from text, both rendered
copies built from them.

## nid rules

- Hashed on `type|page|normalized-text` when the node has text (immune to
  bbox drift), else `type|page|coarse-bbox`; containers hash the join of
  their children's nids. Collisions get `-2`, `-3` suffixes.
- Stable across reconverts as long as text is stable; `remap.py` re-anchors
  ops/feedback for the rest (exact text → similarity → bbox proximity), at
  **every depth** — cells, items and captions remap like paragraphs.
- Never derive meaning from a nid; it is an opaque address.

## Traversal

Use `rk3.irwalk` (walk / leaves / find / find_parent / of_type /
subtree_text) — never hand-roll a walker. `walk(skip=…)` drops whole
subtrees; `walk(prune=…)` yields a container but not its interior.

## Version history

- **1** (analyze v139, 2026-07-02): unified container model. Cells, list
  items and captions became nodes; `items`/`rows`/`sub` retired; nids
  everywhere; `sups` consumed into `refs`.
