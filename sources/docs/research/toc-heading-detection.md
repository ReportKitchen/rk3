# TOC & heading-detection research (2026-06-30)

Using the author's TOC as ground truth to find what to change. Read the 6
missed-TOC PNGs + block data, swept reconciliation across the 27 active docs,
and prototyped/validated detectors. **Findings + recommendations only — not yet
acted on** (except the read-only toccompare diagnostic).

## Part 1 — why we miss TOCs entirely (6 docs)

Detector today (`analyze._toc_pages`) fires only on **dot-leader + trailing
number** (`\.{3,}\d+$`, ≥5 lines) OR **"Contents" title + ≥3 trailing-number
lines**. Real designed TOCs break both assumptions. The 6 with feedback:

| doc | title | page-number layout | leaders |
|---|---|---|---|
| ecp-homeforgood | "Table of Contents" | separate **right** column | rendered as `--`/`- -` marks at line START, not `...` |
| edf-ir23 | **"WHAT'S INSIDE"** | separate **left** column | none |
| foia-basics | "TABLE OF CONTENTS" | **leading** number, merged into entry line | none |
| gates-earth | "Table of contents" | separate **right** column | none |
| invest-in-black-led | "Table of contents" | **leading** number, merged | none |
| race-to-lead | "Contents" | **leading** numbers, **two-column** | none |

**Root cause (unifying):** designed TOCs put the page number in a **separate
aligned column** (left or right) or as a **leading token**, and use whitespace
alignment instead of `...` leaders. Our regexes require the number on the entry
line, trailing. So none fire.

**Validated fix — a structural detector** (prototyped read-only, caught all 6,
0 false positives on body pages):
- **Signal A — numeric column:** ≥4 standalone numeric-only blocks (`0?\d{1,3}`)
  on a page = a page-number column. Caught ecp(5), edf(8), gates(13), race(6).
- **Signal B — leading-number lines:** ≥4 lines matching `^\s*0?\d{1,3}\s+[A-Z“(]`
  = page-number-prefixed entries. Caught foia(7), invest(8), race(16).
- **Guard (needed):** B alone false-fires on deep numbered-content pages
  (gates p40, a numbered list, leadnum=6). Gate the whole detector on
  **front-of-document** (page ≤ max(8, 12% of pages)) **OR** a Contents-ish title
  **OR** page-number plausibility (the numbers ascend / are varied, not a 1..N
  list sequence). All 6 real TOCs are on pages 2–7; gates p40 is excluded.
- **Broaden `TOC_TITLE`:** add "what's inside", "inside", "in this (report|issue)",
  "sections", "in this guide".

## Part 2 — accuracy of recognized TOCs

After the earlier wrap/dot/roman fixes, parsing is mostly clean (toolkit-hiring:
2 minor issues / 49). Remaining:
- **Run-together words** (space-synthesis failure): ecp `DefiningLegalandTechnicalTerms`,
  `HowtheEvictionProcessWorks`. → NLP de-concatenation (Part 4).
- **Spaced-dot leaders** (`. . . .`) occasionally un-stripped (community-schools
  `DEDICATION . . . .`). The current strip wants ≥2 *consecutive* dot chars;
  spaced dots slip through. Widen to `[\s.·•…_]{2,}$` already covers spaces, but
  a single space *between* every dot defeats it — strip `(\s*[.·•…]){3,}\s*$`.
- **Uppercase-starting wrap continuations** not folded (investing "Outcome and
  Opportunity Gaps…" was a wrap of the prior entry but starts capitalized — the
  lowercase-continuation heuristic only catches lowercase wraps). Could also fold
  a short next line at the SAME indent with NO page number of its own.
- **List of Figures/Tables** entries mixed into the TOC (design-principles
  `Figure 3 …`, `Figure 4 …`) — should be detected as a separate list and not
  counted as missed section headings.

## Part 3 — header-finding gaps (TOC "missed" = headings we didn't detect)

Categories of real recall gaps (excluding fuzzy/figure-list noise):
- **Front-matter section titles** on title/divider pages — Forewords (oxfam),
  "Open Letter from…" (points-of-light), Dedication, Highlights (tenure). Large
  display text that doesn't fall in our size clusters or sits alone on a page.
- **All-caps section dividers** — `PART III: THE ROAD FORWARD`, `END NOTES`,
  `HIGHLIGHTS`. Caps headings on divider pages.
- **Reordered-word titles** — oxfam `1.4 The link between corporate power and
  extreme wealth` vs our heading `…extreme wealth and corporate power`. Match,
  not recall — fix with **token-set** fuzzy matching.
- **Space-in-number** — `Chapter 1 0` (= "Chapter 10"), space-synthesis again.

**Dominant reconciliation note is LEVEL disagreement** (advancing 20/20 matched
entries flagged, rwjf-futures 34/41, oxfam 15) — our h-levels vs TOC depth. This
is the "adopt TOC levels" action, the single biggest header-quality lever.

## Part 4 — lightweight NLP tools (MEASURED — reversed the initial take)

Installed wordninja + wordfreq and measured run-together prevalence across the
26 active docs: 1190 distinct "rare-word-that-splits-into-common-words" tokens.
**The overwhelming majority are FALSE positives** — proper nouns
(`Baystate`→"Bay state", `Hillenbrand`→"Hill en brand", `Honoroff`, `Shillingford`),
CamelCase brands that are *correct* as written (`StriveTogether`, `HomeStart`,
`CareerRise`, `EdPrepLab`), and closed compounds (`grantmaking`,
`biomanufacturing`, `preservice`, `underinvestment`, `changemakers`). Genuine
missing-space cases (`ofthe`, `towardsjustice`) were rare and mostly in the
now-parked docs.

**Verdict: do NOT auto-split with wordninja in the pipeline — it would corrupt
far more than it fixes** (and offset-rebasing of style runs makes it costly too).
- The one real symptom (a run-together TOC entry not matching its spaced
  heading, ecp `DefiningLegalandTechnicalTerms`) is fixed safely by a
  **space-insensitive match** in toccompare (compare titles with all spaces
  removed) — no text mutation, no corruption risk. ecp missed 14 → 5.
- **wordfreq as a QA flag** is too noisy as-is (1190 mostly-false hits); would
  need a much stronger filter (e.g. exclude CamelCase, known compounds, and
  capitalized/proper-noun tokens) before it's useful. Deferred.
- **symspellpy** — not pursued; glyph-map misspellings (`Nonproffits`) are a
  different, font-specific problem, and spell-correction on domain text is risky.

## Recommendations (priority order)

1. **TOC detection:** add numeric-column + leading-number signals with the
   front/title/plausibility guard → recovers all 6 missed docs.
   (`analyze._toc_pages` for the drop + the toccompare parser for the diagnostic.)
2. **TOC parser:** pair separate number columns to entries by baseline-y; strip
   leading numbers as the page; fix spaced-dot leaders; separate List of
   Figures/Tables.
3. ~~NLP de-concatenation with wordninja~~ — **rejected after measuring** (mostly
   mis-splits proper nouns/brands/compounds). Use a space-insensitive TOC match
   instead (done). wordfreq QA-flag deferred (too noisy without a stronger filter).
4. **Header recall:** detect front-matter/display section titles + all-caps
   dividers — the TOC says these are exactly what the author thinks matters.
5. **Header levels:** adopt TOC nesting as level authority (fixes the widespread
   level? flags).
6. **Matching:** token-set fuzzy match for reordered titles.
