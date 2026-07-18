import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { t } from "../../content.js";
import { assetBase, sourceUrl } from "../../api.js";
import { LandingRenderer } from "../LandingRenderer.jsx";
import { editSignatures } from "../finalHtml.js";
import { buildSectionConfig } from "./model.js";
import { Icon } from "./icons.jsx";

const countWords = (s) => (String(s || "").trim().match(/\S+/g) || []).length;

// Wordsmith: read the page top to bottom and fix the wording. The page renders in
// the MAIN document (not a Puck iframe) with the real block components — the AI
// sections in their own words — made editable in place (bold / italic / lists /
// links only). Structural changes happen back in Assemble.
export default function Wordsmith({ slug, title, coverAsset, cover, sections, cta, ai, edits, onEditsChange, onBack, onPublish }) {
  const editorRef = useRef(null);
  const savedRange = useRef(null);      // selection kept alive while the link popover has focus
  const editsRef = useRef(edits);       // latest saved edits, read by the render effect w/o re-running it
  editsRef.current = edits;
  const captureTimer = useRef(null);
  const [words, setWords] = useState(0);
  const [bar, setBar] = useState(null); // {top,left} of the floating toolbar
  const [linkEd, setLinkEd] = useState(null); // {top,left,url,newTab} inline link editor
  const linkEdRef = useRef(null);       // so syncBar can keep the toolbar up while the link editor is open
  linkEdRef.current = linkEd;

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

  // a structural signature per editable block — an edit is only re-applied while
  // the structure it was made against is unchanged (else the fresh render wins).
  // Shared with the final-page builder so Preview/export re-apply identically.
  const sigByKey = useMemo(() => editSignatures(config), [config]);

  const recomputeWords = useCallback(() => {
    setWords(countWords(editorRef.current?.innerText));
  }, []);

  // capture the current per-section edited HTML (keyed by skey, tagged with the
  // structural signature) and hand it up to persist
  const captureEdits = useCallback(() => {
    const ed = editorRef.current;
    if (!ed || !onEditsChange) return;
    const map = {};
    ed.querySelectorAll("[data-skey]").forEach((el) => {
      const sk = el.getAttribute("data-skey");
      map[sk] = { html: el.innerHTML, sig: sigByKey[sk] };
    });
    onEditsChange(map);
  }, [onEditsChange, sigByKey]);

  const onInput = useCallback(() => {
    recomputeWords();
    clearTimeout(captureTimer.current);
    captureTimer.current = setTimeout(captureEdits, 500);
  }, [recomputeWords, captureEdits]);

  useEffect(() => {
    if (!editorRef.current) return;
    editorRef.current.innerHTML = html;
    // re-apply saved edits where the block's structure is unchanged
    const ed = editsRef.current || {};
    Object.entries(ed).forEach(([sk, rec]) => {
      if (!rec || rec.sig !== sigByKey[sk]) return;
      const el = editorRef.current.querySelector(`[data-skey="${sk}"]`);
      if (el) el.innerHTML = rec.html;
    });
    recomputeWords();
  }, [html, sigByKey, recomputeWords]);

  const syncBar = useCallback(() => {
    // while the link editor is open, keep the toolbar exactly where it is — the
    // input has stolen focus/selection, but the toolbar must stay put (like any editor)
    if (linkEdRef.current) return;
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
    captureEdits();
  };
  // set the block format (paragraph / heading level) of the selection's block
  const block = (tag) => exec("formatBlock", tag);
  // clear formatting — strip bold/italic/etc. AND any link, back to normal text
  const clearFormatting = () => {
    document.execCommand("removeFormat", false);
    document.execCommand("unlink", false);
    editorRef.current?.focus();
    recomputeWords();
    captureEdits();
  };

  // the anchor the current selection sits inside (for editing an existing link)
  const selectionAnchor = () => {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return null;
    let n = sel.getRangeAt(0).startContainer;
    n = n.nodeType === 3 ? n.parentElement : n;
    return n?.closest ? n.closest("a") : null;
  };

  // open the inline link editor (NEVER window.prompt — it hijacks the whole UI)
  const openLinkEditor = () => {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return;
    savedRange.current = sel.getRangeAt(0).cloneRange();  // survive the input stealing focus
    const a = selectionAnchor();
    setLinkEd({
      top: (bar?.top ?? 0) + 44, left: bar?.left ?? 0,
      url: a?.getAttribute("href") || "",
      newTab: a ? a.getAttribute("target") === "_blank" : true,
    });
  };
  const closeLinkEditor = () => { savedRange.current = null; setLinkEd(null); };

  const restoreRange = () => {
    const sel = window.getSelection();
    if (savedRange.current && sel) { sel.removeAllRanges(); sel.addRange(savedRange.current); }
  };
  const applyLink = (url, newTab) => {
    const clean = (url || "").trim();
    if (!clean) { closeLinkEditor(); return; }
    restoreRange();
    document.execCommand("createLink", false, clean);
    // createLink can't set target — find the anchor we just made and flag it
    const a = selectionAnchor();
    if (a) {
      if (newTab) { a.setAttribute("target", "_blank"); a.setAttribute("rel", "noopener noreferrer"); }
      else { a.removeAttribute("target"); a.removeAttribute("rel"); }
    }
    recomputeWords();
    captureEdits();
    closeLinkEditor();
  };
  const removeLink = () => {
    restoreRange();
    document.execCommand("unlink", false);
    recomputeWords();
    captureEdits();
    closeLinkEditor();
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
        {onPublish && (
          <button type="button" className="asm-ws-next" onClick={onPublish}>
            {t("lpm.wordsmith.to_publish")}<Icon name="chevron-right" size={14} />
          </button>
        )}
      </div>
      <div className="asm-ws-canvas">
        <aside className="asm-ws-help">
          <div className="asm-ws-help-title">{t("lpm.wordsmith.help_title")}</div>
          <p className="asm-ws-help-body">{t("lpm.wordsmith.help")}</p>
        </aside>
        <div className="asm-ws-pagewrap" style={{ position: "relative" }}>
        {bar && (
          <div className="asm-ws-toolbar" style={{ top: bar.top, left: bar.left }} onMouseDown={(e) => e.preventDefault()}>
            <button type="button" className="asm-ws-tool" style={{ fontWeight: 800 }} title={t("lpm.wordsmith.tool.bold")} onClick={() => exec("bold")}>B</button>
            <button type="button" className="asm-ws-tool" style={{ fontStyle: "italic" }} title={t("lpm.wordsmith.tool.italic")} onClick={() => exec("italic")}>I</button>
            <span className="asm-ws-tool-sep" />
            <button type="button" className="asm-ws-tool asm-ws-tool-txt" title={t("lpm.wordsmith.tool.normal")} onClick={() => block("P")}>¶</button>
            <button type="button" className="asm-ws-tool asm-ws-tool-txt" title={t("lpm.wordsmith.tool.h1")} onClick={() => block("H1")}>H1</button>
            <button type="button" className="asm-ws-tool asm-ws-tool-txt" title={t("lpm.wordsmith.tool.h2")} onClick={() => block("H2")}>H2</button>
            <button type="button" className="asm-ws-tool asm-ws-tool-txt" title={t("lpm.wordsmith.tool.h3")} onClick={() => block("H3")}>H3</button>
            <button type="button" className="asm-ws-tool asm-ws-tool-txt" title={t("lpm.wordsmith.tool.h4")} onClick={() => block("H4")}>H4</button>
            <span className="asm-ws-tool-sep" />
            <button type="button" className="asm-ws-tool" title={t("lpm.wordsmith.tool.list")} onClick={() => exec("insertUnorderedList")}><Icon name="list-bullet" size={15} /></button>
            <button type="button" className="asm-ws-tool" title={t("lpm.wordsmith.tool.hr")} onClick={() => exec("insertHorizontalRule")}><Icon name="minus" size={16} /></button>
            <button type="button" className="asm-ws-tool" title={t("lpm.wordsmith.tool.link")} onClick={openLinkEditor}><Icon name="link" size={15} /></button>
            <span className="asm-ws-tool-sep" />
            <button type="button" className="asm-ws-tool" title={t("lpm.wordsmith.tool.clear")} onClick={clearFormatting}><Icon name="remove-formatting" size={15} /></button>
          </div>
        )}
        {linkEd && (
          <LinkEditor
            top={linkEd.top} left={linkEd.left} url={linkEd.url} newTab={linkEd.newTab}
            onApply={applyLink} onRemove={removeLink} onCancel={closeLinkEditor}
          />
        )}
        <div
          className="asm-ws-page lp-body"
          ref={editorRef}
          contentEditable
          suppressContentEditableWarning
          onInput={onInput}
          onMouseUp={syncBar}
          onKeyUp={syncBar}
        />
        </div>
      </div>
    </div>
  );
}

// Inline link editor — a small popover by the toolbar (NOT a browser prompt/dialog,
// which blocks and breaks the in-place editing). URL field + open-in-new-window.
function LinkEditor({ top, left, url, newTab, onApply, onRemove, onCancel }) {
  const [value, setValue] = useState(url || "");
  const [nt, setNt] = useState(!!newTab);
  const inputRef = useRef(null);
  useEffect(() => { inputRef.current?.focus(); inputRef.current?.select(); }, []);
  return (
    <div className="asm-ws-linkpop" style={{ top, left }}
      onMouseDown={(e) => e.stopPropagation()}>
      <div className="asm-ws-linkrow">
        <input
          ref={inputRef} className="asm-ws-linkinput" value={value}
          placeholder={t("lpm.wordsmith.link.placeholder")}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") { e.preventDefault(); onApply(value, nt); }
            if (e.key === "Escape") { e.preventDefault(); onCancel(); }
          }}
        />
        <button type="button" className="asm-ws-linkapply" onClick={() => onApply(value, nt)}>
          {t("lpm.wordsmith.link.apply")}
        </button>
        {url ? (
          <button type="button" className="asm-ws-linktext" onClick={onRemove}>
            {t("lpm.wordsmith.link.remove")}
          </button>
        ) : null}
        <button type="button" className="asm-ws-linkx" onClick={onCancel} aria-label="Cancel">
          <Icon name="x" size={14} />
        </button>
      </div>
      <label className="asm-ws-linknewtab">
        <input type="checkbox" checked={nt} onChange={(e) => setNt(e.target.checked)} />
        {t("lpm.wordsmith.link.newtab")}
      </label>
    </div>
  );
}
