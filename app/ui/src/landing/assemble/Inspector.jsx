import React, { useEffect } from "react";
import { t } from "../../content.js";
import { LandingRenderer, SHARE_NETWORKS, statTreatmentsFor, quoteTreatmentsFor } from "../LandingRenderer.jsx";
import { PRESENTATIONS, REC_WORDS, wordCount, effectiveProse, trimProse } from "./model.js";
import { Icon, BLOCK_ICONS } from "./icons.jsx";
import WhiskLoader from "./WhiskLoader.jsx";

const VOICES = ["intro", "neutral", "hardsell"];
const SHARE_STYLES = ["plain", "round", "square"];

// Center column: inspect one thing — a content section, the AI Summary, or a CTA —
// see it rendered exactly "as it will appear" (the real block components), read
// why it earns a place, adjust it, and add/remove it. Before anything is picked,
// a friendly welcome panel.
export default function Inspector({
  sel, sections, cta, ai, defs, slug, length,
  onToggleSection, onToggleCta, onSetPresentation, onSetQuoteTreatment, onSetTrimmed, onSetTreatment,
  onToggleAi, onAiVoice, onPatchCta,
}) {
  if (!sel) return <Welcome />;
  if (sel === "ai-summary") {
    return <AiInspector ai={ai} onToggle={onToggleAi} onVoice={onAiVoice} />;
  }
  const section = sections.find((s) => s.id === sel);
  if (section) {
    return (
      <SectionInspector
        section={section}
        onToggle={() => onToggleSection(section.id)}
        onSetQuoteTreatment={(tr) => onSetQuoteTreatment(section.id, tr)}
        onSetTrimmed={(v) => onSetTrimmed(section.id, v)}
        onSetTreatment={(tr) => onSetTreatment(section.id, tr)}
      />
    );
  }
  // otherwise it's a CTA key
  return <CtaInspector sel={sel} cta={cta} onToggle={() => onToggleCta(sel)} onPatch={onPatchCta} />;
}

