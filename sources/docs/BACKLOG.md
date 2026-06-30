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

Another example: all the large tan callouts in Design Principles -- it'd be amazing to select them all and say "take the <strong> subheads plus their following text, and collapse those as accordions."  or "make them go side-by-side (grid or flex) instead." The key is to identify it's a repeating pattern -- in this case *nested* pattern: multiple subhead+txts inside callouts.

Also related: these are currently all per-node exceptions.  They should be a class: large header inside callout=orange, subheader inside callout=strong.


## HTML output
The HTML being shown in the iframe is the debugging version -- the final would eliminate most of the data attributes.  I've found some limited data attributes can help in targeting css at styling time, but that should definitely be a config -- what gets uuid ids added, what gets data attributes added etc.

## Styling
When it comes to naming classes, we probably want sane defaults + config, so the user gets the clean HTML they want with the classes they need for styling.

## Amazing UI touch
Let the user drag the feedback box around by the titlebar.  Let them also, once the popup is open, select-drag text to add as evidence to the already-open popup.

## Another amazing touch: Answering converter questions
When the user chooses one of the options in the converter, and it's not the one currently being displayed, it'd be amazing if it could flip realtime to show whatever the other option is.  Even if it had to wait to rebuild the document on the server and then pass the diff or whatever - a little spinner is better than a full page load.

Same would apply to intentional enhancements like making text into an accordion.  Ideally that would happen in front of your eyes without a refresh.


## Comments
I'd like to let the user drop comment bubbles into the text, that don't require any action on our end. Example is "remember to ask alex if this number is right." Then we want a workflow similar to the feedback -- see a list of them, click to jump, edit, delete.  longterm: assign to another user and track completion status.

## Edit ops
Once an edit has been made, I'd like a toggle to show or hide completed/closed edit bubbles in the text.

## maybe a silly request
One way I justify this work is by claiming HTML performs better in SEO and AEO than PDF.  I'd like to make the claim that x% of the PDFs we checked, did NOT have easily-spotted semantic headers and thus are harder for an LLM to grasp the outline.  At the bottom of the PDF list in the viewer, can you indicate how many of our pdfs have vs don't have clean semantic headers?

## Let's get smarter
Whenever the user does a manual override, we should log that and see if we can identify common issues that we could have prevented.  We could periodically do a review of these and select ones for implementation.


# Grouping by node becomes classnames
It's great that we're grouping styles instead of one-offs.  At some point we need to convert that list of data nids into a class name and apply it to all the associated nodes. 

# Additional Tabs
The full UX will feature the following tabs:
- Document Analysis
- Landing Page Maker
- Full Document

Note that once we build in the user model, some users will only have access to some of these tabs.

## Document Analysis tab
The goal of this tab is to give the user some high-level, aggregate information about their document(s).

## Landing Page Maker
This should be a highly interactive, workshop-style page.  The user will have a variety of simple controls they can use to customize a landing page for their PDF.

The goal of this builder should be to offer opinionated best practices for an SEO/AEO/a11y optimized PDF landing page, not necessarily to build a highly customizable page builder.  The expectation is the user will either download HTML code to paste into their CMS, or copy a JavaScript embed code from us and embed the landing page they've built, into their site.

### UX
Upon inital load, we need to analyze the PDF and extract information to build from.  If we've already converted the document from PDF into our IR much of that will already be available.  

The page itself should be the main document element -- that is, when the user scrolls the outermost element (BODY) the landing page scrolls.

### Content Elements
The page should be assembled as a stack of content elements.  Users can drag to reorder them, and click to insert a new element at the beginning, end, or in between two existing elements.  The UX for this "mini CMS" needs to be highly interactive and intuitive. We may build this portion custom or we may use an existing "blocks based" CMS-style page builder.


### Config
We need a config file to represent the landing page -- which elements are included, what colors various elements are, etc.  I want several different starter templates to choose from.


