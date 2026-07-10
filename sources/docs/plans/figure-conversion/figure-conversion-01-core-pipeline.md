# Figure Conversion Plan 01: Core Extraction, Classification, Rendering, and QA

## Purpose

Build the non-vision Figure Conversion pipeline. This phase covers figure package extraction, classification, candidate generation, and QA/scoring. It should produce useful web-native conversions for simple diagrams and recoverable charts while preserving image fallback for every figure.

This phase includes Chart.js support for data charts. Exported HTML must not depend on the RK3 server.

## Location

Active plan file: `docs/plans/figure-conversion-01-core-pipeline.md`  
Feature standards file: `docs/features/figure-conversion-standards.md`

## Scope

Phase 1 covers:

1. Figure detection and extraction.
2. Figure classification.
3. Candidate generation for image, accessible image, HTML/CSS, SVG, and Chart.js.
4. QA/scoring and default output selection.

Vision assistance is not part of this phase. User correction is not part of this phase except that the data structures should be ready to accept correction ops later.

## Workstream A: Figure package extraction

### Goals

For every candidate figure, create a persisted figure artifact package that can support fallback rendering, QA inspection, classification, and future reconstruction.

### Required extraction

For each detected figure candidate, extract:

- stable figure ID
- source document ID
- page number
- page dimensions
- figure bounding box
- rendered crop image
- page preview reference
- text blocks inside and near the figure
- vector drawing primitives when available
- detected colors
- likely title/caption/source/note blocks
- neighboring body text context

### Vector extraction

Use the existing RK3 engine where possible. Add libraries if needed.

Recommended starting point for PDF vector extraction:

- PyMuPDF `page.get_drawings()` for drawing primitives.
- PyMuPDF text extraction for text blocks and coordinates.
- Existing RK3 raster/page preview logic for image fallback and overlays.

The extraction layer should normalize coordinates, colors, fills, strokes, and primitive types enough for downstream pattern detection.

### Figure boundary detection

Start with conservative detection. Good early signals include:

- clusters of vector primitives
- clusters of text and shapes separated from body text
- existing PDF structure when available
- captions/titles such as `Figure`, `Table`, `Exhibit`, or styled figure headings
- large non-body layout regions
- colored blocks, bars, callouts, diagram shapes, icons, and chart-like groups

Do not overfit to one PDF. When uncertain, create a candidate with low confidence and preserve image fallback.

### Output artifact

Persist a document-level `figures.json` or equivalent RK3 artifact with one entry per candidate figure.

Minimum useful shape:

```json
{
  "figure_id": "p5_fig2",
  "page": 5,
  "bbox": [72, 144, 468, 250],
  "crop_path": "artifacts/figures/p5_fig2.png",
  "page_preview_path": "artifacts/pages/page-5.png",
  "text_blocks": [],
  "vector_primitives": [],
  "title_candidates": [],
  "caption_candidates": [],
  "source_candidates": [],
  "note_candidates": [],
  "classification": null,
  "render_candidates": [],
  "selected_render_mode": "image",
  "warnings": []
}
```

Use actual RK3 artifact naming and storage conventions where available.

## Workstream B: Classification

### Goals

Classify figure candidates into a controlled taxonomy and determine whether the figure needs data-aware reconstruction.

### Initial taxonomy

Support the taxonomy defined in `docs/features/figure-conversion-standards.md`:

- `photo`
- `illustration`
- `table`
- `simple_diagram`
- `timeline`
- `flowchart`
- `matrix`
- `callout_group`
- `icon_list`
- `bar_chart`
- `stacked_bar_chart`
- `line_chart`
- `pie_or_donut_chart`
- `bubble_chart`
- `scatterplot`
- `map`
- `mixed_infographic`
- `unknown`

### Required flags

Set these separately from type:

- `geometry_encodes_data`
- `data_values_visible`
- `requires_exact_geometry`
- `layout_is_semantic`
- `decorative_layout`
- `safe_for_auto_reconstruction`
- `requires_manual_review`

### Early high-value patterns

Prioritize reliable detection for:

1. Stacked horizontal bar charts with visible percentages.
2. Simple bar charts with visible labels.
3. Bubble/circle comparison charts with visible values.
4. Timelines with labeled points.
5. Box-and-arrow process diagrams.
6. Callout groups and stat cards.
7. Simple icon lists.

### Example: stacked horizontal bar

A strong candidate includes:

- adjacent horizontal rectangles with same height
- distinct fills
- visible percentage labels inside or near the segments
- legend swatches using matching colors
- title/subtitle/note nearby

