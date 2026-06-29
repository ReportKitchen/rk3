import React, { useEffect, useMemo, useState } from "react";
import { getPdfMetadata } from "../api.js";
import { guard } from "../errorBus.js";

// Admin → PDF Metadata: one row per document with its authoring tools (PDF
// Creator/Producer) and the fonts it uses. The main (bulk) font is shown in its
// own column; the full font list stays collapsed behind a "+N" toggle so a
// document with dozens of named fonts doesn't blow up the table. Font usage
// comes from the converted ir.json, so it's blank until a document is converted.

const COLUMNS = [
  { key: "docName", label: "Document" },
  { key: "creator", label: "Created with", width: "14rem" },
  { key: "producer", label: "PDF Producer", width: "12rem" },
  { key: "mainFont", label: "Main font", width: "12rem" },
  { key: "fontCount", label: "Fonts", num: true, width: "4rem" },
  { key: "embedComplete", label: "Embed", width: "9rem" },
];

// the embed verdict cell: did font extraction fully reconstruct every font
// (so embedding is on by default), or does some font drop glyphs (default off)?
function embedCell(r) {
  if (!r.embedTotal) return <span className="meta-dim">—</span>;
  if (r.embedComplete) {
    return <span className="meta-embed ok" title="all fonts fully reconstructed — embedded by default">on · {r.embedTotal}</span>;
  }
  return <span className="meta-embed partial"
    title={`${r.embedPartial} of ${r.embedTotal} fonts drop glyphs — embedding off by default`}>
    off · {r.embedPartial}/{r.embedTotal} partial</span>;
}

export default function MetadataTable({ onOpen }) {
  const [rows, setRows] = useState(null);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState({ key: "docName", dir: "asc" });
  const [expanded, setExpanded] = useState(() => new Set());

  const load = () => getPdfMetadata().then(setRows)
    .catch((e) => { guard("load pdf metadata", null)(e); setRows([]); });
  useEffect(() => { load(); }, []);

  const toggle = (slug) => setExpanded((s) => {
    const n = new Set(s);
    n.has(slug) ? n.delete(slug) : n.add(slug);
    return n;
  });

  const clickSort = (key) =>
    setSort((s) => s.key === key
      ? { key, dir: s.dir === "asc" ? "desc" : "asc" }
      : { key, dir: "asc" });

  const view = useMemo(() => {
    if (!rows) return [];
    const q = query.trim().toLowerCase();
    let r = rows;
    if (q) {
      r = r.filter((x) =>
        [x.docName, x.creator, x.producer, x.mainFont]
          .some((v) => v && String(v).toLowerCase().includes(q))
        || (x.fonts || []).some((f) => f.name.toLowerCase().includes(q)));
    }
    const col = COLUMNS.find((c) => c.key === sort.key) || COLUMNS[0];
    const sign = sort.dir === "asc" ? 1 : -1;
    return [...r].sort((a, b) => {
      const av = a[col.key], bv = b[col.key];
      if (col.num) return ((av ?? -1) - (bv ?? -1)) * sign;
      return String(av ?? "").localeCompare(String(bv ?? ""),
        undefined, { sensitivity: "base", numeric: true }) * sign;
    });
  }, [rows, query, sort]);

  if (rows === null) return <p className="hint">Loading metadata…</p>;

  const converted = rows.filter((r) => r.fontCount > 0).length;

  return (
    <div className="fbtable">
      <div className="fbtable-bar">
        <h2>PDF Metadata</h2>
        <input
          className="fbtable-search"
          type="search"
          placeholder="Search tool or font…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />
        <span className="fbtable-count">
          {view.length} of {rows.length} · {converted} converted
        </span>
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
            {view.map((r) => {
              const isOpen = expanded.has(r.slug);
              const extra = r.fontCount - 1;
              return (
                <React.Fragment key={r.slug}>
                  <tr>
                    <td>
                      <button className="fbtable-doc" title="Open document"
                              onClick={() => onOpen(r.slug)}>
                        {r.docName}
                      </button>
                    </td>
                    <td title={r.creator || ""}>{r.creator || <span className="meta-dim">—</span>}</td>
                    <td title={r.producer || ""}>{r.producer || <span className="meta-dim">—</span>}</td>
                    <td title={r.mainFont || ""}>
                      {r.mainFont
                        ? <span className="meta-font">{r.mainFont}</span>
                        : <span className="meta-dim">not converted</span>}
                    </td>
                    <td className="num">
                      {r.fontCount > 1 ? (
                        <button className="meta-more" onClick={() => toggle(r.slug)}
                                title="Show all fonts">
                          {isOpen ? "▾" : `+${extra}`}
                        </button>
                      ) : (r.fontCount || "")}
                    </td>
                    <td>{embedCell(r)}</td>
                  </tr>
                  {isOpen && (
                    <tr className="meta-fontrow">
                      <td colSpan={COLUMNS.length}>
                        <div className="meta-fontlist">
                          {(r.fonts || []).map((f, i) => (
                            <span key={f.name + i}
                                  className={"meta-chip" + (i === 0 ? " main" : "")
                                             + (f.embedded ? " embedded" : "")}
                                  title={`${f.chars.toLocaleString()} characters`
                                         + (f.embedded ? " · embedded in the PDF" : "")}>
                              {f.name}
                              <em>{f.chars.toLocaleString()}</em>
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
            {view.length === 0 && (
              <tr><td colSpan={COLUMNS.length} className="hint">No matching documents.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
