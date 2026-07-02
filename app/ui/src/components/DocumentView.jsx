import React, { Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Group, Panel, Separator, useDefaultLayout } from "react-resizable-panels";
import { docUrl, pageUrl } from "../api.js";
import { setupSync } from "../syncScroll.js";
import DocToolbar from "./DocToolbar.jsx";
import { saveOrderAssertion, saveReorderOp, saveMergeOp, saveMergeAssertion,
         getSnapshot, saveAssertion } from "../api.js";
import { reportError } from "../errorBus.js";
import QuestionsPanel from "./QuestionsPanel.jsx";
import TocCompare from "./TocCompare.jsx";
import ReviewBoard from "./ReviewBoard.jsx";

// Puck is heavy (~90kB gzip); load the Landing Page Maker only when its tab opens
const LandingMaker = lazy(() => import("../landing/LandingMaker.jsx"));

// content-area views; "convert" is the full document view (html + pdf), the
// rest are alternate representations of the same content
const TABS = [
  { id: "convert", label: "Convert Document" },
  { id: "review", label: "Review" },
  { id: "toc", label: "TOC ⇔ Headings" },
  { id: "landing", label: "Landing Page" },
];

// injected into the iframe while editing reading order: a translucent tint +
// an up/down control on each reorderable element
const ORDER_CSS = `
.rk-order-mode [data-nid] { position: relative; }
.rk-order-mode .rk-order-item { outline: 1.5px solid rgba(43,74,117,.45);
  outline-offset: 1px; }
.rk-order-mode .rk-order-leaf { background: rgba(91,127,181,.10); }
.rk-order-ctl { position: absolute; top: 0; right: 0; z-index: 9; display: flex;
  gap: 2px; background: rgba(255,255,255,.92); border: 1px solid #b8cae3;
  border-radius: 5px; padding: 1px; box-shadow: 0 1px 3px rgba(0,0,0,.15); }
/* containers (a callout, a list) put their handle on the LEFT so it doesn't
   collide with the top-right handle of their first child */
.rk-order-container > .rk-order-ctl { right: auto; left: 0; border-color: #cdb48c;
  background: rgba(250,243,230,.95); }
.rk-order-ctl button { font: 13px/1 sans-serif; width: 22px; height: 20px;
  border: none; background: #eef3fa; color: #2c4a75; cursor: pointer;
  border-radius: 3px; }
.rk-order-container > .rk-order-ctl button { background: #faf3e6; color: #6b5320; }
.rk-order-ctl button:hover { filter: brightness(0.94); }
`;

const MARKER_CSS = `
.rk-qmark {
  display: inline-flex; align-items: center; justify-content: center;
  width: 1.1rem; height: 1.1rem; margin-right: 0.4rem;
  border-radius: 50%; border: 1px solid #b58900; background: #fdf3d7;
  color: #8a6d00; font: 700 0.75rem/1 sans-serif; cursor: pointer;
  vertical-align: text-top;
  /* out of flow so the marker's glyph doesn't steal ::first-letter from
     the element's real first letter (drop caps vanished on noted paras) */
  float: left;
}
.rk-qmark.rk-resolved { border-color: #2e7d32; background: #e6f2e6; color: #2e7d32; }
.rk-feedback-mode, .rk-feedback-mode * { cursor: crosshair !important; }
.rk-flash { outline: 2px solid #d99a06; transition: outline 0.8s; }
.rk-active {
  outline: 2px dashed #b58900 !important;
  outline-offset: 4px;
  background: rgba(253, 243, 215, 0.35);
}
.rk-fbmark {
  display: inline-flex; align-items: center; justify-content: center;
  width: 1.1rem; height: 1.1rem; margin-right: 0.4rem;
  border-radius: 3px; border: 1px solid #5b7fb5; background: #e2ecf8;
  color: #2c4a75; font: 700 0.7rem/1 sans-serif; cursor: help;
  vertical-align: text-top;
  float: left; /* see .rk-qmark: keep ::first-letter on the real first letter */
}
.rk-fbmark.rk-resolved { border-color: #999; background: #eee; color: #777; }
.rk-assert-sel { outline: 2px dashed #0a7d6b !important; outline-offset: 3px; }
`;

