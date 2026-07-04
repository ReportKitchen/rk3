> **STATUS:** PARTIALLY SHIPPED. §1 IR stabilization (irVersion in analyze.py; legacy-shim removal via [done/unified-container-model.md](done/unified-container-model.md)) and §2 rk3.irwalk toolkit are **DONE**. §3 analyze pass-manifest split and §4 durable-state hardening are **OPEN** (analyze.py is still one module).

# Plan: Post-container consolidation and readiness work

Status: proposed (for the pause after the unified node / container model lands).

## Why

The unified container model should remove the biggest content-shape problem:
every meaningful thing becomes a node, and every container holds `children`.
The best next move is not to immediately add a new major feature. It is to
cash in the refactor: remove transitional compatibility paths, lock the new IR
contract, and give future work one stable model to target.

This plan is for the work **after** `unified-container-model.md` is done. It is
not parallel work.

## 1. Stabilize the new IR model

Define "container work is done" as more than "the corpus renders." It should
mean every consumer has stopped assuming the old table/list/caption shapes.

- Remove old-shape compatibility code once corpus and eval pass.
- Add `irVersion` to `ir.json`.
- Document the final node contract:
  - required node fields: `type`, `nid`, `page`, `bbox`, `rk`, `data`
  - leaf nodes: `text` plus inline runs (`emph`, `links`, `marks`, `colors`,
    `refs`, `breaks`)
  - container nodes: `children`, never raw text
  - stable `nid` rules for generated child nodes such as `list-item`,
    `table-cell`, `caption`, `table-row`, and future embedded content
  - source-page provenance: `page`, `bbox`, and rendered `data-page` / `data-yf`
- Update render, eval, remap, landing extraction, tests, and the viewer to
consume the final recursive shape only.

Acceptance:

- No production code path checks both "old list items" and "new list-item
  nodes."
- No table cell, caption, header cell, or list item is represented as a bare
  string or text-dict.
- The docs say which IR version introduced the unified container model.

## 2. Build the shared IR toolkit

The unified model makes a shared recursive toolkit worth doing immediately.
Right now the repo has several local walkers and normalizers with slightly
different depth and semantics.

Create a small `rk3.irwalk` module with helpers for:

- walking every node recursively
- walking leaf text nodes only
- finding a node by `nid`
- finding a node and its parent container
- collecting plain text from any subtree
- collecting headings, figures, footnotes, and other common node kinds
- stable text normalization, with named variants if different consumers need
  different matching behavior
- producing a lightweight node summary for tests and debugging

Then replace local walkers in:

- `render.py`
- `eval.py`
- `remap.py`
- `landing/extract.py`
- `tests/summarize.py`

Acceptance:

- Remap is fully recursive, not top-level-plus-one-child.
- Eval list/freeze/order checks work on nested `list-item`, `table-cell`, and
  caption content.
- Tests use the same text collection semantics as the engine.

## 3. Refactor analyze around a declared pass manifest

After the model is stable, split `analyze.py` by contract, not by taste. The
goal is behavior-preserving structure: make the pass order visible to the
machine and to future maintainers before doing more heuristic work.

First create a manifest in code or adjacent docs with:

- pass name
- input shape
- output shape
- what it may mutate
- what must precede it
- what cheap preconditions/assertions it can check

Initial pass groups:

- regions and graphics
- captions
- reading order
- initial node construction
- tables
- headings and lead-heading promotion
- list grouping
- paragraph joins
- pullquotes, asides, and layout annotations
- footnotes and reconciliation
- final audit / question generation

Then move code mechanically into modules following those groups.

Acceptance:

- A pass whose ordering constraint exists only in a comment is treated as a
  defect.
- The full corpus, eval checks, smoke scan, and snapshot review pass after each
  mechanical move.
- No heuristic behavior changes are mixed into the module split.

## 4. Harden durable state

The next product work will write more state: proposals, accepted fixes, magic
button actions, generated alt text, and review dispositions. Before that, make
the existing file-backed state safer.

- Centralize feedback JSONL reads/writes/updates/deletes/dispositions behind
  one helper.
- Use atomic writes or locking for read-modify-write routes.
- Consider doing the same for `.ops.json`.
- Keep the existing API responses unchanged.
- Keep feedback, ops, and proposals as durable files beside or near the source,
  not hidden framework state.

Acceptance:

- `app/main.py` no longer hand-rolls JSONL mutation in every route.
- Concurrent edits cannot silently drop feedback entries.
- Existing UI behavior is unchanged.

## 5. Design the proposal layer on top of ops

Once every content target has a stable `nid`, proposals can become the bridge
between automated analysis and durable user-approved changes.

Rules:

- A proposal is a suggestion, not a mutation.
- An accepted proposal becomes one or more ops.
- Generated content is marked in place and reviewable.
- Assistance-level settings determine which proposal types are generated or
  shown.

First proposal kinds:

- generated alt text
- table-from-image / element OCR opportunity
- accessibility color or link-distinctness warning
- reading-order uncertainty
- heading hierarchy concern
- heading/nav shortening suggestion
- "add headings to help readers scan" suggestion

First op vocabulary to evaluate on paper:

- `set-alt`
- `set-style`
- `insert-node`
- `replace-node`
- `wrap-region`
- `set-nav-label`
- `mark-generated`

Acceptance:

- The Phase Contract examples can be expressed without positional storage.
- A generated alt-text proposal, a table-from-image proposal, and an
  accessibility magic-button proposal can each be represented as proposal(s)
  that become durable op(s).
- Nothing requires re-running an AI model to reproduce an accepted change.

## 6. Prepare the review UX requirements

Use the pause to clarify the product surface before building it.

Known product rules from the open questions:

- First view should look like the user's document, only more readable.
- Improvements are recommendations, not surprise changes.
- Users need both "explain this" and "just fix the obvious stuff" paths.
- Technical users need inspectable detail; overwhelmed users need a guided path.
- Dev dashboard and end-user dashboard are different products.

Draft candidate review surfaces:

- document-local side panel
- wizard pass through suggestions
- issue table with filters and paging
- inline annotation markers
- magic-button summary with undo/review trail

Acceptance:

- The UX doc separates dev-review needs from end-user review needs.
- Each proposal kind has a likely review surface and a likely "magic" behavior.
- The design names what is hidden by default for non-technical users.

## Test plan

For cleanup and toolkit work:

```bash
pytest
python -m rk3 eval
python tools/smoke.py --all
```

For each mechanical analyze split:

- reconvert the representative corpus
- review snapshot diffs intentionally
- eyeball at least one document rich in lists, one rich in tables, one with
  asides/callouts, and one with footnotes

For durable-state work:

- add route-level tests or a small unit suite for feedback update, disposition,
  clear, delete, and empty-trash behavior
- test that two sequential updates preserve both records

## Non-goals

- Do not start Word / Google Docs import in this consolidation pass.
- Do not start the PDF.js replacement here.
- Do not add new content types such as video or accordions yet.
- Do not mix fidelity heuristics into the analyze split.
- Do not build the full proposals UI before the proposal/ops contract is clear.

## Suggested order

1. Stabilize the new IR model.
2. Add the shared IR toolkit.
3. Harden feedback and ops storage.
4. Create the analyze pass manifest.
5. Mechanically split analyze.
6. Design proposals and assistance levels.
7. Draft review UX requirements.

The key principle: after the unified container model lands, make every future
feature aim at one stable tree, one walker, and one durable enhancement path.
