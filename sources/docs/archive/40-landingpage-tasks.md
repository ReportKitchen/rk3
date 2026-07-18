- content settings - AI - WHEN we have a user model, the user's AI settings can override the options here, but until then, we should show the options.

note this means we have to remove some blocks from the library and from the content page, if they downgrade their settings from when they started.  if that's going to happen, we should also show a note under the AI settings area telling them that.  No need for a confirmation box -- the notice will serve as that confirmation.

- Doc summary: paragraphs shown and floated image could be a good bit longer; they feel unnaturally short.  and, if there's no floated image then don't show that control here.

- Export zip contains an HTML comment that starts:
  The landing page's own styles — used in three places from this single
   source: bundled so Puck copies it into its canvas iframe....
None of that should be shown the end user.

- We should bundle a "Read Me.txt" file with instructions on pasting the content into a CMS.  not sure what else we can say besides "paste it" but even a little instructions, with a section for "WordPress, Drupal, or other systems..." makes people feel like they're on the right track if they're using one of those.


- Export: is it possible to offer an export mode with no CSS, only all inline styles?  I'd like to see an option like:

Styles:
- embed stylesheet in HTML
- separate CSS file
- inline styles


## TOC element
- make default titled "Report Contents"


## Findings
these can be very long.

ex: Clean air fund has this bullet list:
**A total of $330 million of known funding went to air-quality projects between 2015 and 2022.** Since 2015, the level of investment to air-quality projects has more than quadrupled, indicating funders’ growing commitment. However, the level of funding from foundations to air quality in 2022, estimated at $71.3 million, has increased only slightly since 2021, suggesting a slowdown in year-on-year growth.

I'd love to just show the bold parts of each of those.  it's a relatively common pattern -- can we try identifying it and just pulling the main point of each bullet?



RTE:
- The headings button (a) doesn't let you un-heading text, and (b) doesn't wrap its content in h3 on the front end -- 
)

Highlights:
- remove the preview side and make the entire dialog one pane.  heading, body, box color, is all we need.