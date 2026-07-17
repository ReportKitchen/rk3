import React from "react";
import { t } from "../../content.js";
import { PRESENTATIONS, CTA_KEYS, splitSections } from "./model.js";
import { Icon, BLOCK_ICONS } from "./icons.jsx";

// Left column, three groups top-to-bottom: Introduction (the document's own
// foreword / summary), Highlights (the meaningful body sections — the star), and
// Call to action (the fixed scaffolding). Click a card to inspect and adjust it.
export default function SectionLibrary({ sections, cta, ai, sel, noai, genError, docRead, onSelect }) {
  const notice = genError
    ? <div className="asm-error-notice">{t("lpm.sections.error_notice", { reason: genError })}</div>
    : noai
      ? <div className="asm-noai-notice">{t("lpm.sections.noai_notice")}</div>
      : null;
  const { intro, body } = splitSections(sections);
  return (
    <div className="asm-col asm-col-left">
      {notice}

      <Group
        title={t("lpm.sections.intro.title")}
        sub={t("lpm.sections.intro.sub", { n: intro.length, ai: noai ? "no" : "yes" })}
        first={!notice}
      >
        {intro.map((s) => <SectionCard key={s.id} s={s} sel={sel} onSelect={onSelect} />)}
        {!noai && <AiCard ai={ai} sel={sel} onSelect={onSelect} />}
      </Group>

      <Group
        title={t("lpm.sections.highlights.title")} sub={t("lpm.sections.highlights.sub")}
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
            <OnBadge on={cta[key]} />
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

// on/off status at a glance: a filled green check when featured, a faint empty
// ring when not.
function OnBadge({ on }) {
  return on
    ? <span className="asm-on-badge is-on"><Icon name="check" size={11} /></span>
    : <span className="asm-on-badge" />;
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
        <span className="asm-card-name">{s.heading}</span>
        <span className="asm-card-guidance">{s.summary || t("lpm.sections.placeholder_hint")}</span>
      </span>
      <OnBadge on={s.on} />
    </button>
  );
}

// The one AI-written option (a pitch in a chosen voice). Badged AI-written — the
// exception in a verbatim-first page.
function AiCard({ ai, sel, onSelect }) {
  return (
    <button
      type="button"
      className={"asm-card" + (sel === "ai-summary" ? " is-selected" : "")}
      onClick={() => onSelect("ai-summary")}
    >
      <span className="asm-card-icon"><Icon name="sparkles" size={15} /></span>
      <span className="asm-card-body">
        <span className="asm-card-name">
          {t("lpm.sections.ai.heading")}
          <span className="asm-ai-badge">{t("lpm.sections.ai.badge")}</span>
        </span>
        <span className="asm-card-guidance">{t("lpm.sections.ai.caption")}</span>
      </span>
      <OnBadge on={ai.on} />
    </button>
  );
}
