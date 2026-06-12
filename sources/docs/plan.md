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

## Deferred (recorded so we don't lose them)

- LLM assist stage (heading adjudication, callout semantics, footnote matching, vision-based layer-3 recovery)
- Engine #2+, engine-switcher UI
- Progress indicators, batch processing
- Configurable footnote placement
- ExpressJS front-end
