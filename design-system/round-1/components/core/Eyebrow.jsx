import React from "react";

/**
 * Eyebrow — small tracked-out uppercase label that sits above section
 * headings. Optional leading tick mark in the accent color.
 */
export function Eyebrow({ children, color = "tomato", tick = true, style, ...rest }) {
  const colors = {
    tomato: "var(--rk-tomato)",
    macaroni: "var(--rk-macaroni-600)",
    muffin: "var(--rk-rhino-500)",
    white: "var(--rk-macaroni-500)",
  };
  const c = colors[color] || colors.tomato;
  return React.createElement(
    "span",
    {
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        fontFamily: "var(--rk-font-body)",
        fontWeight: 700,
        fontSize: 13,
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        color: c,
        ...style,
      },
      ...rest,
    },
    [
      tick ? React.createElement("span", { key: "t", style: { width: 18, height: 2, background: c, display: "inline-block" } }) : null,
      React.createElement("span", { key: "l" }, children),
    ]
  );
}
