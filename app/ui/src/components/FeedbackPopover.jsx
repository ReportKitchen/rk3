import React, { useEffect, useRef, useState } from "react";

export default function FeedbackPopover({ popover, onSubmit, onDelete, onClose }) {
  const { pos, target, question, existing } = popover;
  const [text, setText] = useState(existing?.text ?? "");
  const [choice, setChoice] = useState(question?.chosen ?? null);
  const [armed, setArmed] = useState(false); // delete asks for a second click
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
          <p className="q-prompt">{existing ? `Edit your note on ${where}` : `Feedback on ${where}`}</p>
        )}
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
      </div>
    </>
  );
}
