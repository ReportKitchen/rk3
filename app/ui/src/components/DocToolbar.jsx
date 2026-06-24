import React from "react";

// toggles for the full document view; lives inside the Convert Document tab
// since every control here only affects the html/pdf representation
export default function DocToolbar({ doc, toggles, setToggles, questionCount, answeredCount }) {
  const done = doc.status === "done";
  const set = (key) => (e) => setToggles((t) => ({ ...t, [key]: e.target.checked }));

  return (
    <div className="doc-toolbar">
      {done && (
        <button
          className={"mode" + (toggles.feedbackMode ? " active" : "")}
          title="When on, clicking the document or the PDF annotates instead of navigating"
          onClick={() => setToggles((t) => ({ ...t, feedbackMode: !t.feedbackMode }))}
        >
          ✏ Feedback {toggles.feedbackMode ? "on" : "off"}
        </button>
      )}
      {done && questionCount > 0 && (
        <button
          className={"mode" + (toggles.panelOpen ? " active" : "")}
          onClick={() => setToggles((t) => ({ ...t, panelOpen: !t.panelOpen }))}
        >
          ? Questions {answeredCount}/{questionCount}
        </button>
      )}
      {doc.pages > 0 && (
        <label><input type="checkbox" checked={toggles.showPdf} onChange={set("showPdf")} /> Original PDF</label>
      )}
      {done && toggles.showPdf && (
        <label><input type="checkbox" checked={toggles.sync} onChange={set("sync")} /> Sync scroll</label>
      )}
      {done && (
        <label><input type="checkbox" checked={toggles.layer3} onChange={set("layer3")} /> Original-look CSS</label>
      )}
    </div>
  );
}
