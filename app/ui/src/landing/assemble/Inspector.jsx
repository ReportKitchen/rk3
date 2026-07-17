import React, { useEffect, useMemo, useRef, useState } from "react";
import { t } from "../../content.js";
import { getAiSummary } from "../../api.js";
import { SUMMARY_LENGTH } from "./model.js";
import { Icon, BLOCK_ICONS } from "./icons.jsx";

const VOICES = ["intro", "neutral", "hardsell"];

const itemText = (it) => (typeof it === "string" ? it : (it?.value || it?.text || ""));
const wordCount = (s) => (String(s || "").replace(/<[^>]+>/g, " ").trim().match(/\S+/g) || []).length;
// a short label for a (sometimes long) story subject: first clause + page
function shortSubject(s) {
  const base = (s.subject || s.attribution || "").split(/[—,·]/)[0].trim();
  return base.length > 26 ? base.slice(0, 25).trim() + "…" : base;
}

// Center column: inspect one block — see it "as it will appear", make its
// choices (which facts, which voice, whose story), and add/remove it.
export default function Inspector({
  slug, sel, guidance, blockDefaults, added, onToggle, length, pages,
  stats, checkedFacts, setCheckedFacts, onAddOwnFact,
  voice, setVoice, stories, person, setPerson,
}) {
  const isAdded = added.has(sel);
  const defs = blockDefaults || {};

  // ---- AI summary text (lazy, cached by voice:length) ----
  const [aiText, setAiText] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const aiCache = useRef(new Map());
  useEffect(() => {
    if (sel !== "aiSummary") return;
    const slen = SUMMARY_LENGTH[length] || "medium";
    const key = `${voice}:${slen}`;
    const cached = aiCache.current.get(key);
    if (cached !== undefined) { setAiText(cached); setAiLoading(false); return; }
    let alive = true;
    setAiLoading(true);
    getAiSummary(slug, voice, slen)
      .then((text) => { if (!alive) return; aiCache.current.set(key, text || ""); setAiText(text || ""); })
      .catch(() => { if (alive) setAiText(""); })
      .finally(() => { if (alive) setAiLoading(false); });
    return () => { alive = false; };
  }, [sel, voice, length, slug]);

  const pickedFacts = useMemo(
    () => checkedFacts.map((i) => stats[i]).filter(Boolean),
    [checkedFacts, stats]);
  const over = pickedFacts.length > 5;
  const curStory = stories[person] || stories[0] || null;

  const toggleFact = (i) =>
    setCheckedFacts((prev) => (prev.includes(i) ? prev.filter((x) => x !== i) : [...prev, i]));

  return (
    <div className="asm-col asm-col-mid">
      <div className="asm-insp-head">
        <span className="asm-insp-icon"><Icon name={BLOCK_ICONS[sel]} size={20} /></span>
        <div style={{ flex: 1 }}>
          <div className="asm-insp-name">{t(`lpm.blocks.${sel}.name`)}</div>
        </div>
        {isAdded ? (
          <button type="button" className="asm-btn-remove" onClick={() => onToggle(sel)}>
            <Icon name="minus" size={13} />{t("lpm.inspector.remove")}
          </button>
        ) : (
          <button type="button" className="asm-btn-add" onClick={() => onToggle(sel)}>
            <Icon name="plus" size={13} />{t("lpm.inspector.add")}
          </button>
        )}
      </div>
      <p className="asm-insp-blurb">
        {t(`lpm.blocks.${sel}.what`)} {t(`lpm.blocks.${sel}.when`)}
      </p>

      {/* per-block choices, above the preview */}
      {sel === "aiSummary" && (
        <div className="asm-chips">
          {VOICES.map((v) => (
            <button
              key={v} type="button"
              className={"asm-chip" + (voice === v ? " is-active" : "")}
              onClick={() => setVoice(v)}
            >
              {t(`lpm.inspector.voice.${v}.label`)}{" "}
              <span className="asm-chip-desc">— {t(`lpm.inspector.voice.${v}.note`)}</span>
            </button>
          ))}
        </div>
      )}
      {sel === "storytelling" && stories.length > 0 && (
        <div className="asm-chips">
          {stories.map((s, i) => (
            <button
              key={i} type="button"
              className={"asm-chip asm-chip-person" + (person === i ? " is-active" : "")}
              onClick={() => setPerson(i)}
            >
              {shortSubject(s)}{s.page ? ` · ${s.page}` : ""}
            </button>
          ))}
        </div>
      )}

      <div className="asm-eyebrow">{t("lpm.inspector.preview_label")}</div>
      <div className="asm-preview">
        <Preview
          sel={sel} defs={defs} aiText={aiText} aiLoading={aiLoading} voice={voice}
          pickedFacts={pickedFacts} story={curStory}
        />
      </div>

      {/* Findings: the fact-picker lives here (a user fact is just another item) */}
      {sel === "findings" && (
        <FactPicker
          stats={stats} checkedFacts={checkedFacts} onToggle={toggleFact}
          over={over} onAddOwnFact={onAddOwnFact}
        />
      )}
    </div>
  );
}

