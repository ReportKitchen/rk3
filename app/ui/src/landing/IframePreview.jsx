import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { LANDING_CSS, FONT_LINK, applyTheme } from "./css.js";

// Renders the landing page inside an isolated iframe so the preview is true to
// the exported file: the iframe's own BODY scrolls (the page is the document),
// and its styles can't leak to/from the app. React content is portaled into the
// iframe body, so structural edits update live; theme changes are applied as
// CSS variables on the iframe <html> — instant, no content re-render.
export default function IframePreview({ theme, children }) {
  const iframeRef = useRef(null);
  const [mount, setMount] = useState(null);

  const setup = () => {
    const doc = iframeRef.current?.contentDocument;
    if (!doc) return;
    doc.documentElement.lang = "en";
    doc.head.innerHTML =
      `<meta charset="utf-8">` +
      `<link rel="stylesheet" href="${FONT_LINK}">` +
      `<style>${LANDING_CSS}</style>`;
    doc.body.className = "lp-body";
    doc.body.innerHTML = "";
    const root = doc.createElement("div");
    root.className = "lp-page";
    doc.body.appendChild(root);
    applyTheme(doc.documentElement, theme);
    setMount(root);
  };

  // re-apply theme vars whenever the theme changes (live, no re-render)
  useEffect(() => {
    const doc = iframeRef.current?.contentDocument;
    if (doc && mount) applyTheme(doc.documentElement, theme);
  }, [theme, mount]);

  return (
    <>
      <iframe
        ref={iframeRef}
        className="lp-preview-frame"
        title="Landing page preview"
        srcDoc="<!doctype html><html><head></head><body></body></html>"
        onLoad={setup}
      />
      {mount && createPortal(children, mount)}
    </>
  );
}
