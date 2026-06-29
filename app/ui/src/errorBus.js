// Central place for surfacing failures. In heavy dev we want crashes and stack
// dumps visible, not swallowed — every silent `.catch` should route here.
const subs = new Set();
let seq = 0;
const items = [];

export function reportError(context, err) {
  // also keep it in the console with the original object for stack inspection
  console.error(`[${context}]`, err);
  const detail = err?.detail || err?.stack || (err == null ? "" : String(err));
  const message = err?.message || (err == null ? "unknown error" : String(err));
  const entry = { id: ++seq, context, message, detail, time: new Date() };
  items.push(entry);
  for (const fn of subs) fn(items.slice());
  return entry;
}

export function subscribe(fn) {
  subs.add(fn);
  fn(items.slice());
  return () => subs.delete(fn);
}

export function dismiss(id) {
  const i = items.findIndex((e) => e.id === id);
  if (i >= 0) items.splice(i, 1);
  for (const fn of subs) fn(items.slice());
}

export function clearErrors() {
  items.length = 0;
  for (const fn of subs) fn(items.slice());
}

// wrap a promise so a rejection is reported (and re-resolved to `fallback` so
// callers keep working) instead of vanishing
export function guard(context, fallback) {
  return (err) => {
    reportError(context, err);
    return fallback;
  };
}
