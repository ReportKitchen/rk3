import React, { useEffect } from "react";
import { t } from "../../content.js";
import { LandingRenderer } from "../LandingRenderer.jsx";
import { PRESENTATIONS } from "./model.js";
import { Icon, BLOCK_ICONS } from "./icons.jsx";

const VOICES = ["intro", "neutral", "hardsell"];

// Center column: inspect one thing — a content section, the AI Summary, or a CTA —
// see it rendered exactly "as it will appear" (the real block components), read
// why it earns a place, adjust how it looks, and add/remove it.
export default function Inspector({
  sel, sections, cta, ai, defs, slug, length,
  onToggleSection, onToggleCta, onSetPresentation, onSetQuotePull, onToggleAi, onAiVoice,
}) {
  if (sel === "ai-summary") {
    return <AiInspector ai={ai} onToggle={onToggleAi} onVoice={onAiVoice} />;
  }
  const section = sections.find((s) => s.id === sel);
  if (section) {
    return (
      <SectionInspector
        section={section}
        onToggle={() => onToggleSection(section.id)}
        onSetQuotePull={(pull) => onSetQuotePull(section.id, pull)}
      />
    );
  }
  // otherwise it's a CTA key
  return <CtaInspector sel={sel} cta={cta} defs={defs} onToggle={() => onToggleCta(sel)} />;
}

function AddRemove({ on, onToggle }) {
  return on ? (
    <button type="button" className="asm-btn-remove" onClick={onToggle}>
      <Icon name="minus" size={13} />{t("lpm.inspector.remove")}
    </button>
  ) : (
    <button type="button" className="asm-btn-add" onClick={onToggle}>
      <Icon name="plus" size={13} />{t("lpm.inspector.add")}
    </button>
  );
}

function SectionInspector({ section, onToggle, onSetQuotePull }) {
  const presLabel = t(`lpm.sections.pres.${section.presentation}`);
  const config = { blocks: [{ type: "section", id: section.id, props: {
    heading: section.heading, presentation: section.presentation, prose: section.prose,
    bullets: section.bullets, cards: section.cards, quote: section.quote, steps: section.steps,
  } }] };
  const hasContent =
    (section.presentation === "prose" && section.prose) ||
    (section.presentation === "bullets" && (section.bullets || []).length) ||
    (section.presentation === "statCards" && (section.cards || []).length) ||
    (section.presentation === "quote" && section.quote?.text) ||
    (section.presentation === "steps" && (section.steps || []).length);

  return (
    <div className="asm-col asm-col-mid">
      <div className="asm-insp-head">
        <span className="asm-insp-icon">
          <Icon name={PRESENTATIONS[section.presentation]?.icon || "file-text"} size={20} />
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="asm-insp-name">{section.heading}</div>
          <div className="asm-insp-meta">
            {presLabel}{section.page ? ` · ${section.page}` : ""}
          </div>
        </div>
        <AddRemove on={section.on} onToggle={onToggle} />
      </div>
      {section.summary && <p className="asm-insp-blurb">{section.summary}</p>}

      {/* adjust how it looks — for quotes: standard vs pullquote */}
      {section.presentation === "quote" && (
        <>
          <div className="asm-eyebrow">{t("lpm.sections.how_label")}</div>
          <div className="asm-chips">
            <button type="button"
              className={"asm-chip" + (!section.quote?.pull ? " is-active" : "")}
              onClick={() => onSetQuotePull(false)}>{t("lpm.sections.quote.standard")}</button>
            <button type="button"
              className={"asm-chip" + (section.quote?.pull ? " is-active" : "")}
              onClick={() => onSetQuotePull(true)}>{t("lpm.sections.quote.pull")}</button>
          </div>
        </>
      )}

      <div className="asm-eyebrow">{t("lpm.inspector.preview_label")}</div>
      <div className="asm-secpv">
        {hasContent
          ? <div className="lp-body"><LandingRenderer config={config} /></div>
          : <p className="asm-pv-empty">{t("lpm.sections.placeholder_hint")}</p>}
      </div>
    </div>
  );
}

// The AI Summary — the one AI-written section. Voice taste-test + live preview.
function AiInspector({ ai, onToggle, onVoice }) {
  // fetch the default voice the first time it's opened
  useEffect(() => {
    if (!ai.prose && !ai.loading) onVoice(ai.voice);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const config = { blocks: [{ type: "section", props: {
    heading: "", presentation: "prose", prose: ai.prose,
    bullets: [], cards: [], quote: {}, steps: [],
  } }] };
  return (
    <div className="asm-col asm-col-mid">
      <div className="asm-insp-head">
        <span className="asm-insp-icon"><Icon name="sparkles" size={20} /></span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="asm-insp-name">
            {t("lpm.sections.ai.heading")}
            <span className="asm-ai-badge">{t("lpm.sections.ai.badge")}</span>
          </div>
        </div>
        <AddRemove on={ai.on} onToggle={onToggle} />
      </div>
      <p className="asm-insp-blurb">{t("lpm.sections.ai.caption")}</p>

      <div className="asm-eyebrow">{t("lpm.sections.ai.voice_label")}</div>
      <div className="asm-chips">
        {VOICES.map((v) => (
          <button
            key={v} type="button"
            className={"asm-chip" + (ai.voice === v ? " is-active" : "")}
            onClick={() => onVoice(v)}
          >
            {t(`lpm.inspector.voice.${v}.label`)}{" "}
            <span className="asm-chip-desc">— {t(`lpm.inspector.voice.${v}.note`)}</span>
          </button>
        ))}
      </div>

      <div className="asm-eyebrow">{t("lpm.inspector.preview_label")}</div>
      <div className="asm-secpv">
        {ai.loading
          ? <p className="asm-pv-loading">{t("lpm.inspector.loading")}</p>
          : ai.prose
            ? <div className="lp-body"><LandingRenderer config={config} /></div>
            : <p className="asm-pv-empty">{t("lpm.inspector.loading")}</p>}
      </div>
    </div>
  );
}

function CtaInspector({ sel, cta, defs, onToggle }) {
  const label = sel === "download" ? (cta.downloadLabel || defs?.download?.label)
    : sel === "secondary" ? (cta.secondaryLabel || defs?.secondaryCta?.label) : "";
  const config =
    sel === "download" ? { blocks: [{ type: "download", props: { label } }] }
    : sel === "secondary" ? { blocks: [{ type: "secondaryCta", props: { label } }] }
    : { blocks: [{ type: "share", props: {} }] };
  return (
    <div className="asm-col asm-col-mid">
      <div className="asm-insp-head">
        <span className="asm-insp-icon"><Icon name={BLOCK_ICONS[sel]} size={20} /></span>
        <div style={{ flex: 1 }}>
          <div className="asm-insp-name">{t(`lpm.blocks.${sel}.name`)}</div>
        </div>
        <AddRemove on={!!cta[sel]} onToggle={onToggle} />
      </div>
      <p className="asm-insp-blurb">{t(`lpm.blocks.${sel}.what`)} {t(`lpm.blocks.${sel}.when`)}</p>
      <div className="asm-eyebrow">{t("lpm.inspector.preview_label")}</div>
      <div className="asm-secpv">
        <div className="lp-body"><LandingRenderer config={config} /></div>
      </div>
    </div>
  );
}
