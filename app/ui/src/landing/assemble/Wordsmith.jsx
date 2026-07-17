import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { t } from "../../content.js";
import { assetBase, sourceUrl, getGuided } from "../../api.js";
import { guard } from "../../errorBus.js";
import { LandingRenderer } from "../LandingRenderer.jsx";
import { Icon } from "./icons.jsx";

// config block type -> library key (title/cover are page fundamentals -> null)
const TYPE_KEY = {
  docSummary: "execSummary", highlights: "highlights", findings: "findings",
  toc: "toc", storytelling: "storytelling", download: "download",
  secondaryCta: "secondary", share: "share",
};
function blockKey(b) {
  if (b.type === "summary") return (b.props?.heading || "").toLowerCase().includes("exec") ? "execSummary" : "aiSummary";
  return TYPE_KEY[b.type] ?? null;
}

// Narrow the /guided config to what's actually on the page (the added set) and
// apply the picked facts to the Findings block.
function effectiveConfig(config, added, stats, checkedFacts) {
  if (!config?.blocks) return { blocks: [] };
  const picked = checkedFacts.map((i) => stats[i]).filter(Boolean)
    .map((s) => ({ stat: s.value, text: s.fact, page: s.page || "" }));
  const blocks = config.blocks
    .filter((b) => { const k = blockKey(b); return k === null || added.has(k); })
    .map((b) => (b.type === "findings" && picked.length ? { ...b, props: { ...b.props, items: picked } } : b));
  return { ...config, blocks };
}

const countWords = (s) => (String(s || "").trim().match(/\S+/g) || []).length;

// Wordsmith: read the page top to bottom and fix the wording. The page renders
// in the MAIN document (not a Puck iframe) with the real block components, made
// editable in place — bold / italic / lists / links only, on purpose. Structural
// changes happen back in Assemble.
export default function Wordsmith({ slug, length, cover, added, stats, checkedFacts, profile, onBack }) {
  const editorRef = useRef(null);
  const [config, setConfig] = useState(null);
  const [words, setWords] = useState(0);
  const [bar, setBar] = useState(null); // {top,left} of the floating toolbar

  // pull a fresh /guided for the current length+cover so the page matches Assemble
  useEffect(() => {
    let alive = true;
    getGuided(slug, length, cover).then((c) => alive && setConfig(c)).catch(guard("wordsmith: guided", null));
    return () => { alive = false; };
  }, [slug, length, cover]);

  const eff = useMemo(
    () => effectiveConfig(config, added, stats, checkedFacts),
    [config, added, stats, checkedFacts]);

  const html = useMemo(() => renderToStaticMarkup(
    <LandingRenderer
      config={eff}
      resolveAsset={(s) => (s?.startsWith("http") ? s : `${assetBase(slug)}/${s}`)}
      downloadHref={sourceUrl(slug)}
    />
  ), [eff, slug]);

  const recomputeWords = useCallback(() => {
    setWords(countWords(editorRef.current?.innerText));
  }, []);

  // render the page HTML into the editable surface once per config; edits then
  // live in the DOM (React doesn't re-own this subtree)
  useEffect(() => {
    if (editorRef.current) { editorRef.current.innerHTML = html; recomputeWords(); }
  }, [html, recomputeWords]);

  // floating toolbar follows a non-empty selection inside the editor
  const syncBar = useCallback(() => {
    const sel = window.getSelection();
    const ed = editorRef.current;
    if (!sel || sel.isCollapsed || sel.rangeCount === 0 || !ed) { setBar(null); return; }
    const range = sel.getRangeAt(0);
    if (!ed.contains(range.commonAncestorContainer)) { setBar(null); return; }
    const r = range.getBoundingClientRect();
    // position within the editor's relative wrapper (the toolbar's offset parent)
    const host = ed.parentElement.getBoundingClientRect();
    setBar({ top: r.top - host.top - 8, left: r.left - host.left + r.width / 2 });
  }, []);
  useEffect(() => {
    document.addEventListener("selectionchange", syncBar);
    return () => document.removeEventListener("selectionchange", syncBar);
  }, [syncBar]);

  const exec = (cmd, value) => {
    document.execCommand(cmd, false, value);
    editorRef.current?.focus();
    recomputeWords();
  };
  const link = () => {
    const url = window.prompt("Link URL");
    if (url) exec("createLink", url);
  };

  const min = Math.max(1, Math.round(words / 200));

  return (
    <div className="asm-ws">
      <div className="asm-ws-bar">
        <button type="button" className="asm-ws-back" onClick={onBack}>
          <Icon name="chevron-left" size={14} />{t("lpm.wordsmith.back_to_assemble")}
        </button>
        <span className="asm-ws-back-hint">{t("lpm.wordsmith.back_to_assemble_hint")}</span>
        <span className="asm-ws-estimate">{t("lpm.wordsmith.read_estimate", { words, min })}</span>
      </div>
      <div className="asm-ws-help">{t("lpm.wordsmith.help")}</div>
      <div style={{ position: "relative" }}>
        {bar && (
          <div className="asm-ws-toolbar" style={{ top: bar.top, left: bar.left }} onMouseDown={(e) => e.preventDefault()}>
            <button type="button" className="asm-ws-tool" style={{ fontWeight: 800 }} onClick={() => exec("bold")}>B</button>
            <button type="button" className="asm-ws-tool" style={{ fontStyle: "italic" }} onClick={() => exec("italic")}>I</button>
            <button type="button" className="asm-ws-tool" onClick={() => exec("insertUnorderedList")}><Icon name="list-bullet" size={15} /></button>
            <button type="button" className="asm-ws-tool" onClick={link}><Icon name="link" size={15} /></button>
          </div>
        )}
        <div
          className="asm-ws-page lp-body"
          ref={editorRef}
          contentEditable
          suppressContentEditableWarning
          onInput={recomputeWords}
          onMouseUp={syncBar}
          onKeyUp={syncBar}
        />
      </div>
    </div>
  );
}
