"""Experimental social-post renderers for PDF cover pages.

Five deliberately separate paths let the owner compare which part of the
workflow matters: the vision model, the image renderer, or a deterministic SVG
render.  Results are local, regenerable artifacts under each document's output
directory.  Prompts are loaded fresh on every click so tuning needs no restart.
"""

from __future__ import annotations

import base64
import datetime
import json
import os
import re
import threading
import traceback
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

from rk3.ai import DEFAULT_MODELS, edit_image, edit_image_gemini, vision_text
from rk3.documents import output_dir
from rk3.prompts import load_prompt


WIDTH = 1200
HEIGHT = 630
# GPT Image requires both dimensions to be multiples of 16.  Crop the returned
# 1200x640 image by five pixels on each horizontal edge after generation.
IMAGE_API_SIZE = "1200x640"

MODES = (
    "openai-reformat",
    "claude-reformat",
    "gemini-reformat",
    "openai-rebuild",
    "claude-rebuild",
)

_active: set[tuple[str, str]] = set()
_lock = threading.Lock()
ET.register_namespace("", "http://www.w3.org/2000/svg")


def _cover_path(slug: str) -> Path:
    return output_dir(slug) / "pages" / "page-0001.png"


def _social_dir(slug: str) -> Path:
    return output_dir(slug) / "social-post"


def _result_path(slug: str, mode: str) -> Path:
    extension = "jpg" if mode == "gemini-reformat" else "png"
    return _social_dir(slug) / f"{mode}.{extension}"


def _error_path(slug: str, mode: str) -> Path:
    return _social_dir(slug) / f"{mode}.error.txt"


def _usage_path(slug: str, mode: str) -> Path:
    return _social_dir(slug) / f"{mode}.usage.json"


def _artifact_url(slug: str, mode: str, path: Path) -> str:
    # mtime cache busting means a replaced image appears immediately without
    # forcing no-store on every generated image response.
    return (f"/output/pdfium/{slug}/social-post/{path.name}"
            f"?v={path.stat().st_mtime_ns}")


