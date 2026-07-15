# Handoff: Report Kitchen — WordPress Theme (rebranded marketing site)

## Overview
This is the rebranded ReportKitchen.com marketing site: a brochureware site
pitching Report Kitchen's services (turning dense PDFs into interactive,
accessible, responsive websites) to communications pros at nonprofits,
foundations, and higher ed. It is to be built as a **custom WordPress theme**.

The new brand is **photo-free** — flat color blocks, confident type, and line
icons. No stainless-steel kitchen photography; no whisk background pattern (the
whisk appears only in the logo lockup and a faint footer accent).

## About the design files
The files in this bundle are **design references created in HTML/React** —
prototypes showing intended look and behavior, **not production code to copy
directly**. The task is to **recreate these designs as a WordPress theme** using
WordPress's established patterns (theme templates, blocks/ACF, the loop, menus,
CPTs). Do not ship the React prototype; rebuild it in PHP/WordPress.

This is a **design system**, so the tokens and component styling are the source
of truth. `styles.css` + the `tokens/` files can be adapted almost verbatim into
the theme's stylesheet; the React components document the exact markup/spacing/
states each UI piece should have.

## Fidelity
**High-fidelity.** Final colors, typography, spacing, radii, shadows, and
interactions are all specified in the tokens and components. Recreate the UI
pixel-perfectly using the token values below. The one liberty: the "PDF →
website" and "before/after" hero devices are illustrative compositions built
from divs — reproduce the spirit (a stylized document turning into a site), not
every pixel.

## Recommended WordPress structure
- **Pages (static templates):** Home, About, each Service page, Report Kitchen
  Custom, Consulting. Build with block patterns or ACF flexible-content.
- **Custom post type `project`** → "Our Work". Fields: client, summary,
  category (taxonomy), cover color, cover icon (Lucide id), before/after notes,
  stats, external URL. Archive = the filterable grid; single = Project Profile.
- **Custom post type `post`/`insight`** → "Insights" (the blog — never labeled
  "blog"). Standard loop; category taxonomy drives the sidebar filter. Images
  are intentionally optional (see Insights below).
- **Custom post type `pattern`** → Info Design Pattern Library. Fields: name,
  category, description, "when to use", Lucide icon id.
- **Primary menu:** a "Services" mega-menu (custom Walker or a block), the
  standalone items Our Work / Insights / About, a set-off "Pattern Library"
  pill, and a "Contact the Kitchen" button.

## Screens / views

### Global — Header
- Sticky, translucent warm-paper background (`rgba(251,247,240,0.86)`) with
  `backdrop-filter: blur(10px)` and a 1px bottom hairline (`--rk-border`).
  Padding 16px 40px. Logo left (red logo SVG, 38px tall).
- Nav right, 15px Mulish 600. Order: **Services** (mega-menu trigger, chevron
  rotates 180° when open) · Our Work · Insights · About · **Pattern Library**
  (set-off pill) · **Contact the Kitchen** (primary button, sm).
