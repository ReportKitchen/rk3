# RK3 goals for information design

Report Kitchen's key value proposition is based on our understanding of large structured bodies of content -- primarily these semi-scholarly reports.  The life cycle of this content is generally:

1. research happens
2. authors write it up
3. junior editors pull the pieces together
4. senior editors rework the content to be more compelling
5. designers lay it out for print
6. it gets posted as a PDF

We have no part in #1 - #3.  
If your content isn't at at least #3 yet, you're not ready for Report Kitchen.
- Sometimes, we get the content after #3, as Word/Google Docs. It reads as a coherent document, but it's typically flat.
- Sometimes we get it after #4. The content is structured and compelling, with out much/any visual design
- Sometimes we get it after #5 (as InDesign) or #6 (as PDF).  Levels of desgign can vary from almost none (our headers and bullets are dark green) to nearly magazine-style visual punch.
- If you content looks like Teen Beat magazine, you'll probably need a fully manual reformatting process, and aren't an ideal Report Kitchen customer.

The skill and level of effort applied at steps #4 and #5 vary widely.

## RK's primary goal is reformating #5/#6 as standards-compliant web content, leveraging the design cues from the PDF.

Examples of this reformatting include:
- correctly identifying all the levels of headers and turning them into navigation
- correctly identifying the logical flow of text, handling multi-column layouts, boxes that inturrupt the flow of text, content that goes across page breaks, etc.
- correctly identifying images, charts, tables, figures, etc and displaying them appropriately
- correctly handling footnote/endnotes, internal and external links, etc. These need to be extracted as addressible elements, with a default of approximating the visual appearance in the document (superscript, colored, question mark icons, etc; collected at the end of the page, end of the report, etc) but then easily reformulated once the user has selected some options (change the note numbers into icons, move all notes to the end of the report, have the references pop up on hover of the numbers, etc)

At a minimum, they need to look "more or less" like they do in the print version. Ideally, we 
- intelligently turn text tables into html/css, optionally with responsive, sort/search, etc capabilities. 
- identify when images are "design filler" vs. genuine content.  In a report on housing, a smiling family in front of a house is likely filler.  It can be repositioned, sized up or down, and potentially cropped, reused, replaced or even dropped. In the same report a photo showing a cutaway house with labeled parts showing cost/energy saving opportunities, is content.  It should probably be displayed at nearly-full screen size (but still visible on one screen) and depending on the level of detail, offered with a zoom in/out tool so readers can get the full value of the diagram.  Ideally, if possible, we'd turn the graphic into an interactive experience, letting people roll over sections of the house to learn more.  These conversions depend heavily on the source content and what we can get out of it, as well as time/effort the user is willing to invest.  In some cases select specific pieces like this might be rebuilt by a programmer.
- Same goes for charts & graphs. Minimum: extract titles, subtitles, captions and attribution text and show those as HTML text, while displaying the content of the chart as an image.  Ideally, be able to extract the exact data and rebuild the chart, leveraging its existing design cues, as either an SVG or using an interactive JS charting library.

Where #4 and #5 have been performed with great skill, our mandate is to mirror the PDF as closely as possible while still leveraging the HTML environment.

## RK's secondary goal is to assist teams with great researchers and writers, but without access to a great content strategist and/or information designer.

Where #4 and #5 have been performed but there's still opportunity for improvement, such as:
- an old report done in outdated visual branding
- a report leaning heavily on visual placements -- frequent use of "as shown below," "as the previous page illustrates," "in the boxes above from left to right..."; lines of text flowing organically around an irregular outline such as an animal, etc; key information that exists entirely as a graphic ("lessons learned" written in handwriting on a chalkboard)

In these cases we need to extract as much information as we can, both the semantics as well as the existing visual treatments, and reformat them in potentially entirely new ways, that work better online and/or better match a new visual direction.

Where #5 hasn't been done at all (we get a straight Word document) we need to prepare the text as cleanly as possible for one of two next steps: (1) we export clean HTML to an environment where a designer will take it further, or (2) we offer relatively sophisticated design tools with a focus on batch behavior: Either document wide, or according to select rules (each chapter has a different accent color.  apply that accent color to headers, table outlines, etc. etc.).  We're not aiming for "direct manipulation" style "move this header over 5px" but rather easy-to-use tools that help the user create a consistent look across the entire document, without having to know the intracacies of designating different elements with classes, etc.

Where #4 hasn't been done or is lacking, we want to be able to offer suggestions for "information design patterns" such as:

- accordions
- horizontal tabsets
- callout boxes
- infographic-style number/fact
- pullquotes
- popup modals
- photo/gallery sliders
- explainer graphics/diagrams (hover on an element to get a description, click to progress a sequence)
- lists: ul, ol, dl but also: suggest a set of icons to dress up a list or a table, make a deeply nested list more accessible by collapsing parts, etc.

As a "reach" goal I'd like to pursue the kind of "clever" design treatments you expect from great human designers, such as:
- Enhancing content that has a geographic focus with maps, flags, or other geo elements
- Taking a bullet list from a report on education and styling it as handwriting on a chalkboard
- Illustrating the process and steps of immigration by using calendars or timelines
- Explaining home solar energy with an interactive image of a house where you can adjust the number and size of the panels, select a loction (for latitude), adjust the cost of grid power, and see a live calculation of expected savings.

Deep expertise with these information design patterns is critical to RK3 -- landing page maker, self-serve Express version, and consultant-led full version.

## Finally our no-compromises goal is to output web content that performs exceptionally in all aspects of:
- readability/comprehension
- accessibility
- traditional SEO
- still-evolving AEO

A typical report for us could be the result of half-million-dollar grant funded project, that involved a dozen or more staff members for 6 to 24 months.  The PDF might be 150 pages. There's an unspoken understanding that, quite possibly, zero people will read the report from start to finish.  There are people and organizations who say such reports should never again be produced -- that such a project should disseminate its information through wide variety of modern digital channels.

Report Kitchen aims to be the bridge from the world of 150 page PDFs, to that world. 

A distant future incarnation of Report Kitchen could collect findings from researchers in the field, pass them to program managers for verification, then to editors for commentary, then combine them with video submitted by a different team working the same problem, and produce social posts for a media consultant to review and publish.  

Until organizations are ready for that, we need to take their 150 page PDFs and help drive the greatest possible impact that work can have on the world, by making sure the research, the opinions, the ideas and insights, reach the people who can turn those into action.  And that includes people who already follow the organization, those who follow the subject are but don't know about the organization, and those who operate several degrees of separation away who don't know this information exists and don't necessarily know how to look for it.

AI answer engines in particular will play a strong role in the last case. And while the top-line recommendations (produce clean semantic HTML) are simple, the nuances -- of how crawlers identify and process information, and how inference determines what to surface to their inquirer -- are less clear, and are evolving as we speak. Where we can, we need to instrument our final output so we can learn and adapt as these requirements and opportunities shift.

