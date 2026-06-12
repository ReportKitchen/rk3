# RK3 — Implementation Plan (v1)

Decisions from discussion (2026-06-12):

- Python web app for the spike (FastAPI). Long-term front-end will be ExpressJS; nothing here should assume otherwise.
- Engines emit a shared intermediate representation (IR); a single renderer produces the HTML and the 3 CSS layers. Engines compete on analysis only.
- Engine #1 uses **all available signals**: PDF structure tags when present (4 of the 7 corpus PDFs are tagged), blended with geometric/font heuristics. Final structural decisions weigh everything.
- No LLM in v1. The pipeline reserves an optional IR→IR "assist" stage for later; it must be cacheable (keyed on file hash + config hash) and diffable against the deterministic output.
- Headers/footers/page numbers stripped; provenance preserved as `data-` attributes (`data-page` etc.).
- Footnotes: collected at end of document with backlinks (placement becomes configurable later).
- Hyperlinks preserved as `<a>`. TOC pages detected and **removed**; navigation is reconstructed from our H1/H2/H3 tagging.
- Config: `<name>.config.json` alongside `<name>.pdf`, merged over defaults.
- The 7 sample PDFs are representative but not the target: the product must be general-purpose across any text PDF (no OCR). Thorough testing with the largest documents is deferred until basic processing works on the smaller ones.
- Viewer statuses: **unconverted / in progress / converted** (plus **failed**, which the scanned PDF will exercise by design). Display only; source files never move. No progress UI; user reloads to check.
- No conversion time limit.

## Directory layout

```
/var/www/rk3/
  sources/01|02|03/        # PDFs + optional <name>.config.json (existing)
  output/<engine>/<slug>/  # conversion artifacts per document per engine
    index.html
    layout.css             # layer 1: pure layout
    default.css            # layer 2: plain greyscale styling
    original.css           # layer 3: original-look recreation (toggleable)
    images/                # rasterized figure crops
    ir.json                # the IR, kept for debugging/diffing
    meta.json              # status, timings, source hash, engine version, error info
  app/                     # FastAPI app, API, static viewer assets
  rk3/                     # Python package: pipeline, IR, renderer, engines
```

`<slug>` is a filesystem-safe version of the PDF filename. `meta.json` is written
at conversion start (`in_progress`) and finalized on completion (`done` /
`failed` + error message) — this is the whole status mechanism; no DB.

## Multi-pass pipeline & stage artifacts

The pipeline is explicitly multi-pass; every stage writes its result to disk as
an artifact before the next stage runs:

| Stage    | Artifact                          | Needs the PDF? |
|----------|-----------------------------------|----------------|
| extract  | `extract.json` + `pages/*.png`    | yes            |
| assemble | `blocks.json`                     | no             |
| analyze  | `ir.json` + `images/`             | no (crops from `pages/*.png`) |
| render   | `index.html` + 3 CSS files        | no             |

Each artifact stores a fingerprint: hash of (source-file hash, the config keys
that stage depends on, a per-stage code version constant). Re-running a
conversion skips any stage whose fingerprint is unchanged — e.g. changing
`footnotePlacement` re-runs only `render`; the PDF is never re-opened. The
`extract` stage pre-renders every page to PNG so downstream figure cropping
also never needs the PDF.

## Debug log

Every conversion appends keyed entries to `debug.jsonl` (one JSON object per
line). Keys are stage-prefixed sequence numbers (`ex-000412`, `an-000037`, …).
Each entry records: stage, event (e.g. `heading`, `strip-footer`, `merge-block`),
the decision made, the *reason* (signals and thresholds involved), and source
provenance (page, bbox, font, original text). Every element in the output HTML
carries `data-rk="<key>"` pointing at the log entry that produced it — the
output files are far too long to grep usefully, so the workflow is: inspect the
problem element in the browser → take its `data-rk` key → grep `debug.jsonl`
for the full decision trail. IR nodes carry the same keys, tying artifacts,
log, and output together.

## Pipeline stages (engine #1: `pdfium`)

1. **Load & gate** — open with pypdfium2; compute per-page extractable-text density;
   if the document is image-only (e.g. `2020-2026 Criteria Comparison Narrative.pdf`),
   fail fast with a clear "scanned/image PDF — OCR out of scope" error in meta.json.
2. **Extract** — text runs with char boxes, font name/size/weight/color; link
   annotations; page geometry. When the PDF is tagged, read the structure tree
   (pikepdf) for role and reading-order signals.
3. **Assemble** — cluster runs into lines and blocks; detect multi-column layout
   and linearize into natural reading order; detect repeating per-page blocks
   (running headers/footers/page numbers) and strip them, recording `data-page`.
