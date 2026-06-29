import React, { useEffect, useState } from "react";
import { subscribe, dismiss, clearErrors } from "../errorBus.js";

// Fixed bottom-left stack of failures. Heavy-dev posture: show the context,
// message, and any server-side detail/traceback rather than hiding it.
export default function ErrorBanner() {
  const [errs, setErrs] = useState([]);
  const [open, setOpen] = useState({}); // id -> expanded
  useEffect(() => subscribe(setErrs), []);
  if (!errs.length) return null;
  return (
    <div className="err-banner">
      <div className="err-banner-head">
        <strong>{errs.length} error{errs.length > 1 ? "s" : ""}</strong>
        <button onClick={clearErrors}>clear all</button>
      </div>
      {errs.slice(-6).map((e) => (
        <div className="err-row" key={e.id}>
          <div className="err-line">
            <span className="err-ctx">{e.context}</span>
            <span className="err-msg">{e.message}</span>
            {e.detail && (
              <button className="err-toggle"
                      onClick={() => setOpen((o) => ({ ...o, [e.id]: !o[e.id] }))}>
                {open[e.id] ? "hide" : "details"}
              </button>
            )}
            <button className="err-x" onClick={() => dismiss(e.id)}>×</button>
          </div>
          {open[e.id] && e.detail && <pre className="err-detail">{e.detail}</pre>}
        </div>
      ))}
    </div>
  );
}
