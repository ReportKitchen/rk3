// Report Kitchen website — Info Design Pattern Library
const RKl = window.ReportKitchenDesignSystem_07c3a7;
const hl = React.createElement;

const RK_PATTERNS = [
  { icon: "layout-dashboard", name: "Layered navigation", cat: "Navigation", desc: "Reveal depth on demand with accordions, tabs and expanding sections so readers scan first, dive second.", when: "Long documents with clear hierarchy." },
  { icon: "bar-chart-3", name: "Data visualization", cat: "Data", desc: "Turn tables of numbers into charts readers can actually interpret at a glance.", when: "Reports built on survey or statistical data." },
  { icon: "list-tree", name: "Expanding lists", cat: "Navigation", desc: "Progressive disclosure for long reference lists — summaries up top, detail on click.", when: "Directories, glossaries, recommendations." },
  { icon: "map", name: "Interactive maps", cat: "Geography", desc: "Let readers explore place-based data by region instead of scrolling static images.", when: "Geographic or jurisdictional content." },
  { icon: "sliders-horizontal", name: "Filter & search", cat: "Data", desc: "Give readers controls to narrow large datasets to what's relevant to them.", when: "Databases and large tables." },
  { icon: "quote", name: "Pull quotes & callouts", cat: "Editorial", desc: "Surface the most memorable lines and key takeaways as designed moments.", when: "Narrative-heavy reports." },
  { icon: "table-2", name: "Responsive tables", cat: "Data", desc: "Tables that reflow gracefully on phones instead of forcing a pinch-and-zoom.", when: "Any content with tabular data." },
  { icon: "milestone", name: "Timelines", cat: "Editorial", desc: "Sequence events or process steps as a scannable visual path.", when: "History, roadmaps, multi-phase plans." },
  { icon: "video", name: "Embedded media", cat: "Media", desc: "Weave video and audio into the reading flow — no awkward external links.", when: "Interviews and multimedia projects." },
];

function PatternLibrary({ go }) {
  const { Tag, Eyebrow, Callout } = RKl;
  const cats = ["All", "Navigation", "Data", "Editorial", "Media", "Geography"];
  const [active, setActive] = React.useState("All");
  const wrap = { maxWidth: 1160, margin: "0 auto", padding: "0 40px" };
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); }, [active]);
  const shown = active === "All" ? RK_PATTERNS : RK_PATTERNS.filter((p) => p.cat === active);

  return hl("div", null, [
    hl("section", { key: "head", style: { padding: "64px 0 48px" } },
      hl("div", { style: { ...wrap, display: "flex", flexDirection: "column", gap: 18, alignItems: "center", textAlign: "center" } }, [
        hl(Eyebrow, { key: "e", color: "macaroni" }, "Free resource · Content marketing"),
        hl("h1", { key: "h", style: { margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 800, fontSize: 56, lineHeight: 1.02, letterSpacing: "-0.03em", color: "var(--rk-text-strong)", maxWidth: 820, textWrap: "balance" } }, "The Info Design Pattern Library"),
        hl("p", { key: "p", style: { margin: 0, maxWidth: 640, fontFamily: "var(--rk-font-body)", fontSize: 19, lineHeight: 1.55, color: "var(--rk-text-muted)" } }, "A growing, open library of information-design patterns for long-form content — what each one is, when to use it, and how to build it."),
      ])
    ),
    hl("section", { key: "grid", style: { padding: "0 0 80px" } },
      hl("div", { style: { ...wrap, display: "flex", flexDirection: "column", gap: 28 } }, [
        hl("div", { key: "f", style: { display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center" } },
          cats.map((c) => hl(Tag, { key: c, interactive: true, active: active === c, onClick: () => setActive(c) }, c))
        ),
        hl("div", { key: "g", style: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 } },
          shown.map((p, i) => hl(PatternCard, { key: p.name, p }))
        ),
      ])
    ),
    hl("section", { key: "cta", style: { padding: "0 0 88px" } },
      hl("div", { style: wrap }, hl(Callout, { tone: "cream", eyebrow: "Want a hand?", title: "Not sure which pattern fits your report?", primaryLabel: "Talk to the Kitchen", secondaryLabel: "See our work", onClickSecondary: () => go("work") }, "We use these patterns every day. Tell us about your content and we'll recommend the right approach."))
    ),
  ]);
}

function PatternCard({ p }) {
  const [hover, setHover] = React.useState(false);
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); });
  return hl("div", { onMouseEnter: () => setHover(true), onMouseLeave: () => setHover(false),
    style: { display: "flex", flexDirection: "column", gap: 14, padding: 26, background: "var(--rk-surface-card)", border: "1px solid var(--rk-border)", borderRadius: "var(--rk-radius-lg)", boxShadow: hover ? "var(--rk-shadow-md)" : "none", transform: hover ? "translateY(-3px)" : "none", transition: "transform var(--rk-dur) var(--rk-ease-out), box-shadow var(--rk-dur)" } }, [
    hl("div", { key: "top", style: { display: "flex", alignItems: "center", justifyContent: "space-between" } }, [
      hl("div", { key: "ic", style: { width: 50, height: 50, borderRadius: "var(--rk-radius-md)", background: "var(--rk-macaroni-100)", display: "flex", alignItems: "center", justifyContent: "center" } }, hl("i", { "data-lucide": p.icon, width: 25, height: 25, style: { strokeWidth: 1.9,  color: "var(--rk-macaroni-600)" } })),
      hl("span", { key: "c", style: { fontFamily: "var(--rk-font-body)", fontWeight: 600, fontSize: 12, textTransform: "uppercase", letterSpacing: ".06em", color: "var(--rk-rhino-300)" } }, p.cat),
    ]),
    hl("h3", { key: "t", style: { margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 700, fontSize: 21, letterSpacing: "-0.01em", color: "var(--rk-text-strong)" } }, p.name),
    hl("p", { key: "d", style: { margin: 0, fontFamily: "var(--rk-font-body)", fontSize: 15, lineHeight: 1.55, color: "var(--rk-text-muted)" } }, p.desc),
    hl("div", { key: "w", style: { marginTop: "auto", paddingTop: 12, borderTop: "1px dashed var(--rk-border-strong)", display: "flex", gap: 8, alignItems: "baseline" } }, [
      hl("span", { key: "l", style: { fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 12.5, textTransform: "uppercase", letterSpacing: ".05em", color: "var(--rk-tomato)" } }, "When"),
      hl("span", { key: "v", style: { fontFamily: "var(--rk-font-body)", fontSize: 14, color: "var(--rk-text-body)" } }, p.when),
    ]),
  ]);
}

window.RKSite = window.RKSite || {};
window.RKSite.PatternLibrary = PatternLibrary;
