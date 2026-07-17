# DEFERRED · Content-registry enforcement (the "nothing hardcoded" teeth)

**Status:** deferred to get on with the LPM design rebuild.
**Context:** the content registry is built and in use — `rk3/content.py` (loader +
`validate()`), `content/*.yml`, `GET /api/content`, `app/ui/src/content.js` (`t()`),
and the CLAUDE.md "Content & copy" convention. Commits `28d1391`, `d57bf2b`.

Two of the four enforcement layers exist (**convention** in CLAUDE.md, **validator**
via `python rk3/content.py`). Those keep the registry well-formed and steer future
work, but they do **not** catch a string that gets hardcoded and never added. This
doc is the remaining two layers — the ones that turn "please don't hardcode" into
"hardcoding fails the build."

## Layer 3 — lint gate for hardcoded copy/prompts (the actual teeth)

Wire into CI (and ideally pre-commit) so a hardcoded user-facing string or an
inline prompt **fails the build**.

- **Frontend — no literal JSX strings.** Add `eslint-plugin-i18next`
  (`no-literal-string`) or the formatjs equivalent to `app/ui`'s eslint config.
  It flags user-facing string literals in JSX text and human-readable props.
  Needs an **allowlist** to avoid noise on day one: className/id/test-id, aria
  roles, URLs/paths, `data-*`, purely technical constants, and single symbols.
  Start in `warn`, burn down the existing hardcoded copy as it's migrated, then
  flip to `error` in CI.
- **Python — no raw prompt into a model call.** A small custom check (a pytest,
  or a ruff/flake8 plugin, or a grep-based CI step) that fails when a string
  *literal* is passed as `system=`/`user=` to `complete_json` / `vision_json`, or
  to `client.messages.create` outside `rk3/ai.py`. Prompts must come from
  `content.prompt(key)` (or, until migrated, `load_prompt`).

## Layer 4 — structural chokepoint for prompts (strongest; optional)

Change `rk3/ai.py`'s entry points (`complete_json`, `vision_json`) to take a
**content key** instead of a raw system string — they resolve the prompt (and its
per-piece model) from the registry themselves. Then it is *impossible* to send a
prompt that isn't in the registry; layer 3's Python check becomes redundant.
Cost: touches every AI caller, so do it as prompts migrate off `prompts/*.md`.

## Known limit (not solvable by tooling)

**Scope placement** (`lpm.*` vs `shared.*`) is a judgment call no linter makes.
Tooling can enforce "the key exists and is used," not "this string is correctly
categorized." Convention + the "start narrow, promote when a second app needs it"
rule + review is the realistic answer.

## Pick this up when

- A second contributor (human or a less-supervised agent) starts touching UI/AI
  code, **or**
- before GA / first external users, **or**
- right after the LPM rebuild lands, when there's a fresh batch of copy + the
  guidance-engine prompts to migrate in — do the migration and stand up the gate
  in the same pass so the new code ships already-compliant.
