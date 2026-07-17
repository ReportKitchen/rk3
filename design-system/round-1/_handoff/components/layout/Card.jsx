import React from "react";

/**
 * ProjectCard — the "Our Work" tile. Photo-free: the cover is a flat color
 * block carrying an oversized Lucide icon and the client/format label. Hover
 * lifts the card and shifts the title to tomato.
 */
export function Card({
  title,
  description,
  client,
  tags = [],
  coverColor = "var(--rk-rhino-700)",
  coverIcon = "file-text",
  coverText,
  href = "#",
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); });

  return React.createElement(
    "a",
    {
      href,
      onMouseEnter: () => setHover(true),
      onMouseLeave: () => setHover(false),
      style: {
        display: "flex",
        flexDirection: "column",
        background: "var(--rk-surface-card)",
        border: "1px solid var(--rk-border)",
        borderRadius: "var(--rk-radius-lg)",
        overflow: "hidden",
        textDecoration: "none",
        boxShadow: hover ? "var(--rk-shadow-md)" : "none",
        transform: hover ? "translateY(-3px)" : "translateY(0)",
        transition: "transform var(--rk-dur) var(--rk-ease-out), box-shadow var(--rk-dur) var(--rk-ease-out)",
        ...style,
      },
      ...rest,
    },
    [
      // cover
      React.createElement(
        "div",
        {
          key: "cover",
          style: {
            position: "relative",
            aspectRatio: "16 / 10",
            background: coverColor,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
          },
        },
        [
          React.createElement("i", {
            key: "ic",
            "data-lucide": coverIcon,
            width: 64,
            height: 64,
            style: { strokeWidth: 1.5,  color: "rgba(255,255,255,0.92)" },
          }),
          coverText
            ? React.createElement(
                "span",
                {
                  key: "ct",
                  style: {
                    position: "absolute",
                    bottom: 14,
                    left: 16,
                    fontFamily: "var(--rk-font-body)",
                    fontWeight: 700,
                    fontSize: 12,
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    color: "rgba(255,255,255,0.85)",
                  },
                },
                coverText
              )
            : null,
        ]
      ),
      // body
      React.createElement(
        "div",
        { key: "body", style: { padding: "20px 22px 22px", display: "flex", flexDirection: "column", gap: 10, flex: 1 } },
        [
          client
            ? React.createElement(
                "span",
                { key: "cl", style: { fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 12, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--rk-tomato)" } },
                client
              )
            : null,
          React.createElement(
            "h3",
            { key: "t", style: { margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 700, fontSize: 22, lineHeight: 1.15, letterSpacing: "-0.01em", color: hover ? "var(--rk-tomato)" : "var(--rk-text-strong)", transition: "color var(--rk-dur)" } },
            title
          ),
          description
            ? React.createElement("p", { key: "d", style: { margin: 0, fontFamily: "var(--rk-font-body)", fontSize: 15, lineHeight: 1.55, color: "var(--rk-text-muted)" } }, description)
            : null,
          tags.length
            ? React.createElement(
                "div",
                { key: "tg", style: { display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 } },
                tags.map((t, i) =>
                  React.createElement("span", { key: i, style: { fontFamily: "var(--rk-font-body)", fontWeight: 600, fontSize: 12, padding: "4px 10px", borderRadius: "var(--rk-radius-pill)", background: "var(--rk-gray-100)", color: "var(--rk-rhino-700)" } }, t)
                )
              )
            : null,
        ]
      ),
    ]
  );
}
