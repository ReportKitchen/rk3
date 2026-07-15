import React from "react";

/**
 * Accordion — layered/expandable content, the pattern Report Kitchen uses to
 * make long toolkits scannable. Pass `items` as [{ q, a }]. Single-open by
 * default; set `multi` to allow several open at once.
 */
export function Accordion({ items = [], multi = false, defaultOpen = [0], style, ...rest }) {
  const [open, setOpen] = React.useState(new Set(defaultOpen));
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); });

  const toggle = (i) => {
    setOpen((prev) => {
      const next = new Set(multi ? prev : []);
      if (prev.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  return React.createElement(
    "div",
    { style: { display: "flex", flexDirection: "column", background: "var(--rk-surface-card)", border: "1px solid var(--rk-border)", borderRadius: "var(--rk-radius-md)", overflow: "hidden", ...style }, ...rest },
    items.map((it, i) => {
      const isOpen = open.has(i);
      return React.createElement(
        "div",
        { key: i, style: { borderTop: i === 0 ? "none" : "1px solid var(--rk-border)" } },
        [
          React.createElement(
            "button",
            {
              key: "h",
              onClick: () => toggle(i),
              style: { all: "unset", boxSizing: "border-box", width: "100%", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, padding: "20px 24px", fontFamily: "var(--rk-font-display)", fontWeight: 600, fontSize: 19, color: "var(--rk-text-strong)" },
            },
            [
              React.createElement("span", { key: "q" }, it.q),
              React.createElement("i", { key: "i", "data-lucide": "plus", width: 22, height: 22, style: { strokeWidth: 2,  flexShrink: 0, color: "var(--rk-tomato-500)", transform: isOpen ? "rotate(45deg)" : "rotate(0)", transition: "transform var(--rk-dur) var(--rk-ease-out)" } }),
            ]
          ),
          React.createElement(
            "div",
            { key: "p", style: { display: "grid", gridTemplateRows: isOpen ? "1fr" : "0fr", transition: "grid-template-rows var(--rk-dur-slow) var(--rk-ease-out)" } },
            React.createElement(
              "div",
              { style: { overflow: "hidden" } },
              React.createElement("div", { style: { padding: "0 24px 22px", fontFamily: "var(--rk-font-body)", fontSize: 16, lineHeight: 1.62, color: "var(--rk-text-muted)" } }, it.a)
            )
          ),
        ]
      );
    })
  );
}
