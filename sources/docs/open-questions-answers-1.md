RK3 Open Questions

*Created 2026-06-30, for the car ride. These are the calls where your judgment is the bottleneck — the ones I shouldn't be answering by guessing. ★ marks the ones that also unblock current engine work (cycles 2–3).*

**How to use this:** don't try to answer all of them. Pick the ones that spark something. Half-formed answers are gold — even "I keep wanting X" tells me where to steer. Jot, ramble, contradict yourself. The point is to surface what only you can decide so the engine stops drifting on my assumptions.

---

## The three that cascade

If you only think about three things, these are the ones that set the frame for almost everything else.

**1. Who hires RK3, and for the one job?**
Not "who could use it" — who's the specific person, and what's the single job they're hiring it to do? ("A comms person at a foundation who needs the annual report readable + shareable on the web by Friday" implies very different priorities than "an archivist digitizing 10,000 PDFs" or "a designer who wants a first draft to refine.") Almost every tradeoff below resolves differently depending on this answer.

A person working in comms at a nonprofit/foundation who’s been given a large report and told to put it on the web. They know in a month they’ll be asked for a Google analytics report on it, and it sure would be great if the numbers were really good. It’s also great if when it goes out in the newsletter, people say “I saw that report — really good work!” Or when the people in Programs get compliments on the report, and that feedback makes it back to comms. 


**2. When the layout IS the meaning, what wins — fidelity to appearance, or fidelity to information?**
A two-column pro/con, a comparison table, a timeline, a process diagram — here the 2D arrangement *carries* the content. Linearizing it to one web column is faithful to the words but destroys the meaning. So: is the north star "looks like the original" or "means the same as the original, expressed natively for the web"? They diverge constantly, and I need to know which one breaks ties.

Anything that relies on positioning/layout for meaning needs to have that **meaning** preserved. The easiest way to ensure that is to reproduce the appearance. Opportunities usually exist for other ways to preserve the meaning, such as:
- if it’s too small to read, offer a zoom & pan tool
- If it’s a very complex table/matrix, hide data beneath accordions, offer filter options, etc.
- If it’s a diagram, hide information behind popups

One of the best ways to simplify a complex element is to provide options that remove information that doesn’t apply to the user. Ex:
- a matrix of building regulations has a column for the state it applies in. A state filter can reduce the size of the table substantially. 
The caveat is that this isn’t appropriate if the purpose of the element is comparison. Drinking age by state:
Comparison is useful. Name of the head of the dept of transportation: lookup is the goal,  
not comparison.






**3. Faithful, or better-than-the-original?**
Your governing philosophy says "never degrade without approval" — but the dashboard also surfaces *opportunities* with magic-fixes, which implies we sometimes *improve* on the source's information design. Where's the line? If a source is genuinely badly designed (wall of text, weak hierarchy), do we reproduce the mediocrity faithfully, or is there a sanctioned tier where RK3 makes it *better*? And if better — better by whose standard?

> *your notes:*

It’s almost guaranteed that the user is at least moderately familiar with the document before uploading it. When they hit the first conversion screen, we want them to immediately see something they recognize as “their document” with the primary difference being, PDFs generally open showing a zoomed out, hard to read view. We’re always going to be showing readable-sized text and no zooming. 

“It’s my document but I can read it!” Is more likely to matter to them than “it’s my document but with stronger hierarchy!”

That’s the first take. The second take is “oh you have recommendations for how I can make it better?  Let’s see what those are” and from there, we try to meet a range of people’s familiarity with web stuff: I do want a tool to review all images and adjust alt tags, but also a “magic button” for “improve accessibility” where we try to make as many decisions for them as possible. 

Exceptions: changes we’ll make on the first view:
- If important text is hiding in images, we should try to get that out. 



---

## 1. The contract — what "faithful" actually covers

**1a.** Rank these by how much you'd sacrifice the others to keep them: *exact words* · *reading order* · *visual appearance (fonts/color/layout)* · *semantic structure (headings/lists/tables)* · *accessibility*. When two collide, which yields?

> *your notes:*






**1b.** The source uses a low-contrast color (pale gray text) that fails WCAG. Fidelity says match it; accessibility says fix it. Current rubric: match by default, accessibility opt-in. Still right — or should some accessibility floors be non-negotiable?

> *your notes:*

