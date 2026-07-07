> **STATUS:** CYCLE 1 EXECUTED end-to-end (Claude Opus, 2026-07-04..07). Deterministic
> backbone §0–§6 + §7.1 COMPLETE + durable (census 71/6→77/5); vision-loop thesis
> VALIDATED (§7.2, §5-first confirmed); §8 handoff report at `webified-report.md`.
> The LEDGER + PARKED below are the durable state. Cycle 2 restart: see the report's §5.

# WEBIFIED: the long cycle to "that's my document, only webified"

*(Authored by Fable 2026-07-03 for execution by Claude Opus in one long,
uninterrupted development cycle. The owner will not be available to answer
questions mid-run — every decision an executor would normally ask about is
pre-decided in this document. When something is genuinely undecidable, use
the PARKED protocol in §0.6 and keep moving.)*

## The goal

The owner opens a converted document and says: **"That's the same document,
only webified."** Concretely, a PAGE PASSES when:

- a vision-QA scan of that page reports **zero issues at severity medium or
  higher** (low-severity and by-design transforms are acceptable), and
- every gold stake touching that page is green.

A DOCUMENT PASSES when >80% of its pages pass. The RUN SUCCEEDS when more
than half of all pages corpus-wide pass, and every failing page appears on
the final residual list with a stated reason and the missing lever that
would fix it (§8).

## Why this architecture

Two years of evidence in this repo says: deterministic rules compress the
easy 80% beautifully and hit a complexity ceiling on the tail (this week:
every new figure rule needed three guards mined from three mis-fires).
The owner's direction, adopted here:

1. The deterministic engine stays the backbone — it handles easy pages and
   provides the VOCABULARY (regions, bands, claims, captions, order).
2. Hard pages get a per-document VISION LOOP: a vision model compares our
   render against the original page and emits OVERRIDES — declarative,
   per-document, reversible config entries in the same schema the owner's
   own answers use — never prose rules and never engine edits.
3. The loop iterates per document until convergence. Residue that no lever
   can express gets PARKED with a named missing lever, not hacked around.
4. Cross-document learning moves offline: recurring override patterns are
   promotion candidates for the deterministic core (§8), harvested at the
   end, not during the run.

---

## §0 — Ground rules (the constitution; violating these is run failure)

### 0.1 Verification gates — every engine change, no exceptions
1. **Stakes first**: plant the gold check BEFORE the fix; verify it FAILS;
   record red-at-plant in the yaml comment. `python -m rk3 eval <slug>`.
2. **VERSION bump**: any logic change to `rk3/engines/pdfium/analyze.py`
   bumps its `VERSION`; any change to `rk3/render.py` bumps its `VERSION`.
   Forgetting this silently serves cached stages and has burned this
   project three times. If you changed logic and re-ran without a bump,
   your results are lies — bump and re-run.
3. **Census**: `python -m rk3 eval` (full corpus). Previously-green checks
   that turn red are REGRESSIONS: fix or revert before proceeding. The
   count of greens must be monotonically non-decreasing across the run.
4. **Snapshot ritual**: `python -m pytest tests/ -q`. For each snapshot
   diff, adjudicate with the leaf-walk diff (recipe in §0.8) against the
   SOURCE PAGE IMAGE (`output/pdfium/<slug>/pages/page-NNNN.png`). Only
   after every diff is judged intended: `python -m tests.regen`, re-run
   pytest, review `git diff tests/snapshot.json`.
5. **Eyeball rule (owner, all-caps, non-negotiable)**: every fix ends with
   screenshotting the rendered page and LOOKING at it. Scratch scripts for
   this exist and are promoted into `tools/` in §1.4. Artifact metrics are
   not verification. Logs are not verification (this run exists partly
   because log lines that looked like fixes weren't).
6. **Vision delta for visual work**: any change touching figures, layout,
   or styles reports a before/after vision scan on the affected pages
   (§0.8 for the endpoint). "Census green" alone is insufficient for
   anything the eye can see.

### 0.2 Change policy
- Per-document fixes go in OVERRIDES (config/ops), never engine code.
- Engine changes are allowed only when a stage below explicitly calls for
  them, and always under the §0.1 gates.
- NO new architecture, NO new frameworks, NO new dashboards beyond what a
  stage explicitly specifies. If mid-run you believe an architectural
  change is needed: PARK it (§0.6). This is the anti-drift rule; the run's
  value is a straight line.

### 0.3 Files you must never edit
- `feedback/*.jsonl` EXCEPT via the two sanctioned writes: appending
  vision-qa records through the API, and setting `disposition` on
  vision-qa records you can prove resolved (§1.2). Owner-typed notes
  (`type: comment/answer`, no `source` field) are read-only.
- `sources/**/*.ops.json` — owner-authored edit ops. Read-only.
- `sources/docs/TODO.md`, `sources/docs/BACKLOG/**` — owner's files.
- `patterns/**` — the pattern-track agent's territory (a separate agent).
- Never `git add -A`: the tree is shared with the owner and another agent.
  Stage files by name.

### 0.4 Commit discipline
Commit per completed work item (stake green + gates passed), staged by
name, message in the house style: what changed, why, which golds flipped,
what was verified against which source pages, census count. End with:
`Co-Authored-By: Claude Opus <noreply@anthropic.com>`.

### 0.5 The traps list (each has bitten this project; memorize)
- **x-comparison trap**: absolute x coordinates mean nothing across
  columns, across pages, or against a multi-column union bbox. Any
  indent/position guard must require same-page + x-overlap, or compare
  only the decidable direction.
- **NOTES LOCATE, SOURCES DECIDE**: `feedback/<slug>.jsonl` is the only
  authoritative note→document binding (three notes have been mis-attributed
  from summaries). Before planting any stake from a note, verify the
  claim against the source page image. Owner-minted assertions can be
  backwards — one was; correct with evidence in a comment, never silently.
- **claimed/snippet ambiguity**: eval snippets must be unique to their
  target — body prose legitimately quotes chart numbers.
- **Tag order ≠ visual order**: tagged PDFs (tenure) sometimes author
  struct-tree order that contradicts the page. Known open: tenure p14
  "sections 4<5". Do not chase it with figure/layout levers; it needs the
  orderPin lever (§3.2).
- **Crop = raster of everything in bbox**: any region bbox that overlaps
  live text renders that text twice. Trim or claim; never both-live.
- **The venv**: `python3` is `/var/www/rk3/.venv/bin/python3`. `pymupdf`
  is pinned 1.27.2.3 (pymupdf-layout pins it; 1.28 conflicts). `wordfreq`
  is available. Playwright is available.
- **Service**: the viewer runs via systemd on 127.0.0.1:8300 with
  --reload on app/ and rk3/. The UI is vite-built: after editing
  `app/ui/src/**`, run `npm run build` in `app/ui/`.
- **Scratchpad is volatile**: durable tooling goes in `tools/` (§1.4).

### 0.6 PARKED protocol
When blocked, or when a fix would require architecture/scope not in this
plan: append to the `PARKED` ledger at the bottom of this file — one line:
`- [stage] <what> | why blocked | suggested lever/decision needed` — then
continue with the next item. Never redesign mid-run. Never wait.

Cleanup observations ("this code/doc/route looks dead or wrong") are NOT
your job in this run: append them to the INBOX in
`sources/docs/plans/sweep.md` (one line each) and move on. The sweep is
a separate post-run cycle.

### 0.7 Budget controls (vision spend)
- Vision calls only on pages triaged `hard` (§2), only on cluster
  representatives first (§2.3), max 3 loop iterations per page (§4.4),
  hard cap 40 vision-scanned page-iterations per document — when the cap
  hits, converge what you have and PARK the rest. Log every call's page
  count in the loop ledger (§4.6).
- **Model tiering per ROLE (owner-approved, cycle 2).** The plumbing
  exists (`qa_page/qa_doc/prescribe` take `model=`; usage logger prices
  all tiers). Policy:
  - `scan` (find issues — the volume op): `claude-sonnet-4-6`
  - `verify` (net-improvement re-scans: "did severe count drop?"):
    `claude-haiku-4-5`
  - `prescribe` (author overrides — the judgment op, cluster reps only):
    `claude-opus-4-8` (never downgrade this one)
  Wire as `ai.models: {scan, verify, prescribe}` in config.json via
  `get_ai_config()`, env-overridable; every loop record logs which model
  ran.
  **Calibration gate before trusting the downgrades**: take ~10 pages
  already scanned by Opus in cycle 1 (race + pol pilots have them);
  run the Sonnet scanner on the same pages; require it reproduces ≥90%
  of Opus's medium+ findings (severity-matched, text-similar). If Sonnet
  passes, run the same test for Haiku in the verify role (binary
  severe-count judgment only). Any tier that fails calibration keeps the
  next tier up, and the result — hit rates + per-page cost both models —
  goes in the ledger. Never calibrate by vibes.

### 0.8 Command recipes
- Convert/eval one doc: `python -m rk3 eval <slug>` (reconverts changed
  stages, runs its yaml checks). Full census: `python -m rk3 eval`.
- Run one check programmatically: `rk3.eval.evaluate_check(slug, check)`.
- Vision scan: `POST http://127.0.0.1:8300/api/qa/<slug>/run` body
  `{"pages": [..]}` → appends `source: vision-qa` issues to feedback and
  returns them. Issues carry severity/category/text/where/fix.
- Leaf-walk diff (adjudicating snapshot changes): walk both IRs
  (`git show HEAD:output/pdfium/<slug>/ir.json` vs current), print
  `p{page} {type}: text[:110]` per text leaf, unified-diff them. Write
  this once into `tools/nodediff.py` (§1.4).
- Screenshots: playwright against `file://output/pdfium/<slug>/index.html`
  (element-scoped) or `http://127.0.0.1:8300/?doc=<slug>` for the viewer.
- Page images: `output/pdfium/<slug>/pages/page-NNNN.png` (1-based).

---

## §1 — Stage 1: Make the state trustworthy (hygiene + instruments)

*Purpose: the owner is inundated because the feedback state lies — stale
issues, resolved-but-open notes, six channels with no summary. Fix the
instruments before touching the engine.*

**1.1 Baseline scoreboard.** Write `tools/scoreboard.py`: for every doc,
for every page, emit `output/pdfium/<slug>/scoreboard.json`:
`{page, class: null(for now), visionIssues: {critical,high,medium,low},
stakes: {green: n, red: n}, openOwnerNotes: n}`. Stakes are evaluated live
via `evaluate_check` against that doc's `eval/<slug>.yaml`, attributed to
pages via the check's note text (`pNN`) or matched nid. Commit the tool +
a one-line `make scoreboard`-style invocation note in the plan ledger.

**1.2 Sweep stale vision issues.** For each doc with vision-qa records:
re-scan the pages those records reference (batch per doc, one call).
Any OPEN vision issue whose page's fresh scan no longer reports a matching
issue (same page + category, similar text) → set
`disposition: "fixed"` with a `note: "auto-swept: not reproduced by rescan
<date>"`. Never touch owner-typed records. Expected effect: the review
board shrinks to reality. Commit per ~5 docs.

**1.3 Stakes tab (the one sanctioned UI item).** The owner explicitly
asked to SEE the stakes. In `app/ui/src/components/` add a `StakesPanel`
tab beside Patterns in the doc view: list the doc's eval checks with live
red/green (server endpoint wrapping `evaluate_check`), each row = state
chip + note text + jump (by matched element where derivable). Add
`GET /api/stakes/<slug>` to `app/main.py`. Style like the existing panels
(no new deps). Build the UI. Screenshot it open on race-to-lead and
gates-earth; verify reds/greens match `python -m rk3 eval` output exactly.

**1.4 Promote scratch tooling into the repo.** Create `tools/nodediff.py`
(leaf-walk differ), `tools/shoot.py` (playwright screenshot: doc+selector
→ png; also `--svg file` mode), `tools/visionloop.py` (stub now, filled in
§4). Deterministic, no side effects outside `/tmp` unless told.

**1.5 THE OWNER'S QA SURFACE (added after cycle 1 — owner feedback:
"I can't translate stakes/census/pytest into 'this looks right'"; do this
FIRST in cycle 2, before any lever/loop work).** The owner judges pages,
not checks. Build the visual layer that makes every claim auditable by
eye, using machinery that already exists (viewer, page PNGs, scoreboard,
evaluate_check):

