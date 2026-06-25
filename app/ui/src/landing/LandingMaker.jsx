import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Puck } from "@measured/puck";
import "@measured/puck/puck.css";
import "./landingPage.css"; // bundled so Puck copies it into the canvas iframe
import "./landing.css";
import {
  assetBase, sourceUrl, getIr, getLanding, getLandingTheme,
  getLandingTemplate, getArchetypes, getBlockDefaults, postLanding, postLandingTheme,
} from "../api.js";
import { puckConfig, TYPE_TO_PUCK } from "./puckConfig.jsx";
import { toPuck, fromPuck, propsToPuck } from "./puckAdapter.js";
import { exportZip } from "./exportZip.js";
import { LandingCtx } from "./landingCtx.js";
import RightPanel, { SavedStatus } from "./RightPanel.jsx";

// the viewport picker means "simulated host-page width", complementary to the
// content-width slider (our column inside that page)
const VIEWPORTS = [
  { width: 400, height: "auto", label: "Mobile" },
  { width: 800, height: "auto", label: "Laptop" },
  { width: 1200, height: "auto", label: "Desktop" },
];

// stable override slots (no live state captured here — RightPanel/SavedStatus
// read live values from LandingCtx, so this object can be created once)
// NOTE: don't override `components` — Puck.Components (our Add catalog) renders
// through that slot. The default left sidebar is hidden via UI state instead.
const OVERRIDES = {
  outline: () => null,
  headerActions: () => <SavedStatus />,
  fields: ({ children }) => <RightPanel>{children}</RightPanel>,
};

// Landing Page Maker, on Puck. Our landing.json/theme are the source of truth:
// seed Puck from them via the adapter and autosave changes back.
export default function LandingMaker({ doc }) {
  const slug = doc.slug;
  const [initial, setInitial] = useState(null);
  const [seedKey, setSeedKey] = useState(0);
  const [images, setImages] = useState([]);
  const [blockDefaults, setBlockDefaults] = useState(null);
  const [archetypes, setArchetypes] = useState({});
  const [arch, setArch] = useState("");
  const [saved, setSaved] = useState(true);
  const [dirty, setDirty] = useState(false);    // edited since the last seed
  const [exporting, setExporting] = useState(false);
  const [fading, setFading] = useState(false);   // crossfade during a re-seed
  const [open, setOpen] = useState("page");       // accordion section (survives re-seed)
  const dataRef = useRef(null);
  const seedingRef = useRef(false);              // swallow the onChange right after a seed
  const dispatchRef = useRef(null);              // Puck's dispatch, registered by RightPanel
  const setDispatch = useCallback((d) => { dispatchRef.current = d; }, []);
  const archRef = useRef("");                    // current template (not stored in Puck data)
  useEffect(() => { archRef.current = arch; }, [arch]);

  const markSeeded = () => {
    seedingRef.current = true;
    setTimeout(() => { seedingRef.current = false; }, 400);
  };

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
        markSeeded();
        setDirty(false);
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
    if (!seedingRef.current) setDirty(true);
    setSaved(false);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      const { config, theme } = fromPuck(data);
      config.template = archRef.current || config.template; // template is our state, not in Puck data
      save(config, theme);
    }, 600);
  }, [save]);
  useEffect(() => () => clearTimeout(timer.current), []);

  // re-seed Puck from a config, with a brief crossfade
  const reseed = useCallback((config, theme) => {
    setFading(true);
    // let the iframe fade out (matches the 0.28s CSS transition), then swap
    // content in place via setData — no remount, so the canvas column keeps
    // its width and the right panel doesn't jump — then fade back in
    setTimeout(() => {
      const d = toPuck(config, theme);
      dataRef.current = d;
      setArch(config.template || "");
      markSeeded();
      setDirty(false);
      if (dispatchRef.current) {
        dispatchRef.current({ type: "setData", data: d });
      } else {
        setInitial(d);
        setSeedKey((k) => k + 1);
      }
      save(config, theme);
      setTimeout(() => setFading(false), 80);
    }, 300);
  }, [save]);

  // switch templates: type-merge so the user's edits to shared blocks survive;
  // add the new template's blocks, drop the ones it doesn't use, reorder to it
  const switchTemplate = useCallback(async (next) => {
    if (next === arch) return;
    const tmpl = await getLandingTemplate(slug, next);
    const { config: cur, theme } = fromPuck(dataRef.current);
    const merged = tmpl.blocks.map((tb) => {
      const c = cur.blocks.find((cb) => cb.type === tb.type);
      return c ? { ...c } : tb;
    });
    reseed({ version: 1, template: next, blocks: merged }, theme);
  }, [arch, slug, reseed]);

  // reset the current template to its pristine default
  const reloadTemplate = useCallback(async () => {
    const tmpl = await getLandingTemplate(slug, arch);
    const { theme } = fromPuck(dataRef.current);
    reseed(tmpl, theme);
  }, [arch, slug, reseed]);

  const onExport = useCallback(async () => {
    setExporting(true);
    try {
      const { config, theme } = fromPuck(dataRef.current);
      config.template = archRef.current || config.template;
      await exportZip(slug, config, theme, doc.name);
    } finally { setExporting(false); }
  }, [slug, doc.name]);

  // block defaults converted to Puck prop shape, keyed by Puck type, for
  // prepopulate-on-insert (resolveData reads metadata.blockDefaults)
  const puckBlockDefaults = useMemo(() => {
    if (!blockDefaults) return {};
    const out = {};
    for (const [ourType, props] of Object.entries(blockDefaults)) {
      let p = props;
      if (ourType === "summary" && p.variants) { const { variants, ...rest } = p; p = rest; }
      out[TYPE_TO_PUCK[ourType]] = propsToPuck(ourType, p);
    }
    return out;
  }, [blockDefaults]);

  const metadata = useMemo(() => ({
    assetBase: assetBase(slug),
    downloadHref: sourceUrl(slug),
    images,
    summaryVariants: blockDefaults?.summary?.variants || {},
    blockDefaults: puckBlockDefaults,
  }), [slug, images, blockDefaults, puckBlockDefaults]);

  const ctx = useMemo(() => ({
    archetypes, arch, dirty, exporting, saved, open, setOpen, setDispatch,
    onSwitch: switchTemplate, onReload: reloadTemplate, onExport,
  }), [archetypes, arch, dirty, exporting, saved, open, setDispatch, switchTemplate, reloadTemplate, onExport]);

  if (!initial) return <div className="lp-loading hint">Loading editor…</div>;

  return (
    <LandingCtx.Provider value={ctx}>
      <div className={"lp-maker" + (fading ? " fading" : "")}>
        <Puck
          key={seedKey}
          config={puckConfig}
          data={initial}
          viewports={VIEWPORTS}
          onChange={onChange}
          metadata={metadata}
          overrides={OVERRIDES}
        />
      </div>
    </LandingCtx.Provider>
  );
}
