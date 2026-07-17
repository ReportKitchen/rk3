import React from "react";
import { t } from "../../content.js";
import { LandingRenderer } from "../LandingRenderer.jsx";
import { PRESENTATIONS } from "./model.js";
import { Icon, BLOCK_ICONS } from "./icons.jsx";

// Center column: inspect one thing — a content section or a CTA — see it rendered
// exactly "as it will appear" (the real block components), read why it earns a
// place, adjust how it looks, and add/remove it.
export default function Inspector({
  sel, sections, cta, defs, onToggleSection, onToggleCta, onSetPresentation, onSetQuotePull,
}) {
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
            {section.verbatim && <span className="asm-verbatim-badge">{t("lpm.sections.verbatim_badge")}</span>}
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
