"""CMS-safe styling: fold the landing page's stylesheet into inline styles.

Some CMSes strip <style> blocks on paste (the email-HTML problem), so the
Publish step offers an inline-styled variant. css-inline (Rust-backed, the
maintained successor to premailer) does the cascade correctly; this module adds
the one thing it can't know: our CSS leans on `var(--lp-accent, fallback)`
custom properties, whose :root definitions vanish with the <style> block —
browsers would quietly use the fallbacks (losing the user's accent), and CMS
sanitizers sometimes strip var() outright. So every var() is resolved to a
concrete value first: the caller's value when provided, else the fallback.

Known, accepted losses (inherent to inline styles, same as any email export):
:hover polish, the share-button "Copied!" ::after bubble, and the @container
responsive tweaks. The float clearfixes (also ::after) are compensated by the
frontend, which appends real clear divs before asking for the inline variant.
"""
from __future__ import annotations

import re

import css_inline

# var(--name) or var(--name, fallback) — fallback may hold one level of nested
# parens (e.g. another function); nested var() in fallbacks is resolved by the
# outer substitution loop running until no var() remains.
_VAR = re.compile(
    r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*(?:\([^()]*\)[^()]*)*))?\)")


def resolve_vars(css: str, values: dict[str, str] | None = None,
                 max_rounds: int = 5) -> str:
    """Replace every var() reference with a concrete value."""
    values = values or {}

    def sub(m: re.Match) -> str:
        name, fallback = m.group(1), m.group(2)
        return values.get(name) or (fallback or "").strip()

    for _ in range(max_rounds):
        out = _VAR.sub(sub, css)
        if out == css:
            return out
        css = out
    return css


def inline_html(html: str, values: dict[str, str] | None = None) -> str:
    """Resolve var()s, then inline everything. Resolution runs over the WHOLE
    document, not just <style> blocks — the renderer also emits var() inside
    style="" attributes (e.g. the accent on embedded download buttons), and the
    `var(--` shape can't occur in our generated text or scripts."""
    return css_inline.inline(resolve_vars(html, values), keep_style_tags=False)
