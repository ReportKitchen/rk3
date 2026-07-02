# Proposals layer — open calls (Q&A)

*2026-07-02. The design itself is in plans/proposals-layer.md; these are the
calls I shouldn't make by guessing. Same format as the car-ride doc: context,
my recommendation, and a blank for your notes. Half-formed answers are gold.*

---

**Q1. The auto-apply whitelist (your 4d, still unanswered).**
Autopilot needs a list of kinds that may apply without asking when confidence
is high. My proposed starting whitelist — everything else always asks:

- missing-space / glued-word fixes (pure fidelity, no judgment)
- footnote-residue rescues when the flag's arithmetic is exact (single-gap)
- alt text: **generated but never "applied silently"** — it's invisible in
  the render, so it auto-applies at *assist* already, marked, with the
  review-all-images tool as the gate
- NOT: reading order, heading levels, contrast, any deletion — always ask

My recommendation: start there, expand per-kind as trust builds (each kind
earns autopilot by its accepted/dismissed ratio in the dashboard).

> *your notes:*

agreed.

---

**Q2. Dismissals — per-document quirk or global pattern (your 4c)?**
When you dismiss "shorten this nav label" on one doc, should RK3 (a) shut up
about that label in this doc only, (b) stop suggesting nav-label shortening
for this whole doc, (c) learn an org-level preference? These imply different
machinery (pid-level vs kind-level vs settings mutation).

My recommendation: (a) is the record (pid-keyed, already designed), (b) is a
one-click "stop suggesting these here" that flips the per-doc kind toggle,
(c) is just the org defaults screen — no learning magic. All three cheap; the
UI phrasing is the real decision.

> *your notes:*

Agreed. And the familiar pattern of "Stop suggesting for this document | Don't suggest this for me ever again" works fine.  Along with a setting in prefs to clear it.  I don't think this is necessarily worth learning.


---

**Q3. Does the vision-QA triage board merge into proposals?**
The vision-QA roadmap called for its own triage board. The proposals store
can BE that board (findings land as `fidelity-diff` proposals, dev surface
filters by finder). One store, one disposition model, remap for free — but it
couples the dev loop to the proposals schema.

My recommendation: merge. A vision finding and a rule finding differ only in
`source`; two disposition systems would drift apart exactly like the three
container models did.

> *your notes:*

Agreed.  

---

**Q4. Assistance level names + the default.**
Working names: **faithful / suggest / assist / autopilot**, defaulting new
docs to **suggest**. You wanted better names than "might make changes
assistance" — do these read right for the comms-person persona? Is *suggest*
the right default for doc #1 (their baby), with the 3-docs-a-week persona
flipping their org default to assist/autopilot?

> *your notes:*

Honestly the branding needs a lot of work and I want it all to be coherent.

For now I'm happy with "Assistance Level: 0 (none) - 5 (autopilot) and we can tune the words later.

---

**Q5. Severity — who ranks, and on what scale?**
Issues get severity 1–5 for the dashboard sort. Rules can self-rank (missing
text = 5, spacing glitch = 2); vision findings come with model confidence,
not severity. Do you want a single blended "fix this first" ordering, or
issues-by-severity and opportunities-by-value as two separately-sorted lists?

My recommendation: two lists, two sorts; blending hides the
fidelity-vs-improvement distinction your whole philosophy runs on.

> *your notes:*

agreed

---

**Q6. Where do proposals live in the repo tree?**
Design says `<source>.proposals.jsonl` beside the PDF, like `.ops.json`. The
alternative is a `proposals/` dir like `feedback/`. Beside-the-source keeps
the "durable files near the doc" doctrine; the feedback-style dir keeps
generated churn out of `sources/`. Proposals regenerate on reconvert, so
they're churnier than ops.

My recommendation: `proposals/<slug>.jsonl` (feedback-style) — regenerated
files don't belong next to hand-authored ops; dispositions are the durable
part and they ride inside the same file either way.

> *your notes:*

Agreed

---

*Anything unanswered I'll resolve with the recommendation when the build
starts, and flag the choice in the commit message.*
