import React from "react";

/**
 * Report Kitchen primary action control.
 * Variants: primary (tomato), secondary (rhino outline), accent (macaroni),
 * ghost. Sizes sm | md | lg. Optional Lucide icon name on either side.
 */
export function Button({
  children,
  variant = "primary",
  size = "md",
  pill = false,
  iconLeft,
  iconRight,
  href,
  disabled = false,
  full = false,
  style,
  ...rest
}) {
  const iconRef = React.useRef(null);
  React.useEffect(() => {
    if (window.lucide && iconRef.current) window.lucide.createIcons();
  });

  const sizes = {
    sm: { fontSize: 14, padding: "8px 16px", gap: 6, icon: 16 },
    md: { fontSize: 16, padding: "12px 22px", gap: 8, icon: 18 },
    lg: { fontSize: 18, padding: "16px 30px", gap: 10, icon: 20 },
  };
  const s = sizes[size] || sizes.md;

  const palette = {
    primary: { bg: "var(--rk-tomato-500)", bgHover: "var(--rk-tomato-600)", fg: "#fff", bd: "transparent" },
    secondary: { bg: "transparent", bgHover: "var(--rk-rhino-100)", fg: "var(--rk-rhino-700)", bd: "var(--rk-rhino-700)" },
    accent: { bg: "var(--rk-macaroni-500)", bgHover: "var(--rk-macaroni-600)", fg: "var(--rk-rhino-900)", bd: "transparent" },
    ghost: { bg: "transparent", bgHover: "var(--rk-rhino-100)", fg: "var(--rk-rhino-700)", bd: "transparent" },
  };
  const p = palette[variant] || palette.primary;

  const base = {
    display: full ? "flex" : "inline-flex",
    width: full ? "100%" : undefined,
    alignItems: "center",
    justifyContent: "center",
    gap: s.gap,
    fontFamily: "var(--rk-font-body)",
    fontWeight: 700,
    fontSize: s.fontSize,
    lineHeight: 1,
    padding: s.padding,
    color: p.fg,
    background: p.bg,
    border: `2px solid ${p.bd}`,
    borderRadius: pill ? "var(--rk-radius-pill)" : "var(--rk-radius-sm)",
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.5 : 1,
    textDecoration: "none",
    transition: "background var(--rk-dur) var(--rk-ease-out), transform var(--rk-dur-fast) var(--rk-ease-out), box-shadow var(--rk-dur) var(--rk-ease-out)",
    whiteSpace: "nowrap",
    ...style,
  };

  const onEnter = (e) => { if (disabled) return; e.currentTarget.style.background = p.bgHover; e.currentTarget.style.transform = "translateY(-1px)"; };
  const onLeave = (e) => { if (disabled) return; e.currentTarget.style.background = p.bg; e.currentTarget.style.transform = "translateY(0)"; };

  const inner = [
    iconLeft ? React.createElement("i", { key: "l", ref: iconRef, "data-lucide": iconLeft, width: s.icon, height: s.icon, style: { strokeWidth: 2.25 } }) : null,
    React.createElement("span", { key: "t" }, children),
    iconRight ? React.createElement("i", { key: "r", ref: iconRef, "data-lucide": iconRight, width: s.icon, height: s.icon, style: { strokeWidth: 2.25 } }) : null,
  ];

  const tag = href ? "a" : "button";
  return React.createElement(
    tag,
    { style: base, href: href, disabled: tag === "button" ? disabled : undefined, onMouseEnter: onEnter, onMouseLeave: onLeave, ...rest },
    inner
  );
}
