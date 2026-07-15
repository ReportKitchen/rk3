// Report Kitchen website — Home
const RK = window.ReportKitchenDesignSystem_07c3a7;
const h = React.createElement;

// Photo-free hero device: a PDF page transforming into a responsive site.
function PdfToWeb() {
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); });
  const line = (w, c = "var(--rk-rhino-200)", k) => h("div", { key: k, style: { height: 7, width: w, borderRadius: 4, background: c } });
  return h("div", { style: { position: "relative", height: 380, display: "flex", alignItems: "center", justifyContent: "center" } }, [
    // soft color field behind
    h("div", { key: "bg", style: { position: "absolute", inset: "10% 4%", background: "var(--rk-macaroni-100)", borderRadius: "var(--rk-radius-xl)" } }),
    // PDF card (left, tilted)
    h("div", { key: "pdf", style: { position: "absolute", left: "6%", top: 40, width: 190, background: "#fff", border: "1px solid var(--rk-border)", borderRadius: "var(--rk-radius-sm)", boxShadow: "var(--rk-shadow-md)", padding: 18, transform: "rotate(-5deg)", display: "flex", flexDirection: "column", gap: 9 } }, [
      h("div", { key: "b", style: { display: "flex", alignItems: "center", gap: 7, marginBottom: 4 } }, [
        h("i", { key: "i", "data-lucide": "file-text", width: 18, height: 18, style: { strokeWidth: 2,  color: "var(--rk-tomato-500)" } }),
        h("span", { key: "t", style: { fontFamily: "var(--rk-font-mono)", fontSize: 11, color: "var(--rk-text-muted)" } }, "report.pdf"),
      ]),
      line("70%", "var(--rk-rhino-300)", "l1"), line("100%", undefined, "l2"), line("92%", undefined, "l3"), line("100%", undefined, "l4"), line("60%", undefined, "l5"),
      h("div", { key: "sp", style: { height: 4 } }),
      line("100%", undefined, "l6"), line("80%", undefined, "l7"),
    ]),
    // arrow
    h("div", { key: "arr", style: { position: "absolute", left: "44%", top: 175, width: 52, height: 52, borderRadius: "50%", background: "var(--rk-tomato-500)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "var(--rk-shadow-md)", zIndex: 3 } },
      h("i", { "data-lucide": "arrow-right", width: 26, height: 26, style: { strokeWidth: 2.5,  color: "#fff" } })
    ),
    // browser card (right)
    h("div", { key: "web", style: { position: "absolute", right: "5%", top: 60, width: 260, background: "#fff", border: "1px solid var(--rk-border)", borderRadius: "var(--rk-radius-md)", boxShadow: "var(--rk-shadow-lg)", overflow: "hidden" } }, [
      h("div", { key: "bar", style: { display: "flex", alignItems: "center", gap: 6, padding: "10px 12px", background: "var(--rk-gray-100)", borderBottom: "1px solid var(--rk-border)" } },
        ["#E4614F", "#F2BB2E", "#7683A2"].map((c, i) => h("span", { key: i, style: { width: 9, height: 9, borderRadius: "50%", background: c } }))
      ),
      h("div", { key: "hero", style: { background: "var(--rk-rhino-700)", padding: "18px 16px", display: "flex", flexDirection: "column", gap: 8 } }, [
        line("55%", "var(--rk-macaroni-500)", "h1"), line("85%", "rgba(255,255,255,0.85)", "h2"), line("70%", "rgba(255,255,255,0.55)", "h3"),
      ]),
      h("div", { key: "body", style: { padding: 16, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 } }, [
        h("div", { key: "c", style: { gridColumn: "1 / -1", height: 44, borderRadius: 8, background: "var(--rk-macaroni-100)", display: "flex", alignItems: "center", justifyContent: "center" } },
          h("i", { "data-lucide": "bar-chart-3", width: 22, height: 22, style: { color: "var(--rk-macaroni-600)" } })),
        h("div", { key: "a", style: { height: 30, borderRadius: 6, background: "var(--rk-gray-100)" } }),
        h("div", { key: "b", style: { height: 30, borderRadius: 6, background: "var(--rk-gray-100)" } }),
      ]),
    ]),
  ]);
}

function TrustStrip_unused() {
  const clients = ["Enterprise Community Partners", "Learning Policy Institute", "Charles Stewart Mott Foundation", "Center for Constitutional Rights"];
  return h("div", { style: { display: "flex", flexDirection: "column", gap: 18, alignItems: "center" } }, [
    h("span", { key: "l", style: { fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 13, textTransform: "uppercase", letterSpacing: ".08em", color: "var(--rk-text-muted)" } }, "Trusted by mission-driven teams"),
    h("div", { key: "row", style: { display: "flex", flexWrap: "wrap", gap: "18px 40px", justifyContent: "center" } },
      clients.map((c, i) => h("span", { key: i, style: { fontFamily: "var(--rk-font-display)", fontWeight: 600, fontSize: 18, color: "var(--rk-rhino-500)" } }, c))
    ),
  ]);
}

function Step({ n, icon, title, body }) {
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); });
  return h("div", { style: { display: "flex", flexDirection: "column", gap: 12, flex: 1 } }, [
    h("div", { key: "top", style: { display: "flex", alignItems: "center", gap: 12 } }, [
      h("div", { key: "ic", style: { width: 48, height: 48, borderRadius: "var(--rk-radius-md)", background: "#fff", border: "1px solid var(--rk-border)", display: "flex", alignItems: "center", justifyContent: "center" } },
        h("i", { "data-lucide": icon, width: 24, height: 24, style: { strokeWidth: 2,  color: "var(--rk-tomato-500)" } })),
      h("span", { key: "n", style: { fontFamily: "var(--rk-font-display)", fontWeight: 700, fontSize: 40, color: "var(--rk-rhino-100)" } }, n),
    ]),
    h("h3", { key: "t", style: { margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 700, fontSize: 22, color: "var(--rk-text-strong)" } }, title),
    h("p", { key: "b", style: { margin: 0, fontFamily: "var(--rk-font-body)", fontSize: 15.5, lineHeight: 1.6, color: "var(--rk-text-muted)" } }, body),
  ]);
}

