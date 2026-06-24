// Theming helpers. Page-wide values become CSS custom properties; the actual
// rule text lives in landingPage.css (one source for the Puck canvas and the
// export). Per-element colors are NOT here — they live on each block's props.

export const FONT_LINK =
  "https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&display=swap";

// theme -> { cssProp: value }; usable directly as a React style object (custom
// properties are valid style keys) or stringified for the export.
export function themeProps(theme) {
  return {
    "--lp-width": `${theme?.contentWidth || 800}px`,
    ...(theme?.vars || {}),
  };
}

export const themeCssVars = (theme) =>
  ":root {\n" +
  Object.entries(themeProps(theme)).map(([k, v]) => `  ${k}: ${v};`).join("\n") +
  "\n}";
