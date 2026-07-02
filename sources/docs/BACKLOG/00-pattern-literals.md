# Pattern literals

we have cases like this

    TOC_TITLE = re.compile(
    r"(table of )?contents|what.?s inside|in this (report|issue|guide)") 

There are no doubt other text patterns people use for their TOC. We should learn, either in a dedicated training pass, or passively as we go

Also Note: other languages exist...

- Pull out all instances where we use literal words like this into json/YAML files where they can be inspected and updated (and/or translated)
- Back burner a method of learning more examples based on reading more documents