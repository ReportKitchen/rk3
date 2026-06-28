import React, { useEffect, useMemo, useState } from "react";
import { getAllFeedback } from "../api.js";

// Admin → All Feedback: a client-side sortable/searchable table of every
// feedback entry across all documents. The list is kept short enough to handle
// entirely in the browser.

const COLUMNS = [
  { key: "docName", label: "Document" },
  { key: "page", label: "Page", num: true, width: "3.5rem" },
  { key: "category", label: "Category", width: "7rem" },
  { key: "type", label: "Type", width: "5rem" },
  { key: "statusLabel", label: "Status", width: "4.5rem" },
  { key: "modified", label: "Modified", width: "8.5rem" },
  { key: "note", label: "Note" },
];

function derive(f) {
  const modified = f.edited || f.clearedAt || f.ts || "";
  return {
    ...f,
    statusLabel: f.status === "cleared" ? "closed" : (f.status || "open"),
    modified,
    note: (f.text || f.choice || f.qPrompt || "").trim(),
  };
}

function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleString(undefined,
    { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function FeedbackTable({ onOpen }) {
  const [rows, setRows] = useState(null);
  const [query, setQuery] = useState("");
  const [showClosed, setShowClosed] = useState(false);
  const [sort, setSort] = useState({ key: "modified", dir: "desc" });

  const load = () => getAllFeedback().then((r) => setRows(r.map(derive))).catch(() => setRows([]));
  useEffect(() => { load(); }, []);

  const clickSort = (key) =>
    setSort((s) => s.key === key
      ? { key, dir: s.dir === "asc" ? "desc" : "asc" }
      : { key, dir: "asc" });

  const view = useMemo(() => {
    if (!rows) return [];
    const q = query.trim().toLowerCase();
    let r = rows;
    if (!showClosed) r = r.filter((x) => x.statusLabel !== "closed");
    if (q) {
      r = r.filter((x) => COLUMNS.some((c) => {
        const v = x[c.key];
        return v != null && String(v).toLowerCase().includes(q);
      }));
    }
    const col = COLUMNS.find((c) => c.key === sort.key) || COLUMNS[0];
    const sign = sort.dir === "asc" ? 1 : -1;
    return [...r].sort((a, b) => {
      let av = a[col.key], bv = b[col.key];
      if (col.num) return ((av ?? -1) - (bv ?? -1)) * sign;
      return String(av ?? "").localeCompare(String(bv ?? ""),
        undefined, { sensitivity: "base", numeric: true }) * sign;
    });
  }, [rows, query, showClosed, sort]);

  if (rows === null) return <p className="hint">Loading feedback…</p>;

  const closedCount = rows.filter((x) => x.statusLabel === "closed").length;

  return (
    <div className="fbtable">
      <div className="fbtable-bar">
        <h2>All Feedback</h2>
        <input
          className="fbtable-search"
          type="search"
          placeholder="Search…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />
        <label className="fbtable-toggle">
          <input type="checkbox" checked={showClosed}
            onChange={(e) => setShowClosed(e.target.checked)} />
          Show closed{closedCount ? ` (${closedCount})` : ""}
        </label>
        <span className="fbtable-count">{view.length} of {rows.length}</span>
        <button className="fbtable-refresh" onClick={load} title="Reload">↻</button>
      </div>
      <div className="fbtable-scroll">
        <table>
          <thead>
            <tr>
              {COLUMNS.map((c) => (
                <th key={c.key} style={c.width ? { width: c.width } : undefined}
                    onClick={() => clickSort(c.key)}>
                  {c.label}
                  {sort.key === c.key && (sort.dir === "asc" ? " ▲" : " ▼")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {view.map((r) => (
              <tr key={r.slug + ":" + (r.id || r.ts)}
                  className={r.statusLabel === "closed" ? "closed" : ""}>
                <td>
                  <button className="fbtable-doc" title="Open document"
                          onClick={() => onOpen(r.slug)}>
                    {r.docName}
                  </button>
                </td>
                <td className="num">{r.page ?? ""}</td>
                <td>{r.category || ""}</td>
                <td>{r.type || ""}</td>
                <td>{r.statusLabel}</td>
                <td title={r.modified}>{fmtDate(r.modified)}</td>
                <td className="fbtable-note">{r.note}</td>
              </tr>
            ))}
            {view.length === 0 && (
              <tr><td colSpan={COLUMNS.length} className="hint">No matching feedback.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
