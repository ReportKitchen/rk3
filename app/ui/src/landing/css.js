// Landing page styles, shared verbatim by the live preview (injected into the
// iframe) and the export (inlined into index.html), so what you see is what you
// download. All theming flows through CSS custom properties, so width/color
// changes are instant variable writes — never a re-render.

export const FONT_LINK =
  "https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&display=swap";

export const LANDING_CSS = `
* { box-sizing: border-box; }
.lp-body {
  margin: 0;
  background: var(--lp-page-bg, #f4f4f5);
  color: var(--lp-text, #111);
  font-family: var(--lp-font, system-ui, sans-serif);
  line-height: 1.6;
}
.lp-page { min-height: 100vh; padding: 40px 20px; }

.lp-content,
.lp-page > * {
  max-width: var(--lp-width, 800px);
  margin-left: auto;
  margin-right: auto;
}

.lp-block {
  background: var(--lp-content-bg, #fff);
  padding: 28px 36px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 8px 24px rgba(0,0,0,0.06);
}
/* seamless white column: collapse the gaps between stacked blocks */
.lp-block + .lp-block { padding-top: 0; }

.lp-block h1, .lp-block h2 { color: var(--lp-heading, #111); line-height: 1.25; }
.lp-title h1 { font-size: 2.1rem; font-weight: 700; margin: 0; }
.lp-summary p { font-size: 1.15rem; margin: 0; }

/* figures default to UA margins; zero only the vertical so the horizontal
   auto-centering from .lp-page > * still aligns them with the other blocks */
.lp-cover, .lp-hero { margin-top: 0; margin-bottom: 0; }
.lp-cover img, .lp-hero img {
  display: block; width: 100%; height: auto;
  border: 1px solid #e6e6e6; border-radius: 4px;
}

.lp-toc h2, .lp-highlights h2 {
  font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em;
  color: #666; margin: 0 0 0.6rem;
}
.lp-toc ul { list-style: none; margin: 0; padding: 0; }
.lp-toc li { padding: 0.2rem 0; }
.lp-toc li.lvl-3 { padding-left: 1rem; }
.lp-toc li.lvl-4 { padding-left: 2rem; }
.lp-toc a { color: var(--lp-accent, #1b4965); text-decoration: none; }
.lp-toc a:hover { text-decoration: underline; }

.lp-highlights {
  background: var(--lp-el-highlights-bg, #eef3fa);
}
.lp-highlights ul { margin: 0; padding-left: 1.2rem; }
.lp-highlights li { margin: 0.3rem 0; }

.lp-share { display: flex; align-items: center; gap: 0.75rem; }
.lp-share .lp-share-label {
  font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em; color: #666;
}
.lp-share a {
  border: 1px solid #d0d0d0; border-radius: 4px; padding: 0.3rem 0.7rem;
  font-size: 0.85rem; color: var(--lp-accent, #1b4965); text-decoration: none;
}

.lp-download { text-align: center; }
.lp-cta {
  display: inline-block;
  background: var(--lp-el-download-bg, var(--lp-accent, #1b4965));
  color: var(--lp-el-download-fg, #fff);
  padding: 0.8rem 1.6rem; border-radius: 6px;
  font-weight: 600; text-decoration: none;
}
.lp-cta:hover { filter: brightness(1.08); }
`;

// theme -> { cssProp: value }, the single source both the live preview
// (setProperty) and the export (string) derive from.
export function themeProps(theme) {
  const props = {
    "--lp-width": `${theme?.contentWidth || 800}px`,
    ...(theme?.vars || {}),
  };
  for (const [el, colors] of Object.entries(theme?.elementColors || {})) {
    for (const [key, val] of Object.entries(colors)) {
      props[`--lp-el-${el}-${key}`] = val;
    }
  }
  return props;
}

export const themeCssVars = (theme) =>
  ":root {\n" +
  Object.entries(themeProps(theme)).map(([k, v]) => `  ${k}: ${v};`).join("\n") +
  "\n}";

// live update: write the variables onto the iframe's <html>; instant, no reflow
// of React content
export function applyTheme(docEl, theme) {
  const props = themeProps(theme);
  for (const [k, v] of Object.entries(props)) docEl.style.setProperty(k, v);
}
