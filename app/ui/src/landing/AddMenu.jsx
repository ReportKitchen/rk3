import React, { useEffect, useState } from "react";
import { usePuck } from "@measured/puck";

const uid = (t) => `${t}-${Math.random().toString(36).slice(2, 9)}`;

// Our "+ Add" replaces Puck's always-on component palette: it opens a modal
// of available sections and appends the chosen one. Rendered inside Puck (via
// overrides.headerActions) so it can use usePuck. Also hides Puck's left
// sidebar on mount, since the palette now lives here.
export default function AddMenu() {
  const { dispatch, config } = usePuck();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    dispatch({ type: "setUi", ui: { leftSideBarVisible: false } });
  }, [dispatch]);

  const add = (type) => {
    const def = config.components[type]?.defaultProps || {};
    const item = { type, props: { id: uid(type), ...def } };
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
              {Object.entries(config.components).map(([type, c]) => (
                <button key={type} className="lp-add-item" onClick={() => add(type)}>
                  {c.label || type}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
