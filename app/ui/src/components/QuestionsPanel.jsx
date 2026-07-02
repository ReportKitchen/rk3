import React from "react";

export default function QuestionsPanel({
  questions, answers, feedback, onJump, onAnswer, onClear, onEmptyTrash,
  ops = [], onRemoveOp, resolveNid = null,
}) {
  const comments = feedback.filter((f) => f.type === "comment" && f.status !== "cleared");
  const trashCount = feedback.filter((f) => f.status === "cleared").length;

  return (
    <div className="qpanel">
      {comments.length > 0 && (
        <>
          <h2>Feedback notes</h2>
          <ul>
            {comments.map((c) => (
              <li key={c.id ?? c.ts} className={c.status === "resolved" ? "resolved" : "open"}>
                {c.nid ? (
                  <button className="jump" onClick={() => onJump(c.nid)}>
                    {c.page != null ? `p${c.page}` : "doc"}
                  </button>
                ) : (
                  <span className="jump-placeholder">{c.page != null ? `p${c.page}` : "doc"}</span>
                )}
                <div className="q-body">
                  {c.selText && <blockquote className="sel-quote">“{c.selText.slice(0, 80)}”</blockquote>}
                  <p>{c.text}</p>
                  {c.status === "resolved" && c.resolution && (
                    <p className="resolution">{c.resolution}</p>
                  )}
                  <button
                    className="q-clear"
                    title="Mark corrected — hides the note (kept in trash, recoverable)"
                    onClick={() => onClear(c.id)}
                  >
                    ✓ Mark corrected
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
      <h2>Converter questions</h2>
      {questions.length === 0 && <p className="hint">None for this document.</p>}
      <ul>
        {questions.map((q) => {
          const answered = answers.has(q.qid);
          return (
            <li key={q.qid} className={answered ? "resolved" : "open"}>
              <button className="jump" onClick={() => onJump(q.nid)} title="Show in document">
                p{q.page}
              </button>
              <div className="q-body">
                <p>{q.prompt}</p>
                {answered ? (
                  <p className="q-state">✓ answered: <strong>{answers.get(q.qid)}</strong></p>
                ) : (
                  <button className="q-answer" onClick={() => onAnswer(q)}>Answer…</button>
                )}
              </div>
            </li>
          );
        })}
      </ul>
      {ops.length > 0 && (
        <>
          <h2>Edits</h2>
          <ul>
            {ops.map((o) => {
              // where this op actually lands in the document: merges live on
              // their INTO node (frm is folded away at render); the synthetic
              // "merge-…"/"reorder-doc" keys match nothing in the DOM
              const target = o.op === "merge" ? o.into
                : o.op === "reorder" ? null : o.nid;
              const info = target && resolveNid ? resolveNid(target) : null;
              return (
                <li key={o.op + o.nid} className={o.orphaned ? "resolved" : "open"}>
                  <button className="jump" disabled={!target}
                          title={target ? "Show in document" : "Whole-document edit"}
                          onClick={() => target && onJump(target)}>→</button>
                  <div className="q-body">
                    <p>
                      <strong>{o.op}</strong>
                      {o.op === "reorder" &&
                        ` — whole document (${(o.order || []).length} elements)`}
                      {o.op === "merge" && !info && " → (target not in this build)"}
                      {o.value !== undefined && `: ${String(o.value).slice(0, 60)}`}
                      {info && ` · p${info.page} · “${(info.text || info.type || "").slice(0, 70)}”`}
                      {o.orphaned && " (orphaned)"}
                    </p>
                    {target && <code className="op-nid">{target}</code>}
                    <button className="q-clear" title="Undo this edit"
                            onClick={() => onRemoveOp(o)}>Undo</button>
                  </div>
                </li>
              );
            })}
          </ul>
        </>
      )}
      {trashCount > 0 && (
        <p className="trash-row">
          Trash: {trashCount} cleared note{trashCount > 1 ? "s" : ""}
          {" · "}
          <button className="trash-empty" onClick={onEmptyTrash}>Empty trash</button>
        </p>
      )}
    </div>
  );
}
