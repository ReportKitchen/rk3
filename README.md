# RK3

A multi-pass pipeline that converts PDFs into clean, semantic HTML, with a web
viewer for reviewing conversions and a **Landing Page Maker** for building an
SEO/AEO/a11y landing page from each document.

Source PDFs live in `sources/<folder>/`; conversions are written to
`output/pdfium/<slug>/`. A document's **slug** is `<folder>--<slugified-name>`
(run `list` to see them).

## Usage

### Command line

Run from the project root (`python` = the project venv, `.venv/bin/python`):

| Command | What it does |
|---|---|
| `python -m rk3 list` | List source documents and their conversion status. |
| `python -m rk3 convert <slug> [--force]` | Run the conversion pipeline for a document. `--force` reconverts even if nothing changed. |
| `python -m rk3 remove <slug \| file.pdf>` | Delete a document and **all** its derived artifacts — the source PDF, the `output/` conversion, the per-document sidecars (`.config/.ops/.landing/.landing-theme/.landing-ai.json`), and its `feedback/` notes. Accepts a slug or a PDF filename. |

Conversions are also triggered automatically by the web app when you open an
unconverted document or apply an edit.

### Web app

FastAPI backend + a Vite/React SPA (`app/ui`).

```bash
# backend (also runs as the rk3 systemd service in this environment)
uvicorn app.main:app --host 127.0.0.1 --port 8300

# UI: build once into app/ui/dist (served by the backend at /)
cd app/ui && npm run build
# …or run the Vite dev server (proxies /api and /output to :8300)
cd app/ui && npm run dev
```

### AI (Landing Page Maker)

The AI pass is provider-configurable and has three usage tiers, set in
`config.json` (the `ai` section) or via env vars (`AI_MODE`, `AI_PROVIDER`,
`AI_MODEL`):

| `ai.mode` | Behaviour |
|---|---|
| `none` | No AI — deterministic heuristics only. |
| `analyze` | AI may **locate** content (e.g. identify the intro/executive-summary section for the verbatim Document Summary) but writes nothing. |
| `generate` | AI may also **author** copy (AI Summary styles/lengths, title, key findings). |

`mode` defaults to `generate`. The legacy `"enabled": true/false` still works
(`true` → `generate`, `false` → `none`). The default provider is `anthropic`
(`claude-opus-4-8`). API keys are read from `.env` (`ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, `DEEPSEEK_API_KEY`) — `.env` is gitignored; never commit it.
