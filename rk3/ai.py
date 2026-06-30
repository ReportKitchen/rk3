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
    return {"mode": mode, "provider": provider, "model": model}


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


def complete_json(system: str, user: str, schema: dict, *, max_tokens: int = 2000) -> dict:
    """Run a single structured-extraction call and return the parsed object.
    Raises on any failure; callers decide whether to fall back to heuristics."""
    cfg = get_ai_config()
    if cfg["provider"] == "anthropic":
        return _anthropic_json(system, user, schema, cfg["model"], max_tokens)
    return _openai_json(system, user, schema, cfg["model"], cfg["provider"], max_tokens)


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
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": content}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    # adaptive thinking is a 4.6+ feature; Haiku 4.5 rejects it
    if "haiku" not in model:
        kwargs["thinking"] = {"type": "adaptive"}
    resp = client.messages.create(**kwargs)
    _record_usage(model, resp.usage)
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return _parse_json(text)


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
