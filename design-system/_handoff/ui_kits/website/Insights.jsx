// Report Kitchen website — Insights (editorial section; sample articles)
const RKi = window.ReportKitchenDesignSystem_07c3a7;
const hi = React.createElement;

const RK_INSIGHTS = [
  { title: "Nobody reads your PDF. Here's the data.", cat: "Research", read: "6 min",
    dek: "We pulled analytics from 40 report launches. The drop-off between download and first page is worse than you think — and what to do about it.",
    color: "var(--rk-rhino-700)", icon: "line-chart", featured: true },
  { title: "Five information-design patterns every report should steal", cat: "Design", read: "8 min",
    dek: "From layered navigation to filterable data tables — the moves that turn a wall of text into something people actually explore.",
    color: "var(--rk-tomato-500)", icon: "layout-dashboard" },
  { title: "Using AI responsibly in nonprofit communications", cat: "AI", read: "7 min",
    dek: "Where large language models genuinely help with long-form content — and the guardrails we put in place before they touch a client's report.",
    color: "var(--rk-muffin)", icon: "sparkles" },
  { title: "Accessibility isn't a feature. It's the whole point.", cat: "Accessibility", read: "5 min",
    dek: "How we build to WCAG AA by default, and why an accessible report is almost always a more effective one.",
    color: "var(--rk-macaroni-600)", icon: "accessibility" },
  { title: "The 200-page problem: publishing comprehensive plans on the web", cat: "Case study", read: "9 min",
    dek: "Municipal comprehensive plans are massive. Here's how we make them navigable without losing an ounce of substance.",
    color: "var(--rk-rhino-500)", icon: "map" },
  { title: "Charts that earn their place", cat: "Data viz", read: "6 min",
    dek: "A field guide to choosing (and cutting) data visualizations so every chart in your report does real work.",
    color: "var(--rk-success)", icon: "bar-chart-3" },
];

function Insights({ go }) {
  const { Eyebrow, Callout } = RKi;
  const cats = ["All", "Design", "Research", "AI", "Accessibility", "Data viz", "Case study"];
  const [active, setActive] = React.useState("All");
  const wrap = { maxWidth: 1080, margin: "0 auto", padding: "0 40px" };
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); }, [active]);

  const dated = RK_INSIGHTS.map((a, i) => ({ ...a, date: ["Jul 2, 2026", "Jun 18, 2026", "Jun 3, 2026", "May 21, 2026", "May 6, 2026", "Apr 22, 2026"][i] }));
  const shown = active === "All" ? dated : dated.filter((a) => a.cat === active);

  return hi("div", null, [
    // HEAD
    hi("section", { key: "head", style: { padding: "60px 0 32px", borderBottom: "1px solid var(--rk-border)" } },
      hi("div", { style: { ...wrap, display: "flex", flexDirection: "column", gap: 14 } }, [
        hi(Eyebrow, { key: "e" }, "Insights"),
        hi("h1", { key: "h", style: { margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 800, fontSize: 48, lineHeight: 1.04, letterSpacing: "-0.03em", color: "var(--rk-text-strong)", maxWidth: 760, textWrap: "balance" } }, "Ideas on reports, information design, and AI"),
        hi("p", { key: "p", style: { margin: 0, maxWidth: 620, fontFamily: "var(--rk-font-body)", fontSize: 18, lineHeight: 1.55, color: "var(--rk-text-muted)" } }, "Notes from the Kitchen on making long-form content more usable, accessible, and engaging."),
      ])
    ),
    // LIST + SIDEBAR
    hi("section", { key: "list", style: { padding: "40px 0 72px" } },
      hi("div", { style: { ...wrap, display: "grid", gridTemplateColumns: "1fr 240px", gap: 56, alignItems: "start" } }, [
        // main column of posts
        hi("div", { key: "posts", style: { display: "flex", flexDirection: "column" } },
          shown.map((a, i) => hi(PostRow, { key: a.title, a, first: i === 0 }))
        ),
        // sidebar
        hi("aside", { key: "side", style: { position: "sticky", top: 96, display: "flex", flexDirection: "column", gap: 28 } }, [
          hi("div", { key: "topics", style: { display: "flex", flexDirection: "column", gap: 4 } }, [
            hi("span", { key: "t", style: { fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 12, textTransform: "uppercase", letterSpacing: ".08em", color: "var(--rk-rhino-300)", marginBottom: 8 } }, "Topics"),
            ...cats.map((c) => hi("button", { key: c, onClick: () => setActive(c),
              style: { all: "unset", cursor: "pointer", padding: "7px 0", fontFamily: "var(--rk-font-body)", fontSize: 15,
                fontWeight: active === c ? 700 : 500, color: active === c ? "var(--rk-tomato-600)" : "var(--rk-text-body)",
                borderBottom: "1px solid var(--rk-border)" } }, c)),
          ]),
          hi("div", { key: "sub", style: { background: "var(--rk-rhino-700)", borderRadius: "var(--rk-radius-md)", padding: "20px 18px", display: "flex", flexDirection: "column", gap: 10 } }, [
            hi("span", { key: "t", style: { fontFamily: "var(--rk-font-display)", fontWeight: 700, fontSize: 17, color: "#fff" } }, "Fresh from the oven"),
            hi("p", { key: "p", style: { margin: 0, fontFamily: "var(--rk-font-body)", fontSize: 13.5, lineHeight: 1.5, color: "var(--rk-text-on-dark)", opacity: 0.85 } }, "A short, occasional note when we publish something new."),
            hi("button", { key: "b", style: { all: "unset", cursor: "pointer", marginTop: 4, textAlign: "center", fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 14, color: "var(--rk-rhino-900)", background: "var(--rk-macaroni-500)", borderRadius: "var(--rk-radius-sm)", padding: "10px 14px" } }, "Subscribe"),
          ]),
        ]),
      ])
    ),
  ]);
}

