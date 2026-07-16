import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Puck, usePuck } from "@measured/puck";
import { BlockLibrary } from "./blockLibrary.jsx";
import Modal, { ModalFooter } from "./Modal.jsx";
import MiniPreview from "./MiniPreview.jsx";
import { fromPuck } from "./puckAdapter.js";

const ARCHETYPE_DESC = {
  research: "Executive summary + contents, download-led. For longform reports.",
  campaign: "Findings first, with sharing and a secondary CTA. For surveys & advocacy.",
  annual: "Impact highlights + cover, supporter-facing. For annual / impact reports.",
  toolkit: "Lean: a short summary and the download. For guides & toolkits.",
};

const svg = (paths, size = 15) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="2" aria-hidden="true">{paths}</svg>
);
const GearIcon = ({ size }) => svg(
  <>
    <circle cx="12" cy="12" r="3" />
    <path d="M19 12a7 7 0 0 0-.1-1.2l2-1.6-2-3.4-2.4 1a7 7 0 0 0-2-1.2L14 3h-4l-.4 2.6a7 7 0 0 0-2 1.2l-2.5-1-2 3.4 2 1.6a7 7 0 0 0 0 2.4l-2 1.6 2 3.4 2.5-1a7 7 0 0 0 2 1.2L10 21h4l.4-2.6a7 7 0 0 0 2-1.2l2.4 1 2-3.4-2-1.6c.07-.4.1-.8.1-1.2z" />
  </>, size);
const DocIcon = ({ size }) => svg(<path d="M6 3h9l4 4v14H6zM15 3v4h4M9 11h7M9 15h7" />, size);
// "Copy my site styles": a toggle. On => apply the scanned client look; off =>
// revert to the manual theme. `onToggle(on)` does the work and returns a summary
// (and rebases the modal snapshot); this component owns only the busy/error UI.
// The whole control is hidden by the caller when the doc has no template URL.
function CopyMySite({ on, busy, error, summary, onToggle }) {
  return (
    <div className={"lp-copy" + (on ? " on" : "")}>
      <label className="lp-copy-row">
        <input type="checkbox" checked={on} disabled={busy}
          onChange={(e) => onToggle(e.target.checked)} />
        <span className="lp-copy-label">Copy my site styles</span>
        {busy ? <span className="lp-copy-spin">Scanning…</span> : null}
      </label>
      <p className={"lp-copy-note" + (error ? " err" : "")}>
        {error ? error
          : on && summary ? `Matched — ${summary}`
            : "Pull colours, font, width and layout from your published page. Turn off to restore your own."}
      </p>
    </div>
  );
}

// Page setup: everything that applies to the whole page rather than one block.
// Puck.Fields with nothing selected renders the root fields, so the theme
// controls come straight from puckConfig.root — no second definition of them.
function PageSetupModal({ ctx, onCancel, onDone }) {
  const { archetypes, arch, dirty, onSwitch, onReload, copy, aiMode, preview } = ctx;
  return (
    <Modal
      icon={<GearIcon size={17} />}
      title="Page setup"
      meta="applies to the whole page"
      onCancel={onCancel}
      footer={<ModalFooter note="Cancel puts everything back." onCancel={onCancel} onDone={onDone} />}
    >
      <div className="lp-modal-cfg">
        {copy.hasUrl ? (
          <CopyMySite on={copy.on} busy={copy.busy} error={copy.error}
            summary={copy.summary} onToggle={copy.onToggle} />
        ) : null}
        <p className="lp-modal-l">Template</p>
        <div className="lp-templates">
          {Object.entries(archetypes).map(([k, label]) => (
            <button key={k} className={"lp-tmpl" + (k === arch ? " active" : "")}
              onClick={() => k !== arch && onSwitch(k)}>
              <span className="lp-tmpl-top">
                <span className="lp-tmpl-name">{label}</span>
                {k === arch && dirty && (
                  <span className="lp-tmpl-reload" role="button" title="Reset this template to its default"
                    onClick={(e) => { e.stopPropagation(); onReload(); }}>↻</span>
                )}
              </span>
              <span className="lp-tmpl-desc">{ARCHETYPE_DESC[k] || ""}</span>
            </button>
          ))}
        </div>
        <p className="lp-modal-l">Page</p>
        <Puck.Fields />
        <p className="lp-modal-l">Level of AI</p>
        <p className="lp-modal-ai">
          {aiMode === "generate" ? "AI content generation"
            : aiMode === "analyze" ? "Analysis only — verbatim copy"
              : "AI off"}
          <span> · set for this install, not per page</span>
        </p>
      </div>
      <MiniPreview {...preview} />
    </Modal>
  );
}

