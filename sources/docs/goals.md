# RK3

This is a development spike to determine the suitability of different methods of converting PDF documents into standards-compliant, responsive HTML/CSS suitable for reading on the web.

In /sources are folders 01/, 02/, 03/ containing PDFs. Those in 01 have the simplest formatting, 03 the most complex.

I want you to build 2 pieces:
- An engine that converts PDF documents like these into HTML/CSS and formats them
- A 2-panel viewer that lets the user browse the list of available PDFs in the left panel, showing which have been converted and which haven't. In the right panel:
  - For the unconverted, a button that begins the conversion.  This can happen asyncronously for now - no progress or results display are needed.
  - For the converted, clicking the filename on the left should load the converted result on the right.

I anticipate trying different engines and approaches.  Initially there will only be one, so no additional controls are needed.  If/when we add more engines, a control to switch output display between engines will be needed.

## Goals for output HTML
The goal again is to extract the content and create the "best" HTML rendering of it. Best is defined as:
- Clean, standards-compliant, semantic HTML/CSS. 
- Pay particular attention to identification and conversion of heading levels. Regardless of internal styling/naming, mark top-level sections as H1, second-level as H2 etc.
- Primary content should be in a single column. Where PDFs are laid out in multiple columns, content should be laid together in the natural order of reading.
- Best-effort attempts at handling inline images, tables, charts.  Create these as <figure> elements
- Best-effort attempts at handling "callout boxes" -- typically an outlined or colored region with separate content inside. Create these as <aside> elements.
- Best-effort attempt at handling footnotes/endnotes. These can come in a variety of forms: sometimes they're actually notes and references within the PDF. Other times they're simply a superscript number within the text, with a number that happens to correspond, at the bottom of the page, end of the section, or end of the file, with the text of the footnote.
- If a piece of content has any relevant metadata like style/class names, anchor references, etc. copy that information into data- attributes on the output version.

## Goals for output CSS
I want CSS created in 3 layers: They can be 3 separate files, or some other arrangement that makes sense, but I want to be able to toggle primarily the 3rd layer on and off.
- First is purely layout: use it to create a suitable layout for the content, and to position any images or callout boxes in as close an approximation to the layout as you can.
- Second is a default styling: shade callouts with a light grey background, anything boxed or bordered, give a thin black outline, provide reasonable spacing around elements, etc. End result should still be a rather plain, greyscale version of the original
- Third, attempt to recreate the original styling to the extent that it serves the visual result without compromising the reading experience.  Primarily focus on 
  - identifying and assigning fonts, using serif and sans-serif family fallbacks.
  - coloring text, headers, callout boxes, etc the original colors.
  - better reproducing the relative sizes of images, callout boxes, etc.

## First pass at configuration
Getting this right will take adjustment. I anticipate a JSON config file that would accompany the source file and give instructions to the system on both the input and output steps. It should function without any config file, using defaults, but as much as possible should be able to be overridden with the config file.

## Engine #1
I first want to try using the pypdfium2 engine. 

- If the PDF is scanned/image text, bail out.  This is not an OCR effort.

## Questions to discuss before writing a plan
- Would this system benefit from any additional engines or significant additional components?
- Would this system benefit from access to a LLM? (runtime, not during the build)