# info design tab

for our immediate next deliverable, I'd like to see our first tab, before "convert document" and "landing page" be called something like "info design". This would have two columns: an inventory, and the document.  The document would use the same side-by-side sync scroll as "convert."  I find it extremely valuable; almost essential in reviewing the document to assess our success with these tasks.  the "inventory" window would have 2 lists: identified patterns, and suggested patterns.

For this task we're just focussed on finding and extracting, so I'd like to see a run of text either outlined and/or shaded, with a label indicating what type of pattern it found or is suggesting.  

note, in markups like this I prefer css "outline" and absolutely-positioned elements or pseudo elements, so they don't shift the layout of the document.

Aside: we'll soon need to start separating out CSS -- we should be keeping rules like this (how to mark up targets during a source review) separate from rules governing the overal chrome/UX, as well as those governing document appearance. I suspect soon we're going to make a big refactor step since we're still sort of running with the layout more suited to a research spike, and at that time we'll add a database and user model, and we can also add a builder and switch to scss or some such.  For now just be aware we'll need to separate these rules out soon.


