# RK3 Pattern Identification Worktrack

This package implements the parallel, identification-only worktrack described
in `sources/docs/plans/rk3-pattern-identification-worktrack-plan.md`.

It reads `output/pdfium/<slug>/ir.json`, traverses nodes through `rk3.irwalk`,
and writes regenerable JSON reports to `patterns/out/` plus markdown review
summaries to `patterns/reports/`.

## Commands

```bash
python3 -m patterns ingest 02--foia-basics-for-activists-may-2019
python3 -m patterns analyze 02--foia-basics-for-activists-may-2019
python3 -m patterns report 02--foia-basics-for-activists-may-2019
python3 -m patterns eval 02--foia-basics-for-activists-may-2019
python3 -m patterns eval --all
python3 -m patterns review-summary --markdown
python3 -m patterns graph 03--enterprise-annual-report-2022
python3 -m patterns vet 02--clean-air-fund --pattern-type statistic --limit 12 --dry-run
python3 -m patterns vet 02--clean-air-fund --pattern-type statistic --limit 12 --provider deepseek --model deepseek-chat --write
python3 -m patterns vet-summary 02--clean-air-fund --markdown
python3 -m patterns llm-scan 02--clean-air-fund --page 4 --page 5 --limit-findings 12 --provider deepseek --model deepseek-chat --write
python3 -m patterns llm-scan-summary 02--clean-air-fund --markdown
```

`pattern-id` is the command name used by the CLI help text; until a packaging
entry point exists, `python3 -m patterns` is the executable form.

`vet` is a development helper: it asks the configured LLM for structured
first-pass reviews of deterministic candidates and writes optional JSONL rows to
`patterns/llm-reviews/`; `vet-summary` makes those rows easier to scan. Human
review decisions in `patterns/review-decisions/` remain the source of truth.

`llm-scan` is the complementary development helper: it asks the LLM to do its
own document scan from the IR text and writes optional JSONL rows to
`patterns/llm-scans/`; `llm-scan-summary` highlights likely deterministic
overlap versus LLM-only findings.
