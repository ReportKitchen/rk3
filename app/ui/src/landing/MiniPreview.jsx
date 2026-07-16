import React, { useEffect, useRef, useState } from "react";
import { LandingRenderer } from "./LandingRenderer.jsx";
import { themeProps } from "./css.js";
import { ensureFont, primaryFamily } from "./fonts.js";

// a browser viewport is ~800px tall; the landing page's "first screen" is
// roughly that once the host chrome is accounted for — an estimate, drawn as a
// dotted fold line when `fold` is set
const FOLD_PX = 760;

// The modals' live preview.
//
// Renders LandingRenderer — the same component the static export uses — so what
// you see while configuring is what ends up in the zip, not an editor
// approximation. (root.render / DocSummaryRender call usePuck, so Puck's own
// <Render> can't be used here.) Fits the page to the frame width and scrolls
// vertically when it's taller than fits; `chrome` wraps it in a minimal browser
// frame, `fold` marks the estimated first screen.
export default function MiniPreview({ config, theme, assetBase, downloadHref, chrome, fold }) {
  const empty = !(config?.blocks || []).length;
  const contentWidth = theme?.contentWidth || 800;
  const viewRef = useRef(null);
  const innerRef = useRef(null);
  const [scale, setScale] = useState(0.4);
  const [innerH, setInnerH] = useState(0);

  useEffect(() => {
    ensureFont(primaryFamily(theme?.vars?.["--lp-font"]), document);
  }, [theme]);

  // scale to fit the frame width
  useEffect(() => {
    const el = viewRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const measure = () => setScale(Math.min(1, Math.max(0.1, (el.clientWidth - 2) / contentWidth)));
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    measure();
    return () => ro.disconnect();
  }, [contentWidth]);

  // measure the (unscaled) content height so the scroll box is the scaled height
  // — a transform doesn't change layout size, so we set it explicitly
  useEffect(() => {
    const el = innerRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const measure = () => setInnerH(el.scrollHeight);
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    measure();
    return () => ro.disconnect();
  });

  return (
    <div className="lp-mini">
      <div className={"lp-browser" + (chrome ? "" : " bare")}>
        {chrome ? (
          <div className="lp-browser-bar">
            <span className="lp-dot" /><span className="lp-dot" /><span className="lp-dot" />
            <span className="lp-browser-addr">your report on your site</span>
          </div>
        ) : null}
        <div className="lp-browser-view" ref={viewRef}>
          {empty ? (
            <p className="lp-mini-empty">Nothing to preview yet.</p>
          ) : (
            <div className="lp-mini-doc"
              style={{ width: Math.round(contentWidth * scale), height: Math.round(innerH * scale) || undefined }}>
              <div ref={innerRef} className="lp-mini-scale"
                style={{ width: contentWidth, transform: `scale(${scale})`, transformOrigin: "top left" }}>
                <div className="lp-page" style={themeProps(theme)}>
                  <LandingRenderer config={config}
                    resolveAsset={(src) => `${assetBase}/${src}`} downloadHref={downloadHref} />
                </div>
              </div>
              {fold ? (
                <div className="lp-fold" style={{ top: Math.round(FOLD_PX * scale) }}>
                  <span>estimated first screen</span>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
