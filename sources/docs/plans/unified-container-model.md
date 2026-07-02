# Plan: Unified node / container model

Status: IMPLEMENTED (2026-07-02, owner approved; five eval-gated commits).
- Step 1 — `_leaf`/`_container` constructors, `_assert_nids` invariant,
  paragraph+heading routed through `_leaf` (3988053; byte-identical output).
- Step 2 — table > row > cell > paragraph-leaf (02fa59b); cell refs/bold/
  links live; gates notes-without-ref → 0. Naming as implemented: `row` /
  `cell` (not table-row/table-cell).
- Step 3 — list > item > [leaf, nested list] (0a25f6e); `_upgrade_lists` is
  the finalization point (list passes keep runs-dict internals).
- Step 4 — figure title/caption → `caption{variant, children:[leaf]}`
  (292783b); caption refs/italics live. Header cells were covered by step 2.
- Step 5 — legacy shims removed; `_assert_nids` also rejects retired
  items/rows/sub shapes. Six sourceless orphan docs keep their pre-migration
  static HTML (they cannot reconvert or re-render; no source PDF).
Eval held 25/4 at every step; representative pages eyeballed per step.

## Why

The footnote work kept hitting the same wall from new angles: a reference in a
list item, then in a heading, then in a table cell. Each was "we looked in the
wrong kind of node." The root cause is that the IR has **three different models
for holding content**, so "can this thing contain that thing?" has three
different answers depending on where you are:

| Container | Today holds | Can hold text? | Can hold a figure / video / aside? |
|---|---|---|---|
| paragraph / heading | its own `text` + inline runs | yes | **no** |
| list item | a text-dict (`{text, emph, links, marks, colors}`) + optional `sub` list | yes | **no** |
| table cell, header cell, figure caption | a bare **string** | barely (no inline runs) | **no** |
| aside, columns | `children`: a list of real nodes | via child nodes | **yes** |

Only asides and columns are right. Everything else is a dead end: a table cell
can't even carry bold, let alone a footnote reference (that's why gates notes
320-325 can't reconcile), and nothing but an aside/column can ever hold a
figure. The stated near-future need — "a video in a table cell, a figure in a
header, an aside in a caption" — is impossible in today's model, and every
feature that adds a new place content can live re-opens the same bug.

This is the concrete form of the [[first-class-content]] rule and the R3
"IR contract / shared walker" backlog item.

## The target model

One node schema. One containment rule. One recursive pass.

1. **Every piece of content is a node.** A node has: `type`, `nid`, `page`,
   `bbox`, `data`, `rk`. (Today cells and list items have no `nid` — so they
   can't be addressed by ops or feedback. Under this model everything is
   addressable, which the edit-ops and assertion layers want anyway.)

2. **Two node shapes, nothing else:**
   - **Leaf (text) nodes** carry `text` plus inline runs (`emph`, `links`,
     `marks`, `colors`, and `sups`→`refs`). `paragraph` and `heading` are leaves.
   - **Container nodes** carry `children`: an ordered list of nodes. `list`,
     `list-item`, `table`, `table-row`, `table-cell`, `caption`, `aside`,
     `columns`, `column`, `footnotes` are containers.
   A container never stores raw text of its own; text lives in a leaf child.
   (A text table cell becomes `cell{children:[paragraph]}`. Slightly more
   verbose, but it means the cell can just as easily hold `[figure]` or
   `[video]` tomorrow with zero new plumbing.)

3. **One recursive walk.** `_attach_refs` is already fully generic (visits every
   dict, every list). Rendering, reconciliation, the audit, and the edit-ops
   apply-pass all collapse to the same shape: dispatch a leaf by `type`, render
   a container by rendering its `children`. Adding a new node type (video embed,
   accordion, tab group) needs a renderer for that type and nothing else — it
   automatically nests anywhere, and refs/links inside it automatically work.

## What changes, concretely

### analyze (production side)
- Introduce a small constructor set: `_leaf(type, text, runs, blk)` and
  `_container(type, children, blk)` that always attach `nid`/`page`/`bbox`/`rk`
  and thread inline runs (incl. `sups`) — so no builder can hand-roll a node and
  drop a field. This is the structural guarantee that replaces "remember to
  carry sups in each builder."
- Migrate the string/text-dict containers to `children`:
  - **table cells** → `table-cell{children:[leaf...]}`; the cell's text (and its
    superscript refs, bold, links) live in a leaf built from the cell's block
    slice. Header cells likewise.
  - **list items** → `list-item{children:[leaf, (nested list)]}` instead of a
    text-dict with `sub`.
  - **figure captions** → `caption{children:[leaf]}` instead of a caption string.
- `_attach_refs` unchanged (already generic) — it just starts finding the refs
  that now exist on the migrated leaves.

### render (consumption side)
- Collapse `_render_node` so container types render `children` recursively;
  delete the bespoke string handling (`html.escape(c)` for cells,
  `_item_inline` special path). One `_inline` for every leaf.
- Table render becomes: `<td>` + render(children). Caption/header the same.

### everything else that reads the old shapes
- audit (`_alnum` over cell strings), reconciliation, ops apply-pass, eval
  anchor-matching, `_fn_keys`. Each currently assumes strings/text-dicts in
  places; each moves to the leaf/container shape. The generic walk means most of
  these get simpler, not more complex.

## Migration order (each step: reconvert corpus + eval must hold, eyeball)

Do it container-by-container behind a tolerant renderer (render accepts both the
old shape and the new during the transition), so the corpus is never broken:

1. **Node constructors + nids-everywhere** (no behavior change; adds ids).
2. **Table cells → containers.** Verifies on gates (320-325 reconcile as a side
   effect; cell bold/links appear). Highest value, most-contained.
3. **List items → containers.** Verify list-heavy docs (good-food, oxfam).
4. **Captions / header cells → containers.**
5. **Remove the compatibility shim**; assert one shape everywhere.

## Risks / guards
- Blast radius is the whole IR consumer surface; the eval gold set (25/4) is the
  regression gate at every step, plus eyeball on representative docs per the
  hard rule.
- Verbosity: wrapping text cells in a leaf child grows the IR. Acceptable; it's
  the price of composability and the JSON compresses.
- Ops/feedback addressing: giving cells/items nids is a prerequisite and a win
  (users can tag a cell), but nid stability rules ([[phase-contract]]) must hold
  — ids hashed on normalized text like existing nodes.

## What it unlocks
- References/emphasis/links **everywhere** by structure, not per-type code — the
  footnote residue in cells (320-325) closes without a table-specific feature.
- "Video in a cell, figure in a header, aside in a caption" become trivial: put
  the node in the child list.
- The edit-ops and landing-page/interactive-embed roadmap get a single content
  model to target instead of three.

## Non-goals (for this refactor)
- No new content types (video/accordion) built here — just the model that makes
  them cheap.
- No change to reading-order, pagination, or the footnote logic just shipped.
- OCR / image-text extraction unchanged.
