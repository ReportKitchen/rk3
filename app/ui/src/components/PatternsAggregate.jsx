import React, { useEffect, useMemo, useState } from "react";
import { getPatternsIndex } from "../api.js";
import { reportError } from "../errorBus.js";

/** Admin page: the pattern-identification track's results across the corpus —
 *  one column per analyzed doc, one row per pattern type, counts in cells.
 *  Clicking a doc opens it (its Patterns tab has the per-candidate review). */
export default function PatternsAggregate({ onOpen }) {
  const [rows, setRows] = useState(null);

  useEffect(() => {
    getPatternsIndex().then(setRows)
      .catch((e) => { reportError("load pattern index", e); setRows([]); });
  }, []);

  const types = useMemo(() => {
    const totals = new Map();
    for (const r of rows || []) {
      for (const [t, n] of Object.entries(r.inventory || {})) {
        totals.set(t, (totals.get(t) || 0) + n);
      }
    }
    return [...totals.entries()].sort((a, b) => b[1] - a[1]);
  }, [rows]);

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
        {rows.length} document{rows.length > 1 ? "s" : ""} analyzed ·{" "}
        {types.reduce((a, [, n]) => a + n, 0)} candidates. Click a document to
        review its candidates in place (Patterns tab).
      </p>
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
                  {r.decided}/{r.total} reviewed
                  {r.warnings > 0 && ` · ${r.warnings}⚠`}
                </div>
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
