"""Unified content registry — one keyed store for every text piece the product
sends out: static UI copy, token templates, AI prompts, and AI-generated-with-
fallback strings. Supersedes the prompt-only loader (rk3/prompts.py) with one
mechanism that also owns UI copy and per-piece model preferences.

KEYS ARE NAMESPACED BY SCOPE so the same registry serves all of RK3, and it's
obvious which app owns a string:

    shared.<domain>.<name>   reusable across apps — doc analysis, extraction,
                             the guidance engine (any RK3 app can pull these)
    lpm.<domain>.<name>      Landing Page Maker only
    core.<domain>.<name>     the shared app shell / chrome
    express.* / custom.*     other RK3 products (future)

Scope + domain come from the file path (content/<scope>/<domain>.yml); the name
is the key within that file. Full key = "<scope>.<domain>.<name>".

ENTRY KINDS
    static    a fixed string                      → text
    template  a string with {tokens}              → text, tokens
    prompt    text sent to a model                → text, model?
    ai        AI writes it when AI is on, else a  → prompt, model?, fallback
              static fallback                        (fallback is a template too)

Files are read fresh (mtime-checked), so edits take effect on the next call with
no restart — the same live-edit property the old prompt files had. The store is
plain YAML: git-backed, reviewable, and modelable by a git-backed CMS (TinaCMS)
when we want an editing UI over it.
"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"

KINDS = ("static", "template", "prompt", "ai")

_cache: dict = {}
_cache_sig = None


def _signature() -> tuple:
    """Max mtime + file count under content/, so any edit/add/remove reloads."""
    files = sorted(CONTENT_DIR.rglob("*.yml"))
    return (len(files), max((f.stat().st_mtime for f in files), default=0.0))


def _load() -> dict:
    """Build {full_key: entry} from every content/<scope>/<domain>.yml."""
    global _cache, _cache_sig
    sig = _signature()
    if sig == _cache_sig and _cache:
        return _cache
    reg: dict = {}
    for f in sorted(CONTENT_DIR.rglob("*.yml")):
        rel = f.relative_to(CONTENT_DIR)
        if len(rel.parts) < 2:
            continue  # need at least <scope>/<domain>.yml
        scope = rel.parts[0]
        domain = f.stem
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for name, entry in data.items():
            if not isinstance(entry, dict) or "kind" not in entry:
                raise ValueError(f"content: {rel}:{name} needs a 'kind'")
            if entry["kind"] not in KINDS:
                raise ValueError(f"content: {rel}:{name} has unknown kind {entry['kind']!r}")
            reg[f"{scope}.{domain}.{name}"] = {**entry, "_scope": scope, "_domain": domain}
    _cache, _cache_sig = reg, sig
    return reg


def get(key: str) -> dict:
    """The raw entry for a key. Raises KeyError — a missing key is a bug."""
    reg = _load()
    if key not in reg:
        raise KeyError(f"content: no entry {key!r}")
    return reg[key]


def _interpolate(s: str, tokens: dict) -> str:
    """Fill {name} tokens. Server-side is deliberately simple substitution; the
    frontend does full ICU (plurals/conditionals) on the same strings."""
    return re.sub(r"\{(\w+)\}", lambda m: str(tokens.get(m.group(1), m.group(0))), s or "")


def text(key: str, **tokens) -> str:
    """Resolve a static / template string (or an ai entry's fallback) with tokens.
    Not for prompt entries — use prompt()."""
    e = get(key)
    if e["kind"] == "prompt":
        raise ValueError(f"content: {key} is a prompt; use prompt()")
    src = e.get("fallback") if e["kind"] == "ai" else e.get("text", "")
    return _interpolate(src, tokens)


def prompt(key: str) -> tuple[str, str | None]:
    """(prompt_text, model_or_None) for a prompt / ai entry. model=None means the
    caller's configured default (config.json ai) applies."""
    e = get(key)
    if e["kind"] not in ("prompt", "ai"):
        raise ValueError(f"content: {key} is {e['kind']}, not a prompt")
    body = e.get("text") if e["kind"] == "prompt" else e.get("prompt", "")
    return body, e.get("model")


def entries(scope: str | None = None, kinds=("static", "template", "ai")) -> dict:
    """Public copy for a scope, keyed, for the frontend (`/api/content`). Prompt
    bodies are never shipped to the client — only their text/fallback for `ai`.
    A None scope returns everything in the given kinds."""
    out = {}
    for key, e in _load().items():
        if e["kind"] not in kinds:
            continue
        if scope and e["_scope"] not in (scope, "shared", "core"):
            continue
        val = {"kind": e["kind"], "tokens": e.get("tokens", [])}
        val["text"] = e.get("fallback", "") if e["kind"] == "ai" else e.get("text", "")
        out[key] = val
    return out
