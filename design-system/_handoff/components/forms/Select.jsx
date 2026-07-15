import React from "react";

/**
 * Select — native dropdown styled to match the form field system, with a
 * Lucide chevron. Pass `options` as strings or [{value,label}].
 */
export function Select({ label, options = [], placeholder = "Select…", helper, id, style, ...rest }) {
  const [focus, setFocus] = React.useState(false);
  const fieldId = id || `rk-sel-${Math.random().toString(36).slice(2, 7)}`;
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); });
  const opts = options.map((o) => (typeof o === "string" ? { value: o, label: o } : o));
  return React.createElement(
    "div",
    { style: { display: "flex", flexDirection: "column", gap: 7, ...style } },
    [
      label
        ? React.createElement("label", { key: "l", htmlFor: fieldId, style: { fontFamily: "var(--rk-font-body)", fontWeight: 600, fontSize: 14, color: "var(--rk-text-strong)" } }, label)
        : null,
      React.createElement(
        "div",
        { key: "w", style: { position: "relative", display: "flex", alignItems: "center" } },
        [
          React.createElement(
            "select",
            {
              key: "f",
              id: fieldId,
              defaultValue: "",
              onFocus: () => setFocus(true),
              onBlur: () => setFocus(false),
              style: {
                width: "100%",
                boxSizing: "border-box",
                appearance: "none",
                fontFamily: "var(--rk-font-body)",
                fontSize: 16,
                color: "var(--rk-text-body)",
                padding: "13px 42px 13px 16px",
                background: "var(--rk-white)",
                border: `1.5px solid ${focus ? "var(--rk-muffin)" : "var(--rk-border-strong)"}`,
                borderRadius: "var(--rk-radius-sm)",
                outline: "none",
                cursor: "pointer",
                boxShadow: focus ? "var(--rk-ring)" : "none",
                transition: "border-color var(--rk-dur), box-shadow var(--rk-dur)",
              },
              ...rest,
            },
            [
              React.createElement("option", { key: "ph", value: "", disabled: true }, placeholder),
              ...opts.map((o, i) => React.createElement("option", { key: i, value: o.value }, o.label)),
            ]
          ),
          React.createElement("i", { key: "c", "data-lucide": "chevron-down", width: 18, height: 18, style: { strokeWidth: 2,  position: "absolute", right: 14, color: "var(--rk-rhino-500)", pointerEvents: "none" } }),
        ]
      ),
      helper
        ? React.createElement("span", { key: "h", style: { fontFamily: "var(--rk-font-body)", fontSize: 13, color: "var(--rk-text-muted)" } }, helper)
        : null,
    ]
  );
}
