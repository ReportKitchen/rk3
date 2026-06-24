import React, { useCallback, useEffect, useRef, useState } from "react";
import { Group, Panel, Separator, useDefaultLayout } from "react-resizable-panels";
import {
  assetBase, sourceUrl,
  getLanding, getLandingTheme, postLanding, postLandingTheme,
} from "../api.js";
import { LandingRenderer } from "./LandingRenderer.jsx";
import IframePreview from "./IframePreview.jsx";
import ControlsPanel from "./ControlsPanel.jsx";
import { exportZip } from "./exportZip.js";
import "./landing.css";

// immutable nested set: setIn(theme, ["elementColors","download","bg"], "#fff")
function setIn(obj, path, value) {
  if (!path.length) return value;
  const [k, ...rest] = path;
  return { ...obj, [k]: setIn(obj?.[k] ?? {}, rest, value) };
}

// The Landing Page Maker tab: a resizable split of controls | live preview.
// config + theme are the source of truth (loaded from / autosaved to the
// server); the preview and the export both render from them.
export default function LandingMaker({ doc }) {
  const slug = doc.slug;
  const [config, setConfig] = useState(null);
  const [theme, setTheme] = useState(null);
  const [saved, setSaved] = useState(true);
  const [exporting, setExporting] = useState(false);
  const layout = useDefaultLayout({ id: "rk3-landing-split", panelIds: ["controls", "preview"] });

  useEffect(() => {
    let alive = true;
    setConfig(null);
    setTheme(null);
    Promise.all([getLanding(slug), getLandingTheme(slug)])
      .then(([c, t]) => { if (alive) { setConfig(c); setTheme(t); } })
      .catch(() => {});
    return () => { alive = false; };
  }, [slug]);

  // debounced autosave. Handlers call scheduleSave() after mutating state;
  // the timer reads the latest state from refs, so nothing is dropped on a
  // quick succession of edits or a tab switch.
  const configRef = useRef(); configRef.current = config;
  const themeRef = useRef(); themeRef.current = theme;
  const timer = useRef();
  const scheduleSave = useCallback(() => {
    setSaved(false);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      Promise.all([
        postLanding(slug, configRef.current),
        postLandingTheme(slug, themeRef.current),
      ]).then(() => setSaved(true)).catch(() => {});
    }, 600);
  }, [slug]);
  useEffect(() => () => clearTimeout(timer.current), []);

  const onToggle = useCallback((id) => {
    setConfig((c) => ({ ...c, blocks: c.blocks.map((b) => b.id === id ? { ...b, enabled: !b.enabled } : b) }));
    scheduleSave();
  }, [scheduleSave]);

  const onMove = useCallback((i, dir) => {
    setConfig((c) => {
      const bs = [...c.blocks];
      const j = i + dir;
      if (j < 0 || j >= bs.length) return c;
      [bs[i], bs[j]] = [bs[j], bs[i]];
      return { ...c, blocks: bs };
    });
    scheduleSave();
  }, [scheduleSave]);

  const onWidth = useCallback((px) => {
    setTheme((t) => ({ ...t, contentWidth: px }));
    scheduleSave();
  }, [scheduleSave]);

  const onColor = useCallback((path, value) => {
    setTheme((t) => setIn(t, path, value));
    scheduleSave();
  }, [scheduleSave]);

  const onExport = useCallback(async () => {
    setExporting(true);
    try { await exportZip(slug, configRef.current, themeRef.current, doc.name); }
    finally { setExporting(false); }
  }, [slug, doc.name]);

  if (!config || !theme) return <div className="lp-loading hint">Loading landing page…</div>;

  return (
    <Group
      orientation="horizontal"
      className="lp-maker"
      style={{ flex: 1, minWidth: 0, minHeight: 0, height: "auto" }}
      defaultLayout={layout.defaultLayout}
      onLayoutChanged={layout.onLayoutChanged}
    >
      <Panel id="controls" defaultSize="32%" minSize="22%" className="lp-controls-panel">
        <ControlsPanel
          config={config} theme={theme}
          onToggle={onToggle} onMove={onMove} onWidth={onWidth} onColor={onColor}
          onExport={onExport} exporting={exporting} saved={saved}
        />
      </Panel>
      <Separator className="resizer" />
      <Panel id="preview" minSize="30%" className="lp-preview-panel">
        <IframePreview theme={theme}>
          <LandingRenderer
            config={config}
            resolveAsset={(src) => `${assetBase(slug)}/${src}`}
            downloadHref={sourceUrl(slug)}
          />
        </IframePreview>
      </Panel>
    </Group>
  );
}
