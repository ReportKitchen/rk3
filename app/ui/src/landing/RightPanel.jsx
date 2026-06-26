import React, { useContext, useEffect } from "react";
import { Puck, usePuck } from "@measured/puck";
import { LandingCtx } from "./landingCtx.js";

const ARCHETYPE_DESC = {
  research: "Executive summary + contents, download-led. For longform reports.",
  campaign: "Findings first, with sharing and a secondary CTA. For surveys & advocacy.",
  annual: "Impact highlights + cover, supporter-facing. For annual / impact reports.",
  toolkit: "Lean: a short summary and the download. For guides & toolkits.",
};

function TemplateButtons() {
  const { archetypes, arch, dirty, onSwitch, onReload } = useContext(LandingCtx);
  return (
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
  );
}

// the saved indicator (rendered in Puck's header via overrides.headerActions)
export function SavedStatus() {
  const { saved } = useContext(LandingCtx);
  return <span className="lp-saved">{saved ? "Saved" : "Saving…"}</span>;
}

// hide the AI Summary from the Add catalog unless AI may generate content
// (overrides.drawerItem)
export function DrawerItem({ name, children }) {
  const { canGenerate } = useContext(LandingCtx);
  if (name === "Summary" && !canGenerate) return null;
  return children;
}

// one accordion section; bodies stay mounted so open/close animates (grid
// 0fr→1fr), and the open section can be collapsed again
function Section({ id, label, open, onToggle, children }) {
  return (
    <div className={"lp-acc-sec" + (open === id ? " open" : "")}>
      <button className="lp-acc-head" onClick={() => onToggle(id)}>{label}</button>
      <div className="lp-acc-wrap">
        <div className="lp-acc-clip">
          <div className="lp-acc-body">{children}</div>
        </div>
      </div>
    </div>
  );
}

// The right panel as an accordion (one section open at a time, or all closed).
// `children` is Puck's fields view, which reflects the current selection
// (root → Page, element → Content).
export default function RightPanel({ children }) {
  const { appState, dispatch } = usePuck();
  // `open` lives in context so it survives the Puck remount on a re-seed
  const { exporting, onExport, open, setOpen, setDispatch } = useContext(LandingCtx);
  const sel = appState?.ui?.itemSelector || null;
  const selKey = sel ? `${sel.zone ?? "root"}:${sel.index}` : null;

  // hide Puck's default left sidebar (we add via the Add accordion section)
  useEffect(() => {
    dispatch({ type: "setUi", ui: { leftSideBarVisible: false } });
  }, [dispatch]);

  // expose dispatch so LandingMaker can swap content in place (setData) on a
  // template switch/reload, avoiding a remount-induced layout jump
  useEffect(() => { setDispatch(dispatch); }, [dispatch, setDispatch]);

  // selecting an element opens Content; deselecting falls back to Page
  useEffect(() => {
    if (selKey) setOpen("content");
    else setOpen((o) => (o === "content" ? "page" : o));
  }, [selKey]);

  // clicking a header toggles it (so any open section can be collapsed);
  // opening Page deselects so its root fields show
  const toggle = (id) => {
    if (id === "page" && open !== "page") dispatch({ type: "setUi", ui: { itemSelector: null } });
    setOpen(open === id ? null : id);
  };

  return (
    <div className="lp-acc">
      <Section id="template" label="Template" open={open} onToggle={toggle}>
        <TemplateButtons />
      </Section>
      <Section id="page" label="Page" open={open} onToggle={toggle}>
        {sel
          ? <p className="lp-hint-sm">Editing an element — open Page to deselect and edit page settings.</p>
          : children}
      </Section>
      <Section id="content" label="Content" open={open} onToggle={toggle}>
        {sel ? children : <p className="lp-hint-sm">Select an element on the page to edit it.</p>}
      </Section>
      <Section id="add" label="Add" open={open} onToggle={toggle}>
        <div className="lp-add-catalog"><Puck.Components /></div>
      </Section>
      <Section id="export" label="Export" open={open} onToggle={toggle}>
        <button className="lp-export" onClick={onExport} disabled={exporting}>
          {exporting ? "Building…" : "Download .zip"}
        </button>
        <p className="lp-export-hint">Self-contained zip: index.html + images + the PDF.</p>
      </Section>
    </div>
  );
}
