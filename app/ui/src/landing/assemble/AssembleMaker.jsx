import React, { useCallback, useEffect, useRef, useState } from "react";
import "./assemble.css";
import "../landingPage.css"; // block-render styles, reused by the previews + Wordsmith
import { getBlockDefaults, getAiSummary, getAssembled, saveAssembled,
  getSocialPost, generateSocialPost } from "../../api.js";
import { loadContent, t } from "../../content.js";
import { guard } from "../../errorBus.js";
import { LENGTHS, SUMMARY_LENGTH, recommendOn, titleCase, canTrim, pickAiHeading, STAT_TREATMENT_ORDER, QUOTE_TREATMENT_ORDER, normalizeCover, assignKeys, mergeSaved, toAssembled, CTA_KEYS, SOCIAL_MODE } from "./model.js";
import { useDelayed } from "./hooks.js";
import Chrome from "./Chrome.jsx";
import WhiskLoader from "./WhiskLoader.jsx";
import SectionLibrary from "./SectionLibrary.jsx";
import Inspector from "./Inspector.jsx";
import Controls from "./Controls.jsx";
import Wordsmith from "./Wordsmith.jsx";
import Preview from "./Preview.jsx";
import Publish from "./Publish.jsx";

const getSections = (slug) =>
  fetch(`/api/landing/${slug}/sections`).then((r) => r.json());

