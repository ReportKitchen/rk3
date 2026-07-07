> **STATUS:** HANDOFF REPORT (webified §8) — written 2026-07-07 by Claude Opus at
> the end of the first execution cycle. Companion to `webified.md` (the plan +
> its LEDGER/PARKED). This is the durable synthesis; the LEDGER has the blow-by-blow.

# WEBIFIED — cycle 1 handoff report

*"That's the same document, only webified."* — the owner's bar. This cycle built
the deterministic backbone toward it and validated the vision-loop thesis.

---

## 1. Scoreboard

**Gold census** (the objective, no-cost regression gate — `python -m rk3 eval`):

| checkpoint | passed | failed |
|---|---|---|
| cycle start (sweep Stage 0 baseline) | 71 | 6 |
| after §3 levers (orderPin flips tenure p14) | 74 | 5 |
| after §5.3 (blue names) | 75 | 5 |
| after §6.2 tenure p8 (cell-split) | 76 | 5 |
| after §6.2 atlantic p7 (header bands) + §7.1 | **77** | **5** |

Monotonically non-decreasing greens across every one of ~12 commits; zero
regressions (each engine change gated by stakes-first + census + pytest + leaf-walk
diff + eyeball). The +6 greens = the one flipped red (tenure p14 tag-order) plus
five NEW gold kinds planted this cycle and passing: `styleColor` (§5.3), `cells`
(§6.2), `table` (§6.2), `float` (§3.4), and the §3 lever golds.

**Page-pass rate** (the plan's real bar — zero medium+ vision issues + green
stakes per page) is NOT fully measured: it needs a corpus-wide vision scan
(~$0.1–0.5/page, deferred as cost). The one page re-scanned this cycle
(points-of-light p25) went from 5 medium+ issues (§4.5) to a page whose *styling*
is correct and whose one structural fix lands cleanly (§7.2 below).

**What every document gained** (§7.1 refreshed all 26 docs, not just specimens):
caps mirroring, source text colors, white-on-dark callout text, figure-kicker
styling, a `styleguide.json` design-token digest, and the table cell-split +
colored-header-band fixes.

---

## 2. Convergence stories (salad → webified)

Three pages that visibly crossed the line this cycle. (Before/after screenshots
were eyeballed during the work; paths noted for a re-shoot via `tools/shoot.py`.)

