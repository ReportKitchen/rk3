> **STATUS:** ASPIRATIONAL — not built (no paged-PDF export path in rk3/ or app/); the doc itself flags it as not a development priority.

# PDF on demand

A feature of some RK1 and RK2 sites is the ability to export the content to a new PDF.  This is typically used when the document was not designed, and we were given Word or Google Docs source.

There are advantages, including not having to pay for a print design step, and the ability to make edits and have them reflected in the PDF immediately, but there are significant issues with reliably producing a paged PDF from web-optimized HTML.

We should keep our eyes on this feature in case there are opportunities to lay groundwork to improve the quality we get from these, but it's not an overall development priority.

## To consider: feedback loop
Can we design a feedback loop where the PDF gets produced, and then we analyze it to identify common failures, like tables breaking across pages, widows & orphans, etc. The most effective, if blunt, tool we have is forcing a page break, but if we could at least do that in a tight automated loop, it would save significant time and make the output much better. 