def mode_status(slug: str, mode: str) -> dict:
    if mode not in MODES:
        raise ValueError(f"unknown social-post mode {mode!r}")
    key = (slug, mode)
    result = _result_path(slug, mode)
    error = _error_path(slug, mode)
    with _lock:
        running = key in _active
    data = {
        "mode": mode,
        "status": "in_progress" if running else "empty",
        "url": _artifact_url(slug, mode, result) if result.exists() else None,
        "error": None,
        "usage": None,
    }
    usage_path = _usage_path(slug, mode)
    if usage_path.exists():
        try:
            data["usage"] = json.loads(usage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    if not running and error.exists():
        data["status"] = "failed"
        data["error"] = error.read_text(encoding="utf-8").strip()
    elif not running and result.exists():
        data["status"] = "ready"
    return data


def all_status(slug: str) -> dict:
    cover = _cover_path(slug)
    return {
        "slug": slug,
        "cover": (f"/output/pdfium/{slug}/pages/page-0001.png"
                  if cover.exists() else None),
        "modes": {mode: mode_status(slug, mode) for mode in MODES},
    }


def _required_keys(mode: str) -> list[str]:
    if mode == "gemini-reformat":
        keys = ["GOOGLE_API_KEY"]
    elif mode == "claude-rebuild":
        keys = ["ANTHROPIC_API_KEY"]
    elif mode == "claude-reformat":
        keys = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
    else:
        keys = ["OPENAI_API_KEY"]
    return [key for key in keys if not os.getenv(key)]


def start_generation(slug: str, mode: str) -> bool:
    """Start one mode in the background.  Return False if it is already busy."""
    if mode not in MODES:
        raise ValueError(f"unknown social-post mode {mode!r}")
    cover = _cover_path(slug)
    if not cover.exists():
        raise FileNotFoundError(f"cover image not found: {cover}")
    missing = _required_keys(mode)
    if missing:
        raise RuntimeError(f"missing API credential: {', '.join(missing)}")

    key = (slug, mode)
    with _lock:
        if key in _active:
            return False
        _active.add(key)

    def work() -> None:
        out_dir = _social_dir(slug)
        out_dir.mkdir(parents=True, exist_ok=True)
        error = _error_path(slug, mode)
        usage = _new_usage(mode)
        _write_usage(slug, mode, usage)

        def record_call(call: dict) -> None:
            usage["calls"].append(call)
            _write_usage(slug, mode, usage)

        try:
            if mode == "openai-reformat":
                _openai_image_edit(cover, _result_path(slug, mode),
                                   load_prompt("social-openai-reformat.md"),
                                   record_call)
            elif mode == "claude-reformat":
                brief, call = _claude_vision(
                    cover, load_prompt("social-claude-reformat.system.md"))
                record_call(call)
                _atomic_text(out_dir / f"{mode}.brief.txt", brief)
                _openai_image_edit(cover, _result_path(slug, mode), brief,
                                   record_call)
            elif mode == "gemini-reformat":
                _gemini_image_edit(cover, _result_path(slug, mode),
                                   load_prompt("social-gemini-reformat.md"),
                                   record_call)
            elif mode == "openai-rebuild":
                raw, call = _openai_vision(
                    cover, load_prompt("social-openai-rebuild.system.md"))
                record_call(call)
                _save_svg_render(cover, raw, out_dir / f"{mode}.svg",
                                 _result_path(slug, mode))
            elif mode == "claude-rebuild":
                raw, call = _claude_vision(
                    cover, load_prompt("social-claude-rebuild.system.md"))
                record_call(call)
                _save_svg_render(cover, raw, out_dir / f"{mode}.svg",
                                 _result_path(slug, mode))
            error.unlink(missing_ok=True)
            (out_dir / f"{mode}.traceback.txt").unlink(missing_ok=True)
            _finish_usage(slug, mode, usage, "succeeded")
        except Exception as exc:
            # Keep a previous successful image in place.  The UI can show it
            # alongside the failed regeneration message.
            message = f"{type(exc).__name__}: {exc}"
            _atomic_text(error, message)
            (out_dir / f"{mode}.traceback.txt").write_text(
                traceback.format_exc(), encoding="utf-8")
            _finish_usage(slug, mode, usage, "failed")
        finally:
            with _lock:
                _active.discard(key)

    threading.Thread(target=work, daemon=True,
                     name=f"social-post-{slug}-{mode}").start()
    return True


def _openai_image_edit(cover: Path, destination: Path, prompt: str,
                       record_call) -> None:
    image_bytes, call = edit_image(
        prompt, cover,
        model=os.getenv("SOCIAL_POST_IMAGE_MODEL", "gpt-image-2"),
        size=IMAGE_API_SIZE,
        quality=os.getenv("SOCIAL_POST_IMAGE_QUALITY", "medium"),
    )
    # Persist cost before local decoding/cropping; the API call is billable even
    # if post-processing subsequently fails.
    record_call(call)
    generated = Image.open(BytesIO(image_bytes)).convert("RGB")
    # Usually this removes only 5px top and bottom.  ImageOps.fit is also a
    # defensive normalization if the provider returns unexpected dimensions.
    final = ImageOps.fit(generated, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
    _atomic_png(final, destination)


def _gemini_image_edit(cover: Path, destination: Path, prompt: str,
                       record_call) -> None:
    image_bytes, call, mime_type = edit_image_gemini(
        prompt, cover,
        model=os.getenv("SOCIAL_POST_GEMINI_MODEL",
                        "gemini-3.1-flash-image"),
        aspect_ratio="16:9",
        image_size=os.getenv("SOCIAL_POST_GEMINI_IMAGE_SIZE", "1K"),
    )
    record_call(call)
    if mime_type != "image/jpeg":
        raise RuntimeError(
            f"Google Gemini returned {mime_type!r}; expected 'image/jpeg'")
    # Preserve the provider's JPEG byte-for-byte: the browser can display it
    # directly, and decoding/resaving would only add generation loss.
    _atomic_bytes(destination, image_bytes)


def _image_data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _openai_vision(cover: Path, instructions: str) -> tuple[str, dict]:
    return vision_text(
        instructions, load_prompt("social-cover.user.md"), cover,
        provider="openai",
        model=os.getenv("SOCIAL_POST_OPENAI_MODEL", "gpt-5.6"),
        max_tokens=12000,
    )


def _claude_vision(cover: Path, system: str) -> tuple[str, dict]:
    return vision_text(
        system, load_prompt("social-cover.user.md"), cover,
        provider="anthropic",
        model=os.getenv("SOCIAL_POST_CLAUDE_MODEL",
                        DEFAULT_MODELS["anthropic"]),
        max_tokens=12000,
    )


_FORBIDDEN_SVG = re.compile(
    r"<(?:script|foreignObject|iframe|object|embed|audio|video)\b|"
    r"javascript:|@import|data:", re.IGNORECASE)
_EVENT_ATTR = re.compile(r"^on[a-z]+$", re.IGNORECASE)
_COVER_TOKEN = "{{COVER_DATA_URL}}"


def _extract_and_sanitize_svg(raw: str, cover: Path) -> str:
    """Return inert SVG with no network/script surface and an embedded cover."""
    start = raw.find("<svg")
    end = raw.rfind("</svg>")
    if start < 0 or end < start:
        raise ValueError("model did not return a complete SVG")
    svg = raw[start:end + len("</svg>")]
    if _FORBIDDEN_SVG.search(svg):
        raise ValueError("generated SVG contains forbidden active or external content")
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        raise ValueError(f"generated SVG is not valid XML: {exc}") from exc
    if root.tag.split("}")[-1] != "svg":
        raise ValueError("generated document root is not SVG")

    for element in root.iter():
        tag = element.tag.split("}")[-1]
        if tag in {"script", "foreignObject", "iframe", "object", "embed"}:
            raise ValueError(f"generated SVG contains forbidden <{tag}>")
        for attr, value in list(element.attrib.items()):
            local = attr.split("}")[-1]
            if _EVENT_ATTR.match(local):
                del element.attrib[attr]
                continue
            if local in {"href", "src"} and not (
                    value == _COVER_TOKEN or value.startswith("#")):
                raise ValueError("generated SVG references an unapproved resource")
            urls = re.findall(r"url\(\s*([^)]*?)\s*\)", value,
                              flags=re.IGNORECASE)
            if any(not url.startswith("#") for url in urls):
                raise ValueError("generated SVG contains an external CSS URL")
        if element.text:
            if re.search(r"https?://|javascript:|@import|data:", element.text,
                         flags=re.IGNORECASE):
                raise ValueError("generated SVG contains external style content")
            urls = re.findall(r"url\(\s*([^)]*?)\s*\)", element.text,
                              flags=re.IGNORECASE)
            if any(not url.startswith("#") for url in urls):
                raise ValueError("generated SVG contains an external style URL")

    root.set("width", str(WIDTH))
    root.set("height", str(HEIGHT))
    root.set("viewBox", f"0 0 {WIDTH} {HEIGHT}")
    clean = ET.tostring(root, encoding="unicode")
    # The only data URL is injected by us after validation, never supplied by
    # the model.  This keeps the original art available to deterministic layouts.
    return clean.replace(_COVER_TOKEN, _image_data_url(cover))


def _save_svg_render(cover: Path, raw: str, svg_path: Path,
                     png_path: Path) -> None:
    svg = _extract_and_sanitize_svg(raw, cover)
    _atomic_text(svg_path, svg)
    _rasterize_svg(svg, png_path)


def _rasterize_svg(svg: str, destination: Path) -> None:
    from playwright.sync_api import sync_playwright

    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_name(f".{destination.name}.tmp.png")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(
                viewport={"width": WIDTH, "height": HEIGHT},
                device_scale_factor=1,
            )
            page.set_content(
                "<!doctype html><style>html,body{margin:0;width:1200px;"
                "height:630px;overflow:hidden}</style>" + svg,
                wait_until="load",
            )
            page.locator("svg").screenshot(path=str(tmp))
        finally:
            browser.close()
    with Image.open(tmp) as image:
        if image.size != (WIDTH, HEIGHT):
            raise RuntimeError(f"SVG rasterized at {image.size}, expected {(WIDTH, HEIGHT)}")
    tmp.replace(destination)


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def _atomic_json(path: Path, data: dict) -> None:
    _atomic_text(path, json.dumps(data, indent=2, ensure_ascii=False))


def _new_usage(mode: str) -> dict:
    return {
        "mode": mode,
        "status": "in_progress",
        "startedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "completedAt": None,
        "calls": [],
        "totalCostUsd": None,
        "costComplete": False,
        "pricingBasis": "public-standard-rates-2026-07-18",
    }


def _write_usage(slug: str, mode: str, usage: dict) -> None:
    costs = [call.get("costUsd") for call in usage["calls"]]
    known = [cost for cost in costs if cost is not None]
    usage["totalCostUsd"] = round(sum(known), 6) if known else None
    usage["costComplete"] = bool(costs) and len(known) == len(costs)
    _atomic_json(_usage_path(slug, mode), usage)


def _finish_usage(slug: str, mode: str, usage: dict, status: str) -> None:
    usage["status"] = status
    usage["completedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _write_usage(slug, mode, usage)
    history = _social_dir(slug) / f"{mode}.usage-history.jsonl"
    with history.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(usage, ensure_ascii=False) + "\n")


def _atomic_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.png")
    image.save(tmp, "PNG")
    tmp.replace(path)
