# Report Kitchen — Website UI Kit

A high-fidelity recreation of the rebranded ReportKitchen.com marketing site
(brochureware, to be built on WordPress). Photo-free: all color blocks, type,
and Lucide icons. Composes the design-system primitives — it does not
re-implement them.

## Run
Open `index.html`. It loads React + Babel, Lucide, the compiled
`_ds_bundle.js`, and each screen file, then renders a small client-side router.

## Screens
- **Home** (`Home.jsx`) — hero with a photo-free "PDF → website" device, trust
  strip, the four offerings, how-it-works, featured work, Pattern Library
  teaser, CTA.
- **Our Work** (`OurWork.jsx`) — filterable grid of all 16 project profiles
  (real projects from the live site).
- **Project Profile** (`ProjectProfile.jsx`) — Housing2Justice, with a
  before/after (PDF → interactive) device, proof-point stats, and an accordion.
- **Report Kitchen Custom** (`OfferingCustom.jsx`) — the flagship offering
  page: value props, four-step process, samples, strong contact CTA. The nav's
  other offerings (Landing Page Maker, RK Express, Consulting) route here as a
  representative offering layout.
- **Pattern Library** (`PatternLibrary.jsx`) — the Info Design Pattern Library
  content-marketing piece: filterable grid of patterns with "when to use".
- **Header / Footer** (`Header.jsx`) — shared chrome; the whisk appears only as
  a faint footer accent.

`Insights` and `About` are represented by a placeholder (not built out).

## Interactions
- Header nav + offerings dropdown route between screens.
- Project cards → Project Profile. Our Work / Pattern Library category chips
  filter live. Accordions expand.

## Notes / shortcuts
- Client logos are set as text (we don't have permission-cleared logo assets).
- Icons are Lucide (CDN) — the flagged substitute icon set.
- Fonts (Bricolage Grotesque + Mulish) are proposals replacing Lato.
