# DEFERRED: on-demand OCR for text baked into images

**Status: DEFERRED capability (owner-requested 2026-07-09).** Not PDF-wide OCR —
a *targeted* extraction the pipeline/app can lean on when we decide we want to pull
text out of a raster.

## Why (owner's framing)
> "I expect we'll need to integrate OCR soon — not PDF-wide but for when text is
> baked into an image and we decide we want to get it out. The app needs to be
> able to lean on that easily if needed."

## The problem it unblocks — the DEDUP category (Phase B #4)
The single biggest QA category is **duplicated content**: text that is baked into a
raster (cover art, chart, infographic, page-thumbnail, section screenshot) AND is
ALSO extracted as live text → the same content renders twice (owner personally
flagged race p13 "two copies of the header"). ~40 CRITICAL findings across ~20 docs.

A safe fix is BLOCKED without image-content understanding. Proven on 2026-07-09
(scratchpad dupimg_scan.py / dupimg_diag.py): a geometric "drop the figure that
overlaps live text" rule is UNSAFE — of 7 flagged figures, 3 were REAL content
(invest p28 a bar chart, clean-air p11 a solar-panel photo, advancing p16 a
building photo). Color-complexity gating doesn't separate them cleanly either
(good-food text-box 15 colors, but invest chart 57 and foia screenshot 34 overlap
the photo range). The only reliable discriminator is: **does the image actually
CONTAIN the same text?** — i.e. OCR the crop and compare to the live text.

## Design sketch (when built)
- A small OCR helper (`ocr_image(png_path) -> text`) callable on any figure crop
  or sub-region. Lazy/opt-in; never runs corpus-wide by default.
- Dedup use: for a figure whose bbox overlaps a complete live-text block, OCR the
  crop; if OCR text ≈ the live text (high token overlap), it's a duplicate →
  suppress the correct copy. DIRECTION matters and is per-case:
  - screenshot of a text section (good-food p8/p10, gates p5) → drop the IMAGE, keep live text.
  - cover art / photo with baked title (clean-air p1, tenure p1, edf p1) → drop the LIVE TEXT, keep the image.
  Discriminator seen in the data: covers = full-page image + few live nodes with
  NO sentence punctuation (title fragments); screenshots = image overlaps a
  complete multi-node block WITH sentences.
- App hook: expose an "extract text from this image region" action so a user/agent
  can pull baked-in text on demand (e.g. to make a chart's labels selectable).

## Related
- Memory [[webified-track]] (dedup lever, cycle-3 Phase B #4).
- Scratchpad evidence: dupimg_scan.py, dupimg_diag.py (session cb1ac080).
- Vision-QA already proves the duplication exists; OCR is the missing extract-side leg.
