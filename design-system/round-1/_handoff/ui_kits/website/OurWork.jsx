// Report Kitchen website — Our Work grid
const RKw = window.ReportKitchenDesignSystem_07c3a7;
const hw = React.createElement;

const RK_PROJECTS = [
  { title: "Green Communities 2026", client: "Enterprise Community Partners", desc: "Interactive certification guide helps affordable housing teams navigate sustainable building requirements.", color: "var(--rk-success)", icon: "leaf", kind: "Guide", cat: "Housing" },
  { title: "Housing2Justice National Toolkit", client: "Enterprise Community Partners", desc: "Helping the housing industry better understand and serve the justice-impacted population.", color: "var(--rk-rhino-700)", icon: "scale", kind: "Toolkit", cat: "Housing" },
  { title: "Climate Smart Housing", client: "Enterprise Community Partners", desc: "Driving climate improvements into low- and moderate-income communities.", color: "var(--rk-muffin)", icon: "cloud-sun", kind: "Report", cat: "Climate" },
  { title: "Social Housing in Vienna", client: "LA Housing Leaders", desc: "Reflections from Los Angeles housing leaders on Vienna's social housing model.", color: "var(--rk-tomato-500)", icon: "building-2", kind: "Report", cat: "Housing" },
  { title: "Anchor Collaboratives Playbook", client: "Democracy Collaborative", desc: "A digital playbook for advancing equitable economic development and wealth building.", color: "var(--rk-rhino-500)", icon: "book-open", kind: "Playbook", cat: "Economy" },
  { title: "Climate Safe Housing", client: "Enterprise Community Partners", desc: "Strategies to protect multifamily buildings against extreme weather and build resilient communities.", color: "var(--rk-macaroni-600)", icon: "shield", kind: "Toolkit", cat: "Climate" },
  { title: "Trauma-Informed Housing", client: "Enterprise Community Partners", desc: "A toolkit for advancing equity and economic opportunity in affordable housing.", color: "var(--rk-muffin)", icon: "heart-handshake", kind: "Toolkit", cat: "Housing" },
  { title: "Whole Child Policy Toolkit", client: "Learning Policy Institute", desc: "Evidence-based strategies and resources to advance whole-child policy and systems change.", color: "var(--rk-tomato-500)", icon: "graduation-cap", kind: "Toolkit", cat: "Education" },
  { title: "FOIA Basics for Activists", client: "Center for Constitutional Rights", desc: "A resource for activists with tools and advice for successful FOIA requests.", color: "var(--rk-rhino-700)", icon: "file-search", kind: "Guide", cat: "Policy" },
  { title: "Restarting & Reinventing School", client: "Learning Policy Institute", desc: "A framework to reimagine schooling using safe, equitable, student-centered approaches.", color: "var(--rk-macaroni-600)", icon: "school", kind: "Framework", cat: "Education" },
  { title: "Keep Safe Manual", client: "Enterprise Community Partners", desc: "A 500+ page resource for resilient housing design in island communities, made easy to navigate.", color: "var(--rk-rhino-500)", icon: "life-buoy", kind: "Manual", cat: "Climate" },
  { title: "Enterprise Green Communities", client: "Enterprise Community Partners", desc: "The certification framework for sustainable affordable housing — free of the old PDF format.", color: "var(--rk-success)", icon: "leaf", kind: "Criteria", cat: "Housing" },
  { title: "ALEC Attacks", client: "Center for Constitutional Rights", desc: "A report exposing the tactics of a secretive corporate lobbying group.", color: "var(--rk-tomato-600)", icon: "megaphone", kind: "Report", cat: "Policy" },
  { title: "Focus on Flint", client: "Charles Stewart Mott Foundation", desc: "Dozens of charts and infographics across eight issues affecting the Flint community.", color: "var(--rk-muffin)", icon: "bar-chart-3", kind: "Report", cat: "Data" },
  { title: "Public Attitudes Towards Gifted Education", client: "Institute for Educational Advancement", desc: "Findings from a broad survey of American attitudes towards gifted education.", color: "var(--rk-rhino-700)", icon: "clipboard-list", kind: "Survey", cat: "Education" },
  { title: "Elements of Success", client: "Housing Authority Partnership", desc: "Best-practices review with video interviews woven seamlessly into the reader experience.", color: "var(--rk-macaroni-600)", icon: "video", kind: "Review", cat: "Housing" },
];

function OurWork({ go }) {
  const cats = ["All", "Housing", "Education", "Climate", "Policy", "Economy", "Data"];
  const [active, setActive] = React.useState("All");
  const { Card, Tag, Eyebrow } = RKw;
  const wrap = { maxWidth: 1200, margin: "0 auto", padding: "0 40px" };
  const shown = active === "All" ? RK_PROJECTS : RK_PROJECTS.filter((p) => p.cat === active);
  return hw("div", null, [
    hw("section", { key: "head", style: { background: "var(--rk-cream)", padding: "64px 0 56px", borderBottom: "1px solid var(--rk-border)" } },
      hw("div", { style: { ...wrap, display: "flex", flexDirection: "column", gap: 18 } }, [
        hw(Eyebrow, { key: "e" }, "Our Work"),
        hw("h1", { key: "h", style: { margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 800, fontSize: 54, lineHeight: 1.03, letterSpacing: "-0.03em", color: "var(--rk-text-strong)", maxWidth: 820, textWrap: "balance" } }, "Reports, toolkits and plans — reinvented as living websites."),
        hw("p", { key: "p", style: { margin: 0, maxWidth: 640, fontFamily: "var(--rk-font-body)", fontSize: 19, lineHeight: 1.55, color: "var(--rk-text-muted)" } }, "A taste of what happens when long-form content breaks free of the PDF. Browse by focus area."),
      ])
    ),
    hw("section", { key: "grid", style: { padding: "40px 0 88px" } },
      hw("div", { style: { ...wrap, display: "flex", flexDirection: "column", gap: 32 } }, [
        hw("div", { key: "filters", style: { display: "flex", gap: 8, flexWrap: "wrap" } },
          cats.map((c) => hw(Tag, { key: c, interactive: true, active: active === c, onClick: () => setActive(c) }, c))
        ),
        hw("div", { key: "g", style: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 22 } },
          shown.map((p, i) => hw(Card, { key: i, client: p.client, title: p.title, description: p.desc, coverColor: p.color, coverIcon: p.icon, coverText: p.kind, tags: [p.cat], onClick: () => go("profile") }))
        ),
      ])
    ),
  ]);
}

window.RKSite = window.RKSite || {};
window.RKSite.OurWork = OurWork;
window.RK_PROJECTS = RK_PROJECTS;
