import React, { useCallback, useEffect, useState } from "react";
import { getFeedback, runVisionQa, setDisposition } from "../api.js";
import { reportError } from "../errorBus.js";

// the triage dashboard: the vision-QA reviewer scans our render against the
// original page images and drops severity-ranked issues (and opportunities)
// here; the user dispositions each — Fix / Accept / Dismiss.
const SEV = { critical: 0, high: 1, medium: 2, low: 3 };
const ACTIONS = [["fixed", "Fix"], ["accepted", "Accept"], ["dismissed", "Dismiss"]];

function parsePages(s) {
  const out = new Set();
  for (const part of (s || "").split(",")) {
    const m = part.trim().match(/^(\d+)\s*-\s*(\d+)$/);
    if (m) { for (let i = +m[1]; i <= +m[2]; i++) out.add(i); }
    else if (/^\d+$/.test(part.trim())) out.add(+part.trim());
  }
  return [...out].sort((a, b) => a - b);
}

export default function ReviewBoard({ slug }) {
  const [issues, setIssues] = useState([]);
  const [pages, setPages] = useState("1-5");
  const [running, setRunning] = useState(false);
  const [showResolved, setShowResolved] = useState(false);

  const load = useCallback(() => {
    getFeedback(slug)
      .then((list) => setIssues(list.filter((e) => e.source === "vision-qa")))
      .catch((e) => reportError("load issues", e));
  }, [slug]);
  useEffect(() => { load(); }, [load]);

  const run = async () => {
    setRunning(true);
    try { await runVisionQa(slug, parsePages(pages)); load(); }
    catch (e) { reportError("run vision QA", e); }
    finally { setRunning(false); }
  };

  const dispose = async (id, d) => {
    setIssues((prev) => prev.map((i) => (i.id === id ? { ...i, disposition: d } : i)));
    try { await setDisposition(slug, id, d); }
    catch (e) { reportError("set disposition", e); load(); }
  };

  const dispo = (i) => i.disposition || "open";
  const count = (d) => issues.filter((i) => dispo(i) === d).length;
  const shown = issues
    .filter((i) => showResolved || dispo(i) === "open")
    .sort((a, b) => (SEV[a.severity] ?? 9) - (SEV[b.severity] ?? 9)
      || (a.page || 0) - (b.page || 0));

  return (
    <div className="review">
      <div className="review-bar">
        <button className="rv-run" onClick={run} disabled={running}>
          {running ? "Scanning…" : "▶ Run vision QA"}
        </button>
        <label className="rv-pages">pages&nbsp;
          <input value={pages} onChange={(e) => setPages(e.target.value)} />
        </label>
        <span className="rv-counts">
          <b>{count("open")}</b> open · <b className="ok">{count("fixed")}</b> fixed ·{" "}
          <b className="muted">{count("accepted")}</b> accepted ·{" "}
          <b className="muted">{count("dismissed")}</b> dismissed
        </span>
        <label className="rv-showres">
          <input type="checkbox" checked={showResolved}
            onChange={(e) => setShowResolved(e.target.checked)} /> show resolved
        </label>
      </div>

      {shown.length === 0 && (
        <p className="hint" style={{ padding: "1.5rem" }}>
          {running ? "Scanning the original pages against our render…"
            : "No open issues. Run vision QA to scan pages against the originals."}
        </p>
      )}

      <ul className="rv-list">
        {shown.map((i) => (
          <li key={i.id} className={"rv-item " + (i.severity || "")
            + (dispo(i) !== "open" ? " done" : "")}>
            <div className="rv-head">
              <span className={"rv-sev " + (i.severity || "")}>{i.severity}</span>
              <span className={"rv-kind " + (i.kind || "")}>{i.kind}</span>
              <span className="rv-cat">{i.category}</span>
              {i.page != null && <span className="rv-pg">p{i.page}</span>}
              {dispo(i) !== "open" && <span className="rv-dispo">{dispo(i)}</span>}
            </div>
            <div className="rv-issue">{i.text}</div>
            {i.fix && <div className="rv-fix">→ {i.fix}</div>}
            <div className="rv-actions">
              {ACTIONS.map(([d, label]) => (
                <button key={d} className={dispo(i) === d ? "active" : ""}
                  onClick={() => dispose(i.id, dispo(i) === d ? "open" : d)}>
                  {label}
                </button>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
