# font weights
OK separate from semantic bold/italic, we want to translate the overall type sizes and weights as best we can. 

One option is to extract the fonts from the PDF and use fontTools to inspect the font to determine its weight (and possibly bold and italic as additional signals?)

Another signal could be PDF FontDescriptor metadata.

Is it possible to run a quick spike to determine if this data exists and is accurate?

Another option is to extract the fonts from the PDF and use the actual fonts via @font-face. If we try this it needs to be optional, since that won't always be the best path or the one users would expect, but if it produces good results it could work.  I'm not concerned about licensing because we can solve that with a simple note and disclaimer: If this font is licensed it's on you to make sure you have the rights to web-serve it.  But between you and me, and this isn't normally how I like to run things, but a first impression that looks rock-solid goes a long way, and any disappointment in loss of fidelity when switching off "use the PDF's fonts" can be dealt with later -- it's as simple as hand-adjusting weights of classes, but at least that effort is deferred until after we've made a good impression.


# font specs cache
would it make any sense to start a library of font names and attributes like weight and italic, and track cases where we don't have enough information and need some manual input?  Recall that the vision is for an organization to use this to convert multiple documents, and there's every chance one org uses a small number of fonts, so X font doesn't have the info we need, and we or they supply it manually, that's a one-time fix.  also, would it make sense as a system-wide cache of font metadata so potentially we could skip extracting the font and doing the fontTools measurement?  possibly adding some hash to ensure we don't get caught by different fonts that have the same internal name?  and/or would caching results of the glyph testing add any value?