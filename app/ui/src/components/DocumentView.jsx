import React, { Suspense, lazy, useEffect, useRef, useState } from "react";
import { Group, Panel, Separator, useDefaultLayout } from "react-resizable-panels";
import { docUrl, pageUrl } from "../api.js";
import { setupSync } from "../syncScroll.js";
import DocToolbar from "./DocToolbar.jsx";
import QuestionsPanel from "./QuestionsPanel.jsx";

// Puck is heavy (~90kB gzip); load the Landing Page Maker only when its tab opens
const LandingMaker = lazy(() => import("../landing/LandingMaker.jsx"));

// content-area views; "convert" is the full document view (html + pdf), the
// rest are alternate representations of the same content
const TABS = [
  { id: "convert", label: "Convert Document" },
  { id: "landing", label: "Landing Page" },
];

const MARKER_CSS = `
.rk-qmark {
  display: inline-flex; align-items: center; justify-content: center;
  width: 1.1rem; height: 1.1rem; margin-right: 0.4rem;
  border-radius: 50%; border: 1px solid #b58900; background: #fdf3d7;
  color: #8a6d00; font: 700 0.75rem/1 sans-serif; cursor: pointer;
  vertical-align: text-top;
}
.rk-qmark.rk-resolved { border-color: #2e7d32; background: #e6f2e6; color: #2e7d32; }
.rk-feedback-mode, .rk-feedback-mode * { cursor: crosshair !important; }
.rk-flash { outline: 2px solid #d99a06; transition: outline 0.8s; }
.rk-active {
  outline: 2px dashed #b58900 !important;
  outline-offset: 4px;
  background: rgba(253, 243, 215, 0.35);
}
.rk-fbmark {
  display: inline-flex; align-items: center; justify-content: center;
  width: 1.1rem; height: 1.1rem; margin-right: 0.4rem;
  border-radius: 3px; border: 1px solid #5b7fb5; background: #e2ecf8;
  color: #2c4a75; font: 700 0.7rem/1 sans-serif; cursor: help;
  vertical-align: text-top;
}
.rk-fbmark.rk-resolved { border-color: #999; background: #eee; color: #777; }
`;

