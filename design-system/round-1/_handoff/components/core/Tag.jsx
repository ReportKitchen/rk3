import React from "react";

/**
 * Small pill Tag for topics / categories (e.g. "Housing", "Toolkit").
 * tone: neutral | tomato | macaroni | muffin | rhino. `interactive` adds
 * hover affordance for filter chips.
 */
export function Tag({ children, tone = "neutral", interactive = false, active = false, style, ...rest }) {
  const [hover, setHover] = React.useState(false);
  const tones = {
    neutral: { bg: "var(--rk-white)", fg: "var(--rk-rhino-700)", bd: "var(--rk-border-strong)" },
    tomato: { bg: "var(--rk-tomato-100)", fg: "var(--rk-tomato-700)", bd: "transparent" },
    macaroni: { bg: "var(--rk-macaroni-100)", fg: "var(--rk-macaroni-600)", bd: "transparent" },
    muffin: { bg: "var(--rk-rhino-100)", fg: "var(--rk-rhino-700)", bd: "transparent" },
    rhino: { bg: "var(--rk-rhino-700)", fg: "#fff", bd: "transparent" },
  };
  const t = tones[tone] || tones.neutral;
  const isActive = active || (interactive && hover);
  const base = {
    display: "inline-flex",
    alignItems: "center",
    fontFamily: "var(--rk-font-body)",
    fontWeight: 600,
    fontSize: 13,
    lineHeight: 1,
    letterSpacing: "0.01em",
    padding: "6px 12px",
    borderRadius: "var(--rk-radius-pill)",
    background: active ? "var(--rk-rhino-700)" : t.bg,
    color: active ? "#fff" : t.fg,
    border: `1px solid ${active ? "transparent" : t.bd}`,
    cursor: interactive ? "pointer" : "default",
    transition: "background var(--rk-dur), color var(--rk-dur)",
    ...style,
  };
  if (interactive && hover && !active) base.background = "var(--rk-rhino-100)";
  return React.createElement(
    "span",
    {
      style: base,
      onMouseEnter: interactive ? () => setHover(true) : undefined,
      onMouseLeave: interactive ? () => setHover(false) : undefined,
      ...rest,
    },
    children
  );
}
