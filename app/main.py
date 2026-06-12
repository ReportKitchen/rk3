"""RK3 web app: documents API, async conversion, static viewer + output."""

import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from rk3.documents import OUTPUT, list_documents, source_for_slug
from rk3.pipeline import convert

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
            convert(slug, force=force)
        finally:
            with _active_lock:
                _active.discard(slug)

    threading.Thread(target=work, daemon=True, name=f"convert-{slug}").start()
    return {"slug": slug, "status": "in_progress"}


OUTPUT.mkdir(parents=True, exist_ok=True)
app.mount("/output", StaticFiles(directory=OUTPUT), name="output")
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True),
          name="viewer")
