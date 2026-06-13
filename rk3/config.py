"""Per-document config: <name>.config.json alongside the PDF, merged over defaults."""

import copy
import json
from pathlib import Path

DEFAULTS = {
    "input": {
        "pageRange": None,            # [first, last] 1-based inclusive, or null for all
        "scannedTextThreshold": 100,  # median chars/page below this => scanned, bail
        "headerFooterZones": None,    # override [topFrac, bottomFrac], e.g. [0.12, 0.12]
        "columnHint": None,           # future: force column count
        "pageImageScale": 2,          # scale for the page PNGs written by extract
    },
    "structure": {
        # [{"textPrefix": str, "level": int}] — level 0 forces paragraph;
        # consumption path for heading-or-paragraph / caps / tag-conflict answers
        "headingOverrides": [],
        # [{"textPrefix": str, "breaks": bool}] — consumption path for
        # hard-returns answers
        "breakOverrides": [],
        "calloutHints": [],           # future
        "footnotePlacement": "end",   # v1: always end of document
        "dropToc": True,
        # asides whose text duplicates nearby body text (print pull-quotes):
        # "keep" (floated decoration, aria-hidden) or "drop"
        "pullQuotes": "keep",
        # answers to figure-or-callout questions, applied on re-run:
        # [{"page": n, "bbox": [l,b,r,t], "kind": "figure"|"callout"}]
        "regionOverrides": [],
        # design-element numerals glued to headings ("4Institutional"):
        # "styled" (separate <span class="section-number">), "inline" ("4. X"),
        # or "removed"
        "sectionNumbers": "styled",
        # paragraphs indented from the page's prevailing left edge: web
        # convention flushes them left ("remove"); "preserve" keeps the
        # indent in layer 3. Per-paragraph answers:
        # [{"textPrefix": str, "mode": "preserve"|"remove"}]
        "indents": "remove",
        "indentOverrides": [],
    },
    "output": {
        "imageScale": 2,
        "cssLayers": ["layout", "default", "original"],
        "autolinkUrls": True,  # plain-text URLs/DOIs become <a class="autolink">
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_config(pdf_path: Path) -> dict:
    cfg_path = pdf_path.with_suffix("").with_name(pdf_path.stem + ".config.json")
    if cfg_path.exists():
        cfg = _deep_merge(DEFAULTS, json.loads(cfg_path.read_text()))
    else:
        cfg = copy.deepcopy(DEFAULTS)
    # edit ops: durable per-element operations (viewer-written), applied at
    # render; loading them into cfg puts them in the render fingerprint, so
    # an op change re-runs render alone
    ops_path = pdf_path.with_name(pdf_path.stem + ".ops.json")
    cfg["ops"] = json.loads(ops_path.read_text()) if ops_path.exists() else []
    return cfg


def config_slice(cfg: dict, keys: list[str]) -> dict:
    """Extract the subset of config a stage depends on, by dotted key prefix."""
    out = {}
    for key in keys:
        node, parts = cfg, key.split(".")
        try:
            for p in parts:
                node = node[p]
        except (KeyError, TypeError):
            continue
        out[key] = node
    return out
