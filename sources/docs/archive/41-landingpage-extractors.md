## H2
Many sections make use of H2.  I think we should set that once in Page Setup rather than having per-block settings.
- color
- all caps yes/no

## Summaries
we need to strip out footnote references.   Now we get "the graphic below 2" where 2 is supposed to be a <sup> footnote.  IR should have the data to tell us that's a footnote right?  I suppose it shouldn't be that hard to actually show the footnotes and their references?  At best it should be an advanced option. Initally I think we should just hide them.
- Noticed on Points Of Light that most formatting is stripped.  We should at least allow bold and italic, and I saw an OL that was turned into a UL.  We should keep that as original if we can.
- Advancing mobility has a "TM" that needs a <SUP> to look right


## Title
- If you remove all the text from one of the fields, it should collapse away and not be present in the output or take up space.
- all 3 text inputs are way too short to hold these lines.  (1) make the modal wider and use the extra space for the controls area, (2) make the text input field multi-line and wrap as needed.


## Social Share
- add fields for linkedin, X, bluesky, facebook, instagram
- and make them work
- add a field for the title, default to "Share"
- need a control for the button style, with examples rather than these names:
  - plain, no button
  - round button
  - square button
- for now lets try, for plain, show the icon in the link color, for the buttons, show the button background in the link color and the icon in white.

## Hero Image
the extracting the images is awesome.  
- add a field for caption
- Do we have the captions from the figures and can we populate that, and change it as they choose different images?
- same thing can we populate & change the ALT text correctly?

## Document Summary
- Many of these are super long.  Add a slider for limiting the number of paragraphs.  (the floated imnage position already knows the number of paragraph)
- Floated image position -- text lable crashes into the control.  might need 2 lines, or maybe only as a responsive breakpoint.

## Table of Contents
- looks like only the first item in the TOC is coming through on some?  Points of light shows one line here, but 10 in the "convert document" panel.
- also, these shouldn't be linked -- there's nothing to link them to.  It's just a list.

## CTAs
- change these to "Download Button" and "Secondary Button"
- change download subtext to "Let readers download the full PDF"
- on secondary subtext, add ", etc." at the end so they don't think those are their only choices. 
- PDF download: I might tweak this language but let's do this:
  - provide a toggle for "Do you have a URL where your PDF will live, or would you like it bundled with your download?"
    [ ] Use my URL
    [x] Include PDF in my download
  Obviously, use my.. opens a field for download URL


## Highlights
Editing this is really awkward. Candidate for RTE?

## AI Summary
- the radio buttons look weird -- white on black on grey
- Summary -- it's awkward here -- candidate for RTE?
- on the page, the line height is different than the rest of the content.



## All
- Can we add a very simple RTE for editing certain fields?  Bold, italic, bulllets, links, heading - that's about it.
- lp-field and puck-field both have a 1px border, which ends up duplicating.  only show 1 line between.


## Main builder UX
can you fade in the block toolbar after 1 second on hover?