This should classify as `stacked_bar_chart`, with:

```json
{
  "geometry_encodes_data": true,
  "data_values_visible": true,
  "safe_for_auto_reconstruction": true
}
```

when segment values can be recovered confidently.

## Workstream C: Candidate generation

### Required render candidates

Every figure must have at least:

1. `image`
2. `accessible_image`

When applicable, add:

3. `html_css`
4. `svg`
5. `chartjs`

### Image fallback

Always generate or preserve a rendered crop. This is the baseline output and the fallback for all reconstructed figures.

### Accessible image

Add title, caption, source, note, alt text, and optional extracted data table when available.

### HTML/CSS renderer

Use for diagrams where semantic structure matters more than precise geometry:

- timelines
- callout groups
- stat cards
- process diagrams
- icon lists
- simple comparison layouts

The output should be responsive and exportable without RK3 server dependencies.

### SVG renderer

Use when geometry matters but the content is still better represented as shapes and text than as a charting library.

Good SVG targets:

- diagrams with precise connectors
- arrow-heavy layouts
- custom spatial arrangements
- simple vector reconstructions from PDF primitives

### Chart.js renderer

Use for true data charts when values are recoverable.

Early Chart.js targets:

- simple bar chart
- stacked horizontal bar chart
- bubble/circle comparison chart when values are visible

Chart.js output must include:

- extracted data structure
- chart configuration
- accessible text summary
- fallback table where appropriate
- image fallback
- export dependency declaration

## Workstream D: Export bundle support

### Requirement

HTML output cannot reference anything from the RK3 server.

If Chart.js or another runtime dependency is used, the export bundle builder must support one of these policies:

1. Reference Chart.js from a configured public CDN.
2. Include Chart.js in the exported bundle.
3. Disable Chart.js render candidates for export modes that disallow external or bundled JavaScript.

The selected policy should be explicit in export metadata.

### Bundle metadata

Each render candidate should declare dependencies:

```json
{
  "render_mode": "chartjs",
  "dependencies": [
    {
      "name": "chart.js",
      "type": "js",
      "source_policy": "cdn_or_bundle",
      "required": true
    }
  ]
}
```

The bundle builder should resolve these dependencies before export.

## Workstream E: QA/scoring

### Candidate scores

Score each candidate for:

- text coverage
- title/caption/source confidence
- data extraction confidence
- geometry confidence
- semantic classification confidence
- visual similarity
- accessibility quality
- responsive-readiness
- bundle-readiness
- manual-review requirement

### Default selection

Default output selection should be policy-based.

Suggested default policy:

- Use image fallback for unknown, low-confidence, complex, or non-data-safe figures.
- Use accessible image when text/caption extraction is good but reconstruction is unsafe.
- Use HTML/CSS for high-confidence semantic diagrams.
- Use SVG for high-confidence geometry-sensitive diagrams.
- Use Chart.js for high-confidence recoverable data charts.

Preserve the image fallback even when another output is selected.

## Workstream F: Figures QA UI integration

Update the Figures tab from Plan 00 to show:

- classification results
- data-criticality flags
- all render candidates
- candidate previews
- selected output
- candidate scores
- dependency/bundle warnings
- extraction warnings

The UI should make it easy to compare the original crop with the generated candidate.

## Testing and evaluation

Create a small fixture set from known PDFs containing:

- stacked horizontal bar chart
- simple timeline
- bubble/circle comparison chart
- callout/stat card
- figure that should remain image-only
- ambiguous figure requiring review

For each fixture, store expected classification and minimum expected outputs. Do not require pixel-perfect output for semantic diagrams. For charts, verify that extracted values match visible values.

## Acceptance criteria

Phase 1 is complete when:

- RK3 creates figure artifact packages for detected figure candidates.
- Every figure has an image fallback.
- The classifier assigns figure type and data-criticality flags.
- The pipeline generates candidate outputs for image and accessible image.
- The pipeline can generate HTML/CSS for at least one simple diagram class.
- The pipeline can generate SVG for at least one geometry-sensitive class or vector reconstruction class.
- The pipeline can generate Chart.js output for at least one simple recoverable chart class.
- Export bundle logic supports Chart.js through CDN and/or bundled asset policy.
- The Figures QA tab shows extraction, classification, candidates, scores, and warnings.
- A small fixture/eval set exists and can catch regressions.

## Non-goals

- No vision model integration.
- No user correction UI.
- No guarantee of full chart reconstruction for charts without visible values.
- No pixel-perfect recreation requirement for semantic diagrams.
- No dependency on RK3-hosted assets in exported HTML.
