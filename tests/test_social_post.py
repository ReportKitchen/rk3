import base64
import json
from pathlib import Path

import pytest
from PIL import Image

from rk3.social_post import (HEIGHT, WIDTH, _extract_and_sanitize_svg,
                             _gemini_image_edit, _rasterize_svg,
                             _required_keys, _result_path)
from rk3.ai import call_usage, edit_image_gemini, gemini_call_usage


def _cover(tmp_path: Path) -> Path:
    path = tmp_path / "cover.png"
    Image.new("RGB", (300, 500), "#345678").save(path)
    return path


def test_svg_sanitizer_embeds_only_server_supplied_cover(tmp_path):
    raw = """Some preamble
    <svg xmlns="http://www.w3.org/2000/svg" width="1" height="2">
      <rect width="1200" height="630" fill="#fff"/>
      <image href="{{COVER_DATA_URL}}" x="20" y="20" width="200" height="400"/>
      <text x="300" y="100">Exact title</text>
    </svg>
    trailing text"""
    clean = _extract_and_sanitize_svg(raw, _cover(tmp_path))
    assert 'width="1200"' in clean
    assert 'height="630"' in clean
    assert 'viewBox="0 0 1200 630"' in clean
    assert "data:image/png;base64," in clean
    assert "{{COVER_DATA_URL}}" not in clean
    assert clean.startswith("<svg")
    assert "ns0:" not in clean


@pytest.mark.parametrize("payload", [
    '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.com/x.png"/></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject/></svg>',
])
def test_svg_sanitizer_rejects_active_or_external_content(tmp_path, payload):
    with pytest.raises(ValueError):
        _extract_and_sanitize_svg(payload, _cover(tmp_path))


def test_svg_rasterizer_outputs_exact_social_dimensions(tmp_path):
    out = tmp_path / "social.png"
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
           f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">'
           '<rect width="1200" height="630" fill="#123456"/></svg>')
    _rasterize_svg(svg, out)
    with Image.open(out) as image:
        assert image.size == (WIDTH, HEIGHT)


def test_each_mode_requires_only_the_providers_it_uses(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert _required_keys("openai-reformat") == ["OPENAI_API_KEY"]
    assert _required_keys("openai-rebuild") == ["OPENAI_API_KEY"]
    assert _required_keys("claude-reformat") == ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
    assert _required_keys("claude-rebuild") == ["ANTHROPIC_API_KEY"]
    assert _required_keys("gemini-reformat") == ["GOOGLE_API_KEY"]


def test_openai_image_cost_uses_modality_specific_token_rates():
    class Details:
        text_tokens = 1000
        image_tokens = 2000
    class Usage:
        input_tokens = 3000
        output_tokens = 4000
        input_tokens_details = Details()
        output_tokens_details = Details()
    record = call_usage("openai", "gpt-image-2", "image_edit", Usage())
    # (1k text × $5 + 2k image input × $8 + 2k image output × $30) / 1M
    assert record["costUsd"] == 0.081


def test_claude_cost_uses_model_token_rates():
    class Usage:
        input_tokens = 2000
        output_tokens = 1000
        cache_read_input_tokens = 0
        cache_creation_input_tokens = 0
    record = call_usage("anthropic", "claude-opus-4-8", "vision_text", Usage())
    assert record["costUsd"] == 0.035


def test_missing_provider_usage_is_not_reported_as_free():
    record = call_usage("openai", "gpt-image-2", "image_edit", None)
    assert record["costUsd"] is None


def test_gemini_image_cost_uses_output_modality_and_thinking_rates():
    response = {
        "id": "interaction-123",
        "usage": {
            "total_input_tokens": 1000,
            "total_output_tokens": 1150,
            "total_thought_tokens": 20,
            "input_tokens_by_modality": [
                {"modality": "text", "tokens": 440},
                {"modality": "image", "tokens": 560},
            ],
            "output_tokens_by_modality": [
                {"modality": "text", "tokens": 30},
                {"modality": "image", "tokens": 1120},
            ],
        },
    }
    record = gemini_call_usage(response, "gemini-3.1-flash-image")
    # 1k input × $0.50 + (30 text + 20 thought) × $3
    # + 1,120 image output × $60, all per 1M tokens.
    assert record["costUsd"] == 0.06785
    assert record["provider"] == "google"


def test_gemini_one_shot_sends_cover_and_reads_final_image(tmp_path, monkeypatch):
    captured = {}
    response = {
        "id": "interaction-123",
        "status": "completed",
        "steps": [{"type": "model_output", "content": [
            {"type": "image", "mime_type": "image/jpeg",
             "data": base64.b64encode(b"generated-image").decode("ascii")},
        ]}],
        "usage": {"total_input_tokens": 1, "total_output_tokens": 1120,
                  "output_tokens_by_modality": [
                      {"modality": "image", "tokens": 1120}]},
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(response).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    image, usage, mime_type = edit_image_gemini(
        "Reformat it", _cover(tmp_path), model="gemini-3.1-flash-image")

    assert image == b"generated-image"
    assert mime_type == "image/jpeg"
    assert captured["payload"]["input"][1]["type"] == "image"
    assert captured["payload"]["response_format"]["aspect_ratio"] == "16:9"
    assert captured["payload"]["response_format"]["mime_type"] == "image/jpeg"
    assert usage["costUsd"] == 0.0672


def test_gemini_result_keeps_a_jpeg_extension(monkeypatch, tmp_path):
    monkeypatch.setattr("rk3.social_post.output_dir", lambda _slug: tmp_path)
    assert _result_path("doc", "gemini-reformat").suffix == ".jpg"
    assert _result_path("doc", "openai-reformat").suffix == ".png"


def test_gemini_jpeg_is_saved_without_recompression(tmp_path, monkeypatch):
    jpeg = b"exact-provider-jpeg-bytes"
    call = {"provider": "google", "costUsd": 0.0672}
    monkeypatch.setattr(
        "rk3.social_post.edit_image_gemini",
        lambda *_args, **_kwargs: (jpeg, call, "image/jpeg"),
    )
    destination = tmp_path / "gemini-reformat.jpg"
    recorded = []
    _gemini_image_edit(_cover(tmp_path), destination, "prompt", recorded.append)
    assert destination.read_bytes() == jpeg
    assert recorded == [call]
