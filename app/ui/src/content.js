// Frontend side of the content registry (see /content/README.md). Fetches the
// UI-copy bundle from /api/content once, then t(key, tokens) renders any string
// with full ICU MessageFormat — so plurals/conditionals ("1 story" vs "8
// stories") live in the copy, editable without touching code.
//
// Prompts never reach the browser; this is static/template/ai-fallback copy only.
import { IntlMessageFormat } from "intl-messageformat";

let _bundle = null;
const _mf = new Map(); // key -> compiled IntlMessageFormat (cache)

// Call once (e.g. at app/tab mount) with the app scope ("lpm"); returns the copy
// bundle. `shared` and `core` copy always come along.
export async function loadContent(scope) {
  if (_bundle) return _bundle;
  const res = await fetch(`/api/content${scope ? `?scope=${encodeURIComponent(scope)}` : ""}`);
  if (!res.ok) throw new Error(`content: ${res.status}`);
  _bundle = await res.json();
  return _bundle;
}

// Render a piece. Missing key returns the key itself (loud, never blank), so a
// gap is obvious in the UI instead of silently empty.
export function t(key, tokens = {}) {
  const e = _bundle && _bundle[key];
  if (!e) return key;
  if (!tokens || Object.keys(tokens).length === 0) {
    // fast path for plain strings
    if (!e.text.includes("{")) return e.text;
  }
  try {
    let mf = _mf.get(key);
    if (!mf) { mf = new IntlMessageFormat(e.text, "en"); _mf.set(key, mf); }
    return mf.format(tokens);
  } catch {
    return e.text;
  }
}
