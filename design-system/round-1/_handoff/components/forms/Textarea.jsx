import React from "react";

/**
 * Textarea — multi-line field for "tell us about your report" contact forms.
 */
export function Textarea({ label, placeholder, rows = 4, helper, error, id, style, ...rest }) {
  const [focus, setFocus] = React.useState(false);
  const fieldId = id || `rk-ta-${Math.random().toString(36).slice(2, 7)}`;
  const borderColor = error ? "var(--rk-danger)" : focus ? "var(--rk-muffin)" : "var(--rk-border-strong)";
  return React.createElement(
    "div",
    { style: { display: "flex", flexDirection: "column", gap: 7, ...style } },
    [
      label
        ? React.createElement("label", { key: "l", htmlFor: fieldId, style: { fontFamily: "var(--rk-font-body)", fontWeight: 600, fontSize: 14, color: "var(--rk-text-strong)" } }, label)
        : null,
      React.createElement("textarea", {
        key: "f",
        id: fieldId,
        rows,
        placeholder,
        onFocus: () => setFocus(true),
        onBlur: () => setFocus(false),
        style: {
          width: "100%",
          boxSizing: "border-box",
          fontFamily: "var(--rk-font-body)",
          fontSize: 16,
          lineHeight: 1.5,
          color: "var(--rk-text-body)",
          padding: "13px 16px",
          background: "var(--rk-white)",
          border: `1.5px solid ${borderColor}`,
          borderRadius: "var(--rk-radius-sm)",
          outline: "none",
          resize: "vertical",
          boxShadow: focus ? "var(--rk-ring)" : "none",
          transition: "border-color var(--rk-dur), box-shadow var(--rk-dur)",
        },
        ...rest,
      }),
      helper || error
        ? React.createElement("span", { key: "h", style: { fontFamily: "var(--rk-font-body)", fontSize: 13, color: error ? "var(--rk-danger)" : "var(--rk-text-muted)" } }, error || helper)
        : null,
    ]
  );
}
