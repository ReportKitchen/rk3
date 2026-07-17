# AI content sections — the block-model reframe (content-first, verbatim-first)

**Status:** SHIPPED 2026-07-17 (owner-approved). Backend engine + renderer
primitives + full Assemble/Wordsmith UI rewire all landed and screenshot-verified
on Oxfam + teacher-prep. Replaces the fixed block catalog
(execSummary/highlights/findings/toc/storytelling/…) with **AI-identified semantic
sections**; supersedes the Highlights-vs-Findings split.

## What shipped
- **Engine** — `rk3/landing/sections.py` (`generate` + `fallback`), schema, prompts
  `shared.analysis.sections_*`, `GET/POST /api/landing/{slug}/sections`.
- **Renderer** — `Section` component in `LandingRenderer.jsx` (type `section`) +
  relative-unit primitive CSS in `landingPage.css` (`.lp-sec-*`; em/%, currentColor
  — so exported sections adopt the host site's type/colour). Export parity via the
  existing `landingPage.css?raw` bundling.
- **UI** — `app/ui/src/landing/assemble/`: `AssembleMaker` loads `/sections` +
  holds section state; `SectionLibrary` (**Highlights** = the AI sections, the
  star + **Call to action**); `Inspector` renders the real primitive "as it will
  appear" + presentation adjust (quote standard⇄pullquote) + add/remove;
  `Controls` rough page from the on-sections; `Wordsmith` renders the sections
  page editable. Copy in `content/lpm/sections.yml`. Retired `BlockLibrary` +
  the old catalog model.
- **"YOUR WORDS" badge** surfaces `verbatim:true` on every section (trust signal).

## Follow-ups (not yet done)
- Section reorder (drag) — cards are toggle/select only.
- Persist the assembled config to `.landing.json` (Wordsmith edits still live in
  the DOM only; no structured write-back).
- Cover `beside`/`inset` float treatment (currently the cover leads full-width for
  every layout except text-forward).
- Presentation swaps beyond quote pull (e.g. offer bullets⇄statCards where a
  section's content supports both — needs the engine to emit both shapes).
- AI-summary-as-alternative-intro (the one rewritten-voice block) as an opt-in.

---
### Original decision record (kept for reference)

## Why (the trigger)
Two problems, one root. On the Oxfam Davos doc the Highlights *card note* said
"the four ways corporate power fuels inequality" but the *bullets* were five
unrelated stats — because the **advisor** (`guidance.py`, writes the notes) and
the **author** (`ai.py`, writes highlights) are separate AI passes that never
meet. And Highlights vs Findings turned out to be the *same facts twice* (prose
bullets vs number cards). Fixed buckets force the document into our shapes; a
content-first, AI-wired tool should let the document define its own shapes.

## The model: scaffolding + sections
Two layers.

1. **Structural scaffolding — fixed, few.** Title, Cover, Summary (the intro),
   CTA row (download / secondary / share). Page plumbing; stays a fixed catalog.
2. **Content sections — AI-identified, semantic, ordered.** The AI reads the whole
   doc and proposes the meaningful units of *this* document. Each section:
   - `heading` — the document's *own* framing ("The four ways corporate power
     fuels inequality", "Steps you can take to combat climate change", "Who we serve").
   - `summary` — one line of intent (this drives the guidance note, so **note ↔
     content can't disagree** — same pass authored both).
   - `presentation` — one of a small fixed vocabulary (below).
   - `content` — shape depends on the presentation.
   - `page`, `strength` (strongest|solid|thin), `verbatim` (bool).

Highlights + Findings collapse into `bullets` vs `statCards` presentations of a
key-points section; Storytelling becomes a `quote` section. Dedupe across sections
so a fact isn't shown twice.

## Presentation primitives (fixed, whitelisted)
Kept small so rendering, export, and Wordsmith stay consistent:
- `prose` — verbatim paragraphs (the exec-summary shape).
- `bullets` — the doc's own key points, lightly trimmed.
- `statCards` — big number + the fact it proves (the Findings shape).
- `quote` — a verbatim pull-quote + attribution; **variant `pull`** = big
  quotation-mark pullquote vs standard formatting (owner asked for this toggle).
- `steps` — ordered actions ("Steps you can take"), the doc's own step language.
- `table` — deferred to v2 (table extraction is its own problem).

The **middle card (Inspector)** lets the user adjust the presentation per section
(bullets ⇄ statCards where both fit; quote standard ⇄ pullquote).

## Hard constraints (owner)
- **Verbatim-first — "that feels just like my document," not a heavy-handed
  rewrite.** Every section pulls the document's *own words* — select, order, lightly
  trim. NO paraphrase/rewrite. The **one** exception is the opt-in `aiSummary`
  scaffolding block (an explicit AI-voice pitch). `verbatim:true` on everything else.
- **Relative, adaptable CSS (renderer).** Section styles use relative units so the
  exported page adopts the *target site's* CSS: font-size in em multipliers
  (0.8em / 1.2em, not px), blockquote indent in %, inherit font/color. No precise
  pixel type scale. This is what makes a section "drop into" the client's page.
- **Functional no-AI version.** Without AI: extract the exec summary as a `prose`
  section, plus a few *canned recommendation* placeholder sections ("Try to find a
  compelling story in your report and add it here"). Degraded but usable; the AI
  path is the star.
- **Keep the app working during the migration** — build sections additively
  (`rk3/landing/sections.py`, `/api/landing/{slug}/sections`), verify on real docs,
  then rewire Assemble/Inspector/Controls/Wordsmith and retire the old
  highlights/findings/guidance-blocks split.

## Build order
1. **Backend generator** (this slice): `sections.py` + content prompts
   (`shared.analysis.sections_*`) + schema + endpoint + no-AI fallback. Verify the
   verbatim-ness and section quality on Oxfam + teacher-prep.
2. **Renderer primitives** with relative CSS (extend `LandingRenderer` + a new
   `sections.css` of em/%-based rules).
3. **UI rewire**: Assemble left = the AI's proposed sections (+ scaffolding);
   Inspector = per-section presentation adjust + verbatim preview; retire the fixed
   catalog cards, Highlights/Findings split, and the advisor/author disconnect.

## Contract sketch (subject to change in the build)
```
{ documentRead:{whatItIs,audience,coreMessage},
  recommendedPage:{length(short|middle|long), cover(onTop|beside|inset|textForward)},
  sections:[ { heading, summary, presentation, page, strength, verbatim,
               prose, bullets[], cards[{value,label}], quote{text,attribution,pull},
               steps[{label,body}] } ] }   // one content field filled per presentation
```
