import React from "react";

const LABELS = {
  unconverted: "unconverted",
  in_progress: "in progress",
  done: "converted",
  failed: "failed",
};

export default function DocList({ docs, selected, onSelect, onRefresh }) {
  const groups = [];
  let folder = null;
  for (const d of docs) {
    if (d.folder !== folder) {
      folder = d.folder;
      groups.push({ folder, docs: [] });
    }
    groups[groups.length - 1].docs.push(d);
  }

  return (
    <div id="left">
      <header>
        <h1>RK3</h1>
        <button onClick={onRefresh} title="Refresh list">&#8635; Refresh</button>
      </header>
      <ul id="doclist">
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
