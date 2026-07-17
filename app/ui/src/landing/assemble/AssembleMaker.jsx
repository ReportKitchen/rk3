import React, { useCallback, useEffect, useState } from "react";
import "./assemble.css";
import "../landingPage.css"; // block-render styles, reused by the previews + Wordsmith
import { getBlockDefaults, getAiSummary } from "../../api.js";
import { loadContent, t } from "../../content.js";
import { guard } from "../../errorBus.js";
import { LENGTHS, SUMMARY_LENGTH, recommendOn, titleCase, wordCount, AUTO_TRIM_OVER, pickAiHeading, STAT_TREATMENT_ORDER } from "./model.js";
import Chrome from "./Chrome.jsx";
import WhiskLoader from "./WhiskLoader.jsx";
import SectionLibrary from "./SectionLibrary.jsx";
import Inspector from "./Inspector.jsx";
import Controls from "./Controls.jsx";
import Wordsmith from "./Wordsmith.jsx";

const getSections = (slug) =>
  fetch(`/api/landing/${slug}/sections`).then((r) => r.json());

const LOADING_PHRASES = [
  "lpm.assemble.loading.reading", "lpm.assemble.loading.highlights",
  "lpm.assemble.loading.stats", "lpm.assemble.loading.quotes",
  "lpm.assemble.loading.outline", "lpm.assemble.loading.summary",
  "lpm.assemble.loading.polish",
];

// Content-first Landing Page Maker (the AI-sections rebuild, BACKLOG/61). The
// sections engine proposes the document's meaningful sections in its own words;
// the user picks which to keep, adjusts each section's presentation, then fixes
// the wording in Wordsmith. "Highlights" = the AI sections (the star of the
// screen); the CTA scaffolding sits beside them.
export default function AssembleMaker({ doc }) {
  const slug = doc.slug;
  const [ready, setReady] = useState(false);
  const [booted, setBooted] = useState(false);    // content bundle loaded (for the loader caption)
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
  const [accent, setAccent] = useState("#D72E2C");   // the one settable accent
  const [cta, setCta] = useState({ download: true, secondary: false, share: true });
  // the opt-in AI Summary — the ONE AI-written section (a pitch in a chosen voice)
  const [ai, setAi] = useState({ on: false, voice: "neutral", prose: "", loading: false, fetched: false });

  useEffect(() => {
    let alive = true;
    setReady(false); setError(null);
    setAi({ on: false, voice: "neutral", prose: "", loading: false, fetched: false });
    loadContent("lpm")
      .then(() => { if (alive) setBooted(true); })
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
        const secs = raw.map((s, i) => ({
          id: `sec-${i}`,
          heading: titleCase(s.heading), summary: s.summary, role: s.role, presentation: s.presentation,
          page: s.page, strength: s.strength, verbatim: s.verbatim,
          prose: s.prose, bullets: s.bullets, cards: s.cards, quote: s.quote, steps: s.steps,
          on: false,
          // long verbatim summaries default to trimmed (they can run screens)
          trimmed: s.presentation === "prose" && wordCount(s.prose) > AUTO_TRIM_OVER,
          treatment: null,
        }));
        // give each stat section a different default treatment (variety on browse)
        let statIdx = 0;
        secs.forEach((s) => {
          if (s.presentation === "statCards") {
            s.treatment = STAT_TREATMENT_ORDER[statIdx % STAT_TREATMENT_ORDER.length];
            statIdx += 1;
          }
        });
        // recommend some-on/some-off so the opening page lands in the good zone
        const on = recommendOn(secs);
        secs.forEach((s, i) => { s.on = on[i]; });
        setSections(secs);
        setAi((a) => ({ ...a, heading: pickAiHeading(secs) }));   // a title the doc doesn't already use
        setDocRead(art.documentRead || null);
        setNoai(!!sd?.noai);
        setGenError(sd?.error || null);
        setDefs(defaults || {});
        setLength(len);
        setCover(rec.cover || "beside");
        setCta({
          download: true, secondary: false, share: true,
          downloadLabel: defaults?.download?.label || "", downloadUrl: "",
          secondaryLabel: defaults?.secondaryCta?.label || "", secondaryUrl: "",
          shareNetworks: { linkedin: true, x: true, link: true },
          shareStyle: "plain",
        });
        setSel(null);   // open on the friendly welcome panel
        setReady(true);
      })
      .catch((e) => { if (alive) { setError(e); setReady(true); } });
    return () => { alive = false; };
  }, [slug]);

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

  const setTrimmed = useCallback((id, trimmed) => {
    setSections((prev) => prev.map((s) => (s.id === id ? { ...s, trimmed } : s)));
  }, []);

  const setTreatment = useCallback((id, treatment) => {
    setSections((prev) => prev.map((s) => (s.id === id ? { ...s, treatment } : s)));
  }, []);

  const toggleCta = useCallback((key) => {
    setCta((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const patchCta = useCallback((patch) => setCta((prev) => ({ ...prev, ...patch })), []);

  const toggleAi = useCallback(() => setAi((a) => ({ ...a, on: !a.on })), []);

  // fetch (lazily) the AI-written summary for a voice at the current length
  const fetchAiVoice = useCallback((voice) => {
    setAi((a) => ({ ...a, voice, loading: true }));
    getAiSummary(slug, voice, SUMMARY_LENGTH[length] || "medium")
      .then((text) => setAi((a) => (a.voice === voice
        ? { ...a, loading: false, fetched: true, prose: text ? text.split(/\n\n+/).map((p) => `<p>${p.trim()}</p>`).join("") : "" }
        : a)))
      .catch(() => setAi((a) => ({ ...a, loading: false, fetched: true })));
  }, [slug, length]);

  const title = defs?.title || null;
  const coverAsset = defs?.cover || null;

  if (!ready) return (
    <div className="asm-root">
      <div className="asm-loading">
        <WhiskLoader size={150} captions={booted ? LOADING_PHRASES.map((k) => t(k)) : undefined} />
      </div>
    </div>
  );

  return (
    <div className="asm-root" style={{ "--lp-accent": accent }}>
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
            onSetTrimmed={setTrimmed} onSetTreatment={setTreatment}
            onToggleAi={toggleAi} onAiVoice={fetchAiVoice} onPatchCta={patchCta}
          />
          <Controls
            cover={cover} onCover={setCover} accent={accent} onAccent={setAccent}
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