// Deliberately no "Reading your report" / "Almost there" — those narrate a fake
// progress and give the canned loop away. Just neutral, true-ish work phrases.
const LOADING_PHRASES = [
  "lpm.assemble.loading.highlights", "lpm.assemble.loading.stats",
  "lpm.assemble.loading.quotes", "lpm.assemble.loading.outline",
  "lpm.assemble.loading.summary",
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
  const [accent, setAccent] = useState("#1E3A5F");   // the one settable accent (dark blue default)
  const [cta, setCta] = useState({ download: true, secondary: false, share: true, order: CTA_KEYS });
  // the opt-in AI Summary — the ONE AI-written section (a pitch in a chosen voice)
  const [ai, setAi] = useState({ on: false, voice: "neutral", prose: "", loading: false, fetched: false });
  const [edits, setEdits] = useState({});   // Wordsmith per-section text edits {skey:{html,sig}}
  const [shareImage, setShareImage] = useState("cover");  // og:/twitter: preview: cover | social
  const [socialPosts, setSocialPosts] = useState([]);     // 4 suggested posts (sections pass)
  const [postsPending, setPostsPending] = useState(false); // server is backfilling an old cache
  const [socialDoc, setSocialDoc] = useState(false);      // bundle posts .docx in the zip
  const [dlStyle, setDlStyle] = useState("embedded");     // zip stylesheet: embedded | inline
  const loadedRef = useRef(false);           // gate the autosave until the first load hydrates

  useEffect(() => {
    let alive = true;
    setReady(false); setError(null); loadedRef.current = false;
    setAi({ on: false, voice: "neutral", prose: "", loading: false, fetched: false });
    loadContent("lpm")
      .then(() => { if (alive) setBooted(true); })
      .then(() => Promise.all([
        getSections(slug).catch(guard("assemble: sections", null)),
        getBlockDefaults(slug).catch(guard("assemble: block defaults", null)),
        getAssembled(slug).catch(() => ({})),
      ]))
      .then(([sd, defaults, saved]) => {
        if (!alive) return;
        saved = saved || {};
        const art = sd?.sections || {};
        const rec = art.recommendedPage || {};
        const len = LENGTHS.includes(saved.length) ? saved.length
          : (LENGTHS.includes(rec.length) ? rec.length : "middle");
        const raw = art.sections || [];
        const secs = raw.map((s, i) => ({
          id: `sec-${i}`,
          heading: titleCase(s.heading), summary: s.summary, role: s.role, presentation: s.presentation,
          page: s.page, strength: s.strength, verbatim: s.verbatim,
          prose: s.prose, bullets: s.bullets, cards: s.cards, steps: s.steps,
          // add the editorial eyebrow; keep any explicit treatment, else rotate below.
          // (the old pull flag maps to the quiet "standard" look.)
          quote: { ...s.quote, eyebrow: t("lpm.sections.quote.eyebrow"),
            treatment: s.quote?.treatment || (s.quote?.pull === false ? "standard" : null) },
          on: false,
          // long verbatim summaries default to trimmed (they can run screens)
          trimmed: s.presentation === "prose" && canTrim(s.prose),
          treatment: null,
        }));
        // give each stat/quote section a different default treatment (variety on browse)
        let statIdx = 0, quoteIdx = 0;
        secs.forEach((s) => {
          if (s.presentation === "statCards") {
            s.treatment = STAT_TREATMENT_ORDER[statIdx % STAT_TREATMENT_ORDER.length];
            statIdx += 1;
          } else if (s.presentation === "quote" && !s.quote.treatment) {
            s.quote.treatment = QUOTE_TREATMENT_ORDER[quoteIdx % QUOTE_TREATMENT_ORDER.length];
            quoteIdx += 1;
          }
        });
        // recommend some-on/some-off so the opening page lands in the good zone
        const on = recommendOn(secs);
        secs.forEach((s, i) => { s.on = on[i]; });
        assignKeys(secs);                       // stable heading-slug keys, then...
        const merged = mergeSaved(secs, saved);  // ...apply saved overrides + order
        setSections(merged);
        setAi((a) => ({ ...a, heading: pickAiHeading(merged),
          on: !!saved.ai?.on, voice: saved.ai?.voice || a.voice }));
        setDocRead(art.documentRead || null);
        setSocialPosts(Array.isArray(art.socialPosts) ? art.socialPosts : []);
        setPostsPending(!!sd?.postsPending);
        setNoai(!!sd?.noai);
        setGenError(sd?.error || null);
        setDefs(defaults || {});
        setLength(len);
        setCover(saved.cover ? normalizeCover(saved.cover) : normalizeCover(rec.cover));
        if (saved.accent) setAccent(saved.accent);
        if (saved.shareImage) setShareImage(saved.shareImage);
        setSocialDoc(!!saved.socialDoc);
        if (saved.dlStyle) setDlStyle(saved.dlStyle);
        setEdits(saved.edits || {});
        setCta({
          download: true, secondary: false, share: true, order: CTA_KEYS,
          downloadLabel: defaults?.download?.label || "", downloadUrl: "",
          secondaryLabel: defaults?.secondaryCta?.label || "", secondaryUrl: "",
          shareNetworks: { linkedin: true, x: true, link: true },
          shareStyle: "plain",
          ...(saved.cta || {}),
        });
        // if the AI summary was saved on, warm its prose so Wordsmith can render it
        if (saved.ai?.on) {
          getAiSummary(slug, saved.ai.voice || "neutral", SUMMARY_LENGTH[len] || "medium")
            .then((text) => { if (alive) setAi((a) => ({ ...a, loading: false, fetched: true,
              prose: text ? text.split(/\n\n+/).map((p) => `<p>${p.trim()}</p>`).join("") : "" })); })
            .catch(() => {});
        }
        setSel(null);   // open on the friendly welcome panel
        setReady(true);
        loadedRef.current = true;   // hydration done — autosave may run now

        // The landing content is gathered — now warm the social graphic in the
        // background (GPT Image takes a while; by Publish it should be ready).
        // Fire-and-forget, ONCE per doc: only when the pathway has never run
        // (a previous failure or result stays put — no cost loop on open).
        if (!sd?.noai && defaults?.cover?.src) {
          getSocialPost(slug)
            .then((st) => {
              if (st?.modes?.[SOCIAL_MODE]?.status === "empty") {
                return generateSocialPost(slug, SOCIAL_MODE);
              }
              return null;
            })
            .catch(guard("assemble: social graphic warm-up", null));
        }
      })
      .catch((e) => { if (alive) { setError(e); setReady(true); } });
    return () => { alive = false; };
  }, [slug]);

  // An old sections cache is having its posts backfilled server-side — poll
  // until they land (or give up quietly after ~3 minutes; the card just hides).
  useEffect(() => {
    if (!postsPending) return undefined;
    let tries = 0;
    const id = setInterval(() => {
      tries += 1;
      getSections(slug)
        .then((sd) => {
          const posts = sd?.sections?.socialPosts;
          if (Array.isArray(posts)) {
            setSocialPosts(posts);
            setPostsPending(false);
          } else if (tries >= 36) {
            setPostsPending(false);
          }
        })
        .catch(() => { if (tries >= 36) setPostsPending(false); });
    }, 5000);
    return () => clearInterval(id);
  }, [postsPending, slug]);

  const toggleSection = useCallback((id) => {
    setSections((prev) => prev.map((s) => (s.id === id ? { ...s, on: !s.on } : s)));
  }, []);

  const setPresentation = useCallback((id, presentation) => {
    setSections((prev) => prev.map((s) => (s.id === id ? { ...s, presentation } : s)));
  }, []);

  const setQuoteTreatment = useCallback((id, treatment) => {
    setSections((prev) => prev.map((s) =>
      (s.id === id ? { ...s, quote: { ...s.quote, treatment } } : s)));
  }, []);

  const setTrimmed = useCallback((id, trimmed) => {
    setSections((prev) => prev.map((s) => (s.id === id ? { ...s, trimmed } : s)));
  }, []);

  const setTreatment = useCallback((id, treatment) => {
    setSections((prev) => prev.map((s) => (s.id === id ? { ...s, treatment } : s)));
  }, []);

  // drag-reorder (dnd-kit): move the dragged section to the target's slot within
  // its group — arrayMove(from, to), matching the sortable's onDragEnd
  const reorderSection = useCallback((activeId, overId) => {
    if (!activeId || activeId === overId) return;
    setSections((prev) => {
      const from = prev.findIndex((s) => s.id === activeId);
      const to = prev.findIndex((s) => s.id === overId);
      if (from < 0 || to < 0 || prev[from].role !== prev[to].role) return prev;
      const next = prev.slice();
      next.splice(to, 0, next.splice(from, 1)[0]);
      return next;
    });
  }, []);

  const toggleCta = useCallback((key) => {
    setCta((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  // CTAs reorder like sections (arrayMove on cta.order)
  const reorderCta = useCallback((activeKey, overKey) => {
    if (!activeKey || activeKey === overKey) return;
    setCta((prev) => {
      const order = (prev.order || CTA_KEYS).slice();
      const from = order.indexOf(activeKey);
      const to = order.indexOf(overKey);
      if (from < 0 || to < 0) return prev;
      order.splice(to, 0, order.splice(from, 1)[0]);
      return { ...prev, order };
    });
  }, []);

  const patchCta = useCallback((patch) => setCta((prev) => ({ ...prev, ...patch })), []);

  const toggleAi = useCallback(() => setAi((a) => ({ ...a, on: !a.on })), []);

  // fetch (lazily) the AI-written summary for a voice at the current length.
  // Always mark loading; the whisk is gated behind useDelayed so it only shows
  // for a genuine wait (a cached voice resolves before the delay and never
  // flashes a loader — the old prose just crossfades to the new).
  const fetchAiVoice = useCallback((voice) => {
    setAi((a) => ({ ...a, voice, loading: true }));
    getAiSummary(slug, voice, SUMMARY_LENGTH[length] || "medium")
      .then((text) => setAi((a) => (a.voice === voice
        ? { ...a, loading: false, fetched: true, prose: text ? text.split(/\n\n+/).map((p) => `<p>${p.trim()}</p>`).join("") : "" }
        : a)))
      .catch(() => setAi((a) => ({ ...a, loading: false, fetched: true })));
  }, [slug, length]);

  // Wordsmith hands back per-section text edits (whole map each time)
  const onEditsChange = useCallback((map) => setEdits(map), []);

  // Autosave the assembled state next to the source (debounced), once hydrated.
  // toAssembled only serializes ai.on/voice, so the ai-prose/loading churn during
  // a voice fetch doesn't need to be a dependency here.
  useEffect(() => {
    if (!loadedRef.current) return undefined;
    const id = setTimeout(() => {
      saveAssembled(slug, toAssembled({ sections, cover, accent, length, cta, ai, edits, shareImage, socialDoc, dlStyle }))
        .catch(guard("assemble: save", null));
    }, 700);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, sections, cover, accent, length, cta, ai.on, ai.voice, edits, shareImage, socialDoc, dlStyle]);

  const showBootLoader = useDelayed(!ready);
  const title = defs?.title || null;
  const coverAsset = defs?.cover || null;

  // the page-load whisk only appears if the load is genuinely slow (AI generating
  // sections) — a cached load resolves first and shows nothing, not a flash
  if (!ready) return (
    <div className="asm-root">
      {showBootLoader && (
        <div className="asm-loading">
          <WhiskLoader size={150} captions={booted ? LOADING_PHRASES.map((k) => t(k)) : undefined} />
        </div>
      )}
    </div>
  );

  return (
    <div className="asm-root" style={{ "--lp-accent": accent }}>
      <Chrome
        title={doc.name || doc.slug}
        activeIdx={{ assemble: 0, wordsmith: 1, preview: 2, publish: 3 }[mode] ?? 0}
        onStep={(i) => setMode(["assemble", "wordsmith", "preview", "publish"][i] || "assemble")}
      />
      {mode === "publish" ? (
        <Publish
          slug={slug} docName={doc.name || slug} title={title} coverAsset={coverAsset}
          cover={cover} accent={accent} sections={sections} cta={cta} ai={ai} edits={edits}
          noai={noai} socialPosts={socialPosts} postsPending={postsPending}
          shareImage={shareImage} onShareImage={setShareImage}
          socialDoc={socialDoc} onSocialDoc={setSocialDoc}
          dlStyle={dlStyle} onDlStyle={setDlStyle}
          onBack={() => setMode("preview")}
        />
      ) : mode === "preview" ? (
        <Preview
          slug={slug} docName={doc.name || slug} title={title} coverAsset={coverAsset}
          cover={cover} accent={accent} sections={sections} cta={cta} ai={ai} edits={edits}
          onBack={() => setMode("wordsmith")} onPublish={() => setMode("publish")}
        />
      ) : mode === "wordsmith" ? (
        <Wordsmith
          slug={slug} title={title} coverAsset={coverAsset} cover={cover}
          sections={sections} cta={cta} ai={ai} edits={edits} onEditsChange={onEditsChange}
          onBack={() => setMode("assemble")} onPreview={() => setMode("preview")}
        />
      ) : (
        <div className="asm-grid">
          <SectionLibrary
            sections={sections} cta={cta} ai={ai} sel={sel} noai={noai} genError={genError}
            docRead={docRead} onSelect={setSel} onReorder={reorderSection} onReorderCta={reorderCta}
          />
          <Inspector
            sel={sel} sections={sections} cta={cta} ai={ai} defs={defs}
            slug={slug} length={length}
            onToggleSection={toggleSection} onToggleCta={toggleCta}
            onSetPresentation={setPresentation} onSetQuoteTreatment={setQuoteTreatment}
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
