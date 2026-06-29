import React, { useCallback, useEffect, useMemo, useState } from "react";
import { ADMIN_FEEDBACK, ADMIN_METADATA, clearFeedback, deleteFeedback, deleteOp, emptyTrash, getBuildStatus, getDocuments, getFeedback, getIr, getOps, startConvert, postFeedback, postOp } from "./api.js";
import DocList from "./components/DocList.jsx";
import DocumentView from "./components/DocumentView.jsx";
import ErrorBanner from "./components/ErrorBanner.jsx";
import FeedbackPopover from "./components/FeedbackPopover.jsx";
import FeedbackTable from "./components/FeedbackTable.jsx";
import MetadataTable from "./components/MetadataTable.jsx";
import Toolbar from "./components/Toolbar.jsx";
import { guard, reportError } from "./errorBus.js";

function findNode(ir, nid) {
  for (const n of ir?.body ?? []) {
    if (n.nid === nid) return n;
    for (const c of n.children ?? []) if (c.nid === nid) return c;
  }
  return null;
}

// deep link from the All Feedback table: /?doc=<slug>&nid=<nid> opens the doc
// with the feedback panel open, scrolled to that element
const _params = new URLSearchParams(window.location.search);
const DEEPLINK = { doc: _params.get("doc"), nid: _params.get("nid") };

export default function App() {
  const [docs, setDocs] = useState([]);
  const [selected, setSelected] = useState(DEEPLINK.doc || null);
  const [deepLinkNid, setDeepLinkNid] = useState(DEEPLINK.nid || null);
  const [toggles, setToggles] = useState({
    showPdf: true, sync: true, layer3: true, embedFonts: true,
    feedbackMode: false, panelOpen: !!DEEPLINK.doc,
  });
  const [ir, setIr] = useState(null);
  const [feedback, setFeedback] = useState([]);
  const [ops, setOps] = useState([]);
  const [docVersion, setDocVersion] = useState(0);
  const [buildStatus, setBuildStatus] = useState(null);
  const [flashNid, setFlashNid] = useState(null);
  // popover: { pos: {x, y}, target: {...}, question? }
  const [popover, setPopover] = useState(null);

  const doc = docs.find((d) => d.slug === selected);

  const refresh = useCallback(async () => {
    setDocs(await getDocuments());
  }, []);

  const refreshFeedback = useCallback(async () => {
    // admin sentinels ("admin:…") aren't real slugs — the feedback endpoint
    // rejects the colon (400). Skip the per-document fetch for those views.
    if (!selected || selected.startsWith("admin:")) { setFeedback([]); return; }
    setFeedback(await getFeedback(selected).catch(guard("load feedback", [])));
  }, [selected]);

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    setIr(null);
    setPopover(null);
    refreshFeedback();
  }, [selected, refreshFeedback]);

  useEffect(() => {
    if (doc?.status === "done") {
      getIr(doc.slug).then(setIr).catch((e) => { reportError("load IR", e); setIr(null); });
      getOps(doc.slug).then(setOps).catch((e) => { reportError("load ops", e); setOps([]); });
    }
  }, [doc?.slug, doc?.status, docVersion]);

  // build freshness: poll so a CLI/agent rebuild is detected even without an
  // in-app action; build_id (render fingerprint) busts the content iframe
  useEffect(() => {
    if (!selected || selected === ADMIN_FEEDBACK || selected === ADMIN_METADATA) {
      setBuildStatus(null); return;
    }
    let alive = true;
    const tick = () =>
      getBuildStatus(selected)
        .then((s) => alive && setBuildStatus(s))
        .catch((e) => {
          reportError("build status", e);
          if (alive) setBuildStatus({ fetchError: e.message || "unreachable" });
        });
    tick();
    const id = setInterval(tick, 20000);
    return () => { alive = false; clearInterval(id); };
  }, [selected, doc?.finished, docVersion]);

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

  const submitPopover = useCallback(async ({ text, choice, category }) => {
    const p = popover;
    setPopover(null);
    const node = p.target?.nid ? findNode(ir, p.target.nid) : null;
    const ctx = node?.text ? { elementText: node.text.slice(0, 100) } : {};
    const entry = p.question
      ? { type: "answer", qid: p.question.qid, choice, text,
          qKind: p.question.kind, qPrompt: p.question.prompt.slice(0, 140),
          ...ctx, ...p.target }
      : { type: "comment", category, text, ...ctx, ...p.target };
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
        {doc && <Toolbar doc={doc} build={buildStatus} />}
        <div id="content">
          {selected === ADMIN_FEEDBACK ? (
            <FeedbackTable onOpen={setSelected} />
          ) : selected === ADMIN_METADATA ? (
            <MetadataTable onOpen={setSelected} />
          ) : doc ? (
            <DocumentView
              key={doc.slug}
              docVersion={docVersion}
              flashNid={flashNid}
              doc={doc}
              buildId={buildStatus?.build_id}
              toggles={toggles}
              setToggles={setToggles}
              questions={questions}
              answers={answers}
              feedback={feedback}
              ops={ops}
              pageDims={ir?.pages}
              onConvert={convert}
              onAnnotate={annotate}
              onQuestion={openQuestion}
              onClearNote={clearNote}
              onEmptyTrash={emptyNoteTrash}
              onRemoveOp={(o) => applyOp({ ...o, remove: true })}
              highlightNid={popover?.target?.nid ?? null}
              deepLinkNid={selected === DEEPLINK.doc ? deepLinkNid : null}
              onConsumeDeepLink={() => setDeepLinkNid(null)}
            />
          ) : (
            <p className="hint">Select a document on the left.</p>
          )}
        </div>
      </div>
      {popover && (
        <FeedbackPopover
          popover={popover}
          slug={selected}
          onSubmit={submitPopover}
          onDelete={deletePopover}
          onClose={() => setPopover(null)}
          onApplyOp={applyOp}
          nodeInfo={popover.target?.nid ? findNode(ir, popover.target.nid) : null}
        />
      )}
      <ErrorBanner />
    </div>
  );
}
