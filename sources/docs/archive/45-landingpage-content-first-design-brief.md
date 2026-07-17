# Landing Page Maker — Content-First Redesign Brief

**For:** Claude Design (who built our design system)
**From:** product + eng
**Purpose:** mock up the key screens for a re-centered version of the Landing Page Maker (LPM).

---

## 0. Scope & guardrails — read first

- **This is a CONTENT / LAYOUT / UX round. NOT colors, type, or visual styling.** Those are locked: use the existing design system. Do **not** propose new palettes, fonts, or a fresh visual language. If a screen needs a card, a badge, a button — pull it from the kit.
- We're deciding **what's on the screen, how it's organized, and how the flow feels** — not how it's painted.
- Reuse the existing block set and design-system components wherever possible. The novelty is in *organization, guidance, and flow*, not new chrome.

---

## 1. The repositioning (the "why", so the screens have a spine)

We are **not** a page builder. Not Gutenberg, not Elementor. Every hour we spend on style controls (leading, sidebars, floats, color pickers) is an hour spent on a problem our users don't have.

**Our user:** someone making a *single, simple page* who is stuck because they don't know **what content belongs on it** — not because they can't choose a line-height.

**Our value:** editorial guidance. We understand the communication needs of *this* report and help the user assemble the *right content elements in the right order*, with an opinion at every step.

So the redesign pulls hard toward **content and guidance**, and pushes styling into **sane, invisible defaults**. The whole tool should feel like a smart editor sitting next to you, not a canvas full of knobs.

Design north star: **"help me decide what to say," not "help me design a page."**

---

## 2. Core flow — two modes

The product splits into two clearly separated modes. The split is the whole idea: **decide, then polish.**

### Mode A — **Assemble** (content-first, guidance-heavy)
The star of the show. This is where our value lives.

