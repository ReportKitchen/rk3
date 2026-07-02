# Plan: The proposals layer

Status: designed on paper (2026-07-02); open calls for the owner live in
sources/docs/proposals-QA.md. Build order sits after the columns/reading-order
sprint unless re-prioritized.

## What a proposal is

**A proposal is a suggestion, not a mutation.** It is the bridge between
everything that *finds* things (analyze heuristics, the vision-QA reviewer,
the reconciliation flag, magic-wand invocations, future AI passes) and the one
thing that *changes* documents durably: **ops**. Accepting a proposal appends
op(s); nothing else ever mutates content. This keeps the phase contract
intact — the render output is always `f(artifacts, ops)`, reproducible without
re-running any model.

```
finders (rules / vision / wand / AI)          user surfaces
        │                                          │
        ▼                                          ▼
   proposals  ──accept──▶  ops  ──render──▶  output     (auto-apply: accept
        │                                                performed by the
        └──dismiss──▶ recorded, suppressed              system, logged, and
                                                         reviewable)
```

## The record

Stored per-doc in `<source>.proposals.jsonl` beside the source, like ops and
feedback (durable files, not framework state). nid-anchored, so `remap.py`
re-anchors them across reconverts at any depth (cells/items/captions
included — this is why the layer waited for the unified container model).

```jsonc
{
  "pid": "p7c9…",              // hash of (kind, nid, payload) — stable across regeneration
  "kind": "alt-text",          // registry below
  "lane": "issue" | "opportunity",
  "nid": "n4d96…",             // target node(s); [] for doc-level
  "severity": 1-5,              // issues: how broken; opportunities: expected value
  "confidence": 0.0-1.0,
  "source": {"finder": "vision-qa", "model": "haiku-4.5", "run": "rk…"},
  "explain": "…",              // the education text — every proposal teaches why
  "preview": {…},              // optional before/after payload for the UI
  "ops": [{"op": "set-alt", "nid": "…", "value": "…"}],  // EXACT ops acceptance appends
  "status": "open" | "accepted" | "auto-applied" | "dismissed",
  "disposition": {"by": "user"|"auto", "at": …, "opIds": […]}
}
```

Key properties:

- **The payload is complete.** `ops` carries the concrete values (the alt
  text, the color, the reorder sequence). Accepting never re-runs a model;
  regenerating proposals never loses an accepted change (it's in ops).
- **`pid` is content-derived**, so a reconvert that regenerates the same
  suggestion collides with the recorded disposition: a dismissed proposal
  stays dismissed, an accepted one is recognized as already-applied.
- **Generated content is marked.** Ops born from content-gen proposals carry
  `generated: true` + the pid; render emits `data-generated`, and the review
  surface can list every generated fragment in one read (owner rule: any
  content-gen is called out, in place and reviewable in a single pass).

## Lanes: issues vs opportunities

Two lanes, one machinery ([[conversion-philosophy]]: dashboard of
severity-ranked **issues** AND **opportunities**):

- **issue** — fidelity is broken (missing text, wrong order, unmatched
  footnote, garbled table). Default-visible at every assistance level.
- **opportunity** — the original is faithful but could be better on the web
  (contrast floor, alt text, long nav labels, add-headings-to-scan).
  Visibility gated by assistance settings; the copy explains and almost
  justifies each change (the dashboard is partly an education tool).

## Assistance levels

Per-doc (later per-org defaults), same pattern as the AI tier config. Levels
gate which proposal kinds are *generated/shown*, and which may *auto-apply*:

| level | behavior |
|---|---|
| **faithful** | issues only; nothing auto-applies except capital-crime fixes (broken file). "As faithful as possible, but more webby." For orgs forbidden to deviate from the approved document. |
| **suggest** (default) | issues + opportunities surfaced; nothing applies without a click. |
| **assist** | suggest + magic buttons enabled (one click accepts a themed batch, e.g. "improve accessibility"). |
| **autopilot** | assist + whitelisted kinds auto-apply above a confidence threshold — logged, marked, reviewable, one-click revertible (owner: auto-action OK "as long as it's logged and reviewable"). |

Per-kind toggles under the level (the owner's heading examples: shorten
headings/nav, add headings to help readers scan, combine short sections) —
settings inform all three surfaces: magic buttons, the wizard pass, and the
dashboard table.

## First proposal kinds (registry)

| kind | lane | ops it emits | finder |
|---|---|---|---|
| `footnote-residue` | issue | `note` / `ref` | reconciliation flag (exists) |
| `reading-order` | issue | `reorder` (page-scoped) | ordering confidence (columns plan) |
| `fidelity-diff` | issue | varies (`set-text`, `merge`) | vision-QA reviewer (exists, needs wiring) |
| `heading-hierarchy` | issue | `set-level` | rule pass |
| `alt-text` | opportunity | `set-alt` (new op) | content-gen (marked) |
| `contrast` | opportunity | `set-style` (new op) | rule pass (WCAG floor; first view still matches source) |
| `nav-label` | opportunity | `set-nav-label` (new op) | rule or content-gen |
| `table-from-image` | opportunity | `replace-node` (new op) | element-OCR gate ([[rk3-architecture]] sanctions element-level OCR) |
| `wand` | issue | whatever the diagnosis needs | magic-wand invocation on a selection |

Op vocabulary additions this implies — `set-alt`, `set-style`,
`set-nav-label`, `insert-node`, `replace-node`, `mark-generated` (a flag on
other ops rather than an op of its own). All nid-addressed; `wrap-region`
deferred until a concrete kind needs it. Each new op must be expressible
without positional storage (phase contract) — all of these are.

## Magic wand

The wand is a **proposal generator with auto-accept**: user pops a selection,
the finder (AI, analysis tier) diagnoses, and the resulting proposal is
accepted in the same gesture — but it *is* a proposal, so the record, the
marking, and the revert path are identical to everything else. One UX beat
for the user; zero special cases in the machinery.

## Surfaces (requirements round still to come)

- **Dev**: the existing flexi-panel becomes a proposals triage board
  (vision-QA findings land here as `fidelity-diff` proposals; clustering by
  kind across the corpus drives engine work).
- **End-user**: document-centric — wizard pass (one suggestion at a time),
  dashboard table (filter/page), magic buttons (batch accept), inline
  markers. Per the owner: separate products, separate UIs; end-user UX needs
  its own requirements-gathering round before building.

## Build order (when green-lit)

1. Store + lifecycle: proposals.jsonl, pid hashing, disposition persistence
   across reconverts, remap integration. No UI — CLI/JSON only.
2. First rule-based finders (footnote-residue from the flag; contrast): they
   exercise the whole loop with zero AI dependency.
3. `set-alt`/`set-style`/`set-nav-label` ops in render + generated-content
   marking.
4. Wire vision-QA findings in as `fidelity-diff` proposals (replaces the
   planned bespoke triage board data model).
5. Dev triage surface on the flexi-panel; magic buttons; wizard later, after
   the end-user UX requirements round.

## Non-goals

- No proposals UI before the contract above survives store+finders (post-
  container plan's warning).
- No auto-apply defaults beyond the whitelist the owner approves (QA doc).
- Never: outside information, significant-pivot suggestions, dropping
  designed content (pull quotes stay, unconditionally).
