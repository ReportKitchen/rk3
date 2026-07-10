# Figure Conversion Plan 03: User Correction Ops and Sidecars

## Purpose

Add user correction support for Figure Conversion. Corrections should be repeatable instructions that run after RK3’s standard figure extraction, classification, and rendering rules.

The correction system should let users or reviewers fix figure bounds, classification, data, render choices, labels, and custom code without hardcoding one-off logic into the core converter.

## Location

Active plan file: `docs/plans/figure-conversion-03-user-correction.md`  
Feature standards file: `docs/features/figure-conversion-standards.md`

## Scope

Phase 3 adds:

- correction ops model
- sidecar model for custom HTML/CSS/JS/data
- correction UI in the Figures tab
- correction application step after standard rules
- correction persistence
- correction audit/review display
- export integration for sidecars

## Correction philosophy

Corrections should not mutate the source PDF or silently patch intermediate artifacts. They should be stored as explicit operations that run after standard processing.

This keeps the core converter general, while allowing project/document-specific overrides.

## Correction ops

Correction ops should be ordered and applied after standard extraction, classification, rendering, and candidate scoring unless an op explicitly needs to run earlier.

Recommended initial ops:

### Bounds and grouping ops

- `setFigureBounds`
- `splitFigure`
- `mergeFigures`
- `assignTitleBlock`
- `assignCaptionBlock`
- `assignSourceBlock`
- `assignNoteBlock`
- `excludeBlockFromFigure`
- `includeBlockInFigure`

### Classification ops

- `setFigureType`
- `setDataCriticality`
- `setGeometryEncodesData`
- `setRequiresManualReview`

### Data ops

- `setChartData`
- `editChartDataValue`
- `mapLabelToColor`
- `mapLabelToShape`
- `setSeriesLabels`
- `setCategoryLabels`
- `setUnits`

### Render selection ops

- `selectRenderMode`
- `disableRenderMode`
- `forceImageFallback`
- `forceAccessibleImage`
- `forceHtmlCss`
- `forceSvg`
- `forceChartJs`

### Sidecar ops

- `attachHtmlSidecar`
- `attachCssSidecar`
- `attachJsSidecar`
- `attachDataSidecar`
- `replaceRenderWithSidecar`

### Review ops

- `markReviewed`
- `markNeedsReview`
- `addReviewerNote`

## Example ops file

```json
{
  "document_id": "example-document",
  "ops_version": 1,
  "ops": [
    {
      "op": "setFigureType",
      "figure_id": "p5_fig2",
      "value": "stacked_bar_chart",
      "reason": "Reviewer confirmed chart type."
    },
    {
      "op": "setChartData",
      "figure_id": "p5_fig2",
      "data": [
        {"label": "Some program areas", "value": 25, "unit": "%"},
        {"label": "Most program areas", "value": 36, "unit": "%"},
        {"label": "All program areas", "value": 39, "unit": "%"}
      ]
    },
    {
      "op": "selectRenderMode",
      "figure_id": "p5_fig2",
      "value": "chartjs"
    }
  ]
}
```

Use actual RK3 artifact and config conventions where available.

## Sidecars

Additional code or assets should be stored as sidecars, not embedded invisibly into correction ops.

Sidecars may include:

- custom HTML
- custom CSS
- custom JavaScript
- corrected chart data
- replacement SVG
- supporting assets

Sidecars must be:

- explicitly referenced by correction ops
- versioned or hashable
- included in export bundles when used
- visible in QA
- removable without corrupting standard processing

## Correction UI

The Figures tab should gain editing controls after the read-only review UI is stable.

### Required controls

For each figure, allow a reviewer to:

- adjust bounds
- reassign title/caption/source/note
- set figure type
- set data-criticality flags
- edit extracted chart data
- choose render mode
- force image fallback
- attach or select sidecars
- add reviewer notes
- mark reviewed
- mark needs review

### UI constraints

The UI should save corrections as ops. It should not directly edit generated output files as the primary correction mechanism.

The UI should show:

- original detected value
- corrected value
- active ops affecting the figure
- sidecars attached to the figure
- final selected output after ops

## Correction application step

Add a pipeline step that applies correction ops after standard rules.

Recommended order:

1. Run standard figure extraction.
2. Run standard classification.
3. Generate standard render candidates.
4. Score candidates.
5. Apply correction ops.
6. Regenerate affected candidates if needed.
7. Re-score or mark corrected outputs.
8. Select final output.
9. Export final output and sidecars.

Some ops, such as bounds changes or split/merge, may require partial reprocessing. Implement this explicitly rather than silently modifying late artifacts in a way that hides dependencies.

## Persistence

Store correction ops in a durable project/document location. They should be easy to move, diff, review, and rerun.

Preferred early approach:

- JSON correction ops sidecar per document or per source PDF.
- Additional code/assets as sidecars in a document-specific directory.

If RK3 later moves corrections into the database, preserve export/import to the same JSON ops format so corrections remain portable and reviewable.

## Export integration

The export builder must include any sidecars required by selected figure outputs.

If a corrected figure uses custom JavaScript, custom CSS, a replacement SVG, or Chart.js, the exported bundle must include or reference those dependencies according to export policy.

Exported HTML must not reference RK3 server paths.

## Audit and regression behavior

Corrections should be visible in QA and should become part of regression fixtures when appropriate.

For each corrected figure, preserve:

- who or what created the op when available
- timestamp
- reason/note
- prior value where practical
- resulting selected output

Do not require full user accounts to implement the first local/dev correction version, but design the schema so audit metadata can be added.

## Acceptance criteria

Phase 3 is complete when:

- Correction ops can be stored and loaded for a document.
- The converter applies correction ops after standard rules.
- Bounds, classification, data, render-mode, and fallback corrections are supported.
- HTML/CSS/JS/data sidecars can be attached and exported.
- The Figures QA tab supports creating and viewing correction ops.
- The final output reflects applied correction ops.
- The QA UI shows which values were standard vs corrected.
- Exported bundles include required sidecars and do not depend on RK3 server paths.

## Non-goals

- No freeform direct editing of generated output as the primary correction model.
- No requirement to build a full graphic design editor.
- No expectation that user corrections retrain the classifier automatically.
- No removal of image fallback.
