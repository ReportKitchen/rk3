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
        "headingOverrides": [],       # future: explicit text/size -> level rules
        "calloutHints": [],           # future
        "footnotePlacement": "end",   # v1: always end of document
        "dropToc": True,
        # answers to figure-or-callout questions, applied on re-run:
        # [{"page": n, "bbox": [l,b,r,t], "kind": "figure"|"callout"}]
        "regionOverrides": [],
        # design-element numerals glued to headings ("4Institutional"):
        # "styled" (separate <span class="section-number">), "inline" ("4. X"),
        # or "removed"
        "sectionNumbers": "styled",
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
        return _deep_merge(DEFAULTS, json.loads(cfg_path.read_text()))
    return copy.deepcopy(DEFAULTS)


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
