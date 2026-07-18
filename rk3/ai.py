"""Provider-agnostic LLM access for AI-assisted features.

Provider + model are configured via config.json (the ``ai`` section) or
environment variables (AI_ENABLED / AI_PROVIDER / AI_MODEL); API keys come from
.env. Anthropic uses the official ``anthropic`` SDK; OpenAI and DeepSeek
(OpenAI-compatible) use the ``openai`` SDK. There is no admin UI yet — switch
providers by editing config.json or .env.
"""

import datetime
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# $ per 1M tokens (input, output); falls back to Opus-tier rates
_PRICING = {"claude-opus-4-8": (5.0, 25.0), "claude-opus-4-7": (5.0, 25.0),
            "claude-sonnet-4-6": (3.0, 15.0), "claude-haiku-4-5": (1.0, 5.0)}

# Public standard API rates per 1M tokens, checked 2026-07-18.  These estimates
# deliberately exclude private discounts, priority processing, and regional
# uplifts. Sources:
#   https://developers.openai.com/api/docs/pricing
#   https://platform.claude.com/docs/en/about-claude/pricing
_OPENAI_TEXT_PRICING = {
    "gpt-5.6": (5.0, 0.50, 30.0),
    "gpt-5.6-sol": (5.0, 0.50, 30.0),
}
_OPENAI_IMAGE_PRICING = {
    # text input, image input, cached image input, image output
    "gpt-image-2": (5.0, 8.0, 2.0, 30.0),
}
_GOOGLE_IMAGE_PRICING = {
    # input, text/thinking output, image output
    "gemini-3.1-flash-image": (0.50, 3.0, 60.0),
}


