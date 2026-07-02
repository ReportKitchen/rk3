# Lessons from RK1 — read from the code, 2026-07-01

*Drafted by Claude after an archaeology pass over `/var/www/rk3/rk1`
(rpkn_profiler + rk_resil_import). Each lesson cites what the code actually
shows, then how RK3 answers it — or should. The `> your notes:` blocks are for
the human context the code can't show: what it felt like, what it cost, what
finally made you stop doing it.*

---

## 1. Fossil code accumulates when deletion isn't safe

**The evidence:** `get_dom_plugins.old.inc` beside `get_dom_plugins.inc`.
`footnotes.1.inc` beside `footnotes.inc`. `lists_OLD.inc`.
`cairo.complicated.inc`. Functions named `mso_fix_listsFAIL`,
`mso_fix_lists_hack`, `rk_braces_all_TODO`. `if (false) {` blocks labeled
"Old, complicated approach." Giant commented-out regions kept as
`// LOST+FOUND`.

**The mechanism:** without a regression net you can't prove a deletion is
safe, so failed attempts are kept "just in case" — and the file becomes a dig
site where the *current* logic is indistinguishable from the abandoned.

**RK3's answer:** git + the eval gate (delete freely; eval proves nothing
broke) + the no-backwards-compat doctrine. **The defense is only as strong as
eval coverage** — every fixed bug should keep minting assertions (the
"learning lock"). This is anti-spaghetti mechanism #1.

> your notes:

Some of the reason for this would be "coding for today's problem."  Footnotes and lists are two examples that come in very differently depending on the source.  We'd get a footnote routine dialed in, and the next doc would be so different we'd want to start over.  but.... what if the next one is like the last one.... let's save the code here just in case.  Some of that is pure sloppy coding but some does point to another concern -- coding for today's problem.

## 2. Ordering-by-comment is invisible coupling — the actual spaghetti recipe

**The evidence:** in v1.json: *"remove MS Word lang, spell, mso- spans" —
`// must come after fix-lists, and after lowercase_class_names`*. The machine
never sees that constraint; the next editor breaks it silently.

