import React, { useCallback, useEffect, useRef, useState } from "react";
import { Puck } from "@measured/puck";
import "@measured/puck/puck.css";
import "./landingPage.css"; // bundled so Puck copies it into the canvas iframe
import "./landing.css";
import {
  assetBase, sourceUrl, getIr, getLanding, getLandingTheme,
  getLandingTemplate, getArchetypes, getBlockDefaults, postLanding, postLandingTheme,
} from "../api.js";
import { puckConfig } from "./puckConfig.jsx";
import { toPuck, fromPuck } from "./puckAdapter.js";
import { exportZip } from "./exportZip.js";
import AddMenu from "./AddMenu.jsx";

// trimmed Puck chrome: no outline, no always-on palette (we add via the modal)
const noChrome = { outline: () => null, components: () => null };

// the viewport picker now means "simulated host-page width", complementary to
// the content-width slider (our column inside that page)
const VIEWPORTS = [
  { width: 400, height: "auto", label: "Mobile" },
  { width: 800, height: "auto", label: "Laptop" },
  { width: 1200, height: "auto", label: "Desktop" },
];

// Landing Page Maker, on Puck. Our landing.json/theme remain the source of
// truth: we seed Puck from them via the adapter and autosave changes back.
// The document gets an auto-detected archetype template; the user can switch.
export default function LandingMaker({ doc }) {
  const slug = doc.slug;
  const [initial, setInitial] = useState(null); // seed Puck (re-seeded on switch)
  const [seedKey, setSeedKey] = useState(0);     // bump to remount Puck on re-seed
  const [images, setImages] = useState([]);
  const [blockDefaults, setBlockDefaults] = useState(null);
  const [archetypes, setArchetypes] = useState({});
  const [arch, setArch] = useState("");
  const [saved, setSaved] = useState(true);
  const [exporting, setExporting] = useState(false);
  const dataRef = useRef(null); // latest Puck data (from onChange)

  useEffect(() => {
    let alive = true;
    setInitial(null);
    getArchetypes().then((a) => alive && setArchetypes(a)).catch(() => {});
    getBlockDefaults(slug).then((d) => alive && setBlockDefaults(d)).catch(() => {});
    Promise.all([getLanding(slug), getLandingTheme(slug)])
      .then(([config, theme]) => {
        if (!alive) return;
        setArch(config.template || "");
        const d = toPuck(config, theme);
        dataRef.current = d;
        setInitial(d);
      }).catch(() => {});
    getIr(slug).then((ir) => {
      if (!alive) return;
      const figs = (ir.body || []).filter((n) => n.type === "figure" && n.src);
      setImages([
        { src: "pages/page-0001.png", label: "Page 1 (cover)" },
        ...figs.map((f, i) => ({ src: f.src, label: `Figure ${i + 1} (${f.width}×${f.height})` })),
      ]);
    }).catch(() => {});
    return () => { alive = false; };
  }, [slug]);

  const timer = useRef();
  const save = useCallback((config, theme) => {
    setSaved(false);
    Promise.all([postLanding(slug, config), postLandingTheme(slug, theme)])
      .then(() => setSaved(true)).catch(() => {});
  }, [slug]);

  const onChange = useCallback((data) => {
    dataRef.current = data;
    setSaved(false);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      const { config, theme } = fromPuck(data);
      save(config, theme);
    }, 600);
  }, [save]);
  useEffect(() => () => clearTimeout(timer.current), []);

  const switchTemplate = useCallback(async (next) => {
    if (next === arch) return;
    if (!window.confirm(`Switch to the “${archetypes[next] || next}” template? This replaces the current layout (your colors and width are kept).`)) return;
    const config = await getLandingTemplate(slug, next);
    const { theme } = fromPuck(dataRef.current); // keep current theme
    const d = toPuck(config, theme);
    dataRef.current = d;
    setArch(next);
    setInitial(d);
    setSeedKey((k) => k + 1); // remount Puck with the new content
    save(config, theme);
  }, [arch, archetypes, slug, save]);

  const onExport = useCallback(async () => {
    setExporting(true);
    try {
      const { config, theme } = fromPuck(dataRef.current);
      await exportZip(slug, config, theme, doc.name);
    } finally { setExporting(false); }
  }, [slug, doc.name]);

  if (!initial) return <div className="lp-loading hint">Loading editor…</div>;

  return (
    <div className="lp-maker">
      <Puck
        key={seedKey}
        config={puckConfig}
        data={initial}
        viewports={VIEWPORTS}
        onChange={onChange}
        metadata={{
          assetBase: assetBase(slug),
          downloadHref: sourceUrl(slug),
          images,
          // live summary variants (intro/neutral/hardsell/heuristic), so the
          // Summary "Version" switch is always driven by the current extraction
          summaryVariants: blockDefaults?.summary?.variants || {},
        }}
        overrides={{
          ...noChrome,
          headerActions: () => (
            <span className="lp-header-actions">
              <AddMenu blockDefaults={blockDefaults} />
              <label className="lp-template">
                Template:
                <select value={arch} onChange={(e) => switchTemplate(e.target.value)}>
                  {Object.entries(archetypes).map(([k, label]) => (
                    <option key={k} value={k}>{label}</option>
                  ))}
                </select>
              </label>
              <span className="lp-saved">{saved ? "Saved" : "Saving…"}</span>
              <button className="lp-export" onClick={onExport} disabled={exporting}>
                {exporting ? "Building…" : "Download .zip"}
              </button>
            </span>
          ),
        }}
      />
    </div>
  );
}
