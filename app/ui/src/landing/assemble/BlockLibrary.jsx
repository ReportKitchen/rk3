import React from "react";
import { t } from "../../content.js";
import { BUCKETS, NEW_BLOCKS } from "./model.js";
import { Icon, BLOCK_ICONS } from "./icons.jsx";

// Left column: the block library, grouped Intro / Evidence / CTA. Each card
// teaches when a block earns its place — the contextual line under the name is
// the guidance engine's per-block note for THIS document (guidance.blocks[key]),
// falling back to the durable "what it is" copy. Click a card to inspect it.
export default function BlockLibrary({ guidance, added, sel, onSelect }) {
  const notes = guidance?.blocks || {};
  return (
    <div className="asm-col asm-col-left">
      <h1 className="asm-h1">{t("lpm.blocks.library.title")}</h1>
      <p className="asm-sub">{t("lpm.blocks.library.sub")}</p>
      {BUCKETS.map((bucket) => (
        <div key={bucket.id}>
          <div className="asm-bucket-name">
            {t(`lpm.blocks.bucket.${bucket.id}.title`)}{" "}
            <span className="asm-bucket-hint">· {t(`lpm.blocks.bucket.${bucket.id}.hint`)}</span>
          </div>
          <div className="asm-cards">
            {bucket.keys.map((key) => {
              const isSel = sel === key;
              const isAdded = added.has(key);
              const note = notes[key]?.note || t(`lpm.blocks.${key}.what`);
              return (
                <button
                  key={key}
                  type="button"
                  className={"asm-card" + (isSel ? " is-selected" : "")}
                  onClick={() => onSelect(key)}
                >
                  <span className="asm-card-icon">
                    <Icon name={BLOCK_ICONS[key]} size={15} />
                  </span>
                  <span className="asm-card-body">
                    <span className="asm-card-name">
                      {t(`lpm.blocks.${key}.name`)}
                      {NEW_BLOCKS.has(key) && <span className="asm-new-badge">{t("lpm.blocks.new_badge")}</span>}
                    </span>
                    <span className="asm-card-guidance">{note}</span>
                  </span>
                  {isAdded
                    ? <Icon name="check" size={14} className="asm-card-check" />
                    : <Icon name="chevron-right" size={14} className="asm-card-chev" />}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