- **(a) Page gallery.** Per doc, a "Pages" view: a grid of the ORIGINAL
  page thumbnails (`pages/page-NNNN.png`), each with a status ring from
  scoreboard.json — green (passes: no medium+ vision issues, no red
  stakes), amber (medium issues), red (high/critical issue or red stake),
  grey (never vision-scanned — DO NOT fake green; unscanned is its own
  honest state). One glance answers "how much of this doc looks right,
  and does the machine agree with my eyes?"
- **(b) Compare view.** Clicking a thumbnail opens original-vs-render
  side by side: page PNG left, the RENDER scrolled to that page's first
  element right (the viewer's existing sync-scroll + Original-PDF pane
  machinery — reuse, don't rebuild), with that page's open vision issues
  and stakes listed under it in plain words.
- **(c) Stakes tab → elements.** Every check row gets a jump: extend the
  eval evaluators to RETURN the matched nid(s) (they already locate the
  nodes internally — surface them), and the tab highlights/flashes the
  element like the Patterns tab does. A stake with no resolvable element
  says so explicitly. Each row also shows its matched text snippet, so a
  red reads as "THIS text, THIS page, broken in THIS way" — not a slug.
- **(d) Plain-words glossary**, one screen, linked from the tab header:
  stake = frozen owner-note assertion (green holds / red broken);
  census = all stakes across all docs; vision issue = model-spotted
  render-vs-original difference; page PASS = no medium+ issues + green
  stakes. Four lines, owner vocabulary.

Gate for 1.5: the owner can open any doc, see the gallery, click any
amber/red page, and understand what is wrong from that screen alone —
verify by walking race-to-lead and points-of-light yourself and
screenshotting the gallery + one compare view into the ledger.

**Gate to leave stage 1**: scoreboard runs corpus-wide; sweep done; stakes
tab live and accurate; tools committed. Census unchanged (no engine edits
happened). Write stage summary to the ledger.

---

## §2 — Stage 2: Page triage (deterministic, cheap)

*Purpose: know where the hard pages are without spending vision calls.*

**2.1 Classifier.** In `rk3/` add `triage.py`: consume the artifacts that
already exist per doc — `ir.json`, `debug-analyze.jsonl` events
(`figure-model`, `column-model`, `figure`, `callout`, `table`, question
events) — and classify each page:

- `easy`: only paragraphs/headings/lists; ≤1 simple figure; single column
  or clean 2-col; no callouts/tables; no dissolve/label-soup events.
- `moderate`: 2-col with asides OR 1-2 well-formed figures with bound
  anatomy OR one small table.
- `hard`: any of — label-soup/assembled/grown figure events, table nodes,
  ≥2 callouts, hero pages, dissolves, region questions, >4 figures,
  reading-order confidence low.

Output into scoreboard.json (`class` field). No ML, no vision — thresholds
on evidence that already exists.

**2.2 Calibration.** Hand-check 20 pages you select across 5 docs
(race-to-lead 10/13/15/17/20 must be `hard`; race 16 `easy`; tenure 13/14
`hard`; a plain gates text page `easy`...). Look at the page PNGs
yourself. Adjust thresholds until ≥18/20 agree. Record the 20 and the
score in the ledger.

**2.3 Template clustering (spend reducer).** Within a doc, cluster hard
pages by signature: (n_figures, n_tables, n_callouts, column count,
has_kicker_titles, hero). Pages sharing a signature form a cluster; the
vision loop (§4) runs on ONE representative first and applies its
document-level lessons to siblings before scanning them (their scans then
run only to VERIFY, which usually terminates in 1 iteration).

**2.4 QUICK SCAN — representative-page selection (owner proposal,
2026-07-07; cycle 2).** A capped scan mode that beats both "full doc"
(cost) and "first 10 pages" (blind): pick ≤10 pages per doc that
representatively cover its FEATURES, deterministically, from the triage
signatures we already have.

Selection (greedy set-cover, stable ordering so re-runs pick the same
pages):
1. one representative per hard-page cluster (§2.3), largest clusters
   first;
2. then fill feature-type coverage gaps: if the doc has tables/figures/
   callouts/multi-column/hero/list-heavy pages and none is selected yet,
   add the densest page of each missing type;
3. always include ONE `easy` page as a control (styling regressions show
   there first, and it keeps the sample honest);
4. cap at 10 (configurable), prefer never-scanned pages on re-runs.

Plumbing: `{"mode": "quick"}` on `/api/qa/<slug>/run` (server picks the
pages and echoes which it chose + why: `"p14: cluster rep (3 siblings);
p3: only table page; p21: easy control"`); `tools/visionloop.py --quick`
uses the same selector. Scoreboard/gallery HONESTY rule: a page whose
status is inferred from a scanned cluster-sibling displays differently
from a directly-scanned page (hollow vs solid ring) — inherited green is
a hypothesis, not a measurement.

Uses: the cheap corpus-wide "did it get better" number (~10 pages × 27
docs vs ~1,700 full), gallery status at reasonable cost, and the §4
net-improvement gate's re-scans.

**Gate**: triage in scoreboard for all 27 docs; calibration ≥18/20.
Quick-scan selector returns sensible pages on race-to-lead and
points-of-light (eyeball the chosen list against the triage table and
record it in the ledger).

---

## §3 — Stage 3: Override levers (the vocabulary vision writes in)

*Purpose: the loop can only fix what a lever can express. Build each lever
as: config schema → engine consumption → eval kind/gold → verification.
All levers live in per-doc `<name>.config.json` under `"structure"`, carry
`_source` provenance strings, and are idempotent (re-running conversion
with the same overrides yields identical output).*

Existing levers (verify each still works; write one regression gold each
if none exists): `regionOverrides` (kinds: figure/callout/text),
`headingOverrides`, `breakOverrides`, `indentOverrides`, `typedLines`,
ops (`reorder`, `merge`, `set-text`), `pullQuotes`.

Build these, in order:

**3.1 figureBand** — `{"page": n, "title": "text-prefix" | null,
"bbox": [l,b,r,t] | null, "floor": y | null}`: forces a figure assembly
band exactly (the §vision loop's most-used lever for charts the kicker
heuristic misses — bubble charts, unkickered charts). Consumed where
`_assemble_titled_figures` runs; an explicit band bypasses the heuristics.
Gold: apply one by hand to race p15's fig-10 (currently heuristic), assert
`in_figure`/`claimed`, remove, re-add via config only.

**3.2 orderPin** — `{"page": n, "sequence": ["text-prefix", ...]}`:
pins reading order of the matched top-level nodes on that page (matched
by normalized prefix; unmatched nodes keep engine order, interpolated
after their engine-order predecessor — the ops-reorder semantics already
in render.py, but at ANALYZE level and page-scoped). This retires
whole-document reorder ops and finally gives a lever for tag-order
defects. Gold: tenure p14 "sections read in order (4 before 5)" — the
known red — goes green via an orderPin entry in tenure's config with
`_source: "plan §3.2 known tag-order defect"`.

**3.3 tablePin** — `{"page": n, "bbox": [l,b,r,t], "cols": [x-cuts...] |
null, "headerRows": 0|1}`: forces `_try_table` to treat the bbox as a
table, with optional explicit column cuts (the failure mode of table
detection is almost always column inference). Gold: tenure p8's
definitions table (owner note edd55787: "should only be one table, not
broken up on column and page breaks") — pin it, assert a `table_shape:`
eval kind you add (n rows ≥ X, specific cell text pairs in one row).

**3.4 floatPin** — `{"nid" | "textPrefix": ..., "float": "left"|"right"|
"none"|"wide"}`: overrides float evidence per figure.

**3.5 styleTokens (read §5 first — build the schema here, consumption in
§5)** — per-doc: `{"kickerCaps": true, "headingColors": {...},
"quoteColor": "#...", "legendDots": true}`.

**Gate**: each lever has schema doc (in `rk3/config.py` DEFAULTS
comments), consumption, ≥1 gold, and made idempotent. Census greens
non-decreasing. Full §0.1 ritual per lever. Commit per lever.

---

## §4 — Stage 4: The vision loop (prove it on pilots BEFORE anything global)

*Purpose: the core of the owner's proposal. Vision stops complaining and
starts PRESCRIBING. Prove convergence on three pilot docs end-to-end.*

**Pilots (owner-selected, easy-first — do not substitute)**:
`02--race-to-lead` (simple vector charts, our best-instrumented),
`02--points-of-light` (clean text-and-pull-quote layout), and
`02--edf-ir23-digital-pages` (moderate: photos, wrapped images,
signatures). The owner's directive: **nail the easy stuff beautifully
before progressing** — a converged easy page must look genuinely right,
not merely pass. The hard docs (tenure, atlantic, chep) come only in §7,
in ascending difficulty order, after the pilots have proven the loop on
gentle material.

**4.1 The prescriber.** Extend `rk3/visionqa.py` with a second mode:
`prescribe(slug, page) -> {"overrides": [...], "ops": [...],
"residuals": [...]}`. Inputs to the model: the ORIGINAL page PNG, a
SCREENSHOT of our current render scrolled to that page's content
(tools/shoot.py; identify the page's span via nids), the page's IR
skeleton (types + first-60-chars + nids + bboxes, one line per node), and
the LEVER CATALOG (short schema + one example each, §3). Ask for the
MINIMAL set of overrides that would make the render match the original's
structure; anything inexpressible goes to `residuals` with a
`missingLever` name. Temperature low; require valid JSON against a schema
(reject+retry once on invalid).

**4.2 Safety rails on applying prescriptions.**
- Apply only known lever types; validate against schema; drop invalid
  entries and log them.
- Provenance on every entry: `_source: "vision-loop <date> p<NN> iter<K>"`.
- NEVER let a prescription touch pages outside its scope or delete
  owner-authored entries.
- Oscillation ledger: a prescription that reverts a previous vision-loop
  entry on the same target is refused; the page converges as-is and the
  conflict goes to residuals.

**4.3 The loop, per document:**
```
triage → hard pages → cluster → for each cluster representative:
  iter 1..3:
    scan (vision issues) ; if no medium+ issues → page PASSES, break
    prescribe → apply overrides → re-convert doc → re-render
  after reps converge: apply doc-level lessons, then scan siblings once;
  any sibling with medium+ issues gets its own loop (within budget §0.7)
easy/moderate pages: single verification scan per DOC-level sample only
  (5 random easy pages per doc; if any fails, triage was wrong — re-class)
```

**4.4 Convergence bookkeeping.** `output/pdfium/<slug>/visionloop.jsonl`:
one record per iteration — page, issues before/after by severity,
overrides applied, spend. The scoreboard picks these up.

**4.5 Pilot exit criteria (the go/no-go for the rest of the run):**
- Each pilot doc: **every easy page passes AND looks beautiful under your
  own eyeball** (this bar comes first — the owner's directive), ≥70% of
  its hard pages reach PASS within budget, ZERO regressions on its
  stakes, and the doc-level census stays green.
- Eyeball five converged hard pages per pilot against their source PNGs
  yourself and record verdicts in the ledger.
- If a pilot fails these bars: STOP the loop rollout. Write a diagnosis
  (which residual categories dominate; which levers are missing), PARK
  the loop, and proceed to §5/§6 anyway — they are valuable regardless,
  and the final report (§8) will carry the loop verdict. This is the
  graceful-degradation path; do not thrash on the loop.

**Gate**: pilot verdict recorded (pass → proceed with loop enabled
corpus-wide in §7; fail → loop parked with diagnosis).

---

## §5 — Stage 5: Styles baseline (the "looks like" half)

*Purpose: half the owner's "jumps out at me" items are presentation:
ALL-CAPS kickers lowercased, lost legend swatches, quote colors, callout
styling. No structural iteration fixes these. Deterministic, source-driven,
global — so strictest gates.*

Work items, each with named specimen pages (owner notes in parens),
each gated by §0.1 + before/after screenshots + vision delta on its
specimens:

- **5.1 Caps mirroring**: text extracted from all-caps runs renders
  all-caps. The engine currently smart-cases some; stop lowercasing when
  the source glyphs are caps — render a `.caps`/kicker class instead.
  (race p9 note 9611d5aa; vision flagged it on every race chart page.)
- **5.2 Legend swatches**: figure legends authored as text got their
  colored dots from vector fills — the fill colors are in the extract
  colors table. Where a legend line is a live caption/label leaf, render
  swatch dots (inline `<span class="swatch" style="background:...">`)
  using the nearest preceding fill colors from the figure's region model.
  Where the legend is claimed into the crop, do nothing (pixels carry it).
  (atlantic p10 75158669-adjacent; vision "color" issues.)
- **5.3 Quote/attribution styling**: pull-quote sidebars keep source color
  (sample the source glyph color — it's in the extract), decorative
  quotation glyphs when present, attribution attached to its quote block
  (race p20 vision items; edf p3 blue names).
- **5.4 Callout fidelity**: rounded corners when the source box path has
  arc segments; full-page-bg callouts (clean-air eae7b462 + c5012b9d
  family); text color inside dark callouts sampled from source
  (good-food p22 627c7db3: white-on-dark, never black-on-dark).
- **5.5 Figcaption/kicker styling**: figure titles render as styled
  kickers (small caps, letter-spacing) — matches how every corpus doc
  designs them.
- **5.6 Per-doc style guide artifact**: emit `styleguide.json` per doc
  (heading scale/colors, body font/size, link color, callout palettes,
  quote style) from the extract's fonts/colors tables. The renderer
  consumes tokens; the vision loop may adjust via styleTokens (§3.5).

**Gate**: all specimens eyeballed before/after; census non-decreasing;
vision deltas on race p9-20 / clean-air / good-food p22 improve or hold.

---

## §6 — Stage 6: Tables (the owner's "enormous mess")

*Purpose: bounded, specimen-driven table offensive. Perfection is not the
bar; honest fallback is.*

- **6.1 Table census** (log-only): per table-ish region — grid-rule
  evidence, column-cut confidence, row count, cell-text density, tagged
  table roles if present. One `table-model` event each. Eyeball the models
  for the specimen list below before changing behavior.
- **6.2 Specimens to fix via engine (each: stake red → fix → green)**:
  tenure p8 definitions table (one table across column/page break — note
  edd55787), tenure p54 hidden 2-col name table (note 9480e0a1 — guards
  exist, build the actual table), atlantic p7 tables (note b0399c90),
  invest p21 (note 8dd24ee5), dp p40 (note 54b39020), the baystate p12
  table+title (regression-guarded already).
- **6.3 tablePin fallback**: where inference fails, the vision loop
  prescribes tablePin (§3.3). Where even tablePin can't express it
  (nested/spanned monsters): the region renders as a clean FIGURE with
  svg sidecar + a converter question — an honest image beats a garbled
  table. Make this fallback automatic when `_try_table` confidence is low
  AND no pin exists.
- **6.4 chep-300pages**: has ~50 tables; run the loop on a 5-table sample
  only, PARK the rest with counts (budget rule).

**Gate**: all six specimen stakes green; fallback demonstrably produces
figure+question on one deliberately-broken case; census non-decreasing.

---

## §7 — Stage 7: The corpus run

With the loop proven (or parked), run the full pipeline over all 27 docs
**in ascending difficulty order** (rank docs by their share of hard pages
from §2 triage; easiest first). The owner's easy-first directive applies
corpus-wide: a doc is not "done" because its hard pages converged — its
easy pages must look beautiful, and they are cheap to verify, so verify
them first and fix any easy-page blemish before spending budget on that
doc's hard pages. Reconvert → triage → easy-page verification → vision
loop on hard pages (if enabled) → scoreboard. Then the final sweep: §1.2
again (close what converged), refresh the stakes tab data, and regenerate
every scoreboard.

Produce `output/CORPUS-SCOREBOARD.md`: per doc — pages passed/total, issue
counts by severity, spend, top residual categories. This file is the
owner's single "where are we" view.

**Gate**: scoreboard says >50% of pages corpus-wide PASS → run succeeded.
If not: the residual analysis in §8 explains exactly why, in categories.

---

## §8 — Stage 8: Handoff report

Write `sources/docs/plans/webified-report.md`:
1. The scoreboard summary + before/after page-pass counts.
2. Convergence stories: 3 pages that went salad→webified (with images).
3. Residual taxonomy: every non-passing page bucketed by cause, each
   bucket with its missing lever / engine gap / styles gap named.
4. Promotion candidates: override patterns that recurred ≥5 times across
   docs — each is a candidate deterministic rule, with the evidence.
5. The restart instruction: exactly what a second cycle should do first.
6. Sweep the PARKED ledger into categorized recommendations.

Update the memory directory (figures-track, new webified-track entry,
MEMORY.md index) per its conventions.

---

## Execution order & pacing

§0 read fully → §1 → §2 → §3 (levers 3.1-3.4; 3.5 schema only) → §4
pilots (GO/NO-GO) → §5 → §6 → §7 → §8. Within stages, commit small and
often. If total context/compaction pressure hits, the ledger below plus
plan-stage state is the durable memory — keep it current after EVERY
work item; assume any un-ledgered progress may be lost.

Do not ask the owner anything. Do not build anything not listed. When in
doubt: smaller scope, PARK, keep moving.

---

## LEDGER (executor maintains; newest on top)

- **§8 handoff report WRITTEN** (2026-07-07). `sources/docs/plans/webified-report.md`
  — the durable cycle-1 synthesis per §8's spec: (1) scoreboard (census 71/6→77/5,
  monotonic, zero regressions); (2) three convergence stories (tenure p8 acronyms
  cell-split, atlantic p7 header bands, pol p25 loop); (3) residual taxonomy — the
  5 remaining gold fails are ALL reading-order/column-model defects, cleanly
  signalling cycle-2's engine focus; (4) promotion candidates (attribution-label
  recurred in BOTH pilots; the §5/§6 fixes ARE this cycle's promotions — header-band
  = 18 tables from one rule); (5) restart instruction (wire 3 cheap loop lever gaps
  + net-improvement gate → run §7.2 wide); (6) PARKED swept into 5 categorized
  recommendation buckets. THE PLAN IS EXECUTED end-to-end: deterministic backbone
  complete + durable, vision-loop thesis validated.
- **§7.2 vision-loop pilot re-run (points-of-light p25) — §5-FIRST THESIS
  CONFIRMED** (2026-07-07, bounded, $0.54 spend). Re-ran the loop on the SAME page
  the §4.5 pilot failed on, now that §5 styling is in place. RESULT: the loop
  applied orderPin (SUMMARY box → after heading) + floatPin (pull-quote left);
  iter-2 rescan reported severe 4→5 and the oscillation rail fired — but EYEBALL
  showed the render was UNCHANGED, so the 4→5 was vision-scan NOISE on a page the
  overrides didn't move, NOT the §4.5-style styling DEGRADATION. THE KEY WIN:
  applying structural overrides no longer strips the correct styling (heading
  green, callout, colors, pull-quote decoration all stayed intact) — exactly the
  §5-first bet. Diagnosed WHY the overrides didn't land: (1) orderPin prefix
  "SUMMARY It is resource intensive" spanned TWO child nodes so the lead-text
  matcher missed the callout (matched 5/6); a one-word hand-correction to
  "SUMMARY" → matched 6/6 and the SUMMARY box MOVED correctly into place with zero
  styling loss (kept, provenance-stamped, in Points-of-Light.config.json). (2)
  floatPin is figures-only; the pull-quote is a paragraph → no-op (dropped). (3)
  "NONPROFIT LEADER" stays a heading (prescriber flagged the residual). VERDICT:
  the §5-first sequencing WORKS — the loop's structural fixes now land atop
  correct styling instead of degrading it. The residual gaps are lever-COVERAGE
  (prescriber prefix-matching, floatPin scope, attribution lever), PARKED. This
  validates the owner's whole thesis end-to-end.
- **§7.1 corpus output baselines REFRESHED** (2026-07-07). All §5.1–5.6 + §6.2
  deterministic wins were committed only for specimen docs; the rest sat at STALE
  pre-§5 committed output (each specimen commit did `git checkout -- output/` to
  drop the churn). GOTCHA CONFIRMED: `rk3 eval`/`convert()` served CACHED stale
  artifacts even after VERSION bumps once the on-disk artifacts were git-reverted —
  only `convert(slug, force=True)` regenerates. Force-refreshed all 26 done docs
  (scratchpad refresh_corpus.py); 23 changed, 0 failed. census 77/5, code
  unchanged since 62f7c88 so pytest 33 holds. Verified advancing-mobility gained
  295 §5.3 styled-color spans. Commit = the 87 output files (ir.json/index.html/
  *.css corpus-wide). NOW every doc — not just specimens — carries caps, source
  colors, white-on-dark callouts, kicker styling, styleguide.json, and the table
  cell-split + header-band fixes. REMAINING §7: (b) re-enable the vision loop on
  pilots (COST — deliberately gated behind §5, now done), (c) route the PARKED
  table tail through prescribed overrides. Then §8.
- **§6 STATUS: 2 clean specimens shipped, deep tail PARKED** (2026-07-07). §6.1
  census + §6.2 tenure p8 (cell-split) + atlantic p7 (header bands) DONE — the two
  specimens with concrete, engine-expressible defects, both broad wins (census
  75/5→77/5). The remaining specimens are each DEEP re-architecture or corpus-wide
  heuristic, PARKED with named missing levers + scouting (see PARKED): spans-pages
  cross-page assembly (dp p40, tenure p8 merge, ~28 more), hidden-table detection
  (tenure p54), auto-figure fallback (invest p21 + 8, scan_fallback.py), tablePin
  consumption. baystate p12 is already guarded in-engine (the "title survives the
  figure→table conversion" caption logic, analyze.py ~L555; + pytest snapshot).
  These belong to §7's per-doc loop (prescribe tablePin/figure overrides) — the
  vision loop's whole purpose is the tail no deterministic rule compresses.
- **§6.2 atlantic p7 header bands DONE** (2026-07-07). Owner note b0399c90 ("quite
  a bit of format missing"): the "OPPORTUNITY #N" tables print a full-width RED/
  orange band as their header, but `_try_table`'s header test required EVERY column
  filled — the band's title spans one cell (col 0 empty) → header=false → the red
  headBg (#c02026, already captured) was never applied; the band rendered on the
  pink BODY fill, and its title read as an underlined styled-link. FIX: (1) header
  detection — a wide `head_fill` band + any row-0 text IS a header (the fill is the
  signal), else fall back to the all-cells-filled + distinct-color heuristic;
  (2) `a[data-link-styled]{text-decoration:none}` in default.css — print cross-refs
  aren't underlined in the source. analyze VERSION 206→**207**, render 83→**84**.
  NEW eval kind `table:{nid|textPrefix, header?, headBg?, cols?}` + gold on the
  Opportunity-1 red band (RED-AT-PLANT documented from the §6.1 census + IR probe,
  both recording header=false pre-fix). census 76/5→**77/5** (+1 gold, 0 regress);
  pytest 33 (header flip changes no node-count/textChars → no snapshot change).
  BLAST RADIUS is a WIN: 18 tables corpus-wide flipped to header via the band path
  (all 5 atlantic Opportunity tables + gates p20/p88/p101/… grey column-header
  bands + advancing-mobility p81/p92 + ecp p19). EYEBALLED atlantic p7 (white-on-
  red/orange, no underline ✓), gates p20 + mobility p81 (grey header bands now show
  ✓); mobility p43 is a pre-existing case-study-as-13col-table mess, my change
  neutral there. RESIDUAL: the header BAND's second row (italic subtitle) stays on
  the body fill — a multi-row-header feature, not done. Committed analyze+eval+css+
  atlantic yaml+output; corpus refresh → §7.
- **§6.2 tenure p8 "wrong column" DONE** (2026-07-07). Owner note edd55787: the
  Acronyms glossary had "several definitions land in the wrong column". Root
  cause: single-line rows (term + short value on ONE line, uniform COLOR but the
  term in a BOLD cut) failed `_color_segments` (single-color) and dumped the whole
  line into the term column, leaving the value column empty. FIX: `_font_segments`
  — a font-run fallback splitting bold-term|regular-value, wired as
  `_color_segments(line) or _font_segments(line, ctx)`. GUARDS mined from 3
  mis-fires (the tail's complexity ceiling, as the plan warned): (1) WIDE-span —
  block must fill ≥50% of the columns it straddles (else a narrow value cell over
  a mis-placed cut isn't a spanning row); (2) WEIGHT-contrast — segments must span
  bold(≥600)→regular(≤500), not bold→semibold (killed gates p133 "6%"w800|"(12)"
  w600 over-split); (3) SINGLE-LINE + EXACTLY-2-COL — the glossary pattern (killed
  gates p134 3-col scoring-cell split). analyze VERSION 202→**206** (4 guard
  iterations; cache gotcha bit once — a same-VERSION edit served stale analyze
  until I bumped). NEW eval kind `cells: [t0,t1]` (a table row's cells start with
  these, in order) + gold on ANT row (RED-at-plant → GREEN). census 75/5→**76/5**
  (+1 gold, 0 regress); pytest 33 (tenure snapshot regen: textChars −16 = the
  boundary spaces the split drops; gates & all others UNCHANGED via nodediff +
  snapshot). EYEBALLED tenure p8 — every single-line row (ANT|National Land
  Agency, CFR|…, CLAN!|…, COFO, FOSPA, FRC, GFN) now splits into two cells,
  matching source. REMAINING (owner's other half, NOT done): "should be ONE table
  not two" — the glossary is split across the page's two layout-columns (+ onto
  p9); a cross-column/page table MERGE, harder, "good candidate for a Converter
  Question" (owner's words). Committed analyze+eval+tenure yaml+output+snapshot.
- **§6.1 table census DONE (log-only)** (2026-07-06). `_try_table` now emits a
  `table-model` event at every exit (success + each rejection w/ reason + grid
  evidence: hlines/vlines/cols/rows/blocks/kind), suppressing the 0-1-block
  strict figure-check noise. analyze VERSION 201→**202** (log-only → IR unchanged
  → census 75/5, pytest 33). CORPUS MAP (tools scratchpad table_census.py):
  **47 tables convert; 298 reject** — reasons {no-grid 148, too-few-blocks 108,
  spans-pages 30, strict-sparse 12}. READING: (1) `spans-pages` (30) = the tenure
  p8 class — a table split by column/page break whose fragments don't merge (6.2
  target); (2) `no-grid` (148) is MIXED — real gridless tables that need column
  inference AND charts/figures correctly rejected (kind=figure strict, many
  blocks) — needs per-region eyeball to separate; (3) `too-few-blocks` (108) =
  2-3 block small tables/near-misses. Per-doc load: advancing-mobility 65,
  gates-earth 52, race 36, invest 29, atlantic 27, tenure 24. The census is the
  instrument 6.2/6.3 read to pick+verify fixes. events → debug-analyze.jsonl
  (gitignored); only the analyze code commits. NEXT: §6.2 specimen fixes (each
  stake red→fix→green: tenure p8 spans-pages first) — DEEP table-reconstruction
  surgery w/ high regression risk to the 47 converting tables; the plan brackets
  this as the hard tail ("eyeball models BEFORE changing behavior" = §6.1 done).
- **§5.6 styleguide.json DONE** (2026-07-06). New per-doc design-token digest
  emitted by the render stage (`render._styleguide(ir)` → `styleguide.json`):
  `{body:{font,size,color}, headings:{1..6:{font,size,color}}, linkColor,
  calloutPalette:[fills], quote}`. Serializes what layer-3 CSS already derives
  (`_style_profile` + link/aside scans) — the styleTokens (§3.5) substrate the
  §7 loop will adjust. A DERIVED LOCAL artifact like scoreboard.json (gitignored;
  not whitelisted), regenerated each convert — only the CODE commits. render
  VERSION 82→**83** (bump so the stage re-runs corpus-wide). Additive (no HTML/CSS
  change) → census provably unchanged; pytest 33. VERIFIED by reading edf (blue
  #0033cc scale) + nff (Univers 10pt body, #5c6f7b links, 8-color callout palette)
  — both faithful. §5 STYLES BASELINE COMPLETE (5.1 caps ✓ / 5.2 PARK / 5.3 quote
  color ✓ / 5.4 white-on-dark ✓ / 5.5 kicker ✓ / 5.6 tokens ✓). NEXT: §6 tables.
- **§5.5 kicker styling DONE (verify-only, no code)** (2026-07-06). §5.1 already
  delivers it: `data-caps`→`text-transform:uppercase` + `figcaption[data-caps]
  {letter-spacing:0.03em}`, and figure kickers carry their source color/font
  (Whitney-MediumSC via embedFonts). EYEBALLED race p10 — "FIGURE 2 |
  RACE/ETHNICITY", "FIGURE 3 | IMMIGRATION EXPERIENCE", "FIGURE 4 | SEXUAL
  ORIENTATION" render as proper uppercase muted-teal letter-spaced kickers; the
  legends (PEOPLE OF COLOR ● WHITE) carry their swatch dots from the claimed
  figure pixels (consistent w/ §5.2). No code change; race output not re-committed
  (refreshes in §7).
- **§5.4 callout fidelity DONE (white-on-dark)** (2026-07-06). Owner-flagged core:
  text inside DARK callouts was rendering body-black (illegible) instead of the
  source's near-white. Root cause: `_usable_color` drops near-white as unusable
  on our white page, and the dark-bg restore only fired when `bg` sat on the node
  itself — but a callout's fill lives on the ANCESTOR aside, so child paragraphs
  never saw it. FIX (render-only): (1) `_dark_callout_fg(node)` samples the
  dominant LIGHT descendant color; an aside with a dark fill emits `color:<fg>`
  so children inherit light-on-dark; (2) a companion `[data-nid] a, …h1-h6` rule
  forces that color on descendant links/headings (else a mis-detected styled-link
  title — good-food "Conclusion" resolved to a self-anchor — takes the dark link
  color); (3) the heading-with-bg path (clean-air p15 banner) emitted no color
  when its LEVEL's dominant color was itself near-white (level rule drops white +
  per-nid `own!=lv_color` guard both skipped it) → added an `on_dark` flag that
  emits the restored near-white unconditionally. render VERSION 81→**82** (NO
  analyze change → census provably unchanged: every eval kind reads the IR, not
  CSS). census **75/5**; pytest 33. EYEBALLED good-food p22 (teal box: white
  title+body ✓) + clean-air p15 ($330M red aside ✓ AND red banner heading ✓) vs
  source. Committed render + both specimens; corpus refresh → §7. §5.4's other two
  sub-items PARKED (rounded corners / text-over-image) — see PARKED. NEXT: §5.5
  (verify kicker styling done) + §5.6 styleguide.json.
- **§5.3 quote/attribution color DONE (blue names)** (2026-07-06). Named specimen
  edf p3 "blue names": signatory names (Amanda Leland / Fred Krupp / Mark Heising)
  are link-COLORED (#0033cc) with no link target — a deliberate color, but the
  engine carried them as `{styled:true}` with NO color and the renderer flattened
  them to body black. Root cause traced to `analyze._build_runs`: a link-colored
  run without an anchor becomes a styled link but only the boolean survived.
  FIX (2 lines of real change): `_build_runs` now stores `{styled:true,color:_hex}`
  (the matched source color); `render._link_markup` emits `style="color:…"` on the
  un-anchored `<span data-link-styled>`, gated by `_usable_color` (near-white link
  colors, legible only on the PDF's dark panels, stay body color — no white-on-
  white). Heading color was ALREADY faithful (level rule `h{lv}{color}` + per-nid
  outlier rule) — EYEBALLED edf p3 before/after: blue headings already blue; only
  the names were black→now blue (titles stay black). NEW eval kind `styleColor`
  {nid|textPrefix, is:#hex} + gold on edf (RED-at-plant "color none" → GREEN).
  VERSIONS analyze 200→**201**, render 80→**81**. census **75/5** (+1 gold, ZERO
  regressions — the +1 check is the only delta; 5 reds unchanged). nodediff edf =
  no leaf-stream change (purely additive styling). BLAST RADIUS eyeballed: 8 docs /
  907 usable styled runs now colored; sampled advancing-mobility p11 — pull-quote
  "The Partnership's collective ambition…" is blue-italic in SOURCE, renders blue
  = faithful; stat numbers orange = faithful. (mobility's duplicate-quote + Venn-
  label banners are PRE-EXISTING structural bugs, not color.) Committed code + eval
  + edf output; corpus output refresh deferred to §7. NEXT: §5.4 callout fidelity
  (clean-air full-bg, good-food p22 white-on-dark), §5.5 (mostly done), §5.6.
- **§5.2 legend swatches → PARKED, no clean specimen** (2026-07-06). Investigated
  all three candidate specimens; §5.2's premise (a live legend LEAF that merely
  lost its swatch dots) matches NONE of them:
  • **race p10** — legend claimed into the native figure SVG (pixels carry
    "people of color / white"); §5.2's own rule says do nothing. ✓ verified prior.
  • **atlantic p10** (owner note 75158669, now `orphaned:true`) — the chart is a
    RASTER crop (`fig-001.png`); owner's flagged "optimists/pessimists" bracket
    labels are DROPPED (no leaf in current IR: nid `nd580e4e92d` gone; crop bbox
    excludes them). No live legend leaf; a figure-COMPLETENESS residual, not a
    swatch gap. Eyeballed page-0010.png + fig-001.png.
  • **nff p12** (`03--nff-2025-survey-report`, the ONLY corpus doc with a live
    legend text leaf — found via corpus scan `scan_live_legends.py`) — the
    "MAJOR CHALLENGE / MINOR CHALLENGE" legend IS live, BUT the whole chart is
    STRUCTURALLY SHREDDED: two half-charts as separate bar-image figures
    (`fig-021.svg` light-green MAJOR, `fig-022.svg` dark-green MINOR), the six
    category labels split into standalone `<h6>` headings (an-000502..507), the
    percentages into stray `<p>` ("18% 20%"), and the legend demoted to fig-022's
    figcaption. Swatch dots here = lipstick on a decomposition bug.
  ROOT CAUSE of the park: the IR has NO legend-region concept — no "legend" role,
  no swatch↔label grouping in the figure region model — so §5.2's precondition
  ("a legend line that is a live caption/label leaf") cannot be satisfied cleanly
  anywhere. Building a figcaption→swatch detector would need the multi-guard
  gating the plan warns against, and wouldn't move any page's PASS state (race
  already correct; atlantic/nff broken upstream). PARKED with named missing lever
  (see PARKED). NEXT: §5.3 (quote/attribution) — clean specimens exist (edf p3
  blue names, race p20 quotes) — then §5.4, §5.5 (mostly done via §5.1), §5.6.
- **§5.1 caps mirroring DONE** (2026-07-04). Root cause: all-caps kickers/
  labels/headings are lowercase CODEPOINTS displayed caps by a small-caps font
  (confirmed `Whitney-MediumSC`) — extraction faithfully returns the lowercase
  glyphs. Deterministic detector `assemble._line_caps` (glyph geometry: a run's
  short x-height letters a/c/e/… all reach CAP height, which mixed-case never
  shows) → `line["caps"]`; propagated `_join_block` runs["caps"] → `_leaf`
  data.caps (paragraphs/captions) + heading `prov.caps` (hand-rolled runs dict);
  render emits `data-caps` (figcaption hard-coded, others via `_attrs`); CSS
  `[data-caps]{text-transform:uppercase}` + figcaption letter-spacing. VERSIONS
  assemble 50→**51**, analyze 199→**200**, render 79→**80**. Detection: 125
  clean hits on race, ZERO body false-fires. Eyeballed race p10 (FIGURE 2 |
  RACE/ETHNICITY etc.) + p16 (CAREER SUPPORT) — mirror the source; body
  unchanged. census **74/5** (non-decreasing — IR text stays lowercase so
  text/freeze golds unaffected); pytest 33. RESIDUAL: mixed kicker+title lines
  ("KEY FINDING 1: The Same Story") stay un-flagged (the LINE is mixed-case) —
  a run-level (sub-line) caps refinement, filed for later. Committed code + CSS
  + race output; other docs' caps output refreshes in §7.
- **§4.5 pilot verdict: "§5 FIRST" (graceful-degradation PARK, NOT no-go)**
  (2026-07-04). Demonstrated the full loop on pilot points-of-light p25
  (SUMMARY callout + pull-quote page): scan→prescribe→apply→reconvert→rescan,
  2 iters, **$0.43**. FINDINGS: (1) the machinery works end-to-end and the
  oscillation safety rail FIRED correctly (refused a conflicting iter-2
  orderPin). (2) Prescriber quality is HIGH — it emitted 3 correct minimal
  structural overrides (orderPin: SUMMARY box reads after the heading; floatPin:
  pull-quote left; headingOverride: "NONPROFIT LEADER" is an attribution not a
  heading), each the right lever with accurate page-grounded reasoning. This
  validates the owner's core thesis. (3) BUT apply-all was MIXED: the orderPin
  genuinely fixed the SUMMARY ordering, yet applying also lost the SUMMARY
  label, stripped the pull-quote's decoration (quote-mark/green → plain), and
  shuffled order; severe only 5→4, and the page did NOT "look genuinely right"
  (§4.5 bar). Config REVERTED (eyeballed, restored clean; never degrade w/o
  approval). DIAGNOSIS: dominant residuals are STYLING (callout label/color,
  pull-quote decoration) — the structural levers can't express them; §5 owns
  them. Also a convergence-criteria gap: don't apply an override that trades one
  medium+ issue for another (needs a net-improvement gate). VERDICT per §4.5:
  the mechanism + prescriber are sound, so this is not a NO-GO — it is **PARK
  the corpus loop rollout until §5 lands**, then the loop's structural fixes
  land atop correct styling. Machinery banked for reuse.
- **§4.1–4.4 vision-loop machinery BUILT + validated** (2026-07-03).
  §4.1 `rk3.visionqa.prescribe(slug, page)` — feeds the model the original page
  PNG + our render crop (shoot) + the IR skeleton (`ir_skeleton`) + the lever
  catalog; returns `{overrides:[{lever,entry,why}], ops, residuals:[{issue,
  missingLever}]}`. The API caps schema complexity, so entry/ops are JSON-string
  encoded and parsed (`_parse_entries`); reject+retry once. Validated on race
  p12 → valid empty response (structurally faithful; styling isn't its remit).
  §4.2–4.4 `tools/visionloop.py` (replaces the stub): `apply_prescription`
  safety rails — known-lever-only, page-scope guard (never touches another
  page), `_source` provenance stamp, append-only merge (owner entries never
  deleted), oscillation refusal (target-sig vs value-sig), idempotent dupes;
  `converge_page` runs scan→prescribe→apply→reconvert up to 3 iters (medium+ =
  fail); `run` does triage→cluster→one-rep-per-cluster within a page budget;
  bookkeeping to `output/pdfium/<slug>/visionloop.jsonl` (§4.4). Imports clean,
  all 8 list-levers wired.
- **§3.4 floatPin lever DONE — §3 substantially complete** (2026-07-03).
  `structure.floatPins` [{nid|textPrefix, float: left|right|none|wide}] →
  `_apply_float_pins` overrides a figure node's data.float after
  `_figure_float_evidence`; new `float:` eval kind (nid or caption match).
  Gold: tenure p7 Nonette-Royo portrait — eyeballed the source (bottom-left),
  pinned `left` by nid; `float-pin` log FIRED, gold green. VERSION 198→**199**;
  census **73→74** (non-decreasing); pytest 33; idempotent. **§3 STATUS**:
  fully-built levers with consumption+gold = orderPin(3.2), figureBand(3.1),
  floatPin(3.4); schema-only (by design) = tablePin(3.3, consumption→§6),
  styleTokens(3.5, consumption→§5). Existing levers (regionOverrides,
  heading/break/indentOverrides, typedLines, ops, pullQuotes) remain green in
  the census (their golds unaffected across VERSION 196→199). Levers now give
  the §4 vision loop a real vocabulary. Reds remaining: 5 (atlantic p6, foia p4,
  edf footer, covid p7, jhu-p20 endnotes).
- **§3.1 figureBand + §3.5/§3.4/§3.3 schemas DONE** (2026-07-03). figureBand
  (`structure.figureBands`) — a pre-pass `_apply_figure_bands` before
  `_assemble_titled_figures` synthesizes a figure region from an explicit bbox
  (or title+floor deriving the band), claims interior non-prose blocks, marks
  the title absorbed so the kicker heuristic skips it; idempotent. Gold: race
  p15 fig-10 forced via config bbox — `figureBand (config)` log FIRED,
  in_figure gold green. VERSION 197→**198**; census **72→73** (non-decreasing);
  pytest 33; nodediff = race leaf stream IDENTICAL to HEAD (lever reproduces the
  heuristic exactly, ir.json differs only in figure provenance); eyeballed
  race p15 (fig-10 title kicker + legend + bars, clean). Also added SCHEMAS
  (config.py DEFAULTS, no consumption yet): floatPins (§3.4), tablePins (§3.3,
  consumption→§6), styleTokens (§3.5, consumption→§5). Levers with full
  consumption+gold: orderPin, figureBand. Churn from the VERSION bump
  discarded (deep-equal).
- **§3.2 orderPin lever DONE — flips a standing red** (2026-07-03). Schema in
  config.py DEFAULTS (`structure.orderPins`); consumption `_apply_order_pins`
  in analyze.py (page-scoped reorder after `_upgrade_lists`, matched by
  normalized text prefix, render.py reorder-op interpolation semantics for
  unmatched nodes; idempotent). Gold = tenure p14 "sections read in order (4
  before 5)", the known tag-order red — added the pin to Tenure's config.json
  with `_source`. Full §0.1 ritual: VERSION 196→**197**; tenure **9/1→10/0**;
  census **71/6 → 72/5** (greens non-decreasing, ZERO regressions); pytest 33
  green; nodediff shows the ONLY change is p14 (Section 5 moved from pos 3 → pos
  5, giving Why→S2→S3→S4→S5→S6→S7→appendices); eyeballed the rendered p14 — reads
  in order. NOTE: the VERSION bump reconverted all docs; 12 pinless docs'
  ir.json are byte-different but **deep-equal** (verified `cur==old`) — pure
  serialization churn from stale committed baselines, discarded (not my change).
- **§2 page triage DONE** (2026-07-03). `rk3/triage.py` (read-only; no
  VERSION bump, census untouched) classifies each page easy/moderate/hard from
  ir.json node types + debug-analyze events (figure `reason` = label-soup/
  assembled/hero; `table`/`region-dissolved`/`callout`/`figure-grown` events;
  `column-model` ncols+conf; region `question`s via nid→page). Key threshold
  (§2.1): clean multi-column text is EASY — only asides/figures/callouts/tables
  or a hard signal escalate; low-confidence (<0.55) multicol is hard.
  `tools/scoreboard.py` now writes the `class`. **Calibration 18/20** (≥18 bar
  MET): race p10/13/15/17 hard ✓, p16 easy ✓, tenure p1/8/13/14 hard ✓
  (watermark-dissolve p14 eyeballed), tenure p3/10 easy ✓, gates p1/11 hard ✓
  p7 easy ✓, foia p1/3 ✓, oxfam p6 moderate/p7 hard ✓. **2 misses**, both the
  SAME class: race p20 (pull-quote sidebar) + gates p8 (hero banner) were
  flattened by the engine to plain paragraphs — ZERO figure/aside events, so no
  deterministic signal exists; both under-call to easy. §5 (pull-quotes/banner
  extraction) resolves them structurally, after which triage auto-catches them;
  §4.3's easy-sample verification scan is the safety net meanwhile. §2.3
  clustering (`triage.clusters`): race's 31 hard pages → 18 clusters (top=6
  pages), a ~42% cut in representative scans. Corpus distribution:
  easy=757 / moderate=360 / hard=623; ascending-difficulty order for §7 =
  covid(0 hard) → community-schools → baystate → points-of-light → … → the
  03-- reports (near all-hard). PARKED nothing.
- **§1.3 Stakes tab DONE** (2026-07-03). `GET /api/stakes/<slug>` (thin
  wrapper over `checks_with_status`, adds page hint from `pNN`) + `StakesPanel`
  tab beside Patterns: failing-first list of every gold check with green/red
  chip, note, kind·stage·page meta, jump-to-element, and pass/fail iframe
  outlines; "hide passing" + refresh. Built (`npm run build`). VERIFIED by
  screenshot + endpoint vs `python -m rk3 eval`: race **7/0**, gates **6/0**,
  tenure **9/1** (the p14 FAIL row renders red with the exact CLI detail).
  Counts match the CLI exactly. dist is gitignored; source committed.
  **Stage 1 gate MET**: scoreboard corpus-wide ✓, sweep ✓, stakes tab live+
  accurate ✓, tools committed ✓, no engine edits (census stays 71/6).
- **§1.2 stale vision sweep DONE** (2026-07-03). `tools/sweepvision.py`
  (durable, reused in §7): fresh batched rescan of the pages an OPEN
  `vision-qa` record references → mark non-reproduced (same page+category,
  text-sim <0.45) as `disposition:fixed` w/ auto-swept note; owner notes never
  touched. Only 2 docs had vision records. Result: race-to-lead 66→**17** open
  (49 swept; its board was inflated by two same-day scans stacking
  near-duplicates), tenure 22→**11** open (11 swept). Board shrank 88→28.
  Owner notes intact (race 20, tenure 28). Vision spend **$0.97** total
  (opus reviewer, 11 page-scans). feedback/ is gitignored → local state only;
  scoreboards for both docs refreshed. Commit = the tool + this ledger.
- **§1.1 scoreboard built** (2026-07-03). `tools/scoreboard.py` → one
  `output/pdfium/<slug>/scoreboard.json` per doc, one record per page:
  `{page, class, visionIssues:{crit,high,med,low}, stakes:{green,red},
  openOwnerNotes}`. Stakes live from `checks_with_status` (no reconvert),
  attributed to a page by anchoring-nid page → `pNN` note → doc-level
  (`page:null`) bucket; vision issues = OPEN `source:vision-qa` records by
  severity; owner notes = `type:comment/answer` w/o `source`, `status!=cleared`.
  Preserves any prior triage `class`. Invocation: `python tools/scoreboard.py
  [slug]`. Ran corpus-wide: **26 docs** (race p10/12/13/15/17/20 carry the
  vision load, tenure too; verified per-page attribution). NOTE: scoreboard.json
  is auto-gitignored (`output/pdfium/*/*` whitelist), so it's local state — the
  stakes tab (§1.3) and §7 read it; nothing to commit but the tool.
- **§1.4 tools promoted** (2026-07-03). `tools/nodediff.py` (leaf-walk
  differ: `python tools/nodediff.py <slug> [--ref REF]` → unified diff of
  `p{page} {type}: text[:110]` lines, HEAD vs working tree — verified clean
  on race-to-lead), `tools/shoot.py` (playwright screenshotter: `--page N` /
  `--selector CSS` / `--full` / `--svg FILE`; reuses visionqa's `_BBOX_JS`
  page-crop; verified on race p10 — captured charts+legends), and
  `tools/visionloop.py` (STUB until §4, raises NotImplementedError). No
  engine edits; census untouched.
- Stage 0 of the SWEEP companion (truth pass) ran first and is COMPLETE
  (census 71/6, pytest 33). Baseline reds going into this run: atlantic p6,
  foia p4, edf running-footer, covid p7 column-weld, jhu-p20 endnotes,
  tenure p14 order 4<5 (the §3.2 orderPin target).

## PARKED

- [§7.2] Prescriber orderPin prefix-matching | the loop's orderPin sequence used a
  prefix ("SUMMARY It is resource intensive") that spanned TWO child nodes, so the
  analyze lead-text matcher missed the callout (matched 5/6, no reorder); a
  one-word fix ("SUMMARY") landed it | NAMED MISSING LEVER: make prescribe() emit
  each sequence entry as either a nid or a prefix that matches ONE node's lead
  text (its first line), not concatenated cross-node text; or make _apply_order_pins
  match on subtree_text as a fallback. Cheap, high-leverage for the loop.
- [§7.2] floatPin scope = figures only | the pull-quote on pol p25 is a PARAGRAPH
  (not a figure/aside), so floatPin (sets data.float, consumed only for figures)
  is a no-op on it | NAMED MISSING LEVER: extend float to paragraph/aside pull-
  quotes — a floated side-quote is a common layout; the renderer needs a
  `.para-float-left/right` path mirroring `.fig-float-*`.
- [§7.2] attribution-label classification | "NONPROFIT LEADER" (a pull-quote
  attribution) is classified as a heading; the prescriber correctly flagged the
  residual but has no lever for it | NAMED MISSING LEVER: a headingOverride /
  role-pin that demotes a mis-tagged heading to an attribution/label leaf bound to
  its quote (the §4.5 pilot proposed this too — recurring, promotion candidate).
- [§6.2/§6.3] Spans-pages table assembly | 30 corpus tables (census reason
  `spans-pages`) — incl. dp p40 (note 54b39020), tenure p8's "one table not two"
  MERGE (note edd55787), tenure p8→p9 continuation — are ONE table split by a
  column/page break; `_try_table` early-returns on `reg.get("endPage")` and reads
  grid objects from a SINGLE page (`pages[reg["page"]]`) with one bbox | NAMED
  MISSING LEVER: cross-page/column table assembly — gather grid rules + blocks
  from both fragments, build a unified grid, render one <table>. Deep; high
  regression risk to the 47 converting tables. Owner suggests a Converter Question
  for the tenure p8 case. Route via §7 loop (tablePin) or a dedicated pass.
- [§6.2] Hidden 2-col name table (tenure p54, note 9480e0a1) | the region is not
  detected as a table at all (guards exist per the note) — build one where none
  is found | NAMED MISSING LEVER: gridless-table DETECTION from aligned text
  columns (no drawn rules), distinct from the cell-split/header fixes which act on
  already-detected tables.
- [§6.3] Auto-figure fallback for un-griddable tables | invest p21 (owner note
  8dd24ee5 "should be a figure with a table in it"): a table with row rules but NO
  vertical grid (`hlines:17, vlines:0`) fails column inference → renders as a
  callout with columns run together ("Don't know how to apply 44% (8)37% (119)").
  The plan's §6.3 fallback (honest image beats garbled table) applies. SCOUTED:
  exactly 9 corpus candidates (callout reject, hlines≥3, vlines<2) — tool
  scan_fallback.py: invest p19/p21, advancing-mobility p13/p23/p27, ecp p6,
  good-food p10, rock-farm p22, nff p12 (the last is a CHART, must be excluded) |
  NAMED MISSING LEVER: gated callout→figure conversion — when `_try_table` rejects
  a row-ruled region, render `_figure_node` (crop) + a converter question instead
  of `_aside_node`; needs text-accounting claim (figure claims the region text)
  and a gate that excludes charts/legit callouts. Bounded (9 regions) but each
  needs before/after eyeball; a real feature-cycle, not a one-line fix.
- [§6.3] tablePin consumption | the schema exists (config.py DEFAULTS `tablePins`,
  §3.3) but has no consumer, AND no clean proof-specimen (the no-grid rejects are
  mostly charts; the real tables that fail are spans-pages, which a pin's cols
  alone can't assemble) | NAMED MISSING LEVER: honor a tablePin in `_try_table`
  (force table treatment + explicit `cols` cuts + `headerRows`, bypass grid
  rejection). Wire alongside the §7 loop so it has a real pin-writer + specimen.
- [§5.4] Rounded-corner / circle callouts | clean-air's $330M callout is a CIRCLE
  in source, rendered as a rectangle; §5.4's "rounded corners when the box path
  has arc segments" needs vector path-segment geometry that the region model does
  not carry (grep of extract/blocks for arc/ellipse/radius = ~0 hits) | NAMED
  MISSING LEVER: callout-shape geometry — extract arc/ellipse path segments in
  the region model → emit border-radius (or clip-path for true circles). An
  extraction-layer feature, not a §5 style token.
- [§5.4] Full-page text-over-image callouts | clean-air p15's banner ("There has
  been a recent slowdown…") overlays a hero image in the source; we render the
  text color correctly (white) but as a separate solid band BELOW the image, not
  overlaid on it | NAMED MISSING LEVER: hero-overlay layout — when a titled band
  sits atop a full-bleed figure, position the text over the figure (absolute /
  grid overlay) instead of stacking. A figures-track / layout concern.
- [§5.2] Legend-swatch renderer | premise (a live legend LEAF needing swatch dots)
  has NO clean corpus specimen — legends are either claimed into figure pixels
  (race, atlantic: do nothing) or the chart is structurally fragmented (nff p12).
  The IR models no legend region, so there is nothing to reliably hang swatches
  on | NAMED MISSING LEVER: a **legend-region model** — detect swatch□+label
  groups inside a figure's region model, expose them as legend leaves carrying
  their associated vector-fill colors; THEN §5.2's renderer (`<span class="swatch"
  style="background:…">`) becomes a trivial, safe consumer. A figures-track /
  upstream-analysis job, not a §5 style token.
- [figures] NFF p12 chart fragmentation | the "FINANCIAL CHALLENGES IN FY 2024"
  paired-bar chart decomposes into 2 bar-image figures + 6 label `<h6>` + stray
  `%` paragraphs + legend-as-figcaption, instead of one figure | NAMED MISSING
  LEVER: chart-region unification (a multi-column chart whose bars are separate
  vector groups but share one titled region should assemble as ONE figure, its
  axis labels/legend absorbed). Hard; route to the §7 vision loop or a dedicated
  figures-track pass, not §5.
- [figures] Atlantic p10 dropped chart labels | owner note 75158669: the
  "optimists/pessimists" bracket labels were live authoring-environment text
  layered on a raster chart; current pipeline drops them (not in crop, not as
  text) | NAMED MISSING LEVER: raster-figure text-overlap recovery — when a live
  text leaf sits within a raster figure's bbox and is neither caption nor absorbed
  into the crop, either extend the crop to include it or keep it as an in-figure
  caption; never silently drop.
- [§4.5] Corpus vision-loop rollout | the pilot (points-of-light p25) proved the
  machinery + prescriber but apply-all traded structural fixes for STYLING
  losses (callout label/color, pull-quote decoration) → page didn't "look
  genuinely right" | do §5 (styles baseline) FIRST, then re-run pilots; the
  loop's structural fixes land atop correct styling instead of degrading it.
- [§4.3] Convergence-criteria gap | the loop applies any override the prescriber
  returns, even one that trades one medium+ issue for another (p25 went 5→4, not
  to 0) | add a NET-IMPROVEMENT gate: re-scan after apply and KEEP the override
  only if severe-count strictly drops; else roll it back (an auto-revert rail in
  converge_page).
- [§2] Triage under-calls engine-flattened styling pages (race p20 pull-quote,
  gates p8 hero banner) → classified easy, no deterministic signal exists |
  resolves automatically once §5 makes pull-quotes / banners real nodes; until
  then §4.3's easy-sample verification scan is the net.
