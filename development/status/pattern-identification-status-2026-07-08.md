# Pattern Identification Status - 2026-07-08

## Overall Task

Build the parallel pattern-identification worktrack described in
[`rk3-pattern-identification-worktrack-plan.md`](../../sources/docs/plans/rk3-pattern-identification-worktrack-plan.md):
read RK3 IR, identify reusable information patterns, support owner review, and
prepare the high-value findings needed by Landing Page work without disturbing
the core PDF conversion pipeline.

## Completed

- Deterministic pattern harness exists under [`patterns/`](../../patterns/),
  with registry, detectors, reports, validation, review summaries, graph export,
  and generated per-document reports.
- LLM prompts have been moved into reviewable prompt assets under
  [`prompts/patterns/`](../../prompts/patterns/) and indexed in
  [`prompts/README.md`](../../prompts/README.md).
- `llm-scan` now focuses on Landing Page signals: `statistic`,
  `impact_statement`, `funding_event`, `quotation`, `key_finding`, and
  `recommendation`, using definitions from
  [`patterns/registry/patterns.json`](../../patterns/registry/patterns.json).
- The Patterns UI surfaces deterministic findings, LLM vetting, LLM proposals,
  provider/model chips, owner review controls, and proposal feedback.
- The corpus view has per-document Analyze buttons plus Analyze all, respecting
  `excludeFromBatch: true`.
- Pilot LLM scans have been run for Design Principles, Clean Air, and Points of
  Light; results live in [`patterns/llm-scans/`](../../patterns/llm-scans/).
- Owner scoring of those proposals has started surfacing actionable misses:
  worded/approximate statistics are now treated as deterministic candidates, and
  LLM statistics are filtered unless they carry an actual value.
- `report_metadata` now separates facts about the report/work itself, such as
  supporters or production credits, from real-world `funding_event` findings.

## Still Undone

- Continue reviewing and classifying pilot LLM proposals beyond the first scored
  pass, especially true LLM-only findings.
- Broaden `report_metadata` beyond the first supporter/production-credit rules
  once more report-about examples appear in owner review.
- Decide which parts of the current development LLM workflow become real
  Landing Page product workflow.
- Expand evaluation beyond the three pilot documents once the review loop feels
  reliable.

## Suggested Next Steps

1. Use the Patterns tab to review LLM proposal rows for the three pilot docs.
2. Summarize accepted/rejected LLM-only proposals by pattern type.
3. Convert repeated deterministic misses into detector improvements where cheap.
4. Keep LLM scanning for nuanced impact, finding, recommendation, and quotation
   extraction where deterministic rules are likely to plateau.
5. Run a second pilot after the next round of rule/prompt tuning.

## Needed From You

- Review enough LLM proposals in the Patterns tab to establish which misses are
  genuinely Landing Page-useful.
- Call out any pattern definitions in
  [`patterns/registry/patterns.json`](../../patterns/registry/patterns.json) that
  do not match your intended meaning.
- Confirm whether LLM proposal review decisions should remain development-only
  training/tuning data or start shaping the production Landing Page extraction
  workflow.
