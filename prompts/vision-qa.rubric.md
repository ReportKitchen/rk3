Distilled conversion rules for the QA reviewer. Every rule is PRESERVE (must
carry through — flag if lost/wrong), TRANSFORM (a deliberate web change — do NOT
flag), or ERROR (never acceptable). Use these to tell an intentional transform
from a real defect. (This is the scanner's working rubric, distilled from the
team's design decisions — not the design doc itself.)

NORTH STAR: "This looks just like my document, but webified." Same content, same
reading order, same emphasis, same look and colors — reflowed to a single
readable web column. It is a re-flow, not a pixel-diff: single-column and
web-optimized is expected, but the content, structure, colors, and emphasis must
read as the same document.

## Intentional TRANSFORMS — do NOT flag these
- Multi-column page layout linearized to ONE column. (Exception: two columns held
  side-by-side for comparison — a table-like or two-things-at-once arrangement —
  should keep their 2-D relationship; long name/author/funder lists linearized to
  a list are fine.)
- No page breaks; continuous flow. Page numbers gone.
- Running headers/footers removed (including drifting per-section headers).
- The table of contents is dropped from the body (navigation is rebuilt).
- List bullet glyphs / "1." markers removed and rendered as real list semantics.
- Typed line breaks joined into paragraphs (unless the text is intentionally
  one-per-line, like an address block).
- Section numbers kept as a separate styled element (CSS decides presentation).
- Drop cap rendered as a styled large first letter (the letter still belongs to
  its word: "EDF", never "E DF").
- Footnotes/endnotes collected to the end of the document (markers stay in place).
- Text baked inside an image/infographic is NOT lifted out to live text — the
  image is kept as-is. (The ONE exception: a data TABLE baked as an image should
  be rebuilt as an HTML table; a table left as an image is an 'opportunity'.)
- No alt text on images in the first pass (added later on review) — do NOT flag
  missing alt text as an error; a missing-alt note is at most a low opportunity.

## PRESERVE — flag if lost or wrong
- Reading order — content reads in the author's intended order.
- Headings — present and at the right level (h1–h6).
- Emphasis intent — bold and italic carried through (as <strong>/<em>).
- Link targets — every link still points where it did. Links should VISUALLY read
  as links (color/underline are a CSS concern and DO appear in our render); flag a
  link only if it is visually indistinguishable from surrounding body text, or if
  a whole link/phrase is missing. Do NOT flag "no underline tag" — underlining is
  CSS, and a styled link that reads as a link is correct.
- List grouping — bullet/ordinal lists kept as one list with all their items and
  item-level emphasis/links; no item leaking into an adjacent box.
- Page-spanning content rejoined — a sentence, list, or table split across a page
  or column break is stitched back together.
- Callouts / asides / pull-quotes — kept as semantic boxes WITH their look: their
  background/fill color, border, and title. A callout's fill and a header strip's
  color should match the original (a should-be-white box rendered colored, or a
  header-strip color smeared over the whole box, is a real defect — see the
  wrong-fill hunt in the system prompt).
- Colors and theme — match the source's colors as closely as possible (headings,
  accents, callout fills, colored emphasis). "Same look, same colors" is the bar.
- Footnote/endnote reference markers — carried through as references.

## Genuine ERRORS — never acceptable
Lost content · DUPLICATED content (the same title/heading/banner/block appearing
twice — see the duplicate hunt in the system prompt) · wrong reading order ·
dropped or wrong emphasis · broken or missing link target · mis-spaced or merged
words ("review b y", "includingf oods") · content in the wrong container
(list-into-callout, caption-into-callout) · a heading missed or mis-leveled · a
figure or table silently dropped · an element (callout, box, banner) rendered in
the wrong color.

## The one allowed duplication
A genuine PULL-QUOTE that intentionally re-quotes a sentence of body text is a
design echo — do NOT flag it. This exemption is ONLY for a short quoted sentence
shown as a pull-quote; a whole title, heading, header, or banner appearing twice
is never a pull-quote and is a duplicate ERROR.
