> **STATUS:** IMPLEMENTED — footnotes are fielded data with reconciliation (analyze.py `_note_marker`; `footnotes` inline+data variants; `_reconcile_notes` emits a footnote-mismatch banner node).

# Footnotes are data

Footnotes (aka endnotes) consist of 2 parts: a referece and a note.

Part 1: References are inline in the text, usually superscripted. The visual style of footnote references is typically the same site-wide.  the only variation is when the text is on a colored backgound, then the text will be a different color.

References are usually numbers, but can be roman numerals, or letters. 

Typically there's one set that runs through a document, however sometimes the numbering restarts every page, or every chapter. 

This is easy to verify: find every reference, check its style and the background color it's on.  If 64 black-on-white references are bold and 1 is not -- that 1 is probably wrong.


Part 2: Notes 



ok, the previous session got us off track on footnotes.  I was told again and again they were fixed, and they weren't. I don't think the agent understood footnotes - you have to collect them as fielded data, the index (number, roman numeral, or letter) separate from the text/html.  Then you have to parse the notes the same way.  When we break pages, if a page has #4-#9 then we need to put those at the bottom of that page, in a hidden div, so the rollover JS can find it and show it as a tooltip.  None of this needs to be done now, but this makes it clear that you HAVE to track the index of both references and notes.

It's a very easy QA step to say "does every refrence and every note have a match?"  If not, raise a flag (we don't have a flags panel yet so dump it at the top of the document for now)

current version, we're dumping out all the footnotes at the bottom of the document, in a OL, making sure the index numbering matches.

if the document has a "Footnotes" section, replace it with our dump of the footnotes we collected, making sure to keep headers and styles intact.

evidently some rule told the agent to output footnotes somewhere in the document.  that makes no sense and is wrong.