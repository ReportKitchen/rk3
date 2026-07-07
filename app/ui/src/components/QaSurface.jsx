import React, { useEffect, useRef, useState } from "react";
import { Group, Panel, Separator, useDefaultLayout } from "react-resizable-panels";
import { docUrl, pageUrl, getScoreboard, getStakes, getFeedback } from "../api.js";

// The owner's QA surface (webified §1.5): a page gallery with honest status
// rings, an original-vs-render compare view, and per-page stakes + vision issues
// in plain words. The owner judges PAGES, not checks — this is that visual layer.

const CMP_CSS = `.rk-qa-flash { outline: 3px solid #0a7d6b !important; outline-offset: 2px; }`;

// status ring per page (§1.5a). Precedence honours the honesty rule: a red stake
// or high/critical issue is RED; a medium issue AMBER; an un-scanned clean page
// is GREY (never a fake green); only a scanned, clean, no-red-stake page is GREEN.
function ringOf(p) {
  if (!p) return "grey";
  const vi = p.visionIssues || {};
  if ((p.stakes?.red || 0) > 0 || (vi.critical || 0) > 0 || (vi.high || 0) > 0) return "red";
  if ((vi.medium || 0) > 0) return "amber";
  if (!p.scanned) return "grey";
  return "green";
}
const RING_LABEL = {
  green: "looks right (scanned, no issues, stakes hold)",
  amber: "medium issues found",
  red: "high/critical issue or a broken stake",
  grey: "not vision-scanned yet — status unknown",
};

function Glossary() {
  return (
    <dl className="qa-gloss">
      <div><dt>stake</dt><dd>a frozen assertion from an owner note — <b>green</b> = still holds, <b>red</b> = broke.</dd></div>
      <div><dt>census</dt><dd>every stake across every document, counted (the internal "did we re-break anything" gate).</dd></div>
      <div><dt>vision issue</dt><dd>a difference the model spotted between our render and the original page.</dd></div>
      <div><dt>page looks right</dt><dd>no medium-or-worse vision issues on the page and its stakes are green.</dd></div>
    </dl>
  );
}

