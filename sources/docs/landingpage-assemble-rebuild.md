# LPM Assemble/Wordsmith rebuild — executable plan (content-first pivot)

**Status:** backend DONE + **UI DONE** through **Preview** (2026-07-18). The Puck
LPM is retired. Design was LOCKED in `design-system/round-2/`. NOTE: the block
model described below was superseded by the AI-sections model (BACKLOG/61) —
sections engine + presentations replaced the fixed catalog; drag-reorder and
persistence (`.landing-assembled.json`) have since shipped too.

## UI BUILT — where it lives
- **`app/ui/src/landing/assemble/`** — the bespoke Assemble/Wordsmith React:
  `AssembleMaker.jsx` (default export, mounted in DocumentView), `Chrome.jsx`
  (three-step stepper: Assemble → Wordsmith → **Publish**),
  `SectionLibrary.jsx` (left), `Inspector.jsx` (center), `Controls.jsx` (right),
  `Wordsmith.jsx` (contentEditable + floating toolbar), `Preview.jsx` (the
  finished page in an isolated iframe srcdoc — its own head/CSS/fonts — with a
  desktop/mobile width toggle; narrow windows ZOOM the page via transform
  scale, never reflow), `Publish.jsx` (the dedicated export surface, two
  centred card columns: LEFT = the promotion kit — the **social graphic** (the
  PDF cover reformatted to a 1200×630 card by the social-post engine's
  `openai-reformat` pathway, warmed in the background when Assemble loads the
  sections, whisk-in-place while cooking) with the PDF-cover ⇄ social-graphic
  share-image toggle (persisted `shareImage`), and the **social posts** — 4
  weekly promo posts from the SAME sections pass, per-post Copy + "include as
  Word file" checkbox (persisted `socialDoc` → `social-posts.docx` via
  `socialDocx.js`, minimal OOXML on JSZip); RIGHT = **Copy-and-paste into a
  CMS** (an inline-styled fragment in a copy box — `rk3/landing/inlinecss.py`
  resolves every var() to concrete values then folds the stylesheet in via the
  `css-inline` package (venv dep, no manifest), `POST /api/inline-css`;
  fragment = the .lp-page div carrying the body styles, absolute asset URLs)
  and **Download full page** with an Embedded ⇄ Inline-styles stylesheet
  choice (persisted `dlStyle`)),
  `model.js`, `icons.jsx`, `assemble.css` (`asm-*` classes on `--rk-*` tokens).
