import React, { useEffect, useRef, useState } from "react";

export default function FeedbackPopover({ popover, onSubmit, onDelete, onClose,
                                           onApplyOp, nodeInfo }) {
  const { pos, target, question, existing } = popover;
  const [text, setText] = useState(existing?.text ?? "");
  const [choice, setChoice] = useState(question?.chosen ?? null);
  const [armed, setArmed] = useState(false); // delete asks for a second click
  const [editText, setEditText] = useState(null); // non-null => editing element text
  const [opArmed, setOpArmed] = useState(false);
  const boxRef = useRef(null);

  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const x = Math.min(pos.x, window.innerWidth - 340);
  const y = Math.min(pos.y, window.innerHeight - 260);

  const where = target.nid
    ? `element ${target.nid}`
    : target.xf != null
      ? `page ${target.page} @ (${Math.round(target.xf * 100)}%, ${Math.round(target.yf * 100)}%)`
      : "document";

  return (
    <>
      <div className="popover-backdrop" onClick={onClose} />
      <div
        className="popover"
        ref={boxRef}
        style={{ left: x, top: y }}
        onMouseDown={(e) => {
          if (armed && !e.target.closest(".fb-delete")) setArmed(false);
        }}
      >
        {question ? (
          <>
            <p className="q-prompt">{question.prompt}</p>
            <div className="q-options">
              {question.options.map((opt) => (
                <button
                  key={opt}
                  className={"q-option" + (choice === opt ? " chosen" : "")}
                  onClick={() => setChoice(opt)}
                >
                  {opt}{opt === question.chosen ? " (converter's pick)" : ""}
                </button>
              ))}
            </div>
          </>
        ) : (
          <>
            <p className="q-prompt">{existing ? `Edit your note on ${where}` : `Feedback on ${where}`}</p>
            {target.selText && (
              <blockquote className="sel-quote">“{target.selText.slice(0, 120)}”</blockquote>
            )}
            {nodeInfo && !existing && (
              <div className="op-row">
                <button onClick={() => setEditText(nodeInfo.text ?? "")}>✏ Edit text</button>
                {(nodeInfo.type === "heading" || nodeInfo.type === "paragraph") && (
                  <select
                    value={nodeInfo.type === "heading" ? nodeInfo.level : 0}
                    onChange={(e) => onApplyOp({ nid: target.nid, op: "set-level",
                                                 value: +e.target.value })}
                  >
                    <option value={0}>paragraph</option>
                    {[1, 2, 3, 4, 5, 6].map((l) => (
                      <option key={l} value={l}>h{l}</option>
                    ))}
                  </select>
                )}
                <button
                  className={"op-delete" + (opArmed ? " armed" : "")}
                  onClick={() => opArmed
                    ? onApplyOp({ nid: target.nid, op: "delete" })
                    : setOpArmed(true)}
                  onBlur={() => setOpArmed(false)}
                >
                  {opArmed ? "Confirm remove" : "Remove element"}
                </button>
              </div>
            )}
            {editText !== null && (
              <>
                <textarea
                  rows={5}
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                />
                <div className="popover-actions">
                  <button onClick={() => setEditText(null)}>Cancel</button>
                  <button
                    className="primary"
                    onClick={() => onApplyOp({ nid: target.nid, op: "set-text",
                                               value: editText })}
                  >
                    Save text
                  </button>
                </div>
              </>
            )}
          </>
        )}
        {editText === null && (
          <>
            <textarea
              autoFocus
              rows={3}
              placeholder={question ? "Optional note…" : "What should change here?"}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) onSubmit({ text, choice });
              }}
            />
            <div className="popover-actions">
              {existing && !question && (
                <button
                  className={"fb-delete" + (armed ? " armed" : "")}
                  onClick={() => (armed ? onDelete() : setArmed(true))}
                >
                  {armed ? "Confirm Delete" : "Delete"}
                </button>
              )}
              <button onClick={onClose}>Cancel</button>
              <button
                className="primary"
                disabled={question ? !choice : !text.trim()}
                onClick={() => onSubmit({ text, choice })}
              >
                {question ? "Answer" : existing ? "Update note" : "Submit"}
              </button>
            </div>
          </>
        )}
      </div>
    </>
  );
}
