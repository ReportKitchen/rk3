# These are fundamental elements that need to be addressed wholistically


## Headings
Header parsing is actually huge for RK.  I'm pretty sure we'll never come up with a ruleset that never fails.  And, it's critical for breaking into web pages, building navigation, for understanding semantics, for outlining/summarizing, for "reading by scanning" etc.

also when we get to importing "final but not polished" documents, it's common to have to adjust headings up or down.  Most authors don't meticulously curate their headings, so if it hasn't been to a designer yet, anything goes.


## Footnotes
- match the size and position of the references.  They're almost always superscripted, but vanilla HTML superscripts mess with line-heights, so we need as lean and approach as possbile to avoid that while staying semantically pure.
- consistency: the formatting of references is almost always consistent within a document.  an easy QA pass of the computed style attributes of refs should yeild at most a small number of variations (typically color changes when they occur within a region with a background)
- placement at the bottom of the document: again should be consistent -- never would we expect font sizes, indents, or other major attributes to change substantially.

## Column ordering
- when we reach a point of diminishing returns, should we build a lightweight column order adjustment tool? If we know all the peices that belong in columns could we make a drag-and-drop that locked you to reordering elements in a single dimension?

## Callouts


## Tables

## Figures: Charts & Graph
- extract from PDF, not crop from render
- retain any ALT text in the source
- QA pass: identify images with missing alts; if AI == gen then offer to auto-caption

## Figures: Images

## More precise styling, fonts, colors

## Handling design elements: lines, random graphics floating around
- we often want to ignore these.  QA tool that lets you decide which to keep and which to toss?
- the more complete solution is to reinterpret what the design elements were doing, and apply that to a web-optimized format.
- good example: Tenure p14 - purple tree graphic.  Converter thought it was a callout.


## Page Breaks


## Internal links