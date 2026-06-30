# User options

We are beginning to encounter questions of conversion that truly are a matter of preference - retaining or deleting design elements, handling indents etc.

We have "converter options" but we need a more unified way of handling these, including:
- document-wide preferences, like "use embedded fonts"
- clustering (if there's a header question, show the question on every header but once it's answered it's answered for all)
- admin overrides (don't allow this doc to use or even ask about embedded fonts)
- might be good to keep a log of changes and allow "undo" or something

I also want a map of these options: what's the universe of situations that could trigger the questions, what's the text of the question and answers, etc.

I also want to keep stats of the final answers: how many times did X feature have the default accepted vs. overruled.  Won't matter until we get more users in but good to plan.

## cf: feedback
the feedback popup is intended only for development and for tuning the converter.

Yet the UX offers some options that belong in this end-user-options UX -- namely, edit, change element, remove element.  I want to add:
- toggle a paragraph from honoring hard-returns to removing them.


## Converter questions bugs:
- choosing the non-default doesn't take any effect
- right column shows answered, yet opening it in the icon shows the other answer.


## Other options
- Pick a font to substitute, instead of either embedding or trying to reference google.