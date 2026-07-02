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
```

`pattern-id` is the command name used by the CLI help text; until a packaging
entry point exists, `python3 -m patterns` is the executable form.
