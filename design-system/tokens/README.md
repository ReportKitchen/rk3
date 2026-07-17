# design-system/tokens — the stable, deployable token set

This is the **canonical** copy of the Report Kitchen design tokens (colors,
typography, spacing, effects, fonts). **The app imports from here**
(`app/ui/src/rk-tokens.css`), so the build never depends on a design *working*
directory.

`round-1/` and `round-2/` are design artifacts (mocks, explorations) — not
deployment assets and not a stable import path. When the design system's tokens
change, sync them into this directory deliberately; don't point the app at a
`round-N/` folder.

Currently identical to `round-1/tokens` and `round-2`'s tokens (round 2 was a
content/layout/UX round — colors and type were locked).
