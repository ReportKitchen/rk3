# design pattern schema

I feel completely unprepared to spec this out.  I'm absolutely confident that it will change and grow.

Can we make this a directory of markdown files to start? I need visibility into it and possibly to make some additions/adjustments.  It definitely can't live in code, although, I can absolutely see -- maybe just for now or maybe forever -- that within a directory for a pattern could be some JS or python files containing code for operating on the elements.  We'll also need output templates for outputting the extracted IR version of an element when we're building.  It "feels good" to me to imagine some code and some twig files sitting in these directories, along with LLM prompts, markdown for "encyclopedia pages" and more.  

Is this a nightmare waiting to happen?

I'd also want to build (at least) two gardening tools up front:
- a web-view inventory/browser, showing the patterns and all the content that lives with each
- some QA, like ''4 patterns have a section for "how to identify this in the wild" while 3 don't have that section'', or "2 patterns have this section as YAML and 2 have it as JSON -- that don't seem right"

Maybe this QA step can build an actual schema along with it -- adding entries for things it finds, then you or I can mark entries in the schema with further validation information (this is required, this is optional, this markdown is for humans, this markdown is a prompt)