def _record_usage(model, usage):
    """Append per-call token usage + estimated cost to logs/api-usage.jsonl."""
    try:
        ipt = getattr(usage, "input_tokens", 0) or 0
        opt = getattr(usage, "output_tokens", 0) or 0
        rin, rout = _PRICING.get(model, (5.0, 25.0))
        rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"),
               "model": model, "in": ipt, "out": opt,
               "cost": round((ipt * rin + opt * rout) / 1e6, 4)}
        d = ROOT / "logs"
        d.mkdir(exist_ok=True)
        with (d / "api-usage.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass  # usage logging must never break a conversion


def call_usage(provider: str, model: str, kind: str, usage,
               request_id: str | None = None) -> dict:
    """Normalize one provider response's usage and estimate its USD cost."""
    if usage is None:
        return {
            "provider": provider,
            "model": model,
            "kind": kind,
            "requestId": request_id,
            "inputTokens": 0,
            "outputTokens": 0,
            "details": {},
            "costUsd": None,
        }
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    details: dict[str, int] = {}
    cost = None

    if provider == "openai" and kind == "image_edit":
        inp = getattr(usage, "input_tokens_details", None)
        out = getattr(usage, "output_tokens_details", None)
        text_in = int(getattr(inp, "text_tokens", 0) or 0)
        image_in = int(getattr(inp, "image_tokens", 0) or 0)
        image_out = int(getattr(out, "image_tokens", output_tokens) or 0)
        details = {"textInput": text_in, "imageInput": image_in,
                   "imageOutput": image_out}
        rates = _OPENAI_IMAGE_PRICING.get(model)
        if rates:
            text_rate, image_rate, _cached_rate, output_rate = rates
            cost = (text_in * text_rate + image_in * image_rate
                    + image_out * output_rate) / 1_000_000
    elif provider == "openai":
        inp = getattr(usage, "input_tokens_details", None)
        cached = int(getattr(inp, "cached_tokens", 0) or 0)
        details = {"cachedInput": cached}
        rates = _OPENAI_TEXT_PRICING.get(model)
        if rates:
            input_rate, cached_rate, output_rate = rates
            cost = ((input_tokens - cached) * input_rate
                    + cached * cached_rate
                    + output_tokens * output_rate) / 1_000_000
    elif provider == "anthropic":
        cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        cache_write = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
        details = {"cacheReadInput": cache_read, "cacheWriteInput": cache_write}
        rates = _PRICING.get(model)
        if rates:
            input_rate, output_rate = rates
            # Social-post calls do not enable caching.  Include cache fields
            # defensively using the normal 0.1x read / 1.25x 5m-write rates.
            cost = (input_tokens * input_rate
                    + cache_read * input_rate * 0.1
                    + cache_write * input_rate * 1.25
                    + output_tokens * output_rate) / 1_000_000

    return {
        "provider": provider,
        "model": model,
        "kind": kind,
        "requestId": request_id,
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "details": details,
        "costUsd": round(cost, 6) if cost is not None else None,
    }


def usage_summary():
    """Running total across all logged API calls."""
    p = ROOT / "logs" / "api-usage.jsonl"
    if not p.exists():
        return {"calls": 0, "in": 0, "out": 0, "cost": 0.0}
    recs = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    return {"calls": len(recs), "in": sum(r["in"] for r in recs),
            "out": sum(r["out"] for r in recs),
            "cost": round(sum(r["cost"] for r in recs), 2)}

# default model per provider; "model": null in config falls through to these
DEFAULT_MODELS = {
    "anthropic": "claude-opus-4-8",
    "openai": "gpt-4o",
    "deepseek": "deepseek-chat",
}


def _load_env() -> None:
    """Load .env into the process environment (without clobbering real env)."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip())


_load_env()


# AI usage tiers (a trust gradient), not just on/off:
#   none     — no AI; heuristics only
#   analyze  — AI may read/locate content (returns pointers) but writes nothing
#   generate — AI may also author copy (summaries, title, findings)
AI_MODES = ("none", "analyze", "generate")


def get_ai_config() -> dict:
    cfg = {}
    path = ROOT / "config.json"
    if path.exists():
        try:
            cfg = json.loads(path.read_text()).get("ai", {})
        except (json.JSONDecodeError, OSError):
            cfg = {}

    # explicit mode wins; else derive from the legacy boolean `enabled`
    mode = cfg.get("mode") or os.getenv("AI_MODE")
    if not mode:
        enabled = cfg.get("enabled")
        if enabled is None:
            enabled = os.getenv("AI_ENABLED", "true").lower() not in ("0", "false", "no", "off")
        mode = "generate" if enabled else "none"
    mode = mode if mode in AI_MODES else "generate"
    provider = cfg.get("provider") or os.getenv("AI_PROVIDER", "anthropic")
    model = cfg.get("model") or os.getenv("AI_MODEL") or DEFAULT_MODELS.get(provider)
    # per-ROLE model tiering (webified §0.7): scan (volume) / verify (cheap binary
    # re-scan) / prescribe (judgment). Each falls back to the base model, so
    # tiering is OPT-IN — the calibration gate writes ai.models once a downgrade
    # is proven, else every role stays on the (safe) base model.
    role_cfg = cfg.get("models") or {}
    models = {r: (role_cfg.get(r) or os.getenv(f"AI_MODEL_{r.upper()}") or model)
              for r in ("scan", "verify", "prescribe")}
    return {"mode": mode, "provider": provider, "model": model, "models": models}


def model_for(role: str) -> str:
    """The configured model for a loop ROLE (scan|verify|prescribe), §0.7."""
    return get_ai_config()["models"].get(role) or get_ai_config()["model"]


def ai_mode() -> str:
    return get_ai_config()["mode"]


def ai_can_analyze() -> bool:
    """AI may locate/identify existing content (no prose generated)."""
    return ai_mode() in ("analyze", "generate")


def ai_can_generate() -> bool:
    """AI may author new copy (summaries, title, findings)."""
    return ai_mode() == "generate"


def ai_enabled() -> bool:  # back-compat: "enabled" meant content generation
    return ai_can_generate()


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):  # strip a ```json fence if a model adds one
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)


def complete_json(system: str, user: str, schema: dict, *, max_tokens: int = 2000,
                  provider: str = None, model: str = None) -> dict:
    """Run a single structured-extraction call and return the parsed object.
    Raises on any failure; callers decide whether to fall back to heuristics."""
    cfg = get_ai_config()
    provider = provider or cfg["provider"]
    model = model or cfg["model"]
    if provider == "anthropic":
        return _anthropic_json(system, user, schema, model, max_tokens)
    return _openai_json(system, user, schema, model, provider, max_tokens)


def _anthropic_json(system, user, schema, model, max_tokens) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    _record_usage(model, resp.usage)
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return _parse_json(text)


def vision_json(system: str, user: str, image_paths, schema: dict,
                *, max_tokens: int = 4000, model: str = None) -> dict:
    """Structured call that also sees one or more page images — the basis of the
    vision-QA reviewer (analysis-only: it flags discrepancies, never edits).
    Anthropic only; raises on failure so callers decide on fallback."""
    import base64
    import anthropic

    cfg = get_ai_config()
    if cfg["provider"] != "anthropic":
        raise RuntimeError("vision QA requires the anthropic provider")
    content = []
    for p in image_paths:
        b64 = base64.standard_b64encode(Path(p).read_bytes()).decode()
        content.append({"type": "image", "source": {
            "type": "base64", "media_type": "image/png", "data": b64}})
    content.append({"type": "text", "text": user})
    model = model or cfg["model"]
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    # adaptive thinking (4.6+; Haiku 4.5 rejects it) can eat the token budget and
    # truncate the JSON output — a "char 22" JSONDecodeError. Retry once with a
    # bigger budget AND thinking OFF so the whole budget goes to the structured
    # answer; that reliably completes the JSON.
    last_err = None
    for attempt in range(2):
        kwargs = dict(
            model=model,
            max_tokens=max_tokens * (2 if attempt else 1),
            system=system,
            messages=[{"role": "user", "content": content}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        if "haiku" not in model and attempt == 0:
            kwargs["thinking"] = {"type": "adaptive"}
        resp = client.messages.create(**kwargs)
        _record_usage(model, resp.usage)
        text = next((b.text for b in resp.content if b.type == "text"), "")
        try:
            return _parse_json(text)
        except (json.JSONDecodeError, ValueError) as e:
            last_err = e
    raise last_err


def vision_text(system: str, user: str, image_path, *, provider: str,
                model: str, max_tokens: int = 12000) -> tuple[str, dict]:
    """Ask one provider to inspect a PNG and return free-form text.

    This is the provider chokepoint for outputs such as an art-direction brief
    or SVG source, where a JSON schema would only add escaping and truncation
    risk.  Prompts remain the caller's responsibility and must come from the
    prompt registry.
    """
    import base64

    image_path = Path(image_path)
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    if provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": "image/png",
                    "data": encoded}},
                {"type": "text", "text": user},
            ]}],
        )
        _record_usage(model, resp.usage)
        text = "\n".join(
            block.text for block in resp.content if block.type == "text")
        usage_record = call_usage(
            provider, model, "vision_text", resp.usage,
            getattr(resp, "_request_id", None))
    elif provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = client.responses.create(
            model=model,
            instructions=system,
            input=[{"role": "user", "content": [
                {"type": "input_text", "text": user},
                {"type": "input_image",
                 "image_url": f"data:image/png;base64,{encoded}",
                 "detail": "high"},
            ]}],
            max_output_tokens=max_tokens,
        )
        text = resp.output_text or ""
        usage_record = call_usage(
            provider, model, "vision_text", resp.usage,
            getattr(resp, "_request_id", None))
    else:
        raise ValueError(f"unsupported vision-text provider {provider!r}")
    text = text.strip()
    if not text:
        raise RuntimeError(f"{provider} vision response was empty")
    return text, usage_record


def edit_image(prompt: str, image_path, *, model: str, size: str,
               quality: str = "medium") -> tuple[bytes, dict]:
    """Edit one image with OpenAI's Image API and return the PNG bytes."""
    import base64
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    with Path(image_path).open("rb") as image:
        resp = client.images.edit(
            model=model,
            image=image,
            prompt=prompt,
            size=size,
            quality=quality,
            output_format="png",
        )
    encoded = resp.data[0].b64_json
    if not encoded:
        raise RuntimeError("OpenAI image edit returned no image data")
    usage_record = call_usage(
        "openai", model, "image_edit", resp.usage,
        getattr(resp, "_request_id", None))
    return base64.b64decode(encoded), usage_record


def _modality_tokens(usage: dict, field: str) -> dict[str, int]:
    return {
        str(item.get("modality", "")).lower(): int(item.get("tokens", 0) or 0)
        for item in usage.get(field, [])
        if isinstance(item, dict)
    }


def gemini_call_usage(response: dict, model: str) -> dict:
    """Normalize Gemini Interactions usage and estimate standard-tier cost."""
    usage = response.get("usage") or {}
    input_by = _modality_tokens(usage, "input_tokens_by_modality")
    output_by = _modality_tokens(usage, "output_tokens_by_modality")
    input_tokens = int(usage.get("total_input_tokens", 0) or 0)
    output_tokens = int(usage.get("total_output_tokens", 0) or 0)
    thought_tokens = int(usage.get("total_thought_tokens", 0) or 0)
    image_output = output_by.get("image", 0) if output_by else output_tokens
    text_output = output_by.get("text", max(0, output_tokens - image_output))
    rates = _GOOGLE_IMAGE_PRICING.get(model)
    cost = None
    if rates and usage:
        input_rate, text_output_rate, image_output_rate = rates
        cost = (input_tokens * input_rate
                + (text_output + thought_tokens) * text_output_rate
                + image_output * image_output_rate) / 1_000_000
    return {
        "provider": "google",
        "model": model,
        "kind": "image_edit",
        "requestId": response.get("id"),
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "details": {
            "inputByModality": input_by,
            "outputByModality": output_by,
            "thoughtTokens": thought_tokens,
        },
        "costUsd": round(cost, 6) if cost is not None else None,
    }


def edit_image_gemini(prompt: str, image_path, *, model: str,
                      aspect_ratio: str = "16:9",
                      image_size: str = "1K") -> tuple[bytes, dict, str]:
    """One-shot image edit through Google's synchronous Interactions REST API."""
    import base64
    import urllib.error
    import urllib.request

    encoded = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
    payload = {
        "model": model,
        "input": [
            {"type": "text", "text": prompt},
            {"type": "image", "mime_type": "image/png", "data": encoded},
        ],
        "response_format": {
            "type": "image",
            # Gemini 3.1 Flash Image currently rejects image/png here even
            # though some Interactions API examples show it.  PIL decodes the
            # returned JPEG and the social-post pipeline still saves PNG.
            "mime_type": "image/jpeg",
            "aspect_ratio": aspect_ratio,
            "image_size": image_size,
        },
    }
    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/interactions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": os.environ["GOOGLE_API_KEY"],
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as api_response:
            response = json.loads(api_response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(
            f"Google Gemini API returned HTTP {exc.code}: {detail}") from exc

    if response.get("status") != "completed":
        raise RuntimeError(
            f"Google Gemini interaction ended with status "
            f"{response.get('status', 'unknown')!r}")
    image_block = next((
        block
        for step in reversed(response.get("steps") or [])
        if step.get("type") == "model_output"
        for block in reversed(step.get("content") or [])
        if block.get("type") == "image" and block.get("data")
    ), None)
    if image_block is None:
        raise RuntimeError("Google Gemini image edit returned no image data")
    mime_type = image_block.get("mime_type") or "application/octet-stream"
    return (base64.b64decode(image_block["data"]),
            gemini_call_usage(response, model), mime_type)


def _openai_json(system, user, schema, model, provider, max_tokens) -> dict:
    from openai import OpenAI

    if provider == "deepseek":
        client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
        # DeepSeek supports json_object mode but not full json_schema — give it
        # the schema in the prompt instead
        system = f"{system}\n\nReturn ONLY a JSON object matching this schema:\n{json.dumps(schema)}"
        response_format = {"type": "json_object"}
    else:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response_format = {"type": "json_schema",
                           "json_schema": {"name": "result", "schema": schema, "strict": False}}

    resp = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        response_format=response_format,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return _parse_json(resp.choices[0].message.content or "")
