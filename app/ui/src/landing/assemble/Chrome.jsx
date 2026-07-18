import React from "react";
import { Icon } from "./icons.jsx";

// The 56px top stepper (round-2 parts/LpmChrome, reduced to three steps):
// Assemble → Wordsmith → Publish. Numbered circles turn into a ✓ once a step is
// behind you. Publish = the full-page preview + the publish rail (social
// graphic, download) — the separate Preview/Publish split was collapsed.
const STEPS = ["Assemble", "Wordsmith", "Publish"];

export default function Chrome({ title, activeIdx, onStep }) {
  return (
    <div className="asm-chrome">
      <span className="asm-chrome-logo">Report Kitchen</span>
      <span className="asm-chrome-badge">Landing Page Maker</span>
      <span className="asm-chrome-divider" />
      <span className="asm-chrome-title" title={title}>{title}</span>
      <div className="asm-steps">
        {STEPS.map((name, i) => {
          const done = i < activeIdx;
          const active = i === activeIdx;
          return (
            <React.Fragment key={name}>
              <button
                type="button"
                className={"asm-step" + (active ? " is-active" : "") + (done ? " is-done" : "")}
                onClick={() => onStep(i)}
              >
                <span className="asm-step-circle">{done ? "✓" : i + 1}</span>
                <span className="asm-step-label">{name}</span>
              </button>
              {i < STEPS.length - 1 && (
                <Icon name="chevron-right" size={13} className="asm-step-sep" />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
