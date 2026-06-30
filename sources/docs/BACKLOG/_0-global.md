# No Data Left Behind campaign

The signal we're leaving on the table — and it's the bold story again: 13 of 31 docs are tagged PDFs. Their struct tree declares the reading order (the element sequence IS the reading order). We currently read the tags only for roles (heading/list/caption) and throw the order away, then re-infer it geometrically. For ~42% of the corpus, reading order is deterministic and we're guessing it.

Can we ensure this isn't happening anywhere else?  


# [x] Input sources
 we're focussed on PDF right now but before long we'll want to be able to imnport MS Word documents, and Google Docs (via API or HTML upload).

- IDML import is a possibility, although, with solid-enough PDF that may not be necessary.
- if we can import Google Docs we can import more-or-less any HTML (although additional cleaning/rules will likely apply)
- Down the road I anticipate other API import plugins but my guess is anything liked that would deliver us either HTML, docx, or pdf anyway.

so the real issue is making sure we're not coupled too tightly to PDF, and can add MS Word or HTML import processing without much rework.