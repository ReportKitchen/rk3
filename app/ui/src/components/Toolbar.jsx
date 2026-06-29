import React, { useEffect, useState } from "react";

// "15 min ago" style age from an ISO timestamp
function relAge(iso) {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  const s = Math.max(0, (Date.now() - t) / 1000);
  if (s < 60) return "just now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} hr${h > 1 ? "s" : ""} ago`;
  const d = Math.floor(h / 24);
  return `${d} day${d > 1 ? "s" : ""} ago`;
}

// full local "YYYY-MM-DD HH:MM am/pm" for the hover tooltip
function fullStamp(iso) {
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return "";
  const p = (n) => String(n).padStart(2, "0");
  let h = dt.getHours();
  const ap = h < 12 ? "am" : "pm";
  h = h % 12 || 12;
  return `${dt.getFullYear()}-${p(dt.getMonth() + 1)}-${p(dt.getDate())} `
    + `${p(h)}:${p(dt.getMinutes())} ${ap}`;
}

// top bar: document name, plus how fresh the current build is. The age + pill
// answer "am I looking at the latest?" — the pill is driven by a server-side
// fingerprint comparison (code + config + source), not just a version number.
export default function Toolbar({ doc, build }) {
  // re-render every 30s so the relative age keeps ticking between polls
  const [, tick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => tick((n) => n + 1), 30000);
    return () => clearInterval(id);
  }, []);

  const finished = build?.finished;
  const age = finished ? relAge(finished) : null;
  const stamp = finished ? fullStamp(finished) : "";
  const versions = (build?.stages || []).map((s) => `${s.stage} v${s.version}`).join(" · ");
  const building = doc.status === "in_progress" || build?.status === "in_progress";

  let pill = null;
  if (build?.fetchError) {
    // don't hide a missing/old server behind a blank toolbar — say so
    pill = { cls: "error", label: "⚠ status unavailable",
             tip: `Couldn't reach /api/build-status: ${build.fetchError}.\n`
                + `Is the server running the latest code? (restart if it predates a change)` };
  } else if (build?.status === "failed") {
    pill = { cls: "error", label: "✗ build failed",
             tip: build.error || "Conversion failed — see the error banner / convert log." };
  } else if (building) {
    pill = { cls: "building", label: "● building…", tip: "A conversion is running" };
  } else if (build?.up_to_date) {
    pill = { cls: "current", label: "✓ current",
             tip: `Built from the current code, config & source.\n${versions}` };
  } else if (build?.stale?.length) {
    pill = { cls: "stale", label: "⚠ stale",
             tip: `Behind current code in: ${build.stale.join(", ")}. `
                + `Reconvert to update.\n${versions}` };
  }

  return (
    <div id="toolbar">
      <span id="docname">{doc.name}</span>
      {age && (
        <span className="build-age" title={`Last build: ${stamp}\n${versions}`}>
          last build: {age}
        </span>
      )}
      {pill && (
        <span className={"build-pill " + pill.cls} title={pill.tip}>{pill.label}</span>
      )}
    </div>
  );
}