### 2.1 tenure-annual-report p8 — the Acronyms glossary (§6.2)
- **Before:** every single-line row crammed the acronym AND its definition into
  column 1, leaving column 2 empty ("ANT National Land Agency", "CLAN! Community
  Land Action Now!"). Owner note edd55787: "landed in the wrong column."
- **Root cause:** the rows are one COLOR (so the color-based cell splitter failed)
  but the term is a BOLD font and the value REGULAR — the boundary was expressible
  by font, not color.
- **After:** a font-run fallback (`_font_segments`, guarded by wide-span +
  bold→regular weight contrast + single-line/2-column) splits term | value. Every
  row now reads "**ANT** | National Land Agency", matching the source.
- Re-shoot: `tools/shoot.py 02--tenure-annual-report --page 8`.

### 2.2 atlantic-council-report p7 — the OPPORTUNITY tables (§6.2)
- **Before:** the full-width RED "OPPORTUNITY #1" header band rendered on the pink
  BODY fill, its title an underlined styled-link. Owner note b0399c90: "quite a bit
  of format missing."
- **Root cause:** header detection required every column filled; the band's title
  spans one cell (col 0 empty) → `header=false` → the captured red `headBg` was
  never applied.
- **After:** a wide colored band + any row-0 text now counts as a header; the title
  renders white-on-red, no underline. **This single fix flipped 18 tables
  corpus-wide** to show their header bands (all 5 atlantic Opportunity tables, plus
  grey column-header bands in gates-earth, advancing-mobility, ecp).
- Re-shoot: `tools/shoot.py 02--atlantic-council-report-060823 --page 7`.

### 2.3 points-of-light p25 — the vision loop, at last (§7.2)
- **Before (this cycle's §4.5 pilot):** applying the loop's overrides fixed the
  SUMMARY-box ordering but STRIPPED the styling (lost the callout label, flattened
  the pull-quote decoration) — the page did not "look genuinely right." Verdict:
  do §5 styles FIRST.
- **After (§5 done, re-run):** the SUMMARY box moves to right after the heading via
  the loop's orderPin, and the styling stays fully intact — heading green italic,
  callout, colors, pull-quote decoration all preserved. **The §5-first thesis is
  confirmed:** structural fixes now land ATOP correct styling instead of degrading
  it. (One-word prescriber-prefix correction was needed to make the orderPin match
  the callout — see §3/§4 below.)
- Re-shoot: `tools/shoot.py 02--points-of-light --page 25`.

Honorable mentions (deterministic §5 wins, all eyeballed): good-food p22 (teal
callout: black-on-teal → white-on-teal), clean-air p15 (red $330M callout + banner:
black → white text), edf p3 (signatory names: black → source blue).

---

## 3. Residual taxonomy — every non-passing gold, bucketed

The 5 remaining gold failures are ALL reading-order / column-model defects — none
are styling or table-structure (those were this cycle's focus). This is a clean
signal that the NEXT cycle's engine work is the column/reading-order model.

| bucket | pages | defect | missing lever / gap |
|---|---|---|---|
| **column-weld** (a paragraph split across a column break not rejoined) | foia p4, edf p7 | "post-filing" / "Day and evening" fused-or-split at the column boundary | column-break paragraph stitching (the `reading-order` memory's fused-line class) |
| **cross-column reading order** | atlantic p6, jhu p20 | a signature / body-tail reads AFTER the thing it should precede (grateful-line, ENDNOTES) | region-membership ordering below a multi-column split |
| **running-header misclassification** | edf footer | "EDF IMPACT 2023" typed as a heading | running-header detector misses a footer that also looks heading-like |

Beyond the golds, the vision-flagged / owner-noted residuals this cycle PARKED
(see §6) bucket as: **table-tail** (spans-pages assembly, hidden tables, un-griddable
→ figure), **callout geometry** (rounded/circle shapes, text-over-image overlay,
multi-row header bands), **legend** (live-legend swatches), and **loop lever-coverage**
(prescriber prefix-matching, floatPin scope, attribution classification).

---

## 4. Promotion candidates

The plan's bar for a promotion candidate is an override pattern recurring **≥5
times** across docs. This cycle ran the loop on only 1–2 pages (the §5-first pivot
front-loaded deterministic work), so **no override pattern hit ≥5 recurrences yet**
— that count needs a wider §7.2 run.

BUT two signals already point at the highest-value promotions:

1. **Attribution-label classification** — a pull-quote attribution ("NONPROFIT
   LEADER") mis-typed as a heading was flagged as a residual by BOTH the §4.5 and
   §7.2 pilots (2/2 pilot pages). Recurring on every pull-quote page → strong
   promotion candidate for a deterministic rule (a short ALL-CAPS line directly
   under a quote block is an attribution, not a heading).
2. **The §5/§6 fixes ARE this cycle's promotions.** Caps-mirroring, source-color,
   white-on-dark, header-band detection, and font-based cell-split were each mined
   from recurring owner notes across docs and promoted straight to engine rules
   (not left as per-doc overrides). Evidence: the header-band fix alone corrected
   18 tables from a single rule.

---

## 5. Restart instruction — what cycle 2 does first

In priority order:

0. **The owner's QA surface — webified.md §1.5 (added post-cycle-1 from owner
   feedback: "I can't translate stakes/census/pytest into 'this looks right'").**
   Page gallery with honest status rings (grey = never scanned), original-vs-
   render compare view, stakes rows that jump to and highlight their elements,
   plain-words glossary. This comes BEFORE lever work: it is how the owner will
   audit everything else this cycle claims. Gate: walking race-to-lead and
   points-of-light, gallery + compare view alone must explain every amber/red.
   Alongside it: **QUICK SCAN (webified.md §2.4, owner proposal)** — a ≤10-page
   representative scan mode (cluster reps + feature-coverage fill + one easy-page
   control, greedy set-cover over the existing triage signatures) so the gallery
   and the "did it get better" number are affordable corpus-wide; inferred
   sibling status renders hollow, never fake-solid.

1. **Wire the loop's lever-coverage gaps** (cheap, high-leverage — all PARKED [§7.2]):
   (a) make `prescribe()` emit orderPin sequence entries as nids or
   single-node-lead-text prefixes (the ONE thing that blocked the pol-p25 fix from
   landing automatically); (b) extend `float` to paragraph/aside pull-quotes; (c)
   add the attribution-label role-pin (also the top promotion candidate).
2. **Wire the net-improvement gate** (PARKED [§4.3]): in `converge_page`, re-scan
   after apply and keep an override only if severe-count strictly drops — this
   turns the vision-scan NOISE observed in §7.2 (4→5 on an unchanged page) into a
   non-event.
3. **Then run §7.2 wide** — the loop on the pilot corpus (race, edf, +
   points-of-light siblings) to convergence, now that (1)+(2) make apply safe and
   effective. This also finally produces the ≥5-recurrence promotion data §4 lacks.
4. **Column/reading-order cycle** — the 5 residual golds (§3) are all here; this is
   the `reading-order` memory's phase-3+ work (fused-line/region-membership classes).
5. **Table tail** — build the PARKED table levers (spans-pages assembly first — 30
   tables; then auto-figure fallback — 9 candidates scanned).

---

## 6. PARKED ledger → categorized recommendations

Sweeping `webified.md`'s PARKED section into buckets, each an actionable
recommendation with its named missing lever:

**A. Loop lever-coverage (do first — cheap, unblocks the loop):**
- Prescriber orderPin prefix-matching (nid / single-node lead text) — [§7.2]
- floatPin → paragraph/aside pull-quotes (`.para-float-*` render path) — [§7.2]
- Attribution-label role-pin (demote mis-tagged heading → attribution leaf) — [§7.2]
- Net-improvement gate in `converge_page` (keep override only if severe drops) — [§4.3]

**B. Table tail (deep; the owner's "enormous mess"):**
- Cross-page/column table assembly — 30 spans-pages tables (dp p40, tenure p8 merge) — [§6.2/§6.3]
- Gridless-table detection (aligned columns, no drawn rules) — tenure p54 — [§6.2]
- Auto-figure fallback for un-griddable tables — invest p21 + 8 (nff p12 = chart, exclude) — [§6.3]
- tablePin consumption in `_try_table` (needs a real pin-writer + specimen) — [§6.3]

**C. Callout / figure geometry (styling tail):**
- Callout-shape geometry → border-radius / clip-path (circle callouts) — [§5.4]
- Hero-overlay layout (text over full-bleed figure) — clean-air p15 banner — [§5.4]
- Multi-row header band (the band's subtitle row) — atlantic p7 — [§6.2]

**D. Legend (no clean specimen — build the upstream model first):**
- Legend-region model (swatch□+label groups → legend leaves w/ fill colors) — [§5.2]
- Chart-region unification (a shredded paired-bar chart → one figure) — nff p12 — [figures]
- Raster-figure text-overlap recovery (dropped optimists/pessimists labels) — atlantic p10 — [figures]

**E. Triage precision:**
- Triage under-calls engine-flattened styling pages (race p20 pull-quote) — [§2]

---

## Bottom line

The **deterministic backbone is complete and durable** (§0–§6 + §7.1): styles
baseline, table census + two shipped specimens, and all 26 docs refreshed. The
**vision-loop thesis is validated** (§7.2): with styling correct, the loop's
structural fixes land without degrading the page — the exact failure the §4.5
pilot hit, now resolved. What remains is mechanical, well-scoped, and fully
documented: wire three cheap lever gaps, then let the loop run wide.
