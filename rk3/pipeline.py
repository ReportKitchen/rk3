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


_SRC_SHA_CACHE: dict = {}


def _file_sha_cached(path: Path) -> str:
    """_file_sha keyed on (path, mtime, size) so repeated build-status polls
    don't re-hash a large PDF every time."""
    st = path.stat()
    key = (str(path), st.st_mtime_ns, st.st_size)
    if _SRC_SHA_CACHE.get("key") != key:
        _SRC_SHA_CACHE["key"] = key
        _SRC_SHA_CACHE["val"] = _file_sha(path)
    return _SRC_SHA_CACHE["val"]


def build_status(slug: str) -> dict:
    """Recompute the expected fingerprint chain from the CURRENT code + config +
    source WITHOUT running any stage, and compare it to what the doc was built
    with (meta.json). A per-stage match means the artifact on disk is exactly
    what today's code would produce — the authoritative "is this the latest"
    signal, since the chain folds in code VERSION, config, and the source PDF
    (a bare version number would miss the latter two). `build_id` is the stored
    render fingerprint: a cache-bust key that changes the instant a new render
    lands on disk, even from a CLI rebuild."""
    outdir = output_dir(slug)
    meta = _read_meta(outdir)
    source = source_for_slug(slug)
    stored_render = (meta.get("stages", {}).get("render") or {}).get("fingerprint")
    out = {
        "slug": slug,
        "status": meta.get("status", "unconverted"),
        "finished": meta.get("finished"),
        "error": meta.get("error"),
        "stages": [],
        "stale": [],
        "up_to_date": False,
        "build_id": stored_render,
    }
    if source is None or not meta.get("stages"):
        return out
    cfg = load_config(source)
    fp = _file_sha_cached(source)
    for stage, module_name, cfg_keys in STAGES:
        mod = importlib.import_module(module_name)
        version = getattr(mod, "VERSION", 0)
        fp = _fingerprint(fp, config_slice(cfg, cfg_keys), version)
        stored = (meta["stages"].get(stage) or {}).get("fingerprint")
        ok = stored == fp
        out["stages"].append({"stage": stage, "version": version, "current": ok})
        if not ok:
            out["stale"].append(stage)
    out["up_to_date"] = not out["stale"] and meta.get("status") == "done"
    return out


def convert(slug: str, force: bool = False) -> dict:
    """The corpus entry: resolve a sources/ slug, then run on explicit paths."""
    source = source_for_slug(slug)
    if source is None:
        raise FileNotFoundError(f"no source PDF for slug {slug!r}")
    return convert_paths(source, output_dir(slug), force=force, slug=slug)


def convert_paths(source, outdir, force: bool = False, slug: str = "") -> dict:
    """The explicit-context entry (multiuser Stage 1): run the pipeline on THIS
    source file into THIS output directory — no global sources/ scan. The
    platform worker converts uploaded documents through here; the slug entry
    above delegates, so both surfaces share one pipeline."""
    from pathlib import Path
    source = Path(source)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    cfg = load_config(source)
    meta = _read_meta(outdir)
    meta.update({"slug": slug or source.stem, "source": str(source), "status": "in_progress",
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
        # feedback/ops remapping is keyed by corpus slug — platform documents
        # (explicit-path runs, no slug) have no anchor history to remap
        if slug and old_ir is not None and not meta["stages"]["analyze"].get("skipped"):
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
