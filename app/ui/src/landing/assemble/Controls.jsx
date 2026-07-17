import React, { useEffect, useRef, useState } from "react";
import { t } from "../../content.js";
import { LENGTHS, COVERS } from "./model.js";
import { Icon } from "./icons.jsx";

const shortLabel = (h) => (h && h.length > 18 ? h.slice(0, 17).trim() + "…" : (h || ""));

// Right column: the two page-shape controls (Length, Cover), the grayscale "rough
// draft" of the page (cover layout + the on-sections + CTA), and the nudge toward
// Wordsmith.
export default function Controls({ length, cover, onLength, onCover, sections, cta, onWordsmith }) {
  const rows = buildRows(sections, cta);
  return (
    <div className="asm-col asm-col-right">
      <div className="asm-controls">
        <Dropdown
          category={t("lpm.length.category")} value={length} options={LENGTHS} onPick={onLength}
          label={(id) => t(`lpm.length.${id}.title`)} advice={(id) => t(`lpm.length.${id}.promise`)}
          glyph={<LengthGlyph />}
        />
        <Dropdown
          category={t("lpm.cover.category")} value={cover} options={COVERS} onPick={onCover}
          label={(id) => t(`lpm.cover.${id}.title`)} advice={(id) => t(`lpm.cover.${id}.line`)}
          glyph={<CoverGlyph id={cover} />} optionGlyph={(id) => <CoverGlyph id={id} />}
        />
      </div>

      <div className="asm-page-head">
        <span className="asm-page-head-title">{t("lpm.assemble.page_heading")}</span>
        <span className="asm-page-head-note">{t("lpm.assemble.rough_draft_label")}</span>
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
        <div className="asm-page-foot">{t("lpm.assemble.rough_draft_note")}</div>
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

// on-sections + CTA -> rough-page rows
function buildRows(sections, cta) {
  const out = [];
  for (const s of sections) {
    if (!s.on) continue;
    const label = shortLabel(s.heading);
    if (s.presentation === "statCards") out.push({ label, kind: "stats", cols: Math.min(Math.max((s.cards || []).length, 1), 4) });
    else if (s.presentation === "bullets") out.push({ label, kind: "bullets" });
    else if (s.presentation === "quote") out.push({ label, kind: "story" });
    else if (s.presentation === "steps") out.push({ label, kind: "steps", n: Math.min((s.steps || []).length || 3, 4) });
    else out.push({ label, kind: "text" });
  }
  const parts = [];
  if (cta.download) parts.push("Download");
  if (cta.secondary) parts.push("action");
  if (cta.share) parts.push("share");
  if (cta.download || cta.secondary || cta.share) {
    out.push({ label: parts.join(" + "), kind: "cta", download: cta.download, secondary: cta.secondary, social: cta.share });
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

function CoverSkeleton({ cover }) {
  if (cover === "beside") {
    return (
      <div style={{ display: "flex", gap: 12, marginBottom: 14 }}>
        <div className="asm-pp-cover" style={{ width: "42%", aspectRatio: "3 / 4" }}>COVER</div>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 5, paddingTop: 4 }}>
          <div className="asm-pp-line" style={{ height: 11 }} />
          <div className="asm-pp-line" style={{ height: 11, width: "70%" }} />
          <div className="asm-pp-faint" style={{ height: 4, width: "55%", marginTop: 6 }} />
        </div>
      </div>
    );
  }
  if (cover === "onTop") {
    return (
      <div style={{ marginBottom: 14 }}>
        <div className="asm-pp-cover" style={{ height: 64, marginBottom: 8 }}>COVER</div>
        <div className="asm-pp-line" style={{ height: 11, marginBottom: 5 }} />
        <div className="asm-pp-line" style={{ height: 11, width: "70%" }} />
      </div>
    );
  }
  if (cover === "inset") {
    return (
      <div style={{ marginBottom: 14 }}>
        <div className="asm-pp-line" style={{ height: 11, marginBottom: 5 }} />
        <div className="asm-pp-line" style={{ height: 11, width: "65%", marginBottom: 9 }} />
        <div style={{ display: "flex", gap: 10 }}>
          <div className="asm-pp-cover" style={{ width: "30%", aspectRatio: "3 / 4", fontSize: 8, flex: "none" }}>COVER</div>
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 5 }}>
            {["100%", "100%", "85%", "60%"].map((w, i) => <div key={i} className="asm-pp-faint" style={{ height: 5, width: w }} />)}
          </div>
        </div>
      </div>
    );
  }
  return (
    <div style={{ marginBottom: 14 }}>
      <div className="asm-pp-line" style={{ height: 11, marginBottom: 5 }} />
      <div className="asm-pp-line" style={{ height: 11, width: "70%", marginBottom: 8 }} />
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <div style={{ width: 22, height: 29, background: "#c9ccd4", borderRadius: 1, flex: "none" }} />
        <div className="asm-pp-faint" style={{ height: 4, flex: 1, maxWidth: "55%" }} />
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

function LengthGlyph() {
  return (
    <span style={{ width: 30, display: "flex", flexDirection: "column", gap: 2.5 }}>
      <span style={{ height: 4, background: "var(--rk-rhino-300)", borderRadius: 2 }} />
      <span style={{ height: 4, background: "var(--rk-rhino-300)", borderRadius: 2, width: "75%" }} />
      <span style={{ height: 4, background: "var(--rk-rhino-300)", borderRadius: 2, width: "50%" }} />
    </span>
  );
}

function CoverGlyph({ id }) {
  const bar = { background: "var(--rk-gray-200)", borderRadius: 1, height: 3 };
  const rhino = { background: "var(--rk-rhino-300)", borderRadius: 1 };
  if (id === "onTop") {
    return (
      <span style={{ width: 30, display: "flex", flexDirection: "column", gap: 2 }}>
        <span style={{ ...rhino, height: 9 }} /><span style={bar} /><span style={{ ...bar, width: "70%" }} />
      </span>
    );
  }
  if (id === "inset") {
    return (
      <span style={{ width: 30, display: "flex", gap: 2 }}>
        <span style={{ ...rhino, width: 9, height: 11, flex: "none" }} />
        <span style={{ flex: 1, display: "flex", flexDirection: "column", gap: 2 }}>
          <span style={bar} /><span style={bar} /><span style={{ ...bar, width: "80%" }} />
        </span>
      </span>
    );
  }
  if (id === "textForward") {
    return (
      <span style={{ width: 30, display: "flex", flexDirection: "column", gap: 2 }}>
        <span style={{ ...rhino, height: 4 }} /><span style={bar} /><span style={bar} /><span style={{ ...bar, width: "65%" }} />
      </span>
    );
  }
  return (
    <span style={{ width: 30, display: "flex", gap: 2 }}>
      <span style={{ ...rhino, width: 13, height: 16, flex: "none" }} />
      <span style={{ flex: 1, display: "flex", flexDirection: "column", gap: 2, justifyContent: "center" }}>
        <span style={bar} /><span style={{ ...bar, width: "80%" }} />
      </span>
    </span>
  );
}
