import React, { useState } from "react";
import {
  DndContext, DragOverlay, PointerSensor, KeyboardSensor, useSensor, useSensors, closestCenter,
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
// foreword / summary + the AI Summary), Highlights (the meaningful body sections —
// the star), and Call to action. Click a card to inspect it; drag any card by its
// grip to reorder within its group. A DragOverlay carries the dragged card at full
// size (no squish, no lag); the empty slot shows where it will drop.
export default function SectionLibrary({ sections, cta, ai, sel, noai, genError, docRead, onSelect, onReorder, onReorderCta }) {
  const notice = genError
    ? <div className="asm-error-notice">{t("lpm.sections.error_notice", { reason: genError })}</div>
    : noai
      ? <div className="asm-noai-notice">{t("lpm.sections.noai_notice")}</div>
      : null;
  const { intro, body } = splitSections(sections);
  const sectItem = (s) => ({
    id: s.id, icon: PRESENTATIONS[s.presentation]?.icon || "file-text",
    name: s.heading, guidance: s.summary || t("lpm.sections.placeholder_hint"), on: s.on,
  });
  const ctaItems = (cta.order || CTA_KEYS).map((key) => ({
    id: key, icon: BLOCK_ICONS[key], name: t(`lpm.blocks.${key}.name`),
    guidance: t(`lpm.blocks.${key}.what`), on: !!cta[key],
  }));
  const aiItem = {
    id: "ai-summary", icon: "sparkles", name: t("lpm.sections.ai.heading"),
    badge: <span className="asm-ai-badge">{t("lpm.sections.ai.badge")}</span>,
    guidance: t("lpm.sections.ai.caption"), on: ai.on,
  };

  return (
    <div className="asm-col asm-col-left">
      {notice}

      <Group
        title={t("lpm.sections.intro.title")}
        sub={t("lpm.sections.intro.sub", { n: intro.length, ai: noai ? "no" : "yes" })}
        first={!notice}
      >
        <SortableList items={intro.map(sectItem)} sel={sel} onSelect={onSelect} onReorder={onReorder}
          trailing={!noai && <CardShell item={aiItem} selected={sel === "ai-summary"} shift={sel === "ai-summary"} onSelect={onSelect} />} />
      </Group>

      <Group title={t("lpm.sections.highlights.title")} sub={t("lpm.sections.highlights.sub")}>
        {body.length === 0 && <p className="asm-sub">{t("lpm.sections.empty")}</p>}
        <SortableList items={body.map(sectItem)} sel={sel} onSelect={onSelect} onReorder={onReorder} />
      </Group>

      <Group title={t("lpm.sections.cta.title")} sub={t("lpm.sections.cta.sub")}>
        <SortableList items={ctaItems} sel={sel} onSelect={onSelect} onReorder={onReorderCta} />
      </Group>
    </div>
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

// A sortable list with its own DndContext (drags never cross into another group).
// The DragOverlay renders the active card at full size, so a tall card dragged
// over a short card's slot keeps its height — nothing is ever squished.
function SortableList({ items, sel, onSelect, onReorder, trailing }) {
  const [activeId, setActiveId] = useState(null);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),  // click still selects
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const active = items.find((i) => i.id === activeId);
  const body = (
    <div className="asm-cards">
      {items.map((i) => <SortableRow key={i.id} item={i} sel={sel} onSelect={onSelect} />)}
      {trailing || null}
    </div>
  );
  if (!items.length) return body;
  return (
    <DndContext
      sensors={sensors} collisionDetection={closestCenter} modifiers={[restrictToVerticalAxis]}
      onDragStart={({ active: a }) => setActiveId(a.id)}
      onDragCancel={() => setActiveId(null)}
      onDragEnd={({ active: a, over }) => { setActiveId(null); if (over && a.id !== over.id) onReorder(a.id, over.id); }}
    >
      <SortableContext items={items.map((i) => i.id)} strategy={verticalListSortingStrategy}>
        {body}
      </SortableContext>
      <DragOverlay dropAnimation={{ duration: 200, easing: "cubic-bezier(0.2, 0, 0, 1)" }}>
        {active ? <CardShell item={active} selected={sel === active.id} overlay /> : null}
      </DragOverlay>
    </DndContext>
  );
}

// One row: the dnd-controlled slot (transform/transition come from dnd-kit) wraps
// the visual card. While dragging, the card is a faded placeholder marking the
// drop spot (same height as the real card); the DragOverlay shows the live one.
function SortableRow({ item, sel, onSelect }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.id });
  const style = { transform: CSS.Transform.toString(transform), transition };
  return (
    <div ref={setNodeRef} style={style} className="asm-card-slot">
      <CardShell
        item={item} selected={sel === item.id}
        shift={sel === item.id && !isDragging}   // the select-shift lives on the inner card, so dnd's transform never fights it
        placeholder={isDragging}
        onSelect={onSelect} gripProps={{ ...attributes, ...listeners }}
      />
    </div>
  );
}

// The pure card visual. `shift` slides a selected card right (its own transform,
// transitioned smoothly). `placeholder`/`overlay` are the two drag states.
function CardShell({ item, selected, shift, placeholder, overlay, onSelect, gripProps }) {
  const cls = "asm-card"
    + (selected ? " is-selected" : "")
    + (shift ? " is-shift" : "")
    + (placeholder ? " is-placeholder" : "")
    + (overlay ? " is-overlay" : "");
  const clickable = !overlay && !placeholder;
  return (
    <div
      className={cls}
      role="button" tabIndex={clickable ? 0 : undefined}
      onClick={clickable ? () => onSelect(item.id) : undefined}
      onKeyDown={clickable ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(item.id); } } : undefined}
    >
      <span className="asm-card-icon"><Icon name={item.icon} size={15} /></span>
      <span className="asm-card-body">
        <span className="asm-card-name">{item.name}{item.badge || null}</span>
        <span className="asm-card-guidance">{item.guidance}</span>
      </span>
      {gripProps ? (
        <span className="asm-card-grip" {...gripProps} aria-label={t("lpm.sections.drag_hint")}
          onClick={(e) => e.stopPropagation()}>
          <Icon name="grip-vertical" size={14} />
        </span>
      ) : null}
      <OnBadge on={item.on} />
    </div>
  );
}

// in-use = a filled green check; not-in-use = a slashed circle (status, not a
// clickable radio).
function OnBadge({ on }) {
  return on
    ? <span className="asm-on-badge is-on"><Icon name="check" size={11} /></span>
    : <span className="asm-on-badge is-off" />;
}
