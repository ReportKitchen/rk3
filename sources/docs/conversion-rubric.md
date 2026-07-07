# Conversion Rubric — page-layout PDF → web-optimized HTML

> **This is a DESIGN / DECISION document, NOT a prompt.** It carries OPEN
> questions, deliberations, and owner "your call" notes. The vision-QA scanner
> reads a DISTILLED, resolved rubric at `prompts/vision-qa.rubric.md` (rules
> only) — feeding this doc raw confused the scanner. When a decision here is
> resolved, fold it into that distilled rubric.

The contract for what "a faithful conversion" means. Written once here so we
(and the vision-QA reviewer, and a future operator) stop re-deciding it per
document. **`OPEN` sections need your call** — fill them in.

## North star
**"This looks just like my document, but webified and more interactive."**
(A comms person's words, not a capital-D Designer's.) The user knows this
document intimately — they may have lived with it for 18 months. The first
view must read as *their document*: same look, same colors, same voice —
just readable-sized text with no zooming, flowing on the web.

Faithful to the INFORMATION and the INTENT — and where layout carries meaning,
the easiest way to preserve the meaning is to reproduce the appearance. This is
a re-flow, not a pixel-diff; but "it's my document and I can read it!" beats
"it's my document but with stronger hierarchy." Improvements are the SECOND
take: a dashboard of explained, opt-in recommendations (with magic buttons) —
never silent changes to the first view. One first-view exception: important
text hiding inside images should be surfaced.

**Who it's for:** a comms person at a nonprofit/foundation told to put a big
report on the web. Success = the analytics look great next month, the
newsletter gets "I saw that report — really good work!", and ultimately the
report gets the policy uptake it deserves.

## How to read this (esp. the QA reviewer)
Every rule is one of three kinds. The reviewer uses this to tell an *intentional
transform* from a *real error*:
- **PRESERVE** — must carry through faithfully (meaning, order, emphasis intent).
- **TRANSFORM** — we deliberately change it for the web (don't flag as an error).
- **ERROR** — never acceptable.

---

## 1. Layout & flow
- **TRANSFORM — single column.** Multi-column page layout → one linear column.
  - **DECIDED — comparison-intent columns are the exception.** Two columns that
    don't flow 1→2 but hold two things up side-by-side (a table masquerading as
    columns) keep their 2-D arrangement. Long name lists (authors, funders) are
    lists masquerading as columns: linearize as a list, but always offer
    responsive multi-column presentation.
- **PRESERVE — reading order.** Content reads in the author's intended order
  (struct-tree order for tagged PDFs; geometry/column order otherwise).
  - **DECIDED — ambiguity policy: always guess, flag when confidence is low.**
    Stop-and-ask is reserved for capital crimes (broken file, password-protected,
    full-OCR-required). The manual-reorder tool is the escape hatch, not the
    default.
- **DECIDED — sidebars/callouts float on their original side**, within
  thresholds (starting points: min-width 20%, max-width 50%, max-height 80vh).
  If even max-width would run too tall, fall back to inline placement **before**
  the related text (option: after). Thresholds and defaults are org-manager
  settings — sidebars/pull-quotes/callouts are a rich schema, not one rule.
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
  ("includingf oods"). This is the trust bar: a power user who finds zero
  low-level text errors in their first three documents is a customer for life.
- **DECIDED — drop caps: preserve via CSS.** The ornamental large first letter
  renders as a styled first-letter (size/color intact) by default; removing the
  decoration is a user option. The letter itself always joins its word in the
  text ("EDF", never "E DF").
- 🔲 **OPEN — colored text that ISN'T a link.** When source text is colored for
  emphasis (not bold/italic, not a link), what do we do — promote to `<strong>`,
  a named role class, adopt the color, or ignore it?
  _(your call): promote to strong, give it a class




## 4. Links
- **PRESERVE — the link target.** The destination URL/anchor always carries
  through, intact.
- **TRANSFORM — consolidated color palette (your stated intent).** A small,
  context-aware set of link colors — default / on-light / on-dark (or per
  callout background) — NOT a class per source color. Currently links render
  near-black (`#111`).
  🔲 **OPEN — define the exact palette** (how many, which contexts).
- **DECIDED — link underlines are a CSS concern, not HTML markup.** We do NOT emit
  HTML underline tags (`<u>`) on links; underlining is styling. By the time the
  vision-QA reviewer sees the RENDERED output, a link that calls for an underline
  DOES show one (via CSS). So the reviewer must NOT treat a missing `<u>` tag as a
  dropped feature — the rendered link carries its own visual affordance
  (color/underline). The real rule (per below): flag a link only when it reads too
  much like non-link body text.

per note below: in our very first pass, we strive for fidelity. We immediately present a list of issues/concerns/opportunities for improvement, along with an importance scale (low, med, high, critical).  If we judge their links to be "too close visually to other non-link text" then we drop a "high" issue into the queue.  These notes would have buttons/options for how to resolve, including a "magic button" to just do it for them.  In this case that would mean adjusting underlines and colors so links were distinctive.  But again, not until they say so.


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
_(your call) 

we should always attempt to convert a table-as-image to HTML, matching the original fonts/colors/spacing/borders/etc. The review interface should have an option to switch out the converted for the original so the user can see how each looks -- but we should default to HTML


