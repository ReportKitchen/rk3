import React from "react";
import {
  DndContext, PointerSensor, KeyboardSensor, useSensor, useSensors, closestCenter,
} from "@dnd-kit/core";
import {
  SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { restrictToVerticalAxis } from "@dnd-kit/modifiers";
import { CSS } from "@dnd-kit/utilities";
import { t } from "../../content.js";
import { PRESENTATIONS, CTA_KEYS, splitSections } from "./model.js";
import { Icon, BLOCK_ICONS } from "./icons.jsx";

// Left column, three groups top-to-bottom: Introduction (the document's own
// foreword / summary), Highlights (the meaningful body sections — the star), and
// Call to action (the fixed scaffolding). Click a card to inspect and adjust it;
// drag a section card by its grip to reorder within its group (standard sortable:
// neighbours slide, the card drops into place). CTAs are fixed — not reorderable.
export default function SectionLibrary({ sections, cta, ai, sel, noai, genError, docRead, onSelect, onReorder }) {
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
        <SortableGroup items={intro} sel={sel} onSelect={onSelect} onReorder={onReorder}
          trailing={!noai && <AiCard ai={ai} sel={sel} onSelect={onSelect} />} />
      </Group>

      <Group
        title={t("lpm.sections.highlights.title")} sub={t("lpm.sections.highlights.sub")}
      >
        {body.length === 0 && <p className="asm-sub">{t("lpm.sections.empty")}</p>}
        <SortableGroup items={body} sel={sel} onSelect={onSelect} onReorder={onReorder} />
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

// One sortable group (its own DndContext so drags never cross into another group).
// `trailing` is a non-sortable card shown after the sortable ones (the AI card).
function SortableGroup({ items, sel, onSelect, onReorder, trailing }) {
  const sensors = useSensors(
    // a small activation distance so a plain click still selects (no accidental drag)
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const onDragEnd = ({ active, over }) => {
    if (over && active.id !== over.id) onReorder(active.id, over.id);
  };
  const body = (
    <div className="asm-cards">
      {items.map((s) => <SectionCard key={s.id} s={s} sel={sel} onSelect={onSelect} />)}
      {trailing || null}
    </div>
  );
  if (!items.length) return body;   // nothing to sort — still show the trailing card
  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter}
      modifiers={[restrictToVerticalAxis]} onDragEnd={onDragEnd}>
      <SortableContext items={items.map((s) => s.id)} strategy={verticalListSortingStrategy}>
        {body}
      </SortableContext>
    </DndContext>
  );
}

function Group({ title, sub, first, children }) {
  return (
    <>
      <div className="asm-bucket-name" style={{ marginTop: first ? 0 : 18 }}>{title}</div>
      <p className="asm-sub">{sub}</p>
      {children}
    </>
  );
}

// in-use = a filled green check; not-in-use = a slashed circle (status, not a
// clickable radio).
function OnBadge({ on }) {
  return on
    ? <span className="asm-on-badge is-on"><Icon name="check" size={11} /></span>
    : <span className="asm-on-badge is-off" />;
}

function SectionCard({ s, sel, onSelect }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: s.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 5 : undefined,
  };
  return (
    <div
      ref={setNodeRef} style={style}
      className={"asm-card" + (sel === s.id ? " is-selected" : "") + (isDragging ? " is-dragging" : "")}
      role="button" tabIndex={0}
      onClick={() => onSelect(s.id)}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(s.id); } }}
    >
      <span className="asm-card-icon">
        <Icon name={PRESENTATIONS[s.presentation]?.icon || "file-text"} size={15} />
      </span>
      <span className="asm-card-body">
        <span className="asm-card-name">{s.heading}</span>
        <span className="asm-card-guidance">{s.summary || t("lpm.sections.placeholder_hint")}</span>
      </span>
      <span className="asm-card-grip" {...attributes} {...listeners}
        aria-label={t("lpm.sections.drag_hint")} onClick={(e) => e.stopPropagation()}>
        <Icon name="grip-vertical" size={14} />
      </span>
      <OnBadge on={s.on} />
    </div>
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