export default function DocumentView({
  doc, buildId = null, toggles, setToggles, questions, answers, feedback, ops, pageDims, onConvert, onAnnotate,
  onQuestion, onClearNote, onEmptyTrash, onRemoveOp, highlightNid,
  docVersion = 0, flashNid = null, deepLinkNid = null, onConsumeDeepLink,
  fontsComplete = null, onPersistEmbed, ir = null,
}) {
  const iframeRef = useRef(null);
  const pdfPaneRef = useRef(null);
  const [frameLoaded, setFrameLoaded] = useState(false);
  // embedded-fonts state is driven by the iframe's css-embed link (render bakes
  // in the per-doc default: auto-verdict or saved override), so it survives
  // reconversions; the checkbox reads it on load and writes it on toggle.
  const [embed, setEmbed] = useState({ has: false, on: false });
  const [tab, setTab] = useState("convert");
  // jump-to-node requests from the questions panel (now rendered inside this view)
  const [scrollToNid, setScrollToNid] = useState(null);
  // persists the content|pdf divider position to localStorage
  const splitLayout = useDefaultLayout({ id: "rk3-content-split", panelIds: ["content", "pdf"] });
  const savedScroll = useRef(null);
  // cache-bust key: in-app edits bump docVersion; a CLI/agent rebuild changes
  // buildId (the on-disk render fingerprint). Either reloads the iframe.
  const bust = `${docVersion}-${buildId || ""}`;
  const prevBust = useRef(bust);

  // capture the reading position first so the user stays exactly where they were
  if (bust !== prevBust.current) {
    prevBust.current = bust;
    const win = iframeRef.current?.contentWindow;
    savedScroll.current = { y: win ? win.scrollY : 0 };
    setFrameLoaded(false);  // render-phase reset: effects rebind on new load
  }

  useEffect(() => {
    if (!frameLoaded || !savedScroll.current) return;
    const win = iframeRef.current?.contentWindow;
    const idoc = iframeRef.current?.contentDocument;
    if (win) win.scrollTo(0, savedScroll.current.y);
    savedScroll.current = null;
    if (flashNid && idoc) {
      const el = idoc.querySelector(`[data-nid="${flashNid}"]`);
      if (el) {
        el.classList.add("rk-flash");
        setTimeout(() => el.classList.remove("rk-flash"), 1500);
      }
    }
  }, [frameLoaded, flashNid]);

  // refs so iframe-side handlers never see stale state
  const stateRef = useRef({});
  stateRef.current = { toggles, questions, answers, feedback, onAnnotate, onQuestion };

  // assert mode: click an element -> mint an eval assertion (freeze / heading
  // level / list). Shift-click multi-selects elements for a list assertion.
  const [assertPop, setAssertPop] = useState(null);   // {x, y, nid, snippet}
  const [assertSel, setAssertSel] = useState([]);     // [{nid, snippet}]
  const [assertMsg, setAssertMsg] = useState(null);   // {ok, text, force?}
  const [freezePrev, setFreezePrev] = useState(null); // snapshot preview html

  // an element's text with viewer markers excluded — the assertion anchor
  const elSnippet = (el) => {
    const clone = el.cloneNode(true);
    for (const m of clone.querySelectorAll(".rk-qmark,.rk-fbmark,.rk-order-ctl"))
      m.remove();
    return clone.textContent.replace(/\s+/g, " ").trim().slice(0, 60);
  };

  const clearAssertSel = useCallback(() => {
    const idoc = iframeRef.current?.contentDocument;
    if (idoc) for (const el of idoc.querySelectorAll(".rk-assert-sel"))
      el.classList.remove("rk-assert-sel");
    setAssertSel([]);
  }, []);

  const mintAssertion = async (check, allowForce = true) => {
    try {
      const res = await saveAssertion(doc.slug, check);
      if (res.saved) {
        setAssertMsg({ ok: true, text: `Saved ✓ — ${res.total} checks on this doc` });
      } else {
        setAssertMsg({
          ok: false,
          text: `Currently FAILS: ${res.detail}`,
          force: allowForce ? async () => {
            const r2 = await saveAssertion(doc.slug, check, true);
            setAssertMsg({ ok: true, text: `Saved as regression target ✓ — ${r2.total} checks` });
          } : null,
        });
      }
    } catch (e) { reportError("save assertion", e); }
  };

  const doFreeze = async () => {
    try {
      const snap = await getSnapshot(doc.slug, assertPop.nid);
      setFreezePrev(snap.html);
      await mintAssertion({
        freeze: snap, stage: "analyze",
        note: `freeze: ${snap.anchor.slice(0, 44)}`,
      }, false);
    } catch (e) { reportError("freeze assertion", e); }
  };

  const doRole = (level) => mintAssertion(level
    ? { role: { text: assertPop.snippet, is: "heading", level }, stage: "analyze",
        note: `h${level}: ${assertPop.snippet.slice(0, 40)}` }
    : { role: { text: assertPop.snippet, is: "not-heading" }, stage: "analyze",
        note: `not a heading: ${assertPop.snippet.slice(0, 40)}` });

  const doList = async () => {
    // items in DOCUMENT order regardless of click order
    const idoc = iframeRef.current?.contentDocument;
    const ordered = [...assertSel].sort((a, b) => {
      const ea = idoc?.querySelector(`[data-nid="${a.nid}"]`);
      const eb = idoc?.querySelector(`[data-nid="${b.nid}"]`);
      if (!ea || !eb) return 0;
      return ea.compareDocumentPosition(eb) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1;
    });
    await mintAssertion({
      list: ordered.map((s) => s.snippet), stage: "analyze",
      note: `${ordered.length} items form one list: ${ordered[0].snippet.slice(0, 30)}…`,
    });
    clearAssertSel();
  };

  // an element's existing open note, so a second click edits instead of duplicating
  const findExisting = (nid, rk) =>
    (stateRef.current.feedback ?? []).find(
      (f) => f.type === "comment" && f.status === "open"
        && ((f.nid && f.nid === nid) || (!f.nid && f.rk && f.rk === rk)));

  const failed = doc.status === "failed";

  // layer-3 CSS toggle
  useEffect(() => {
    const link = iframeRef.current?.contentDocument?.getElementById("css-original");
    if (link) link.disabled = !toggles.layer3;
  }, [toggles.layer3, frameLoaded]);

  // read the embed default the render baked into the css-embed link (present
  // only when the doc has embeddable fonts); sync the checkbox to it on load
  useEffect(() => {
    const link = iframeRef.current?.contentDocument?.getElementById("css-embed");
    setEmbed({ has: !!link, on: link ? !link.disabled : false });
  }, [frameLoaded]);

  // toggling flips the layer live (off => "PDFEmbed X" vars vanish, rules fall
  // back to the guessed font) and persists the choice to the doc's config
  const toggleEmbed = useCallback((on) => {
    const link = iframeRef.current?.contentDocument?.getElementById("css-embed");
    if (link) link.disabled = !on;
    setEmbed((e) => ({ ...e, on }));
    onPersistEmbed?.(on);
  }, [onPersistEmbed]);

  // ----- inline reading-order editing (overlay up/down on each element) -----
  const [orderEdit, setOrderEdit] = useState(false);
  const [orderMsg, setOrderMsg] = useState(null);
  const dirtyPages = useRef(new Set());
  const merges = useRef([]);  // [{into, frm}] folds queued in this edit session
  const textByNid = useMemo(() => {
    const m = {};
    const walk = (nodes) => {
      for (const n of nodes || []) {
        m[n.nid] = n.text || n.title || `[${n.type}]`;
        walk(n.children);
      }
    };
    walk(ir?.body);
    return m;
  }, [ir]);
  // the engine's leaf reading order (no children), to detect which adjacencies
  // the user actually fixed — we only assert those (the eval order check is a
  // strict A-before-B pair)
  const irLeafOrder = useMemo(() => {
    const out = [];
    const walk = (nodes, page) => {
      for (const n of nodes || []) {
        const pg = n.page ?? page;
        if (n.children?.length) walk(n.children, pg);
        else out.push({ nid: n.nid, page: pg });
      }
    };
    walk(ir?.body, null);
    return out;
  }, [ir]);

  useEffect(() => {
    const idoc = iframeRef.current?.contentDocument;
    if (!idoc?.body || !frameLoaded) return;
    if (!orderEdit) {
      idoc.body.classList.remove("rk-order-mode");
      idoc.querySelectorAll(".rk-order-ctl").forEach((c) => c.remove());
      idoc.querySelectorAll(".rk-order-item").forEach((e) => e.classList.remove("rk-order-item", "rk-order-container", "rk-order-leaf"));
      return;
    }
    if (!idoc.getElementById("rk-order-style")) {
      const s = idoc.createElement("style");
      s.id = "rk-order-style";
      s.textContent = ORDER_CSS;
      idoc.head.appendChild(s);
    }
    idoc.body.classList.add("rk-order-mode");
    dirtyPages.current = new Set();
    merges.current = [];
    // a reorderable element's siblings are the OTHER [data-nid] elements with
    // the same parent — so this works at any level (top-level OR inside a
    // callout/list). The injected handle is a non-[data-nid] child, so it never
    // counts as a sibling.
    const reSib = (el, dir) => {
      let s = dir < 0 ? el.previousElementSibling : el.nextElementSibling;
      while (s && !s.dataset?.nid) s = dir < 0 ? s.previousElementSibling : s.nextElementSibling;
      return s;
    };
    const move = (el, dir) => {
      const sib = reSib(el, dir);
      if (!sib) return;
      if (dir < 0) el.parentNode.insertBefore(el, sib);
      else el.parentNode.insertBefore(sib, el);
      for (const e of [el, sib]) if (e.dataset.page) dirtyPages.current.add(+e.dataset.page);
      el.scrollIntoView({ block: "nearest" });
    };
    // merge this element with the next leaf: pull its content in (space-joined),
    // record the fold, remove it from the DOM
    const mergeDown = (el) => {
      const sib = reSib(el, 1);
      if (!sib || sib.querySelector("[data-nid]")) return;  // next must be a leaf
      const elCtl = el.querySelector(":scope > .rk-order-ctl");
      el.insertBefore(idoc.createTextNode(" "), elCtl);
      for (const node of [...sib.childNodes]) {
        if (node.classList?.contains("rk-order-ctl")) continue;
        el.insertBefore(node, elCtl);
      }
      merges.current.push({ into: el.dataset.nid, frm: sib.dataset.nid });
      if (el.dataset.page) dirtyPages.current.add(+el.dataset.page);
      sib.remove();
    };
    for (const el of idoc.querySelectorAll("[data-nid]")) {
      const container = !!el.querySelector("[data-nid]");
      el.classList.add("rk-order-item", container ? "rk-order-container" : "rk-order-leaf");
      const ctl = idoc.createElement("div");
      ctl.className = "rk-order-ctl";
      ctl.setAttribute("contenteditable", "false");
      const btns = [[() => move(el, -1), "↑", "Move up"], [() => move(el, 1), "↓", "Move down"]];
      if (!container) btns.push([() => mergeDown(el), "⊕", "Merge with the element below"]);
      for (const [fn, glyph, title] of btns) {
        const b = idoc.createElement("button");
        b.textContent = glyph;
        b.title = title;
        b.onclick = (e) => { e.preventDefault(); e.stopPropagation(); fn(); };
        ctl.appendChild(b);
      }
      el.appendChild(ctl);
    }
    return () => {
      idoc.body.classList.remove("rk-order-mode");
      idoc.querySelectorAll(".rk-order-ctl").forEach((c) => c.remove());
      idoc.querySelectorAll(".rk-order-item").forEach((e) => e.classList.remove("rk-order-item", "rk-order-container", "rk-order-leaf"));
    };
  }, [orderEdit, frameLoaded]);

  // every [data-nid] in document (= reading) order, at all nesting levels; the
  // `leaf` ones (no nested [data-nid]) are the actual content sequence we assert
  const _orderSeq = () => {
    const idoc = iframeRef.current?.contentDocument;
    return [...(idoc?.querySelectorAll("[data-nid]") || [])].map((e) => ({
      nid: e.dataset.nid, page: +e.dataset.page || null,
      leaf: !e.querySelector("[data-nid]"),
    }));
  };
  const enterOrderEdit = () => {
    setToggles((t) => ({ ...t, feedbackMode: false, assertMode: false }));  // modes are exclusive
    setOrderMsg(null);
    setOrderEdit(true);
  };
  const reloadFrame = () => iframeRef.current?.contentWindow?.location.reload();
  const cancelOrder = () => { setOrderEdit(false); reloadFrame(); };
  const clean = (nid) => (textByNid[nid] || "").replace(/\s+/g, " ").trim();
  const saveOrder = async () => {
    const cur = _orderSeq().filter((x) => x.leaf);
    const origIdx = {};
    irLeafOrder.forEach((x, i) => { origIdx[x.nid] = i; });
    let n = 0, skipped = 0;
    for (const pg of dirtyPages.current) {
      const leaves = cur.filter((x) => x.page === pg);
      for (let i = 0; i < leaves.length - 1; i++) {
        const X = leaves[i].nid, Y = leaves[i + 1].nid;
        // assert only an adjacency the user FIXED (X was after Y before)
        if (origIdx[X] == null || origIdx[Y] == null || origIdx[X] <= origIdx[Y]) continue;
        const tx = clean(X).slice(0, 45), ty = clean(Y).slice(0, 45);
        if (!tx || !ty || tx.startsWith("[") || ty.startsWith("[")) { skipped++; continue; }
        await saveOrderAssertion(doc.slug, [tx, ty], `reads before (p${pg})`)
          .then(() => n++).catch((e) => reportError("save order assertion", e));
      }
    }
    let m = 0;
    for (const { into, frm } of merges.current) {
      const a = clean(into).slice(0, 45), b = clean(frm).slice(0, 45);
      if (a && b && !a.startsWith("[") && !b.startsWith("["))
        await saveMergeAssertion(doc.slug, a, b).then(() => m++)
          .catch((e) => reportError("save merge assertion", e));
    }
    setOrderEdit(false);
    setOrderMsg([n && `${n} order`, m && `${m} merge`].filter(Boolean).join(" + ")
      ? `Saved ${[n && `${n} order`, m && `${m} merge`].filter(Boolean).join(" + ")} assertion(s).`
      : "No changes to save.");
    reloadFrame();
  };
  const fixOrder = async () => {
    await saveReorderOp(doc.slug, _orderSeq().map((x) => x.nid))
      .catch((e) => reportError("apply reorder", e));
    for (const { into, frm } of merges.current)
      await saveMergeOp(doc.slug, into, frm).catch((e) => reportError("apply merge", e));
    setOrderEdit(false);
    setOrderMsg("Applied — reconverting…");
  };

  // sync scroll
  useEffect(() => {
    if (!frameLoaded || !pdfPaneRef.current) return;
    const win = iframeRef.current.contentWindow;
    const idoc = iframeRef.current.contentDocument;
    if (!win || !idoc) return;
    return setupSync(win, idoc, pdfPaneRef.current,
      () => stateRef.current.toggles.sync && stateRef.current.toggles.showPdf);
  }, [frameLoaded, toggles.showPdf]);

  // feedback-mode click capture + cursor inside the iframe
  useEffect(() => {
    if (!frameLoaded) return;
    const idoc = iframeRef.current.contentDocument;
    if (!idoc) return;
    const onClick = (e) => {
      const s = stateRef.current;
      if (!s.toggles.feedbackMode) return;
      if (e.target.closest(".rk-qmark")) return; // markers handle themselves
      e.preventDefault();
      e.stopPropagation();
      let el = e.target.closest("[data-nid],[data-rk]");
      if (!el) {
        // click landed in the whitespace between elements: snap to the
        // vertically nearest anchored element (within 80px)
        let best = null, dist = 80;
        for (const cand of idoc.querySelectorAll("[data-nid]")) {
          const r = cand.getBoundingClientRect();
          const d = e.clientY < r.top ? r.top - e.clientY
                  : e.clientY > r.bottom ? e.clientY - r.bottom : 0;
          if (d < dist) { best = cand; dist = d; }
        }
        el = best;
      }
      const rect = iframeRef.current.getBoundingClientRect();
      const target = el
        ? { nid: el.dataset.nid, rk: el.dataset.rk, page: +el.dataset.page || null }
        : { page: null };
      // drag-selected text narrows the note to a span within the element;
      // offsets are relative to the node's text (viewer markers excluded)
      const sel = idoc.getSelection();
      if (el && sel && !sel.isCollapsed && el.contains(sel.anchorNode)) {
        const range = sel.getRangeAt(0);
        const pre = idoc.createRange();
        pre.selectNodeContents(el);
        pre.setEnd(range.startContainer, range.startOffset);
        let start = pre.toString().length;
        for (const m of el.querySelectorAll(".rk-qmark,.rk-fbmark")) {
          if (pre.intersectsNode(m)) start -= m.textContent.length;
        }
        const text = sel.toString();
        target.selText = text.slice(0, 300);
        target.selStart = Math.max(0, start);
        target.selEnd = Math.max(0, start) + text.length;
      }
      s.onAnnotate(
        target,
        { x: rect.left + e.clientX, y: rect.top + e.clientY },
        el ? findExisting(el.dataset.nid, el.dataset.rk) : null,
      );
    };
    idoc.addEventListener("click", onClick, true);
    return () => idoc.removeEventListener("click", onClick, true);
  }, [frameLoaded]);

  // assert-mode click capture: plain click opens the assert popup, shift-click
  // multi-selects elements for a list assertion
  useEffect(() => {
    if (!frameLoaded) return;
    const idoc = iframeRef.current.contentDocument;
    if (!idoc) return;
    const onClick = (e) => {
      if (!stateRef.current.toggles.assertMode) return;
      e.preventDefault();
      e.stopPropagation();
      const el = e.target.closest("[data-nid]");
      if (!el) return;
      const snippet = elSnippet(el);
      if (e.shiftKey) {
        const on = el.classList.toggle("rk-assert-sel");
        setAssertSel((sel) => on
          ? [...sel, { nid: el.dataset.nid, snippet }]
          : sel.filter((s) => s.nid !== el.dataset.nid));
        return;
      }
      const rect = iframeRef.current.getBoundingClientRect();
      setFreezePrev(null);
      setAssertMsg(null);
      setAssertPop({
        x: Math.min(rect.left + e.clientX, window.innerWidth - 360),
        y: rect.top + e.clientY - (iframeRef.current.contentWindow?.scrollY ? 0 : 0),
        nid: el.dataset.nid, snippet,
      });
    };
    idoc.addEventListener("click", onClick, true);
    return () => idoc.removeEventListener("click", onClick, true);
  }, [frameLoaded]);

  useEffect(() => {
    const idoc = iframeRef.current?.contentDocument;
    if (!idoc?.body) return;
    idoc.body.classList.toggle("rk-feedback-mode",
      toggles.feedbackMode || toggles.assertMode);
  }, [toggles.feedbackMode, toggles.assertMode, frameLoaded]);

  // question markers, re-injected when questions/answers change
  useEffect(() => {
    if (!frameLoaded) return;
    const idoc = iframeRef.current.contentDocument;
    if (!idoc?.body) return;
    if (!idoc.getElementById("rk-viewer-style")) {
      const style = idoc.createElement("style");
      style.id = "rk-viewer-style";
      style.textContent = MARKER_CSS;
      idoc.head.appendChild(style);
    }
    idoc.querySelectorAll(".rk-qmark").forEach((m) => m.remove());
    for (const q of questions) {
      const el = idoc.querySelector(`[data-nid="${q.nid}"]`);
      if (!el) continue;
      const btn = idoc.createElement("button");
      btn.className = "rk-qmark" + (answers.has(q.qid) ? " rk-resolved" : "");
      btn.textContent = answers.has(q.qid) ? "✓" : "?";
      btn.title = q.prompt;
      btn.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        const rect = iframeRef.current.getBoundingClientRect();
        const r = btn.getBoundingClientRect();
        stateRef.current.onQuestion(q, { x: rect.left + r.left, y: rect.top + r.bottom + 4 });
      };
      el.prepend(btn);
    }
  }, [frameLoaded, questions, answers]);

  // markers where feedback was already left, so spots aren't annotated twice
  useEffect(() => {
    if (!frameLoaded) return;
    const idoc = iframeRef.current.contentDocument;
    if (!idoc?.body) return;
    idoc.querySelectorAll(".rk-fbmark").forEach((m) => m.remove());
    for (const f of feedback ?? []) {
      if (f.type !== "comment" || f.status === "cleared") continue;
      const target = (f.nid && idoc.querySelector(`[data-nid="${f.nid}"]`))
        || (f.rk && idoc.querySelector(`[data-rk="${f.rk}"]`));
      if (!target) continue;
      const mark = idoc.createElement("span");
      mark.className = "rk-fbmark" + (f.status === "resolved" ? " rk-resolved" : "");
      mark.textContent = f.status === "resolved" ? "✓" : "✎";
      mark.title = (f.status === "resolved" ? "Resolved: " : "Your note (click to edit): ") + f.text;
      if (f.status !== "resolved") {
        mark.style.cursor = "pointer";
        mark.onclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          const rect = iframeRef.current.getBoundingClientRect();
          const r = mark.getBoundingClientRect();
          stateRef.current.onAnnotate(
            { nid: f.nid, rk: f.rk, page: f.page },
            { x: rect.left + r.left, y: rect.top + r.bottom + 4 }, f);
        };
      }
      target.prepend(mark);
    }
  }, [frameLoaded, feedback]);

  // outline the element a question/feedback popover refers to, so its extent
  // is unambiguous (e.g. a full-page callout)
  useEffect(() => {
    if (!frameLoaded || !highlightNid) return;
    const el = iframeRef.current.contentDocument
      ?.querySelector(`[data-nid="${highlightNid}"]`);
    if (!el) return;
    el.classList.add("rk-active");
    return () => el.classList.remove("rk-active");
  }, [frameLoaded, highlightNid]);

  // deep link (new window from the All Feedback table): once the frame is up,
  // scroll to the linked element — reusing the questions-panel jump path
  useEffect(() => {
    if (frameLoaded && deepLinkNid) {
      setScrollToNid(deepLinkNid);
      onConsumeDeepLink?.();
    }
  }, [frameLoaded, deepLinkNid]);

  // jump-to-node requests from the questions panel
  useEffect(() => {
    if (!scrollToNid || !frameLoaded) return;
    const idoc = iframeRef.current.contentDocument;
    const el = idoc?.querySelector(`[data-nid="${scrollToNid}"]`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("rk-flash");
      setTimeout(() => el.classList.remove("rk-flash"), 1200);
    }
    setScrollToNid(null);
  }, [scrollToNid, frameLoaded]);

  const onPdfClick = (e) => {
    if (!stateRef.current.toggles.feedbackMode) return;
    const img = e.target.closest("img[data-page]");
    if (!img) return;
    const r = img.getBoundingClientRect();
    onAnnotate(
      { page: +img.dataset.page,
        xf: +((e.clientX - r.left) / r.width).toFixed(4),
        yf: +((e.clientY - r.top) / r.height).toFixed(4) },
      { x: e.clientX, y: e.clientY },
    );
  };

  const pdfPane = doc.pages > 0 && toggles.showPdf && (
    <div
      className={"pdfpane" + (doc.status !== "done" ? " solo" : "")}
      ref={pdfPaneRef}
      onClick={onPdfClick}
      style={toggles.feedbackMode ? { cursor: "crosshair" } : undefined}
    >
      {Array.from({ length: doc.pages }, (_, i) => {
        const spots = (feedback ?? []).filter(
          (f) => f.type === "comment" && f.status !== "cleared"
            && f.xf != null && f.page === i + 1);
        const dims = pageDims?.[String(i + 1)];
        return (
          <div key={i + 1} className="pagewrap">
            <img
              src={pageUrl(doc.slug, i + 1)}
              data-page={i + 1}
              alt={`page ${i + 1}`}
              // true page proportions before the PNG loads, so sync-scroll
              // anchors are correct from the first frame
              style={dims ? { aspectRatio: `${dims[0]} / ${dims[1]}` } : undefined}
            />
            {spots.map((f, k) => (
              <span
                key={k}
                className={"fb-spot" + (f.status === "resolved" ? " resolved" : "")}
                style={{ left: `${f.xf * 100}%`, top: `${f.yf * 100}%` }}
                title={(f.status === "resolved" ? "Resolved: " : "Your note (click to edit): ") + f.text}
                onClick={f.status === "resolved" ? undefined : (e) => {
                  e.stopPropagation();
                  onAnnotate({ page: f.page, xf: f.xf, yf: f.yf },
                             { x: e.clientX, y: e.clientY }, f);
                }}
              >
                {f.status === "resolved" ? "✓" : "✎"}
              </span>
            ))}
          </div>
        );
      })}
    </div>
  );

  if (doc.status === "done") {
    return (
      <div className="docview">
        <div className="tabs" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              className={"tab" + (tab === t.id ? " active" : "")}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Convert Document: kept mounted (display-toggled) so the iframe's
            scroll position, markers and sync survive tab switches */}
        <div className="convert-tab" style={{ display: tab === "convert" ? "flex" : "none" }}>
          <DocToolbar
            doc={doc}
            toggles={toggles}
            setToggles={setToggles}
            embed={embed}
            fontsComplete={fontsComplete}
            onToggleEmbed={toggleEmbed}
            orderEdit={orderEdit}
            orderMsg={orderMsg}
            onEnterOrderEdit={enterOrderEdit}
            onSaveOrder={saveOrder}
            onFixOrder={fixOrder}
            onCancelOrder={cancelOrder}
            questionCount={questions.length}
            answeredCount={questions.filter((q) => answers.has(q.qid)).length}
          />
          <div className="convert-body">
            <Group
              orientation="horizontal"
              className="split"
              style={{ flex: 1, minWidth: 0, minHeight: 0, height: "auto" }}
              defaultLayout={splitLayout.defaultLayout}
              onLayoutChanged={splitLayout.onLayoutChanged}
            >
              <Panel id="content" minSize="20%" className="content-panel">
                <iframe
                  title={doc.name}
                  ref={iframeRef}
                  src={docUrl(doc.slug) + `?v=${encodeURIComponent(bust)}`}
                  onLoad={() => setFrameLoaded(true)}
                />
                {assertPop && (
                  <div className="assert-pop"
                    style={{ left: assertPop.x, top: Math.min(assertPop.y, window.innerHeight - 260) }}>
                    <div className="ap-head">
                      <span className="ap-snippet">“{assertPop.snippet.slice(0, 46)}…”</span>
                      <button className="ap-close"
                        onClick={() => { setAssertPop(null); setAssertMsg(null); }}>✕</button>
                    </div>
                    <div className="ap-row">
                      <button className="ap-freeze" onClick={doFreeze}
                        title="Lock this element's exact content + markup (text, bold/italic, links, structure) as a permanent check">
                        ❄ Freeze content
                      </button>
                    </div>
                    <div className="ap-row ap-role">
                      <span>heading:</span>
                      {[1, 2, 3, 4].map((l) => (
                        <button key={l} onClick={() => doRole(l)}>h{l}</button>
                      ))}
                      <button onClick={() => doRole(null)}>not one</button>
                    </div>
                    {assertSel.length >= 2 && (
                      <div className="ap-row">
                        <button onClick={doList}>☰ These {assertSel.length} are one list</button>
                        <button onClick={clearAssertSel}>clear</button>
                      </div>
                    )}
                    {assertSel.length < 2 && (
                      <div className="ap-hint">shift-click elements to assert a list</div>
                    )}
                    {freezePrev && <pre className="ap-preview">{freezePrev}</pre>}
                    {assertMsg && (
                      <div className={"ap-msg " + (assertMsg.ok ? "ok" : "bad")}>
                        {assertMsg.text}
                        {assertMsg.force && (
                          <button onClick={assertMsg.force}>Save anyway (regression target)</button>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </Panel>
              {pdfPane && <Separator className="resizer" />}
              {pdfPane && (
                <Panel id="pdf" defaultSize="50%" minSize="20%" className="pdf-panel">
                  {pdfPane}
                </Panel>
              )}
            </Group>
            {toggles.panelOpen && (
              <QuestionsPanel
                questions={questions}
                answers={answers}
                feedback={feedback}
                ops={ops}
                onJump={(nid) => setScrollToNid(nid)}
                onAnswer={(q) => onQuestion(q, { x: window.innerWidth / 2, y: 160 })}
                onClear={onClearNote}
                onEmptyTrash={onEmptyTrash}
                onRemoveOp={onRemoveOp}
              />
            )}
          </div>
        </div>

        {tab === "review" && <ReviewBoard slug={doc.slug} />}

        {tab === "toc" && <TocCompare slug={doc.slug} />}

        {tab === "landing" && (
          <Suspense fallback={<div className="hint" style={{ padding: "2rem" }}>Loading editor…</div>}>
            <LandingMaker doc={doc} />
          </Suspense>
        )}
      </div>
    );
  }

  if (doc.status === "in_progress") {
    return (
      <div className="pane">
        <p>Conversion in progress…</p>
        <p className="hint">No live progress in v1 — use Refresh to check.</p>
      </div>
    );
  }

  return (
    <div className="failpane">
      <div className="pane">
        {failed && (
          <>
            <p><strong>Conversion failed.</strong></p>
            <pre className="error">{doc.error || "unknown error"}</pre>
          </>
        )}
        <button className="action" onClick={() => onConvert(doc.slug, failed)}>
          {failed ? "Retry conversion" : "Convert"}
        </button>
      </div>
      {pdfPane}
    </div>
  );
}
