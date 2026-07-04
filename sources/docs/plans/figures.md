> **STATUS:** phases 0-5 **SHIPPED** (v169-196, commits da25b20..08fef28). Phase 6 (reproduction tiers) **OPEN** — absorbed into [webified.md](webified.md) §5 (styles) / §6 (tables). See the PROGRESS block near the bottom.

# Figures: images, charts, and their blast radius

*(drafted 2026-07-02 from the owner's ~60 figure notes; specimen note ids
in parentheses refer to feedback/*.jsonl)*

## The problem

A "figure" today is whatever falls out of region detection: a graphics
cluster becomes either a **raster crop** of the page PNG (kind=figure) or
an **aside with live text** (kind=callout), chosen by a text-density
threshold. Everything the owner's notes ask for — anatomy, deduplication,
native quality, correct membership, placement — is emergent behavior with
no model behind it. The blast radius is text: content that belongs INSIDE
a figure stays live and confuses flow, ordering, joins, and notes; content
that belongs to the FLOW gets swallowed by phantom regions.

Two renders make it vivid:

- design-principles p10: the Figure ES.1 wheel diagram became a *callout*
  (its many short labels tripped the chars_inside threshold), so the
  render shows a teal box full of single-letter paragraphs ("S", "T",
  "U"…) — the rotated ring labels — and no image at all.
- atlantic p12: the crop contains its own "Figure 2"/"Figure 3" titles
  AND the titles render as live headings above it — duplicates — plus two
  distinct figures fused into one crop with running-header debris.

## Ground truth about today's pipeline

- `_crop` is always a **raster crop of the pre-rendered page PNG**. Native
  image payloads are never extracted (extract.py stores only bounds +
  colors for OBJ_IMAGE). Quality is capped at page-render DPI; whatever
  text is painted inside the bbox is baked into the pixels.
- Top-level figure regions **claim** interior normal-size text (audit);
  callouts keep text live. Aside-interior figures only just learned to
  claim overlay text (v165-168) with a background guard.
- figure-vs-callout: `chars_inside <= 150` (or `<= 400` with no images) →
  figure, else callout; `uncertain` regions raise a two-option converter
  question (figure | callout). There is no "neither — it's decoration
  over body text" option, though regionOverride kind=text exists in
  config (tenure p13, toolkit p133 precedents).

## Note-derived defect classes

| # | class | specimens (owner notes) | today |
|---|-------|------------------------|-------|
| F1 | **figure anatomy** — title + image + caption/source/subhead as ONE `<figure>` | dp p10 7b850cd8 ("title, image, source caption"), atlantic p10 80f32560 ("down to Source…"), p15 d4d0241f, oxfam p13 264febc8 (missed subhead), oxfam p26 92d5ec78, clean-air p25 d702b517, race p9 9611d5aa (title caps styling), tenure p31 2b2535cc (photo+caption+subcaption) | no anatomy model; title/caption land inside or outside the crop by bbox accident |
| F2 | **duplicated text** — live text ALSO baked into the crop | atlantic p12 e1aad018 (Fig 2/3 headers twice), p17 df78bee5 (ABC letters), clean-air p15 1d05935c, edf p18 ab0deeab, good-food p10 6745a31a (crop duplicates the image below) | crop bakes everything; claiming is inconsistent by region kind |
| F3 | **flow text wrongly absorbed** — background/decoration minted a region | tenure p13 32654fad + p14 46f46d38 (pale graphics behind text; p13 fixed via config), good-food p8 433b7b34, dp p16 c368b1ac, oxfam p56 e99317af, race p8 5d8db09a | graphic+text ⇒ callout; no backgroundness test; question offers no dissolve |
| F4 | **figure↔callout misclassification** — label-dense diagrams read as callouts | dp p10 f9d468e2 / p19 d0550223 / p21 e8a0f7b4 ("they should all have the same treatment"), atlantic p53 056fc8c9, respond p15 9cb90ee5 | char-count threshold can't tell axis/diagram labels from prose |
| F5 | **raster quality** — crops of rasterized pages, not native assets | dp p44 df4dbebc ("extracting when we can, for maximum quality" + compression recs), edf p6 114745f7 ("cropped instead of extracted?"), edf p3 afaddb25 (missing signature graphics), tenure p11 fe05853b (photo dropped entirely), oxfam p7 2fa928b2 | no native extraction path exists |
| F6 | **crop bleed** — bbox edges catch neighbouring body text | edf p6 114745f7 ("showing some words from the paragraph"), edf p6 24619014 (excess padding) | fixed 4pt pad; bbox from object cluster, not content-aware |
| F7 | **notes/refs vs figures** — both directions | gates p61 18c4eb6c + p80 f0bed61d (doc notes swallowed), oxfam p53 e7f8f52d (note hiding in graphic), gates p13 fb5c0ab5/68c650c9 (refs that DO belong to the figure), clean-air p36 3bde230a (figure-local footnotes ≠ doc footnotes) | note recovery and figure claiming don't know about each other |
| F8 | **placement & floats** | atlantic p14 ddc5fe23 (graphic before the page title), p20 f4bec293 (figure splits a running paragraph), gates p6 cc2f63d5, tenure p25 687a4d3d (float right), p30 b2eb5940 (non-floated ⇒ 100% width), p31 (floatable anywhere in section), compelling p1 26e4afbf | insertion by bbox key only; spanning-figure rule just landed (v167); no float model |
| F9 | **callout styling fidelity** | clean-air c5012b9d/f8f06a67/2519b55c/4bf4088e (rounded, white text), clean-air p36 eae7b462 (full-page bg ⇒ page-wide callout), advancing 4a0c4f14 (thick brown border), good-food e4d1746e (partial border ≠ full box), good-food p22 627c7db3 (unreadable colors; new headers need color decisions), community-schools f02830ea | fill/stroke/borders captured; radius, text color, full-page bg not |
| F10 | **reproduction tiers** — image vs HTML/CSS vs interactive | advancing a533704d ("reproduce as HTML/CSS") + 609b9dd6 ("reproduce or use the image"), good-food 3aaeef21 (easy table), invest 8dd24ee5 (figure with a table), dp p40 54b39020, atlantic b0399c90, oxfam p29 4f552968 (responsive 2-col bios), dp p51 9e1f43ae (recognize copied-in art; restyle offer), dp f9d468e2 (RK2 got the SVG, interactive) | tables get `_try_table`; everything else is a crop |
| F11 | **figure-list residue** | dp p6 a39f1955 (list of figures dropped as TOC, its heading orphaned) | TOC drop is heading-blind |

## Doctrine (carried over from columns/lists)

1. **Model first, behavior second.** Phase 1 builds a logged, per-region
   FIGURE EVIDENCE MODEL before any behavior changes — the same
   discipline as the column model and the list census, which is what made
   those flips safe.
2. **Read the file.** Backgroundness, image payloads, z-order, border
   shapes, caption geometry are all IN the PDF. No vibes.
3. **Fidelity first, opportunities second.** HTML/CSS reproduction of a
   chart, interactive SVG, restyling copied-in art (F10) are DASHBOARD
   OFFERS per conversion-philosophy — never silent choices. The silent
   default is the faithful image.
4. **Escape hatches stay first-class.** regionOverrides (config), the
   figure-or-callout question (extended with a third "ordinary text"
   option), and ops for placement. Every automatic call must be
   overridable per-doc without code.

## Phases

### Phase 0 — gold stakes from the notes

Encode targets BEFORE the engine moves (red at plant, verified against
source page images — notes locate, sources decide):

- F1: dp p10 ES.1 (`<figure>` holding title + image + Source line) and
  atlantic p10. Needs a new eval kind `in_figure: [A, B]` — A and B are
  leaf texts of the SAME figure container — plus `not_in_figure:` as the
  negative control (flow text stays out).
- F2: atlantic p12 — "Figure 2. Overall LAC…" appears EXACTLY ONCE as
  live text (a `once:` kind or a not_in_figure + count check).
- F3: tenure p14 (the p13 sibling, still red) — body text reads in flow.
- F4: dp p10 — the wheel renders as an image (in_figure of two ring
  labels… or simpler: not_list/`role` on the leaked single-letter
  paragraphs; decide when encoding).
- F7: gates p61 #256 — note text ends up in footnotes, not the figure.
- Guards on what already works: oxfam p4 a92c2999 ("great job") freeze;
  tenure p48 overlay-claim behavior.

### Phase 1 — the figure evidence model (log-only)

Per region, one `figure-model` log event:

- **images**: count, native pixel dims (via pdfium bitmap API — see
  phase 4), each image's coverage fraction of the region bbox;
- **backgroundness** per image/fill: coverage ≥ 0.8 of region AND (fill
  color ≈ page background OR sits z-first) — the F3 discriminator we
  hand-rolled twice already (v168 area guard, tenure p13 config);
- **interior text taxonomy** (geometric, not semantic): title candidates
  (above the graphics, bold/larger, "Figure N." lead), caption/source
  candidates (below, smaller, "Source:"/"Note:" leads), label soup
  (many short lines, scattered/rotated, sub-body size — the F4
  discriminator), prose blocks (sentence-length, column-grid-aligned —
  the F3 discriminator);
- **column-grid alignment**: do interior text blocks match the page's
  column model x-ranges (decoration-over-body signal, F3);
- **note candidates**: marker-led lines matching the doc's footnote
  sequence (F7 — hand off to note recovery instead of claiming);
- **border/box evidence**: existing per-side borders + radius detection
  (rounded rect segments) + full-page-bg flag (F9).

Eyeball the logged models against every specimen page above before phase
2 (the columns-plan ritual).

### Phase 2 — anatomy assembly + deduplication

- Rebuild the figure node as a CONTAINER (unified model already allows
  it): `figure > [title leaf?, image, caption leaf?, source leaf?]`,
  title/caption/source pulled OUT of the crop bbox and kept as live,
  styleable text; the crop shrinks to the graphics extent.
- Everything the crop still shows is CLAIMED, never also live (kills F2
  wholesale — one rule, both region kinds; v165-168's overlay claim is
  the embryo).
- Adjacent same-content crops dedupe (good-food p10's crop-of-a-crop).
- Note-marker lines inside regions route to note recovery, not the crop
  (F7); refs that belong to the figure (gates p13) stay as figure-caption
  refs — the noteish gate already knows the shape.
- Render: `<figure>` + `<figcaption>`; title/caption classes for the
  styles system; race p9's caps-mirroring falls out of per-doc style
  extraction.

### Phase 3 — classification repair + the third answer

- Three-way call from the phase-1 model: **figure** (label soup / low
  prose / high graphics), **callout** (prose-dominant, boxed, own
  interior geometry), **dissolve** (background-dominant + column-grid-
  aligned prose). The ES.1 wheel and tenure p14 are the two poles.
- Extend the figure-or-callout question to three options (figure /
  callout / ordinary text over decoration) and write the answer as a
  regionOverride — the owner has now asked for this three separate ways
  (dp p16, tenure p13/p14, good-food p10).
- Confidence flag on every call (the columns-phase-3 pattern) so
  low-confidence regions surface in the proposals/questions layer
  instead of silently landing.

### Phase 4 — native extraction

- When ONE image object covers the graphics extent (the photo case):
  pull the native bitmap (pdfium `FPDFImageObj_GetRenderedBitmap` /
  `GetImageDataDecoded`, or PyMuPDF `extract_image` if we adopt it —
  leverage-libraries says use the mature lib; consider-PyMuPDF.txt is
  already in the repo root) → full-resolution asset instead of the page-
  DPI crop. Fixes the F5 quality ceiling and edf's missing signature
  images; diagnose tenure p11's dropped photo here.
- Vector figures (owner directive 2026-07-02): when the graphics are
  vector, KEEP A VECTOR VERSION alongside whatever we render — diagrams
  are far more workable with (or convertible to) SVG. pdfium has no SVG
  export; PyMuPDF's `page.get_svg_image(clip=…)` does exactly this, which
  strengthens the adopt-PyMuPDF case for this phase. The raster stays the
  rendering default; the SVG is the preserved asset the F10 tier builds
  on.
- **Image ledger** (owner directive): log every extracted/cropped asset —
  count, pixel dims, native vs crop, source format (jpeg/png/vector),
  bytes — as structured `image-asset` log events per doc, so the
  cross-corpus analysis can aggregate them (the pattern-track/market-
  research angle). Asset hygiene recommendations (dp p44: compression/
  format) read straight off this ledger.

### Phase 5 — placement and floats

- Anchor rule: a figure with a matched title/caption anchors to ITS
  ANATOMY (title first), never before the section heading it happens to
  sit above (atlantic p14) and never splitting a running paragraph
  (atlantic p20 — the wide-figure insert rule from v167 generalizes to
  top-level flow).
- Float model: source-position-derived (right-column narrow figure ⇒
  float right, tenure p25; full-width ⇒ block 100%, tenure p30), owner-
  overridable via a placement op — design this op WITH its editor
  affordance alongside the pending container-ops work (same UI pass).

### Phase 6 — reproduction tiers (opportunity layer)

Per-figure dashboard offers, ranked by confidence: table-in-figure →
real `<table>` (invest p21, good-food p6); chart → HTML/CSS
reproduction (advancing p12) with the image as fallback; copied-in art →
restyle-to-doc-palette offer (dp p51); diagrams → interactive SVG (the
RK2 memory). This phase is where the pattern track's component
recommendations plug in; nothing here runs without a per-doc yes.

## Non-goals (this plan)

- Callout STYLING fidelity (F9 rounded/white-text/full-page-bg) beyond
  capturing the evidence in phase 1 — that's the styles-system track;
  the model feeds it.
- Chart data extraction / re-plotting beyond the phase-6 offer.
- Scanned-PDF figure handling (whole-doc OCR gate owns that).

## Sequencing note

Phase 1 + 2 are the payload — they kill the two biggest classes (F1
anatomy, F2 duplicates) and de-risk everything after. Phase 3 closes the
class the owner hits most while reviewing (F3/F4). Phases 4-6 are
independent after that and can interleave with other tracks.

**PROGRESS:** plan drafted 2026-07-02; phases 0-3 SHIPPED same evening
(v169-180, census 66/6, commits da25b20 / 36c9add / ebdcec5 / ea4b652).
Phase 0: 4 eval kinds (in_figure w/ not_with, not_in_figure, in_flow,
claimed) + 12 stakes. Phase 1: figure-model log events + image-asset
ledger. Phase 2: noteish captions → note recovery, multi-image figure
SPLITTING w/ per-image title binding, aside-figure anatomy + legend
claims (background / noteish / sandwich guards). Phase 3: label-soup
diagram rule + local-color dissolve rule (paleness vs ring-sampled
surroundings, meta-title + vivid-ink + sentence-prose guards), table
conversions keep bound titles as <figcaption>, question gains the
"text"/dissolve option. 11/12 figure golds green; the holdout (tenure
p14 order 4<5) is TAG-ORDER arbitration, filed to reading-order.
Phases 4-5 SHIPPED 2026-07-03 (v181-187, render 79, commits c4e5fe0 /
7ba7d64). Phase 4: PyMuPDF adopted (pinned 1.27.2.3); native payloads
when one image mutually fits the crop and out-resolves the raster (raw
RGB JPEG/PNG byte-for-byte; smask/CMYK via Pixmap capped 3x/1600px);
cropped SVG sidecars for vector figures (viewBox re-window, data.svg);
image-asset ledger (native-jpg/png, crop-png, svg + dims/bytes/xref);
stale-asset purge; HERO pages (full-page photo by pixel variance, ONE
per page — clip-frame layouts draw collage tiles page-sized — raster
composite only; tenure p11 fixed). Phase 5 (engine side): float/wide
from PAGE-CONTENT-width evidence → fig-float-*/fig-wide CSS (tenure
p25/p30 verified); figures never split a running sentence (atlantic
p20 class, healed edf); page-leading figures anchor AFTER the opening
heading (atlantic p14). The placement OP + editor affordance remain
deferred to the joint container-ops UI pass. NEXT: phase 6
reproduction tiers (dashboard offers; pattern-track hook), asset-
hygiene recommendations off the ledger, the placement/container ops
UI pass with the owner.