- **Services mega-menu:** full-width white panel (`left:40 right:40`, 8px below
  header), radius 18px, `--rk-shadow-lg`, 20px padding. Header row ("What's on
  the menu" tomato eyebrow + "Four ways to serve your work"), then a 2-col grid
  of the four services. Each: 42px tomato-100 icon tile (Lucide, tomato-600),
  16px Bricolage 700 title, availability pill (success green / macaroni "Coming
  soon"), 13.5px muted description. Row hover bg `--rk-gray-100`.
- **Pattern Library pill:** distinct from plain nav — 1.5px `--rk-border-strong`
  border, pill radius, book-open icon (macaroni-600) + label; hover border →
  macaroni-500, bg → macaroni-100. Signals "free resource," not a peer nav item.

### Global — Footer
- `--rk-rhino-900` ground, white text, 64/40px padding. Faint white whisk SVG
  bottom-right (opacity 0.08, rotate −10°) — the only sanctioned decorative
  whisk. 4-col grid: brand (white logo, blurb, email `info@reportkitchen.com`,
  phone `215-592-7673`) + Services / Explore / Company link columns (macaroni-500
  uppercase headings). Base row: "© 2025 Report Kitchen" and "Baked with ❤️ in
  Philadelphia" (the one intentional emoji exception).

### Home
Sections top→bottom: (1) **Hero** — 2-col: left = tomato eyebrow, 60px Bricolage
800 headline with "download button" in tomato, 20px muted subhead, two buttons
("Get cooking" primary lg, "See our work" secondary lg); right = illustrative
PDF→website device on a macaroni-100 field. (2) **Services** (white band,
hairline top/bottom) — SectionHeading + 2×2 FeatureCard grid. (3) **How it
works** (cream band) — 3 numbered steps (icon tile, big ghost number, title,
body). (4) **Featured work** (paper) — SectionHeading + "See all work" ghost
button + 3 project cards. (5) **Pattern Library teaser** (rhino band) — inverse
SectionHeading + 2×2 tile grid, "Browse the library" accent button. (6)
**Callout** CTA band.

### Our Work
Cream header band (eyebrow, 54px headline, intro). Body: a row of filter chips
(category taxonomy; "All" + each category) and a 3-col grid of project cards.
Cards: photo-free — flat color cover with a large Lucide icon and a small
uppercase kind label bottom-left; body has tomato client kicker, 22px Bricolage
title, muted description, category tag. Hover: lift 3px + `--rk-shadow-md`, title
→ tomato. 16 seed projects listed in `OurWork.jsx`.

### Project Profile (single project)
Back link → Our Work. Hero: category tags, client name, 56px Bricolage title,
20px intro, two buttons. **Before/After** band (cream): two panels — a faded
static "PDF" (stacked gray lines) → arrow → an "interactive site" (browser
chrome, rhino hero, content tiles). Body: 2-col — proof-point stat list (42px
tomato numbers) + narrative prose and an Accordion. Tomato Callout to close.

### Service pages (Custom / Maker / Express / Consulting)
Use `OfferingCustom.jsx` as the template. Rhino hero (availability Badge, 58px
title, intro, accent + ghost buttons; right = list of value rows). 4-step
process grid. Samples grid (3 project cards, cream band). Callout. Coming-soon
services (RK Express) swap the CTA for a waitlist and show the macaroni "Coming
soon" badge.

### About
Cream hero with the vision line ("help our clients maximize the impact of their
work…"). Narrow (760px) story column — 5 paragraphs, origin narrative (verbatim
from current site, lightly edited). Values band (white): 3 cards (Free the
content / Accessible by default / Built to be measured). Stat strip (3 items,
3px tomato top rule). Callout. **No team page, no portraits** (client decision).

### Insights (the blog)
**Traditional blog layout, image-downplayed** (client explicitly did not want a
card grid like Our Work, and post images are hard to source). Header band
(eyebrow, 48px headline, intro). Body: 2-col grid `1fr 240px`. Left = a single
text column of post rows separated by 1px hairlines — each row: meta line
(tomato category · date · read time), 27px Bricolage headline (hover → tomato),
16.5px dek, "Read more" with arrow. **No per-post images.** Right = sticky
sidebar: "Topics" list (click to filter) + a rhino subscribe block with macaroni
button.

### Pattern Library
Centered header (macaroni eyebrow "Free resource", 56px headline, intro).
Centered filter chips. 3-col grid of pattern cards: 50px macaroni-100 icon tile,
uppercase category, 21px title, description, and a dashed-rule "When [to use]"
footer. Cream Callout to close.

## Interactions & behavior
- **Routing:** the prototype is a client-side router; in WordPress these are
  real pages/permalinks. Preserve nav destinations.
- **Filters:** Our Work, Insights, Pattern Library filter by category client-side
  in the prototype; in WP use taxonomy archive queries (or AJAX/`pre_get_posts`).
- **Accordion:** single-open by default, grid-rows 0fr→1fr expand (`--rk-dur-slow`
  380ms, `--rk-ease-out`); plus icon rotates 45°.
- **Hover:** buttons darken one step + lift 1px; cards lift 3px + shadow-md,
  title → tomato, trailing arrow nudges +3–4px. Links: tomato with animated
  underline. All transitions 120–200ms `--rk-ease-out`. No bounce/parallax.
- **Focus:** visible `--rk-ring` (3px muffin-blue) on all interactive elements.
  Respect `prefers-reduced-motion`.

## Design tokens
Full source in `tokens/` (colors, typography, spacing, effects) and `styles.css`.
Key values:
- **Brand:** Tomato `#D72E2C` (primary/brand), Macaroni `#F2BB2E` (accent),
  Blueberry Muffin `#7683A2` (support), Rhino `#303D61` (ink/dark), Steel
  `#DDDDDD`. Ramps: tomato 700 `#A31E1C` / 600 `#BD2523` / 500 `#D72E2C` / 300
  `#EC8A88` / 100 `#FBE1E0`; macaroni 600 `#D99B12` / 100 `#FDF1D2`; rhino 900
  `#1E2740` / 700 `#303D61` / 500 `#4C5A80` / 300 `#7683A2` / 200 `#A9B2C6` / 100
  `#D5DAE4`.
- **Surfaces:** page = warm paper `#FBF7F0`, sunken = cream `#F4ECDD`, card =
  white, inverse = rhino-700. Border hairline `#E4E1D9`.
- **Type:** headings **Bricolage Grotesque** (700/800, letter-spacing −0.02em),
  body **Mulish**, mono IBM Plex Mono. All via Google Fonts (`@import` in
  `tokens/fonts.css`). **Kano `.otf` = logo only.** Scale: hero 60–76, section
  title 48, card heading 22, body 18, caption 14.
- **Radius:** 4 / 8 / 12 / 18 / 28 / pill 999. **Shadows:** sm `0 1px 2px
  rgba(30,39,64,.06)`, md `0 6px 20px rgba(30,39,64,.08)`, lg `0 18px 44px
  rgba(30,39,64,.12)`; hard offset `6px 6px 0 rhino-900` for accent stickers.
- **Spacing:** 4px base grid (4/8/12/16/24/32/48/64/96/128). Content max 1200px,
  reading measure 760px, section rhythm ~80px.

## Assets
- **Logos:** `assets/logo-{red,white,rhino}.svg` (whisk + wordmark lockup).
  Header uses red on paper; footer uses white on rhino.
- **Whisk:** `assets/whisk-{red,white,rhino}.svg` — logo/footer accent ONLY.
- **Font:** `assets/fonts/Kano.otf` — logo only (the logo SVGs are already
  outlined, so Kano is rarely needed at runtime).
- **Icons:** **Lucide** (https://lucide.dev), MIT/ISC, ~2px rounded stroke. In
  the prototype loaded via CDN + `data-lucide`. For WordPress, either enqueue the
  Lucide JS or (preferred) inline the specific SVGs. Icon ids are named in each
  component/data file (e.g. `file-text`, `wand-sparkles`, `bar-chart-3`,
  `scale`, `book-open`, `accessibility`). *Special Lineal by Magnific is under
  consideration for richer Pattern Library glyphs — proprietary, needs a license
  and self-hosted SVGs; not yet wired in.*

## Files in this bundle
- `styles.css`, `tokens/` — the design tokens (adapt into the theme stylesheet).
- `ui_kits/website/` — the full prototype:
  `index.html` (router), `Header.jsx` (header + footer), `Home.jsx`,
  `OurWork.jsx` (+ 16 seed projects), `ProjectProfile.jsx`, `OfferingCustom.jsx`,
  `PatternLibrary.jsx` (+ pattern data), `About.jsx`, `Insights.jsx` (+ sample
  posts), `README.md`.
- `components/` — React reference implementations of every primitive (Button,
  Link, Tag, Badge, Eyebrow, Icon, Card, FeatureCard, SectionHeading, Callout,
  Accordion, Input, Textarea, Select), each with a `.d.ts` props contract and a
  `.prompt.md` usage note. These document exact markup, variants, and states.
- `assets/` — logos, whisk, Kano font.
- `design-system-readme.md` — full CONTENT FUNDAMENTALS, VISUAL FOUNDATIONS, and
  ICONOGRAPHY. **Read this first** for voice/tone and visual rules.

## Voice & tone (for any copy the theme needs)
Warm, witty, culinary metaphor with real substance. Second person to the reader
("your report"), "we"/"the Kitchen" for the company. Sentence case. Bold the
payoff phrase. No emoji except the footer heart. Examples: "Get cooking,"
"Contact the Kitchen," "Fresh from the oven," "Your 200-page PDF deserves better
than a download button."