### Elements
Optional elements to include
- Title
- Summary
- Hero image
- Report cover/thumbnail
- Table of Contents
- Social Share prompt
- Charts/graphs
- Slideshow
- Highlights / Key Findings bullet points
- Download CTA

We need to evaluate how much of this we can extract with deterministic code vs. where we need to pass content to an AI LLM for analysis and extraction. 

The system should allow for future content elements to be developed, and some elements to be gated based on user access level.

### AI Elements
Some users may wish to disable AI entirely from their experience.  We need to:
- Clearly label any component/option which is based on sending the user's content to an AI engine
- Offer a user setting to disable all AI-based features


### Styling
The styling for the landing page should be a separate config file. Values will come from multiple sources:
- system defaults
- extract from the PDF
- extract from a given web URL (make this look like our site)
- a stored profile (paid user account can store one or more design systems)

For the system default config file use black text on white background, sane defaults for header sizes, and use Public Sans from Google Fonts


#### Features to be available based on user level, in the future

#### Level of AI Use
Options:
- none
- analysis only (allows only copying **verbatim** from the source)
- content generation (summaries, etc)

##### Split document into sections
From a single uploaded document, identify where major sections split (chapters, parts etc) and offer a table of downloads of the individual parts.  This requires splitting the PDF into multiple separate files.

##### Multiple PDFs
Sometimes the work actually consists of multiple documents, such as an executive summary, full report, methodology notes, sources notes, other language translations etc.  Allow user to upload multiple supporting documents in addition to the primary, and offer those in a download box/table/panel etc.

#### Edit the prompts sent to the AI agent for generating summaries
Make additional styles like the "hard sell" version



-- then, we need to improve the contents/TOC field.  Much of this applies to the full RK3, so consider where to make your edits so they benefit the whole platform the most.  -- they're not always very reflective of the actual contents.  Gates for example, it pulls a bullet list of items from chapter 5 instead of getting the actual chapter titles.  Atlantic council is a bit of a mess, RWJF is better than it was, but we should also take the time to fix up the uppercase/lowercase mess.   That's something I wrestled quite a bit with in RK2, specifically, it's imperative to offer a document- and/or client-specific list of forced upper and lower case words and phrases.  There's just no getting around it.  An org can very easily have acronyms as simple/common as THE or AND and now any automatic case-conversion fails.  The approach I used was to keep a list of words and phrases to retain as-is.

But that's getting ahead of ourselves.  I think we're close to needing to build out a full user model and there's no sense worrying about per-user/per-org customizations when we don't have those concepts yet.  so flag that for future, and just work in some better TOC detection and first-pass case cleanup to round out




- I need ALL prompts that get sent to AI engines to be easily reviewed and configured -- either in config files or in the database with an admin.







# So "two-column" isn't a stable IR feature to assert on
The vast majority of the time, we don't care if two columns were merged into one for the purposes of the IR.  However (1) we will occasionally want to specify text be in two columns.  So that should be supported.  and (2) I do worry about losing too much information in the IR -- sometimes detecting something far down the line suddenly becomes easier if you realize the text had a certain class, or size indent, or number of leading spaces, or something else trivial.  Are we throwing away any potentially useful information in building the IR?



## Document Styling
I want tools to let the user adjust the styling on the document.  

  **We do need to remember our focus:** Conversion and information design patterns.  Visual design is a distant second priority, but where it's straightforward, we should offer it.  When we reach that limit, the user is better off exporting the HTML/CSS and taking it to a more sophisticated design platform.  We might even consider one-click exports to such tools.

Primary focus is document-wide: Body text, body color, heading sizes, etc.

I want multiple surfaces for this (editing the same source of truth)
- click the element and adjust, real-time
- A "style guide" style panel with sliders and pulldowns
- A CSS editing panel
- A code editor showing the full CSS (possibly. Might decide against)

Secondary focus is *fixing* issues, like we didn't pick up this section of bold, or we missed a UL.  

All of these tools need to be usable by agents as well -- user may choose to tell an agent to make H2 30% larger, rather than doing that directly with controls.



