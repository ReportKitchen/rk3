import React from "react";
import { BLOCK_LABELS } from "./LandingRenderer.jsx";

// Color swatches exposed in v1. Each maps to a CSS variable the preview reads
// live. `path` says where the value lives in the theme object.
const COLOR_FIELDS = [
  { label: "Page background", path: ["vars", "--lp-page-bg"] },
  { label: "Content background", path: ["vars", "--lp-content-bg"] },
  { label: "Body text", path: ["vars", "--lp-text"] },
  { label: "Headings", path: ["vars", "--lp-heading"] },
  { label: "Accent / links", path: ["vars", "--lp-accent"] },
  { label: "Highlights box", path: ["elementColors", "highlights", "bg"] },
  { label: "Download button", path: ["elementColors", "download", "bg"] },
  { label: "Download text", path: ["elementColors", "download", "fg"] },
];

const get = (obj, path) => path.reduce((o, k) => (o ? o[k] : undefined), obj);

export default function ControlsPanel({
  config, theme, onToggle, onMove, onWidth, onColor, onExport, exporting, saved,
}) {
  const blocks = config?.blocks || [];
  const width = theme?.contentWidth || 800;

  return (
    <div className="lp-controls">
      <div className="lp-controls-head">
        <h2>Landing Page</h2>
        <span className="lp-saved">{saved ? "Saved" : "Saving…"}</span>
      </div>

      <section>
        <h3>Elements</h3>
        <ul className="lp-elements">
          {blocks.map((b, i) => (
            <li key={b.id} className={b.enabled ? "" : "off"}>
              <label className="lp-el-toggle">
                <input type="checkbox" checked={b.enabled}
                  onChange={() => onToggle(b.id)} />
                {BLOCK_LABELS[b.type] || b.type}
                {b.type === "summary" && b.props?.source === "heuristic" && (
                  <span className="lp-tag" title="Auto-extracted; AI summary coming soon">auto</span>
                )}
              </label>
              <span className="lp-reorder">
                <button disabled={i === 0} onClick={() => onMove(i, -1)} title="Move up">↑</button>
                <button disabled={i === blocks.length - 1} onClick={() => onMove(i, 1)} title="Move down">↓</button>
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3>Content width</h3>
        <div className="lp-width">
          <input type="range" min="600" max="1200" step="20" value={width}
            onChange={(e) => onWidth(+e.target.value)} />
          <input type="number" min="600" max="1200" value={width}
            onChange={(e) => onWidth(Math.min(1200, Math.max(600, +e.target.value || 800)))} />
          <span className="lp-unit">px</span>
        </div>
      </section>

      <section>
        <h3>Colors</h3>
        <ul className="lp-colors">
          {COLOR_FIELDS.map((f) => (
            <li key={f.label}>
              <input type="color" value={get(theme, f.path) || "#000000"}
                onChange={(e) => onColor(f.path, e.target.value)} />
              <span>{f.label}</span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <button className="lp-export" onClick={onExport} disabled={exporting}>
          {exporting ? "Building zip…" : "Download HTML (.zip)"}
        </button>
        <p className="lp-export-hint">Self-contained: index.html + images + the PDF.</p>
      </section>
    </div>
  );
}