4. **Analyze structure** — all signals combined (tags, font-size/weight clustering,
   numbering patterns, whitespace):
   - Heading levels normalized to H1/H2/H3… regardless of internal naming.
   - Paragraphs, lists.
   - Figures: image and vector-graphic regions → rasterize the page region @2x
     into `images/`, emit `<figure>` (vector charts have no embedded image to
     extract, so region rasterization is the default).
   - Callout boxes: bordered/filled rects containing their own text flow → `<aside>`.
   - Tables: best-effort grid detection → `<table>` inside `<figure>`.
   - Footnotes: superscript-number references matched to note text (bottom of
     page / end of section / end of file forms); v1 renders all notes at
     document end with backlinks.
   - TOC pages: detected (dot leaders, page-number columns, link clusters) and dropped.
5. **IR** — JSON-serializable document tree; every node carries provenance
   (page, bbox, font, style/class names, anchor refs) that the renderer copies
   into `data-` attributes.
6. **Render** — semantic single-column HTML5 + the 3 CSS layers; reconstructed
   `<nav>` built from the heading tree; layer 3 attempts original fonts
   (serif/sans-serif fallbacks), colors, and relative sizing.

## Config file

`<name>.config.json`, all keys optional, merged over defaults. Initial shape:

```json
{
  "input":  { "pageRange": null, "scannedTextThreshold": 100,
              "headerFooterZones": null, "columnHint": null },
  "structure": { "headingOverrides": [], "calloutHints": [],
                 "footnotePlacement": "end", "dropToc": true },
  "output": { "imageScale": 2, "cssLayers": ["layout", "default", "original"] }
}
```

Exact keys will grow as tuning needs emerge; the principle is: defaults work
with no file, everything important is overridable.

## Web app & viewer

- FastAPI + uvicorn. Endpoints:
  - `GET /api/documents` — scan sources/, join with output meta.json → list with status
  - `POST /api/convert/{slug}` — kick off background conversion (FastAPI BackgroundTasks), return immediately
  - `GET /output/...` — static artifacts
  - `GET /` — the viewer
- Viewer: plain HTML/JS, two panels. Left: document list with status badges.
  Right: convert button (unconverted/failed), "in progress" notice, or the
  converted document in an iframe with a **layer-3 CSS on/off toggle**.
- Engine switcher deferred until engine #2 exists, but output paths and the
  documents API are engine-aware from day one (`output/<engine>/…`).

## Milestones

1. **Skeleton** — app, viewer, status lifecycle, background conversion wired to a stub engine. Verifies the whole loop end-to-end.
2. **Core extraction** — stages 1–3 + basic headings/paragraphs; clean HTML for the two text PDFs in 01/; scanned PDF fails gracefully.
3. **Structure** — figures, callouts, tables, lists; CSS layers 1–2; tune against 02/.
4. **Refinement** — footnotes, links, TOC removal, tagged-PDF signal blending, full `data-` provenance.
5. **Layer 3 + config** — original-look CSS, config file support; tune against 03/ (annual report) and the 139-page toolkit.

Acceptance check for v1: all 7 PDFs run through the system; 6 convert, 1 fails
with the scanned-PDF message; headings, reading order, callouts, and footnotes
are reasonable on the 01/ and 02/ documents; viewer statuses behave across reloads.

## Viewer (React) & interaction model — added 2026-06-12

The viewer is React + Vite (`app/ui/`, built with Node 22 via nvm; `npm run
build` → `dist/`, served by FastAPI, later by Express unchanged). Decisions:

- **Stable node IDs**: every IR node carries `nid` (hash of type+page+bbox),
  emitted as `data-nid`. Unlike per-run `rk` debug keys, nids survive re-runs.
  All interaction features target nids.
- **Edits are declarative ops, never DOM mutations** (drag/retag/group UI
  later emits `{target: nid, op, value}`; applied at render stage; re-run is
  render-only so sub-second). User edits, question answers, and the future
  config-agent are all producers of the same op/feedback stream.
- **Feedback**: viewer feedback mode → click element (or PDF-pane spot) →
  popover → `feedback/<slug>.jsonl` (gitignored). During development Claude
  reads and acts on these ("process the feedback"); later the in-codebase
  agent consumes the same stream and may only edit config + re-run.
- **Converter questions**: analyze emits low-confidence decisions into
  ir.json `questions` (stable `qid`), shown as inline (?) markers + a panel;
  answers are feedback entries of type `answer` (phase 1). Phase 2: answers
  become config overrides consumed on re-run.
- **Real-time collab**: tier 2 (live presence, op broadcast over WebSocket,
  LWW per key) is planned and cheap on this model; tier 3 (CRDT prose
  co-editing) remains a maybe and bolts on per-text-node later.

