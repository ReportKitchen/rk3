# Webified — Cycle 3 status (2026-07-08)

Brief status for the conversion-QA track (the "webified" plan). Detail lives in
the referenced docs — this is just the map.

## Task
Execute **Cycle 3** of `sources/docs/plans/webified.md` (the CYCLE 3 DIRECTIVE at
the top of that file): **measure first → fix by frequency → hard stop**. The
number this answers to is "how many pages look right." Governing memory:
`webified-track` (memory dir). Not this track: `patterns/` (other agent).

## Done
- **Owner-audit fixes** (the QA surface was lying / the scanner was weak) — all
  committed: honest scan-log (green needs a *recorded* scan), scanner hunts for
  duplicate-content + wrong-fill, prompts moved to a deployable `prompts/` folder,
  scanner now reads a **distilled** rubric (not the raw design doc
  `sources/docs/conversion-rubric.md`), rubric judges only what's visible +
  duplication measured against the original.
- **Owner quick-hits** — committed: PDF-Metadata Pages+Images columns;
  `excludeFromBatch` flag + toggle (skip big docs from batch, still manual);
  DocList "Disabled" section; **Misflag** disposition (track scanner
  false-positives to tune prompts).
- **Phase A (measure)** — Sonnet scanner calibrated (91.7% vs Opus, ~4× cheaper);
  corpus quick-scan over the **20 active docs** (6 batch-disabled skipped);
  baseline published → `output/CORPUS-SCOREBOARD.md` (**11/166 = 7%** raw, before
  owner review). Appearance categories dominate (§5-first).

## Not done
- **Phase A.3 finalize** — fold in owner review, then commit the baseline + grab
  the representative gallery shots.
- **Phase B (fix by frequency)** — prioritize by pages-affected ÷ effort; new
  lever only if ≥5 pages blocked.
- **Phase C (re-measure + STOPPING RULE)** — the directive's hard stop at
  diminishing returns.
- **Parked engine defects** (Phase B candidates, root-caused): titled-callout
  fill (header-strip vs body), duplicate-heading (dedup). See conversation +
  `webified-track` memory.

## Next steps
1. Owner reviews the scanned docs: Dismiss false positives, **Misflag** scanner
   errors, add misses via Feedback.
2. On owner **"go"**: finalize/commit baseline; produce the prioritized fix list
   (open + misses, minus dismissed/misflagged) + a separate misflag→prompt-tuning
   list.
3. Phase B fixes, verify-re-scan per category; Phase C re-measure; call the stop.

## Need from you
- Finish the review pass and say **"go."**
- Confirm: set aside the **437 pre-today owner comments** (historical backlog) for
  this prioritization? (Default: yes — out of scope by date, untouched in the
  store.)
