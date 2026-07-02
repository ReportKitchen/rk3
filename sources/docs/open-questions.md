# Open Questions — for thinking / writing

*Created 2026-06-30, for the car ride. These are the calls where your judgment is the bottleneck — the ones I shouldn't be answering by guessing. ★ marks the ones that also unblock current engine work (cycles 2–3).*

**How to use this:** don't try to answer all of them. Pick the ones that spark something. Half-formed answers are gold — even "I keep wanting X" tells me where to steer. Jot, ramble, contradict yourself. The point is to surface what only you can decide so the engine stops drifting on my assumptions.

---

## The three that cascade

If you only think about three things, these are the ones that set the frame for almost everything else.

**1. Who hires RK3, and for the one job?**
Not "who could use it" — who's the specific person, and what's the single job they're hiring it to do? ("A comms person at a foundation who needs the annual report readable + shareable on the web by Friday" implies very different priorities than "an archivist digitizing 10,000 PDFs" or "a designer who wants a first draft to refine.") Almost every tradeoff below resolves differently depending on this answer.

> *your notes:*


**2. When the layout IS the meaning, what wins — fidelity to appearance, or fidelity to information?**
A two-column pro/con, a comparison table, a timeline, a process diagram — here the 2D arrangement *carries* the content. Linearizing it to one web column is faithful to the words but destroys the meaning. So: is the north star "looks like the original" or "means the same as the original, expressed natively for the web"? They diverge constantly, and I need to know which one breaks ties.

> *your notes:*


**3. Faithful, or better-than-the-original?**
Your governing philosophy says "never degrade without approval" — but the dashboard also surfaces *opportunities* with magic-fixes, which implies we sometimes *improve* on the source's information design. Where's the line? If a source is genuinely badly designed (wall of text, weak hierarchy), do we reproduce the mediocrity faithfully, or is there a sanctioned tier where RK3 makes it *better*? And if better — better by whose standard?

> *your notes:*


---

## 1. The contract — what "faithful" actually covers

**1a.** Rank these by how much you'd sacrifice the others to keep them: *exact words* · *reading order* · *visual appearance (fonts/color/layout)* · *semantic structure (headings/lists/tables)* · *accessibility*. When two collide, which yields?

**1b.** The source uses a low-contrast color (pale gray text) that fails WCAG. Fidelity says match it; accessibility says fix it. Current rubric: match by default, accessibility opt-in. Still right — or should some accessibility floors be non-negotiable?

**1c.** What's something a conversion could do that would make you say "no — that's a betrayal of the original," even if it looked good? (Defining the *violations* often sharpens the contract faster than defining the ideal.)

> *your notes:*


---

## 2. Reading order & layout ★ (feeds cycle 3 — the column keystone)

**2a.** Two-column page, body text left and right. A **callout/sidebar** floats beside the body. In the linear web version, where does that callout go — right before the paragraph it visually sits next to? After the whole section? Rendered as a visually-distinct aside that "floats" again? What feels right to *read*?

**2b.** **Pull quotes duplicate body text** (we hit this on Oxfam/Good Food — the quote repeats a sentence already in the flow). Keep both (it's a design echo), or drop the duplicate as redundant on the web? Does your answer change if it's styled as a quote vs. just big text?

**2c.** When reading order is genuinely ambiguous (no tag tree, messy layout), what should the system do — make its best guess silently, make a guess **and flag it** for review, or stop and ask? You've sanctioned a manual-reorder escape hatch; when is it acceptable to lean on the human vs. when must the engine just be right?

**2d.** Multi-column *magazine-style* body text: reflowing to one column is usually right for the web. Is there ever a case where you'd want columns *preserved*? What signals it?

> *your notes:*


---

## 3. Figures, tables, drop caps ★ (feeds cycle 2)

**3a. Drop caps** (the thing I'm about to fix): a large ornamental first letter spanning 3 lines. In semantic HTML, should it render as a *styled* first-letter (preserve the ornamental intent via CSS), or just fold into normal paragraph text and drop the decoration? It's both a content fix (right now "EDF" loses its "E") and a style call.

**3b. Tables:** always reconstruct as a real semantic `<table>`, even complex merged-cell ones? And what about a thing that's *shaped* like a table but is really an infographic — table, image, or something else?

**3c. Charts/figures:** you've said figures come from the source image, no OCR (except tables). But a bar chart often has the underlying numbers right there. Worth ever reconstructing a chart as live HTML/SVG + a data table, or always just lift the picture? Where's that not worth it?

**3d. Alt text:** first pass = nothing, magic-button later. For the magic pass, what makes *good* alt text here — describe the image literally, or describe the *point it's making* in the document's argument?

> *your notes:*


---

## 4. The human-in-the-loop & the learning system

**4a.** The dashboard serves two masters: **us** (devs improving the engine via clustered flags) and **end users** (cleaning up one doc). Which is primary for the next stretch — and do they even want the same UI?

**4b.** In production, does the end user want to **review every doc** before trusting it, or **spot-check** and trust the rest? The honest answer shapes how aggressive vs. conservative the auto-fixes should be.

**4c.** "Fixed" mints an eval assertion (the learning lock). "Accepted" stashes a known-tolerated quirk. Should "accepted" quirks be **per-document** (this PDF is just weird) or **global patterns** (RK3 will always be a bit off on X)? They imply different machinery.

**4d.** Which issue types are safe to **auto-fix without asking**, and which must always be human-approved? (My instinct: missing-space = auto; column-reorder = ask. Where's your line?)

> *your notes:*


---

## 5. AI's role & boundaries

**5a.** Three tiers — none / analysis-only / content-gen. Name the things AI should **never** do in RK3, no matter how good it gets. (The hard boundary is more useful to me than the permissions.)

**5b.** The reviewer is now a vision model finding issues. Do you foresee ever letting it **auto-disposition** (decide fixed/accepted itself), or is a human always the gate on what counts as resolved?

**5c.** Content-gen creeps: alt text, table-from-image, maybe a TL;DR, maybe inferred headings. Which of these feel *in bounds* as "helping read the original," and which cross into "writing new content the original never had"?

> *your notes:*


---

## 6. Scope, sequencing, and the shape of the thing

**6a.** The corpus is "wild PDFs" — reports and whitepapers today. What's *out of scope*, firmly? (Forms? Slide decks? Books? Scanned/OCR-only? Spreadsheets-as-PDF?) Drawing the "we don't do that" line is as valuable as the ambitions.

**6b.** **Word / Google Docs import** decouples us from PDF and changes the architecture. Near-term must-have, or someday? If someday, how much should I avoid PDF-specific assumptions *now* to keep that door open?

**6c.** **Landing Page Maker** — is that one product with the converter, or a separate thing sharing parts? Where does it sit against the conversion engine in priority?

**6d.** The north-star UX (2026-dynamic, no-reload editing, real-time collab). How much of that is needed for a *first* real version vs. the long horizon? What's the smallest version that would still feel like "2026, not 2016"?

> *your notes:*


---

## 7. Done, and good enough

**7a.** Describe a *perfect* conversion of one document in one sentence. (Pixel-faithful? Information-faithful? Better-than-original? The adjective you reach for first is telling.)

**7b.** The vision-QA loop exists to end your hand-proofing. What would the dashboard have to show — what threshold of "clean" — for you to actually *trust* a conversion without eyeballing it yourself?

**7c.** A year out, RK3 is a clear success. What's the headline — the one sentence a happy user says about it?

> *your notes:*


---

*When you're back: hand me whatever you wrote (even fragments), or just tell me the three that mattered most. I'll fold the answers into the rubric + the reading-order doctrine, then pick up cycle 2.*
