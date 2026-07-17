import React from "react";

// Stat icons for the `icons` treatment. A curated, INLINE Lucide set (the export
// has no CDN, so we inline just the themes report stats actually hit) plus a
// keyword matcher that picks a good icon from the stat's own words — no AI needed
// (the Lucide long tail can be an AI upgrade later). Each entry is lucide's own
// [tag, attrs] data.
const ICONS = {
  banknote: [["rect", { width: 20, height: 12, x: 2, y: 6, rx: 2 }], ["circle", { cx: 12, cy: 12, r: 2 }], ["path", { d: "M6 12h.01M18 12h.01" }]],
  percent: [["line", { x1: 19, x2: 5, y1: 5, y2: 19 }], ["circle", { cx: 6.5, cy: 6.5, r: 2.5 }], ["circle", { cx: 17.5, cy: 17.5, r: 2.5 }]],
  hourglass: [["path", { d: "M5 22h14" }], ["path", { d: "M5 2h14" }], ["path", { d: "M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22" }], ["path", { d: "M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2" }]],
  users: [["path", { d: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" }], ["circle", { cx: 9, cy: 7, r: 4 }], ["path", { d: "M22 21v-2a4 4 0 0 0-3-3.87" }], ["path", { d: "M16 3.13a4 4 0 0 1 0 7.75" }]],
  "graduation-cap": [["path", { d: "M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z" }], ["path", { d: "M22 10v6" }], ["path", { d: "M6 12.5V16a6 3 0 0 0 12 0v-3.5" }]],
  "heart-pulse": [["path", { d: "M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" }], ["path", { d: "M3.22 12H9.5l.5-1 2 4.5 2-7 1.5 3.5h5.27" }]],
  leaf: [["path", { d: "M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" }], ["path", { d: "M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" }]],
  house: [["path", { d: "M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8" }], ["path", { d: "M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" }]],
  landmark: [["line", { x1: 3, x2: 21, y1: 22, y2: 22 }], ["line", { x1: 6, x2: 6, y1: 18, y2: 11 }], ["line", { x1: 10, x2: 10, y1: 18, y2: 11 }], ["line", { x1: 14, x2: 14, y1: 18, y2: 11 }], ["line", { x1: 18, x2: 18, y1: 18, y2: 11 }], ["polygon", { points: "12 2 20 7 4 7" }]],
  "trending-up": [["polyline", { points: "22 7 13.5 15.5 8.5 10.5 2 17" }], ["polyline", { points: "16 7 22 7 22 13" }]],
  "trending-down": [["polyline", { points: "22 17 13.5 8.5 8.5 13.5 2 7" }], ["polyline", { points: "16 17 22 17 22 11" }]],
  "building-2": [["path", { d: "M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z" }], ["path", { d: "M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" }], ["path", { d: "M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2" }], ["path", { d: "M10 6h4" }], ["path", { d: "M10 10h4" }], ["path", { d: "M10 14h4" }], ["path", { d: "M10 18h4" }]],
  scale: [["path", { d: "m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" }], ["path", { d: "m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" }], ["path", { d: "M7 21h10" }], ["path", { d: "M12 3v18" }], ["path", { d: "M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2" }]],
  globe: [["circle", { cx: 12, cy: 12, r: 10 }], ["path", { d: "M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" }], ["path", { d: "M2 12h20" }]],
  droplet: [["path", { d: "M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z" }]],
  sprout: [["path", { d: "M7 20h10" }], ["path", { d: "M10 20c5.5-2.5.8-6.4 3-10" }], ["path", { d: "M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8z" }], ["path", { d: "M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z" }]],
  briefcase: [["rect", { width: 20, height: 14, x: 2, y: 7, rx: 2, ry: 2 }], ["path", { d: "M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" }]],
  "alert-triangle": [["path", { d: "m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" }], ["path", { d: "M12 9v4" }], ["path", { d: "M12 17h.01" }]],
  clock: [["circle", { cx: 12, cy: 12, r: 10 }], ["polyline", { points: "12 6 12 12 16 14" }]],
  "circle-dot": [["circle", { cx: 12, cy: 12, r: 10 }], ["circle", { cx: 12, cy: 12, r: 1 }]],
};

// label THEME → icon, first match wins. Ordered so specific themes (corporations,
// education) beat the generic money bucket, which otherwise swallows any report
// that mentions dollars.
const RULES = [
  [/school|educat|\blearn|teacher|classroom|student|literac|graduat|curricul|pupil/, "graduation-cap"],
  [/corporat|compan|business|\bceo\b|shareholder|\bfirm|industr|monopol/, "building-2"],
  [/health|hospital|medical|patient|nurse|doctor|mental|disease|mortalit/, "heart-pulse"],
  [/climate|carbon|emission|greenhouse|environment|\benergy|pollut|warming|renewable/, "leaf"],
  [/\bhome\b|housing|shelter|\brent\b|mortgage|tenant|homeowner/, "house"],
  [/government|policy|\bstate\b|govern|\bnation|\blaw\b|justice|court|democra|\bvote|elect/, "landmark"],
  [/inequalit|\bgap\b|divide|dispar|equit|imbalance/, "scale"],
  [/food|farm|agricultur|\bcrop|hunger|nutrit|harvest/, "sprout"],
  [/water|ocean|river|drought|drink/, "droplet"],
  [/global|world|countr|internationa|planet/, "globe"],
  [/\bjob|employ|\bwork|labou?r|staff|workforce/, "briefcase"],
  [/\$|money|wealth|dollar|\btn\b|\bbn\b|\bpay\b|income|\bcost|\bfund|invest|gdp|financ|profit|salar|wage|earn|revenue|budget/, "banknote"],
  [/people|population|\bchildren|\bwomen|\bmen\b|household|famil|adult|resident|citizen|individual|person/, "users"],
  [/increas|\bgrow|\brise|rising|surg|doubl|higher|expand/, "trending-up"],
  [/declin|decreas|\bfall|\bdrop|\bloss|\blost|lower|reduc|shrink/, "trending-down"],
];

const strip = (s) => String(s || "").replace(/<[^>]+>/g, " ");

export function pickStatIcon(value, label) {
  const v = String(value || "").toLowerCase();
  const text = `${v} ${strip(label)}`.toLowerCase();
  // alarming stats first
  if (/traum|abuse|violen|suspend|expel|crisis|homeless|insecur/.test(text)) return "alert-triangle";
  // the VALUE's own unit is the headline (476 YEARS -> time, $105tn -> money)
  if (/\d[\d.,]*\s*(years?|yrs?|days?|hours?|months?|decades?|weeks?)\b/.test(v)) return "hourglass";
  if (/[$£€]|\d[\d.,]*\s*(tn|bn|trillion)\b/.test(v)) return "banknote";
  // then the label's theme
  for (const [re, name] of RULES) if (re.test(text)) return name;
  if (/%/.test(v)) return "percent";
  return "circle-dot";
}

export function StatIcon({ value, label, name, size = "1.35em" }) {
  const key = name || pickStatIcon(value, label);
  const data = ICONS[key] || ICONS["circle-dot"];
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
      style={{ display: "block", flex: "none" }}>
      {data.map(([tag, attrs], i) => React.createElement(tag, { key: i, ...attrs }))}
    </svg>
  );
}
