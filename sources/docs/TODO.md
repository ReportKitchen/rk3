# These are not in order, it should be checked periodically and items should be done at a sensible time

## Page breaks
when deployed to the web, a document will be 4-20 pages or so.  Most often we simply break on H1.  So for the viewer, we want some kind of visual bar that represents a pagebreak, sitting just above each H1, and draggable up or down if it isn't quite right. Also, within each of those drag bars should be a proposed path for that page, user can click to change. (error check they don't use a path name twice)

## Async reviews
It would be great if you started working on feedback items as soon as I entered them, then marked them resolved so I would know to refresh.

## Analysis & Reporting
This was only touched on a bit in RK1/2 but it would be great to have some high-level stats on the current document.  Things like number of images, number of tables, number of callouts, type of callout if there are different ones, number of footnotes, etc.  Mostly simple counts of items that we're probably already separaing out.  Oh also: a frewuency count table of hexcodes used for colors, and same for fonts.

## Sanity checks
SEPARATE from trying to match the pdf I'd like to run some independent checks, such as: are footontes actually sequential from 1 to the end, not out of order, none skipped nor duplicated.

## Retain images
Can we pull originals rather than cropping from pngs?  and position/size them as best we can. Also, I anticipate a config option here: resize/recode images for web.  pngcrush, optimpng etc, resize large images down (never up) to a max of double the size we need (for high res displays).  Definitely deferrable though.  

Actually this brings up a point: there could be (like the above) document-wide options. these should be collected and shown in a single panel somehow - ideally most will be multiple choice answers, so it should be a friendly/easy to use panel.