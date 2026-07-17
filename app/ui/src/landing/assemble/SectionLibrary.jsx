import React from "react";
import { t } from "../../content.js";
import { PRESENTATIONS, CTA_KEYS, splitSections } from "./model.js";
import { Icon, BLOCK_ICONS } from "./icons.jsx";

// Left column, three groups top-to-bottom: Introduction (the document's own
// foreword / summary), Highlights (the meaningful body sections — the star), and
// Call to action (the fixed scaffolding). Click a card to inspect and adjust it.
export default function SectionLibrary({ sections, cta, sel, noai, genError, docRead, onSelect }) {
  const notice = genError
    ? <div className="asm-error-notice">{t("lpm.sections.error_notice", { reason: genError })}</div>
    : noai
      ? <div className="asm-noai-notice">{t("lpm.sections.noai_notice")}</div>
      : null;
  const { intro, body } = splitSections(sections);
  return (
    <div className="asm-col asm-col-left">
      {notice}

      {intro.length > 0 && (
        <Group
          title={t("lpm.sections.intro.title")} sub={t("lpm.sections.intro.sub")}
          first={!notice}
        >
          {intro.map((s) => <SectionCard key={s.id} s={s} sel={sel} onSelect={onSelect} />)}
        </Group>
      )}

      <Group
        title={t("lpm.sections.highlights.title")} sub={t("lpm.sections.highlights.sub")}
        first={!notice && intro.length === 0}
      >
        {body.length === 0 && <p className="asm-sub">{t("lpm.sections.empty")}</p>}
        {body.map((s) => <SectionCard key={s.id} s={s} sel={sel} onSelect={onSelect} />)}
      </Group>

      <Group title={t("lpm.sections.cta.title")} sub={t("lpm.sections.cta.sub")}>
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
      </Group>
    </div>
  );
}

function Group({ title, sub, first, children }) {
  return (
    <>
      <div className="asm-bucket-name" style={{ marginTop: first ? 0 : 18 }}>{title}</div>
      <p className="asm-sub">{sub}</p>
      <div className="asm-cards">{children}</div>
    </>
  );
}

function SectionCard({ s, sel, onSelect }) {
  return (
    <button
      type="button"
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
  );
}
