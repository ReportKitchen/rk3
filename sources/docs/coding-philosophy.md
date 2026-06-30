# Various ideals/approaches to keep in mind

- We're pursuing a strategy of using multiple layers given the variations of PDFs we find, prioritizing approaches that address the most common situations first, adding fallbacks to raise our % success rate.

## Layered techniques — living registry

When we add a fallback layer to handle a PDF variation the primary method misses,
record it here. Every layer also logs its decision (method + reason) to the
per-stage debug JSONL, and every output element carries an `rk` linking back to
that log entry — so "which technique fired on this element" is always
recoverable, and the planned **techniques report** is an aggregation of these.

Known limitation (2026-06): layers are tried **in order until one applies**, and
a fallback only runs when the primary is *inapplicable* — we do NOT yet run
multiple methods and pick the best, so we can't detect when a method we *did*
use was wrong (only when one is unavailable). A future report surfacing method
**disagreements** is how we'd catch those.

| Technique | Layers (primary → fallback) | Logged as (event / reason) | Config knob |
|---|---|---|---|
| **Bold / emphasis** | 1. font name+weight tokens (`_font_weight_rank`) → 2. size-normalized glyph-width bimodality (`assemble._split_width_bold_fonts`, synthetic bold font idx) | `width-bold-split` / `width-bold-skip` (assemble) | thresholds: `_WIDTH_GAP`, `_VALLEY_RATIO`, `_WORD_BOLD_RATIO` (constants, not yet config) |
| **Lists** | struct tags `L/LI/LBody` → sequential ordinal paragraphs → consecutive bullet paragraphs → single-block bullet wrap → `»` jump markers → inline-bullet split of one paragraph; cross-page continuation merges | list `reason:` field (analyze): `"struct tags LBody/LI"`, `"sequential ordinal paragraphs"`, `"opens with a bullet…"`, `"list-from-inline-bullets"`, `"list-item-rejoined"`, `"list-continued(-bullet)"` | — |
| **Headings** | struct tag → size rank vs body → ALL-CAPS kicker → notes-section label → config override | heading `reason:` (analyze); `tag-conflict-heading` question on disagreement | `headingOverrides` |
| **Links** | real PDF annotations → color-styled cross-reference inference (`styled` flag; conservative) | node `links[*]` `styled` flag | — |

Wishlist (Nathan, soon): a **techniques report** (per-doc + corpus-wide tallies of
which method fired, plus method disagreements) as the corpus 10–50x's; and
config to enable/disable/order methods and override thresholds per document.