function PostRow({ a, first }) {
  const [hover, setHover] = React.useState(false);
  return hi("a", { href: "#", onClick: (e) => e.preventDefault(), onMouseEnter: () => setHover(true), onMouseLeave: () => setHover(false),
    style: { display: "flex", flexDirection: "column", gap: 9, padding: "26px 0", textDecoration: "none",
      borderTop: first ? "none" : "1px solid var(--rk-border)" } }, [
    hi("div", { key: "m", style: { display: "flex", alignItems: "center", gap: 10, fontFamily: "var(--rk-font-body)", fontSize: 13 } }, [
      hi("span", { key: "c", style: { fontWeight: 700, textTransform: "uppercase", letterSpacing: ".06em", color: "var(--rk-tomato)" } }, a.cat),
      hi("span", { key: "d1", style: { color: "var(--rk-rhino-200)" } }, "·"),
      hi("span", { key: "dt", style: { color: "var(--rk-text-muted)", fontWeight: 500 } }, a.date),
      hi("span", { key: "d2", style: { color: "var(--rk-rhino-200)" } }, "·"),
      hi("span", { key: "r", style: { color: "var(--rk-text-muted)", fontWeight: 500 } }, a.read + " read"),
    ]),
    hi("h2", { key: "h", style: { margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 700, fontSize: 27, lineHeight: 1.12, letterSpacing: "-0.02em", color: hover ? "var(--rk-tomato-600)" : "var(--rk-text-strong)", transition: "color var(--rk-dur)", maxWidth: 640 } }, a.title),
    hi("p", { key: "dek", style: { margin: 0, fontFamily: "var(--rk-font-body)", fontSize: 16.5, lineHeight: 1.6, color: "var(--rk-text-muted)", maxWidth: 620 } }, a.dek),
    hi("span", { key: "link", style: { display: "inline-flex", alignItems: "center", gap: 6, marginTop: 2, fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 14.5, color: "var(--rk-tomato-600)" } }, [
      "Read more", hi("i", { key: "i", "data-lucide": "arrow-right", width: 16, height: 16, style: { strokeWidth: 2.25, transform: hover ? "translateX(3px)" : "none", transition: "transform var(--rk-dur)" } })]),
  ]);
}

window.RKSite = window.RKSite || {};
window.RKSite.Insights = Insights;
