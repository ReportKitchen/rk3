import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { t } from "../../content.js";
import { assetBase, sourceUrl } from "../../api.js";
import { LandingRenderer } from "../LandingRenderer.jsx";
import { buildSectionConfig } from "./model.js";
import { Icon } from "./icons.jsx";

const countWords = (s) => (String(s || "").trim().match(/\S+/g) || []).length;

// Wordsmith: read the page top to bottom and fix the wording. The page renders in
// the MAIN document (not a Puck iframe) with the real block components — the AI
// sections in their own words — made editable in place (bold / italic / lists /
// links only). Structural changes happen back in Assemble.
export default function Wordsmith({ slug, title, coverAsset, cover, sections, cta, ai, onBack }) {
  const editorRef = useRef(null);
  const [words, setWords] = useState(0);
  const [bar, setBar] = useState(null); // {top,left} of the floating toolbar

  const config = useMemo(() => buildSectionConfig({
    title,
    cover: coverAsset ? { src: coverAsset.src, alt: coverAsset.alt, layout: cover } : null,
    sections, cta, ai,
  }), [title, coverAsset, cover, sections, cta, ai]);

  const html = useMemo(() => renderToStaticMarkup(
    <LandingRenderer
      config={config}
      resolveAsset={(s) => (s?.startsWith("http") ? s : `${assetBase(slug)}/${s}`)}
      downloadHref={sourceUrl(slug)}
    />
  ), [config, slug]);

  const recomputeWords = useCallback(() => {
    setWords(countWords(editorRef.current?.innerText));
  }, []);

  useEffect(() => {
    if (editorRef.current) { editorRef.current.innerHTML = html; recomputeWords(); }
  }, [html, recomputeWords]);

  const syncBar = useCallback(() => {
    const sel = window.getSelection();
    const ed = editorRef.current;
    if (!sel || sel.isCollapsed || sel.rangeCount === 0 || !ed) { setBar(null); return; }
    const range = sel.getRangeAt(0);
    if (!ed.contains(range.commonAncestorContainer)) { setBar(null); return; }
    const r = range.getBoundingClientRect();
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
