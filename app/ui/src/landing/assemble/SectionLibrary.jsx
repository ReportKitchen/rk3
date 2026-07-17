import React from "react";
import { t } from "../../content.js";
import { PRESENTATIONS, CTA_KEYS } from "./model.js";
import { Icon, BLOCK_ICONS } from "./icons.jsx";

// Left column: "Highlights" = the AI-found meaningful sections (the star), each a
// card that teaches what it is and whether it's on the page; below, the "Call to
// action" scaffolding. Click a card to inspect and adjust it in the middle.
export default function SectionLibrary({ sections, cta, sel, noai, genError, docRead, onSelect }) {
  const notice = genError
    ? <div className="asm-error-notice">{t("lpm.sections.error_notice", { reason: genError })}</div>
    : noai
      ? <div className="asm-noai-notice">{t("lpm.sections.noai_notice")}</div>
      : null;
  return (
    <div className="asm-col asm-col-left">
      {notice}

      <div className="asm-bucket-name" style={{ marginTop: (noai || genError) ? 8 : 0 }}>
        {t("lpm.sections.highlights.title")}
      </div>
      <p className="asm-sub">{t("lpm.sections.highlights.sub")}</p>
      <div className="asm-cards">
        {sections.length === 0 && <p className="asm-sub">{t("lpm.sections.empty")}</p>}
        {sections.map((s) => (
          <button
            key={s.id} type="button"
            className={"asm-card" + (sel === s.id ? " is-selected" : "")}
            onClick={() => onSelect(s.id)}
          >
            <span className="asm-card-icon">
              <Icon name={PRESENTATIONS[s.presentation]?.icon || "file-text"} size={15} />
            </span>
            <span className="asm-card-body">
              <span className="asm-card-name">
                {s.heading}
                {s.verbatim && <span className="asm-verbatim-badge">{t("lpm.sections.verbatim_badge")}</span>}
              </span>
              <span className="asm-card-guidance">{s.summary || t("lpm.sections.placeholder_hint")}</span>
            </span>
            {s.on
              ? <Icon name="check" size={14} className="asm-card-check" />
              : <Icon name="chevron-right" size={14} className="asm-card-chev" />}
          </button>
        ))}
      </div>

      <div className="asm-bucket-name">{t("lpm.sections.cta.title")}</div>
      <p className="asm-sub">{t("lpm.sections.cta.sub")}</p>
      <div className="asm-cards">
        {CTA_KEYS.map((key) => (
          <button
            key={key} type="button"
            className={"asm-card" + (sel === key ? " is-selected" : "")}
            onClick={() => onSelect(key)}
          >
            <span className="asm-card-icon"><Icon name={BLOCK_ICONS[key]} size={15} /></span>
            <span className="asm-card-body">
              <span className="asm-card-name">{t(`lpm.blocks.${key}.name`)}</span>
              <span className="asm-card-guidance">{t(`lpm.blocks.${key}.what`)}</span>
            </span>
            {cta[key]
              ? <Icon name="check" size={14} className="asm-card-check" />
              : <Icon name="chevron-right" size={14} className="asm-card-chev" />}
          </button>
        ))}
      </div>
    </div>
  );
}
