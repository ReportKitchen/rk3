import React, { useEffect, useMemo, useState } from "react";
import { getPatternsIndex, postPatternAnalyze, postPatternsAnalyzeAll } from "../api.js";
import { reportError } from "../errorBus.js";

/** Admin page: the pattern-identification track's results across the corpus —
 *  one column per analyzed doc, one row per pattern type, counts in cells.
 *  Clicking a doc opens it (its Patterns tab has the per-candidate review). */
export default function PatternsAggregate({ onOpen }) {
  const [rows, setRows] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = () => {
    getPatternsIndex().then(setRows)
      .catch((e) => { reportError("load pattern index", e); setRows([]); });
  };

  useEffect(() => { load(); }, []);

  const hasActive = (rows || []).some((r) => r.pattern_status === "in_progress");
  useEffect(() => {
    if (!hasActive) return undefined;
    const id = setInterval(load, 2500);
    return () => clearInterval(id);
  }, [hasActive]);

  const types = useMemo(() => {
    const totals = new Map();
    for (const r of rows || []) {
      for (const [t, n] of Object.entries(r.inventory || {})) {
        totals.set(t, (totals.get(t) || 0) + n);
      }
    }
    return [...totals.entries()].sort((a, b) => b[1] - a[1]);
  }, [rows]);

  const analyzeOne = (slug) => {
    setBusy(true);
    postPatternAnalyze(slug)
      .then(load)
      .catch((e) => reportError("analyze patterns", e))
      .finally(() => setBusy(false));
  };

  const analyzeAll = () => {
    setBusy(true);
    postPatternsAnalyzeAll()
      .then(load)
      .catch((e) => reportError("analyze all patterns", e))
      .finally(() => setBusy(false));
  };

  if (rows === null) return <div className="pane hint">Loading pattern reports…</div>;
  if (rows.length === 0) {
    return (
      <div className="pane">
        <p>No pattern reports yet.</p>
        <p className="hint">The pattern track writes them to patterns/out/&lt;slug&gt;.json.</p>
      </div>
    );
  }

  return (
    <div className="pane pat-agg">
      <h1>Information patterns — corpus view</h1>
      <p className="hint">
        {rows.filter((r) => r.total > 0).length}/{rows.length} document{rows.length > 1 ? "s" : ""} analyzed ·{" "}
        {types.reduce((a, [, n]) => a + n, 0)} candidates. Click a document to
        review its candidates in place (Patterns tab).
      </p>
      <div className="pat-agg-actions">
        <button className="pat-mode" disabled={busy || hasActive}
                onClick={analyzeAll}>Analyze all</button>
        <span className="hint">
          skips {rows.filter((r) => r.batchExcluded).length} batch-excluded document{rows.filter((r) => r.batchExcluded).length === 1 ? "" : "s"}
          {hasActive ? " · analysis running" : ""}
        </span>
      </div>
      <table className="pat-matrix">
        <thead>
          <tr>
            <th>pattern type</th>
            <th className="num">total</th>
            {rows.map((r) => (
              <th key={r.slug} className="doc-col">
                <a href="#" onClick={(e) => { e.preventDefault(); onOpen(r.slug); }}
                   title={`open ${r.slug}`}>
                  {r.slug.replace(/^0\d--/, "").slice(0, 18)}
                </a>
                <div className="hint">
                  {r.pattern_status === "missing" ? "not analyzed" : `${r.decided}/${r.total} reviewed`}
                  {r.warnings > 0 && ` · ${r.warnings}⚠`}
                  {r.batchExcluded && " · batch excluded"}
                  {r.pattern_status === "in_progress" && " · running"}
                </div>
                <button className="pat-mini-btn" disabled={busy || r.pattern_status === "in_progress"}
                        onClick={() => analyzeOne(r.slug)}>
                  {r.pattern_status === "in_progress" ? "Analyzing…" : "Analyze"}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {types.map(([t, total]) => (
            <tr key={t}>
              <td>{t}</td>
              <td className="num"><strong>{total}</strong></td>
              {rows.map((r) => (
                <td key={r.slug} className="num">{r.inventory?.[t] || ""}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
