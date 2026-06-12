"""RK3 web app: documents API, async conversion, static viewer + output.

Conversions run in a subprocess (python -m rk3 convert <slug>), not in-process:
a heavy or leaky conversion (pdfium bitmaps, PIL crops, large artifacts) must
not be able to OOM the web server.
"""

import datetime
import json
import re
import subprocess
import sys
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rk3.documents import OUTPUT, list_documents, source_for_slug

ROOT = Path(__file__).resolve().parent.parent
FEEDBACK = ROOT / "feedback"

app = FastAPI(title="RK3")

_active: set[str] = set()
_active_lock = threading.Lock()


@app.get("/api/documents")
def documents():
    docs = list_documents()
    with _active_lock:
        for d in docs:
            if d["slug"] in _active:
                d["status"] = "in_progress"
    return docs


@app.post("/api/convert/{slug}")
def start_convert(slug: str, force: bool = False):
    if source_for_slug(slug) is None:
        raise HTTPException(404, f"unknown document {slug!r}")
    with _active_lock:
        if slug in _active:
            return {"slug": slug, "status": "in_progress"}
        _active.add(slug)

    def work():
        try:
            cmd = [sys.executable, "-m", "rk3", "convert", slug]
            if force:
                cmd.append("--force")
            subprocess.run(cmd, cwd=ROOT, timeout=3600,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        finally:
            with _active_lock:
                _active.discard(slug)

    threading.Thread(target=work, daemon=True, name=f"convert-{slug}").start()
    return {"slug": slug, "status": "in_progress"}


class FeedbackEntry(BaseModel):
    """One viewer annotation. Either an element target (nid/rk) or a PDF-pane
    spot (page + fractional coords). type: "comment" | "answer".
    Answers carry qid + choice. This same stream later feeds the in-codebase
    config agent; during development Claude reads it directly."""
    type: str = "comment"
    text: str = ""
    nid: str | None = None
    rk: str | None = None
    page: int | None = None
    xf: float | None = None
    yf: float | None = None
    qid: str | None = None
    choice: str | None = None
    id: str | None = None  # present => update that entry instead of appending


def _feedback_path(slug: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        raise HTTPException(400, "bad slug")
    FEEDBACK.mkdir(exist_ok=True)
    return FEEDBACK / f"{slug}.jsonl"


@app.get("/api/feedback/{slug}")
def get_feedback(slug: str):
    path = _feedback_path(slug)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@app.post("/api/feedback/{slug}")
def post_feedback(slug: str, entry: FeedbackEntry):
    if source_for_slug(slug) is None:
        raise HTTPException(404, f"unknown document {slug!r}")
    path = _feedback_path(slug)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    body = entry.model_dump(exclude_none=True)

    if entry.id:  # edit an existing entry in place
        lines = [json.loads(l) for l in path.read_text().splitlines()
                 if l.strip()] if path.exists() else []
        for i, rec in enumerate(lines):
            if rec.get("id") == entry.id:
                rec.update(body)
                rec["edited"] = now
                lines[i] = rec
                path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                                        for r in lines))
                return rec
        raise HTTPException(404, f"no feedback entry {entry.id!r}")

    rec = {"ts": now, "status": "open", "id": str(uuid.uuid4())[:8], **body}
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


@app.delete("/api/feedback/{slug}/{entry_id}")
def delete_feedback(slug: str, entry_id: str):
    path = _feedback_path(slug)
    if not path.exists():
        raise HTTPException(404, "no feedback for document")
    lines = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    kept = [r for r in lines if r.get("id") != entry_id]
    if len(kept) == len(lines):
        raise HTTPException(404, f"no feedback entry {entry_id!r}")
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept))
    return {"deleted": entry_id}


OUTPUT.mkdir(parents=True, exist_ok=True)
app.mount("/output", StaticFiles(directory=OUTPUT), name="output")

_dist = Path(__file__).parent / "ui" / "dist"
_static = _dist if _dist.is_dir() else Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=_static, html=True), name="viewer")
