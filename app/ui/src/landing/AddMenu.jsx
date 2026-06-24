import React, { useEffect, useState } from "react";
import { usePuck } from "@measured/puck";
import { BLOCK_LABELS } from "./LandingRenderer.jsx";
import { TYPE_TO_PUCK } from "./puckConfig.jsx";
import { propsToPuck } from "./puckAdapter.js";

const uid = (t) => `${t}-${Math.random().toString(36).slice(2, 9)}`;

// order shown in the picker
const ORDER = ["title", "summary", "cover", "hero", "toc", "highlights", "share", "download", "secondaryCta"];

// Our "+ Add" replaces Puck's always-on component palette: it opens a modal of
// available sections and appends the chosen one, prepopulated from the document
// (block-defaults). Rendered inside Puck (via overrides.headerActions) so it can
// use usePuck; also hides Puck's left sidebar on mount.
export default function AddMenu({ blockDefaults }) {
  const { dispatch, config } = usePuck();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    dispatch({ type: "setUi", ui: { leftSideBarVisible: false } });
  }, [dispatch]);

  const add = (type) => {
    const puckType = TYPE_TO_PUCK[type];
    // document-aware props if we have them, else the component's generic defaults
    let props = blockDefaults?.[type] || config.components[puckType]?.defaultProps || {};
    if (type === "summary" && props.variants) {
      const { variants, ...rest } = props; // variants live in metadata, not the block
      props = rest;
    }
    const item = { type: puckType, props: { id: uid(puckType), ...propsToPuck(type, props) } };
    dispatch({ type: "setData", data: (prev) => ({ ...prev, content: [...prev.content, item] }) });
    setOpen(false);
  };

  return (
    <>
      <button className="lp-add-btn" onClick={() => setOpen(true)}>+ Add</button>
      {open && (
        <div className="lp-add-backdrop" onClick={() => setOpen(false)}>
          <div className="lp-add-modal" onClick={(e) => e.stopPropagation()}>
            <div className="lp-add-head">
              <h3>Add a section</h3>
              <button className="lp-add-close" onClick={() => setOpen(false)} aria-label="Close">×</button>
            </div>
            <div className="lp-add-grid">
              {ORDER.map((type) => (
                <button key={type} className="lp-add-item" onClick={() => add(type)}>
                  {BLOCK_LABELS[type] || type}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
