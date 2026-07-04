# Scratchpad - Don't rely on anything in here to be accurate in any way.

## review signals in doc HTML

>  I'd only re-rendered Tenure and Invest with the outline feature; every other doc's HTML predated it

Drop a note somewhere -- when we touch this work next, lets move review artifacts out of the doc's HTML and inject them with JS onto elements, matching by id.



My impressions:
- I wasn't looking at fields closely -- most were missing a lot.  I decided to focus on "have I found a ___" rather than "did I extract all the pieces correctly."  I believe the second needs a lot more work.
- recommendations never seems very meaningful
- stats is noisy with some prime culprits: years and dates, law/bill numbers, money/funding
- entity hits with high accuracy.  I'm excited to see what we can do with relationships.  "here's a graph linking the people, orgs, initiatives, partnerships, places, funding, legislation, etc" in this report.
- quotations was pretty accurate too, but i didn't see it collecting the speakers very often.  note, quotes often include the speakers organization -- more pieces to connect with entities.



patterns round 2

Pattern agent did another round and I'm reviewing more docs.  
The very first one:


> “Over more than 35 years, Enterprise has created 662,000 homes, invested nearly $53 billion and touched millions of lives.”

previous "funding" patterns were always X gave to Y org.  This is "We've invested X into the communities we serve," and that's separate, and powerful. 

ALSO, we NEED a pattern for "Accomplishments."

> created 662,000 homes

that's not a stat.  Thats an accomplishment/achievement that this org did.  when?

> Over more than 35 years

how many people did you impact?

> millions of lives

ok, that's not great, but you see the potential in the pattern.

This is good, good stuff.  Should we bake this in now, or should I keep reviewing?

GOOD GRIEF!!  The second one:

> “Estimates place the current capital backlog of needed physical repairs and renovations at close to $70 billion,39 increasing by approximatel”

That's my "need" right there.

IT CONTINUES

  The list below details additional programs managed by HUD that advance the preservation and production of affordable housing.

  Community Development Block Grant (CDBG) Programs: One of HUD’s longest running programs, the CDBG program provides annual grants to states and local jurisdictions, including cities

That's a resource.  these documents LOVE collecting "resources" 
Can't tell you how many resource database I've built.



----
process_step_list: this often just finds normal lists.  Is that ok?  Process and step are throwing me.





--------

New pattern:


in their own words

I don’t believe I’m taken as seriously in the workplace because I am a young woman of color. I often question things, which doesn’t always go over well in majority-white organizations. I’ve been used as a ‘token’ brown person.”

—Pakistani Woman


"in their own words" is what this report calls its quote boxes.  this is a common pattern.  "Digging Deeper" or "Policy in action" are other examples.

Authors use these words.  They'll say "I want all the in their own words to be red". So recognizing them will be key.  Also, understanding this pattern can help when we make proposals about jazzing up a black-and-white document.  This is the kind of "experienced designer touch" we need.


----

stats are finding numbers inside figures.  until we get figures right it's hard to know if the patterns is good or not.

----


  The 2025 Survey, conducted in collaboration with EVITARUS and Ambit 360 Consulting, explored how nonprofits are faring in today’s changing environment and the investments needed to secure their long-term futures. From January 30 to March 14, 2025, we asked US nonprofit leaders a series of closed- and open-ended questions to understand the management, operational, and financial picture they navigated in 2024 and anticipated in 2025. Topics included government and foundation funding, workforce well-being, and the implications of recent events – such as the 2024 election, climate emergencies, and federal court system rulings.

Extracting insights from surveys and polls would be a thing.  Seems hard though, and not quite ready to try to find them without LLM support

-----

impact statement: (aka accomplishment/achievement)

Nonprofit Finance Fund® (NFF®) is a nonprofit lender, consultant, and advocate. For more than 40 years, we’ve helped organizations access the money and resources they need to realize their communities’ aspirations. Alongside others, we’re working to build community wealth and well-being and put affordable housing, essential services, quality jobs, and excellent education within reach of more people.


---

“A total of $330 million of known funding went to air-quality projects between 2015 and 2022.”

Our research identified 79 foundations as having provided funding for air-quality initiatives between 2015 and 2022


“The average grant size from CEE foundations between 2015 and 2022 was $234,809.”


that's not funding_event right?  impact?