function Welcome() {
  return (
    <div className="asm-col asm-col-mid">
      <div className="asm-welcome">
        <span className="asm-insp-icon" style={{ width: 44, height: 44 }}>
          <Icon name="pencil-line" size={22} />
        </span>
        <h2 className="asm-welcome-title">{t("lpm.inspector.welcome.title")}</h2>
        <p className="asm-welcome-body">{t("lpm.inspector.welcome.body")}</p>
        <p className="asm-welcome-hint">{t("lpm.inspector.welcome.hint")}</p>
      </div>
    </div>
  );
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

function SectionInspector({ section, onToggle, onSetQuoteTreatment, onSetTrimmed, onSetTreatment }) {
  const presLabel = t(`lpm.sections.pres.${section.presentation}`);
  const config = { blocks: [{ type: "section", id: section.id, props: {
    heading: section.heading, presentation: section.presentation, prose: effectiveProse(section),
    bullets: section.bullets, cards: section.cards, quote: section.quote, steps: section.steps,
    treatment: section.treatment,
  } }] };
  const hasContent =
    (section.presentation === "prose" && section.prose) ||
    (section.presentation === "bullets" && (section.bullets || []).length) ||
    (section.presentation === "statCards" && (section.cards || []).length) ||
    (section.presentation === "quote" && section.quote?.text) ||
    (section.presentation === "steps" && (section.steps || []).length);
  // long verbatim prose gets a Full / Trimmed control (this is where we trim)
  const trimmable = section.presentation === "prose" && wordCount(section.prose) > REC_WORDS;

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

      {/* quotes: pick a pullquote treatment (5a–5f + a quiet standard) */}
      {section.presentation === "quote" && (
        <>
          <div className="asm-eyebrow">{t("lpm.sections.how_label")}</div>
          <div className="asm-chips">
            {quoteTreatmentsFor(section.quote).map((tr) => (
              <button key={tr} type="button"
                className={"asm-chip" + ((section.quote?.treatment || "glyph") === tr ? " is-active" : "")}
                onClick={() => onSetQuoteTreatment(tr)}>{t(`lpm.sections.quote.treatment.${tr}`)}</button>
            ))}
          </div>
        </>
      )}

      {/* stat sections: how the numbers are plated (count/data-aware) */}
      {section.presentation === "statCards" && (
        <>
          <div className="asm-eyebrow">{t("lpm.sections.treatment_label")}</div>
          <div className="asm-chips">
            {statTreatmentsFor(section.cards).map((tr) => (
              <button key={tr} type="button"
                className={"asm-chip" + ((section.treatment || "cards") === tr ? " is-active" : "")}
                onClick={() => onSetTreatment(tr)}>{t(`lpm.sections.treatment.${tr}`)}</button>
            ))}
          </div>
        </>
      )}

      {/* long prose: full vs trimmed */}
      {trimmable && (
        <>
          <div className="asm-eyebrow">{t("lpm.sections.length_label")}</div>
          <div className="asm-chips">
            <button type="button"
              className={"asm-chip" + (!section.trimmed ? " is-active" : "")}
              onClick={() => onSetTrimmed(false)}>{t("lpm.sections.length.full")}</button>
            <button type="button"
              className={"asm-chip" + (section.trimmed ? " is-active" : "")}
              onClick={() => onSetTrimmed(true)}>{t("lpm.sections.length.trimmed")}</button>
          </div>
          {section.trimmed && (
            <p className="asm-trim-note">{t("lpm.sections.length.trimmed_note", { n: wordCount(trimProse(section.prose)) })}</p>
          )}
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
    heading: ai.heading || "", presentation: "prose", prose: ai.prose,
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
          ? <div style={{ padding: "18px 0" }}><WhiskLoader size={84} caption={t("lpm.inspector.loading")} /></div>
          : ai.prose
            ? <div className="lp-body"><LandingRenderer config={config} /></div>
            : ai.fetched
              ? <p className="asm-pv-empty">{t("lpm.inspector.ai_failed")}</p>
              : <div style={{ padding: "18px 0" }}><WhiskLoader size={84} caption={t("lpm.inspector.loading")} /></div>}
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="asm-field">
      <span className="asm-field-label">{label}</span>
      {children}
    </label>
  );
}

function CtaInspector({ sel, cta, onToggle, onPatch }) {
  // editable props + a live preview built from the current cta state
  let config, editor;
  if (sel === "download") {
    config = { blocks: [{ type: "download", props: {
      label: cta.downloadLabel, mode: cta.downloadUrl ? "url" : "bundle", url: cta.downloadUrl } }] };
    editor = (
      <>
        <Field label={t("lpm.inspector.cta.text_label")}>
          <input className="asm-input" value={cta.downloadLabel}
            onChange={(e) => onPatch({ downloadLabel: e.target.value })} />
        </Field>
        <Field label={t("lpm.inspector.cta.url_label")}>
          <input className="asm-input" value={cta.downloadUrl} placeholder={t("lpm.inspector.cta.download_url_ph")}
            onChange={(e) => onPatch({ downloadUrl: e.target.value })} />
        </Field>
      </>
    );
  } else if (sel === "secondary") {
    config = { blocks: [{ type: "secondaryCta", props: { label: cta.secondaryLabel, url: cta.secondaryUrl } }] };
    editor = (
      <>
        <Field label={t("lpm.inspector.cta.text_label")}>
          <input className="asm-input" value={cta.secondaryLabel}
            onChange={(e) => onPatch({ secondaryLabel: e.target.value })} />
        </Field>
        <Field label={t("lpm.inspector.cta.url_label")}>
          <input className="asm-input" value={cta.secondaryUrl} placeholder={t("lpm.inspector.cta.url_ph")}
            onChange={(e) => onPatch({ secondaryUrl: e.target.value })} />
        </Field>
      </>
    );
  } else {
    // social share — networks + button style
    const nets = cta.shareNetworks || {};
    config = { blocks: [{ type: "share", props: { networks: nets, style: cta.shareStyle } }] };
    editor = (
      <>
        <div className="asm-field-label">{t("lpm.inspector.share.networks_label")}</div>
        <div className="asm-share-nets">
          {SHARE_NETWORKS.map((n) => (
            <button key={n.key} type="button"
              className={"asm-chip" + (nets[n.key] ? " is-active" : "")}
              onClick={() => onPatch({ shareNetworks: { ...nets, [n.key]: !nets[n.key] } })}>
              {n.label}
            </button>
          ))}
        </div>
        <div className="asm-field-label" style={{ marginTop: 12 }}>{t("lpm.inspector.share.style_label")}</div>
        <div className="asm-chips">
          {SHARE_STYLES.map((st) => (
            <button key={st} type="button"
              className={"asm-chip" + (cta.shareStyle === st ? " is-active" : "")}
              onClick={() => onPatch({ shareStyle: st })}>
              {t(`lpm.inspector.share.style.${st}`)}
            </button>
          ))}
        </div>
      </>
    );
  }
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
      <div className="asm-fields">{editor}</div>
      <div className="asm-eyebrow">{t("lpm.inspector.preview_label")}</div>
      <div className="asm-secpv">
        <div className="lp-body"><LandingRenderer config={config} /></div>
      </div>
    </div>
  );
}
