import React, { useEffect, useRef, useState } from "react";
import { getSnapshot, saveAssertion } from "../api.js";
import { reportError } from "../errorBus.js";

// The general "this bit is correct — don't let it change" tool: freeze an
// element's semantic content (text + em/strong/a + list/heading structure),
// derived from the IR so data-*, generated classes and CSS are ignored.
function AssertionForm({ slug, target }) {
  const [snap, setSnap] = useState(null);   // {anchor, html}
  const [loadErr, setLoadErr] = useState(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    let alive = true;
    setSnap(null); setLoadErr(null); setResult(null);
    getSnapshot(slug, target.nid)
      .then((s) => alive && setSnap(s))
      .catch((e) => { reportError("read element to freeze", e); if (alive) setLoadErr(e.message); });
    return () => { alive = false; };
  }, [slug, target.nid]);

  const freeze = async () => {
    if (!snap) return;
    setBusy(true); setResult(null);
    try {
      const check = { freeze: { anchor: snap.anchor, html: snap.html } };
      if (note.trim()) check.note = note.trim();
      setResult(await saveAssertion(slug, check, false));
    } catch (e) {
      reportError("freeze element", e);
      setResult({ ok: false, saved: false, detail: e.message || "request failed" });
    } finally { setBusy(false); }
  };

  return (
    <div className="assert-form">
      <p className="assert-intro">
        Freeze this element’s content — its text, <b>bold</b>/<i>italic</i>, links and
        list/heading structure must stay exactly as shown. Styling, ids and
        <code>data-</code> attributes are ignored.
      </p>
      {loadErr && <div className="assert-result bad">couldn’t read element: {loadErr}</div>}
      {!snap && !loadErr && <div className="assert-spin">⏳ reading element…</div>}
      {snap && <pre className="assert-snapshot">{snap.html}</pre>}
      <input className="assert-note" value={note} placeholder="note (optional, shown in eval output)"
             onChange={(e) => setNote(e.target.value)} />
      {result && (
        <div className={"assert-result " + (result.ok ? "ok" : "bad")}>
          {result.saved ? "✓ frozen — saved" : "✗ not saved"}
          {result.total != null ? ` (${result.total} checks)` : ""}
          {!result.ok && <div className="assert-detail">{result.detail}</div>}
        </div>
      )}
      <div className="popover-actions">
        {busy && <span className="assert-spin">⏳…</span>}
        <button className="primary" disabled={!snap || busy} onClick={freeze}>Freeze it</button>
      </div>
    </div>
  );
}

export default function FeedbackPopover({ popover, slug, onSubmit, onDelete, onClose,
                                          onApplyOp, nodeInfo }) {
  const { pos, target, question, existing } = popover;
  const [text, setText] = useState(existing?.text ?? "");
  const [choice, setChoice] = useState(question?.chosen ?? null);
  const [category, setCategory] = useState(existing?.category ?? "structure");
  const [armed, setArmed] = useState(false); // delete asks for a second click
  const [editText, setEditText] = useState(null); // non-null => editing element text
  const [opArmed, setOpArmed] = useState(false);
  const [tab, setTab] = useState("feedback");
  const boxRef = useRef(null);

  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const x = Math.min(pos.x, window.innerWidth - 360);
  const y = Math.min(pos.y, window.innerHeight - 280);

  const where = target.nid
    ? `element ${target.nid}`
    : target.xf != null
      ? `page ${target.page} @ (${Math.round(target.xf * 100)}%, ${Math.round(target.yf * 100)}%)`
      : "document";

  // assertions are element-anchored — only offered on a real node, not a page spot / question
  const canAssert = !question && !!target.nid;

  return (
    <>
      <div className="popover-backdrop" onClick={onClose} />
      <div
        className={"popover" + (canAssert && tab === "assert" ? " wide" : "")}
        ref={boxRef}
        style={{ left: x, top: y }}
        onMouseDown={(e) => {
          if (armed && !e.target.closest(".fb-delete")) setArmed(false);
        }}
      >
        {!question && (
          <div className="popover-title">{where}</div>
        )}
        {canAssert && (
          <div className="popover-tabs">
            <button className={tab === "feedback" ? "active" : ""} onClick={() => setTab("feedback")}>Feedback</button>
            <button className={tab === "assert" ? "active" : ""} onClick={() => setTab("assert")}>Assertion</button>
          </div>
        )}

        {canAssert && tab === "assert" ? (
          <AssertionForm slug={slug} target={target} />
        ) : (
        <>
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
            <p className="q-prompt">{existing ? "Edit your note" : "What should change here?"}</p>
            <label className="fb-category">
              Type:
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="structure">Content / structure</option>
                <option value="styling">Styling (color, font, size, placement)</option>
                <option value="figure">Figure / feature (image vs text/table…)</option>
                <option value="pattern">Info-design pattern note</option>
              </select>
            </label>
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
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) onSubmit({ text, choice, category });
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
                onClick={() => onSubmit({ text, choice, category })}
              >
                {question ? "Answer" : existing ? "Update note" : "Submit"}
              </button>
            </div>
          </>
        )}
        </>
        )}
      </div>
    </>
  );
}