// The "as it will appear" sample, per block.
function Preview({ sel, defs, aiText, aiLoading, voice, pickedFacts, story }) {
  if (sel === "execSummary") {
    const chunks = defs.docSummary?.blocks || [];
    const html = chunks[0] || defs.summary?.text || "";
    return (
      <>
        <div className="asm-pv-ai" dangerouslySetInnerHTML={{ __html: html }} />
        <p className="asm-pv-meta">{t("lpm.inspector.exec.meta")}</p>
      </>
    );
  }
  if (sel === "aiSummary") {
    if (aiLoading) return <p className="asm-pv-loading">{t("lpm.inspector.loading")}</p>;
    return (
      <>
        <p className="asm-pv-ai">{aiText || defs.summary?.text || ""}</p>
        <p className="asm-pv-meta">{t("lpm.inspector.voice.meta", { words: wordCount(aiText) })}</p>
      </>
    );
  }
  if (sel === "highlights") {
    const items = (defs.highlights?.items || []).map(itemText).filter(Boolean);
    return (
      <>
        {defs.highlights?.heading && <div className="asm-pv-h-sm">{defs.highlights.heading}</div>}
        <ul className="asm-pv-bullets">{items.map((it, i) => <li key={i}>{it}</li>)}</ul>
      </>
    );
  }
  if (sel === "findings") {
    return (
      <>
        {defs.findings?.heading && <div className="asm-pv-h">{defs.findings.heading}</div>}
        {pickedFacts.length === 0
          ? <p className="asm-pv-empty">Nothing picked — check a number below to see it here.</p>
          : (
            <div className="asm-pv-findings">
              {pickedFacts.slice(0, 6).map((f, i) => (
                <div key={i}>
                  <div className="asm-pv-finding-n">{f.value}</div>
                  <div className="asm-pv-finding-t">{f.fact}</div>
                </div>
              ))}
            </div>
          )}
      </>
    );
  }
  if (sel === "toc") {
    const items = defs.toc?.items || [];
    return (
      <>
        <div className="asm-pv-h-sm">Inside the report</div>
        <div className="asm-pv-toc">
          {items.map((it, i) => <div key={i}>{it.text}</div>)}
        </div>
      </>
    );
  }
  if (sel === "storytelling") {
    if (!story) return <p className="asm-pv-empty">No story found in this document.</p>;
    return (
      <>
        {story.quote && <p className="asm-pv-story-quote">“{story.quote}”</p>}
        {story.narrative && <p className="asm-pv-story-body">{story.narrative}</p>}
        {story.attribution && <p className="asm-pv-story-attr">{story.attribution}{story.page ? ` · ${story.page}` : ""}</p>}
      </>
    );
  }
  if (sel === "download") {
    return (
      <div className="asm-pv-cta">
        <span className="asm-pv-cta-primary">{defs.download?.label || "Download the report (PDF)"}</span>
      </div>
    );
  }
  if (sel === "secondary") {
    return (
      <div className="asm-pv-cta">
        <span className="asm-pv-cta-secondary">{defs.secondaryCta?.label || "Learn more"}</span>
        <span className="asm-pv-cta-note">label + link are yours to set</span>
      </div>
    );
  }
  if (sel === "share") {
    return (
      <div className="asm-pv-cta">
        <span style={{ fontSize: 14, color: "#333" }}>Share:</span>
        {["LinkedIn", "Bluesky", "Email"].map((n) => <span key={n} className="asm-pv-share-chip">{n}</span>)}
      </div>
    );
  }
  return null;
}

// Findings fact-picker: checkboxes over the doc's stats, with pages shown, a
// 3–5 cap that turns tomato when exceeded, and an "add your own" row (a user
// fact is just another {value, fact, page} item).
function FactPicker({ stats, checkedFacts, onToggle, over, onAddOwnFact }) {
  const [showForm, setShowForm] = useState(false);
  const [stat, setStat] = useState("");
  const [text, setText] = useState("");
  const save = () => {
    if (!stat.trim() && !text.trim()) return;
    onAddOwnFact({ value: stat.trim(), fact: text.trim(), page: "" });
    setStat(""); setText(""); setShowForm(false);
  };
  return (
    <>
      <div className="asm-facts-head">
        <span className="asm-facts-title">{t("lpm.inspector.findings.heading", { n: stats.length })}</span>
        <span className={"asm-facts-cap" + (over ? " is-over" : "")}>
          {t("lpm.inspector.findings.picked", { n: checkedFacts.length })}
        </span>
      </div>
      <p className="asm-facts-hint">{t("lpm.inspector.findings.pick_hint")}</p>
      <div className="asm-facts-grid">
        {stats.map((f, i) => {
          const checked = checkedFacts.includes(i);
          return (
            <button
              key={i} type="button"
              className={"asm-fact" + (checked ? " is-checked" : "")}
              onClick={() => onToggle(i)}
            >
              <span className="asm-fact-grip" aria-hidden="true">⠿</span>
              <span className="asm-fact-box">{checked && <Icon name="check" size={11} />}</span>
              <span className="asm-fact-text"><b>{f.value}</b> {f.fact}</span>
              {f.page && <span className="asm-fact-page">{f.page}</span>}
            </button>
          );
        })}
        {showForm ? (
          <div className="asm-fact-own-form">
            <input className="asm-own-stat" value={stat} placeholder={t("lpm.inspector.findings.own_stat_ph")}
              onChange={(e) => setStat(e.target.value)} autoFocus />
            <input className="asm-own-text" value={text} placeholder={t("lpm.inspector.findings.own_text_ph")}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && save()} />
            <button type="button" className="asm-btn-add" onClick={save}>{t("lpm.inspector.findings.own_save")}</button>
          </div>
        ) : (
          <button type="button" className="asm-fact-own" onClick={() => setShowForm(true)}>
            {t("lpm.inspector.findings.add_own")}
          </button>
        )}
      </div>
    </>
  );
}
