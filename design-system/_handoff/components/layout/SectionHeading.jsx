import React from "react";

/**
 * SectionHeading — eyebrow + display title + optional intro paragraph.
 * align: left | center. `inverse` for use on rhino/dark grounds.
 */
export function SectionHeading({
  eyebrow,
  eyebrowColor = "tomato",
  title,
  intro,
  align = "left",
  inverse = false,
  size = "lg",
  style,
  ...rest
}) {
  const titleSize = size === "sm" ? 28 : size === "md" ? 36 : 48;
  const ec = { tomato: "var(--rk-tomato)", macaroni: "var(--rk-macaroni-500)", muffin: "var(--rk-rhino-500)" }[eyebrowColor] || "var(--rk-tomato)";
  return React.createElement(
    "div",
    {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: 14,
        alignItems: align === "center" ? "center" : "flex-start",
        textAlign: align,
        maxWidth: align === "center" ? 720 : "none",
        marginLeft: align === "center" ? "auto" : undefined,
        marginRight: align === "center" ? "auto" : undefined,
        ...style,
      },
      ...rest,
    },
    [
      eyebrow
        ? React.createElement(
            "span",
            { key: "e", style: { display: "inline-flex", alignItems: "center", gap: 8, fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 13, textTransform: "uppercase", letterSpacing: "0.08em", color: ec } },
            [React.createElement("span", { key: "t", style: { width: 18, height: 2, background: ec } }), React.createElement("span", { key: "x" }, eyebrow)]
          )
        : null,
      React.createElement(
        "h2",
        { key: "t", style: { margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 700, fontSize: titleSize, lineHeight: 1.08, letterSpacing: "-0.02em", color: inverse ? "#fff" : "var(--rk-text-strong)", textWrap: "balance" } },
        title
      ),
      intro
        ? React.createElement(
            "p",
            { key: "i", style: { margin: 0, fontFamily: "var(--rk-font-body)", fontSize: 18, lineHeight: 1.6, color: inverse ? "var(--rk-text-on-dark)" : "var(--rk-text-muted)", maxWidth: 640 } },
            intro
          )
        : null,
    ]
  );
}
