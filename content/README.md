# Content registry

One keyed store for **every text piece the product sends out** — static UI copy,
token templates, the prompts we send to AI models, and strings the AI writes
itself (with a static fallback for when AI is off). One mechanism, so any of it
can be edited in one place, versioned in git, and — later — edited through a
git-backed CMS (TinaCMS) without moving off files.

Loaded by [`rk3/content.py`](../rk3/content.py). Frontend copy is served to the
browser via `GET /api/content` and rendered with a `t(key, tokens)` helper.

## Keys are namespaced by SCOPE, then domain, then name

`<scope>.<domain>.<name>` — the scope + domain come from the file path
(`content/<scope>/<domain>.yml`); the name is the key inside that file.

| scope     | who owns it                                                        |
|-----------|--------------------------------------------------------------------|
| `shared`  | reusable across RK3 apps — doc analysis, extraction, the guidance engine |
| `core`    | the shared app shell / chrome (nav, common buttons)                |
| `lpm`     | Landing Page Maker only                                            |
| `express` | RK Express only (future)                                           |
| `custom`  | RK Custom only (future)                                            |

Rule of thumb: **if a string is about the document itself** (its findings,
stories, summary — anything an analysis produces), it's `shared` and every app
can reuse it. **If it's about one app's UI**, scope it to that app. When in
doubt, start narrow (`lpm.*`) and promote to `shared.*` when a second app needs it.

Example: `shared.analysis.guidance_system` (a doc-analysis prompt any app can
run) vs `lpm.assemble.story_count` (a line only the Landing Page Maker shows).

## Entry kinds

Every entry has a `kind`:

| kind       | fields                          | what it is                                     |
|------------|---------------------------------|------------------------------------------------|
| `static`   | `text`                          | a fixed string                                 |
| `template` | `text`, `tokens`                | a string with `{tokens}` filled at render time |
| `prompt`   | `text`, `model?`                | text sent to a model (`model` optional override) |
| `ai`       | `prompt`, `model?`, `fallback`  | AI writes it when AI is on; `fallback` (a template) is used when AI is off |

- **Tokens** use `{name}`. The frontend renders full ICU MessageFormat on the
  same strings, so plurals/conditionals live *in the copy*, e.g.
  `We found {n, plural, one {# story} other {# stories}} in your PDF`. Declare
  the tokens an entry uses so an editor (and validation) knows what's available.
- **`model`** is an optional per-entry model id (e.g. `claude-haiku-4-5`).
  Omit it to use the app's configured default (`config.json` → `ai`). This is
  where "cheap model for this piece, strong model for that one" lives.
- **`ai`** is how "let the AI write this line" and "here's the plain version when
  AI is off" live in one entry — the fallback is what ships when the user has
  turned AI off (their choice), so nothing ever renders blank.

## Files are live

Entries are read fresh (mtime-checked) — edit a `.yml`, the next call uses it, no
restart. Same property the old `prompts/*.md` files had; those migrate into here
incrementally (a caller at a time), so the live pipeline never breaks mid-move.
