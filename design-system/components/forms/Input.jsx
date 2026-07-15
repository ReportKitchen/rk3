import React from "react";

/**
 * Input — labelled text field for contact / signup forms. Optional Lucide
 * icon, helper text, and error state. Focus shows the muffin-blue ring.
 */
export function Input({ label, type = "text", placeholder, icon, helper, error, id, style, ...rest }) {
  const [focus, setFocus] = React.useState(false);
  const fieldId = id || `rk-inp-${Math.random().toString(36).slice(2, 7)}`;
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); });

  const borderColor = error ? "var(--rk-danger)" : focus ? "var(--rk-muffin)" : "var(--rk-border-strong)";
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
          icon
            ? React.createElement("i", { key: "i", "data-lucide": icon, width: 18, height: 18, style: { strokeWidth: 2,  position: "absolute", left: 14, color: "var(--rk-rhino-500)", pointerEvents: "none" } })
            : null,
          React.createElement("input", {
            key: "f",
            id: fieldId,
            type,
            placeholder,
            onFocus: () => setFocus(true),
            onBlur: () => setFocus(false),
            style: {
              width: "100%",
              boxSizing: "border-box",
              fontFamily: "var(--rk-font-body)",
              fontSize: 16,
              color: "var(--rk-text-body)",
              padding: icon ? "13px 16px 13px 42px" : "13px 16px",
              background: "var(--rk-white)",
              border: `1.5px solid ${borderColor}`,
              borderRadius: "var(--rk-radius-sm)",
              outline: "none",
              boxShadow: focus ? "var(--rk-ring)" : "none",
              transition: "border-color var(--rk-dur), box-shadow var(--rk-dur)",
            },
            ...rest,
          }),
        ]
      ),
      helper || error
        ? React.createElement("span", { key: "h", style: { fontFamily: "var(--rk-font-body)", fontSize: 13, color: error ? "var(--rk-danger)" : "var(--rk-text-muted)" } }, error || helper)
        : null,
    ]
  );
}
