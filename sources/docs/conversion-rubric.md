# Conversion Rubric — page-layout PDF → web-optimized HTML

The contract for what "a faithful conversion" means. Written once here so we
(and the vision-QA reviewer, and a future operator) stop re-deciding it per
document. **`OPEN` sections need your call** — fill them in.

## North star
**Faithful to the INFORMATION and the INTENT, not the pixels.** This is a
re-flow for the web, not a visual reconstruction — success is NOT a pixel-diff.
We surface the document's meaning, structure, and emphasis accurately and
cleanly; we do not reproduce its print layout.

## How to read this (esp. the QA reviewer)
Every rule is one of three kinds. The reviewer uses this to tell an *intentional
transform* from a *real error*:
- **PRESERVE** — must carry through faithfully (meaning, order, emphasis intent).
- **TRANSFORM** — we deliberately change it for the web (don't flag as an error).
- **ERROR** — never acceptable.

---

## 1. Layout & flow
- **TRANSFORM — single column.** Multi-column page layout → one linear column.
- **PRESERVE — reading order.** Content reads in the author's intended order
  (struct-tree order for tagged PDFs; geometry/column order otherwise).
- **TRANSFORM — no page breaks.** Continuous flow; the page is not a unit.
- **TRANSFORM — running headers/footers removed.** (incl. drifting per-section
  headers and standalone page numbers.)
- **PRESERVE — page-spanning content rejoined.** Sentences, lists, and tables
  split across a page break are stitched back together.

## 2. Navigation & structure
- **TRANSFORM — the table of contents is dropped from the body** and navigation
  is rebuilt from our heading tree (`dropToc = true`).
- **PRESERVE — headings → `h1`–`h6`** per the heading rules (size clustering,
  ALL-CAPS kickers, struct tags, bold run-in leads; the TOC is the level
  authority where present, and dotted numbering outranks indentation).
- **DECIDED — section numbers are `styled`** (kept as a separate element, CSS
  decides presentation). Config can switch to `inline` or `removed`.

## 3. Text & emphasis
- **PRESERVE — emphasis intent.** Bold → `<strong>`, italic → `<em>`, detected
  from real glyph ink-width (not font-weight flags).
- **TRANSFORM — typed line breaks join into paragraphs** (`typedLines = join`;
  a per-doc question can preserve intentional one-per-line text like addresses).
- **ERROR — word spacing.** "review b y" must be "review by"; no merged words
  ("includingf oods").
- 🔲 **OPEN — colored text that ISN'T a link.** When source text is colored for
  emphasis (not bold/italic, not a link), what do we do — promote to `<strong>`,
  a named role class, adopt the color, or ignore it?
  _(your call)_

## 4. Links
- **PRESERVE — the link target.** The destination URL/anchor always carries
  through, intact.
- **TRANSFORM — consolidated color palette (your stated intent).** A small,
  context-aware set of link colors — default / on-light / on-dark (or per
  callout background) — NOT a class per source color. Currently links render
  near-black (`#111`).
  🔲 **OPEN — define the exact palette** (how many, which contexts).
- **TRANSFORM — link underlines (your stated intent: do NOT reproduce them).**
  Note the tension: underlines are an accessibility affordance for links; if we
  drop them, color/contrast must carry "this is a link."
  🔲 **OPEN — confirm the rule** (drop entirely? keep on hover? rely on color?).

## 5. Lists
- **PRESERVE — list grouping.** Bullet and ordinal lists are detected and kept
  as one `<ul>`/`<ol>` with their items (and item-level emphasis/links).
- **TRANSFORM — markers rebuilt.** Source bullet glyphs / "1." markers are
  removed and rendered as real list semantics.
- **ERROR — items leaking.** A list item must not bleed into a callout/adjacent
  container, and the list must not drop or split items.

## 6. Tables — 🔲 OPEN (your call)
Today this is decided implicitly: a table detected as structured data → semantic
`<table>` (`<th>`/`<td>`); a table detected as a figure → kept as a cropped
image. Make the policy explicit:
- **When keep the image vs. rebuild as HTML?** (e.g. clean data grid → HTML for
  reflow + accessibility; infographic / merged cells / heavily styled → image?)
- **How closely match column widths?** (approximate proportions, or don't try?)
- **Accessibility for image-tables** (caption? data also available as text?).
_(your call)_

## 7. Figures & images
- **PRESERVE — figures kept as cropped images.**
- **DECIDED — no OCR.** Text baked into an image is NOT extracted; we keep the
  image (so text inside an infographic is intentionally not lifted out).
- 🔲 **OPEN — alt-text policy.** Caption-derived? generated? left empty?
  _(your call — also an accessibility requirement, see §11.)_

## 8. Footnotes & endnotes
- **PRESERVE — reference markers.** Superscript footnote/endnote markers carry
  through as references.
- **DECIDED — collected to the end of the document** (`footnotePlacement = end`,
  v1).
- 🔲 **OPEN — endnote/reference formatting.** Target is "ultra-consistent:
  number / note in clean columns." Define the exact treatment (and how links
  inside notes behave — bleeding footnote links has been a recurring bug).
  _(fill in)_

## 9. Callouts, asides & pull-quotes
- **PRESERVE — kept as semantic asides / blockquotes** with their content and
  emphasis.
- 🔲 **OPEN — styling fidelity.** How faithfully do we reproduce a callout's
  background color / border vs. normalize to a small set of house callout styles?
  _(your call — ties to the link-palette contexts in §4.)_

## 10. Color, theme & fonts
- **DECIDED — fonts.** Web-safe / system fonts by default; embedding the PDF's
  own fonts is tabled (custom-encoding wall).
- 🔲 **OPEN — brand/theme palette.** Do we adopt the source's brand colors
  (design tokens / palette) for headings, accents, callouts — or normalize to a
  neutral house theme?
  _(your call — "tokens/palette" was flagged as the next styling step.)_

## 11. Accessibility — 🔲 OPEN (set the bar)
We emit semantic HTML (real headings, lists, tables, landmarks). Beyond that,
set the explicit target:
- Target standard? (e.g. WCAG 2.1 AA?)
- Color contrast minimums (interacts with §4 link colors and §10 theme).
- Alt text on every meaningful image (§7).
- Heading hierarchy with no skipped levels.
_(your call — what's the bar we hold ourselves to?)_

## 12. Responsiveness — 🔲 OPEN
The output should reflow on any screen (a benefit of single-column). Define:
breakpoints, image/table behavior on mobile, min/max content width.
_(your call)_

## 13. What counts as an ERROR (never acceptable)
Lost or duplicated content · wrong reading order · dropped or wrong emphasis ·
broken/missing link target · mis-spaced or merged words · content in the wrong
container (list-into-callout, caption-into-callout) · a heading missed or
mis-leveled · a figure/table silently dropped.

## 14. Info-design layer — 🔲 FUTURE (your call)
The north star is "surface the most accurate and **compelling** pieces of
information." Beyond faithful conversion, this is the selection/treatment of
key-message, bold-statement, person-profile, and similar content patterns. What
does "compelling" mean operationally, and how aggressive should that treatment be?
_(this is the next value tier — leave for later.)_

## 15. Out of scope — 🔲 confirm
Likely out of scope for now; confirm: math/equations · fillable forms ·
multi-language / right-to-left · audio/video / interactive PDF elements.
_(confirm or move into scope.)_
