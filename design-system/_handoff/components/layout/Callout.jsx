import React from "react";

// Whisk mark inlined as SVG so the component is portable at any path depth
// (no external asset request). Fill follows the `color` prop.
const WHISK_PATHS = [
  "M16.1,4.7c0-1-0.8-1.8-1.7-1.8L1.8,2.7C0.8,2.7,0,3.5,0,4.4c0,1,0.8,1.8,1.7,1.8l12.6,0.2C15.3,6.5,16,5.7,16.1,4.7z M0.8,4.5c0-0.4,0.4-0.8,0.8-0.8c0.4,0,0.8,0.4,0.8,0.8c0,0.4-0.4,0.8-0.8,0.8C1.2,5.2,0.8,4.9,0.8,4.5z",
  "M20,4.8C20,4.8,20,4.8,20,4.8c0-0.1,0.1-0.2,0.2-0.2C20.8,4.4,34.5,0,37.2,0c2.8,0,5,2.4,5,5.2c0,2.8-2.4,5.1-5.2,5l0,0c-2.7,0-16.2-4.9-16.8-5.1C20.1,5,20,4.9,20,4.8z M41.7,5.1c0-2.5-2-4.5-4.5-4.6c-2.3,0-13.2,3.4-16.1,4.3c2.9,1,13.7,4.8,16,4.9C39.5,9.7,41.6,7.7,41.7,5.1z",
  "M20,4.8C20,4.8,20,4.8,20,4.8c0-0.1,0.1-0.2,0.2-0.2c0.6-0.1,14.3-2.8,16.9-2.8c2.8,0,5,1.6,5,3.4c0,0.9-0.6,1.8-1.6,2.4c-1,0.6-2.2,0.9-3.6,0.9c-2.7,0-16.2-3.3-16.8-3.4C20.1,5,20,4.9,20,4.8z M41.7,5.1c0-1.5-2-2.8-4.5-2.9c-2.2,0-12.2,1.9-15.7,2.6C24.8,5.6,34.8,7.9,37,7.9c1.2,0,2.4-0.3,3.3-0.8C41.2,6.6,41.6,5.9,41.7,5.1z",
  "M20,4.8C20,4.8,20,4.8,20,4.8c0-0.1,0.1-0.2,0.2-0.3c0.6,0,14.2-1,16.9-0.9c1.3,0,2.5,0.2,3.5,0.4c1.1,0.3,1.6,0.7,1.6,1.1c0,1-2.7,1.4-5.1,1.4l0,0c-2.7,0-16.2-1.4-16.8-1.5C20.1,5,20,4.9,20,4.8z M41.7,5.2c0-0.1-0.2-0.4-1.2-0.6c-0.9-0.2-2.1-0.4-3.4-0.4c-1.9,0-9.5,0.4-13.8,0.7C27.6,5.3,35.2,6,37.1,6C40,6.1,41.6,5.5,41.7,5.2z",
];

function WhiskMark({ color, style }) {
  return React.createElement(
    "svg",
    { viewBox: "0 0 42.2 10.2", width: 210, height: 51, fill: color, "aria-hidden": "true", style },
    [
      ...WHISK_PATHS.map((d, i) => React.createElement("path", { key: i, d })),
      React.createElement("rect", { key: "r", x: 18, y: 2.3, width: 1.9, height: 4.9,
        transform: "matrix(0.01756758 -0.9998 0.9998 0.01756758 13.783 23.5703)" }),
    ]
  );
}

/**
 * Callout — full-width CTA band. tone: rhino (default dark), tomato, cream.
 * Optional whisk accent in the corner (the one sanctioned decorative use).
 */
export function Callout({
  eyebrow,
  title,
  children,
  primaryLabel = "Contact the Kitchen",
  primaryHref = "#",
  onClickPrimary,
  secondaryLabel,
  secondaryHref = "#",
  onClickSecondary,
  tone = "rhino",
  whisk = true,
  style,
  ...rest
}) {
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); });
  const tones = {
    rhino: { bg: "var(--rk-rhino-700)", fg: "#fff", sub: "var(--rk-text-on-dark)", eb: "var(--rk-macaroni-500)", whisk: "#fff", primary: "accent" },
    tomato: { bg: "var(--rk-tomato-500)", fg: "#fff", sub: "rgba(255,255,255,0.9)", eb: "#fff", whisk: "#fff", primary: "light" },
    cream: { bg: "var(--rk-cream)", fg: "var(--rk-rhino-900)", sub: "var(--rk-text-muted)", eb: "var(--rk-tomato)", whisk: "var(--rk-rhino-700)", primary: "brand" },
  };
  const t = tones[tone] || tones.rhino;

  const btn = (label, href, kind, onClick) => {
    const styles = {
      accent: { bg: "var(--rk-macaroni-500)", fg: "var(--rk-rhino-900)" },
      brand: { bg: "var(--rk-tomato-500)", fg: "#fff" },
      light: { bg: "#fff", fg: "var(--rk-tomato-600)" },
    }[kind];
    return React.createElement(
      "a",
      { key: "p", href, onClick, style: { display: "inline-flex", alignItems: "center", gap: 8, fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 16, padding: "14px 26px", borderRadius: "var(--rk-radius-sm)", background: styles.bg, color: styles.fg, textDecoration: "none", cursor: "pointer" } },
      [React.createElement("span", { key: "l" }, label), React.createElement("i", { key: "a", "data-lucide": "arrow-right", width: 18, height: 18, style: { strokeWidth: 2.25 } })]
    );
  };

  return React.createElement(
    "div",
    {
      style: {
        position: "relative",
        overflow: "hidden",
        background: t.bg,
        color: t.fg,
        borderRadius: "var(--rk-radius-xl)",
        padding: "56px 52px",
        display: "flex",
        flexDirection: "column",
        gap: 18,
        alignItems: "flex-start",
        ...style,
      },
      ...rest,
    },
    [
      whisk
        ? React.createElement(WhiskMark, { key: "w", color: t.whisk, style: { position: "absolute", right: -10, top: 22, opacity: 0.16, transform: "rotate(-8deg)", pointerEvents: "none" } })
        : null,
      eyebrow
        ? React.createElement("span", { key: "e", style: { position: "relative", fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 13, textTransform: "uppercase", letterSpacing: "0.08em", color: t.eb } }, eyebrow)
        : null,
      React.createElement("h2", { key: "t", style: { position: "relative", margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 700, fontSize: 42, lineHeight: 1.08, letterSpacing: "-0.02em", maxWidth: 620, textWrap: "balance" } }, title),
      children
        ? React.createElement("p", { key: "c", style: { position: "relative", margin: 0, fontFamily: "var(--rk-font-body)", fontSize: 18, lineHeight: 1.6, color: t.sub, maxWidth: 560 } }, children)
        : null,
      React.createElement(
        "div",
        { key: "cta", style: { position: "relative", display: "flex", gap: 12, flexWrap: "wrap", marginTop: 6 } },
        [
          btn(primaryLabel, primaryHref, t.primary, onClickPrimary),
          secondaryLabel
            ? React.createElement("a", { key: "s", href: secondaryHref, onClick: onClickSecondary, style: { display: "inline-flex", alignItems: "center", padding: "14px 22px", fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 16, color: t.fg, textDecoration: "none", opacity: 0.9, cursor: "pointer" } }, secondaryLabel)
            : null,
        ]
      ),
    ]
  );
}