// One block's controls, with only that block in the preview.
function BlockConfigModal({ ctx, onCancel, onDone, onRemove }) {
  const { label, position, preview } = ctx;
  return (
    <Modal
      icon={<DocIcon size={17} />}
      title={label}
      meta={position}
      onCancel={onCancel}
      footer={
        <ModalFooter
          destructive={<button className="lp-modal-del" onClick={onRemove}>Remove block</button>}
          onCancel={onCancel}
          onDone={onDone}
        />
      }
    >
      <div className="lp-modal-cfg"><Puck.Fields /></div>
      <MiniPreview {...preview} />
    </Modal>
  );
}

// The builder surface: block library, canvas, and the modals. Lives inside
// <Puck> so it can drive editor state directly.
export default function LandingShell({
  modal, setModal, archetypes, arch, dirty, saved, exporting, aiMode, viewports,
  onSwitch, onReload, onExport, templateUrl, copyOn, onToggleCopy, onPersist,
  assetBase, downloadHref, setDispatch,
}) {
  // `config` here is the Puck config (for block labels); the landing config is
  // derived separately below via fromPuck
  const { appState, dispatch, selectedItem, config: puckCfg } = usePuck();

  // let LandingMaker swap content in place (setData) on a template switch
  useEffect(() => { setDispatch(dispatch); }, [dispatch, setDispatch]);

  // Snapshot the data the moment a modal opens so Cancel can put it back.
  // Puck commits every keystroke to the tree; staging the fields instead would
  // mean reimplementing them, so we let it commit and rewind on Cancel. The
  // AI Summary's resolveData is safe under this: its only side effect is a
  // server-side cache write, which a rewind can harmlessly leave behind.
  const snapshot = useRef(null);
  useEffect(() => {
    if (modal) snapshot.current = appState.data;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- capture at open, not on every edit
  }, [modal]);

  const cancel = useCallback(() => {
    const snap = snapshot.current;
    if (snap) {
      dispatch({ type: "setData", data: snap });
      // setData doesn't fire onChange; persist the revert so an edit that
      // already autosaved (or a Match my site) is undone in the file too
      onPersist(snap);
    }
    snapshot.current = null;
    setModal(null);
  }, [dispatch, onPersist, setModal]);

  const done = useCallback(() => {
    snapshot.current = null;
    setModal(null);
  }, [setModal]);

  // Copy my site styles: a committed mode switch (like the Template buttons),
  // so after it applies we rebase the open modal's snapshot — Cancel then
  // reverts later field tweaks, not the toggle itself.
  const [copyBusy, setCopyBusy] = useState(false);
  const [copyError, setCopyError] = useState(null);
  const [copySummary, setCopySummary] = useState(null);
  const toggleCopy = useCallback(async (on) => {
    setCopyBusy(true); setCopyError(null);
    try {
      const r = await onToggleCopy(on);
      if (r?.data) snapshot.current = r.data;
      setCopySummary(r?.summary || null);
    } catch (e) {
      setCopyError(e?.detail || e?.message || "Couldn't scan the page.");
    } finally {
      setCopyBusy(false);
    }
  }, [onToggleCopy]);

  // Page setup edits the root, which Puck shows only when nothing is selected
  const openPageSetup = useCallback(() => {
    dispatch({ type: "setUi", ui: { itemSelector: null } });
    setModal("page");
  }, [dispatch, setModal]);

  const removeBlock = useCallback(() => {
    const sel = appState.ui.itemSelector;
    if (sel) dispatch({ type: "remove", index: sel.index, zone: sel.zone });
    snapshot.current = null;
    setModal(null);
  }, [appState.ui.itemSelector, dispatch, setModal]);

  const { config, theme } = useMemo(() => fromPuck(appState.data), [appState.data]);

  // Puck doesn't mirror the `viewports` prop into ui.viewports.options, so the
  // options come from the same constant Puck was given; only `current` is state.
  // Puck.Preview also ignores viewports/zoom entirely (that lives in Puck's stock
  // Canvas), so we size and scale the preview ourselves.
  const vpState = appState.ui.viewports;
  const vw = vpState.current.width;
  const setViewport = (v) =>
    dispatch({
      type: "setUi",
      ui: { viewports: { ...vpState, current: { width: v.width, height: v.height } } },
    });

  // measure the scroll area so we can fit-scale wide viewports into it
  const scrollRef = useRef(null);
  const [view, setView] = useState({ w: 0, h: 0 });
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => setView({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    setView({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  // zoom: null => auto-fit the viewport width into the scroll area; a number is a
  // manual override (the zoom control). Reset to auto whenever the viewport changes.
  const [zoomManual, setZoomManual] = useState(null);
  useEffect(() => { setZoomManual(null); }, [vw]);
  const fitZoom = view.w ? Math.max(0.1, Math.min(1, (view.w - 40) / vw)) : 1;
  const zoom = zoomManual ?? fitZoom;
  const ZOOM_STEPS = [0.25, 0.33, 0.5, 0.67, 0.8, 0.9, 1];
  const stepZoom = (dir) => {
    const i = ZOOM_STEPS.findIndex((s) => s >= zoom - 0.001);
    const at = i < 0 ? ZOOM_STEPS.length - 1 : i;
    setZoomManual(ZOOM_STEPS[Math.max(0, Math.min(ZOOM_STEPS.length - 1, at + (dir > 0 ? 1 : -1)))]);
  };
  // outer box takes the scaled (physical) size so layout/centering/scroll use it;
  // the inner box is the logical viewport, scaled from its top-left to fill the outer
  const outerStyle = { width: Math.round(vw * zoom), height: view.h || undefined };
  const innerStyle = {
    width: vw, height: view.h ? Math.round(view.h / zoom) : "100%",
    transform: `scale(${zoom})`, transformOrigin: "top left",
  };

  const selId = selectedItem?.props?.id;
  const blockCtx = useMemo(() => {
    if (!selectedItem) return null;
    const content = appState.data.content || [];
    const i = content.findIndex((c) => c.props?.id === selId);
    return {
      label: puckCfg.components[selectedItem.type]?.label || selectedItem.type,
      position: i >= 0 ? `block ${i + 1} of ${content.length}` : "",
      preview: {
        config: { ...config, blocks: config.blocks.filter((b) => b.id === selId) },
        theme, assetBase, downloadHref, scale: 0.62,
        caption: "Live preview — just this block",
      },
    };
  }, [selectedItem, selId, appState.data.content, config, theme, assetBase, downloadHref, puckCfg]);

  return (
    <div className="lp-shell">
      <aside className="lp-lib">
        <p className="lp-lib-h">Blocks — drag onto the page</p>
        <div className="lp-lib-list">
          <BlockLibrary canGenerate={aiMode === "generate"} canAnalyze={aiMode !== "none"} />
        </div>
      </aside>

      <div className="lp-canvas">
        <div className="lp-zoombar">
          <button className="lp-setupchip" onClick={openPageSetup}>
            <GearIcon size={14} />Page setup
          </button>
          <span className="lp-zb-div" />
          <span className="lp-seg">
            {viewports.map((v) => (
              <button key={v.label} onClick={() => setViewport(v)}
                className={v.width === vw ? "on" : ""} title={`${v.width}px`}>
                {v.label}
              </button>
            ))}
          </span>
          <span className="lp-zb-div" />
          <span className="lp-zoom">
            <button onClick={() => stepZoom(-1)} disabled={zoom <= ZOOM_STEPS[0] + 0.001}
              aria-label="Zoom out">−</button>
            <button className="lp-zoom-pct" onClick={() => setZoomManual(null)}
              title="Fit to window">{Math.round(zoom * 100)}%</button>
            <button onClick={() => stepZoom(1)} disabled={zoom >= 1 - 0.001}
              aria-label="Zoom in">+</button>
          </span>
          <span className="lp-zb-div" />
          <span className="lp-saved">{saved ? "Saved" : "Saving…"}</span>
          <button className="lp-btn-primary" onClick={onExport} disabled={exporting}
            title="Self-contained zip: index.html + images + the PDF">
            {exporting ? "Building…" : "Export"}
          </button>
        </div>
        <div className="lp-scroll" ref={scrollRef}>
          <div className="lp-stage-outer" style={outerStyle}>
            <div className="lp-stage" style={innerStyle}>
              <Puck.Preview />
            </div>
          </div>
        </div>
      </div>

      {modal === "page" && (
        <PageSetupModal
          ctx={{
            archetypes, arch, dirty, onSwitch, onReload, aiMode,
            copy: {
              hasUrl: !!templateUrl, on: copyOn, busy: copyBusy,
              error: copyError, summary: copySummary, onToggle: toggleCopy,
            },
            preview: { config, theme, assetBase, downloadHref },
          }}
          onCancel={cancel}
          onDone={done}
        />
      )}
      {modal === "block" && blockCtx && (
        <BlockConfigModal ctx={blockCtx} onCancel={cancel} onDone={done} onRemove={removeBlock} />
      )}
    </div>
  );
}
