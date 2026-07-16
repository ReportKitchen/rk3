// Loading the landing page's body font on demand. The theme carries a font
// family (default Public Sans, or a scanned client font); it only *renders* if
// the web font is actually loaded. The three surfaces each need it in their own
// document: the modal preview (main document), the Puck canvas (its iframe),
// and the export (its own <head>, built by exportZip).

const GENERIC = new Set([
  "system-ui", "-apple-system", "sans-serif", "serif", "monospace",
  "ui-sans-serif", "ui-serif", "ui-monospace", "inherit",
]);

export function primaryFamily(stack) {
  return (stack || "").split(",")[0].trim().replace(/^["']|["']$/g, "");
}

// A Google Fonts href for a family. If Google doesn't have it the stylesheet
// 404s and the browser falls back — same outcome as not loading it, no error.
export function googleFontHref(family) {
  const fam = family.trim().replace(/\s+/g, "+");
  return `https://fonts.googleapis.com/css2?family=${fam}:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap`;
}

// Inject the font's stylesheet into a document once (idempotent by family). No-op
// for generic families, which need no loading.
export function ensureFont(family, doc = document) {
  if (!family || GENERIC.has(family.toLowerCase())) return;
  const id = "lp-font-" + family.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  if (!doc || !doc.head || doc.getElementById(id)) return;
  const link = doc.createElement("link");
  link.id = id;
  link.rel = "stylesheet";
  link.href = googleFontHref(family);
  doc.head.appendChild(link);
}

// The <link> href the export should load for a theme's font.
export function fontHrefForTheme(theme) {
  const fam = primaryFamily(theme?.vars?.["--lp-font"]) || "Public Sans";
  return googleFontHref(GENERIC.has(fam.toLowerCase()) ? "Public Sans" : fam);
}
