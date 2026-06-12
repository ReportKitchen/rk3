import React, { useCallback, useEffect, useMemo, useState } from "react";
import { deleteFeedback, getDocuments, getFeedback, getIr, startConvert, postFeedback } from "./api.js";
import DocList from "./components/DocList.jsx";
import DocumentView from "./components/DocumentView.jsx";
import FeedbackPopover from "./components/FeedbackPopover.jsx";
import QuestionsPanel from "./components/QuestionsPanel.jsx";
import Toolbar from "./components/Toolbar.jsx";

export default function App() {
  const [docs, setDocs] = useState([]);
  const [selected, setSelected] = useState(null);
  const [toggles, setToggles] = useState({
    showPdf: true, sync: true, layer3: true, feedbackMode: false, panelOpen: false,
  });
  const [ir, setIr] = useState(null);
  const [feedback, setFeedback] = useState([]);
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
    if (doc?.status === "done") getIr(doc.slug).then(setIr).catch(() => setIr(null));
  }, [doc?.slug, doc?.status]);

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
    const entry = p.question
      ? { type: "answer", qid: p.question.qid, choice, text, ...p.target }
      : { type: "comment", text, ...p.target };
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
              doc={doc}
              toggles={toggles}
              questions={questions}
              answers={answers}
              feedback={feedback}
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
        />
      )}
    </div>
  );
}
