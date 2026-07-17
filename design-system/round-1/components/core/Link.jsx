import React from "react";

/**
 * Text link in the Report Kitchen tomato style. `emphasis="macaroni"` swaps
 * to a thick macaroni underline for high-spotlight inline links.
 */
export function Link({ children, href = "#", emphasis = "default", style, ...rest }) {
  const [hover, setHover] = React.useState(false);
  const macaroni = emphasis === "macaroni";
  const base = {
    color: macaroni ? "var(--rk-rhino-900)" : "var(--rk-text-link)",
    fontFamily: "var(--rk-font-body)",
    fontWeight: 600,
    textDecoration: "none",
    backgroundImage: macaroni
      ? "linear-gradient(var(--rk-macaroni-500), var(--rk-macaroni-500))"
      : "linear-gradient(currentColor, currentColor)",
    backgroundSize: hover || macaroni ? "100% 2px" : "0% 2px",
    backgroundPosition: macaroni ? "0 100%" : "0 100%",
    backgroundRepeat: "no-repeat",
    paddingBottom: 1,
    transition: "background-size var(--rk-dur) var(--rk-ease-out), color var(--rk-dur)",
    ...style,
  };
  if (macaroni) base.backgroundSize = "100% 6px";
  return React.createElement(
    "a",
    {
      href,
      style: base,
      onMouseEnter: () => setHover(true),
      onMouseLeave: () => setHover(false),
      ...rest,
    },
    children
  );
}