export default function DocumentView({
  doc, toggles, setToggles, questions, answers, feedback, ops, pageDims, onConvert, onAnnotate,
  onQuestion, onClearNote, onEmptyTrash, onRemoveOp, highlightNid,
  docVersion = 0, flashNid = null,
}) {
  const iframeRef = useRef(null);
  const pdfPaneRef = useRef(null);
  const [frameLoaded, setFrameLoaded] = useState(false);
  const [tab, setTab] = useState("convert");
  // jump-to-node requests from the questions panel (now rendered inside this view)
  const [scrollToNid, setScrollToNid] = useState(null);
  // persists the content|pdf divider position to localStorage
  const splitLayout = useDefaultLayout({ id: "rk3-content-split", panelIds: ["content", "pdf"] });
  const savedScroll = useRef(null);
  const prevVersion = useRef(docVersion);

  // an applied edit reloads only the iframe (?v= cache-buster); capture the
  // reading position first so the user stays exactly where they were
  if (docVersion !== prevVersion.current) {
    prevVersion.current = docVersion;
    const win = iframeRef.current?.contentWindow;
    savedScroll.current = { y: win ? win.scrollY : 0 };
    setFrameLoaded(false);  // render-phase reset: effects rebind on new load
  }

  useEffect(() => {
    if (!frameLoaded || !savedScroll.current) return;
    const win = iframeRef.current?.contentWindow;
    const idoc = iframeRef.current?.contentDocument;
    if (win) win.scrollTo(0, savedScroll.current.y);
    savedScroll.current = null;
    if (flashNid && idoc) {
      const el = idoc.querySelector(`[data-nid="${flashNid}"]`);
      if (el) {
        el.classList.add("rk-flash");
        setTimeout(() => el.classList.remove("rk-flash"), 1500);
      }
    }
  }, [frameLoaded, flashNid]);

  // refs so iframe-side handlers never see stale state
  const stateRef = useRef({});
  stateRef.current = { toggles, questions, answers, feedback, onAnnotate, onQuestion };

  // an element's existing open note, so a second click edits instead of duplicating
  const findExisting = (nid, rk) =>
    (stateRef.current.feedback ?? []).find(
      (f) => f.type === "comment" && f.status === "open"
        && ((f.nid && f.nid === nid) || (!f.nid && f.rk && f.rk === rk)));

  const failed = doc.status === "failed";

  // layer-3 CSS toggle
  useEffect(() => {
    const link = iframeRef.current?.contentDocument?.getElementById("css-original");
    if (link) link.disabled = !toggles.layer3;
  }, [toggles.layer3, frameLoaded]);

  // sync scroll
  useEffect(() => {
    if (!frameLoaded || !pdfPaneRef.current) return;
    const win = iframeRef.current.contentWindow;
    const idoc = iframeRef.current.contentDocument;
    if (!win || !idoc) return;
    return setupSync(win, idoc, pdfPaneRef.current,
      () => stateRef.current.toggles.sync && stateRef.current.toggles.showPdf);
  }, [frameLoaded, toggles.showPdf]);

  // feedback-mode click capture + cursor inside the iframe
  useEffect(() => {
    if (!frameLoaded) return;
    const idoc = iframeRef.current.contentDocument;
    if (!idoc) return;
    const onClick = (e) => {
      const s = stateRef.current;
      if (!s.toggles.feedbackMode) return;
      if (e.target.closest(".rk-qmark")) return; // markers handle themselves
      e.preventDefault();
      e.stopPropagation();
      let el = e.target.closest("[data-nid],[data-rk]");
      if (!el) {
        // click landed in the whitespace between elements: snap to the
        // vertically nearest anchored element (within 80px)
        let best = null, dist = 80;
        for (const cand of idoc.querySelectorAll("[data-nid]")) {
          const r = cand.getBoundingClientRect();
          const d = e.clientY < r.top ? r.top - e.clientY
                  : e.clientY > r.bottom ? e.clientY - r.bottom : 0;
          if (d < dist) { best = cand; dist = d; }
        }
        el = best;
      }
      const rect = iframeRef.current.getBoundingClientRect();
      const target = el
        ? { nid: el.dataset.nid, rk: el.dataset.rk, page: +el.dataset.page || null }
        : { page: null };
      // drag-selected text narrows the note to a span within the element;
      // offsets are relative to the node's text (viewer markers excluded)
      const sel = idoc.getSelection();
      if (el && sel && !sel.isCollapsed && el.contains(sel.anchorNode)) {
        const range = sel.getRangeAt(0);
        const pre = idoc.createRange();
        pre.selectNodeContents(el);
        pre.setEnd(range.startContainer, range.startOffset);
        let start = pre.toString().length;
        for (const m of el.querySelectorAll(".rk-qmark,.rk-fbmark")) {
          if (pre.intersectsNode(m)) start -= m.textContent.length;
        }
        const text = sel.toString();
        target.selText = text.slice(0, 300);
        target.selStart = Math.max(0, start);
        target.selEnd = Math.max(0, start) + text.length;
      }
      s.onAnnotate(
        target,
        { x: rect.left + e.clientX, y: rect.top + e.clientY },
        el ? findExisting(el.dataset.nid, el.dataset.rk) : null,
      );
    };
    idoc.addEventListener("click", onClick, true);
    return () => idoc.removeEventListener("click", onClick, true);
  }, [frameLoaded]);

  useEffect(() => {
    const idoc = iframeRef.current?.contentDocument;
    if (!idoc?.body) return;
    idoc.body.classList.toggle("rk-feedback-mode", toggles.feedbackMode);
  }, [toggles.feedbackMode, frameLoaded]);

  // question markers, re-injected when questions/answers change
  useEffect(() => {
    if (!frameLoaded) return;
    const idoc = iframeRef.current.contentDocument;
    if (!idoc?.body) return;
    if (!idoc.getElementById("rk-viewer-style")) {
      const style = idoc.createElement("style");
      style.id = "rk-viewer-style";
      style.textContent = MARKER_CSS;
      idoc.head.appendChild(style);
    }
    idoc.querySelectorAll(".rk-qmark").forEach((m) => m.remove());
    for (const q of questions) {
      const el = idoc.querySelector(`[data-nid="${q.nid}"]`);
      if (!el) continue;
      const btn = idoc.createElement("button");
      btn.className = "rk-qmark" + (answers.has(q.qid) ? " rk-resolved" : "");
      btn.textContent = answers.has(q.qid) ? "✓" : "?";
      btn.title = q.prompt;
      btn.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        const rect = iframeRef.current.getBoundingClientRect();
        const r = btn.getBoundingClientRect();
        stateRef.current.onQuestion(q, { x: rect.left + r.left, y: rect.top + r.bottom + 4 });
      };
      el.prepend(btn);
    }
  }, [frameLoaded, questions, answers]);

  // markers where feedback was already left, so spots aren't annotated twice
  useEffect(() => {
    if (!frameLoaded) return;
    const idoc = iframeRef.current.contentDocument;
    if (!idoc?.body) return;
    idoc.querySelectorAll(".rk-fbmark").forEach((m) => m.remove());
    for (const f of feedback ?? []) {
      if (f.type !== "comment" || f.status === "cleared") continue;
      const target = (f.nid && idoc.querySelector(`[data-nid="${f.nid}"]`))
        || (f.rk && idoc.querySelector(`[data-rk="${f.rk}"]`));
      if (!target) continue;
      const mark = idoc.createElement("span");
      mark.className = "rk-fbmark" + (f.status === "resolved" ? " rk-resolved" : "");
      mark.textContent = f.status === "resolved" ? "✓" : "✎";
      mark.title = (f.status === "resolved" ? "Resolved: " : "Your note (click to edit): ") + f.text;
      if (f.status !== "resolved") {
        mark.style.cursor = "pointer";
        mark.onclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          const rect = iframeRef.current.getBoundingClientRect();
          const r = mark.getBoundingClientRect();
          stateRef.current.onAnnotate(
            { nid: f.nid, rk: f.rk, page: f.page },
            { x: rect.left + r.left, y: rect.top + r.bottom + 4 }, f);
        };
      }
      target.prepend(mark);
    }
  }, [frameLoaded, feedback]);

  // outline the element a question/feedback popover refers to, so its extent
  // is unambiguous (e.g. a full-page callout)
  useEffect(() => {
    if (!frameLoaded || !highlightNid) return;
    const el = iframeRef.current.contentDocument
      ?.querySelector(`[data-nid="${highlightNid}"]`);
    if (!el) return;
    el.classList.add("rk-active");
    return () => el.classList.remove("rk-active");
  }, [frameLoaded, highlightNid]);

  // jump-to-node requests from the questions panel
  useEffect(() => {
    if (!scrollToNid || !frameLoaded) return;
    const idoc = iframeRef.current.contentDocument;
    const el = idoc?.querySelector(`[data-nid="${scrollToNid}"]`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("rk-flash");
      setTimeout(() => el.classList.remove("rk-flash"), 1200);
    }
    setScrollToNid(null);
  }, [scrollToNid, frameLoaded]);

  const onPdfClick = (e) => {
    if (!stateRef.current.toggles.feedbackMode) return;
    const img = e.target.closest("img[data-page]");
    if (!img) return;
    const r = img.getBoundingClientRect();
    onAnnotate(
      { page: +img.dataset.page,
        xf: +((e.clientX - r.left) / r.width).toFixed(4),
        yf: +((e.clientY - r.top) / r.height).toFixed(4) },
      { x: e.clientX, y: e.clientY },
    );
  };

  const pdfPane = doc.pages > 0 && toggles.showPdf && (
    <div
      className={"pdfpane" + (doc.status !== "done" ? " solo" : "")}
      ref={pdfPaneRef}
      onClick={onPdfClick}
      style={toggles.feedbackMode ? { cursor: "crosshair" } : undefined}
    >
      {Array.from({ length: doc.pages }, (_, i) => {
        const spots = (feedback ?? []).filter(
          (f) => f.type === "comment" && f.status !== "cleared"
            && f.xf != null && f.page === i + 1);
        const dims = pageDims?.[String(i + 1)];
        return (
          <div key={i + 1} className="pagewrap">
            <img
              src={pageUrl(doc.slug, i + 1)}
              data-page={i + 1}
              alt={`page ${i + 1}`}
              // true page proportions before the PNG loads, so sync-scroll
              // anchors are correct from the first frame
              style={dims ? { aspectRatio: `${dims[0]} / ${dims[1]}` } : undefined}
            />
            {spots.map((f, k) => (
              <span
                key={k}
                className={"fb-spot" + (f.status === "resolved" ? " resolved" : "")}
                style={{ left: `${f.xf * 100}%`, top: `${f.yf * 100}%` }}
                title={(f.status === "resolved" ? "Resolved: " : "Your note (click to edit): ") + f.text}
                onClick={f.status === "resolved" ? undefined : (e) => {
                  e.stopPropagation();
                  onAnnotate({ page: f.page, xf: f.xf, yf: f.yf },
                             { x: e.clientX, y: e.clientY }, f);
                }}
              >
                {f.status === "resolved" ? "✓" : "✎"}
              </span>
            ))}
          </div>
        );
      })}
    </div>
  );

  if (doc.status === "done") {
    return (
      <div className="docview">
        <div className="tabs" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              className={"tab" + (tab === t.id ? " active" : "")}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Convert Document: kept mounted (display-toggled) so the iframe's
            scroll position, markers and sync survive tab switches */}
        <div className="convert-tab" style={{ display: tab === "convert" ? "flex" : "none" }}>
          <DocToolbar
            doc={doc}
            toggles={toggles}
            setToggles={setToggles}
            questionCount={questions.length}
            answeredCount={questions.filter((q) => answers.has(q.qid)).length}
          />
          <div className="convert-body">
            <Group
              orientation="horizontal"
              className="split"
              style={{ flex: 1, minWidth: 0, minHeight: 0, height: "auto" }}
              defaultLayout={splitLayout.defaultLayout}
              onLayoutChanged={splitLayout.onLayoutChanged}
            >
              <Panel id="content" minSize="20%" className="content-panel">
                <iframe
                  title={doc.name}
                  ref={iframeRef}
                  src={docUrl(doc.slug) + (docVersion ? `?v=${docVersion}` : "")}
                  onLoad={() => setFrameLoaded(true)}
                />
              </Panel>
              {pdfPane && <Separator className="resizer" />}
              {pdfPane && (
                <Panel id="pdf" defaultSize="50%" minSize="20%" className="pdf-panel">
                  {pdfPane}
                </Panel>
              )}
            </Group>
            {toggles.panelOpen && (
              <QuestionsPanel
                questions={questions}
                answers={answers}
                feedback={feedback}
                ops={ops}
                onJump={(nid) => setScrollToNid(nid)}
                onAnswer={(q) => onQuestion(q, { x: window.innerWidth / 2, y: 160 })}
                onClear={onClearNote}
                onEmptyTrash={onEmptyTrash}
                onRemoveOp={onRemoveOp}
              />
            )}
          </div>
        </div>

        {tab === "landing" && (
          <Suspense fallback={<div className="hint" style={{ padding: "2rem" }}>Loading editor…</div>}>
            <LandingMaker doc={doc} />
          </Suspense>
        )}
      </div>
    );
  }

  if (doc.status === "in_progress") {
    return (
      <div className="pane">
        <p>Conversion in progress…</p>
        <p className="hint">No live progress in v1 — use Refresh to check.</p>
      </div>
    );
  }

  return (
    <div className="failpane">
      <div className="pane">
        {failed && (
          <>
            <p><strong>Conversion failed.</strong></p>
            <pre className="error">{doc.error || "unknown error"}</pre>
          </>
        )}
        <button className="action" onClick={() => onConvert(doc.slug, failed)}>
          {failed ? "Retry conversion" : "Convert"}
        </button>
      </div>
      {pdfPane}
    </div>
  );
}
