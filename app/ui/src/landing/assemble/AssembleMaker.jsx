import React, { useCallback, useEffect, useState } from "react";
import "./assemble.css";
import "../landingPage.css"; // block-render styles, reused by the previews + Wordsmith
import { getBlockDefaults, getAiSummary } from "../../api.js";
import { loadContent } from "../../content.js";
import { guard } from "../../errorBus.js";
import { LENGTHS, SUMMARY_LENGTH, defaultSectionOn } from "./model.js";
import Chrome from "./Chrome.jsx";
import SectionLibrary from "./SectionLibrary.jsx";
import Inspector from "./Inspector.jsx";
import Controls from "./Controls.jsx";
import Wordsmith from "./Wordsmith.jsx";

const getSections = (slug) =>
  fetch(`/api/landing/${slug}/sections`).then((r) => r.json());

// Content-first Landing Page Maker (the AI-sections rebuild, BACKLOG/61). The
// sections engine proposes the document's meaningful sections in its own words;
// the user picks which to keep, adjusts each section's presentation, then fixes
// the wording in Wordsmith. "Highlights" = the AI sections (the star of the
// screen); the CTA scaffolding sits beside them.
export default function AssembleMaker({ doc }) {
  const slug = doc.slug;
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(null);
  const [docRead, setDocRead] = useState(null);   // {whatItIs,audience,coreMessage}
  const [noai, setNoai] = useState(false);
  const [genError, setGenError] = useState(null); // AI on but generation failed
  const [defs, setDefs] = useState(null);          // title/cover/CTA defaults

  const [mode, setMode] = useState("assemble");
  const [sections, setSections] = useState([]);    // [{id, on, presentation, ...content}]
  const [sel, setSel] = useState(null);            // section id | cta key | "ai-summary"
  const [length, setLength] = useState("middle");
  const [cover, setCover] = useState("beside");
  const [cta, setCta] = useState({ download: true, secondary: false, share: true });
  // the opt-in AI Summary — the ONE AI-written section (a pitch in a chosen voice)
  const [ai, setAi] = useState({ on: false, voice: "neutral", prose: "", loading: false });

  useEffect(() => {
    let alive = true;
    setReady(false); setError(null);
    setAi({ on: false, voice: "neutral", prose: "", loading: false });
    loadContent("lpm")
      .then(() => Promise.all([
        getSections(slug).catch(guard("assemble: sections", null)),
        getBlockDefaults(slug).catch(guard("assemble: block defaults", null)),
      ]))
      .then(([sd, defaults]) => {
        if (!alive) return;
        const art = sd?.sections || {};
        const rec = art.recommendedPage || {};
        const len = LENGTHS.includes(rec.length) ? rec.length : "middle";
        const raw = art.sections || [];
        const on = defaultSectionOn(raw, len);
        const secs = raw.map((s, i) => ({
          id: `sec-${i}`,
          heading: s.heading, summary: s.summary, role: s.role, presentation: s.presentation,
          page: s.page, strength: s.strength, verbatim: s.verbatim,
          prose: s.prose, bullets: s.bullets, cards: s.cards, quote: s.quote, steps: s.steps,
          on: on[i],
        }));
        setSections(secs);
        setDocRead(art.documentRead || null);
        setNoai(!!sd?.noai);
        setGenError(sd?.error || null);
        setDefs(defaults || {});
        setLength(len);
        setCover(rec.cover || "beside");
        setCta({
          download: true, secondary: false, share: true,
          downloadLabel: defaults?.download?.label || "",
          secondaryLabel: defaults?.secondaryCta?.label || "",
        });
        setSel(secs.find((s) => s.on)?.id || secs[0]?.id || "download");
        setReady(true);
      })
      .catch((e) => { if (alive) { setError(e); setReady(true); } });
    return () => { alive = false; };
  }, [slug]);

  const changeLength = useCallback((next) => {
    setLength(next);
    setSections((prev) => {
      const on = defaultSectionOn(prev, next);
      return prev.map((s, i) => ({ ...s, on: on[i] }));
    });
  }, []);

  const toggleSection = useCallback((id) => {
    setSections((prev) => prev.map((s) => (s.id === id ? { ...s, on: !s.on } : s)));
  }, []);

  const setPresentation = useCallback((id, presentation) => {
    setSections((prev) => prev.map((s) => (s.id === id ? { ...s, presentation } : s)));
  }, []);

  const setQuotePull = useCallback((id, pull) => {
    setSections((prev) => prev.map((s) =>
      (s.id === id ? { ...s, quote: { ...s.quote, pull } } : s)));
  }, []);

  const toggleCta = useCallback((key) => {
    setCta((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const toggleAi = useCallback(() => setAi((a) => ({ ...a, on: !a.on })), []);

  // fetch (lazily) the AI-written summary for a voice at the current length
  const fetchAiVoice = useCallback((voice) => {
    setAi((a) => ({ ...a, voice, loading: true }));
    getAiSummary(slug, voice, SUMMARY_LENGTH[length] || "medium")
      .then((text) => setAi((a) => (a.voice === voice
        ? { ...a, loading: false, prose: text ? text.split(/\n\n+/).map((p) => `<p>${p.trim()}</p>`).join("") : "" }
        : a)))
      .catch(() => setAi((a) => ({ ...a, loading: false })));
  }, [slug, length]);

  const title = defs?.title || null;
  const coverAsset = defs?.cover || null;

  if (!ready) return <div className="asm-root"><div className="asm-loading">Loading editor…</div></div>;

  return (
    <div className="asm-root">
      <Chrome
        title={doc.name || doc.slug}
        activeIdx={mode === "wordsmith" ? 1 : 0}
        onStep={(i) => setMode(i === 1 ? "wordsmith" : "assemble")}
      />
      {mode === "wordsmith" ? (
        <Wordsmith
          slug={slug} title={title} coverAsset={coverAsset} cover={cover}
          sections={sections} cta={cta} ai={ai} onBack={() => setMode("assemble")}
        />
      ) : (
        <div className="asm-grid">
          <SectionLibrary
            sections={sections} cta={cta} ai={ai} sel={sel} noai={noai} genError={genError}
            docRead={docRead} onSelect={setSel}
          />
          <Inspector
            sel={sel} sections={sections} cta={cta} ai={ai} defs={defs}
            slug={slug} length={length}
            onToggleSection={toggleSection} onToggleCta={toggleCta}
            onSetPresentation={setPresentation} onSetQuotePull={setQuotePull}
            onToggleAi={toggleAi} onAiVoice={fetchAiVoice}
          />
          <Controls
            length={length} cover={cover} onLength={changeLength} onCover={setCover}
            title={title} coverAsset={coverAsset} sections={sections} cta={cta} ai={ai}
            onWordsmith={() => setMode("wordsmith")}
          />
        </div>
      )}
      {error && (
        <div className="asm-loading" style={{ color: "var(--rk-tomato-600)" }}>
          Couldn’t load the editor: {error.detail || error.message}
        </div>
      )}
    </div>
  );
}