function Home({ go }) {
  const { Button, FeatureCard, Card, SectionHeading, Callout, Eyebrow } = RK;
  const wrap = { maxWidth: 1200, margin: "0 auto", padding: "0 40px" };
  return h("div", null, [
    // HERO
    h("section", { key: "hero", style: { padding: "72px 0 84px" } },
      h("div", { style: { ...wrap, display: "grid", gridTemplateColumns: "1.05fr 1fr", gap: 48, alignItems: "center" } }, [
        h("div", { key: "l", style: { display: "flex", flexDirection: "column", gap: 24 } }, [
          h(Eyebrow, { key: "e" }, "PDF → living website"),
          h("h1", { key: "h", style: { margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 800, fontSize: 60, lineHeight: 1.02, letterSpacing: "-0.03em", color: "var(--rk-text-strong)", textWrap: "balance" } },
            ["Your report deserves better than a ", h("span", { key: "s", style: { color: "var(--rk-tomato-500)" } }, "download button"), "."]),
          h("p", { key: "p", style: { margin: 0, maxWidth: 500, fontFamily: "var(--rk-font-body)", fontSize: 20, lineHeight: 1.55, color: "var(--rk-text-muted)" } },
            "Report Kitchen turns dense PDFs into interactive, accessible, fully responsive websites — so your audience can truly engage with your work instead of just downloading it."),
          h("div", { key: "cta", style: { display: "flex", gap: 12, flexWrap: "wrap", marginTop: 4 } }, [
            h(Button, { key: "a", size: "lg", iconRight: "arrow-right", onClick: () => go("custom") }, "Get cooking"),
            h(Button, { key: "b", size: "lg", variant: "secondary", onClick: () => go("work") }, "See our work"),
          ]),
        ]),
        h("div", { key: "r" }, h(PdfToWeb)),
      ])
    ),
    // OFFERINGS
    h("section", { key: "off", style: { background: "#fff", borderTop: "1px solid var(--rk-border)", borderBottom: "1px solid var(--rk-border)", padding: "80px 0" } },
      h("div", { style: { ...wrap, display: "flex", flexDirection: "column", gap: 40 } }, [
        h(SectionHeading, { key: "sh", eyebrow: "What's on the menu", title: "Four ways to serve your work", intro: "From self-serve tools to full white-glove builds — pick the level of help you need." }),
        h("div", { key: "g", style: { display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 20 } }, [
          h(FeatureCard, { key: "1", icon: "wand-sparkles", title: "Landing Page Maker", badge: "Available now", badgeTone: "success", action: "Start free", accent: "tomato", onClick: () => go("maker") }, "Upload a PDF and build a polished landing page for it — free for individuals, paid for teams."),
          h(FeatureCard, { key: "2", icon: "globe", title: "Report Kitchen Express", badge: "Coming soon", badgeTone: "soon", action: "Join the waitlist", accent: "macaroni", onClick: () => go("express") }, "Upload a PDF and get a fully responsive HTML website, automatically. Free & paid tiers."),
          h(FeatureCard, { key: "3", icon: "chef-hat", title: "Report Kitchen Custom", badge: "Available now", badgeTone: "success", action: "Contact the Kitchen", accent: "rhino", onClick: () => go("custom") }, "Hand us your PDF; we build you a bespoke, responsive, accessible website end to end."),
          h(FeatureCard, { key: "4", icon: "messages-square", title: "Consulting", badge: "Available now", badgeTone: "success", action: "Start a conversation", accent: "muffin", onClick: () => go("consulting") }, "Guidance at the intersection of nonprofit communications, long-form reports, and AI."),
        ]),
      ])
    ),
    // HOW IT WORKS
    h("section", { key: "how", style: { background: "var(--rk-cream)", padding: "80px 0" } },
      h("div", { style: { ...wrap, display: "flex", flexDirection: "column", gap: 44 } }, [
        h(SectionHeading, { key: "sh", eyebrow: "How it works", eyebrowColor: "tomato", title: "Three steps, no reformatting headaches" }),
        h("div", { key: "s", style: { display: "flex", gap: 40 } }, [
          h(Step, { key: "1", n: "01", icon: "upload", title: "Send us your PDF", body: "Report, toolkit, comprehensive plan — whatever you've published. We start from what you already have." }),
          h(Step, { key: "2", n: "02", icon: "cooking-pot", title: "We cook it into a site", body: "Layered navigation, real accessibility, responsive layouts, charts and interactive content." }),
          h(Step, { key: "3", n: "03", icon: "rocket", title: "Publish & measure", body: "Launch a site people actually use — with full analytics on what readers engage with." }),
        ]),
      ])
    ),
    // FEATURED WORK
    h("section", { key: "work", style: { padding: "80px 0" } },
      h("div", { style: { ...wrap, display: "flex", flexDirection: "column", gap: 36 } }, [
        h("div", { key: "hd", style: { display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 20 } }, [
          h(SectionHeading, { key: "sh", eyebrow: "Our work", title: "Reports we've reinvented" }),
          h(Button, { key: "b", variant: "ghost", iconRight: "arrow-right", onClick: () => go("work") }, "See all work"),
        ]),
        h("div", { key: "g", style: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 } }, [
          h(Card, { key: "1", client: "Enterprise Community Partners", title: "Housing2Justice National Toolkit", description: "Helping the housing industry better understand and serve the justice-impacted population.", coverColor: "var(--rk-rhino-700)", coverIcon: "scale", coverText: "Toolkit", tags: ["Housing", "Toolkit"], onClick: () => go("profile") }),
          h(Card, { key: "2", client: "Learning Policy Institute", title: "Restarting & Reinventing School", description: "A framework to reimagine schooling using safe, equitable, student-centered approaches.", coverColor: "var(--rk-tomato-500)", coverIcon: "graduation-cap", coverText: "Framework", tags: ["Education", "Policy"], onClick: () => go("profile") }),
          h(Card, { key: "3", client: "Charles Stewart Mott Foundation", title: "Focus on Flint", description: "Dozens of charts and infographics across eight issues affecting the Flint community.", coverColor: "var(--rk-muffin)", coverIcon: "bar-chart-3", coverText: "Report", tags: ["Data", "Community"], onClick: () => go("profile") }),
        ]),
      ])
    ),
    // PATTERN LIBRARY TEASER
    h("section", { key: "pat", style: { background: "var(--rk-rhino-700)", padding: "80px 0" } },
      h("div", { style: { ...wrap, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 48, alignItems: "center" } }, [
        h("div", { key: "l", style: { display: "flex", flexDirection: "column", gap: 22 } }, [
          h(SectionHeading, { key: "sh", inverse: true, eyebrow: "Free resource", eyebrowColor: "macaroni", title: "The Info Design Pattern Library", intro: "A growing, open library of information-design patterns — examples, when to use each, and the tools to build them yourself." }),
          h("div", { key: "b" }, h(Button, { variant: "accent", size: "lg", iconRight: "arrow-right", onClick: () => go("patterns") }, "Browse the library")),
        ]),
        h("div", { key: "r", style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 } },
          [["layout-dashboard", "Layered navigation"], ["bar-chart-3", "Data visualization"], ["list-tree", "Expanding lists"], ["map", "Interactive maps"]].map((p, i) =>
            h("div", { key: i, style: { background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "var(--rk-radius-md)", padding: 20, display: "flex", flexDirection: "column", gap: 12 } }, [
              h(PatIcon, { key: "i", name: p[0] }),
              h("span", { key: "t", style: { fontFamily: "var(--rk-font-display)", fontWeight: 600, fontSize: 17, color: "#fff" } }, p[1]),
            ])
          )
        ),
      ])
    ),
    // CALLOUT
    h("section", { key: "cta", style: { padding: "80px 0" } },
      h("div", { style: wrap },
        h(Callout, { eyebrow: "Ready to cook?", title: "Let's turn your next report into something people use.", primaryLabel: "Contact the Kitchen", secondaryLabel: "See pricing", onClickPrimary: () => go("custom") }, "Tell us what you're publishing and we'll show you what's possible — no obligation, no reformatting.")
      )
    ),
  ]);
}

function PatIcon({ name }) {
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); });
  return h("i", { "data-lucide": name, width: 26, height: 26, style: { strokeWidth: 1.75,  color: "var(--rk-macaroni-500)" } });
}

window.RKSite = window.RKSite || {};
window.RKSite.Home = Home;
