"""Multi-pass conversion pipeline.

Stages run in order; each writes its artifact plus a fingerprint into
meta.json. A stage is skipped when its fingerprint — hash of (upstream
fingerprint, the config slice it depends on, its code VERSION) — matches the
recorded one and its artifact still exists. Changing a render-only config key
therefore re-runs render alone; the PDF is never re-opened.
"""

import datetime
import hashlib
import importlib
import json
import time
import traceback
from pathlib import Path

from .config import config_slice, load_config
from .debuglog import DebugLog
from .documents import output_dir, source_for_slug

# stage name -> (module, dotted config keys the stage depends on)
STAGES = [
    ("extract", "rk3.engines.pdfium.extract", ["input"]),
    ("assemble", "rk3.engines.pdfium.assemble", ["input"]),
    ("analyze", "rk3.engines.pdfium.analyze", ["structure", "output.imageScale"]),
    ("render", "rk3.render", ["output", "structure.footnotePlacement", "ops"]),
]

ARTIFACTS = {
    "extract": "extract.json",
    "assemble": "blocks.json",
    "analyze": "ir.json",
    "render": "index.html",
}


class ScannedPdfError(Exception):
    pass


class Context:
    """Carries paths/config/log through a stage run."""

    def __init__(self, source: Path, outdir: Path, cfg: dict, stage: str):
        self.source = source
        self.outdir = outdir
        self.cfg = cfg
        self.log = DebugLog(outdir, stage)

    def artifact(self, stage: str):
        return json.loads((self.outdir / ARTIFACTS[stage]).read_text())

    def write_artifact(self, stage: str, data):
        (self.outdir / ARTIFACTS[stage]).write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _fingerprint(parent_fp: str, cfg_part: dict, version: int) -> str:
    blob = json.dumps([parent_fp, cfg_part, version], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _read_meta(outdir: Path) -> dict:
    p = outdir / "meta.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def _write_meta(outdir: Path, meta: dict):
    (outdir / "meta.json").write_text(json.dumps(meta, indent=2))


def convert(slug: str, force: bool = False) -> dict:
    source = source_for_slug(slug)
    if source is None:
        raise FileNotFoundError(f"no source PDF for slug {slug!r}")
    outdir = output_dir(slug)
    outdir.mkdir(parents=True, exist_ok=True)

    cfg = load_config(source)
    meta = _read_meta(outdir)
    meta.update({"slug": slug, "source": str(source), "status": "in_progress",
                 "started": _now(), "finished": None, "error": None})
    meta.setdefault("stages", {})
    _write_meta(outdir, meta)

    # snapshot the previous IR: if analyze re-runs, feedback anchors are
    # re-matched against the new one (rk3.remap)
    old_ir = None
    ir_path = outdir / ARTIFACTS["analyze"]
    if ir_path.exists():
        try:
            old_ir = json.loads(ir_path.read_text())
        except json.JSONDecodeError:
            pass

    try:
        fp = _file_sha(source)  # chain starts at the source file
        for stage, module_name, cfg_keys in STAGES:
            mod = importlib.import_module(module_name)
            part = config_slice(cfg, cfg_keys)
            fp = _fingerprint(fp, part, getattr(mod, "VERSION", 0))
            prev = meta["stages"].get(stage, {})
            artifact_ok = (outdir / ARTIFACTS[stage]).exists()
            if not force and prev.get("fingerprint") == fp and artifact_ok:
                meta["stages"][stage]["skipped"] = True
                continue
            ctx = Context(source, outdir, cfg, stage)
            t0 = time.monotonic()
            try:
                mod.run(ctx)
            finally:
                ctx.log.close()
            meta["stages"][stage] = {
                "fingerprint": fp,
                "completed_at": _now(),
                "seconds": round(time.monotonic() - t0, 2),
                "skipped": False,
            }
            _write_meta(outdir, meta)
        if old_ir is not None and not meta["stages"]["analyze"].get("skipped"):
            from .remap import remap_feedback, remap_ops
            log = DebugLog(outdir, "remap")
            try:
                new_ir = json.loads(ir_path.read_text())
                remap_feedback(slug, old_ir, new_ir, log)
                remap_ops(slug, old_ir, new_ir, log)
            finally:
                log.close()
        meta["status"] = "done"
    except ScannedPdfError as e:
        meta["status"] = "failed"
        meta["error"] = str(e)
    except Exception:
        meta["status"] = "failed"
        meta["error"] = traceback.format_exc(limit=8)
    meta["finished"] = _now()
    _write_meta(outdir, meta)
    return meta
