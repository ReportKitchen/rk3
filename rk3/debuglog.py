"""Keyed debug log. Each pipeline stage writes its own debug-<stage>.jsonl,
regenerated whenever the stage re-runs so entries never go stale relative to
the artifacts. Keys (e.g. "an-000037") are stamped into IR nodes and output
HTML as data-rk, so a problem element in the browser greps straight to its
decision trail:  grep an-000037 output/pdfium/<slug>/debug-*.jsonl
"""

import json
from pathlib import Path

STAGE_PREFIX = {"extract": "ex", "assemble": "as", "analyze": "an", "render": "rn"}


class DebugLog:
    def __init__(self, outdir: Path, stage: str):
        self.prefix = STAGE_PREFIX[stage]
        self.path = outdir / f"debug-{stage}.jsonl"
        self._fh = open(self.path, "w", encoding="utf-8")
        self._seq = 0

    def entry(self, event: str, **fields) -> str:
        """Record one decision; returns the key to stamp on the resulting node."""
        self._seq += 1
        key = f"{self.prefix}-{self._seq:06d}"
        rec = {"k": key, "event": event}
        rec.update(fields)
        self._fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        return key

    def close(self):
        self._fh.close()
