import React, { useCallback, useEffect, useMemo, useState } from "react";
import { clearFeedback, deleteFeedback, deleteOp, emptyTrash, getDocuments, getFeedback, getIr, getOps, startConvert, postFeedback, postOp } from "./api.js";
import DocList from "./components/DocList.jsx";
import DocumentView from "./components/DocumentView.jsx";
import FeedbackPopover from "./components/FeedbackPopover.jsx";
import QuestionsPanel from "./components/QuestionsPanel.jsx";
import Toolbar from "./components/Toolbar.jsx";

function findNode(ir, nid) {
  for (const n of ir?.body ?? []) {
    if (n.nid === nid) return n;
    for (const c of n.children ?? []) if (c.nid === nid) return c;
  }
  return null;
}

export default function App() {
  const [docs, setDocs] = useState([]);
  const [selected, setSelected] = useState(null);
  const [toggles, setToggles] = useState({
    showPdf: true, sync: true, layer3: true, feedbackMode: false, panelOpen: false,
  });
  const [ir, setIr] = useState(null);
  const [feedback, setFeedback] = useState([]);
  const [ops, setOps] = useState([]);
  const [docVersion, setDocVersion] = useState(0);
  const [flashNid, setFlashNid] = useState(null);
  // popover: { pos: {x, y}, target: {...}, question? }
  const [popover, setPopover] = useState(null);
  const [scrollToNid, setScrollToNid] = useState(null);

  const doc = docs.find((d) => d.slug === selected);

  const refresh = useCallback(async () => {
    setDocs(await getDocuments());
  }, []);

  const refreshFeedback = useCallback(async () => {
    if (selected) setFeedback(await getFeedback(selected).catch(() => []));
  }, [selected]);

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    setIr(null);
    setPopover(null);
    refreshFeedback();
  }, [selected, refreshFeedback]);

  useEffect(() => {
    if (doc?.status === "done") {
      getIr(doc.slug).then(setIr).catch(() => setIr(null));
      getOps(doc.slug).then(setOps).catch(() => setOps([]));
    }
  }, [doc?.slug, doc?.status, docVersion]);

  // apply an edit op: server reconverts (render-only); poll, then reload the
  // iframe in place (scroll preserved, edited element flashed)
  const applyOp = useCallback(async (op) => {
    if (op.remove) await deleteOp(selected, op.op, op.nid);
    else await postOp(selected, op);
    setPopover(null);
    for (let i = 0; i < 40; i++) {
      await new Promise((r) => setTimeout(r, 500));
      const docs2 = await getDocuments();
      const d = docs2.find((x) => x.slug === selected);
      if (d && d.status !== "in_progress") { setDocs(docs2); break; }
    }
    setFlashNid(op.remove || op.op === "delete" ? null : op.nid);
    setDocVersion((v) => v + 1);
  }, [selected]);

  const questions = ir?.questions ?? [];
  const answers = useMemo(() => {
    const map = new Map();
    for (const f of feedback) if (f.type === "answer" && f.qid) map.set(f.qid, f.choice);
    return map;
  }, [feedback]);

  const annotate = useCallback((target, pos, existing = null) => {
    setPopover({ target, pos, existing });
  }, []);

  const openQuestion = useCallback((question, pos) => {
    setPopover({ target: { nid: question.nid, page: question.page }, pos, question });
  }, []);

  const submitPopover = useCallback(async ({ text, choice }) => {
    const p = popover;
    setPopover(null);
    const node = p.target?.nid ? findNode(ir, p.target.nid) : null;
    const ctx = node?.text ? { elementText: node.text.slice(0, 100) } : {};
    const entry = p.question
      ? { type: "answer", qid: p.question.qid, choice, text,
          qKind: p.question.kind, qPrompt: p.question.prompt.slice(0, 140),
          ...ctx, ...p.target }
      : { type: "comment", text, ...ctx, ...p.target };
    if (p.existing) entry.id = p.existing.id;
    await postFeedback(selected, entry);
    await refreshFeedback();
    setToggles((t) => ({ ...t, panelOpen: true }));
  }, [popover, selected, refreshFeedback]);

  const deletePopover = useCallback(async () => {
    const p = popover;
    setPopover(null);
    await deleteFeedback(selected, p.existing.id);
    await refreshFeedback();
  }, [popover, selected, refreshFeedback]);

  const clearNote = useCallback(async (id) => {
    await clearFeedback(selected, id);
    await refreshFeedback();
  }, [selected, refreshFeedback]);

  const emptyNoteTrash = useCallback(async () => {
    await emptyTrash(selected);
    await refreshFeedback();
  }, [selected, refreshFeedback]);

  const convert = useCallback(async (slug, force) => {
    await startConvert(slug, force);
    await refresh();
  }, [refresh]);

  return (
    <div id="layout">
      <DocList docs={docs} selected={selected} onSelect={setSelected} onRefresh={refresh} />
      <div id="right">
        {doc && (
          <Toolbar
            doc={doc}
            toggles={toggles}
            setToggles={setToggles}
            questionCount={questions.length}
            answeredCount={questions.filter((q) => answers.has(q.qid)).length}
          />
        )}
        <div id="content">
          {doc ? (
            <DocumentView
              key={doc.slug}
              docVersion={docVersion}
              flashNid={flashNid}
              doc={doc}
              toggles={toggles}
              questions={questions}
              answers={answers}
              feedback={feedback}
              pageDims={ir?.pages}
              onConvert={convert}
              onAnnotate={annotate}
              onQuestion={openQuestion}
              scrollToNid={scrollToNid}
              onScrolledToNid={() => setScrollToNid(null)}
              highlightNid={popover?.target?.nid ?? null}
            />
          ) : (
            <p className="hint">Select a document on the left.</p>
          )}
          {toggles.panelOpen && doc?.status === "done" && (
            <QuestionsPanel
              questions={questions}
              answers={answers}
              feedback={feedback}
              onJump={(nid) => setScrollToNid(nid)}
              onAnswer={(q) => openQuestion(q, { x: window.innerWidth / 2, y: 160 })}
              onClear={clearNote}
              onEmptyTrash={emptyNoteTrash}
              ops={ops}
              onRemoveOp={(o) => applyOp({ ...o, remove: true })}
            />
          )}
        </div>
      </div>
      {popover && (
        <FeedbackPopover
          popover={popover}
          onSubmit={submitPopover}
          onDelete={deletePopover}
          onClose={() => setPopover(null)}
          onApplyOp={applyOp}
          nodeInfo={popover.target?.nid ? findNode(ir, popover.target.nid) : null}
        />
      )}
    </div>
  );
}
