import React, { useEffect, useMemo, useRef, useState } from "react";
import { Group, Panel, Separator, useDefaultLayout } from "react-resizable-panels";
import { docUrl, getPatternsDoc, postPatternDecision, postPatternScanDecision } from "../api.js";
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
const VIEW_MODES = [
  ["deterministic", "deterministic"],
  ["overruled", "LLM overrules"],
  ["proposed", "LLM proposals"],
  ["compare", "compare"],
];
const LLM_OVERRULE_DECISIONS = new Set(["reject", "wrong_type"]);

export default function PatternsPanel({ doc }) {
  const [report, setReport] = useState(null);
  const [err, setErr] = useState(null);
  const [typeFilter, setTypeFilter] = useState(null);
  const [hideDecided, setHideDecided] = useState(false);
  const [viewMode, setViewMode] = useState("compare");
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
  const scanDecisions = report?.llm_scan_decisions || {};
  const llmReviews = report?.llm_reviews || [];
  const llmScans = report?.llm_scans || [];
  const reviewByPattern = useMemo(() => {
    const m = new Map();
    for (const r of llmReviews) m.set(r.pattern_id, r);
    return m;
  }, [llmReviews]);
  const candidateById = useMemo(() => {
    const m = new Map();
    for (const c of candidates) m.set(c.pattern_id, c);
    return m;
  }, [candidates]);

  const typeCounts = useMemo(() => {
    const m = new Map();
    const count = (t) => m.set(t, (m.get(t) || 0) + 1);
    if (viewMode !== "proposed") {
      for (const c of candidates) {
        const r = reviewByPattern.get(c.pattern_id);
        if (viewMode === "overruled" && !LLM_OVERRULE_DECISIONS.has(r?.decision)) continue;
        count(c.pattern_type);
      }
    }
    if (viewMode === "proposed" || viewMode === "compare") {
      for (const s of llmScans) count(s.pattern_type);
    }
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [candidates, llmScans, reviewByPattern, viewMode]);

  const shown = useMemo(() => {
    let items = [];
    if (viewMode !== "proposed") {
      items.push(...candidates.map((c) => ({ kind: "deterministic", id: c.pattern_id, candidate: c, llmReview: reviewByPattern.get(c.pattern_id) })));
    }
    if (viewMode === "proposed" || viewMode === "compare") {
      items.push(...llmScans.map((s) => ({ kind: "llm_scan", id: s.scan_id, scan: s, overlapCandidate: candidateById.get(s.deterministic_overlap?.pattern_id) })));
    }
    if (viewMode === "overruled") {
      items = items.filter((item) => LLM_OVERRULE_DECISIONS.has(item.llmReview?.decision));
    }
    if (typeFilter) items = items.filter((item) => itemType(item) === typeFilter);
    if (hideDecided) {
      items = items.filter((item) =>
        item.kind === "deterministic" ? !decisions[item.id] : !scanDecisions[item.id]);
    }
    return items.sort((a, b) => itemPage(a) - itemPage(b) || itemType(a).localeCompare(itemType(b)));
  }, [candidates, llmScans, typeFilter, hideDecided, decisions, scanDecisions, reviewByPattern, candidateById, viewMode]);

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
    for (const item of shown) {
      const c = item.kind === "llm_scan" ? item.overlapCandidate : item.candidate;
      if (!c) continue;
      for (const ref of c.source_refs || []) {
        const el = ref.nid && idoc.querySelector(`[data-nid="${ref.nid}"]`);
        if (el) el.classList.add("rk-pat");
      }
    }
  }, [frameLoaded, shown]);

  const jump = (item) => {
    const idoc = iframeRef.current?.contentDocument;
    const c = item.kind === "llm_scan" ? item.overlapCandidate : item.candidate;
    if (!c) return;
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
  const decideScan = (s, decision, notes = null) => {
    postPatternScanDecision(doc.slug, {
      scan_id: s.scan_id, decision,
      pattern_type: s.pattern_type, notes,
    }).then(() => {
      setReport((r) => ({
        ...r,
        llm_scan_decisions: { ...(r.llm_scan_decisions || {}), [s.scan_id]: { decision, notes } },
      }));
    }).catch((e) => reportError("save LLM proposal decision", e));
  };
  // the qualitative WHY behind a decision is the registry's food (negative
  // indicators, false-positive classes, missing pattern types) — capture it
  // at the click, not in chat
  const addNote = (item, text) => {
    if (item.kind === "llm_scan") {
      const d = scanDecisions[item.id];
      decideScan(item.scan, noteFor?.decision || d?.decision || "needs_more_context", text);
    } else {
      const d = decisions[item.id];
      decide(item.candidate, noteFor?.decision || d?.decision || "needs_more_context", text);
    }
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
  const scanDecided = Object.keys(scanDecisions).length;
  const overruled = candidates.filter((c) => LLM_OVERRULE_DECISIONS.has(reviewByPattern.get(c.pattern_id)?.decision)).length;

  return (
    <div className="patterns-pane">
      <div className="pat-header">
        <span><strong>{candidates.length}</strong> candidates · {decided} reviewed · {llmReviews.length} LLM reviews · {scanDecided}/{llmScans.length} LLM proposals reviewed · {overruled} overruled</span>
        <span className="hint"> · input: irVersion {stamp.irVersion} @ {String(stamp.convertedAt || "").slice(0, 16)}</span>
        <label className="pat-hide">
          <input type="checkbox" checked={hideDecided}
                 onChange={(e) => setHideDecided(e.target.checked)} />
          hide reviewed
        </label>
      </div>
      <div className="pat-modes">
        {VIEW_MODES.map(([mode, label]) => (
          <button key={mode} className={"pat-mode" + (viewMode === mode ? " on" : "")}
                  onClick={() => setViewMode(mode)}>
            {label}
          </button>
        ))}
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
            {shown.map((item) => {
              if (item.kind === "llm_scan") {
                const s = item.scan;
                const overlap = s.deterministic_overlap;
                const d = scanDecisions[s.scan_id];
                return (
                  <li key={item.id} className={"pat-item pat-item-llm" + (d ? ` decided-${d.decision}` : "")}>
                    <div className="pat-row1">
                      <button className="jump" title="Show overlap in document" disabled={!item.overlapCandidate}
                              onClick={() => jump(item)}>→</button>
                      <span className="pat-source">LLM proposal</span>
                      <ModelChip row={s} />
                      <strong>{s.pattern_type}</strong>
                      <span className="pat-meta">{Math.round((s.confidence || 0) * 100)}% · p{s.page}</span>
                      <PatternActions
                        decision={d}
                        onDecide={(decision) => decideScan(s, decision)}
                        onNote={(decision) => setNoteFor({ kind: item.kind, id: item.id, decision })}
                      />
                    </div>
                    {overlap ? (
                      <p className={"pat-llm pat-overlap" + (overlap.pattern_type === s.pattern_type ? " same" : "")}>
                        overlaps deterministic <strong>{overlap.pattern_type}</strong> {overlap.pattern_id} · {Math.round((overlap.score || 0) * 100)}%
                      </p>
                    ) : (
                      <p className="pat-llm pat-only">LLM-only: no deterministic text overlap found.</p>
                    )}
                    <p className="pat-quote">“{(s.quote || "").slice(0, 220)}”</p>
                    {s.reason && <p className="pat-note-saved hint">LLM: {s.reason}</p>}
                    {s.fields && Object.keys(s.fields).length > 0 && <PatternFields fields={s.fields} quote={s.quote} />}
                    {noteFor?.kind === item.kind && noteFor?.id === item.id && (
                      <NoteInput noteFor={noteFor} onSubmit={(text) => addNote(item, text)} onCancel={() => setNoteFor(null)} />
                    )}
                    {d?.notes && <p className="pat-note-saved hint">✎ {d.notes}</p>}
                  </li>
                );
              }
              const c = item.candidate;
              const d = decisions[c.pattern_id];
              const ref = c.source_refs?.[0] || {};
              const llm = item.llmReview;
              return (
                <li key={c.pattern_id}
                    className={"pat-item" + (d ? ` decided-${d.decision}` : "") + (LLM_OVERRULE_DECISIONS.has(llm?.decision) ? " llm-overruled" : "")}>
                  <div className="pat-row1">
                    <button className="jump" title="Show in document"
                            onClick={() => jump(item)}>→</button>
                    <span className="pat-source">deterministic</span>
                    <strong>{c.pattern_type}</strong>
                    <span className="pat-meta">L{c.layer} · {Math.round((c.confidence || 0) * 100)}% · p{ref.page}</span>
                    <PatternActions
                      decision={d}
                      onDecide={(decision) => decide(c, decision)}
                      onNote={(decision) => setNoteFor({ kind: item.kind, id: item.id, decision })}
                    />
                  </div>
                  {llm && (
                    <p className={"pat-llm decision-" + llm.decision}>
                      <ModelChip row={llm} />{" "}
                      LLM {llm.decision?.replaceAll("_", " ")} · {Math.round((llm.confidence || 0) * 100)}%
                      {llm.corrected_pattern_type ? ` · suggested ${llm.corrected_pattern_type}` : ""}
                      {llm.reason ? `: ${llm.reason}` : ""}
                    </p>
                  )}
                  <p className="pat-quote">“{(ref.quote || "").slice(0, 140)}”</p>
                  {c.fields && Object.keys(c.fields).length > 0 && <PatternFields fields={c.fields} quote={ref.quote} />}
                  {noteFor?.kind === item.kind && noteFor?.id === item.id && (
                    <NoteInput noteFor={noteFor} onSubmit={(text) => addNote(item, text)} onCancel={() => setNoteFor(null)} />
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

function itemType(item) {
  return item.kind === "llm_scan" ? item.scan.pattern_type : item.candidate.pattern_type;
}

function itemPage(item) {
  return item.kind === "llm_scan" ? (item.scan.page ?? 0) : (item.candidate.source_refs?.[0]?.page ?? 0);
}

function PatternActions({ decision, onDecide, onNote }) {
  return (
    <span className="pat-actions">
      {DECISIONS.map(([dec, glyph]) => (
        <button key={dec} title={dec}
                className={"pat-btn" + (decision?.decision === dec ? " on" : "")}
                onClick={() => onDecide(dec)}>{glyph}</button>
      ))}
      <select value={MORE_DECISIONS.includes(decision?.decision) ? decision.decision : ""}
              title="Other decision"
              onChange={(e) => {
                const v = e.target.value;
                if (!v) return;
                if (v === "reject+note" || v === "wrong_type+note") {
                  onNote(v.split("+")[0]);
                } else {
                  onDecide(v);
                }
                e.target.value = "";
              }}>
        <option value="">…</option>
        <option value="reject+note">reject with comments…</option>
        <option value="wrong_type+note">wrong type with comments…</option>
        {MORE_DECISIONS.map((m) => <option key={m} value={m}>{m.replaceAll("_", " ")}</option>)}
      </select>
      <button className="pat-btn" title="Add a why-note to this decision"
              onClick={() => onNote(null)}>✎</button>
    </span>
  );
}

function NoteInput({ noteFor, onSubmit, onCancel }) {
  return (
    <input className="pat-note" autoFocus
           placeholder={(noteFor.decision ? `${noteFor.decision.replaceAll("_", " ")} — ` : "")
             + "why? (feeds pattern/LLM tuning — e.g. 'good landing-page finding' or 'not a real statistic')"}
           onKeyDown={(e) => {
             if (e.key === "Enter" && e.target.value.trim()) onSubmit(e.target.value.trim());
             if (e.key === "Escape") onCancel();
           }} />
  );
}

function PatternFields({ fields, quote }) {
  return (
    <p className="pat-fields">
      {Object.entries(fields)
        .filter(([, v]) => v !== null && v !== "" && String(v) !== (quote || ""))
        .map(([k, v]) => (
          <span key={k} className="pat-field">
            <span className="pat-field-k">{k}</span>{" "}
            {String(typeof v === "object" ? JSON.stringify(v) : v).slice(0, 90)}
          </span>
        ))}
    </p>
  );
}

function ModelChip({ row }) {
  if (!row?.provider && !row?.model) return null;
  const label = [row.provider, row.model].filter(Boolean).join("/");
  return <span className="pat-field" title="LLM provider/model">[{label}]</span>;
}
