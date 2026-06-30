import React, { useEffect, useState } from "react";
import { getTocCompare } from "../api.js";
import { reportError } from "../errorBus.js";

const STATUS = {
  match: { label: "match", cls: "ok" },
  "level?": { label: "level?", cls: "warn" },
  missed: { label: "missed", cls: "bad" },
};

// read-only side-by-side: the author's TOC (left) vs the headings we detected
// (right), with reconciliation notes. Diagnostic only — nothing here writes.
export default function TocCompare({ slug }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    setData(null);
    setErr(false);
    getTocCompare(slug)
      .then(setData)
      .catch((e) => { reportError("load TOC comparison", e); setErr(true); });
  }, [slug]);

  if (err) return <div className="hint" style={{ padding: "2rem" }}>Couldn’t load the comparison.</div>;
  if (!data) return <div className="hint" style={{ padding: "2rem" }}>Comparing…</div>;

  const { summary, rows, extras } = data;

  if (!summary.hasToc) {
    return (
      <div className="toccmp">
        <p className="hint" style={{ padding: "1rem 1.25rem" }}>
          No table of contents detected for this document. We found{" "}
          <strong>{summary.headings}</strong> headings — see them under the extras list below.
        </p>
        <ExtraList extras={extras} />
      </div>
    );
  }

  return (
    <div className="toccmp">
      <div className="toccmp-summary">
        <span className="toccmp-stat"><strong>{summary.tocEntries}</strong> TOC entries</span>
        <span className="toccmp-stat ok"><strong>{summary.matched}</strong> match</span>
        {summary.levelFlags > 0 && <span className="toccmp-stat warn"><strong>{summary.levelFlags}</strong> level?</span>}
        {summary.missed > 0 && <span className="toccmp-stat bad"><strong>{summary.missed}</strong> missed</span>}
        <span className="toccmp-stat"><strong>{summary.headings}</strong> headings detected</span>
        <span className="toccmp-stat muted">{summary.extra} below TOC depth</span>
      </div>

      <table className="toccmp-table">
        <thead>
          <tr>
            <th className="toccmp-side">Their TOC</th>
            <th className="toccmp-note">note</th>
            <th className="toccmp-side">Our heading</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const s = STATUS[r.status] || STATUS.match;
            const t = r.toc;
            const h = r.heading;
            return (
              <tr key={i} className={"toccmp-row " + s.cls}>
                <td className="toccmp-side">
                  <span className="toccmp-lvl">{t.level ? "L" + t.level : "—"}</span>
                  <span className="toccmp-title" style={{ paddingLeft: `${((t.level || 1) - 1) * 1.1}rem` }}>
                    {t.title}
                  </span>
                  {t.page != null && <span className="toccmp-pg">p{t.page}</span>}
                </td>
                <td className="toccmp-note">
                  <span className={"toccmp-badge " + s.cls}>{s.label}</span>
                  {r.status === "level?" && (
                    <span className="toccmp-exp">h{h.level} → h{r.expected}</span>
                  )}
                </td>
                <td className="toccmp-side">
                  {h ? (
                    <>
                      <span className="toccmp-lvl">h{h.level}</span>
                      <span className="toccmp-title">{h.text}</span>
                      {h.page != null && <span className="toccmp-pg">p{h.page}</span>}
                    </>
                  ) : (
                    <span className="toccmp-empty">— not detected —</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <ExtraList extras={extras} />
    </div>
  );
}

function ExtraList({ extras }) {
  if (!extras?.length) return null;
  return (
    <details className="toccmp-extras">
      <summary>{extras.length} headings not in the TOC <span className="muted">(usually legitimately below TOC depth)</span></summary>
      <ul>
        {extras.map((h, i) => (
          <li key={i}>
            <span className="toccmp-lvl">h{h.level}</span>
            <span className="toccmp-title">{h.text}</span>
            {h.page != null && <span className="toccmp-pg">p{h.page}</span>}
          </li>
        ))}
      </ul>
    </details>
  );
}
