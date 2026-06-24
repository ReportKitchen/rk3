import React from "react";

// top bar: just the document name; view toggles now live in DocToolbar,
// inside the Convert Document tab
export default function Toolbar({ doc }) {
  return (
    <div id="toolbar">
      <span id="docname">{doc.name}</span>
    </div>
  );
}
