// Report Kitchen website — Report Kitchen Custom (offering page)
const RKc = window.ReportKitchenDesignSystem_07c3a7;
const hc = React.createElement;

function OfferingCustom({ go }) {
  const { Button, Badge, SectionHeading, Callout, Card, FeatureCard } = RKc;
  const wrap = { maxWidth: 1120, margin: "0 auto", padding: "0 40px" };
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); });

  const process = [
    { icon: "upload", t: "Share your PDF", b: "Send us the report, plan or toolkit you've already published." },
    { icon: "pencil-ruler", t: "We design the experience", b: "Information architecture, navigation and layouts tailored to your content." },
    { icon: "cooking-pot", t: "We build it", b: "A bespoke, responsive, accessible site — charts, media and interactions included." },
    { icon: "rocket", t: "Launch & measure", b: "We publish, hand off, and set you up with engagement analytics." },
  ];

  return hc("div", null, [
    // hero
    hc("section", { key: "hero", style: { background: "var(--rk-rhino-700)", padding: "72px 0 80px", color: "#fff" } },
      hc("div", { style: { ...wrap, display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: 48, alignItems: "center" } }, [
        hc("div", { key: "l", style: { display: "flex", flexDirection: "column", gap: 22 } }, [
          hc(Badge, { key: "b", tone: "success", dot: true }, "Available now · Our flagship"),
          hc("h1", { key: "h", style: { margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 800, fontSize: 58, lineHeight: 1.02, letterSpacing: "-0.03em", textWrap: "balance" } }, "Report Kitchen Custom"),
          hc("p", { key: "p", style: { margin: 0, maxWidth: 520, fontFamily: "var(--rk-font-body)", fontSize: 20, lineHeight: 1.55, color: "var(--rk-text-on-dark)" } }, "The full white-glove build. Hand us your PDF and we'll cook up a bespoke, responsive, accessible website — start to finish."),
          hc("div", { key: "cta", style: { display: "flex", gap: 12, marginTop: 4 } }, [hc(Button, { key: "a", variant: "accent", size: "lg", iconRight: "arrow-right", onClick: () => go("custom") }, "Contact the Kitchen"), hc(Button, { key: "b", variant: "ghost", size: "lg", style: { color: "#fff" }, onClick: () => go("work") }, "See examples")]),
        ]),
        hc("div", { key: "r", style: { display: "flex", flexDirection: "column", gap: 12 } },
          [["chef-hat", "Done for you, end to end"], ["accessibility", "Accessible by default (WCAG AA)"], ["smartphone", "Fully responsive on every device"], ["line-chart", "Reader engagement analytics"]].map((v, i) =>
            hc("div", { key: i, style: { display: "flex", alignItems: "center", gap: 14, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "var(--rk-radius-md)", padding: "16px 18px" } }, [
              hc("i", { key: "i", "data-lucide": v[0], width: 24, height: 24, style: { strokeWidth: 2,  color: "var(--rk-macaroni-500)", flexShrink: 0 } }),
              hc("span", { key: "t", style: { fontFamily: "var(--rk-font-body)", fontWeight: 600, fontSize: 16.5 } }, v[1]),
            ])
          )
        ),
      ])
    ),
    // process
    hc("section", { key: "proc", style: { padding: "80px 0" } },
      hc("div", { style: { ...wrap, display: "flex", flexDirection: "column", gap: 44 } }, [
        hc(SectionHeading, { key: "sh", align: "center", eyebrow: "How it works", title: "From PDF to launch in four steps" }),
        hc("div", { key: "g", style: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 20 } },
          process.map((p, i) => hc("div", { key: i, style: { display: "flex", flexDirection: "column", gap: 12, padding: 24, background: "var(--rk-surface-card)", border: "1px solid var(--rk-border)", borderRadius: "var(--rk-radius-lg)" } }, [
            hc("div", { key: "top", style: { display: "flex", alignItems: "center", justifyContent: "space-between" } }, [
              hc("div", { key: "ic", style: { width: 46, height: 46, borderRadius: "var(--rk-radius-md)", background: "var(--rk-tomato-100)", display: "flex", alignItems: "center", justifyContent: "center" } }, hc("i", { "data-lucide": p.icon, width: 23, height: 23, style: { strokeWidth: 2,  color: "var(--rk-tomato-600)" } })),
              hc("span", { key: "n", style: { fontFamily: "var(--rk-font-display)", fontWeight: 800, fontSize: 30, color: "var(--rk-rhino-100)" } }, "0" + (i + 1)),
            ]),
            hc("h3", { key: "t", style: { margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 700, fontSize: 19, color: "var(--rk-text-strong)" } }, p.t),
            hc("p", { key: "b", style: { margin: 0, fontFamily: "var(--rk-font-body)", fontSize: 15, lineHeight: 1.55, color: "var(--rk-text-muted)" } }, p.b),
          ]))
        ),
      ])
    ),
    // samples
    hc("section", { key: "samp", style: { background: "var(--rk-cream)", padding: "80px 0", borderTop: "1px solid var(--rk-border)", borderBottom: "1px solid var(--rk-border)" } },
      hc("div", { style: { ...wrap, display: "flex", flexDirection: "column", gap: 36 } }, [
        hc(SectionHeading, { key: "sh", eyebrow: "Recently plated", title: "A few we've built" }),
        hc("div", { key: "g", style: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 22 } }, [
          hc(Card, { key: "1", client: "Enterprise Community Partners", title: "Housing2Justice Toolkit", description: "80 pages, a legal survey and a provider database — one interactive site.", coverColor: "var(--rk-rhino-700)", coverIcon: "scale", coverText: "Toolkit", tags: ["Housing"], onClick: () => go("profile") }),
          hc(Card, { key: "2", client: "Charles Stewart Mott Foundation", title: "Focus on Flint", description: "Dozens of charts and infographics, fully responsive and shareable.", coverColor: "var(--rk-muffin)", coverIcon: "bar-chart-3", coverText: "Report", tags: ["Data"], onClick: () => go("profile") }),
          hc(Card, { key: "3", client: "Enterprise Community Partners", title: "Keep Safe Manual", description: "A 500+ page resilient-housing manual, made easy to navigate.", coverColor: "var(--rk-macaroni-600)", coverIcon: "life-buoy", coverText: "Manual", tags: ["Climate"], onClick: () => go("profile") }),
        ]),
      ])
    ),
    // callout
    hc("section", { key: "cta", style: { padding: "80px 0" } },
      hc("div", { style: wrap }, hc(Callout, { eyebrow: "Let's talk", title: "Tell us about your report — we'll show you what's possible.", primaryLabel: "Contact the Kitchen", secondaryLabel: "Explore all offerings", onClickSecondary: () => go("home") }, "Every custom build starts with a conversation. No obligation, no reformatting on your end.")),
    ),
  ]);
}

window.RKSite = window.RKSite || {};
window.RKSite.OfferingCustom = OfferingCustom;