**Where RK3 has the same latent risk:** analyze.py's ~40 passes run in an
order that matters, documented only by comments ("a second pass: … the
intruder has been extracted"). This week's heading-aside work tripped exactly
this class of bug (grid output broke downstream list-grouping).

**The fix (architecture-review R2):** split analyze into modules with a
declared pass manifest — each pass states its contract (what it consumes,
what it may change, what must precede it), and the manifest is the one place
order lives.

> your notes:

so is the order always the same? we're not expecting to have to run different loops based on different inputs? 

## 3. Config-as-program becomes a per-document codebase

**The evidence:** each document's recipe (v1.json) is a *program*: an ordered
dict of steps, each naming a plugin + xpath + options. JSON has no comments,
so steps are disabled by renaming keys to `"//step"` — and there are inline
`// doesn't work?` comments that make the file unparseable by a standard JSON
parser (I tried; they bundled jsonlint to cope). Every document shipped its
own pipeline.

**RK3's answer (keep it this way):** ONE pipeline in code; config is
*parameters* (thresholds, modes, overrides), and one-off surgery is *ops* —
never per-document logic. When assistance-levels/org settings arrive, they
must stay parameters, not step lists.

> your notes:

OK so ops is a linear list of changes and is per-document, if needed.


## 4. Per-site forks mean fixes don't propagate

**The evidence:** every site got a `_import` module (hook_rkimport_info /
hook_rkimport_plugin_info) holding its content *and its own plugins*. A list
fix born in one site's module never reached the others.

**RK3's answer:** one engine, per-doc config/ops, and the
push-back-on-one-offs discipline (classify general / config / hand-edit).
The corpus-wide vision-QA loop is the anti-fork: fixes land in base code and
every document benefits.

> your notes:

I do feel like this is a balance though -- sometimes you do get something truely specific and it would be cluttering the code to build it into the codebase when there's every chance you'll never see situation again.  Are you suggestion no per-site code plugins at all?  Actually what would make sense would be a shared library so at least other sites can opt in to the improvement.  

But you tell me if I'm thinking about it wrong.

## 5. You built observability mid-crisis; RK3 built it first (keep feeding it)

**The evidence:** get_dom grew a per-step report table — matches, Δ nodes,
Δ kb, seconds per step — and `save_intermediate_html()` after each stage.
Also `get_get_dom_hints()`: counts of textboxes/comments/endnotes with a TODO
to "query plugins for stuff they could remove/fix" — literally a
proto-dashboard of suggestions, two generations before the current one.

**RK3's answer:** debug JSONL + data-rk, per-stage artifacts + fingerprints,
the audit, and now the vision-QA triage board. The hints TODO is the
proposals layer (architecture-review R4). This lineage is worth honoring: the
ideas survived even when the code didn't.

> your notes:

I do value being able to see what's going on at each step and where the failures are. But RK3's model is different enough that I don't expect to be debugging nodes of an IR and matching uuid's in a log to class names to find problems.  So yes dashboards and observability, but hopefully at a much higher level.

## 6. Parse the source, not a renderer's output

**The evidence:** MSO warfare everywhere: mso-list styles, VML namespaces,
conditional comments, spelle/grame spans, fake bullet glyphs (`·`, `o`) —
three visible generations of list-fixing (hack → FAIL → current). The
converter-HTML path fought the `[A-Z]{6}+` font-subset-tag regex —
**copy-pasted five times**.

**The lesson:** Word's HTML export and PDF-to-HTML converters are
*presentation* formats — parsing them means reverse-engineering someone
else's rendering hacks. RK3 reads the PDF itself per-glyph via pdfium.
**Directly relevant now:** when Word/GDocs import lands (1.0/1.1), enter
through docx XML / the Docs API — never through "Save as HTML."

> your notes:

Good to know.  I'll also mention the "braces" concept in case you were wondering.  As demands for transforms got more complex I'd resort to editing the Word file itself and inserting things like { class: rk-box-3 } and the code would pick that up and apply it.  I'm hoping this gets replaced entirely with ops created (1) by the user with point-and-click review, and (2) by agents translating a user's explanation of their goal, into ops.

## 6b. The escape hatch was a real product need, not a failure

**The context (user):** Cairo was a rarely-used *alternate pipeline* for PDFs
so highly designed/visual that automation was hopeless — the workflow dropped
to clicking and copying element by element, with page/chapter metadata
managed in a spreadsheet.

**The lesson:** some fraction of documents will always exceed the automatic
pipeline, and the answer isn't more heuristics — it's a *good manual path*
that produces the same output format as the automatic one. RK3 already
carries this DNA: the parked "atypical" corpus, the manual-reorder tool, the
ops layer, "bizarre glitches go to the edit-ops layer, not pipeline code."
Worth making explicit in the product: the manual path is a feature tier
(RK Custom *is* partly this), not an embarrassment. And the vision-QA "always
guess + flag" policy is what keeps the hatch rare.

> your notes:

Something I had drafted by never mentioned: I'm not afraid to use vision models to help out, during the actual user-led conversion. My thought would be their role would be to write ops, so while their review and recommendations might be non-determanistic, once a user accepted their recommendation, that becomes fixed.


## 7. Config in spreadsheets, state in the CMS — nothing regenerable

**The evidence:** cairo pulled its page/chapter metadata from a *live Google
Sheets published-CSV URL* at page load. Output shipped into Drupal as
nodes/books/menus; a *list page* quietly deletes lingering empty book menus
as a side effect (orphaned-state cleanup baked into a view). Everything
welded to Drupal 7 (dpm, variable_get, hooks).

**RK3's answer:** config in files beside the source; output as regenerable
static artifacts; the app is a viewer over artifacts, not their owner; stale
data is disposable. The Express-vs-FastAPI question matters less than this:
keep the engine's outputs framework-free.

> your notes:

## 8. Copy-paste idioms are early-warning spaghetti

**The evidence in RK1:** the font-subset regex ×5; report-formatting blocks
duplicated and half-commented.
**The evidence in RK3, today:** the feedback-JSONL read-modify-write idiom is
copy-pasted ~7× in app/main.py (no shared helper, no lock); two different
`_norm()` functions with different semantics (eval.py vs remap.py).

**The fix:** small, cheap, do it during R3 — one feedback-store helper, one
shared normalizer with named variants.

> your notes:

## 9. (yours to fill in — the lessons the code can't show)

What did RK1/RK2 teach that left no trace in the files? Pricing/scope
lessons, client-communication lessons, "we should have said no" lessons, the
moment you decided RK3 must be deterministic-first…

> your notes:

---

## The through-line

RK1's spaghetti didn't come from bad code — it came from **missing
affordances**: no tests (→ fossils), no declared ordering (→ comment-coupling),
no ops layer (→ per-site plugin forks), no artifact discipline (→ CMS-welded
state). RK3 built the affordances first. The one place the old risk pattern
is re-emerging is analyze.py's implicit pass ordering — which is exactly what
the R2 refactor (module split + pass manifest) exists to close.
