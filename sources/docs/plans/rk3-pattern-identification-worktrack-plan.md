# RK3 Parallel Work Track: Pattern Identification Process

Draft version: 0.2 (0.1 revised by the RK3 main agent 2026-07-02: hard
boundary contract added, §21 integration questions answered inline, Stage A
adjusted to consume the IR's typed nodes instead of re-detecting them)
Companion file: `../specifications/rk3-information-pattern-taxonomy-draft.md`

---

# 0. HARD BOUNDARY — read this first

This track is **identification only** and runs beside, never inside, the
conversion pipeline. The contract, from the RK3 main agent:

## You MAY

- **Read** `output/pdfium/<slug>/ir.json` (your primary input — schema
  contract in `sources/docs/ir-contract.md`, currently `irVersion: 1`),
  `pages/page-*.png` (for vision), `meta.json`, and `blocks.json` only if
  you need pre-IR geometry (prefer the IR).
- **Import** `rk3.irwalk` as a read-only library (walk/leaves/find/of_type/
  subtree_text — the sanctioned traversal). Import NOTHING else from `rk3.*`;
  everything under `rk3/engines/` is private and changes without notice.
- **Create and own everything under `patterns/`** — your package, CLI,
  registry, schemas, gold annotations, review reports, logs. Suggested:
  `patterns/` (code + registry + schemas + gold, tracked in git) and
  `patterns/out/<slug>.json` (generated reports, **gitignored** — they are
  regenerable snapshots, like feedback).
- Run `python -m rk3 list` / read `tests/expectations.json` to seed the
  corpus manifest.

## You MUST NOT

- Modify anything under `rk3/`, `app/`, `tests/`, `eval/`, `tools/`,
  `sources/` (except this plan doc and your own notes under
  `sources/docs/patterns/` if needed), `feedback/`, or any `.ops.json`.
- **Write anywhere under `output/`** — those directories are REGENERATED on
  every reconvert and deleted by `rk3 remove`; anything you put there will
  be destroyed without warning. Your outputs live in `patterns/out/`.
- Bump any `VERSION` constant, touch pipeline fingerprints, add a pipeline
  pass or hook, or register anything with the web app. The review UI is the
  main agent's job (see §23) and will consume your JSON — you never touch
  `app/`.
- Add dependencies to the shared environment without writing it up first
  (see below). Prefer stdlib + what's already installed.
- `git add -A` at the repo root. Commit only paths under `patterns/` (and
  your own docs). The main track commits constantly; blanket adds will
  entangle you.

## When you're tempted to cross the line

You will be — Stage A will make you want a pipeline signal, a schema tweak,
an extra field in ir.json. Don't. Write the request into
`patterns/INTEGRATION-REQUESTS.md` (what you need, why, what you're doing
meanwhile) and continue with a workaround. The main agent reads that file
and either ships the request into the IR contract properly or explains the
alternative. This is the mechanism that keeps the tracks decoupled.

## Purpose

Build a parallel RK3 work track that identifies information patterns in long-form PDFs and Word-style reports while the main RK3 track continues improving PDF-to-HTML fidelity.

The goal is not to generate visual templates. The goal is to recognize the organization, hierarchy, and relationships of information so RK3 can recommend web-native publishing components that can later be styled by any client design system.

In short:

```text
source document
→ extracted content with provenance
→ information pattern candidates
→ reviewed structured pattern objects
→ component/treatment recommendations
→ HTML/PDF renderers apply design system styling
```

## Core principle

Keep this work separated from the PDF fidelity pipeline.

This track should consume RK3 extraction outputs or stable intermediate artifacts, but it should not change core PDF extraction, reading order, layout reconstruction, or rendering behavior without explicit integration work from the RK3 main agent.

The first goal is a reliable pattern-identification harness that can run over a known corpus and produce structured reports. Integration into RK3 output should come later.

---

# 1. Working assumptions

## Corpus

Use the existing corpus of approximately 25 well-understood, highly typical PDFs from different sources.

These documents are valuable because they are familiar enough to evaluate manually, but diverse enough to reveal recurring information patterns.

## Initial scope

Start with recognition and extraction, not final rendering.

For each document, the system should answer:

- What information patterns appear in this document?
- Where do they appear?
- What are their extractable parts?
- What source evidence supports each extracted object?
- What possible web-native treatments are suggested?
- Which suggestions are safe now versus require editorial/data follow-up?

## Non-goals for the first track

Do not start by building a polished UI.

Do not start by generating finished designed pages.

Do not let the LLM invent missing data, missing categories, or unsupported structure.

Do not hard-wire visual styles from sample documents into RK3. The corpus should teach information patterns, not visual clones.

---

# 2. Architecture boundary

Create a separate pattern-identification module/package/service within the RK3 repo or adjacent workspace.

Suggested logical boundary:

```text
RK3 extraction/fidelity pipeline
  produces pages, blocks, text, tables, images, headings, provenance

Pattern identification track
  consumes stable extraction artifacts
  produces pattern candidates and component recommendations

Renderer / product UI
  later consumes selected pattern objects
```

Ask the main RK3 agent to define the exact integration point and artifact format. Until then, this track should accept file-based inputs from the existing corpus.

The pattern track should be able to run independently from the main conversion pipeline once given source artifacts.

---

# 3. Input artifact requirements

For each document, request or produce a normalized input package.

Minimum useful input:

- Document ID
- Page count
- Page-level text
- Block-level text
- Heading candidates
- Table candidates
- Captions if available
- Footnotes/endnotes if available
- Basic reading order
- Source provenance for each block/span

Preferred input:

- Stable node IDs
- Page number
- Bounding boxes
- Extraction confidence
- Original text and normalized text
- Inline spans for links, superscripts, footnote refs, emphasis
- Table cell structure
- Image/caption relationships
- Section hierarchy

The pattern recognizer should tolerate incomplete input, but it should report what evidence was missing.

---

# 4. Output artifact requirements

Produce a deterministic JSON report for each document.

The report should contain:

- Document metadata
- Pattern inventory
- Pattern candidates
- Extracted fields
- Evidence spans / source node IDs
- Confidence scores
- Suggested component treatments
- Missing-data suggestions
- Review status
- Evaluation notes

Example object shape:

```json
{
  "document_id": "example-report-01",
  "pattern_id": "patt_000123",
  "pattern_type": "metric_cluster",
  "layer": 2,
  "status": "candidate",
  "confidence": 0.82,
  "source_refs": [
    {
      "node_id": "n_0451",
      "page": 12,
      "bbox": [72, 144, 522, 198],
      "text": "Total population 4,095,000"
    }
  ],
  "fields": {
    "title": "Oklahoma state profile",
    "metrics": [
      {
        "label": "Total population",
        "value": "4,095,000",
        "unit": "people",
        "geography": "Oklahoma",
        "time_period": "2026"
      }
    ]
  },
  "component_recommendations": [
    {
      "component_type": "stat_card_grid",
      "fit_score": 0.91,
      "reason": "Contains multiple short labeled numeric values with shared geography."
    }
  ],
  "missing_data_suggestions": []
}
```

---

# 5. Pattern registry

Turn the taxonomy draft into a machine-readable pattern registry.

Each pattern should eventually have:

- Pattern name
- Layer
- Definition
- Positive indicators
- Negative indicators
- Required fields
- Optional fields
- Evidence requirements
- Candidate component treatments
- Suitability constraints
- Common false positives
- Extraction prompt
- Validation rules
- Evaluation examples

Start with a small subset. Do not try to implement the full taxonomy at once.

Recommended first subset:

## Layer 0

- Statistic
- Quotation
- Named entity
- Footnote/source note reference
- Date/time period
- Geography/place

## Layer 1

- Key finding
- Recommendation
- Question
- Definition
- Callout

## Layer 2

- Metric cluster
- Question list / checklist
- Q&A set
- Comparison table
- Process/step list

## Layer 3

- Case study
- State/profile page
- Executive summary module
- Recommendations section

---

# 6. Build the corpus manifest

Create a manifest for the 25-document corpus.

For each document, capture:

- File name
- Source organization
- Publication type
- Year/date if known
- Approximate page count
- Known notable patterns
- Known extraction problems
- Whether it contains tables
- Whether it contains charts/infographics
- Whether it contains case studies
- Whether it contains footnotes/endnotes
- Whether it contains strong visual design examples
- Evaluation priority

This manifest becomes the roadmap for systematic testing.

Suggested first categories:

- Heavily designed policy report
- Mostly black-and-white Word-style report
- Data-heavy report
- Case-study-heavy report
- Advocacy report
- Toolkit/guide
- Annual report / impact report
- Research brief
- Appendix-heavy report

---

# 7. Establish gold annotations

Before building too much code, manually annotate a small number of documents.

Start with 3 documents:

1. One clean, well-designed report
2. One black-and-white Word-style report
3. One messy but typical report

For each, manually mark expected patterns for 10–20 pages.

Use a simple JSON or YAML annotation file. Include:

- Pattern type
- Page number
- Source text/snippet
- Expected extracted fields
- Notes on ambiguity
- Suggested treatment if obvious

This gives the agent something real to measure against.

Do not require perfect annotation of the full 25-document corpus at the start. Grow the gold set over time.

---

# 8. Build the first harness

Create a command-line harness that can run pattern identification over one document or the whole corpus.

Minimum commands:

```text
pattern-id ingest <document-artifact>
pattern-id analyze <document-id>
pattern-id report <document-id>
pattern-id eval <document-id>
pattern-id eval --all
```

Expected outputs:

- JSON pattern report
- Human-readable markdown summary
- Evaluation report against gold annotations
- Error/warning log

The first harness can be file-based. It does not need database integration yet.

---

# 9. Recognition strategy

Use a layered recognition approach.

## Stage A: deterministic pre-detection

**Consume, don't re-detect (revision):** the IR already TYPES most of the
structural candidates — headings (with levels), lists/items, tables/rows/
cells, captions, asides, footnote references (`refs` runs), footnote
records. Re-deriving these from raw text would be both wasted work and
WORSE than the pipeline's answer. Stage A reads them off the typed nodes
via `rk3.irwalk`.

Detect in code only what the IR does not type:

- Numbers and units
- Currency
- Percentages
- Dates / time periods
- State names / geographies
- Quotations (marks + attribution shapes)
- Questions
- Repeated label/value structures WITHIN typed nodes (e.g. across the
  cells of one table, or the items of one list)
- Repeated row patterns across sibling nodes

This stage should produce candidate spans anchored to nids.

## Stage B: LLM classification and extraction

Use an LLM to classify candidate chunks and extract fields into the pattern schema.

The LLM should be constrained to:

- Use only supplied text/evidence
- Return structured JSON
- Include source spans/node IDs
- Mark uncertainty
- Distinguish extracted facts from suggestions
- Avoid inventing missing data

## Stage C: deterministic validation

Validate LLM output with code:

- Required fields present
- Source refs exist
- Values appear in source text
- Dates/geographies are grounded
- Pattern type is allowed
- Confidence is within range
- Component recommendations meet pattern requirements

Invalid objects should be rejected or marked for review.

## Stage D: grouping and assembly

Combine lower-level objects into higher-level patterns:

- Multiple statistics with shared subject → metric cluster
- Questions in sequence → checklist/question list
- Repeated label/value rows → profile module
- Paragraph + quote + place + outcome → case study candidate
- Recommendations with owners/timelines → action table candidate

Favor transparent scoring over brittle if/else rules.

---

# 10. Prompt strategy

Do not use one giant prompt for the whole document.

Use several focused prompt types.

## Prompt 1: chunk classifier

Purpose: classify a block, table, or section into likely pattern types.

Expected output:

- Candidate pattern types
- Confidence
- Evidence text
- Reasoning summary suitable for logs
- Whether more context is needed

## Prompt 2: atomic extractor

Purpose: extract statistics, quotations, dates, places, entities, source references, definitions, and questions.

Expected output:

- Structured atomic objects
- Exact source text
- Field values
- Confidence
- Warnings

## Prompt 3: compound pattern assembler

Purpose: identify medium-level structures from nearby atomic objects and layout/section context.

Expected output:

- Metric clusters
- Checklists
- Q&A sets
- Process lists
- Comparison structures
- Recommendation groups

## Prompt 4: component recommender

Purpose: suggest web-native treatments from validated pattern objects.

Expected output:

- Candidate components
- Fit score
- Why it fits
- Required data
- Missing data
- Editorial questions
- Accessibility concerns

## Prompt 5: corpus pattern miner

Purpose: offline analysis of high-quality examples to discover reusable information patterns.

Expected output:

- Pattern description
- Content requirements
- Visual/structural traits
- Notable variations
- When not to use
- Candidate registry entry

This prompt is for building the pattern library, not for runtime conversion.

---

# 11. Human review loop

Build the first review loop as simple files, not a full app.

For each document, produce a markdown review report with:

- Pattern inventory by page/section
- High-confidence candidates
- Low-confidence candidates
- Extracted fields
- Suggested treatments
- Missing-data suggestions
- False positive candidates
- Questions for reviewer

Reviewer decisions should be recordable as:

- Accept
- Reject
- Accept with edits
- Wrong type
- Missing fields
- Needs more context
- Useful suggestion but not supported by source

These decisions should feed future evaluation and prompt/rule refinement.

---

# 12. Evaluation method

Track at least three levels of accuracy.

## Detection accuracy

Did the system find the pattern at all?

Example: Did it notice that a page contains a metric cluster?

## Field extraction accuracy

Did it extract the correct parts?

Example: Did it correctly identify quote text, speaker, title, affiliation, and source context?

## Recommendation usefulness

Did it suggest a reasonable component/treatment?

Example: Did it suggest stat cards for short comparable metrics, but not for a dense 40-row appendix table?

Metrics:

- Precision by pattern type
- Recall by pattern type
- Field accuracy
- Source grounding rate
- False positive rate
- Human acceptance rate
- “Needs editorial follow-up” usefulness

The first useful metric may simply be reviewer acceptance rate by pattern type.

---

# 13. Component recommendation layer

Keep this abstract. Do not tie recommendations to final CSS yet.

Recommended output vocabulary:

- Stat card
- Stat card grid
- Pull quote
- Quote card
- Checklist
- Q&A accordion
- Process/timeline
- Comparison table
- Before/after comparison
- Profile header
- Geographic selector
- Case study card
- Key findings module
- Recommendation/action table
- Evidence stack
- Data appendix
- Interactive filter/search module

Each component should declare:

- Required data
- Optional data
- Maximum/minimum item counts
- Text length limits
- Accessibility notes
- Responsive behavior notes
- Good/bad fit examples

The design system later decides colors, typography, spacing, icon style, and final layout details.

---

# 14. Missing-data and editorial suggestions

This is a major product opportunity and should be tracked from the start.

The system should produce two categories of suggestions.

## Safe transformation suggestions

These can be done with the source content as-is.

Examples:

- Convert this 4-row metric table into stat cards.
- Convert this question list into a checklist module.
- Pull this quote into a quote card.
- Convert this recommendations list into an action table.

## Editorial/data follow-up suggestions

These require more information or author/editor review.

Examples:

- This California-only statistic might become stronger as a 50-state comparison if comparable data exists.
- This program description mentions three audiences; consider adding audience-specific takeaways.
- This table has outcomes but no time period; add dates before turning into a chart.
- This case study has a quote and outcome, but no named location or participant role.

Never present editorial/data follow-up suggestions as already-supported transformations.

---

# 15. Pattern mining from high-quality examples

Use the corpus of designed reports and websites to discover patterns, but keep human review in the loop.

Workflow:

1. Extract visual/content structure from high-quality examples.
2. Ask the LLM to describe the information pattern, not the graphic style.
3. Cluster similar patterns across documents.
4. Human reviews cluster labels and examples.
5. Convert accepted patterns into registry entries.
6. Add positive and negative examples.
7. Add suitability rules and component mappings.

Important distinction:

```text
Do learn: "four short metrics can become an icon-topped stat-card row."
Do not learn: "copy this exact Oklahoma profile design."
```

---

# 16. Suggested build phases

## Phase 0: Setup and alignment

Deliverables:

- Read the taxonomy draft.
- Create a short implementation notes document.
- Confirm repo location for the pattern work track.
- Confirm input artifact format with RK3 main agent.
- Create corpus manifest file.
- Select first 3 pilot documents.

Acceptance criteria:

- Agent can describe the separation between PDF fidelity and pattern identification.
- Agent can run a placeholder harness over one document artifact.

## Phase 1: Registry skeleton

Deliverables:

- Machine-readable pattern registry for the initial subset.
- Schema for pattern objects.
- Schema for component recommendations.
- Schema for review decisions.
- Basic validation script.

Acceptance criteria:

- Invalid pattern objects fail validation.
- Pattern registry can be loaded by the harness.
- At least 10 initial pattern definitions exist.

## Phase 2: Corpus manifest and gold annotations

Deliverables:

- Manifest for the 25-document corpus.
- Manual annotations for 10–20 pages across 3 pilot documents.
- Review notes for ambiguous cases.

Acceptance criteria:

- Evaluation harness can compare output to gold annotations.
- Gold annotations include source snippets and expected fields.

## Phase 3: Deterministic pre-detection

Deliverables:

- Candidate detection for statistics, dates, geographies, questions, quotes, bullets, headings, and table-like structures.
- Candidate report per document.

Acceptance criteria:

- The harness finds obvious numeric facts and question lists in pilot documents.
- Output includes source refs and confidence/score.

## Phase 4: LLM extraction harness

Deliverables:

- Prompt templates for chunk classification and atomic extraction.
- JSON output parsing and validation.
- Retry/failure handling.
- Audit logs of prompt input/output.

Acceptance criteria:

- LLM-extracted objects validate against schema.
- Unsupported/invented fields are rejected or flagged.
- Each extracted object includes evidence.

## Phase 5: Compound pattern assembly

Deliverables:

- Grouping/scoring logic for metric clusters, Q&A sets, checklists, process lists, and recommendation groups.
- Compound object output.

Acceptance criteria:

- The system can identify at least 3 compound patterns in pilot documents.
- Reviewer can see why items were grouped.

## Phase 6: Component recommendation

Deliverables:

- Abstract component vocabulary.
- Fit scoring for first set of component treatments.
- Missing-data/editorial suggestion logic.

Acceptance criteria:

- For each accepted compound pattern, the system suggests one or more treatments.
- Suggestions distinguish safe transformations from editorial/data follow-up.

## Phase 7: Review reports

Deliverables:

- Markdown review report per document.
- JSON review-decision file format.
- Summary report across all pilot documents.

Acceptance criteria:

- A human can review candidates without reading raw JSON.
- Review decisions can be fed back into evaluation.

## Phase 8: Expand to 25-document corpus

Deliverables:

- Run harness over full corpus.
- Pattern frequency report.
- False positive report.
- Missing pattern report.
- Recommendations for taxonomy changes.

Acceptance criteria:

- Agent can summarize which patterns are common, rare, noisy, and high-value.
- Agent proposes a prioritized next implementation list based on evidence.

## Phase 9: Integration planning with RK3

Deliverables:

- Proposed input contract from RK3 unified IR.
- Proposed output contract back to RK3/product UI.
- Integration risks.
- Performance/cost estimate.
- Runtime/offline division recommendation.

Acceptance criteria:

- Main RK3 agent can review and approve integration points.
- Pattern track remains separable and testable.

---

# 17. Runtime versus offline use of LLMs

Separate three different uses of LLMs.

## Offline pattern mining

Use LLMs to analyze high-quality examples and help build the registry.

This can be slower, more exploratory, and human-reviewed.

## Assisted extraction

Use LLMs to classify and extract fields from document chunks.

This should be validated and logged.

## Production recommendations

Prefer deterministic logic once patterns and fields are known.

LLM use in production should be optional, bounded, auditable, and never the sole source of truth for unsupported claims.

---

# 18. QA and safety principles

Every pattern object must be source-grounded.

Every generated suggestion must be categorized as either:

- supported by current source
- requires editorial review
- requires additional data
- speculative / not recommended

The system should fail closed:

- If no evidence, do not extract.
- If fields are missing, mark incomplete.
- If confidence is low, route to review.
- If the suggested component requires data not present, state that clearly.

---

# 19. Risks

## Risk: LLM overconfidence

Mitigation: require exact evidence spans, schema validation, confidence scores, and reviewer acceptance tracking.

## Risk: pattern taxonomy becomes too broad

Mitigation: start with high-frequency/high-value patterns only.

## Risk: deterministic rules become spaghetti

Mitigation: use declarative pattern definitions, suitability scoring, and per-pattern validators.

## Risk: visual examples become copied designs

Mitigation: extract abstract information structures and component requirements, not exact appearance.

## Risk: integration destabilizes RK3 fidelity work

Mitigation: keep file-based, read-only integration until the main RK3 agent defines a clean contract.

## Risk: users interpret suggestions as facts

Mitigation: separate source-supported transformations from editorial/data follow-up suggestions.

---

# 20. First agent assignment

Ask the agent to begin with these tasks:

1. Read `rk3-information-pattern-taxonomy-draft.md`.
2. Create a separate pattern-identification work area.
3. Create the corpus manifest structure.
4. Add entries for the 25 known PDFs, even if some fields are initially blank.
5. Define JSON schemas for pattern objects, pattern registry entries, component recommendations, and review decisions.
6. Convert the first 10–15 taxonomy patterns into machine-readable registry entries.
7. Create a CLI harness that can load a document artifact and output an empty but valid pattern report.
8. Implement deterministic pre-detection for statistics, questions, quotations, dates, and geographies.
9. Produce a first review report for one pilot document.
10. Stop and document integration questions for the RK3 main agent before modifying RK3 core code.

---

# 21. Questions for the RK3 main agent — ANSWERED (2026-07-02)

1. **Cleanest stable artifact:** `output/pdfium/<slug>/ir.json`. It just
   stabilized under the unified container model (`irVersion: 1` — one
   schema: text LEAVES with inline runs, CONTAINERS with children; contract
   in `sources/docs/ir-contract.md`). Body order IS reading order. Pair with
   `pages/page-*.png` for vision work.

2. **Yes, all of it:** every typed node at any depth carries a durable
   `nid`, `page`, `bbox`, `rk`. Table cells are real nodes (table > row >
   cell > paragraph leaf), lists are list > item > [leaf, nested list],
   captions are caption > leaf. Inline runs: `emph`, `links`, `marks`,
   `colors`, `refs` (footnote references, `[start, end, value]`), `breaks`.
   Footnotes are fielded records (`n`, `marker`, `page`, `text`) on the
   `footnotes` node. Headings carry `level`.

3. **Output lives in `patterns/out/<slug>.json`** (gitignored, regenerable);
   registry/schemas/gold/code under `patterns/` (tracked). Never under
   `output/` — reconversion destroys those directories.

4. **Separate CLI, file-based.** Not a pipeline op, not a post-processing
   hook. If it ever becomes runtime, that's a §-9-style integration decision
   the main agent makes against the proposals layer.

5. **Anchoring:** reference nodes as `{nid, page, quote}` — nid first, plus
   the verbatim source quote and page as relocation fallback (the same
   triple the feedback system uses). nids are content-hashed and stable
   across most reconverts, but the main track re-converts constantly and
   does NOT remap your files; so ALSO stamp every report with the input's
   `irVersion` and the conversion fingerprint mtime, treat a mismatch as
   "stale — re-run," and never hand-repair anchors. Reports are snapshots,
   not databases.

6. **Reuse:** `python -m rk3 list` for the corpus; `tests/expectations.json`
   for known-doc quirks; `rk3.irwalk` for traversal. The eval gold set
   (`eval/*.yaml`) pins STRUCTURE, not patterns — build your own gold
   annotations as planned (§7); don't extend eval/.

7. **Touch nothing outside `patterns/`** — see §0. The main track is
   mid-flight on lists and proposals; the IR contract (ir-contract.md) is
   the only interface, and changes to it will be versioned and announced
   via `irVersion`.

---

# 22. Definition of done for first useful milestone

The first useful milestone is not a finished product.

It is:

- A 25-document corpus manifest exists.
- Three pilot documents have manual gold annotations.
- A pattern registry exists for the initial subset.
- A harness runs independently.
- The harness detects basic atomic patterns.
- The harness produces source-grounded JSON and markdown reports.
- A human can review candidates and mark accept/reject/edit.
- Evaluation reports show where detection works and fails.
- Integration with RK3 is documented but not entangled.

At that point, the team can decide whether to deepen extraction, build review UI, add component previews, or integrate into the main RK3 workflow.

---

# 23. The handoff: review tab (main agent's side, added 2026-07-02)

When the first `patterns/out/*.json` reports land, the **main agent** builds
a Patterns tab in the existing viewer: an aggregate view (pattern frequency
across the corpus, filterable by type/layer/confidence/status) and a per-doc
overlay (each candidate's `source_refs[].nid` highlights the corresponding
`data-nid` element in the rendered document). Review decisions recorded there
write back to your review-decision format (§11).

What this requires from the pattern track — non-negotiable schema fields:

- top-level `"schema": <int>` in every report (bump on breaking changes; the
  tab pins to a schema version);
- `source_refs` entries as `{nid, page, quote}` (the overlay is nid-driven);
- `"input": {"irVersion": …, "convertedAt": …}` staleness stamp;
- stable `pattern_type` ids matching the registry (aggregation keys).

Two smaller conventions, matching the main repo's practice:

- Log every model call's token usage + cost to `patterns/logs/api-usage.jsonl`
  (same shape as the main pipeline's `logs/api-usage.jsonl`).
- This track is ANALYSIS-ONLY in the AI-tier sense: reports contain pointers
  and structured fields grounded in source text, never generated prose
  presented as content. Editorial/data follow-up suggestions (§14) are
  suggestions, clearly typed — this maps 1:1 onto the proposals layer's
  issue/opportunity lanes when integration eventually happens
  (plans/proposals-layer.md), which is why the safe-vs-editorial distinction
  must never blur.
