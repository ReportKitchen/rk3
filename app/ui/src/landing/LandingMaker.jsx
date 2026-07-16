import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ActionBar, Puck } from "@measured/puck";
import "@measured/puck/puck.css";
import "./landingPage.css"; // bundled so Puck copies it into the canvas iframe
import "./landing.css";
import {
  assetBase, sourceUrl, getIr, getLanding, getLandingTheme, getAiMode,
  getLandingTemplate, getArchetypes, getBlockDefaults, postLanding, postLandingTheme,
  getTemplateUrl, scanTemplate,
} from "../api.js";
import { puckConfig, TYPE_TO_PUCK, LpField } from "./puckConfig.jsx";
import { toPuck, fromPuck, propsToPuck, themeToRoot } from "./puckAdapter.js";
import { ensureFont, primaryFamily } from "./fonts.js";
import { exportZip } from "./exportZip.js";
import { guard } from "../errorBus.js";
import { LandingOptions } from "./landingOptions.js";
import LandingShell from "./LandingShell.jsx";

// the viewport picker means "simulated host-page width", complementary to the
// content-width slider (our column inside that page)
const VIEWPORTS = [
  { width: 400, height: "auto", label: "Mobile" },
  { width: 800, height: "auto", label: "Laptop" },
  { width: 1200, height: "auto", label: "Desktop" },
];

// scanned page-chrome crops -> canvas ghost overlays (absolute URLs the sim can
// load). null when there are no crops, so the sim falls back to grey placeholders.
function buildGhost(regions, base) {
  if (!regions) return null;
  const mk = (r) => (r ? { src: `${base}/${r.src}`, w: r.w, h: r.h, side: r.side } : null);
  const g = { header: mk(regions.header), sidebar: mk(regions.sidebar), footer: mk(regions.footer) };
  return g.header || g.sidebar || g.footer ? g : null;
}

// a figure's caption text: a nested caption child (the "title" variant is the
// caption proper; a "caption" variant is usually the source/credit line)
function captionOf(fig) {
  const caps = (fig.children || []).filter((c) => c.type === "caption");
  const node = caps.find((c) => c.variant === "title") || caps[0];
  if (!node) return "";
  const inner = (node.children || []).filter((c) => c.text).map((c) => c.text).join(" ");
  return (inner || node.text || "").replace(/ /g, " ").trim();
}

// fresh unique ids for a block and any nested slot blocks (templates use
// positional ids that collide when merged across templates)
function freshIds(b) {
  const block = { ...b, id: `${b.type}-${crypto.randomUUID()}` };
  const media = b.props?.media;
  if (Array.isArray(media)) block.props = { ...b.props, media: media.map(freshIds) };
  return block;
}

