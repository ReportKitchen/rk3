"""Content-registry enforcement, layer 3 (Python half) — the "nothing hardcoded"
teeth for prompts. See sources/docs/DEFERRED/content-registry-enforcement.md.

A prompt sent to a model must come from the registry (`content.prompt(key)`, or
legacy `load_prompt`), never a string literal inlined at the call site. This test
walks the Python source with `ast` and FAILS the build when:

  * a string literal is passed as the `system=` or `user=` prompt to
    `complete_json` / `vision_json`, or
  * `.messages.create(...)` is called at all outside `rk3/ai.py` (the single
    sanctioned chokepoint to the SDK).

It intentionally allows variables, `content.prompt(...)`, f-strings built from
registry text, etc. — only inline string *literals* are violations.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# the one file allowed to hold the raw SDK call + assemble the request
AI_MODULE = ROOT / "rk3" / "ai.py"
SCAN_DIRS = [ROOT / "rk3", ROOT / "app"]
PROMPT_FUNCS = {"complete_json", "vision_json"}


def _py_files():
    seen = set()
    for base in SCAN_DIRS:
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if "__pycache__" in p.parts or p == AI_MODULE:
                continue
            if p not in seen:
                seen.add(p)
                yield p


def _is_string_literal(node: ast.AST) -> bool:
    """A hardcoded prompt: a plain string, an f-string, or string concatenation."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if isinstance(node, ast.JoinedStr):  # f"..."
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _is_string_literal(node.left) or _is_string_literal(node.right)
    return False


def _func_name(call: ast.Call) -> str:
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def _is_messages_create(call: ast.Call) -> bool:
    f = call.func
    return (isinstance(f, ast.Attribute) and f.attr == "create"
            and isinstance(f.value, ast.Attribute) and f.value.attr == "messages")


def _violations_in(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _is_messages_create(node):
            out.append((node.lineno, "`.messages.create(...)` outside rk3/ai.py — "
                        "route model calls through complete_json/vision_json"))
            continue
        name = _func_name(node)
        if name not in PROMPT_FUNCS:
            continue
        # positional system=arg0, user=arg1
        for idx, label in ((0, "system"), (1, "user")):
            if len(node.args) > idx and _is_string_literal(node.args[idx]):
                out.append((node.args[idx].lineno,
                            f"literal {label}= prompt in {name}(...) — use content.prompt(key)"))
        for kw in node.keywords:
            if kw.arg in ("system", "user") and _is_string_literal(kw.value):
                out.append((kw.value.lineno,
                            f"literal {kw.arg}= prompt in {name}(...) — use content.prompt(key)"))
    return out


def test_no_hardcoded_prompts():
    problems = []
    for path in _py_files():
        for lineno, msg in _violations_in(path):
            problems.append(f"{path.relative_to(ROOT)}:{lineno}: {msg}")
    assert not problems, (
        "Hardcoded prompt(s) / model call(s) found — prompts must live in the "
        "content registry (content.prompt(key)):\n  " + "\n  ".join(sorted(problems))
    )
