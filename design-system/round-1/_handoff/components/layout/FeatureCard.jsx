import React from "react";

/**
 * FeatureCard — used for offerings and value props. Icon tile, title, body,
 * optional availability Badge and a trailing action link. Hover nudges the
 * arrow and lifts the card.
 */
export function FeatureCard({
  icon = "sparkles",
  title,
  children,
  badge,
  badgeTone = "success",
  action,
  href = "#",
  accent = "tomato",
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); });

  const accents = {
    tomato: { bg: "var(--rk-tomato-100)", fg: "var(--rk-tomato-600)" },
    macaroni: { bg: "var(--rk-macaroni-100)", fg: "var(--rk-macaroni-600)" },
    muffin: { bg: "var(--rk-rhino-100)", fg: "var(--rk-rhino-500)" },
    rhino: { bg: "var(--rk-rhino-100)", fg: "var(--rk-rhino-700)" },
  };
  const a = accents[accent] || accents.tomato;

  const badgeTones = {
    success: { bg: "rgba(46,139,87,0.12)", fg: "#1F6B41" },
    soon: { bg: "var(--rk-macaroni-100)", fg: "var(--rk-macaroni-600)" },
    brand: { bg: "var(--rk-tomato-100)", fg: "var(--rk-tomato-700)" },
  };
  const bt = badgeTones[badgeTone] || badgeTones.success;

  const wrap = {
    display: "flex",
    flexDirection: "column",
    gap: 14,
    padding: "28px",
    background: "var(--rk-surface-card)",
    border: "1px solid var(--rk-border)",
    borderRadius: "var(--rk-radius-lg)",
    textDecoration: "none",
    boxShadow: hover ? "var(--rk-shadow-md)" : "none",
    transform: hover ? "translateY(-3px)" : "translateY(0)",
    transition: "transform var(--rk-dur) var(--rk-ease-out), box-shadow var(--rk-dur) var(--rk-ease-out)",
    ...style,
  };

  return React.createElement(
    action ? "a" : "div",
    { href: action ? href : undefined, style: wrap, onMouseEnter: () => setHover(true), onMouseLeave: () => setHover(false), ...rest },
    [
      React.createElement(
        "div",
        { key: "top", style: { display: "flex", alignItems: "center", justifyContent: "space-between" } },
        [
          React.createElement(
            "div",
            { key: "ico", style: { width: 52, height: 52, borderRadius: "var(--rk-radius-md)", background: a.bg, display: "flex", alignItems: "center", justifyContent: "center" } },
            React.createElement("i", { "data-lucide": icon, width: 26, height: 26, style: { strokeWidth: 2,  color: a.fg } })
          ),
          badge
            ? React.createElement(
                "span",
                { key: "b", style: { fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 12, textTransform: "uppercase", letterSpacing: "0.06em", padding: "5px 10px", borderRadius: "var(--rk-radius-xs)", background: bt.bg, color: bt.fg } },
                badge
              )
            : null,
        ]
      ),
      React.createElement("h3", { key: "t", style: { margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 700, fontSize: 22, lineHeight: 1.15, letterSpacing: "-0.01em", color: "var(--rk-text-strong)" } }, title),
      children
        ? React.createElement("p", { key: "c", style: { margin: 0, fontFamily: "var(--rk-font-body)", fontSize: 15.5, lineHeight: 1.6, color: "var(--rk-text-muted)" } }, children)
        : null,
      action
        ? React.createElement(
            "span",
            { key: "a", style: { marginTop: "auto", display: "inline-flex", alignItems: "center", gap: 7, fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 15, color: "var(--rk-tomato-600)" } },
            [
              React.createElement("span", { key: "l" }, action),
              React.createElement("i", { key: "arr", "data-lucide": "arrow-right", width: 17, height: 17, style: { strokeWidth: 2.25,  transform: hover ? "translateX(4px)" : "translateX(0)", transition: "transform var(--rk-dur) var(--rk-ease-out)" } }),
            ]
          )
        : null,
    ]
  );
}
