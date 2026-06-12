# This is the user's unsorted backlog of tasks
> These are not in order, it should be checked periodically and items that should be done soon should be moved to TODO.md in the order that makes the most stense.

## Page breaks
when deployed to the web, a document will be 4-20 pages or so.  Most often we simply break on H1.  So for the viewer, we want some kind of visual bar that represents a pagebreak, sitting just above each H1, and draggable up or down if it isn't quite right. Also, within each of those drag bars should be a proposed path for that page, user can click to change. (error check they don't use a path name twice)

## Async reviews
It would be great if you started working on feedback items as soon as I entered them, then marked them resolved so I would know to refresh.

## Analysis & Reporting
This was only touched on a bit in RK1/2 but it would be great to have some high-level stats on the current document.  Things like number of images, number of tables, number of callouts, type of callout if there are different ones, number of footnotes, etc.  Mostly simple counts of items that we're probably already separaing out.  Oh also: a frewuency count table of hexcodes used for colors, and same for fonts, links.

## Sanity checks
SEPARATE from trying to match the pdf I'd like to run some independent checks, such as: are footontes actually sequential from 1 to the end, not out of order, none skipped nor duplicated.

## Retain images
Can we pull originals rather than cropping from pngs?  and position/size them as best we can. Also, I anticipate a config option here: resize/recode images for web.  pngcrush, optimpng etc, resize large images down (never up) to a max of double the size we need (for high res displays).  Definitely deferrable though.  

Actually this brings up a point: there could be (like the above) document-wide options. these should be collected and shown in a single panel somehow - ideally most will be multiple choice answers, so it should be a friendly/easy to use panel.

## click-to-edit existing converter notes
This works on feedback notes -- extend it to converter notes.

## to discuss: revieing the injury prevention guide
This is a series of 10+ of the same format of information, and in every case, the same converter choises apply, and I'd leave the same feedback if I were to continue.  


## Grouping converter notes
Facilitator Guide document has many converter notes, but they can be grouped -- 6, 8, 10, 11, etc are the same issue and *probably* will have the same answer.  My thought: keep the ? bubbles in the document - lets me click wherever I see it.  In the comments panel, all the notes pertaining to that same issue collapse into one note, with an indicator ie (8 occurances).  

good example is toolkit_hiring pages 96-97 -- it's a pattern of 6 elements and it's a near-guarantee the user will want to treat them all the same. 

it would be nice if answering the 8 changed the indicator in the document to something indicating it was answered but not submnitted, then as I scroll through i can click a ? and remove it from that group, and give it its own different answer. Unless there'sa good reason to hit that now, just log this as a future item.

ex: revieing the injury prevention guide: This is a series of 10+ copies of the same format of information, and in every case, the same converter choises apply, and I'd leave the same feedback if I were to continue.

re: this -- another amazing capability would be a "Select all like this" similar to how Word will let you select all Heading 3 or whatever.  

Also desired: maybe the same issue maybe not. Repeating patterns are common in this game.  I'd love to see a list with typed numbers instead of bullets, click it and say "find all like this and make them OL's". Might be an agent thing.  But this gets back to our key value prop: mass-cleanup of a huge document at once, retaining and sometimes *adding* semantic structure.

Ex: toolkit p131-132 has the same pattern as 96-97


## HTML output
The HTML being shown in the iframe is the debugging version -- the final would eliminate most of the data attributes.  I've found some limited data attributes can help in targeting css at styling time, but that should definitely be a config -- what gets uuid ids added, what gets data attributes added etc.

## Styling
When it comes to naming classes, we probably want sane defaults + config, so the user gets the clean HTML they want with the classes they need for styling.

## Amazing UI touch
Let the user drag the feedback box around by the titlebar.  Let them also, once the popup is open, select-drag text to add as evidence to the already-open popup.

## Comments
I'd like to let the user drop comments into the text, that don't require any processing on our end. Example is "remember to ask alex is this number is right." Then we want a workflow similar to the feedback -- see a list of them, click to jump, edit, delete.  longterm: assign to another user and track completion status.

# Edit ops
Once an edit has been made, I'd like a toggle to show or hide completed/closed edit bubbles in the text.