import React, { useEffect, useMemo, useRef, useState } from "react";
import { Group, Panel, Separator, useDefaultLayout } from "react-resizable-panels";
import { docUrl, getStakes } from "../api.js";

// injected into the doc iframe: outline anchored stakes green (pass) / red
// (fail), plus the shared flash on jump. Distinct from the amber edit trail
// and purple pattern outline.
const STK_CSS = `
.rk-stk-pass { outline: 2px solid rgba(46,125,50,0.5); outline-offset: 2px; }
.rk-stk-fail { outline: 2px solid rgba(198,40,40,0.65); outline-offset: 2px; }
.rk-stk-flash { outline: 3px solid #0a7d6b !important; }
`;

// The Stakes tab (webified §1.3): the doc's gold checks with live red/green,
// note text, and a jump to the matched element. Reads GET /api/stakes/<slug>,
// which wraps the same checks_with_status `python -m rk3 eval` uses, so the
// board and the CLI agree exactly.
export default function StakesPanel({ doc }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [hidePass, setHidePass] = useState(false);
  const iframeRef = useRef(null);
  const [frameLoaded, setFrameLoaded] = useState(false);
  const layout = useDefaultLayout({ id: "rk3-stakes-split", panelIds: ["slist", "sdoc"] });

  const load = () => getStakes(doc.slug).then(setData).catch(setErr);
  useEffect(() => { setData(null); setErr(null); load(); }, [doc.slug]);

  const checks = data?.checks || [];
  const shown = useMemo(() => {
    const list = hidePass ? checks.filter((c) => !c.ok) : checks;
    // failing first, then by page — the reds are what the owner wants to see
    return [...list].sort((a, b) =>
      (a.ok === b.ok ? 0 : a.ok ? 1 : -1) || ((a.page ?? 9999) - (b.page ?? 9999)));
  }, [checks, hidePass]);

  // outline every anchored stake in the doc, colored by pass/fail
  useEffect(() => {
    const idoc = iframeRef.current?.contentDocument;
    if (!frameLoaded || !idoc) return;
    if (!idoc.getElementById("rk-stk-css")) {
      const st = idoc.createElement("style");
      st.id = "rk-stk-css";
      st.textContent = STK_CSS;
      idoc.head.appendChild(st);
    }
    idoc.querySelectorAll(".rk-stk-pass,.rk-stk-fail")
      .forEach((el) => el.classList.remove("rk-stk-pass", "rk-stk-fail"));
    for (const c of shown) {
      const el = c.nid && idoc.querySelector(`[data-nid="${c.nid}"]`);
      if (el) el.classList.add(c.ok ? "rk-stk-pass" : "rk-stk-fail");
    }
  }, [frameLoaded, shown]);

  const jump = (c) => {
    const idoc = iframeRef.current?.contentDocument;
    const el = c.nid && idoc?.querySelector(`[data-nid="${c.nid}"]`);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.classList.add("rk-stk-flash");
    setTimeout(() => el.classList.remove("rk-stk-flash"), 1200);
  };

  if (err) {
    return (
      <div className="pane">
        <p>No gold stakes for this document.</p>
        <p className="hint">Checks live in eval/&lt;slug&gt;.yaml; mint them from the Convert tab's assert mode.</p>
      </div>
    );
  }
  if (!data) return <div className="pane hint">Loading stakes…</div>;

  return (
    <div className="patterns-pane">
      <div className="pat-header">
        <span>
          <strong className="stk-green">{data.green}</strong> passing ·{" "}
          <strong className="stk-red">{data.red}</strong> failing
        </span>
        <label className="pat-hide">
          <input type="checkbox" checked={hidePass}
                 onChange={(e) => setHidePass(e.target.checked)} />
          hide passing
        </label>
        <button className="stk-refresh" title="Re-evaluate against current artifacts"
                onClick={load}>↻</button>
      </div>
      <Group orientation="horizontal" className="split" {...layout.groupProps}>
        <Panel id="slist" defaultSize="45%" minSize="25%" className="pat-list-panel">
          <ul className="pat-list">
            {shown.map((c) => (
              <li key={c.i} className="pat-item stk-item">
                <div className="pat-row1">
                  <button className="jump" title={c.nid ? "Show in document" : "no anchor element"}
                          disabled={!c.nid} onClick={() => jump(c)}>→</button>
                  <span className={"stk-chip " + (c.ok ? "pass" : "fail")}>
                    {c.ok ? "PASS" : "FAIL"}
                  </span>
                  <span className="stk-note">{c.note || "(no note)"}</span>
                  <span className="pat-meta">
                    {c.kind}
                    {c.stage && c.stage !== "analyze" ? ` · ${c.stage}` : ""}
                    {c.page ? ` · p${c.page}` : ""}
                  </span>
                </div>
                {!c.ok && c.detail && <p className="stk-detail">{c.detail}</p>}
              </li>
            ))}
            {shown.length === 0 && <li className="hint">No stakes match the filter.</li>}
          </ul>
        </Panel>
        <Separator className="resizer" />
        <Panel id="sdoc" defaultSize="55%" minSize="30%" className="pat-doc-panel">
          <iframe ref={iframeRef} title="document" src={docUrl(doc.slug)}
                  onLoad={() => setFrameLoaded(true)} />
        </Panel>
      </Group>
    </div>
  );
}
