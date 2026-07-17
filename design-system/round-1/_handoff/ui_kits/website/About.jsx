// Report Kitchen website — About (single page; story + values, photo-free)
const RKa = window.ReportKitchenDesignSystem_07c3a7;
const ha = React.createElement;

function About({ go }) {
  const { Eyebrow, SectionHeading, Callout, Button } = RKa;
  const wrap = { maxWidth: 1080, margin: "0 auto", padding: "0 40px" };
  const narrow = { maxWidth: 760, margin: "0 auto", padding: "0 40px" };
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); });

  const values = [
    { icon: "unlock", t: "Free the content", b: "The PDF is 25-year-old technology — conceived before smartphones, social media, or even Google. Your reports deserve modern, standards-compliant HTML." },
    { icon: "accessibility", t: "Accessible by default", b: "Real semantic structure, keyboard navigation, and screen-reader support on every build. Accessibility is a value, not an add-on." },
    { icon: "line-chart", t: "Built to be measured", b: "Video, mobile, dataviz, social, and full analytics — so you finally know what readers engage with." },
  ];

  const p = (txt, key) => ha("p", { key, style: { margin: 0, fontFamily: "var(--rk-font-body)", fontSize: 19, lineHeight: 1.7, color: "var(--rk-text-body)" } }, txt);

  return ha("div", null, [
    // HERO
    ha("section", { key: "hero", style: { background: "var(--rk-cream)", padding: "72px 0 64px", borderBottom: "1px solid var(--rk-border)" } },
      ha("div", { style: { ...wrap, display: "flex", flexDirection: "column", gap: 20 } }, [
        ha(Eyebrow, { key: "e" }, "About the Kitchen"),
        ha("h1", { key: "h", style: { margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 800, fontSize: 52, lineHeight: 1.05, letterSpacing: "-0.03em", color: "var(--rk-text-strong)", maxWidth: 880, textWrap: "balance" } },
          "We help our clients maximize the impact of their work — to improve our communities and the world."),
      ])
    ),
    // STORY
    ha("section", { key: "story", style: { padding: "72px 0" } },
      ha("div", { style: { ...narrow, display: "flex", flexDirection: "column", gap: 24 } }, [
        ha("span", { key: "k", style: { fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 13, textTransform: "uppercase", letterSpacing: ".08em", color: "var(--rk-tomato)" } }, "Our story"),
        p("The team behind Report Kitchen began building websites for nonprofits, foundations, and higher-education clients way back in 1999. As our capabilities with data, analytics, and visualization grew, we started working with more research and policy organizations — and we noticed some trends.", "s1"),
        p("The first was that these organizations produced a ton of PDF reports. The second was that nobody was reading them. We soon learned others in the field were having the same experience.", "s2"),
        p("We started brainstorming ways to make these reports more usable and engaging, and it came down to freeing them from the constraints of the PDF — a 25-year-old technology conceived before smartphones, social media, or even Google. The content needed modern, standards-compliant HTML. But writing and editing documents this size in the clumsy editors inside a CMS just wasn't realistic for most teams.", "s3"),
        p("So we built a suite of tools and processes to extract all the text, images, charts, and other content from Word or PDF documents, convert it to HTML, and assemble a web-based digital document with all the features you'd expect today — video, mobile, dataviz, social media, analytics, and much more. We call that platform Report Kitchen, and it's now the primary focus of our company.", "s4"),
        p("So while the platform is brand new, we bring over 20 years of experience designing and developing great web experiences for nonprofit, higher-ed, government, and corporate clients.", "s5"),
      ])
    ),
    // VALUES
    ha("section", { key: "vals", style: { background: "#fff", borderTop: "1px solid var(--rk-border)", borderBottom: "1px solid var(--rk-border)", padding: "72px 0" } },
      ha("div", { style: { ...wrap, display: "flex", flexDirection: "column", gap: 40 } }, [
        ha(SectionHeading, { key: "sh", eyebrow: "How we cook", title: "The principles behind every build" }),
        ha("div", { key: "g", style: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 22 } },
          values.map((v, i) => ha("div", { key: i, style: { display: "flex", flexDirection: "column", gap: 14, padding: 26, background: "var(--rk-paper)", border: "1px solid var(--rk-border)", borderRadius: "var(--rk-radius-lg)" } }, [
            ha("div", { key: "ic", style: { width: 50, height: 50, borderRadius: "var(--rk-radius-md)", background: "var(--rk-macaroni-100)", display: "flex", alignItems: "center", justifyContent: "center" } },
              ha("i", { "data-lucide": v.icon, width: 25, height: 25, style: { strokeWidth: 1.9, color: "var(--rk-macaroni-600)" } })),
            ha("h3", { key: "t", style: { margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 700, fontSize: 20, color: "var(--rk-text-strong)" } }, v.t),
            ha("p", { key: "b", style: { margin: 0, fontFamily: "var(--rk-font-body)", fontSize: 15.5, lineHeight: 1.6, color: "var(--rk-text-muted)" } }, v.b),
          ]))
        ),
      ])
    ),
    // EXPERIENCE STAT STRIP
    ha("section", { key: "stats", style: { padding: "64px 0" } },
      ha("div", { style: { ...wrap, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 24 } },
        [["20+ yrs", "designing web experiences"], ["1999", "building for mission-driven teams"], ["100%", "WCAG AA accessible builds"]].map((s, i) =>
          ha("div", { key: i, style: { display: "flex", flexDirection: "column", gap: 6, padding: "8px 0", borderTop: "3px solid var(--rk-tomato-500)" } }, [
            ha("span", { key: "n", style: { fontFamily: "var(--rk-font-display)", fontWeight: 800, fontSize: 46, letterSpacing: "-0.02em", color: "var(--rk-rhino-900)" } }, s[0]),
            ha("span", { key: "l", style: { fontFamily: "var(--rk-font-body)", fontSize: 16, color: "var(--rk-text-muted)" } }, s[1]),
          ])
        )
      )
    ),
    // CTA
    ha("section", { key: "cta", style: { padding: "0 0 88px" } },
      ha("div", { style: wrap }, ha(Callout, { eyebrow: "Let's work together", title: "Let's make your reports more interactive, engaging, and successful.", primaryLabel: "Contact the Kitchen", secondaryLabel: "See our work", onClickSecondary: () => go("work") }, "Contact us today — we'd love to help your research reports and policy documents reach the audience they deserve."))
    ),
  ]);
}

window.RKSite = window.RKSite || {};
window.RKSite.About = About;
