# Avoid permission problems

When inspecting files, prefer Claude Code's built-in Read, Glob, and Grep tools.
Do not use Bash for read-only file discovery or code search unless explicitly requested.

Avoid shell pipelines like find | grep | head, grep -r, sed -n, awk, xargs, or compound semicolon/&& chains for code inspection.

Use Bash only for commands that truly need execution, such as package scripts, tests, builds, migrations, and git commands, and then, avoid bundling steps together: run one simple command per call so it can match an allow-rule (e.g. `Bash(node:*)`). Compound commands, pipes, and redirects can't be auto-approved and will force a permission prompt no matter what permissions are granted.

Never create or edit files through Bash. Do not use `cat > file`, heredocs (`<< EOF`), `echo >`, `tee`, `sed -i`, or any output redirection (`>`, `>>`) to write files — output redirection is a filesystem write that no command allow-rule can cover, so it always prompts. Use the Write tool to create files and the Edit tool to modify them, then run the resulting file with a plain command (e.g. `node /tmp/script.mjs`).


