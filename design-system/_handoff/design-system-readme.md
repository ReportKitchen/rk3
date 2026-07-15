# Report Kitchen — Design System

Brand refresh for **ReportKitchen.com**. Report Kitchen turns dense PDFs
(research reports, toolkits, comprehensive plans, resource guides) into
**interactive, accessible, fully responsive websites**. This system powers the
rebrand — starting with a new marketing site to be built on WordPress.

**Audience:** communications professionals, primarily at **nonprofits,
foundations, and higher-ed** institutions.

**The refresh in one line:** keep the logo, colors, and brand personality;
drop the stainless-steel kitchen photography and the whisk-as-background
pattern. The new look is **all design elements, color, type, and icons — no
photography.** The whisk lives only in the logo lockup and (sparingly) in
footer accents.

---

## Sources

- `uploads/Report Kitchen Brand Identity and Colors 2025.png` — the 5-color palette (below).
- `uploads/ReportKitchenLogoRed.svg` — full logo lockup (whisk + wordmark). Copied to `assets/logo*.svg`.
- `uploads/whisk-red.svg` — standalone whisk mark. Copied to `assets/whisk*.svg`.
- `uploads/Kano.otf` — the logo's typeface. **Logo only** (the SVG is already outlined; the font is provided for reference / live wordmark typesetting).
- Live site (Drupal, being replaced by WordPress):
  - Home — https://reportkitchen.com/
  - Our Work — https://www.reportkitchen.com/our-work
  - Sample profile — https://www.reportkitchen.com/housing2justice

---

## Products / site map (new site)

Brochureware marketing site pitching the company's services.

**Content**
- **Our Work** — project profiles (16 today, migrating most, adding more).
- **Insights** — the editorial/blog section (never call it "blog").
- **About** — single page (no team page).
- **Info Design Pattern Library** — the flagship content-marketing piece: a
  library of information-design patterns with examples, when/how to use them,
  and implementation tools.

**Offerings (the things being sold — each gets a strong CTA)**
- **Landing Page Maker** — self-serve web tool: upload a PDF, build a landing
  page for it. Free for individuals, paid for teams. *Available at launch.*
- **Report Kitchen Express (RK Express)** — self-serve tool: upload a PDF, get
  a fully responsive HTML site. Free & paid tiers. *Coming soon.*
- **Report Kitchen Custom** — full-service / white-glove: we build your
  responsive site from your PDF. The current flagship. *Available now.*
- **Consulting** — nonprofit communications × long-form reports × AI. Custom
  work; sell on experience, strong contact CTA. *Available now.*

---

## CONTENT FUNDAMENTALS

The voice is the brand's biggest asset: **warm, witty, and confident, built on
a running culinary metaphor** — but never at the expense of clarity for a
serious professional audience.

- **Culinary metaphor, used with restraint.** Reports become dishes; the team
  is "the Kitchen." Real examples from the live site: "Discover a more
  delicious way to present your reports," "Let's get cooking," "Can I get a
  taste?", "Contact the Kitchen." Use it in headlines, section labels, and
  CTAs — **not** in body copy that explains features or accessibility. One
  garnish per course; don't over-season.
- **Person:** second person to the reader ("your report," "your audience"),
  first-person plural for the company ("we combined," "we'd love to talk").
  Warm and direct.
- **Casing:** Sentence case for headings and buttons ("Get in touch,"
  "See our work"). Title Case reserved for proper nouns and product names
  (Landing Page Maker, RK Express). ALL-CAPS only for small eyebrow labels,
  tracked out.