- The screen is **mostly us**: bucketed block library + big instructional cards. Guidance takes up real estate.
- The page **preview is small and deliberately rough** — indicative, not pixel-perfect. This is a *feature*: it keeps the user out of the design weeds and keeps the text feeling like a draft they can freely change (not a finished artifact they're afraid to touch).
- The user **picks content elements from buckets**; each drops into the page outline already **drafted from their PDF** (our extraction/AI fills it). They accept / reorder / remove — guided by an opinion on each element.
- Layout is a **single small choice**: one of a few cover-centric presets (see §5). Not a design panel.

### Mode B — **Wordsmith** (light text cleanup)
Deliberately dumb and reliable.

- Now the page opens up into a **larger, readable, closer-to-final view**, and the user reads top-to-bottom and **fixes wording** — a typo, a name, tightening a sentence, bolding a phrase.
- **This is a simple pass on essentially plain text.** No block library, no style controls. Editing must feel like **second nature** — click a line, change it.
- Because it's a separate, simple pass, it does **not** need a heavy rich-text editor. Bold / italic / lists / links. (Eng note: this is intentional — we are not building or chasing a CKEditor-class RTE. Keep the editing surface boring and dependable.)
- Clear path **back to Assemble** to change structure.

**Mock both modes and the hand-off between them.**

---

## 3. Block library — buckets + big instructional cards

Keep the existing block library as the starting point, but make each block **much bigger** and **fill it with helpful instruction.** The block card is where our editorial opinion shows up.

### Organize blocks into three buckets

**INTRO** — how the page opens / frames itself
- **Exec Summary** — the report's own words, verbatim. Trustworthy; can run long.
- **AI Summary** — Claude writes a punchy pitch in a voice you choose (report intro / neutral / hard sell). Great as a fast hook.
- *(pick one, usually)*

**EVIDENCE** — why the reader should believe / care
- **Highlights** — 3–5 key points as bullets. Good for nuance that isn't purely numeric.
- **Findings/facts/figures** — headline stats: a big number beside the fact it proves. Best when your punch is quantitative.
- **Table of Contents** — signals depth and scope; shows there's a real report behind the page.
- **Storytelling** — *(NEW block)* surface a real person's story pulled from the report. Nothing builds trust like a human example. Best when the work is about people, not just policy. *(Eng: new extraction target — personal narratives / anecdotes / named-person quotes.)*

**CTA** — what you want the reader to do
- **Download** button (the PDF), **Secondary** button (donate / subscribe / contact), **Social share** (buttons + links). This bucket is about *arranging* the actions and social links.

**Page fundamentals (always present, not "picked" from a bucket):**
- **Title / headline** — the page always has one.
- **Cover image** — always present and it *drives the layout* (see §5), so treat it as a page-level thing, not a body block.

### What a block card must carry (the instructional part)
Each card in the library should be roomy enough to hold, at a glance:
1. **Name** + small icon
2. **What it is** — one plain line
3. **When to use it** — the opinionated line ("Best when…", "Reach for this if…")
4. A tiny **structural thumbnail** of the block's shape

And an **expanded / hover state** with a sentence or two of **"what to think about"** (e.g., Findings: *"If your key points are more nuanced than numeric, use Highlights or a Summary instead."*).

**Please mock the card in default + expanded state for ~3 examples** so we can feel the density and voice: **Findings**, the new **Storytelling**, and **Exec Summary vs AI Summary** side-by-side (to show how we help users choose between two similar options).

Voice for the guidance copy: **plainspoken, specific, opinionated.** Talk like a smart colleague, not a manual. Example: *"You've got four hard numbers — a Findings block will land harder than burying them in a paragraph."*

---

## 4. Templates → **short / middle / long** (content depth)

Retire the old archetype templates (Research Article / Campaign / Annual Report / Minimal) — the differences between them were never obvious. Replace with **three length presets** that map to *how much you want to say*:

- **Short** — the essentials. Intro + CTA. **No evidence section.** For a fast, skimmable teaser.
- **Middle** — Intro + one evidence element + CTA, with **content sections capped at ~X words**. The balanced default.
- **Long** — the full pitch: full exec summary, multiple evidence elements, everything uncapped.

Templates are about **content depth**, and they pre-select which blocks appear and how much text each holds. **Mock how the user picks / switches short–middle–long, and what each one promises** (a one-line "what you get").

---

## 5. Layout — a few **cover-centric presets** (and how it stays KISS with length)

Layout is a **small, separate, always-available choice**: 3–4 shapes, **all built around the cover image.** This replaces manual float/width fiddling (dropping a cover at 100% width looks ridiculous; floating it by hand is not obvious). Make it a **pick**, not a puzzle.

Proposed presets (designer to refine — aim for ~4 named shapes):
1. **Cover on top** — cover leads, content stacks below.
2. **Cover beside** — cover to one side of the intro, content flows next to it (offer **left / right**).
3. **Cover inset** — cover smaller, nested within the opening content (the "floated cover" done *for* the user, sized sensibly).
4. **Text-forward** — cover minimized to a small thumbnail (or omitted) for pages that lead with words.

Cover element should have room for some metadata like "date published, authors" etc to ride along with it.

Show these as a **small visual picker** (thumbnails of the shape) plus **one or two applied in the preview.**

### Resolving "how do length templates and layout templates interact?" — KISS
Keep them **orthogonal and each a single simple pick**:
- **Length** (short/middle/long) = *how much content* — the starting choice.
- **Layout** (cover preset) = *how the cover is arranged* — a small always-available toggle.

**No length × layout grid, no combinatorial templates.** You choose a length to decide depth, and a cover shape to decide arrangement, independently. Please mock this so the two coexist without reading as *two competing template systems* — one clearly about "how much to say," the other about "how the cover sits."

---

## 6. Screens to mock (the concrete deliverable for this round)

1. **Assemble — main screen.** The three buckets (Intro / Evidence / CTA) as big instructional cards; the assembled page as a **small, deliberately-rough preview**; the **length control** (short/middle/long); the **cover-layout picker**. The emphasis must read as *guidance-forward* — our tips and explanations occupy more of the screen than the preview does.
2. **Block card close-up** — default + expanded/hover, for **Findings**, **Storytelling**, and **Exec Summary vs AI Summary**. This is where our editorial voice shows.
3. **Wordsmith — main screen.** The page shown **larger and readable**, plain top-to-bottom inline text editing, minimal chrome, an obvious **"← back to Assemble."**
4. **Cover-layout presets** — the 3–4 cover shapes as a chooser, plus one or two shown applied in the preview.
5. *(nice to have)* **Length starter** — how short/middle/long are presented as the opening choice, with a one-line promise for each.
6. *(nice to have)* **Storytelling block, rendered** — what a pulled human story looks like on the page (quote + short narrative + attribution?).

---

## 7. What we're deliberately cutting / de-emphasizing (so it doesn't sneak into the mocks)

- **Per-block style controls** — color pickers, width sliders, all-caps toggles, sidebar toggles, float sliders. Gone from the primary flow.
- **The pixel-accurate live editing canvas** as the main surface. Assemble's preview is intentionally small/rough; Wordsmith's is readable but still not a design tool.
- **"Copy my site" style-cloning + header/footer/sidebar ghosting** — impressive, but it answers a *design* question ("look like my site") when our value is content. **Demote it to an optional, later "match my brand" step — or leave it out of these mocks entirely.** Default look is clean black-on-white Public Sans.
- Anything that makes us feel like Gutenberg or Elementor.

---

## 8. Open questions for design to explore

- **Assemble's proportions:** how big can the guidance get before the small preview stops being useful as an anchor? Where does the eye go first?
- **Discoverability of Wordsmith:** does the user flow Assemble → Wordsmith linearly (a "next" step), or toggle freely? Show your recommendation.
- **The bucket picker vs. the page outline:** one panel or two? How does "pick from a bucket" become "a block in my page" — drag, click-to-add, a menu?
- **Choosing between similar blocks** (Exec vs AI Summary; Highlights vs Findings): can the card layout itself do the teaching, or do we need a tiny "which should I pick?" moment?
- **Empty / first-run state:** what does Assemble look like the instant a doc lands, before the user touches anything? (It should already be a sensible drafted page.)

---

*Reminder: content / layout / UX only. Colors and fonts are set — use the kit.*