// Landing Page Maker, on Puck. Our landing.json/theme are the source of truth:
// seed Puck from them via the adapter and autosave changes back.
//
// Puck runs as a custom interface (children of <Puck>) rather than its stock
// editor: the block library and canvas are LandingShell's, and every control
// lives in a modal reached from a block's Configure tag or the Page setup pill.
export default function LandingMaker({ doc }) {
  const slug = doc.slug;
  const [initial, setInitial] = useState(null);
  const [seedKey, setSeedKey] = useState(0);
  const [images, setImages] = useState([]);
  const [blockDefaults, setBlockDefaults] = useState(null);
  const [archetypes, setArchetypes] = useState({});
  const [aiMode, setAiMode] = useState("generate");
  const [arch, setArch] = useState("");
  const [saved, setSaved] = useState(true);
  const [dirty, setDirty] = useState(false);    // edited since the last seed
  const [exporting, setExporting] = useState(false);
  const [fading, setFading] = useState(false);   // crossfade during a re-seed
  const [modal, setModal] = useState(null);      // null | "page" | "block"
  const [templateUrl, setTemplateUrl] = useState(null);  // null => hide Copy my site
  const [copyOn, setCopyOn] = useState(false);   // "Copy my site styles" checkbox
  const [siteGhost, setSiteGhost] = useState(null);  // header/sidebar/footer crops for the canvas
  // copy-my-site state persisted alongside the theme: { on, url, base, scanned,
  // regions }. base = the manual theme to restore when turned off; scanned = the
  // cached client look; regions = crop URLs. Not in Puck root props, so save()
  // re-attaches it.
  const copySiteRef = useRef(null);
  const dataRef = useRef(null);
  const seedingRef = useRef(false);              // swallow the onChange right after a seed
  const dispatchRef = useRef(null);              // Puck's dispatch, registered by the shell
  const setDispatch = useCallback((d) => { dispatchRef.current = d; }, []);
  const archRef = useRef("");                    // current template (not stored in Puck data)
  useEffect(() => { archRef.current = arch; }, [arch]);

  const markSeeded = () => {
    seedingRef.current = true;
    setTimeout(() => { seedingRef.current = false; }, 400);
  };

  // A block's hover/selected tag carries Configure, which is the only way into
  // its settings. setModal is a stable setState, so this object is built once —
  // Puck remounts the fields view if `overrides` changes identity.
  const overrides = useMemo(() => ({
    actionBar: ({ label, children, parentAction }) => (
      <ActionBar label={label}>
        <ActionBar.Group>
          {parentAction}
          <ActionBar.Action label="Configure" onClick={() => setModal("block")}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19 12a7 7 0 0 0-.1-1.2l2-1.6-2-3.4-2.4 1a7 7 0 0 0-2-1.2L14 3h-4l-.4 2.6a7 7 0 0 0-2 1.2l-2.5-1-2 3.4 2 1.6a7 7 0 0 0 0 2.4l-2 1.6 2 3.4 2.5-1a7 7 0 0 0 2 1.2L10 21h4l.4-2.6a7 7 0 0 0 2-1.2l2.4 1 2-3.4-2-1.6c.07-.4.1-.8.1-1.2z" />
            </svg>
          </ActionBar.Action>
          {children}
        </ActionBar.Group>
      </ActionBar>
    ),
    // built-in fields (block config text/radio/textarea) get the same compact
    // wrapper as our custom fields, so the whole modal reads as one system
    fieldLabel: LpField,
  }), []);

  useEffect(() => {
    let alive = true;
    setInitial(null);
    getArchetypes().then((a) => alive && setArchetypes(a)).catch(guard("landing: archetypes", null));
    getAiMode().then((m) => alive && setAiMode(m)).catch(guard("landing: ai mode", null));
    getBlockDefaults(slug).then((d) => alive && setBlockDefaults(d)).catch(guard("landing: block defaults", null));
    getTemplateUrl(slug).then((u) => alive && setTemplateUrl(u)).catch(guard("landing: template url", null));
    Promise.all([getLanding(slug), getLandingTheme(slug)])
      .then(([config, theme]) => {
        if (!alive) return;
        setArch(config.template || "");
        copySiteRef.current = theme.copySite || null;
        setCopyOn(!!theme.copySite?.on);
        setSiteGhost(theme.copySite?.on ? buildGhost(theme.copySite.regions, assetBase(slug)) : null);
        const d = toPuck(config, theme);
        dataRef.current = d;
        markSeeded();
        setDirty(false);
        setInitial(d);
      }).catch(guard("landing: load config/theme", null));
    getIr(slug).then((ir) => {
      if (!alive) return;
      const figs = (ir.body || []).filter((n) => n.type === "figure" && n.src);
      setImages([
        { src: "pages/page-0001.png", label: "Page 1 (cover)", alt: "", caption: "" },
        ...figs.map((f, i) => ({
          src: f.src, label: `Figure ${i + 1} (${f.width}×${f.height})`,
          // the figure's own alt, and its caption (a nested caption child — the
          // 'title' variant is the caption; a 'caption' variant is the credit),
          // so picking an image can prefill both
          alt: (f.alt || "").replace(/ /g, " ").trim(),
          caption: captionOf(f),
        })),
      ]);
    }).catch(guard("landing: load IR", null));
    return () => { alive = false; };
  }, [slug]);

  const timer = useRef();
  const save = useCallback((config, theme) => {
    // keep the copy-my-site metadata alive across the Puck round-trip (root
    // props don't carry it) and let edits accrue to the active mode's slot, so
    // toggling restores what you last had in each mode
    let themeToSave = theme;
    const cs = copySiteRef.current;
    if (cs) {
      copySiteRef.current = { ...cs, [cs.on ? "scanned" : "base"]: theme };
      themeToSave = { ...theme, copySite: copySiteRef.current };
    }
    setSaved(false);
    Promise.all([postLanding(slug, config), postLandingTheme(slug, themeToSave)])
      .then(() => setSaved(true)).catch(guard("landing: save", null));
  }, [slug]);

  const onChange = useCallback((data) => {
    dataRef.current = data;
    if (!seedingRef.current) setDirty(true);
    setSaved(false);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      const { config, theme } = fromPuck(data, archRef.current);
      save(config, theme);
    }, 600);
  }, [save]);
  useEffect(() => () => clearTimeout(timer.current), []);

  // re-seed Puck from a config, with a brief crossfade
  const reseed = useCallback((config, theme) => {
    setFading(true);
    // let the iframe fade out (matches the 0.28s CSS transition), then swap
    // content in place via setData — no remount, so the canvas keeps its width
    // — then fade back in
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
    // Reuse current blocks of shared types (preserving edits), in the new
    // template's order. Templates use positional ids (b1..bN), so a reused
    // block and a new block can collide — assign every merged block a fresh
    // unique id to avoid duplicate ids (which break Puck selection).
    const merged = tmpl.blocks.map((tb) => {
      const c = cur.blocks.find((cb) => cb.type === tb.type);
      return freshIds(c || tb);
    });
    reseed({ version: 1, template: next, blocks: merged }, theme);
  }, [arch, slug, reseed]);

  // reset the current template to its pristine default
  const reloadTemplate = useCallback(async () => {
    const tmpl = await getLandingTemplate(slug, arch);
    const { theme } = fromPuck(dataRef.current);
    reseed(tmpl, theme);
  }, [arch, slug, reseed]);

  // apply a theme to the page (root props), load its font, and persist. setData
  // doesn't fire Puck's onChange, so save explicitly (like reseed). Returns the
  // applied Puck data so the caller can rebase the modal's Cancel snapshot.
  const applyTheme = useCallback((theme) => {
    const next = { ...(dataRef.current || {}), root: { props: themeToRoot(theme) } };
    dataRef.current = next;
    ensureFont(primaryFamily(theme.vars?.["--lp-font"]));  // main doc (modal preview)
    if (dispatchRef.current) dispatchRef.current({ type: "setData", data: next });
    else { setInitial(next); setSeedKey((k) => k + 1); }
    const applied = fromPuck(next, archRef.current);
    save(applied.config, applied.theme);
    return next;
  }, [save]);

  // "Copy my site styles": on => apply the scanned client look (scan once, then
  // cache); off => restore the manual theme captured when it was first turned
  // on. copySiteRef holds { on, url, base, scanned }; save() persists it.
  const toggleCopySite = useCallback(async (on) => {
    setCopyOn(on);   // reflect intent immediately; the scan takes a few seconds
    try {
      const active = fromPuck(dataRef.current).theme;   // current (root props only)
      let cs = copySiteRef.current || { on: false, url: templateUrl, base: null, scanned: null };
      if (on && !cs.scanned) {
        const r = await scanTemplate(slug);             // may throw -> caller shows why
        cs = { ...cs, scanned: r.theme, url: r.url, regions: r.regions || null };
      }
      cs = on ? { ...cs, on: true, base: cs.base || active } : { ...cs, on: false };
      copySiteRef.current = cs;
      setSiteGhost(on ? buildGhost(cs.regions, assetBase(slug)) : null);
      const target = on ? cs.scanned : (cs.base || active);
      const data = applyTheme(target);
      const font = primaryFamily(target.vars?.["--lp-font"]);
      const side = target.preview?.leftSidebar ? "left sidebar"
        : target.preview?.rightSidebar ? "right sidebar" : "no sidebar";
      return { data, summary: on ? `${font} · links ${target.vars["--lp-accent"]} · ${side} · ${target.contentWidth}px` : null };
    } catch (e) {
      setCopyOn(!on);   // scan failed — put the checkbox back
      throw e;
    }
  }, [slug, templateUrl, applyTheme]);

  // persist a specific Puck data object (used by the modal's Cancel, whose
  // setData revert would otherwise leave the autosaved edits in the file)
  const persist = useCallback((data) => {
    const { config, theme } = fromPuck(data, archRef.current);
    save(config, theme);
  }, [save]);

  const onExport = useCallback(async () => {
    setExporting(true);
    try {
      const { config, theme } = fromPuck(dataRef.current, archRef.current);
      await exportZip(slug, config, theme, doc.name);
    } finally { setExporting(false); }
  }, [slug, doc.name]);

  // block defaults converted to Puck prop shape, keyed by Puck type, for
  // prepopulate-on-insert (resolveData reads metadata.blockDefaults)
  const puckBlockDefaults = useMemo(() => {
    if (!blockDefaults) return {};
    const out = {};
    for (const [ourType, props] of Object.entries(blockDefaults)) {
      // strip the editor-only option lists (Version variants / Section list)
      // before they become a block's insert defaults
      const { variants, sections, ...p } = props;
      out[TYPE_TO_PUCK[ourType]] = propsToPuck(ourType, p);
    }
    return out;
  }, [blockDefaults]);

  const summarySections = blockDefaults?.docSummary?.sections || [];
  const metadata = useMemo(() => ({
    slug,
    assetBase: assetBase(slug),
    downloadHref: sourceUrl(slug),
    images,
    summaryVariants: blockDefaults?.summary?.variants || {},
    // DocSummary's resolveData looks the picked section up here. Metadata does
    // reach resolveData and component render — it's only field renders it can't
    // reach, which is what LandingOptions below is for.
    summarySections,
    blockDefaults: puckBlockDefaults,
    // ghost overlays of the client's page chrome, drawn by the root sim render
    siteGhost,
  }), [slug, images, summarySections, blockDefaults, puckBlockDefaults, siteGhost]);

  // the same per-document options, for the custom *fields* (see landingOptions)
  const options = useMemo(() => ({ summarySections, images }), [summarySections, images]);

  if (!initial) return <div className="lp-loading hint">Loading editor…</div>;

  return (
    <LandingOptions.Provider value={options}>
      <div className={"lp-maker" + (fading ? " fading" : "")}>
        <Puck
          key={seedKey}
          config={puckConfig}
          data={initial}
          viewports={VIEWPORTS}
          onChange={onChange}
          metadata={metadata}
          overrides={overrides}
        >
          <LandingShell
            modal={modal}
            setModal={setModal}
            archetypes={archetypes}
            arch={arch}
            dirty={dirty}
            saved={saved}
            exporting={exporting}
            aiMode={aiMode}
            viewports={VIEWPORTS}
            onSwitch={switchTemplate}
            onReload={reloadTemplate}
            onExport={onExport}
            templateUrl={templateUrl}
            copyOn={copyOn}
            onToggleCopy={toggleCopySite}
            onPersist={persist}
            assetBase={assetBase(slug)}
            downloadHref={sourceUrl(slug)}
            setDispatch={setDispatch}
          />
        </Puck>
      </div>
    </LandingOptions.Provider>
  );
}
