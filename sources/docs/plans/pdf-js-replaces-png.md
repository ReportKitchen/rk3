> **STATUS:** PROPOSED — **not built.** The viewer still renders the original as a PNG page stack (output/pdfium/<slug>/pages/page-NNNN.png); no pdfjs-dist dependency or PdfJsPane component exists.

# Replace Original PDF PNG Stack With PDF.js

## Summary

- Feasible and recommended: replace the right-side "Original PDF" PNG stack with an embedded PDF.js viewer, not a browser PDF iframe. A custom PDF.js pane preserves the current sequential-page UX while adding real PDF text selection and link annotations.
- Current app facts: `app/ui/src/components/DocumentView.jsx` builds the PNG page stack; `app/ui/src/syncScroll.js` maps converted HTML anchors to page-stack positions; `app/main.py` already serves original PDFs at `/api/source/{slug}`.
- The source PDF endpoint is ready for PDF.js streaming: ranged GET returned `206 Partial Content` with `accept-ranges: bytes` locally and through `https://rk3.dev9.rpkn.qa/`.
- PDF.js is a good fit: Mozilla documents browser loading via `getDocument({ url })`, page rendering with viewports/canvas, and NPM usage through `pdfjs-dist`.

References:

- https://mozilla.github.io/pdf.js/examples/
- https://mozilla.github.io/pdf.js/api/draft/module-pdfjsLib.html
- https://github.com/mozilla/pdf.js

## Key Changes

- Add `pdfjs-dist` as a frontend dependency and import the worker/CSS through Vite.
- Add a `PdfJsPane` React component that uses PDF.js viewer primitives to render every page sequentially at pane width, with canvas, text layer, and annotation/link layer enabled.
- Keep all page boxes in the DOM using `pageDims` aspect ratios, but let PDF.js render visible/near-visible pages lazily so large docs like `02--chep-300pages` stay usable.
- Preserve feedback behavior by delegating clicks from the PDF pane to the nearest PDF.js page element and computing `{ page, xf, yf }`; render existing PDF feedback spots as overlays on those page elements.
- Update `setupSync` to accept either legacy `img[data-page]` pages or PDF.js page wrappers such as `.pdfjs-page[data-page]`, using the same `data-page` + HTML `data-yf` interpolation. Sync remains bidirectional.
- Keep the existing PNG stack as an internal fallback if PDF.js fails to load or render; the normal "Original PDF" column becomes PDF.js.

## Public Interfaces

- No backend API change required. Continue using `sourceUrl(slug) -> /api/source/{slug}`.
- Keep `pageUrl(slug, page)` only for fallback PNG rendering.
- New component interface:

```jsx
PdfJsPane({ doc, pageDims, feedback, feedbackMode, onAnnotate, onReady })
```

- `setupSync(win, htmlDoc, pdfPane, isEnabled)` keeps its signature; only page-box discovery changes internally.

## Test Plan

- Add Playwright browser tests for the React viewer:
  - Open a converted doc with the PDF pane visible and assert PDF.js page wrappers render sequentially.
  - Assert `.textLayer` exists and text can be selected in the PDF pane.
  - Assert `.annotationLayer a[href]` exists for a known link-bearing doc and that clicking an external PDF link opens or navigates to the expected URL.
  - Assert scrolling the converted HTML moves the PDF pane, and scrolling the PDF pane moves the converted HTML.
  - Assert feedback-mode clicks on PDF.js pages still create stable `{ page, xf, yf }` targets.
- Run `cd app/ui && npm run build`.
- Manual QA on `https://rk3.dev9.rpkn.qa/` for:
  - `02--foia-basics-for-activists-may-2019` for links/text selection.
  - `02--chep-300pages` for large-doc performance.
  - A failed/scanned doc to confirm the PDF pane still gives the reviewer something useful.

## Assumptions

- "Same behavior" means all pages appear in one vertical sequence, not that every canvas must eagerly render immediately.
- Link testing focuses on the original PDF side; the converted HTML already extracts and renders many PDF links separately.
- The generic PDF.js `web/viewer.html` and native browser PDF iframe are not used because they would make sync scroll, feedback overlays, and automated link tests much harder to control.
