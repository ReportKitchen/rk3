import React, { useState } from "react";
import { ADMIN_FEEDBACK, ADMIN_METADATA } from "../api.js";

const LABELS = {
  unconverted: "unconverted",
  in_progress: "in progress",
  done: "converted",
  failed: "failed",
};

export default function DocList({ docs, selected, onSelect, onRefresh }) {
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
        <li
          className={"doc" + (selected === ADMIN_FEEDBACK ? " selected" : "")}
          onClick={() => onSelect(ADMIN_FEEDBACK)}
        >
          <span>All Feedback</span>
        </li>
        <li
          className={"doc" + (selected === ADMIN_METADATA ? " selected" : "")}
          onClick={() => onSelect(ADMIN_METADATA)}
        >
          <span>PDF Metadata</span>
        </li>
        {groups.map((g) => (
          <React.Fragment key={g.folder}>
            <li className="folder">{g.folder}/</li>
            {g.docs.map((d) => (
              <li
                key={d.slug}
                className={"doc" + (selected === d.slug ? " selected" : "")}
                onClick={() => onSelect(d.slug)}
              >
                <span className={"badge " + d.status}>{LABELS[d.status] ?? d.status}</span>
                <span>{d.name}</span>
              </li>
            ))}
          </React.Fragment>
        ))}
      </ul>
    </div>
  );
}