First view: match. Dashboard explains why they should consider adjusting. Again: pick your colors or hit the magic button and we do it. 


**1c.** What's something a conversion could do that would make you say "no — that's a betrayal of the original," even if it looked good? (Defining the *violations* often sharpens the contract faster than defining the ideal.)

> *your notes:*

With very few exceptions, we **don’t** want to make anything “look good” at the expense of fidelity — again, in the first view. 

On some level: if the user knew the value of things like min-contrast colors, they would have done it. The “fixes dashboard” is partly an education tool — we’ll need to explain and almost justify any change we propose making. 

Now, it has to be easy, and quick, or else it feels like a slog to review and approve 50 changes. That’s where the magic buttons come in — one click to best practices. But on first look, if you don’t know what’s happening, forced min-contrast colors read as “they got my colors wrong.”

---

## 2. Reading order & layout ★ (feeds cycle 3 — the column keystone)

**2a.** Two-column page, body text left and right. A **callout/sidebar** floats beside the body. In the linear web version, where does that callout go — right before the paragraph it visually sits next to? After the whole section? Rendered as a visually-distinct aside that "floats" again? What feels right to *read*?

Ideal: sidebar that floats on the same side as the original, with:
- thresholds for
    - Min width: 20% (?)
    - Max width: 50%
    - Min height: none?
    - Max-height: 80 (?) vh
- Options for:
    - Before the text
    - After the text
If it fails the thresholds (ie even at max width it would be too tall) then the default moves to the next option (before text)

Sidebars, pull quotes and callouts play a huge role in these documents and have a rich schema of options.  We should allow org managers (solo account = they’re the org manager) to adjust these thresholds and defaults. 


