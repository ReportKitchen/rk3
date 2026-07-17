import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "./assemble.css";
import "../landingPage.css"; // block-render styles, reused by the previews + Wordsmith
import { getGuidance, getGuided, getBlockDefaults } from "../../api.js";
import { loadContent } from "../../content.js";
import { guard } from "../../errorBus.js";
import { selectKeys, orderedKeys, LENGTHS } from "./model.js";
import Chrome from "./Chrome.jsx";
import BlockLibrary from "./BlockLibrary.jsx";
import Inspector from "./Inspector.jsx";
import Controls from "./Controls.jsx";
import Wordsmith from "./Wordsmith.jsx";

// Content-first Landing Page Maker (the round-2 Assemble → Wordsmith rebuild that
// replaces the Puck LPM). The guidance engine draws the smart default page; the
// user reshapes WHAT the page says here, then fixes the wording in Wordsmith.
export default function AssembleMaker({ doc }) {
  const slug = doc.slug;
  const [ready, setReady] = useState(false);     // content bundle loaded
  const [guidance, setGuidance] = useState(null); // {profile, guidance} | null (AI off)
  const [blockDefaults, setBlockDefaults] = useState(null);
  const [config, setConfig] = useState(null);     // /guided page config (authoritative)
  const [error, setError] = useState(null);

  const [mode, setMode] = useState("assemble");   // assemble | wordsmith
  const [sel, setSel] = useState("execSummary");  // inspected block key
  const [added, setAdded] = useState(() => new Set());
  const [length, setLength] = useState("middle");
  const [cover, setCover] = useState("beside");
  const [checkedFacts, setCheckedFacts] = useState([]); // indices into stats
  const [ownFacts, setOwnFacts] = useState([]);   // user-added {value,fact,page}
  const [voice, setVoice] = useState("neutral");
  const [person, setPerson] = useState(0);        // index into stories

  const recommendedOrder = useRef([]);

  // ---- initial load: content bundle + guidance + default page + block defaults
  useEffect(() => {
    let alive = true;
    setReady(false); setGuidance(null); setConfig(null); setError(null);
    loadContent("lpm")
      .then(() => Promise.all([
        getGuidance(slug).catch(() => null),        // 503 when AI is off — degrade
        getGuided(slug).catch(guard("assemble: guided", null)),
        getBlockDefaults(slug).catch(guard("assemble: block defaults", null)),
      ]))
      .then(([g, cfg, defs]) => {
        if (!alive) return;
        const gg = g?.guidance || null;
        const rp = gg?.recommendedPage || {};
        const len = LENGTHS.includes(cfg?.length) ? cfg.length
          : (LENGTHS.includes(rp.length) ? rp.length : "middle");
        const cov = cfg?.coverLayout || rp.coverLayout || "beside";
        recommendedOrder.current = rp.blocks && rp.blocks.length ? rp.blocks
          : (cfg?.blocks || []).map((b) => b.type);
        const initAdded = new Set(selectKeys(recommendedOrder.current, len));
        setGuidance(g); setBlockDefaults(defs); setConfig(cfg);
        setLength(len); setCover(cov); setAdded(initAdded);
        // seed choices
        const stats = gg?.stats || [];
        setCheckedFacts(stats.slice(0, 3).map((_, i) => i));
        const stories = gg?.stories || [];
        const strongIdx = stories.findIndex((s) => s.strength === "strongest");
        setPerson(strongIdx >= 0 ? strongIdx : 0);
        setVoice(rp.summaryChoice === "ai" ? "neutral" : "neutral");
        // inspect the first block that's actually on the page
        const first = orderedKeys(initAdded)[0] || "execSummary";
        setSel(first);
        setReady(true);
      })
      .catch((e) => { if (alive) { setError(e); setReady(true); } });
    return () => { alive = false; };
  }, [slug]);

  // ---- length change: refetch /guided AND recompute the smart default set
  const changeLength = useCallback((next) => {
    if (next === length) return;
    setLength(next);
    setAdded(new Set(selectKeys(recommendedOrder.current, next)));
    getGuided(slug, next, cover).then(setConfig).catch(guard("assemble: guided length", null));
  }, [length, cover, slug]);

  // ---- cover change: refetch /guided (keeps the added set)
  const changeCover = useCallback((next) => {
    if (next === cover) return;
    setCover(next);
    getGuided(slug, length, next).then(setConfig).catch(guard("assemble: guided cover", null));
  }, [cover, length, slug]);

  const toggleBlock = useCallback((key) => {
    setAdded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }, []);

  const g = guidance?.guidance || null;
  const profile = guidance?.profile || null;
  const stats = useMemo(() => [...(g?.stats || []), ...ownFacts], [g, ownFacts]);
  const stories = g?.stories || [];
  const pages = profile?.pages || 0;

  const addOwnFact = useCallback((fact) => {
    setOwnFacts((prev) => [...prev, fact]);
    // auto-check the new fact (it lands at the end of the combined stats list)
    setCheckedFacts((prev) => [...prev, (g?.stats?.length || 0) + ownFacts.length]);
  }, [g, ownFacts.length]);

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
          slug={slug} length={length} cover={cover} added={added}
          stats={stats} checkedFacts={checkedFacts} profile={profile}
          onBack={() => setMode("assemble")}
        />
      ) : (
        <div className="asm-grid">
          <BlockLibrary
            guidance={g} added={added} sel={sel}
            onSelect={setSel}
          />
          <Inspector
            slug={slug} sel={sel} guidance={g} blockDefaults={blockDefaults}
            added={added} onToggle={toggleBlock}
            length={length} pages={pages}
            stats={stats} checkedFacts={checkedFacts} setCheckedFacts={setCheckedFacts}
            onAddOwnFact={addOwnFact}
            voice={voice} setVoice={setVoice}
            stories={stories} person={person} setPerson={setPerson}
          />
          <Controls
            length={length} cover={cover}
            onLength={changeLength} onCover={changeCover}
            added={added} stats={stats} checkedFacts={checkedFacts}
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
