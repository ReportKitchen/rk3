# Architecture Review — 2026-07-01

*Requested after the north-star clarification ("this looks just like my document,
but webified") exposed a drift: the team was building toward an idealized pure
semantic pipeline while the user kept asking for fonts and colors to match.
Question on the table: solid foundation or house of cards? What refactoring
serves the fidelity-first path?*

Scope: full read of extract.py (632), assemble.py (709), analyze.py (3,494),
render.py (1,257), pipeline.py, config.py; scouted surveys of app/main.py,
app/ui, eval.py, remap.py, documents.py, and the generated CSS of real outputs.

---

## Verdict: solid foundation, with one honest confession and one real risk

**This is not a house of cards.** The load-bearing walls are genuinely good —
better than the recent visual output suggests. The misalignment you felt is
real, but it is *localized*: the "pure semantic idealization" bias does NOT
live in the architecture. It lives in **one aggregation policy**
(`render._original_css`, a deliberate summarizer) **plus a handful of
taste-gates** that discard captured style data on the way out. The capture side
has been fidelity-first all along.

The one real structural risk is analyze.py — a 3,494-line monolith of ~40
ordered passes whose interactions are the fragile part. It needs structure,
not a rewrite.

---

## 1. What's already RIGHT for the fidelity-first path (the good bones)

**Extract captures nearly everything appearance needs.** Per-char color +
size + *exact font program identity* (embedded programs hash-identified, so
same-named cuts stay distinct); true weight/italic read from the font program
with glyph-ink ranking when programs lie; faux-italic matrix shear detection;
every vector object with fill/stroke/per-side border segments; RGBA palette;
link annotations; struct-tree roles + declared reading order; page PNGs; and
reconstructed browser-servable OTFs of the embedded fonts with coverage
tracking. This layer needs almost nothing for the new north star.

**The 4-layer CSS cascade is exactly the right architecture** for "match their
document by default, house style as an option": layout.css (geometry) /
default.css (house skin) / original.css (generated per-doc from provenance) /
embed.css (the PDF's own fonts, var()-toggleable). The fidelity pivot requires
no re-architecture — it requires original.css to *say more*.

**The "1800 classes" fear is already engineered away.** Identical style
departures share one named class (.lead/.fine/.accent/.caption…), not a pile of
per-node selectors. Per-node rules exist only where truly per-node (callout
fills, floats, table styles). Full fidelity will grow this, but boundedly.

**A real safety culture, in code.** The per-page character audit (in / out /
claimed / moved / lost — silent content loss becomes a logged failure);
`_assert_rich_items` raising `InfoLossError` when a list item would drop its
style runs; every decision logged with rk keys; the fingerprint chain making
stale builds visible; the eval suite gating changes. These are the habits that
prevent houses of cards.

**Durability machinery already exists for the product vision.** Stable
content-derived nids + remap keep feedback and edit-ops anchored across
reconversions; the ops layer (set-text / delete / set-level / reorder / merge)
survives re-renders. This is the substrate the magic-button dashboard needs —
it's already built.

**The engine seam exists.** render.py consumes ir.json only. Word/GDocs can
enter as a second engine emitting IR; the UI/feedback/eval layers ride on
top unchanged.

---

## 2. The fidelity gap — specific, with receipts

`_original_css` is a **lossy summarizer**: it reduces rich capture to
per-block dominant font/color/size, votes one link color, and defers all
spacing to the house skin. The old "faithful to information, NOT the pixels"
north star is encoded here. Concretely dropped between artifact and output:

| # | Captured but not rendered | Where it dies |
|---|---|---|
| 1 | **Inline colored words** (non-link, non-highlight) | `_build_runs` uses color runs only for styled-link inference + marks; rubric §3 ("promote to strong + class") unimplemented |
| 2 | **Page & panel background colors** (full-bleed fills, color blocks) | analyze drops >85%-page fills and unclustered panels; original.css never emits `body{background}` |
| 3 | **Near-white / light-on-dark text** | `_usable_color` discards it — *because* #2 isn't rendered; fix #2 and this unlocks |
| 4 | Paragraph size departures **< 12%** | `feed_exception` threshold |
| 5 | **Decorative rules/dividers/accent bars** | dropped unless they became a callout border |
| 6 | **Alpha channel** (RGBA captured, hex-6 emitted) | `_hex` |
| 7 | **Line-height / letter-spacing / text-transform** | never captured into IR at all |
| 8 | White/near-white **callout fills → transparent** | render aside styling |
| 9 | Vertical rhythm / margins / column width | house layout.css (42rem) |
| 10 | Underlines (as drawn rules under text) | never associated with text |

Items 1–5 are the visible "doesn't look like my document" drivers and are all
render/analyze-policy changes, not new capture. Items 6–10 are second tier.

Also fidelity-adjacent: figures are cropped from the rendered page PNG;
rubric §7 wants them lifted from the source image objects (extract already
enumerates them).

## 3. The real structural risk: analyze.py

3,494 lines, ~40 sequential passes (regions → captions → notes → reading order
→ node build → lead-heading promotion → 6 list-grouping passes → 4 join passes
→ pullquotes → floats → …). **Order matters and passes interact** — this
week's heading-aside fix broke list grouping until its output shape changed;
that class of coupling is where a house of cards *could* grow. Mitigations
(eval gate, logging, audit) are real but the file needs structure:

- Split into modules along its natural seams (`regions.py`, `tables.py`,
  `headings.py`, `lists.py`, `notes.py`, `order.py`, `joins.py`,
  `pullquotes.py`) with `analyze.py` reduced to the declared pass manifest.
- Each pass gets a one-line contract (input shape → output shape, what it may
  touch). Pure code motion, zero behavior change, eval-gated.

## 4. Contract debt (cheap insurance, worth paying soon)

- **ir.json has no version boundary.** The browser fetches it raw; eval,
  remap, and main.py walk it with *inconsistent depth* (2-level vs full
  recursion). Any schema change is a silent multi-surface break. Fix: a
  written IR schema doc + `irVersion` field + one shared walker.
- The **DOM contract** (`data-nid`/`data-page`/`data-yf`, `#css-original`,
  `#css-embed`, `page-%04d.png`) is duplicated between render and the SPA by
  string convention. Document it; consts in one place.
- Feedback JSONL read-modify-write is copy-pasted ~7× in main.py with no lock
  (concurrent writes can drop entries); eval's `append_check` string-splices
  YAML. Small hardening items.
- Dead code: `app/static/` legacy viewer.

## 5. The missing architectural slot: the enhancement layer

The product now clearly needs a home for: magic-button fixes, element-level
OCR (tables/charts/diagrams → HTML), alt-text generation, assistance-level
gating. Today everything must be either deterministic pipeline code or a
manual op. **The right slot already half-exists: grow the ops vocabulary.**

- AI/enhancement passes produce **proposals** (like vision-QA flags — stored,
  severity-ranked, reviewable).
- Accepting a proposal (or pressing the magic button) converts it to an **op**
  (new verbs: `insert-node`, `replace-figure-with-table`, `set-alt`,
  `set-style`). Ops are durable, logged, remapped, applied at render — which
  satisfies the 5c requirement (*all generated content marked in-place and
  reviewable*) for free, and keeps the deterministic pipeline sacred.
- Assistance-level settings become config that filters which proposals are
  even generated/offered.

**OCR doctrine, corrected (user, 2026-07-01):** "No OCR" only ever meant *no
whole-document OCR of scanned PDFs* (the scanned-gate stays). Element-level
OCR — getting text/data out of table images, charts, diagrams — is a big win
for every goal and is sanctioned. It enters through the proposals path above
(default-on attempt for tables per rubric §6, with converted/original toggle).

## 5a. Order of operations — governed by the Phase Contract

Adopted after the RK1 archaeology: **sources/docs/phase-contract.md** is the
constitution for R2 and R4. Summary: Evidence → Structure (ordered, declared)
→ **the nid line** → Enhancements (ops targeting nids, applied at one point)
→ Views (pagination/nav as pure functions). Laws: no positional addressing
below the nid line; pagination is a function, never a stage; page-relative
placement is authoring-convenience only; phase-2 ordering is declared in a
manifest, not remembered in comments.

## 6. Ranked plan

| # | What | Why now | Size |
|---|---|---|---|
| R1 | **Close the fidelity gap in render** (items 1–5: inline color runs → styled spans; backgrounds/panels; un-gate `_usable_color`; lower size gate; decorative rules) | Directly serves the north star; all data already captured; vision-QA measures the delta per change | M, incremental |
| R2 | **Split analyze.py into modules + pass manifest** | The house-of-cards insurance; makes every future cycle safer | M, mechanical |
| R3 | **IR schema doc + version + shared walker; DOM contract doc** | Cheap; protects UI/eval/remap and the future Word engine | S |
| R4 | **Proposals layer on grown ops vocabulary** | Unblocks magic buttons, element-OCR, alt-text, assistance levels — the product differentiators | M–L |
| R5 | **Word/GDocs seam prep** (source-type routing; engine-per-source in STAGES) | User: near-term (1.0/1.1); prep is cheap, engine itself comes later | S prep |

**Explicitly NOT doing:** rewriting analyze heuristics (they encode hundreds of
verified document behaviors — that's an asset); CSS normalization / the clean
3-part style guide (phase 2, per the styles-system doctrine); building the
docx engine now; pixel-diff rendering (the north star is *recognizably theirs*,
not a raster clone).

## 7. One-line answer to the fear

The foundation is solid — capture, provenance, safety rails, and the CSS
layering were all built fidelity-ready. What drifted was a *policy*, mostly in
one generated stylesheet, that summarized where it should have reproduced.
That's a correction, not a rebuild.