**2b.** **Pull quotes duplicate body text** (we hit this on Oxfam/Good Food — the quote repeats a sentence already in the flow). Keep both (it's a design echo), or drop the duplicate as redundant on the web? Does your answer change if it's styled as a quote vs. just big text?

Definitely don’t drop. Don’t even suggest or offer it. User would have to pull up a manual “delete” tool to get rid of it.

When we get to importing unstyled text and start suggesting text to become pull quotes, then we can ask if they want to duplicate or not. But if someone else designed it up like that, it stays.


**2c.** When reading order is genuinely ambiguous (no tag tree, messy layout), what should the system do — make its best guess silently, make a guess **and flag it** for review, or stop and ask? You've sanctioned a manual-reorder escape hatch; when is it acceptable to lean on the human vs. when must the engine just be right?

Always guess, and flag if confidence is below some threshold. 

Stop and ask is reserved for capital crimes: broken file, full OCR required, password protected PDF, etc. 


**2d.** Multi-column *magazine-style* body text: reflowing to one column is usually right for the web. Is there ever a case where you'd want columns *preserved*? What signals it?

> *your notes:*

One of our docs has a case: it’s actually a table masquerading as two-column text. No borders or shading, simple header atop each column. And the text doesn’t flow from 1->2 it stops at the bottom. But that’s the only signal other than reading the context. 

Maybe we look at a review tool for “make these two blocks into 2 columns.  Not sure. Relatively rare. 

The key is the intent was to hold up two things and compare them. 

Oh: actually a great use: long columns of names - authors, funders, etc. But now that’s a list masquerading as columns.   But always offer to put lists like that in columns. (And always responsive)


---

## 3. Figures, tables, drop caps ★ (feeds cycle 2)

**3a. Drop caps** (the thing I'm about to fix): a large ornamental first letter spanning 3 lines. In semantic HTML, should it render as a *styled* first-letter (preserve the ornamental intent via CSS), or just fold into normal paragraph text and drop the decoration? It's both a content fix (right now "EDF" loses its "E") and a style call.

Default: preserve via css only. 
User option: remove the decoration. 



**3b. Tables:** always reconstruct as a real semantic `<table>`, even complex merged-cell ones? And what about a thing that's *shaped* like a table but is really an infographic — table, image, or something else?

**3c. Charts/figures:** you've said figures come from the source image, no OCR (except tables). But a bar chart often has the underlying numbers right there. Worth ever reconstructing a chart as live HTML/SVG + a data table, or always just lift the picture? Where's that not worth it?

**3d. Alt text:** first pass = nothing, magic-button later. For the magic pass, what makes *good* alt text here — describe the image literally, or describe the *point it's making* in the document's argument?

> *your notes:*




---

## 4. The human-in-the-loop & the learning system

**4a.** The dashboard serves two masters: **us** (devs improving the engine via clustered flags) and **end users** (cleaning up one doc). Which is primary for the next stretch — and do they even want the same UI?

No, definitely not the same UI. 

Dev dashboard should be the flexi panel setup.

User dashboard will be document-centric and will avoid information overload. Not sure yet what form it will take: tabs, side panel, floating palettes, wizards, etc. 

I definitely need a round of end-user-ux requirements gathering. 


**4b.** In production, does the end user want to **review every doc** before trusting it, or **spot-check** and trust the rest? The honest answer shapes how aggressive vs. conservative the auto-fixes should be.

- 80-90% of users are cuddling their one document (at a time anyway) like it’s their baby. They may have been working on it (whether writing or just participating from comms perspective) for 18 months before they ever bring it into RK3. They will review it closely.
    - Half of them would feel overwhelmed or out of place if they have to answer a lot of questions, especially about semantic tagging or WCAG levels.
    - Half of them know what HTML tags are, what header levels are, and have a prelaunch checklist somewhere asking about minimum contrast levels. 
- I believe there will be 10-20% of users (they’ve evaluated and turned down RK1-2 as too resource-intensive) who are shipped 1-3 report PDFs per week to post online. They manage 3 websites but act like it’s 30. They’ll spend 2 hours customizing their defaults if it shaves 2 minutes off their per-document conversion time. They’ll scrutinize their first 3 documents, and if they don’t find any low-level problems (missing words, extra letter spaces), and they can eyeball a conversion in 30 seconds and be confident it’s clean, they’re a customer for life. 



**4c.** "Fixed" mints an eval assertion (the learning lock). "Accepted" stashes a known-tolerated quirk. Should "accepted" quirks be **per-document** (this PDF is just weird) or **global patterns** (RK3 will always be a bit off on X)? They imply different machinery.




**4d.** Which issue types are safe to **auto-fix without asking**, and which must always be human-approved? (My instinct: missing-space = auto; column-reorder = ask. Where's your line?)

> *your notes:*


---

## 5. AI's role & boundaries

**5a.** Three tiers — none / analysis-only / content-gen. Name the things AI should **never** do in RK3, no matter how good it gets. (The hard boundary is more useful to me than the permissions.)

- Governance issues: never expose private info, etc. normal stuff 
- content issues: 
    - never add or offer any “outside” information (content is discussing affordable housing. I’ll add this stat about housing costs…)
    - Never suggest a significant pivot (this report would be better as a video / 250 pages is 240 pages too long / etc)



**5b.** The reviewer is now a vision model finding issues. Do you foresee ever letting it **auto-disposition** (decide fixed/accepted itself), or is a human always the gate on what counts as resolved?

If the model is sufficiently confident I’m ok with auto action as long as it’s logged and reviewable. 


**5c.** Content-gen creeps: alt text, table-from-image, maybe a TL;DR, maybe inferred headings. Which of these feel *in bounds* as "helping read the original," and which cross into "writing new content the original never had"?

> *your notes:*

**any** content-gen needs to be called out — marked in-place and available for review in a single read. 

I sometimes think we have 2 use cases, one of which is really a superset of the other. 
- 1. Document is a designed PDF and we’re performing conversion
- 2. Document authoring is complete but structure and information design is minimal and needs help
Really, we should view it as one use case with optional passes of enhancement. Someone may want to alter the structure of a designed PDF. And someone could build significant info design into Word. 

So we need to be clearer about what we’re offering to do. Headers is a great example. 

Once we extract headers into an outline, we offer some steps:

- Asses for proper hierarchy 
- Evaluate header and nav lengths
    - By default the headers become the navigation. In cases where docs use long headers, we should suggest they provide a shorter version for the navigation. 
- Measure content length (and potentially screen length) of each section. If above/below some guidelines, either say so or offer to help add/collapse headers. 
    - We need to tread carefully here. Sometimes the user is, organizationally, absolutely forbidden from deviating from the final approved document. They’re the ones driving the “as faithful as possible, but more webby” side. Sometimes they are or are working with the authors and editors and have more leeway. I’d like to be able to set these gates at a per-doc (and potentially per-user/per-org level) like we do with AI.  If they’ve turned off any “might make changes” assistance (really need a better name and definition) then we don’t offer those steps.  

Possible “assistance level” settings (for headings - other elements would have similar appropriate choices)
- shorten/reword headings/navigation
- Add headings to help readers scan (I like this: explain the benefit right in the name of the setting)
- Remove headers on very short sections / combine adjacent short sections into one

These settings inform all 3 routes: the magic buttons, the wizard pass (just made that up. That’s when we walk the user through the document pointing out our suggestions one by one), and the dashboard (big table with filtering and paging — only show suggestions permitted by the settings).  



---

## 6. Scope, sequencing, and the shape of the thing

**6a.** The corpus is "wild PDFs" — reports and whitepapers today. What's *out of scope*, firmly? (Forms? Slide decks? Books? Scanned/OCR-only? Spreadsheets-as-PDF?) Drawing the "we don't do that" line is as valuable as the ambitions.

- Forms. This is not that tool. 
- Slide decks: I’ve seen people design a slide deck with all the elements we’re looking for in these reports. Rare but it happens. 
- I’m fine excluding OCR-dependent files for now, but it’s a discrete enough step that if we saw demand there we could add a pre-import OCR pass. I don’t anticipate it though, and definitely not v1.0
- Spreadsheets: some RK1 “documents” were assembled from 5-10 different sources. We called them recipes. (Get it?) and sometimes one ingredient would be a spreadsheet that we’d read in and convert to a table and flow it in with the document. I honestly don’t know if RK3 will ever head down that route. V1.0 = we won’t test and optimize for spreadsheets but we certainly don’t have to do anything to actively prevent someone from trying. 
- And that’s really the theme: it doesn’t hurt to try importing something far afield from our focus — it’s not like we’re not going to accept a task unless we’re confident it will go well, that’s just a waste of effort. Our focus shows more on where we test and refine than what we accept. 



**6b.** **Word / Google Docs import** decouples us from PDF and changes the architecture. Near-term must-have, or someday? If someday, how much should I avoid PDF-specific assumptions *now* to keep that door open?

Near term. If not 1.0 then 1.1


**6c.** **Landing Page Maker** — is that one product with the converter, or a separate thing sharing parts? Where does it sit against the conversion engine in priority?

Near term plan is to relaunch reportkitchen.com with 3 offerings:

- landing page maker
- RK express (this work — RK3 as self-service offering)
- RK custom (RK1-2 model. Give us your doc and we do it all for you)

Current plan is to launch LPM and Custom, and say Express is coming soon. 

LPM and Express share the platform - the only difference is the users permissions. I very much hope LPM customers upgrade to being RK3 customers. 

**6d.** The north-star UX (2026-dynamic, no-reload editing, real-time collab). How much of that is needed for a *first* real version vs. the long horizon? What's the smallest version that would still feel like "2026, not 2016"?

> *your notes:*

Realtime collab is definitely v2.0+
Other than that we’re on the right track, although we haven’t even spec’d out the end-user UX yet.  It will lean more fluid than the dev UX but not radically so. 

---

## 7. Done, and good enough

**7a.** Describe a *perfect* conversion of one document in one sentence. (Pixel-faithful? Information-faithful? Better-than-original? The adjective you reach for first is telling.)

“This looks just like my document, but webified and more interactive.”

And that’s a comms persons words not a capital-D Designer. 

**7b.** The vision-QA loop exists to end your hand-proofing. What would the dashboard have to show — what threshold of "clean" — for you to actually *trust* a conversion without eyeballing it yourself?





**7c.** A year out, RK3 is a clear success. What's the headline — the one sentence a happy user says about it?

> *your notes:*

Bears repeating:

“This looks just like my document, but webified and more interactive.”

But I’ll add some more:
- This AEO guy tried to sell me his services. When I gave him our report’s URL to scan he said “never mind, you don’t need me.”
- We used to get one line per document in our analytics report: 15 downloads this month. Now we have a full report of which pages people are reading, and it’s 10x the volume it was before.

And here’s the phrase that convinced me to start RK1: “These reports often don’t have the policy uptake that they should.”

And that’s the ultimate, final goal for all of RK: help the people who want to change the world, do it. 

---

*When you're back: hand me whatever you wrote (even fragments), or just tell me the three that mattered most. I'll fold the answers into the rubric + the reading-order doctrine, then pick up cycle 2.*

