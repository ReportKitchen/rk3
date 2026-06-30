import React, { useState } from "react";
import { ADMIN_FEEDBACK, ADMIN_METADATA } from "../api.js";

const LABELS = {
  unconverted: "unconverted",
  in_progress: "in progress",
  done: "converted",
  failed: "failed",
};

// the doc URL: ?doc=<slug> (admin slugs carry a colon, so encode). Real <a>
// hrefs let the row be right-click → open-in-new-window and put the slug in the
// address bar so a reload lands back on the same document.
const docHref = (slug) => `?doc=${encodeURIComponent(slug)}`;

export default function DocList({ docs, selected, onSelect, onRefresh }) {
  // plain left-click navigates in-app (no reload); let the browser handle
  // ctrl/cmd/shift/alt and middle clicks so new tab / new window still work
  const open = (slug) => (e) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
    e.preventDefault();
    onSelect(slug);
  };
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("rk3-left-collapsed") === "1");
  const setCollapse = (v) => {
    setCollapsed(v);
    localStorage.setItem("rk3-left-collapsed", v ? "1" : "0");
  };

  if (collapsed) {
    return (
      <div id="left" className="collapsed">
        <button className="left-rail" onClick={() => setCollapse(false)}
          title="Expand Source Documents">
          <span className="rail-icon">»</span>
          <span className="rail-title">Source Documents</span>
        </button>
      </div>
    );
  }

  const groups = [];
  let folder = null;
  for (const d of docs) {
    if (d.folder !== folder) {
      folder = d.folder;
      groups.push({ folder, docs: [] });
    }
    groups[groups.length - 1].docs.push(d);
  }
  // documents read alphabetically within each folder
  for (const g of groups) {
    g.docs.sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }));
  }

  return (
    <div id="left">
      <header>
        <h1>Source Documents</h1>
        <span className="left-actions">
          <button onClick={onRefresh} title="Refresh list">&#8635; Refresh</button>
          <button className="collapse-btn" onClick={() => setCollapse(true)}
            title="Collapse">&#8249;</button>
        </span>
      </header>
      <ul id="doclist">
        <li className="folder">Admin/</li>
        <li>
          <a className={"doc" + (selected === ADMIN_FEEDBACK ? " selected" : "")}
            href={docHref(ADMIN_FEEDBACK)} onClick={open(ADMIN_FEEDBACK)}>
            <span>All Feedback</span>
          </a>
        </li>
        <li>
          <a className={"doc" + (selected === ADMIN_METADATA ? " selected" : "")}
            href={docHref(ADMIN_METADATA)} onClick={open(ADMIN_METADATA)}>
            <span>PDF Metadata</span>
          </a>
        </li>
        {groups.map((g) => (
          <React.Fragment key={g.folder}>
            <li className="folder">{g.folder}/</li>
            {g.docs.map((d) => (
              <li key={d.slug}>
                <a className={"doc" + (selected === d.slug ? " selected" : "")}
                  href={docHref(d.slug)} onClick={open(d.slug)}>
                  <span className={"badge " + d.status}>{LABELS[d.status] ?? d.status}</span>
                  <span>{d.name}</span>
                </a>
              </li>
            ))}
          </React.Fragment>
        ))}
      </ul>
    </div>
  );
}
