import React, { useEffect, useRef } from "react";

// The design kit's modal: header (icon / title / meta / close), a body the
// caller lays out, and a footer whose right end is always Cancel + Done.
//
// Cancel and Done are different verbs here, so closing must be explicit: Esc
// and the scrim both mean Cancel (discard), never Done.
export default function Modal({ icon, title, meta, width = 780, onCancel, footer, children }) {
  const dialog = useRef(null);

  // Configure is clicked inside the canvas iframe, so without this the focus
  // stays in that document and Esc never reaches us. Moving focus to the dialog
  // on open fixes the key handler and is what a modal owes a keyboard user.
  useEffect(() => { dialog.current?.focus(); }, []);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onCancel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <div className="lp-scrim" onMouseDown={onCancel}>
      <div
        className="lp-modal"
        style={{ width }}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        ref={dialog}
        tabIndex={-1}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="lp-modal-h">
          {icon}
          <span className="lp-modal-t">{title}</span>
          {meta ? <span className="lp-modal-meta">{meta}</span> : null}
          <button className="lp-modal-x" onClick={onCancel} aria-label="Close">✕</button>
        </div>
        <div className="lp-modal-b">{children}</div>
        <div className="lp-modal-f">{footer}</div>
      </div>
    </div>
  );
}

// The footer's standard right end. `note` is the quiet explanation on the left.
export function ModalFooter({ note, destructive, onCancel, onDone, doneLabel = "Done" }) {
  return (
    <>
      {destructive}
      {note ? <span className="lp-modal-note">{note}</span> : null}
      <button className="lp-btn-ghost lp-modal-cancel" onClick={onCancel}>Cancel</button>
      <button className="lp-btn-secondary" onClick={onDone}>{doneLabel}</button>
    </>
  );
}
