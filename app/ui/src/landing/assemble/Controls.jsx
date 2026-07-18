import React, { useEffect, useRef, useState } from "react";
import { t } from "../../content.js";
import { COVERS, pageWords, WC_SHORT, WC_LONG } from "./model.js";
import { Icon } from "./icons.jsx";

const shortLabel = (h) => (h && h.length > 18 ? h.slice(0, 17).trim() + "…" : (h || ""));

// Right column: the Cover control + a page word-count read (with zones), the
// grayscale outline of the page (cover layout + the on-sections + CTA), and the
// nudge toward Wordsmith.
export default function Controls({ cover, onCover, accent, onAccent, sections, cta, ai, onWordsmith }) {
  const rows = buildRows(sections, cta, ai, cover);
  const words = pageWords(sections, ai);
  return (
    <div className="asm-col asm-col-right">
      <div className="asm-controls">
        <Dropdown
          category={t("lpm.cover.category")} value={cover} options={COVERS} onPick={onCover}
          label={(id) => t(`lpm.cover.${id}.title`)} advice={(id) => t(`lpm.cover.${id}.line`)}
          glyph={<CoverGlyph id={cover} />} optionGlyph={(id) => <CoverGlyph id={id} />}
        />
      </div>

      <div className="asm-rail-row">
        <WordCountBar words={words} />
        <AccentPicker accent={accent} onAccent={onAccent} />
      </div>

      <div className="asm-page-head">
        <span className="asm-page-head-title">{t("lpm.assemble.page_heading")}</span>
      </div>

      <div className="asm-page">
        <CoverSkeleton cover={cover} />
        {rows.length === 0 && <div className="asm-page-empty">Your page is empty — add a section</div>}
        {rows.map((s, i) => (
          <div key={i} className="asm-pp-sec">
            <span className="asm-pp-label">{s.label}</span>
            <SectionSkeleton section={s} />
          </div>
        ))}
      </div>

      <div className="asm-nudge">
        <Icon name="pencil-line" size={16} style={{ marginTop: 1, flex: "none" }} />
        <button type="button" className="asm-nudge-btn" onClick={onWordsmith}>
          {t("lpm.assemble.wordsmith_nudge")}
        </button>
      </div>
    </div>
  );
}

// AI summary (if on) + on-sections + CTA -> rough-page rows
function buildRows(sections, cta, ai, cover) {
  // boxed/band covers carry the download button themselves, so it isn't also
  // repeated in the foot CTA row
  const coverHasDownload = cta.download && (cover === "floatBoxed" || cover === "band");
  const out = [];
  if (ai && ai.on) out.push({ label: ai.heading || t("lpm.sections.ai.heading"), kind: "text" });
  for (const s of sections) {
    if (!s.on) continue;
    const label = shortLabel(s.heading);
    if (s.presentation === "statCards") out.push({ label, kind: "stats", cols: Math.min(Math.max((s.cards || []).length, 1), 4) });
    else if (s.presentation === "bullets") out.push({ label, kind: "bullets" });
    else if (s.presentation === "quote") out.push({ label, kind: "story" });
    else if (s.presentation === "steps") out.push({ label, kind: "steps", n: Math.min((s.steps || []).length || 3, 4) });
    else out.push({ label, kind: "text" });
  }
  const footDownload = cta.download && !coverHasDownload;
  const parts = [];
  if (footDownload) parts.push("Download");
  if (cta.secondary) parts.push("action");
  if (cta.share) parts.push("share");
  if (footDownload || cta.secondary || cta.share) {
    out.push({ label: parts.join(" + "), kind: "cta", download: footDownload, secondary: cta.secondary, social: cta.share });
  }
  return out;
}

