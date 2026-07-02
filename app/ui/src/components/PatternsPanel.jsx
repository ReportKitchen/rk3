import React, { useEffect, useMemo, useRef, useState } from "react";
import { Group, Panel, Separator, useDefaultLayout } from "react-resizable-panels";
import { docUrl, getPatternsDoc, postPatternDecision } from "../api.js";
import { reportError } from "../errorBus.js";

// injected into the doc iframe: pattern-hit overlay (purple, to stay distinct
// from the amber data-op edit trail) + the shared flash
const PAT_CSS = `
.rk-pat { outline: 2px solid rgba(124, 58, 237, 0.55); outline-offset: 2px; }
.rk-pat-flash { outline: 3px solid #7c3aed !important; }
`;

const DECISIONS = [
  ["accept", "✓"],
  ["reject", "✗"],
];
const MORE_DECISIONS = [
  "accept_with_edits", "wrong_type", "missing_fields",
  "needs_more_context", "useful_suggestion_not_supported",
];

export default function PatternsPanel({ doc }) {
  const [report, setReport] = useState(null);
  const [err, setErr] = useState(null);
  const [typeFilter, setTypeFilter] = useState(null);
  const [hideDecided, setHideDecided] = useState(false);
  const iframeRef = useRef(null);
  const [frameLoaded, setFrameLoaded] = useState(false);
  const layout = useDefaultLayout({ id: "rk3-patterns-split", panelIds: ["plist", "pdoc"] });

  useEffect(() => {
    getPatternsDoc(doc.slug)
      .then(setReport)
      .catch((e) => setErr(e));
  }, [doc.slug]);

  const candidates = report?.candidates || [];
  const decisions = report?.decisions || {};

  const typeCounts = useMemo(() => {
    const m = new Map();
    for (const c of candidates) m.set(c.pattern_type, (m.get(c.pattern_type) || 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [candidates]);

  const shown = useMemo(() => {
    let list = candidates;
    if (typeFilter) list = list.filter((c) => c.pattern_type === typeFilter);
    if (hideDecided) list = list.filter((c) => !decisions[c.pattern_id]);
    return [...list].sort((a, b) =>
      (a.source_refs?.[0]?.page ?? 0) - (b.source_refs?.[0]?.page ?? 0));
  }, [candidates, typeFilter, hideDecided, decisions]);

  // overlay: outline every shown candidate's source nodes in the doc
  useEffect(() => {
    const idoc = iframeRef.current?.contentDocument;
    if (!frameLoaded || !idoc) return;
    if (!idoc.getElementById("rk-pat-css")) {
      const st = idoc.createElement("style");
      st.id = "rk-pat-css";
      st.textContent = PAT_CSS;
      idoc.head.appendChild(st);
    }
    idoc.querySelectorAll(".rk-pat").forEach((el) => el.classList.remove("rk-pat"));
    for (const c of shown) {
      for (const ref of c.source_refs || []) {
        const el = ref.nid && idoc.querySelector(`[data-nid="${ref.nid}"]`);
        if (el) el.classList.add("rk-pat");
      }
    }
  }, [frameLoaded, shown]);

  const jump = (c) => {
    const idoc = iframeRef.current?.contentDocument;
    const nid = c.source_refs?.[0]?.nid;
    const el = nid && idoc?.querySelector(`[data-nid="${nid}"]`);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.classList.add("rk-pat-flash");
    setTimeout(() => el.classList.remove("rk-pat-flash"), 1200);
  };

  // {id, decision} — a note box open for pattern id; when `decision` is set
  // (reject-with-comments, wrong-type-with-comments) submitting the note also
  // records that decision in one gesture
  const [noteFor, setNoteFor] = useState(null);
  const decide = (c, decision, notes = null) => {
    postPatternDecision(doc.slug, {
      pattern_id: c.pattern_id, decision,
      pattern_type: c.pattern_type, notes,
    }).then(() => {
      setReport((r) => ({
        ...r,
        decisions: { ...r.decisions, [c.pattern_id]: { decision, notes } },
      }));
    }).catch((e) => reportError("save pattern decision", e));
  };
  // the qualitative WHY behind a decision is the registry's food (negative
  // indicators, false-positive classes, missing pattern types) — capture it
  // at the click, not in chat
  const addNote = (c, text) => {
    const d = decisions[c.pattern_id];
    decide(c, noteFor?.decision || d?.decision || "needs_more_context", text);
    setNoteFor(null);
  };

  if (err) {
    return (
      <div className="pane">
        <p>No pattern report for this document yet.</p>
        <p className="hint">The pattern track writes reports to patterns/out/&lt;slug&gt;.json.</p>
      </div>
    );
  }
  if (!report) return <div className="pane hint">Loading pattern report…</div>;

  const stamp = report.input || {};
  const decided = Object.keys(decisions).length;

  return (
    <div className="patterns-pane">
      <div className="pat-header">
        <span><strong>{candidates.length}</strong> candidates · {decided} reviewed</span>
        <span className="hint"> · input: irVersion {stamp.irVersion} @ {String(stamp.convertedAt || "").slice(0, 16)}</span>
        <label className="pat-hide">
          <input type="checkbox" checked={hideDecided}
                 onChange={(e) => setHideDecided(e.target.checked)} />
          hide reviewed
        </label>
      </div>
      <div className="pat-chips">
        <button className={"chip" + (typeFilter === null ? " on" : "")}
                onClick={() => setTypeFilter(null)}>all</button>
        {typeCounts.map(([t, n]) => (
          <button key={t} className={"chip" + (typeFilter === t ? " on" : "")}
                  onClick={() => setTypeFilter(typeFilter === t ? null : t)}>
            {t} <span className="chip-n">{n}</span>
          </button>
        ))}
      </div>
      <Group orientation="horizontal" className="split" {...layout.groupProps}>
        <Panel id="plist" defaultSize="42%" minSize="25%" className="pat-list-panel">
          <ul className="pat-list">
            {shown.map((c) => {
              const d = decisions[c.pattern_id];
              const ref = c.source_refs?.[0] || {};
              return (
                <li key={c.pattern_id}
                    className={"pat-item" + (d ? ` decided-${d.decision}` : "")}>
                  <div className="pat-row1">
                    <button className="jump" title="Show in document"
                            onClick={() => jump(c)}>→</button>
                    <strong>{c.pattern_type}</strong>
                    <span className="pat-meta">L{c.layer} · {Math.round((c.confidence || 0) * 100)}% · p{ref.page}</span>
                    <span className="pat-actions">
                      {DECISIONS.map(([dec, glyph]) => (
                        <button key={dec} title={dec}
                                className={"pat-btn" + (d?.decision === dec ? " on" : "")}
                                onClick={() => decide(c, dec)}>{glyph}</button>
                      ))}
                      <select value={MORE_DECISIONS.includes(d?.decision) ? d.decision : ""}
                              title="Other decision"
                              onChange={(e) => {
                                const v = e.target.value;
                                if (!v) return;
                                if (v === "reject+note" || v === "wrong_type+note") {
                                  setNoteFor({ id: c.pattern_id, decision: v.split("+")[0] });
                                } else {
                                  decide(c, v);
                                }
                                e.target.value = "";
                              }}>
                        <option value="">…</option>
                        <option value="reject+note">reject with comments…</option>
                        <option value="wrong_type+note">wrong type with comments…</option>
                        {MORE_DECISIONS.map((m) => <option key={m} value={m}>{m.replaceAll("_", " ")}</option>)}
                      </select>
                      <button className="pat-btn" title="Add a why-note to this decision"
                              onClick={() => setNoteFor(noteFor?.id === c.pattern_id ? null : { id: c.pattern_id, decision: null })}>✎</button>
                    </span>
                  </div>
                  <p className="pat-quote">“{(ref.quote || "").slice(0, 140)}”</p>
                  {c.fields && Object.keys(c.fields).length > 0 && (
                    <p className="pat-fields">
                      {Object.entries(c.fields)
                        .filter(([, v]) => v !== null && v !== "" &&
                                String(v) !== (ref.quote || ""))
                        .map(([k, v]) => (
                          <span key={k} className="pat-field">
                            <span className="pat-field-k">{k}</span>{" "}
                            {String(typeof v === "object" ? JSON.stringify(v) : v).slice(0, 70)}
                          </span>
                        ))}
                    </p>
                  )}
                  {noteFor?.id === c.pattern_id && (
                    <input className="pat-note" autoFocus
                           placeholder={(noteFor.decision ? `${noteFor.decision.replaceAll("_", " ")} — ` : "")
                             + "why? (feeds the pattern registry — e.g. 'mission statement, not a quotation')"}
                           onKeyDown={(e) => {
                             if (e.key === "Enter" && e.target.value.trim()) addNote(c, e.target.value.trim());
                             if (e.key === "Escape") setNoteFor(null);
                           }} />
                  )}
                  {d?.notes && <p className="pat-note-saved hint">✎ {d.notes}</p>}
                  {c.component_recommendations?.length > 0 && (
                    <p className="pat-rec hint">
                      → {c.component_recommendations.map((r) => r.component_type).join(", ")}
                    </p>
                  )}
                </li>
              );
            })}
            {shown.length === 0 && <li className="hint">Nothing matches the filter.</li>}
          </ul>
        </Panel>
        <Separator className="resizer" />
        <Panel id="pdoc" defaultSize="58%" minSize="30%" className="pat-doc-panel">
          <iframe ref={iframeRef} title="document" src={docUrl(doc.slug)}
                  onLoad={() => setFrameLoaded(true)} />
        </Panel>
      </Group>
    </div>
  );
}
