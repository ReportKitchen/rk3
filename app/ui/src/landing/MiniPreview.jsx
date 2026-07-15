import React from "react";
import { LandingRenderer } from "./LandingRenderer.jsx";
import { themeProps } from "./css.js";

// The modals' live preview.
//
// This deliberately renders LandingRenderer — the same component the static
// export uses — rather than Puck's canvas. So what you see while configuring is
// the thing that ends up in the zip, not an editor approximation of it. It also
// keeps this outside Puck's editor context: root.render and DocSummaryRender
// both call usePuck(), so Puck's own <Render> can't be used here.
//
// Scale is a plain CSS transform: the page renders at its real content width
// and is shrunk to fit, so type and spacing stay proportional.
export default function MiniPreview({
  config,
  theme,
  assetBase,
  downloadHref,
  scale = 0.42,
  caption = "Live preview — updates as you change options",
}) {
  const empty = !(config?.blocks || []).length;
  return (
    <div className="lp-mini">
      <p className="lp-mini-cap">{caption}</p>
      <div className="lp-mini-frame">
        {empty ? (
          <p className="lp-mini-empty">Nothing to preview yet.</p>
        ) : (
          <div
            className="lp-mini-scale"
            style={{ transform: `scale(${scale})`, width: `${100 / scale}%` }}
          >
            <div className="lp-page" style={themeProps(theme)}>
              <LandingRenderer
                config={config}
                resolveAsset={(src) => `${assetBase}/${src}`}
                downloadHref={downloadHref}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
