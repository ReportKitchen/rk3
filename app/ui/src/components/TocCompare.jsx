import React, { useEffect, useState } from "react";
import { getTocCompare } from "../api.js";
import { reportError } from "../errorBus.js";

const STATUS = {
  match: { label: "match", cls: "ok" },
  "level?": { label: "level?", cls: "warn" },
  missed: { label: "missed", cls: "bad" },
  extra: { label: "", cls: "extra" },
};

// indent a title by its nesting level — whitespace only, no markers
const indent = (level) => ({ paddingLeft: `${Math.max(0, (level || 1) - 1) * 0.9}rem` });

// read-only side-by-side: the headings we detected (left, mirroring how Convert
// Document puts our output on the left) vs the author's TOC (right), with
// per-row reconciliation notes. Diagnostic only — nothing here writes.
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

  const { summary, rows } = data;

  return (
    <div className="toccmp">
      <div className="toccmp-summary">
        {summary.hasToc ? (
          <>
            <span className="toccmp-stat"><strong>{summary.tocEntries}</strong> TOC entries</span>
            <span className="toccmp-stat ok"><strong>{summary.matched}</strong> match</span>
            {summary.levelFlags > 0 && <span className="toccmp-stat warn"><strong>{summary.levelFlags}</strong> level?</span>}
            {summary.missed > 0 && <span className="toccmp-stat bad"><strong>{summary.missed}</strong> missed</span>}
            <span className="toccmp-stat"><strong>{summary.headings}</strong> headings detected</span>
            <span className="toccmp-stat muted">{summary.extra} below TOC depth</span>
          </>
        ) : (
          <span className="toccmp-stat">No table of contents detected · <strong>{summary.headings}</strong> headings detected</span>
        )}
      </div>

      <table className="toccmp-table">
        <thead>
          <tr>
            <th className="toccmp-side">Our headings</th>
            <th className="toccmp-note">note</th>
            <th className="toccmp-side">Their TOC</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const s = STATUS[r.status] || STATUS.match;
            const h = r.heading;
            const t = r.toc;
            return (
              <tr key={i} className={"toccmp-row " + s.cls}>
                <td className="toccmp-side">
                  {h ? (
                    <span className="toccmp-title" style={indent(h.level)}>
                      <span className="toccmp-lvl">h{h.level}</span>{h.text}
                      {h.page != null && <span className="toccmp-pg">p{h.page}</span>}
                    </span>
                  ) : <span className="toccmp-empty">— not detected —</span>}
                </td>
                <td className="toccmp-note">
                  {s.label && <span className={"toccmp-badge " + s.cls}>{s.label}</span>}
                  {r.status === "level?" && <span className="toccmp-exp">h{h.level}→h{r.expected}</span>}
                </td>
                <td className="toccmp-side">
                  {t ? (
                    <span className="toccmp-title" style={indent(t.level)}>
                      {t.title}
                      {t.page != null && <span className="toccmp-pg">p{t.page}</span>}
                    </span>
                  ) : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