### API contract (port spec for the eventual Express backend)

- `GET /api/documents` → `[{slug, name, folder, path, hasConfig, status
  (unconverted|in_progress|done|failed), error?, finished?, pages}]`
- `POST /api/convert/{slug}?force=` → `{slug, status}`; conversion runs in a
  subprocess; status is polled via /api/documents (meta.json is the truth)
- `GET /api/feedback/{slug}` → array of feedback entries
- `POST /api/feedback/{slug}` body `{type: comment|answer, text?, nid?, rk?,
  page?, xf?, yf?, qid?, choice?}` → stored entry (+ts, status:open),
  appended to `feedback/<slug>.jsonl`
- Static: `/` viewer; `/output/<engine>/<slug>/…` artifacts (index.html,
  ir.json, pages/*.png, images/*, debug-*.jsonl, meta.json)

## Additional source formats — decided 2026-06-12

Sources will expand beyond PDF: **MS Word/OpenOffice (DOCX/ODT)** for sure,
possibly the **HTML that Google Docs exports** (may be skipped). Decisions:

- Each source format is just another engine emitting the shared IR; renderer,
  CSS layers, nav, footnote placement, autolink, feedback/questions/ops, and
  the viewer all apply unchanged. **Engines declare their own stage lists**
  (DOCX ≈ extract→analyze→render, no geometric assemble; HTML skips
  extraction and starts at cleanup/normalize).
- **Engines own their nid scheme**: bbox-hash for paginated sources,
  content+position hash for flowed ones.
- **Physics vs policy** discipline: getting text/structure out is per-engine;
  document-shaping decisions (footnote placement, TOC removal, autolink,
  callout styling) live in shared stages so all sources benefit.
- Flowed sources have no pages, so no reference pane or sync-scroll by
  default. Direction chosen: render a reference via `libreoffice --headless`
  → PDF → existing page-PNG path when LibreOffice is available (NOT currently
  installed on this box), keeping the compare/annotate UX uniform.
- Word style mapping: named heading styles map 1:1; direct-formatting soup
  ("bold 16pt Normal") reuses the size-clustering judgment + question
  emission with different signals.
- No structural prep now: pipeline.py's per-engine stage lists and
  extension-based engine selection in documents.py get refactored when the
  first docx engine lands (no-backwards-compat rule applies).

## Tagged-PDF signals — done 2026-06-12

Implemented entirely in pypdfium2 (no content-stream parsing needed): struct
tree gives role→MCID; page-object content marks give MCID→bounds; analyze
votes a (role, coverage) per block by area overlap. Blending learned from the
corpus:

- **Artifact marks are the big win**: running headers/footers/decorations are
  stripped authoritatively (287 blocks in the toolkit, 70 in the annual
  report — which fixed its heading quality more than anything else).
- **Tag heading roles are used when present** (dense-ranked, Title>H1>H2…)
  — but only 1 of 5 tagged sample docs tags headings at all; InDesign
  commonly tags everything P.
- **A P tag never vetoes strong size evidence** (authors mistag real
  headings as P); the disagreement instead emits a tag-conflict question —
  the refinement loop decides.
- Caption role strengthens caption matching; TOC/TOCI roles drop TOC blocks.

## Regression tests — added 2026-06-12

Lesson carried over from RK1/RK2: heuristic tuning for one document silently
breaks others, and rule ordering turns into spaghetti without guardrails.

- `tests/expectations.json` — curated, human-meaningful invariants per
  document, mostly distilled from resolved viewer feedback (exact headings,
  must/must-not contain strings, sequential note numbering, aside structure,
  the scanned-PDF bail-out). A failure here is a regression, full stop.
  **Workflow rule: when a feedback note is resolved, add its invariant here.**
- `tests/snapshot.json` — auto-generated structural summary of every doc
  (headings, node counts, text size). After an intentional rule change run
  `.venv/bin/python -m tests.regen` and **review the git diff doc by doc** —
  that diff is the blast radius of the change.
- Run with `.venv/bin/python -m pytest tests -q` (~7s warm thanks to stage
  fingerprint skipping). Run before every commit.
- Rule-ordering discipline: decision order is the literal sequence in each
  stage's run(); "does X happen before Y" is always answerable by reading it,
  and decisions log their reasons to the keyed debug logs.

## Milestone 5 (layer-3 CSS + config plumbing) — v1 done 2026-06-12

- original.css is now **generated per document** by the render stage from IR
  provenance: body/heading fonts (cleaned names + serif/sans fallbacks +
  weight/style from name), heading colors and rem sizes relative to body,
  per-aside fill/border from the region's drawn rects, original list markers
  (symbol glyphs → square), section-number circle badges in the doc's accent
  color, pull-quote mark styling. Near-white text colors are skipped (they
  were legible only on the PDF's dark backgrounds).
- Every question kind now has a config consumption path: figure-or-callout →
  structure.regionOverrides; heading/caps/tag-conflict → headingOverrides
  (textPrefix → level, 0 = paragraph); hard-returns → breakOverrides.
  Overrides trump all heuristics and log their application.
- output.cssLayers gates which layer <link>s are emitted.
- Remaining for later passes: per-element font exceptions, aside text
  colors, layer-3 typography niceties (letter-spacing, small-caps).

## Edit-ops layer — v1 done 2026-06-12

Durable per-element operations: `<name>.ops.json` next to the source,
loaded into cfg (so ops are in the render fingerprint: an op change is a
render-only, sub-second re-run), applied as the IR transform at the start
of render. v1 vocabulary: **set-text**, **delete**, **set-level**
(paragraph↔heading). This is where one-off cleanups live instead of
hyper-specific pipeline rules (user directive). Viewer: feedback-mode
popover offers Edit text / level select / Remove element on any element;
the panel lists all edits with one-click Undo. Ops are nid-keyed and
remapped across re-runs like feedback (note: a remap lands one conversion
behind, harmless in practice). Config + ops files are now git-tracked
(`!sources/0*/​*.config.json`, `*.ops.json`) — they encode user decisions.
Future vocabulary (move-after, group-collapsible, class-scoped selectors)
extends the same mechanism per the selector-scopes note below.

## Templates & plugins — raised 2026-06-12, deferred by design

Both are IR→IR transforms in a stage between analyze and render (the same
slot reserved for LLM assist). Pipeline shape when built: analyze →
transforms (ordered per-doc list from config) → render.

- **Templates** (RK2's regex→twig pattern): matcher over IR nodes (type,
  text regex, href pattern, data-attrs) + extracted variables + an HTML
  fragment with slots (youtube link → <figure> embed; callouts → modals).
  Templates are pure data (JSON match-spec + HTML string): front-end
  editable (HTML-only editor, drag-in variables), per-doc or shared by
  location, and writable by the future config agent. Needs a "raw HTML" IR
  node type carrying data-transform provenance.
- **Selector scopes** (user, 2026-06-12): transforms/ops/templates must
  support three scopes with one mechanism — instance (nid), class
  ({type: aside, anchor: right} → "all callouts 25% width";
  {type: heading, level: 4} → "all h4s become accordions"), and document.
  Class scope is the system's value prop vs. a CMS editor: changes apply
  board-wide and to future conversions. Structural class transforms need a
  shared **sectionize** primitive (heading + following content → container,
  for details/summary accordions, section moves, page-break grouping).
- **Agent-built templates** (user: "game changer"): because templates are
  pure data, the runtime agent can construct them from a text description —
  user selects a target (nid/span gives coordinates), describes the
  transform in the feedback box, agent reads the matched IR nodes, emits
  the template JSON, render-only re-run shows the result; template stays
  inspectable/editable. Agent emits data only, never code; suite + snapshot
  diff bound the blast radius.
- **Plugins**: Python we write, plugins/<name>.py exporting
  transform(ir, ctx) → ir, referenced from per-doc config (one-doc vs
  shared = same mechanism, different config lists). Examples: CSV-driven
  image replacement + attribution captions; nid-targeted Google-Sheets
  table refresh; chart → interactive d3/chartjs embed.
- Decisions to honor when building: plugin file content hash joins the
  stage fingerprint (editing a plugin busts the cache); network-touching
  plugins are impure — declared TTL or always-rerun, never fake
  determinism. Stable nids are the targeting mechanism ("this table here");
  span offsets target sub-element transforms.

## Deferred (recorded so we don't lose them)

- Validating intended vs unintended change during per-doc config tuning:
  per-doc config can't bleed across documents (each doc's fingerprint chain
  uses only its own config), so cross-doc snapshot diffs always mean a CODE
  change side effect. Residual problem — separating intended from unintended
  diffs *within* the tuned document — deferred until config tuning starts.
- Questions phase 2: answers → per-doc config overrides consumed on re-run
- Edit ops UI (drag-to-move callouts, retag heading levels, accordion
  grouping) + op log; then WebSocket live presence (tier 2)
- nid remapping across reconversions (bbox drift orphans ops/answers)
- LLM assist stage (heading adjudication, callout semantics, footnote matching, vision-based layer-3 recovery)
- Engine #2+, engine-switcher UI
- Progress indicators, batch processing
- Configurable footnote placement
- ExpressJS front-end (API contract above is the port spec)