## 7. Figures & images
- **PRESERVE — figures should be extracted from the PDF source, not cropped from a rendered version.**
- **DECIDED — no OCR.** Text baked into an image is NOT extracted; we keep the
  image (so text inside an infographic is intentionally not lifted out).  The one exception is tables - we should make every attempt to turn image-baked tables into HTML.
- **alt-text policy.** first-pass, nothing.  At review user will have the option to enter alt texts, or click a magic button and have us generate them for them.  If we can find caption text, that becomes the default for the user and for our magic.  if not, we use a vision model to create a description.

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
  emphasis. Placement/float rules are in §1.
- **DECIDED — pull-quote duplication stays.** A pull quote that repeats body
  text is a design echo the author chose: never drop it, never even offer to.
  (Only a manual delete tool removes it. When WE someday suggest pull quotes on
  unstyled imports, then duplicate-or-not becomes a question.)
- 🔲 **OPEN — styling fidelity.** How faithfully do we reproduce a callout's
  background color / border vs. normalize to a small set of house callout styles?
  _(your call — ties to the link-palette contexts in §4.)_

## 10. Color, theme & fonts
- **DECIDED — fonts.** Web-safe / system fonts by default; embedding the PDF's
  own fonts is tabled (custom-encoding wall).
- 🔲 **OPEN — brand/theme palette.** Do we adopt the source's brand colors
  (design tokens / palette) for headings, accents, callouts — or normalize to a
  neutral house theme?
  _your call: per-doc, the end user will have the option to use the document's style, or replace it with one of their stored styles. "use the document's style" means to extract a style guide from the document, including fonts, sizes, spacings, colors, etc.  The style guide should have 3 parts: (1) a base set to start with (h1, p, a) (2) an RK set we anticipate, ex callout-[default|A|B|C]-[title|background|link], footnotes, chart styles/colors,etc, and (3) a set of remaining classes that enables us to match the document's style but that we don't have an obvious anticipated match for.  The goal should be as clean and simple a styleguide as possible (we've discussed this -- elaborate if you like)


## 11. Accessibility — 🔲 OPEN (set the bar)
We emit semantic HTML (real headings, lists, tables, landmarks). Beyond that,
set the explicit target:
- Target standard WCAG 2.1 AA
- Color contrast minimums -- General 
- Alt text on every meaningful image (§7).
- Heading hierarchy with no skipped levels.

House philosophy his to get results as quickly as possible. Don't make the user answer questions up front if we can use a default and give them the option to change it later. So in this context: our default is to match their colors as closely as possible.  After initial conversion they'll see a dashboard with notes about accessibility and they'll have an option to adjust their palette to achive color contrast minimums, add ALT tags, etc. Re: Accessibility we can help and guide but we won't degrade their visual appearance without their approval.


## 12. Responsiveness — 🔲 OPEN
The output should reflow on any screen (a benefit of single-column). Define:
breakpoints, image/table behavior on mobile, min/max content width.
_(your call)_

## 13. What counts as an ERROR (never acceptable)
Lost or duplicated content · wrong reading order · dropped or wrong emphasis ·
broken/missing link target · mis-spaced or merged words · content in the wrong
container (list-into-callout, caption-into-callout) · a heading missed or
mis-leveled · a figure/table silently dropped.

## 13a. AI boundaries & content-gen marking — DECIDED
- **AI never:** adds or offers "outside" information (no "here's a stat about
  housing costs"); never suggests a significant pivot ("this should be a
  video"); standard governance (never expose private info).
- **ALL generated content is called out** — marked in-place AND reviewable in a
  single read.
- **Auto-disposition is sanctioned** when the model is sufficiently confident,
  as long as every action is logged and reviewable.
- **Assistance-level settings** (per-doc, per-user, per-org — like the AI tiers)
  gate what we even OFFER: e.g. for headings — shorten/reword for navigation ·
  "add headings to help readers scan" · combine very short sections. Some users
  are organizationally forbidden from deviating from the approved document;
  their settings suppress those suggestions across all three surfaces: magic
  buttons, the wizard pass (walk the doc suggestion-by-suggestion), and the
  dashboard (filterable table, only permitted suggestions shown).

## 14. Info-design layer —  FUTURE
The north star is "surface the most accurate and **compelling** pieces of
information." Beyond faithful conversion, this is the selection/treatment of
key-message, bold-statement, person-profile, and similar content patterns. What
does "compelling" mean operationally, and how aggressive should that treatment be?
_(this is the next value tier — leave for later.)_

## 15. Scope — DECIDED
**The theme: focus shows in where we test and refine, not in what we accept.**
It doesn't hurt to let someone try an off-focus import.
- **Forms: out.** This is not that tool.
- **OCR-dependent files: out for v1.0** — but it's a discrete pre-import pass
  we could add if demand appears.
- **Spreadsheets: untested, not blocked.** (RK1 "recipes" sometimes flowed a
  spreadsheet in as a table; RK3 may or may not ever go there.)
- **Slide decks: accepted, not optimized.** Occasionally designed like our
  reports.
- **Word / Google Docs import: NEAR-TERM (1.0 or 1.1)** — avoid deep
  PDF-specific coupling in the pipeline now.
- Still likely out: math/equations · multi-language/RTL · audio/video ·
  interactive PDF elements.