- **Sentence rhythm:** short, punchy headlines; medium body sentences.
  Rhetorical questions are on-brand ("How much more engaging would they be?").
  Bold is used inline to spotlight the payoff phrase ("**engaging and
  effective**," "**truly interact with your content**").
- **Substance under the wit.** Concrete proof points: "80 pages of narrative,
  a spreadsheet survey, and a database of service providers into an
  interactive toolkit"; "full analytics on what readers engage with." Numbers
  and specifics earn trust with foundation/nonprofit buyers.
- **No emoji.** The palette and icons carry visual warmth; emoji would cheapen
  the professional register. Culinary *words*, not food emoji.
- **Accessibility & impact are values, not features** — "interactive,
  accessible, optimized web content." Say it plainly.

**Sample lines in voice**
> "Your 200-page PDF deserves better than a download button."
> "From PDF to polished site — without the reformatting headache."
> "Let's get cooking." · "Book a tasting." · "Contact the Kitchen."

---

## VISUAL FOUNDATIONS

The rebrand replaces photography with **flat color, confident type, and clean
line icons.** Think editorial recipe card meets policy report: warm, credible,
a little playful.

**Color.** Five brand colors anchored by **Rhino** navy (#303D61, the ink and
primary dark surface) and **Tomato** red (#D72E2C, the primary action / brand
accent). **Macaroni** yellow (#F2BB2E) is the bright highlight (use in small
doses — underlines, chips, callout grounds). **Blueberry Muffin** (#7683A2) is
the calm support tone and doubles as a mid neutral. **Steel** (#DDDDDD) is the
light neutral. To reintroduce warmth lost with the photography, pages sit on a
**warm paper** ground (`--rk-paper` #FBF7F0) with a deeper **cream**
(`--rk-cream`) for sunken sections. Neutrals are cool, derived from Rhino.

**Type.** Headings in **Bricolage Grotesque** (characterful, editorial, modern);
body/UI in **Mulish** (friendly, legible at length). Big, tight display
headings (letter-spacing −0.02em); relaxed 1.65 line-height for reading
measures capped at ~760px. Small tracked-out uppercase eyebrows label sections.
*[Proposed — replaces the current Lato; client is open to new fonts.]*

**Backgrounds & sections.** Full-bleed **solid color blocks** alternate the page
rhythm — paper → white cards → rhino (inverse) → cream. **No photographs, no
gradients as a crutch, no whisk pattern.** Where a hero image used to live, use
an oversized icon composition, a color field, or a stylized "PDF → website"
device built from simple shapes. Occasional flat geometric accents (a macaroni
underline stroke, a dotted rule, a tomato bracket) add life.

**Corners & cards.** Modest radii: 8–18px on cards and inputs, pill (999px) on
tags/chips and some buttons. Cards are white on paper with a **warm hairline
border** (`--rk-border`) and **no shadow at rest**; they lift with
`--rk-shadow-md` on hover. A playful **hard offset shadow**
(`--rk-shadow-offset`, 6px 6px 0 rhino) is reserved for accent chips/sticker
elements — used rarely.

**Borders & lines.** 1px warm hairlines separate content; 2px in rhino or
tomato for emphasis rules and focus. Dotted/dashed rules evoke recipe-card
tear lines — an occasional flourish, not a system.

**Shadows.** Cool, rhino-tinted, low. sm for resting chrome, md for hover lift,
lg for overlays/modals only. Depth is mostly communicated by color, not shadow.

**Motion.** Quick and confident: 120–200ms on hover/press with an ease-out
curve (`--rk-ease-out`); 380ms for larger reveals. Fades and small translate/
scale — **no bounce, no parallax.** Respect `prefers-reduced-motion`.

**Hover / press.**
- Buttons: hover darkens one step (tomato-500 → tomato-600) and lifts 1px;
  press returns to baseline / darkens further. No color-inversion surprises.
- Cards/links: hover raises the card (shadow-md) and shifts the title to
  tomato; a trailing arrow icon nudges 2–4px.
- Links: tomato, underline on hover (or a macaroni underline for emphasis).

**Transparency & blur.** Used sparingly — a translucent rhino scrim over a
color block for legibility, or a subtle sticky-header blur. Never frosted-glass
everywhere.

**Focus.** Visible `--rk-ring` (3px muffin-blue halo) on all interactive
elements. Accessibility is a brand value; keep it.

---

## ICONOGRAPHY

Icons do heavy lifting in a photo-free brand, so the set must be consistent and
generous.

- **The brand's only bespoke marks are the logo lockup and the whisk.** The
  whisk (`assets/whisk-*.svg`) appears **only in the logo and, sparingly, in
  footer accents** — never tiled as a background, never as a decorative
  sprinkle. Variants provided: red, white, rhino.
- **UI/content icons: Lucide** (https://lucide.dev), loaded from CDN. *This is
  a substitution* — the brand had no icon system of its own; Lucide's ~2px
  rounded-stroke line style pairs cleanly with Bricolage's warmth and the
  rounded logo letterforms. Load: `<script src="https://unpkg.com/lucide@latest"></script>`
  then `lucide.createIcons()`; or use the individual SVG files.
- **Under consideration: Special Lineal by Magnific** (formerly Freepik) —
  ~288k icons, far deeper coverage for Pattern Library specifics. Tradeoff:
  proprietary (needs a Magnific/Freepik license + attribution), no icon-font/
  CDN (download per-icon SVGs and self-host). **Recommendation:** keep Lucide
  as the default system set; use Special Lineal selectively in the Pattern
  Library where a specific expressive glyph is needed. See
  `guidelines/font-pairings.html` for the side-by-side comparison.
- Icons carry the "information design" story: use them to represent report
  types, patterns (chart, table, timeline, map, accordion), and process steps
  (upload → transform → publish).
- **No emoji. No Unicode dingbats as icons.** No PNG icons. SVG line icons only.
- Icon color follows text color (currentColor); accent icons may use tomato or
  macaroni on neutral grounds.

---

## VISUAL / CAVEATS FLAGS (please confirm)

1. **Site fonts** — Bricolage Grotesque + Mulish are *proposals* replacing
   Lato. Happy to explore alternatives (Kano stays logo-only).
2. **Icon set** — Lucide is a substitution; confirm or supply your own.
3. **Warm paper ground** — new neutral (`--rk-paper`) added to inject warmth
   where photography used to; confirm this direction.

---

## INDEX — what's in this system

**Root**
- `styles.css` — global entry (import this).
- `readme.md` — this file.
- `SKILL.md` — portable Agent-Skill wrapper.
- `thumbnail.html` — homepage tile.

**tokens/** — `fonts.css` · `colors.css` · `typography.css` · `spacing.css` · `effects.css`

**assets/** — `logo-{red,white,rhino}.svg`, `whisk-{red,white,rhino}.svg`,
`logo.svg`/`whisk.svg` (source black), `fonts/Kano.otf`.

**guidelines/** — foundation specimen cards (Colors, Type, Spacing, Brand).

**components/** — reusable primitives (see cards, group "Components"):
Button · Link · Tag · Badge · Card · FeatureCard · Accordion · Input ·
Textarea · Select · Eyebrow · SectionHeading · Callout · Icon.

**ui_kits/website/** — Report Kitchen marketing-site recreation
(Home, Our Work, Project Profile, an Offering page, Info Design Pattern
Library) composing the components above.
