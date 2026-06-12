import React from "react";

export default function QuestionsPanel({ questions, answers, feedback, onJump, onAnswer }) {
  const comments = feedback.filter((f) => f.type === "comment");

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
            {comments.map((c, i) => (
              <li key={i} className={c.status === "resolved" ? "resolved" : "open"}>
                {c.nid ? (
                  <button className="jump" onClick={() => onJump(c.nid)}>p{c.page ?? "?"}</button>
                ) : (
                  <span className="jump-placeholder">p{c.page ?? "?"}</span>
                )}
                <div className="q-body"><p>{c.text}</p></div>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
