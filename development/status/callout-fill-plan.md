# Phase B fix #2 — callout/box-fill fidelity (the big lever)

Resume plan for the deepest Phase B fix. This is the `color` category (~45 pages)
plus much of `structure` + `missing-content` overlap — the single biggest
pass-rate lever. Owner flagged it repeatedly (the KEY PARTNERS "brown box").

## Problem (two sub-cases)
1. **Whole-box wrong fill** — a WHITE/light box rendered dark, or a light box
   painted a backing color. Exemplars: advancing-mobility **p15** (white box →
   dark), **p33** (table section on black), invest/others.
2. **Header-strip smear** — a box with a colored HEADER STRIP + white body renders
   with the strip color over the ENTIRE box. Exemplar: advancing-mobility **p13**
   KEY PARTNERS (`data.fill = #a59d94`, the taupe header strip, applied whole-box).

## Root cause (already established)
- `analyze._classify_region` sets `style["fillIdx"] = max(fills, key=area)`
  (~line 1013), i.e. the LARGEST-area fill. The aside emits `data.fill` from it
  (~line 3451).
- The PDF draws a taupe/backing rect for the whole box, then WHITE rects on top
  for the body. Extraction DROPS the white rects (white ≈ page bg), leaving only
  the backing color → it gets applied to the whole box. Verified on p13: the one
  fill overlapping the box is taupe at 100% coverage, but the rendered ORIGINAL
  body samples pure white (only a ~20pt taupe HEADER STRIP at the top).
- KEY infra already present: `analyze._local_bg(ctx, page, bbox)` (~line 1718)
  opens the rendered page PNG and samples colors. So IMAGE-GROUNDED fill
  verification is feasible and idiomatic (owner's "sample bgcolor" note).

## Approach
**Phase 1 — image-grounded whole-box fill (fixes sub-case 1, tractable):**
- Add `_region_interior_fill(ctx, page, bbox)`: sample a GRID inside the region
  (from the page PNG), return the modal/median color (text is a minority, so the
  mode ≈ the true background). Exclude a top strip band from the "body" sample so a
  header strip doesn't dominate.
- Where `fillIdx` is set (or where the aside's `data.fill` is emitted): compare the
  extracted fill color to the sampled interior. If they differ materially, the fill
  is overpainted → use the sampled interior color (or DROP the fill if it's
  near-white/near page-bg). Log a `fill-corrected` event.
- Genuinely-dark callouts (white-on-dark, e.g. good-food p22, clean-air p15 red
  aside) sample dark == extracted fill → unchanged. Light-box-wrongly-dark → fixed.

**Phase 2 — header strip (fixes sub-case 2, harder, optional):**
- If the interior has a top band in the extracted-fill color over a lighter body,
  model a header (strip fill) + body (light). Mirrors the §6.2 table head-band
  work but for asides. Only if Phase 1 leaves KEY PARTNERS wrong.

## Gates + verification (do NOT skip)
- analyze VERSION bump; `python -m rk3 eval` census NON-DECREASING; pytest snapshot
  ritual (regen only after eyeballing the diff is intended fills).
- EYEBALL: advancing p13 (KEY PARTNERS), p15/p33 (white-box), AND a genuinely-dark
  callout that must NOT change (good-food p22, clean-air p15). Screenshot + look.
- Targeted vision re-scan of ONLY the color-category pages (owner: no full runs) to
  confirm the category moved. Then rebuild CORPUS-SCOREBOARD (free).
- Reconvert active docs (batch_documents, CPU-only) to land it.

## Risk
Touches every callout/table fill corpus-wide → high regression risk. Gate hard;
revert if census drops or eyeball shows a genuinely-dark callout going light.
