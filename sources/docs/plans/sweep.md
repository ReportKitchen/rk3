> **STATUS:** ACTIVE — companion to [webified.md](webified.md). Stage 0 (truth pass) runs before the webified cycle; Stages 1-6 run after the webified verdict. The LEDGER at the bottom is durable state.

# SWEEP: root out the old, the inaccurate, and the disused

*(Authored by Fable 2026-07-03. Companion to plans/webified.md. Stage 0
is SAFE and RECOMMENDED to run BEFORE the webified cycle; everything else
runs AFTER the webified verdict — the run changes what counts as disused,
and sweeping first means sweeping twice. Same execution rules as
webified.md §0: stakes/census/snapshot gates for anything touching code,
never edit owner files, commit small by name, PARK what's undecidable.)*

## Why this order

The clutter is not all the same kind of thing:
- **Docs that LIE** (stale progress claims, superseded plans that
  contradict the code) actively mislead an unattended executor → fix
  BEFORE webified (Stage 0).
- **Test artifacts** are mostly load-bearing: eval yamls are the
  regression net, committed `output/` is the baseline `git show HEAD:`
  diffs adjudicate against, feedback jsonls feed the vision loop → keep
  until after, then prune with evidence.
- **Dead code/routes** are inert clutter → after, when the webified run
  has also revealed which paths the new architecture obsoletes.

## INBOX (webified executor: PARK cleanup candidates here as you work)

*(empty)*

---

## Stage 0 — TRUTH PASS (safe pre-webified; docs only, no deletions)

Make every document tell the truth about its own status. No file moves,
no deletions — only headers and corrections.

**0.1 Plan status headers.** Every file in `sources/docs/plans/` gets a
first-line status header:
`> STATUS: SHIPPED (vNNN-vNNN, commits …) | ACTIVE | SUPERSEDED by <plan>`
Verify each claim against `git log --oneline` and the code — do not trust
the PROGRESS blocks blindly; they were written mid-flight. Known truths
to encode: columns-reading-order phases 0-2 + sweep SHIPPED, 3-5 open
(order-pin superseded by webified §3.2 orderPin — mark it); lists.md
L1-L6 SHIPPED with named residue; figures.md phases 0-5 SHIPPED, 6 open
(reproduction tiers absorbed into webified §5/§6 — mark it); proposals-
layer.md status vs what actually shipped (questions exist; proposals
kind does NOT — say so).

**0.2 Root docs.** `README.md`, `AGENTS.md`, `CLAUDE.md`: verify every
instruction and path is current (service port 8300, venv, eval
invocation, plan locations, the webified/sweep pair). Fix or delete
stale lines. `consider-PyMuPDF.txt`: PyMuPDF was adopted (pinned
1.27.2.3, figures phase 4) — replace the file's content with one line
pointing at figures.md phase 4, or fold and delete.

**0.3 Specs and features.** `sources/docs/specifications/`,
`sources/docs/features/`: status headers only (which are implemented,
which are aspirational). Do not rewrite content.

**0.4 Eval yaml comments.** Scan `eval/*.yaml` for comments that state
things now false ("expected to FAIL until then" on checks that now pass,
etc.). Fix the comments; do not touch the checks themselves. The tenure
yaml has a literal duplicated order check (two identical p13 pairs) —
leave the checks (owner-minted; harmless) but note the duplication in a
comment.

**Gate**: `python -m rk3 eval` count unchanged; pytest green; one commit
per numbered item.

---

## Stage 1 — INVENTORY (read-only; after webified verdict)

Produce `sources/docs/plans/sweep-manifest.md`: every candidate with a
verdict — KEEP / ARCHIVE / DELETE / MERGE / **DECISION(owner)** — and
evidence (last git touch, referenced-by grep, imported-by, route called
by UI?). Categories to walk:

- `sources/docs/**` (plans, features, specifications, QA docs)
- `eval/*.yaml` + `eval/inactive/*` (why inactive? reactivate or archive)
- `tests/` (snapshot size/robustness; anything skipped)
- `feedback/*.jsonl` (cleared-note retention; swept vision issues;
  orphaned nids after remaps)
- `output/pdfium/**` committed artifacts (see DECISIONS below)
- `tools/`, stray root files, `rk1/` (the predecessor system — likely
  ARCHIVE candidate; grep for anything importing it first)
- `app/main.py` routes vs `app/ui/src/api.js` calls (routes no UI calls;
  UI calls with no route)
- `app/ui/src/components/` unmounted components
- `rk3/` dead code: functions defined but never called (grep-driven),
  "legacy shim until step N" comments whose step N shipped, unused
  config keys (`calloutHints`, others), unused imports
- CSS: selectors matching nothing the renderer emits
- venv deps: installed-but-unimported (pip list vs grep) — note only,
  no manifest-less uninstalls (there is no requirements file; propose
  creating one as a DECISION)

## Stage 2 — DOCS CONSOLIDATION

- `sources/docs/INDEX.md`: one page saying which doc is authoritative
  for what, linking the status headers from Stage 0.
- Shipped plans: move their long PROGRESS narratives into
  `sources/docs/plans/archive/<plan>-progress.md` if and only if the
  plan header links there; keep the plan body lean.
- Resolve contradictions between docs in favor of code + git history;
  when intent is genuinely unclear, DECISION(owner).

## Stage 3 — TEST ARTIFACTS

- Apply manifest verdicts to eval/inactive (reactivate any whose docs
  now convert cleanly — run them first).
- Feedback: propose (DECISION) a retention policy for `status: cleared`
  notes and swept vision issues (e.g., archive to
  `feedback/archive/<slug>.jsonl` after 30 days). Implement only after
  owner rules.
- Verify `tests/snapshot.json` covers every convertible source doc; add
  missing ones.

## Stage 4 — DEAD CODE AND ROUTES

Each removal is a normal engine change: census + pytest + (if render
touched) VERSION bump + eyeball one affected page. Remove in small
commits, one concern each. If a "dead" function turns out reachable via
config/ops paths, KEEP with a comment saying who calls it.

## Stage 5 — MEMORY HYGIENE

`/home/ubuntu/.claude/projects/-var-www-rk3/memory/`: shipped tracks
marked as shipped in their descriptions; stale next-steps corrected;
index lines match file contents. Follow the memory conventions (update
in place; delete only provably-wrong entries).

## Stage 6 — REPORT

`sources/docs/plans/sweep-report.md`: what was removed/archived (with
commit refs), what was kept and why, the DECISIONS list for the owner,
and repo size / route count / dead-code deltas.

---

## DECISIONS (owner input required — collect, don't block)

- **`output/` in git**: every commit carries thousands of lines of
  regenerated artifacts. Pro: `git show HEAD:` baselines power the
  snapshot-adjudication ritual and remap safety. Con: repo bloat, noisy
  diffs. Options: keep as-is / gitignore + keep a `baselines/` copy of
  ir.json only / git-lfs. Recommend: keep ir.json + index.html tracked,
  gitignore pages/ and images/ (they regenerate deterministically and
  are never diffed). Needs owner sign-off — changes the daily ritual.
- **requirements.txt**: none exists; venv is hand-managed (pymupdf pin
  matters). Recommend creating one. Trivial but changes dev setup docs.
- **`rk1/`**: archive out of the working tree, or keep as reference?
- **Cleared-note retention** (Stage 3).

## LEDGER

*(newest on top)*

- **Stage 0.2 — root docs DONE** (2026-07-03). README.md, AGENTS.md,
  CLAUDE.md audited line-by-line: all current (port 8300, `.venv/bin/python`,
  systemd `rk3` + `--reload` scoping, `npm run build`, AI tiers, default
  `claude-opus-4-8`, `python -m rk3 list/convert/remove`) — no stale lines.
  `consider-PyMuPDF.txt` was already deleted by the owner (commit 506213a
  "don't need this"); its one dangling reference in figures.md §Phase 4 fixed
  to say ADOPTED (1.27.2.3). No census-affecting changes.

- **Stage 0.1 — plan status headers DONE** (2026-07-03). Added a first-line
  `> **STATUS:**` blockquote to every file in `sources/docs/plans/` (10 files
  + this file + webified.md). Statuses verified against `git log` and code,
  not the PROGRESS blocks: columns 0-2+sweep SHIPPED / 3-5 open (order-pin
  SUPERSEDED by webified §3.2); figures 0-5 SHIPPED (v169-196) / 6 absorbed
  into webified §5-6; lists L1-L6 SHIPPED / residue named; proposals-layer
  DESIGN-not-built (verified zero `proposals` refs in rk3/); pdf-js PROPOSED-
  not-built (no pdfjs-dist / PdfJsPane); post-container §1-2 SHIPPED (irVersion
  @ analyze.py:670, rk3/irwalk.py exists) / §3-4 open; pattern-track ACTIVE
  (other agent); unified-container SHIPPED. Baseline census locked at **71
  passed / 6 failed** (doc-only edits cannot move it). Reds: atlantic p6,
  foia p4, edf running-footer, covid p7, jhu p20 endnotes, tenure p14 order
  4<5 (the webified §3.2 orderPin target).

## PARKED

*(empty)*
