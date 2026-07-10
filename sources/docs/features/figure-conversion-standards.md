# Figure Conversion Standards

## Purpose

Figure Conversion is the RK3 feature area responsible for preserving, interpreting, and, when safe, rebuilding figures from source PDFs as web-native HTML, SVG, CSS, JavaScript, and structured data.

The goal is not to force every PDF figure into editable markup. The goal is to preserve every figure reliably, expose what RK3 believes it found, and create editable, accessible, responsive replacements when the structure and data can be recovered with acceptable confidence.

Every figure must always retain an image fallback. Figure reconstruction is an enhancement, not a replacement for reliable preservation.

## Core principles

1. **Preserve first. Rebuild when safe.**  
   RK3 must always be able to fall back to the original rendered figure image. If conversion confidence is low, the image fallback is the correct output.

2. **Separate extraction, interpretation, and rendering.**  
   The system must not jump directly from PDF content to final HTML. It should build intermediate artifacts: page objects, figure bounds, text blocks, vector shapes, classification, extracted data, candidate render specs, and QA scores.

3. **Treat data charts differently from diagrams.**  
   When geometry encodes values, reconstruction must preserve the data relationship. Circle, bubble, bar, line, scatter, stacked bar, and similar charts require data-aware rendering. Decorative diagrams may be approximated more freely.

4. **Expose uncertainty.**  
   Each figure should carry confidence scores and review flags. Agents and users should be able to see why RK3 chose image, HTML, SVG, or Chart.js output.

5. **Prefer structured specs over raw model output.**  
   Vision models may help interpret a figure, but they should return structured figure specs. RK3-owned renderers should generate the final HTML, SVG, CSS, and JavaScript.

6. **Keep exported bundles self-contained.**  
   Exported HTML must not depend on the RK3 server. If a renderer requires Chart.js or another client-side dependency, the bundle builder must either reference it from a public CDN or include the asset in the exported bundle according to the selected export policy.

7. **Make corrections repeatable.**  
   User corrections that function as instructions must be stored as converter ops that run after standard rules. Added custom HTML, CSS, JavaScript, or data assets should be stored as sidecars and referenced by those ops.

8. **Build for review and evaluation.**  
   Figure Conversion must produce artifacts that can be inspected in the QA UI. These artifacts are not just debugging aids; they are the foundation for evaluation, regression testing, and future improvement.

## Standard figure pipeline

The standard pipeline should follow this shape:

1. Detect candidate figure regions.
2. Extract a rendered crop for each candidate.
3. Extract text blocks within and near the candidate region.
4. Extract vector drawing primitives where available: rectangles, paths, lines, fills, strokes, clipping regions, and transforms.
5. Associate title, caption, source, note, and surrounding body text.
6. Classify the figure type.
7. Determine whether geometry encodes data.
8. Generate one or more render candidates.
9. Score candidates.
10. Select a default output according to confidence and project policy.
11. Preserve all artifacts for QA review.
12. Apply post-standard correction ops and sidecars.
13. Export selected output plus image fallback.

## Figure artifact model

Each figure should have a stable ID and an artifact package. At minimum, the package should include:

- source document ID
- page number
- figure index on page
- bounding box
- rendered image crop path
- nearby title/caption/source/note candidates
- extracted text blocks with coordinates
- extracted vector primitives with coordinates and styles
- detected colors
- classification result
- data-criticality result
- candidate outputs
- selected output
- confidence scores
- warnings
- provider metadata for any AI-assisted step
- correction ops applied
- sidecars applied

The figure ID must be stable enough to support review, corrections, and regression tests across repeated runs of the same source document. If bounding boxes shift slightly between runs, matching should use a combination of page number, nearby text, title/caption hash, image hash, and approximate geometry.

## Classification taxonomy

The initial taxonomy should include:

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

The classifier should also set these independent flags:

- `geometry_encodes_data`
- `data_values_visible`
- `requires_exact_geometry`
- `layout_is_semantic`
- `decorative_layout`
- `safe_for_auto_reconstruction`
- `requires_manual_review`

## Render modes

RK3 should support the following render modes:

### Image fallback

The original rendered figure crop is used as the visual output. This mode is always available.

### Accessible image

The image fallback is used visually, but RK3 adds improved alt text, caption, source, note, and optional extracted data table.

### HTML/CSS diagram

Used for cards, timelines, process diagrams, callout groups, simple relationship diagrams, and other layout-driven figures where semantic structure matters more than exact pixel geometry.

### SVG

Used where precise geometry, lines, connectors, arrows, or shape placement are important, but a full charting library is unnecessary.

### Chart.js

Used for data charts where values are recoverable and should remain editable or responsive. Supported early targets should include simple bar charts, stacked horizontal bars, and simple bubble/circle comparison charts where values are visibly printed or otherwise recoverable with high confidence.

Chart.js usage must be compatible with exported bundles. Exported HTML must either include a bundled Chart.js asset or reference a configured public CDN. It must not reference RK3-hosted JavaScript.

## Candidate scoring

Each candidate output should receive scores or flags for:

- text coverage
- title/caption/source confidence
- data extraction confidence
- geometry confidence
- semantic classification confidence
- visual similarity
- accessibility quality
- responsive-readiness
- bundle-readiness
- whether manual review is required

A reconstructed figure should not become the default output unless it passes the selected safety threshold. The fallback image should remain attached even when a reconstruction is selected.

## AI and vision usage

Vision assistance is a separate Figure Conversion task, not a generic QA vision task. It should use the system-wide per-feature AI agent configuration, with a distinct configuration key for figure vision.

The QA UI must show which provider and model were used for each AI-assisted interpretation. This is required so reviewers can compare providers and evaluate quality across documents.

Vision output should be stored as structured interpretation data, including provider metadata, prompt version, response version, confidence, extracted elements, and warnings. Vision models should not be treated as authoritative when they conflict with extracted PDF text or vector data.

## Correction model

User corrections that affect conversion behavior must be stored as ops. These ops run after standard extraction, classification, and rendering rules. Examples:

- set figure type
- adjust bounds
- assign title/caption/source/note
- set data values
- map labels to colors
- choose render mode
- disable reconstruction
- force image fallback
- attach sidecar HTML/CSS/JS/data

Additional code and assets should be stored as sidecars. Sidecars must be explicit, versioned, and included in export bundles when selected output depends on them.

## QA expectations

The existing QA UI should include a Figures tab. The tab should make figure behavior visible early, before correction features exist.

The QA UI should show:

- original page preview
- detected figure bounds
- text vs figure region boundaries
- figure crop
- extracted text blocks
- extracted vector primitives summary
- classification result
- data-criticality flags
- candidate render modes
- selected default output
- confidence scores
- warnings
- AI provider/model metadata when applicable
- applied correction ops when applicable

The first version of this UI does not need direct feedback controls. It must make the system’s assumptions inspectable.

## Success definition

Figure Conversion is successful when RK3 can reliably:

- preserve all figures as images
- identify candidate figure regions
- expose its reasoning in QA
- classify common figure types
- rebuild simple diagrams and recoverable charts
- keep data-aware charts data-accurate
- use vision selectively for ambiguous figures
- accept repeatable post-standard correction ops
- export outputs without RK3 server dependencies
