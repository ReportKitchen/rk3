# The Phase Contract — RK3's order-of-operations constitution

*Adopted 2026-07-01, after the RK1 archaeology (see lessons-from-rk1.md §2/§3
and the recipe evidence: enhancements addressed by `page_range: "13-18"` /
`para_range: "25"`, evaluated mid-pipeline inside the page-breaking config).
This is the constitution for the analyze split (R2) and the enhancement layer
(R4). It exists so "we have to do this before that or else we can't do the
thing down the road" never again becomes the shape of the system.*

Order of operations is three different problems. Phase 1–2 ordering is
irreducible — declare it. Everything below the nid line dissolves ordering
with stable addresses and derived views.

---

## The ladder

```
1. EVIDENCE      extract, assemble          read the source; never destroy
2. STRUCTURE     analyze                    ordered passes, DECLARED order
════════════════ THE NID LINE ═══════════════════════════════════════════
   every node now has a stable, content-derived address (nid)
3. ENHANCEMENTS  ops (+ future proposals)   target nids; applied in sequence
4. VIEWS         partition, nav, HTML, CSS  pure functions of (IR + ops)
```

Each phase may read anything above it; it may only write its own output.
Enhancements apply at ONE point (start of render — `_apply_ops` today), all
of them, in stored sequence; views derive after. Nothing in phases 3–4 runs
"inside" phases 1–2.

## The laws

**L1 — No positional addressing below the nid line.**
Nothing below phase 2 may reference content by page number, paragraph index,
byte offset, or match-pattern-at-apply-time. Enhancements resolve their
target ONCE (at authoring time — a pattern match, a click in the UI) to a
nid, and store the nid. Remap keeps nids honest across reconversions; an
unresolvable nid is flagged `orphaned`, never silently re-matched by
position. *(RK1's `para_range: 25` broke the moment a paragraph was inserted
upstream. Nids don't.)*

**L2 — Pagination is a function, never a stage.**
The IR is one continuous document, always. The Page/Paragraph experience —
RK's signature navigation — is a pure partition over the IR:
`partition(ir_after_ops, breakLevel) → pages + nav`. It is computed in phase
4, costs nothing, and can be recomputed by anyone at any time with the same
result. "Before the first section on page N" is a *query over the
partition*, not a pipeline position. *(This dissolves RK1's "we can't inject
page-relative content until we break pages, but breaking pages needs heading
promotion first…" — promotion is phase 2, partition is phase 4; the order is
enforced by architecture, not memory.)*

**L3 — Page-relative placement is an authoring convenience, never a storage
format.** The UI may offer "insert at the top of page 3"; what it STORES is
`before: <nid>`, resolved against the current partition at click time. This
is what keeps structure-changing ops (promote a heading → page boundaries
move) from feeding back into placement: all ops apply in sequence at one
point, the partition derives after, and no stored op depends on the
partition.

**L4 — Phase-2 ordering is declared, not remembered.**
Analyze's passes run in a manifest: an explicit ordered list where each pass
states its contract — what it consumes, what it may change, what must precede
it — with preconditions asserted where cheap. A pass whose constraint lives
in a comment is a defect. *(RK1: "must come after fix-lists, and after
lowercase_class_names" — in a JSON comment the machine never read.)*
Linear-and-declared beats a dependency solver; do not build a DAG scheduler.

**L5 — Annotations are derived, injections are ops.**
Provenance and derived facts ride the IR (`data`, `layout`, `dropCap`…) —
they describe what IS. Content that wasn't in the source (embeds, generated
alt text, added headings, accordion wrappers) enters ONLY as ops/proposals —
marked, logged, reviewable, per the AI-boundaries rubric §13a. *(RK1 tacked
"all kinds of extra content onto every paragraph and page model, to be
pulled back later" — annotations and injections fused because there was no
address space and no ops layer.)*

**L6 — Structure passes enrich; they do not consume evidence.**
Phase 2 may reorder, group, join, and classify, but the audit's
information-monotonicity holds: every character in is accounted for out. A
pass that needs data assemble didn't carry forward is fixed by carrying it
forward (bump VERSION), never by reaching back around the pipeline.

## What already complies (receipts)

- `_apply_ops` runs FIRST in render; nav derives after — a `set-level` op
  already changes navigation with no ordering thought. L3's shape exists.
- nids + remap + `orphaned` flagging exist and survive reconversion.
- The audit enforces L6 today.
- `data-page` is *source-page provenance* (phase-1 fact), not web pagination —
  no conflict with L2.

## Acceptance test for the R4 vocabulary (paper, before code)

Express RK1's three nastiest real enhancements as ops/proposals under these
laws — if any needs a position or a phase to express, the vocabulary is
wrong, and we find out on paper:

1. **Video embed:** CSV of youtube links/titles/captions; each pairs with
   "the paragraph whose first sentence matches X" → authoring-time match →
   `{op: insert-embed, before: <nid>, payload: {url, title, caption}}`.
2. **Case-study highlighting:** sections 13–18 are case studies; nav shows
   them distinctly → `{op: set-class, nid: <heading nid>, class:
   "case-study", navClass: "case-study"}` per section (authored once via a
   range-select in the UI; stored per-nid).
3. **Accordion-from-pattern:** the elaborate pattern-matched accordion/modal
   builds → `{op: wrap-region, from: <nid>, through: <nid>, as: "accordion",
   summaryFrom: <nid>}`.

## When to build the partition

When its first consumer arrives (the multi-page reading experience / LPM
navigation) — not before. Until then the only obligation is negative: nothing
may bake in "the IR is one web page." (Anchors, nav, and links already
target nids/ids, which are partition-independent.)