function SectionSkeleton({ section }) {
  if (section.kind === "stats") {
    return (
      <div className="asm-pp-stats">
        {Array.from({ length: section.cols }).map((_, i) => (
          <div key={i} className="asm-pp-stat">
            <div className="asm-pp-stat-n" />
            <div className="asm-pp-row" style={{ marginTop: 4 }} />
            <div className="asm-pp-row" style={{ marginTop: 3, maxWidth: "80%" }} />
          </div>
        ))}
      </div>
    );
  }
  if (section.kind === "bullets") {
    return (
      <div className="asm-pp-rows">
        {[85, 70, 78].map((w, i) => (
          <div key={i} className="asm-pp-bullet">
            <span className="asm-pp-dot" />
            <span className="asm-pp-row" style={{ flex: 1, maxWidth: `${w}%` }} />
          </div>
        ))}
      </div>
    );
  }
  if (section.kind === "steps") {
    return (
      <div className="asm-pp-rows">
        {Array.from({ length: section.n }).map((_, i) => (
          <div key={i} className="asm-pp-bullet">
            <span style={{ width: 8, height: 8, borderRadius: "50%", border: "1.5px solid #999", flex: "none" }} />
            <span className="asm-pp-row" style={{ flex: 1, maxWidth: "82%" }} />
          </div>
        ))}
      </div>
    );
  }
  if (section.kind === "story") {
    return (
      <div className="asm-pp-rows">
        <span className="asm-pp-row" style={{ height: 7, width: "88%" }} />
        <span className="asm-pp-row" style={{ height: 7, width: "60%" }} />
        <span className="asm-pp-row" style={{ width: "40%", background: "#aaa", marginTop: 2 }} />
      </div>
    );
  }
  if (section.kind === "cta") {
    return (
      <div className="asm-pp-cta">
        {section.download && <div className="asm-pp-cta-primary" />}
        {section.secondary && <div className="asm-pp-cta-secondary" />}
        {section.social && (
          <div className="asm-pp-cta-social">
            <span className="asm-pp-social-dot" /><span className="asm-pp-social-dot" /><span className="asm-pp-social-dot" />
          </div>
        )}
      </div>
    );
  }
  // text (prose)
  return (
    <div className="asm-pp-rows">
      <div className="asm-pp-row" /><div className="asm-pp-row" />
      <div className="asm-pp-row" style={{ width: "72%" }} />
    </div>
  );
}

// The title always leads full width; the cover then floats into the first summary
// (float / boxed) or sits in a shaded band after it.
function CoverSkeleton({ cover }) {
  const title = (
    <div style={{ display: "flex", flexDirection: "column", gap: 5, marginBottom: 12 }}>
      <div className="asm-pp-line" style={{ height: 12 }} />
      <div className="asm-pp-line" style={{ height: 12, width: "62%" }} />
      <div className="asm-pp-faint" style={{ height: 4, width: "45%", marginTop: 5 }} />
    </div>
  );
  const wrapLines = (n, cutAt) => (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} className="asm-pp-row" style={{ width: i >= cutAt ? "100%" : "88%" }} />
      ))}
    </div>
  );
  const shaded = { background: "var(--rk-rhino-50, #eef1f7)", border: "1px solid var(--rk-border)", borderRadius: 6 };
  const button = { height: 9, borderRadius: 3, background: "var(--lp-accent, #1E3A5F)", marginTop: 6 };

  if (cover === "band") {
    return (
      <div style={{ marginBottom: 14 }}>
        {title}
        <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 10 }}>
          {[100, 100, 70].map((w, i) => <div key={i} className="asm-pp-row" style={{ width: `${w}%` }} />)}
        </div>
        <div style={{ ...shaded, display: "flex", gap: 10, padding: 8 }}>
          <div style={{ width: "24%", flex: "none" }}>
            <div className="asm-pp-cover" style={{ width: "100%", aspectRatio: "3 / 4", fontSize: 0 }} />
            <div style={button} />
          </div>
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 4, paddingTop: 3 }}>
            <div className="asm-pp-line" style={{ height: 9 }} />
            <div className="asm-pp-faint" style={{ height: 4, width: "55%" }} />
          </div>
        </div>
      </div>
    );
  }
  // floatRight / floatBoxed — cover floats into the summary at right, text wraps
  const boxed = cover === "floatBoxed";
  return (
    <div style={{ marginBottom: 14 }}>
      {title}
      <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
        {wrapLines(6, 3)}
        <div style={{ width: "36%", flex: "none", ...(boxed ? { ...shaded, padding: 6 } : {}) }}>
          <div className="asm-pp-cover" style={{ width: "100%", aspectRatio: "3 / 4", fontSize: 0 }} />
          {boxed && <div style={button} />}
        </div>
      </div>
    </div>
  );
}

