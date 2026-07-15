import React from "react";

/**
 * Icon — thin wrapper over Lucide (the system's icon set). Renders a Lucide
 * placeholder and asks the global `lucide` to hydrate it. Pages must load
 * <script src="https://unpkg.com/lucide@latest"></script> once.
 * name = any Lucide icon id (e.g. "arrow-right", "upload", "file-text").
 */
export function Icon({ name, size = 20, strokeWidth = 2, color = "currentColor", style, ...rest }) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  }, [name, size]);
  return React.createElement("i", {
    ref,
    "data-lucide": name,
    width: size,
    height: size,
    style: { display: "inline-flex", color, strokeWidth, verticalAlign: "middle", ...style },
    ...rest,
  });
}
