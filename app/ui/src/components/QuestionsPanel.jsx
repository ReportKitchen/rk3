import React from "react";

export default function QuestionsPanel({
  questions, answers, feedback, onJump, onAnswer, onClear, onEmptyTrash,
  ops = [], onRemoveOp,
}) {
  const comments = feedback.filter((f) => f.type === "comment" && f.status !== "cleared");
  const trashCount = feedback.filter((f) => f.status === "cleared").length;

  return (
    <div className="qpanel">
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
                  {c.status === "resolved" && (
                    <>
                      {c.resolution && <p className="resolution">{c.resolution}</p>}
                      <button
                        className="q-clear"
                        title="Confirmed — move this note to trash"
                        onClick={() => onClear(c.id)}
                      >
                        Clear
                      </button>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
      {ops.length > 0 && (
        <>
          <h2>Edits</h2>
          <ul>
            {ops.map((o) => (
              <li key={o.op + o.nid} className={o.orphaned ? "resolved" : "open"}>
                <button className="jump" onClick={() => onJump(o.nid)}>→</button>
                <div className="q-body">
                  <p>
                    <strong>{o.op}</strong>
                    {o.value !== undefined && `: ${String(o.value).slice(0, 60)}`}
                    {o.orphaned && " (orphaned)"}
                  </p>
                  <button className="q-clear" title="Undo this edit"
                          onClick={() => onRemoveOp(o)}>Undo</button>
                </div>
              </li>
            ))}
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
