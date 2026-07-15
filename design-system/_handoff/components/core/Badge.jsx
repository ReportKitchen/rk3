import React from "react";

/**
 * Status Badge — small label for availability states used across offerings:
 * "Available now" (success), "Coming soon" (macaroni), "Free" / "New".
 */
export function Badge({ children, tone = "neutral", dot = false, style, ...rest }) {
  const tones = {
    neutral: { bg: "var(--rk-gray-100)", fg: "var(--rk-rhino-700)", dot: "var(--rk-rhino-500)" },
    success: { bg: "rgba(46,139,87,0.12)", fg: "#1F6B41", dot: "var(--rk-success)" },
    soon: { bg: "var(--rk-macaroni-100)", fg: "var(--rk-macaroni-600)", dot: "var(--rk-macaroni-500)" },
    brand: { bg: "var(--rk-tomato-100)", fg: "var(--rk-tomato-700)", dot: "var(--rk-tomato-500)" },
  };
  const t = tones[tone] || tones.neutral;
  return React.createElement(
    "span",
    {
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        fontFamily: "var(--rk-font-body)",
        fontWeight: 700,
        fontSize: 12,
        textTransform: "uppercase",
        letterSpacing: "0.06em",
        padding: "5px 10px",
        borderRadius: "var(--rk-radius-xs)",
        background: t.bg,
        color: t.fg,
        ...style,
      },
      ...rest,
    },
    [
      dot
        ? React.createElement("span", {
            key: "d",
            style: { width: 7, height: 7, borderRadius: "50%", background: t.dot, display: "inline-block" },
          })
        : null,
      React.createElement("span", { key: "t" }, children),
    ]
  );
}
