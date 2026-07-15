import React from "react";
import { Drawer } from "@measured/puck";

// The left-hand block library. Puck's DnD comes from Drawer/Drawer.Item; the
// tile markup is ours, so each block gets the design kit's miniature + the
// one-line "what this is" that the old Add catalog never had room for.
//
// `name` MUST match the Puck component name in puckConfig — that's what a drop
// inserts.

const RHINO = "var(--rk-rhino-700)";
const MID = "var(--rk-rhino-300)";
const FAINT = "var(--rk-rhino-100)";
const MAC = "var(--rk-macaroni)";
const MUFFIN = "var(--rk-muffin)";

// one bar of a miniature
const bar = (width, background, height = 3) => ({ width, height, background, borderRadius: 1 });

const Bars = ({ rows }) => rows.map((s, i) => <i key={i} style={s} />);

export const LIBRARY = [
  {
    name: "Title",
    label: "Title",
    hint: "Eyebrow, headline, deck",
    thumb: <Bars rows={[bar("70%", RHINO, 7), bar("50%", FAINT)]} />,
  },
  {
    name: "Summary",
    label: "AI Summary",
    hint: "Claude writes the pitch",
    ai: "generate",
    thumb: <Bars rows={[bar("90%", MAC), bar("85%", FAINT), bar("88%", FAINT)]} />,
  },
  {
    name: "DocSummary",
    label: "Document Summary",
    hint: "A section, quoted",
    thumb: <Bars rows={[bar("88%", FAINT), bar("92%", FAINT), bar("60%", FAINT)]} />,
  },
  {
    name: "Cover",
    label: "Report cover",
    hint: "Page 1 as an image",
    center: true,
    thumb: <i style={{ height: 22, width: 17, background: MUFFIN, border: `1px solid ${FAINT}` }} />,
  },
  {
    name: "Hero",
    label: "Hero image",
    hint: "Full-width visual",
    thumb: <i style={{ height: 26, width: "100%", background: `linear-gradient(120deg, ${MUFFIN}, ${FAINT})` }} />,
  },
  {
    name: "Toc",
    label: "Table of contents",
    hint: "Linked section list",
    thumb: <Bars rows={[bar("55%", MID), bar("70%", FAINT), bar("62%", FAINT)]} />,
  },
  {
    name: "Highlights",
    label: "Highlights",
    hint: "Key points, as bullets",
    thumb: (
      <>
        {[80, 88, 66].map((w, i) => (
          <span key={i} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <i style={{ width: 3, height: 3, borderRadius: "50%", background: MID, flex: "none" }} />
            <i style={bar(`${w}%`, FAINT)} />
          </span>
        ))}
      </>
    ),
  },
  {
    name: "Findings",
    label: "Findings",
    hint: "Figure + the fact it belongs to",
    row: true,
    ai: "analyze",
    thumb: (
      <>
        <i style={{ height: 12, width: 26, background: RHINO, borderRadius: 1, flex: "none" }} />
        <i style={bar("40%", FAINT)} />
      </>
    ),
  },
  {
    name: "Share",
    label: "Social share",
    hint: "Buttons + OG preview",
    row: true,
    center: true,
    thumb: (
      <>
        {["var(--rk-tomato-300)", "var(--rk-macaroni-300)", MUFFIN].map((c) => (
          <i key={c} style={{ height: 10, width: 10, borderRadius: "50%", background: c, flex: "none" }} />
        ))}
      </>
    ),
  },
  {
    name: "Download",
    label: "Download CTA",
    hint: "The button that gets the PDF",
    center: true,
    thumb: <i style={{ height: 13, width: "62%", borderRadius: 3, background: RHINO }} />,
  },
  {
    name: "SecondaryCta",
    label: "Secondary CTA",
    hint: "Donate, subscribe, get in touch",
    center: true,
    thumb: <i style={{ height: 11, width: "50%", borderRadius: 3, border: `1.5px solid ${MID}` }} />,
  },
];

const Grip = () => (
  <svg className="lp-tile-grip" width="10" height="14" viewBox="0 0 10 14" fill="currentColor" aria-hidden="true">
    {[2, 7, 12].map((cy) => (
      <React.Fragment key={cy}>
        <circle cx="3" cy={cy} r="1.3" />
        <circle cx="7" cy={cy} r="1.3" />
      </React.Fragment>
    ))}
  </svg>
);

// AI-backed blocks are hidden rather than disabled when the mode forbids them —
// the same rule the old Add catalog applied via the drawerItem override.
export function BlockLibrary({ canGenerate, canAnalyze }) {
  const items = LIBRARY.filter(
    (b) => !b.ai || (b.ai === "generate" ? canGenerate : canAnalyze),
  );
  return (
    <Drawer>
      {items.map((b) => (
        <Drawer.Item key={b.name} name={b.name} label={b.label}>
          {() => (
            <div className="lp-tile">
              <span className={"lp-tile-thumb" + (b.row ? " row" : "") + (b.center ? " center" : "")}>
                {b.thumb}
              </span>
              <span className="lp-tile-txt">
                <span className="lp-tile-name">{b.label}</span>
                <span className="lp-tile-hint">{b.hint}</span>
              </span>
              <Grip />
            </div>
          )}
        </Drawer.Item>
      ))}
    </Drawer>
  );
}
