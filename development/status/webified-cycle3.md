# Webified — Cycle 3 status (COMPLETE 2026-07-09)

Conversion-QA track ("webified" plan). Detail lives in the referenced docs +
the `webified-track` memory; this is the map.

## Task
Execute **Cycle 3** of `sources/docs/plans/webified.md` (the CYCLE 3 DIRECTIVE):
**measure first → fix by frequency → hard stop**. The number this answers to is
"how many pages look right." Not this track: `patterns/` (other agent).

## Done — CYCLE 3 COMPLETE
- **Phase A (measure):** Sonnet scanner calibrated (91.7% vs Opus, ~4× cheaper);
  honest scan-log (green = *recorded* scan + zero open medium+ error); prompts in a
  deployable `prompts/` folder reading a distilled rubric; scanner hunts
  duplicate-content + wrong-fill. Baseline **15/166 = 9%** over 20 active docs →
  `output/CORPUS-SCOREBOARD.md`. Owner-audit fixes + quick-hits committed.
- **Phase B (fix by frequency) — 4 fixes shipped, all gated (census 79/3,
  pytest 33/33) + eyeballed:**
  1. dehyphenation (`ca25670`, analyze 213)
  2. image-grounded callout fill — the "brown box" lever (`a0be025`, analyze 214;
     38 fixes / 10 docs)
  3. drop-cap all-caps false-positive — edf's whole body was SHOUTED (`71042ac`,
     assemble 53)
  4. reader-chrome removal — footnote-mismatch QA banner (~6 docs) + flipbook nav
     bar (`92db61a`, analyze 215 / render 86)
- **Phase C (re-measure + STOP):** re-scanned the 21 fix-touched pages
  (same model as baseline). **Medium+ findings 79 → 58 (27% cleared)**; pages fully
  green 0/21 → 1/21. Residual is dominated by DEEP FEATURES (dedup, tables,
  figure-recovery, reading-order). Pass-rate ~9% → ~9.6% (<2 pts) → **STOPPING RULE
  DECLARED** (the directive's success condition). Close-out: the Phase C section of
  `output/CORPUS-SCOREBOARD.md`.

## Deferred (named, not lost)
- **Dedup via on-demand OCR** — the biggest category (~40 CRITICAL: text baked into
  a raster AND extracted live). A heuristic proved UNSAFE (would delete real charts +
  photos). Needs OCR to confirm an image contains the same text.
  → `development/status/ocr-baked-text-deferred.md` (owner-requested capability).
- **Callout header-strip modeling** (Phase 2 of fix #2): boxes now render white-body +
  colored border but lose the colored title bar.
- **Table-structure assembly, figure-recovery, deep reading-order** — dedicated
  engine projects, each regression-risky, each parked with exemplars in
  `webified-track` memory.
- **emphasis-style / spacing long-tails** — low-severity, heterogeneous; not pursued
  under the hard-stop rule.

## Needs from owner (to reopen)
- Green-light one of the deferred DEEP features as a dedicated next pass (OCR-dedup is
  the highest-leverage). Otherwise cycle 3 is closed.
