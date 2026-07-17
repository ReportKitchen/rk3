# Avoid permission problems

When inspecting files, prefer Claude Code's built-in Read, Glob, and Grep tools.
Do not use Bash for read-only file discovery or code search unless explicitly requested.

Avoid shell pipelines like find | grep | head, grep -r, sed -n, awk, xargs, or compound semicolon/&& chains for code inspection.

Use Bash only for commands that truly need execution, such as package scripts, tests, builds, migrations, and git commands, and then, avoid bundling steps together: run one simple command per call so it can match an allow-rule (e.g. `Bash(node:*)`). Compound commands, pipes, and redirects can't be auto-approved and will force a permission prompt no matter what permissions are granted.

Never create or edit files through Bash. Do not use `cat > file`, heredocs (`<< EOF`), `echo >`, `tee`, `sed -i`, or any output redirection (`>`, `>>`) to write files — output redirection is a filesystem write that no command allow-rule can cover, so it always prompts. Use the Write tool to create files and the Edit tool to modify them, then run the resulting file with a plain command (e.g. `node /tmp/script.mjs`).

# Content & copy — never hardcode text

Every user-facing string and every model prompt lives in the **content registry** (`content/*.yml`, loaded by `rk3/content.py`). Do NOT hardcode them.

- **UI copy:** render with `t(key, tokens)` on the frontend (`app/ui/src/content.js`) or `content.text(key, **tokens)` on the server. Never put a user-facing string literal in JSX or server-rendered output. Token strings use ICU (`{n, plural, one {# story} other {# stories}}`).
- **AI prompts:** load with `content.prompt(key)` (returns text + optional per-piece model). Never inline a system/user prompt string in Python. (Legacy `prompts/*.md` still load via `rk3/prompts.py`; migrate a prompt into the registry when you next touch its caller.)
- **AI-written copy** goes in an `ai`-kind entry with a static `fallback` for when the user has AI off — so nothing renders blank.
- **Scope keys correctly** (`<scope>.<domain>.<name>`): `shared.*` for anything about the document itself (analysis, findings, the guidance engine — reusable across RK3 apps); `<app>.*` (e.g. `lpm.*`) for one app's UI. Start narrow, promote to `shared.*` when a second app needs it. See `content/README.md`.
- After editing `content/`, run `python rk3/content.py` — it validates kinds, required fields, and token declarations, and is the CI/pre-commit gate.

If you find hardcoded copy or an inline prompt while working nearby, move it into the registry rather than adding more.