export default function QaSurface({ doc }) {
  const [board, setBoard] = useState(null);
  const [stakes, setStakes] = useState([]);
  const [feedback, setFeedback] = useState([]);
  const [err, setErr] = useState(null);
  const [sel, setSel] = useState(null);        // page number in compare view, or null = gallery
  const [showGloss, setShowGloss] = useState(false);
  const [frameLoaded, setFrameLoaded] = useState(false);
  const iframeRef = useRef(null);
  const layout = useDefaultLayout({ id: "rk3-qa-split", panelIds: ["qaimg", "qadoc"] });

  useEffect(() => {
    setBoard(null); setErr(null); setSel(null);
    getScoreboard(doc.slug).then(setBoard).catch(setErr);
    getStakes(doc.slug).then((d) => setStakes(d.checks || [])).catch(() => setStakes([]));
    getFeedback(doc.slug).then((f) => setFeedback(Array.isArray(f) ? f : (f?.entries || [])))
      .catch(() => setFeedback([]));
  }, [doc.slug]);

  // in compare view, scroll the render to this page's first element on load
  useEffect(() => {
    if (sel == null || !frameLoaded) return;
    const idoc = iframeRef.current?.contentDocument;
    if (!idoc) return;
    if (!idoc.getElementById("rk-qa-css")) {
      const st = idoc.createElement("style");
      st.id = "rk-qa-css"; st.textContent = CMP_CSS;
      idoc.head.appendChild(st);
    }
    const el = idoc.querySelector(`[data-page="${sel}"]`);
    if (el) el.scrollIntoView({ block: "start" });
  }, [sel, frameLoaded]);

  const jump = (nid) => {
    const idoc = iframeRef.current?.contentDocument;
    const el = nid && idoc?.querySelector(`[data-nid="${nid}"]`);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.classList.add("rk-qa-flash");
    setTimeout(() => el.classList.remove("rk-qa-flash"), 1200);
  };

  if (err) {
    return (
      <div className="pane">
        <p>Couldn't load the page gallery.</p>
        <p className="hint">{err.detail || String(err)} — the doc may need converting, or run <code>python tools/scoreboard.py {doc.slug}</code>.</p>
      </div>
    );
  }
  if (!board) return <div className="pane hint">Loading pages…</div>;
  const pages = (board.pages || []).filter((p) => p.page != null);

  // ---- gallery ----
  if (sel == null) {
    const counts = { green: 0, amber: 0, red: 0, grey: 0 };
    pages.forEach((p) => { counts[ringOf(p)]++; });
    return (
      <div className="qa-pane">
        <div className="qa-header">
          <span className="qa-legend">
            <span className="qa-dot ring-green" /> {counts.green} look right ·{" "}
            <span className="qa-dot ring-amber" /> {counts.amber} medium ·{" "}
            <span className="qa-dot ring-red" /> {counts.red} broken ·{" "}
            <span className="qa-dot ring-grey" /> {counts.grey} not scanned
          </span>
          <button className="qa-gloss-btn" onClick={() => setShowGloss((s) => !s)}>
            {showGloss ? "hide" : "what do these mean?"}
          </button>
        </div>
        {showGloss && <Glossary />}
        <div className="qa-gallery">
          {pages.map((p) => {
            const st = ringOf(p);
            return (
              <button key={p.page} className="qa-card" onClick={() => setSel(p.page)}
                      title={`p${p.page} — ${RING_LABEL[st]}`}>
                <span className="qa-thumb">
                  <img src={pageUrl(doc.slug, p.page)} loading="lazy" alt={`page ${p.page}`} />
                  <span className={"qa-ring ring-" + st} />
                </span>
                <span className="qa-pnum">p{p.page}</span>
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  // ---- compare view ----
  const rec = pages.find((p) => p.page === sel);
  const st = ringOf(rec);
  const pageStakes = stakes.filter((c) => c.page === sel);
  const pageIssues = feedback.filter((e) =>
    e.page === sel && e.source === "vision-qa"
    && (e.disposition || "open") === "open" && e.status !== "cleared");
  return (
    <div className="qa-pane">
      <div className="qa-header">
        <button className="qa-back" onClick={() => setSel(null)}>← all pages</button>
        <span className="qa-title">
          <span className={"qa-dot ring-" + st} /> Page {sel} — {RING_LABEL[st]}
        </span>
      </div>
      <Group orientation="horizontal" className="split qa-compare" {...layout.groupProps}>
        <Panel id="qaimg" defaultSize="50%" minSize="25%" className="qa-orig-panel">
          <div className="qa-orig"><img src={pageUrl(doc.slug, sel)} alt={`original page ${sel}`} /></div>
        </Panel>
        <Separator className="resizer" />
        <Panel id="qadoc" defaultSize="50%" minSize="25%" className="qa-doc-panel">
          <iframe ref={iframeRef} title="our render" src={docUrl(doc.slug)}
                  onLoad={() => setFrameLoaded(true)} />
        </Panel>
      </Group>
      <div className="qa-findings">
        <div className="qa-find-col">
          <h4>Stakes on this page</h4>
          {pageStakes.length === 0 && <p className="hint">none anchored to p{sel}</p>}
          <ul className="qa-find-list">
            {pageStakes.map((c) => (
              <li key={c.i} className={c.ok ? "ok" : "bad"}>
                <button className="jump" disabled={!c.nid} title={c.nid ? "show it" : "no element"}
                        onClick={() => jump(c.nid)}>→</button>
                <span className={"stk-chip " + (c.ok ? "pass" : "fail")}>{c.ok ? "PASS" : "FAIL"}</span>
                <span className="qa-find-note">{c.note || c.detail || c.kind}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="qa-find-col">
          <h4>Vision issues on this page</h4>
          {pageIssues.length === 0 && (
            <p className="hint">{rec?.scanned ? "none — scanned clean" : "not vision-scanned yet"}</p>
          )}
          <ul className="qa-find-list">
            {pageIssues.map((e, k) => (
              <li key={e.id || k} className={"sev-" + (e.severity || "low")}>
                <span className={"qa-sev sev-" + (e.severity || "low")}>{e.severity || "low"}</span>
                <span className="qa-find-note">
                  {e.text || e.elementText || "(issue)"}
                  {e.category ? <em> · {e.category}</em> : null}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
