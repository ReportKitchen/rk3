I'd like to test out how well we can suss out the client's page settings in order to pre-populate LPM's page settings.  I've added a "landingpage-template" key to the first 2 reports' config.json.  See if you can fetch the page (ignore robots.txt because in this scenario the content owner is directing you to scan their page) and determine the following attributes.

Note this will be useful for RK Express as well, and possibly other tools, so try to keep it as reusable as possible.

And as I say that -- do a little research to see if there's an existing library designed to do this.

From the page:

- find the element holding the main body text and find:
  - its background color
  - its text:
    - font
    - weight
    - color
  - its link:
    - color
    - rollover color
  - its width or max-width
- page background color, or, the background color of the parent element to the main body text
- whether the main body is centered or offset significantly to the left or right -- ie, if there's a sidebar.

I'm also curious how successful we'd be at rendering the page in a browser/playwright, and cropping off the header, footer, and sidebar into 3 graphic elements we could overlay on our page builder (probably ghosted to keep focus on our content)
