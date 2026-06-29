import React, { useEffect, useMemo, useState } from "react";
import { saveOrderAssertion, saveReorderOp } from "../api.js";
import { guard } from "../errorBus.js";

// Reading-order tool: per page, the elements are pre-filled in the order the
// engine produced. Drag the wrong ones into place, then save — either as a
// gold-set `order` assertion (what we measure against) or as a reorder op (a
// per-document fix that corrects the output). No nids, no YAML.

const snippet = (n) =>
  (n.text || n.title || n.children?.find((c) => c.text)?.text || `[${n.type}]`)
    .replace(/\s+/g, " ").trim().slice(0, 80);

export default function ReadingOrderPanel({ slug, ir, onConvert }) {
  const nodes = ir?.body || [];
  const pages = useMemo(
    () => [...new Set(nodes.map((n) => n.page).filter((p) => p != null))]
      .sort((a, b) => a - b),
    [nodes]);
  const [page, setPage] = useState(null);
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState(null);
  const [dragI, setDragI] = useState(null);

  useEffect(() => { if (page == null && pages.length) setPage(pages[0]); }, [pages, page]);
  useEffect(() => {
    setItems(nodes.filter((n) => n.page === page));
    setStatus(null);
  }, [page, ir]);

  const move = (from, to) => setItems((arr) => {
    const a = [...arr];
    a.splice(to, 0, a.splice(from, 1)[0]);
    return a;
  });
  const dirty = items.some((n, i) => n.nid !== nodes.filter((m) => m.page === page)[i]?.nid);

  const saveGold = async () => {
    const order = items.map((n) => snippet(n).slice(0, 45)).filter(Boolean);
    if (order.length < 2) return setStatus("need ≥2 elements to assert an order");
    const r = await saveOrderAssertion(slug, order, `p${page} reading order`)
      .catch(guard("save order assertion", null));
    if (r) setStatus(r.ok
      ? "✓ saved — the engine already reads this page in this order"
      : "✓ saved as gold set — currently FAILS (the engine reads it differently)");
  };
  const applyFix = async () => {
    await saveReorderOp(slug, page, items.map((n) => n.nid))
      .catch(guard("save reorder op", null));
    setStatus("✓ fix saved to the document — reconverting…");
  };

  if (!pages.length)
    return <p className="hint">No page elements — convert the document first.</p>;

  return (
    <div className="rorder">
      <div className="rorder-bar">
        <label>Page&nbsp;
          <select value={page ?? ""} onChange={(e) => setPage(+e.target.value)}>
            {pages.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </label>
        <button className="rorder-save" disabled={!dirty && !items.length}
                onClick={saveGold} title="Record this as the correct order (eval gold set)">
          Save as correct order
        </button>
        <button className="rorder-fix" disabled={!dirty}
                onClick={applyFix} title="Reorder this page in the output (per-document fix)">
          Apply as fix
        </button>
        {status && <span className="rorder-status">{status}</span>}
      </div>
      <ol className="rorder-list">
        {items.map((n, i) => (
          <li key={n.nid} draggable
              onDragStart={() => setDragI(i)}
              onDragEnter={() => { if (dragI != null && dragI !== i) { move(dragI, i); setDragI(i); } }}
              onDragEnd={() => setDragI(null)}
              onDragOver={(e) => e.preventDefault()}
              className={dragI === i ? "dragging" : ""}>
            <span className="rorder-handle" aria-hidden>⠿</span>
            <span className="rorder-num">{i + 1}</span>
            <span className={"rorder-badge " + n.type}>{n.type}</span>
            <span className="rorder-text">{snippet(n)}</span>
          </li>
        ))}
      </ol>
      <p className="hint rorder-help">
        Drag rows into the order a person would read them. <b>Save as correct
        order</b> records a gold-set assertion (what we measure against);
        <b> Apply as fix</b> writes a per-document reorder that corrects the
        output.
      </p>
    </div>
  );
}