function Dropdown({ category, value, options, onPick, label, advice, glyph, optionGlyph }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);
  return (
    <div className={"asm-select" + (open ? " is-open" : "")} ref={ref}>
      <button type="button" className="asm-select-trigger" onClick={() => setOpen((o) => !o)}>
        <span className="asm-select-glyph">{glyph}</span>
        <span className="asm-select-body">
          <span className="asm-select-label"><span className="asm-select-cat">{category} ·</span> <b>{label(value)}</b></span>
          <span className="asm-select-advice">{advice(value)}</span>
        </span>
        <Icon name={open ? "chevron-up" : "chevron-down"} size={15} className="asm-select-chev" />
      </button>
      {open && (
        <div className="asm-select-menu">
          {options.map((id) => (
            <button key={id} type="button" className="asm-select-opt" onClick={() => { onPick(id); setOpen(false); }}>
              {optionGlyph && <span className="asm-select-glyph">{optionGlyph(id)}</span>}
              <span style={{ flex: 1, minWidth: 0, textAlign: "left" }}>
                <span className="asm-select-opt-name" style={{ display: "block" }}>{label(id)}</span>
                <span className="asm-select-opt-advice" style={{ display: "block" }}>{advice(id)}</span>
              </span>
              {value === id && <Icon name="check" size={14} className="asm-select-opt-check" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// One settable accent — a single custom colour box (no palette presets; nobody
// wants RK's brand colours as their own accent). Drives --lp-accent, which every
// treatment/link/share reads.
function AccentPicker({ accent, onAccent }) {
  return (
    <div className="asm-accent">
      <span className="asm-accent-label">{t("lpm.length.accent_label")}</span>
      <label className="asm-accent-box" title={t("lpm.length.accent_pick")}>
        <span className="asm-accent-chip" style={{ background: accent }} />
        <span className="asm-accent-hex">{(accent || "").toUpperCase()}</span>
        <input type="color" value={accent} onChange={(e) => onAccent(e.target.value)} />
      </label>
    </div>
  );
}

// Total page words with a zone read (a bit short / good length / a bit long) —
// the guidance that replaces the blunt short/middle/long control.
function WordCountBar({ words }) {
  const zone = words < WC_SHORT ? "short" : words > WC_LONG ? "long" : "good";
  const good = zone === "good";
  const max = WC_LONG * 1.35;
  const clamp = (v) => Math.max(0, Math.min(100, v));
  const pct = clamp((words / max) * 100);
  const shortPct = (WC_SHORT / max) * 100;
  const longPct = (WC_LONG / max) * 100;
  return (
    <div className="asm-wc">
      <div className="asm-wc-head">
        <span className="asm-wc-label">{t("lpm.length.wordcount_label")}</span>
        <span className={"asm-wc-read" + (good ? " is-good" : " is-off")}>
          {t("lpm.length.words", { n: words })} · {t(`lpm.length.zone.${zone}`)}
        </span>
      </div>
      <div className="asm-wc-track">
        <div className="asm-wc-good" style={{ left: `${shortPct}%`, width: `${longPct - shortPct}%` }} />
        <div className={"asm-wc-marker" + (good ? " is-good" : " is-off")} style={{ left: `${pct}%` }} />
      </div>
    </div>
  );
}

// A mini page: title lines on top (full width), then the layout-specific cover.
function CoverGlyph({ id }) {
  const bar = { background: "var(--rk-gray-200)", borderRadius: 1, height: 2.5 };
  const rhino = { background: "var(--rk-rhino-300)", borderRadius: 1 };
  const titleRows = (
    <>
      <span style={{ ...bar, height: 3, background: "var(--rk-rhino-300)" }} />
      <span style={{ ...bar, height: 3, width: "60%", background: "var(--rk-rhino-300)" }} />
    </>
  );
  if (id === "band") {
    // title, a line or two, then a shaded band with a tiny cover
    return (
      <span style={{ width: 30, display: "flex", flexDirection: "column", gap: 2 }}>
        {titleRows}
        <span style={{ ...bar }} />
        <span style={{ display: "flex", gap: 2, padding: 1.5, background: "var(--rk-rhino-50, #eef1f7)", borderRadius: 2 }}>
          <span style={{ ...rhino, width: 6, height: 8, flex: "none" }} />
          <span style={{ flex: 1, display: "flex", flexDirection: "column", gap: 1.5, justifyContent: "center" }}>
            <span style={bar} /><span style={{ ...bar, width: "70%" }} />
          </span>
        </span>
      </span>
    );
  }
  // floatRight / floatBoxed — title, then lines wrapping a small cover at right
  const boxed = id === "floatBoxed";
  return (
    <span style={{ width: 30, display: "flex", flexDirection: "column", gap: 2 }}>
      {titleRows}
      <span style={{ display: "flex", gap: 2, marginTop: 1 }}>
        <span style={{ flex: 1, display: "flex", flexDirection: "column", gap: 1.5 }}>
          <span style={bar} /><span style={bar} /><span style={{ ...bar, width: "85%" }} />
        </span>
        <span style={boxed
          ? { flex: "none", padding: 1, background: "var(--rk-rhino-50, #eef1f7)", borderRadius: 2, display: "flex" }
          : { display: "flex" }}>
          <span style={{ ...rhino, width: 8, height: 10, flex: "none" }} />
        </span>
      </span>
    </span>
  );
}