- **`app/ui/src/landing/finalHtml.js`** — the ONE final-page builder (Preview
  iframe + export zip both call it): renders the config, re-applies Wordsmith
  edits (shared `editSignatures`), retargets edited asset URLs per context, and
  writes the full document head (title, meta description from the first prose
  section, og:title/description/image + twitter card, inlined `landingPage.css`,
  `--lp-accent`). NO web font — the page uses the system stack (Helvetica,
  Verdana, sans-serif; owner 2026-07-18: Public Sans was a pointless dependency
  when the goal is adopting the host's styling). `exportZip.js` builds the
  self-contained zip (index.html + images/ + the PDF when bundle-mode) on top.
- **Mounted:** `DocumentView.jsx` lazy-imports `AssembleMaker` for `tab==="landing"`.
- **Retired (deleted):** LandingMaker/puckConfig/LandingShell/MiniPreview/puckAdapter/
  landingOptions/blockLibrary/RichText + `@measured/puck` + `react-simple-wysiwyg` deps.
- **Known gaps (follow-ups):** hosted-on-RK public URL deferred (GoLive track);
  JSON-LD Report schema not emitted; no regenerate button for the social graphic
  (a failed generation never retries — rerun from the Social Post tab);
  `Modal.jsx` + `css.js` are orphaned Puck-era leftovers.

---
## Original plan (kept for reference)

This replaced the Puck LPM **entirely** — the owner approved wiping the Puck
workflow. Design is LOCKED in `design-system/round-2/`.

---

## The pivot (why)
Content-first, **guided editorial tool — NOT a page builder** (not Gutenberg/
Elementor). Our users can't make a page because they don't know *what content
belongs*, not how to style it. Two modes: **Assemble** (decide what to say,
guidance-heavy) → **Wordsmith** (light text cleanup). See the full brief:
`sources/docs/BACKLOG/45-landingpage-content-first-design-brief.md`.

## What's DONE (backend, all committed)
- **Guidance engine** — `rk3/landing/guidance.py`. Reads the WHOLE doc (with
  `[p. N]` markers) → guidance artifact:
  `{profile:{title,pages,approxWords,introSectionWords},
    guidance:{documentRead:{whatItIs,audience,coreMessage},
      stats:[{value,fact,page}] (up to 10, strongest first),
      stories:[{subject,kind(personal|caseStudy),quote,narrative,attribution,page,strength(strongest|solid|thin)}],
      recommendedPage:{length(short|middle|long),coverLayout(onTop|beside|inset|textForward),summaryChoice(exec|ai),blocks:[ordered keys]},
      reasons:{length,summaryChoice,coverLayout},
      blocks:{<key>:{verdict(recommended|optional|skip),note}}}}`.
  Prompts in the content registry (`shared.analysis.guidance_system` /
  `block_catalog` / `guidance_task`). Cached `.landing-guidance.json` next to
  source (gitignored). Endpoints: `GET/POST /api/landing/{slug}/guidance[/refresh]`.
- **Default page config** — `rk3/landing/templates.py` `build_from_guidance()`
  → `GET /api/landing/{slug}/guided?length=&cover=`. Length model
  (short=intro+CTA no evidence; middle=+1 evidence, capped; long=all, uncapped;
  **non-destructive** — always re-derivable) + cover presets (beside/inset float
  into summary, onTop standalone, textForward omit). Uses guidance **stats** for
  Findings (with pages) and the top **story** for Storytelling.
- **Storytelling block** — `LandingRenderer.Storytelling` + puckConfig +
  `landingPage.css` (`.lp-story-*`): quote / narrative / attribution + monogram
  avatar; personal (leads with quote) + case-study (leads with narrative).
- **Content registry** — `rk3/content.py` + `content/*.yml`. Keys
  `<scope>.<domain>.<name>`: `shared.*` (analysis prompts, reusable across apps),
  `lpm.*` (UI copy: `assemble`, `blocks`, `length`, `cover`, `wordsmith`,
  `inspector`). Kinds: static/template/prompt/ai. Frontend: `GET /api/content?scope=lpm`
  → `t(key, tokens)` in `app/ui/src/content.js` (intl-messageformat ICU). 97
  entries. **Validate after edits:** `python rk3/content.py`. No-hardcode rule is
  in `CLAUDE.md` ("Content & copy"). Enforcement teeth deferred:
  `sources/docs/DEFERRED/content-registry-enforcement.md`.
- **Stable tokens** — `design-system/tokens/` (app imports via
  `app/ui/src/rk-tokens.css`). `round-1/`, `round-2/` are ARTIFACTS, not deploy;
  never import from a round dir.

## Design source (round-2) — READ THESE
- `design-system/round-2/LPM Assemble Interactive v2.dc.html` — **THE Assemble
  design** (three-column grid `430px 1fr 380px`: blocks | inspector | controls+page).
  The `<script data-dc-script>` `Component.renderVals()` at the bottom holds ALL
  the structure, data shapes, and interactions — read it fully.
- `design-system/round-2/parts/LpmChrome.dc.html` — 56px top **stepper**
  (Assemble → Wordsmith → Preview → Publish; numbered circles, ✓ when done).
- `design-system/round-2/parts/RoughPreview.dc.html` — the rough page.
- `design-system/round-2/LPM Content-First Mocks.dc.html` — all screens incl.
  **Wordsmith**.
- **Framework note:** these use a custom "DCLogic" (React-like: `sc-for`/`sc-if`
  + a `Component` class with `state`/`renderVals`). **Translate to our React** +
  our `--rk-*` tokens + lucide icons (`unpkg lucide` in the mock → we already use
  lucide? check; else inline SVGs). Inline styles map 1:1 to our tokens.

## Build — sequenced slices (each a commit; screenshot-verify vs round-2)
1. **API + data.** `api.js`: `getGuided(slug,length,cover)`,
   `getGuidance(slug)`. `content.js`: `loadContent('lpm')` then `t(key,tokens)`.
2. **Chrome + shell.** The stepper + the `430/1fr/380` grid on stable tokens.
3. **Left: block library.** Buckets Intro/Evidence/CTA (copy: `lpm.blocks.bucket.*`)
   + instructional cards: the "when to use" from `lpm.blocks.<key>.what/when`,
   the CONTEXTUAL blurb from `guidance.blocks[<key>].note`. Select + add state.
   Card `guidance` line + `NEW` badge on storytelling; check/chevron for added.
4. **Center: inspector.** Selected block → name/icon + Add/Remove + blurb +
   per-block choices + a live PREVIEW ("as it will appear"):
   - **Findings** → fact-picker from `guidance.stats` (checkboxes, **page** shown,
     drag-reorder, "3–5 read best" cap turns tomato when >5). "Add your own"
     row belongs HERE (a user fact is just another `{stat,text,page}` item).
   - **AI Summary** → voice taste-test (Report intro/Neutral/Hard sell). Text via
     `GET /api/landing/{slug}/ai-summary?style=intro|neutral|hardsell&length=`.
   - **Storytelling** → story/case-study picker from `guidance.stories` (chips;
     quote+narrative+attribution+page preview).
   - Choice-less blocks (Download/Share) → just preview + blurb + Add.
5. **Right: controls + rough page.** Length + Cover **dropdowns** (copy:
   `lpm.length.*`, `lpm.cover.*`) → refetch `/guided?length=&cover=`. Grayscale
   cover-layout-aware page (block sections + labels). Wordsmith nudge
   (`lpm.assemble.wordsmith_nudge`).
6. **Wordsmith.** Light top-to-bottom editor (from the mocks). Simple text
   editing (bold/italic/lists/links only) — **NOT a heavy RTE, NOT in a Puck
   iframe** (render in the main document so formatting just works; that's the
   whole reason the two-mode split exists). Copy: `lpm.wordsmith.*`.
7. **Mount + retire Puck.** Replace `<LandingMaker>` in
   `app/ui/src/components/DocumentView.jsx` (`tab === "landing"`, ~L866). Delete/
   retire the Puck stack (see below). Keep `LandingRenderer` (block render, used
   by export + preview + Wordsmith).

## Key files
- **Mount:** `app/ui/src/components/DocumentView.jsx` (`tab==="landing"`, ~L866).
- **KEEP:** `app/ui/src/landing/LandingRenderer.jsx` (the `BLOCKS` render map —
  used by export, preview, Wordsmith), `exportZip.js`, `content.js`, `css.js`,
  `fonts.js`, `landingPage.css`, `landing.css`.
- **RETIRE (Puck):** `LandingMaker.jsx`, `puckConfig.jsx`, `LandingShell.jsx`,
  `MiniPreview.jsx`, `puckAdapter.js`, `landingOptions.js`, `blockLibrary.jsx`,
  `RichText.jsx`, and the `@measured/puck` dep. (Some helpers in puckConfig — the
  block-content pieces — moved to `rk3/landing/templates.py`; the FRONTEND needs
  none of Puck once Assemble is bespoke.)
- **Backend:** `rk3/landing/{guidance,templates,extract,ai}.py`, `rk3/content.py`,
  `app/main.py` landing routes.

## Gotchas / decisions
- Guidance judgment varies run-to-run (length, coverLayout, story `kind`).
  It's advisory; the UI's Length/Cover controls override via `/guided` params.
- Stats/story **pages** come from `[p. N]` markers injected into the doc text —
  they're real, and differ from the round-1 mock's hand-guessed pages.
- Voice taste-test uses the EXISTING summary-variant mechanism (lazy + cached).
- Never hardcode copy or prompts — registry + `t()`/`content.prompt()`.
- Import tokens only from `design-system/tokens/`.
