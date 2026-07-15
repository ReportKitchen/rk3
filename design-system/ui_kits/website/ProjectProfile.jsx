// Report Kitchen website — Project Profile (Housing2Justice)
const RKp = window.ReportKitchenDesignSystem_07c3a7;
const hp = React.createElement;

function BeforeAfter() {
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); });
  const line = (w, c, k) => hp("div", { key: k, style: { height: 6, width: w, borderRadius: 4, background: c } });
  const panel = (label, tone) => hp("div", { style: { flex: 1, display: "flex", flexDirection: "column", gap: 12 } }, [
    hp("span", { key: "l", style: { fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 12, textTransform: "uppercase", letterSpacing: ".07em", color: tone === "before" ? "var(--rk-text-muted)" : "var(--rk-tomato)" } }, label),
    tone === "before"
      ? hp("div", { key: "c", style: { background: "#fff", border: "1px solid var(--rk-border)", borderRadius: "var(--rk-radius-sm)", padding: 22, display: "flex", flexDirection: "column", gap: 9, opacity: 0.75 } },
          [line("60%", "var(--rk-rhino-300)", "a"), line("100%", "var(--rk-rhino-100)", "b"), line("95%", "var(--rk-rhino-100)", "c"), line("100%", "var(--rk-rhino-100)", "d"), line("80%", "var(--rk-rhino-100)", "e"), line("100%", "var(--rk-rhino-100)", "f"), line("55%", "var(--rk-rhino-100)", "g")])
      : hp("div", { key: "c", style: { background: "#fff", border: "1px solid var(--rk-border)", borderRadius: "var(--rk-radius-md)", overflow: "hidden", boxShadow: "var(--rk-shadow-md)" } }, [
          hp("div", { key: "b", style: { background: "var(--rk-rhino-700)", padding: "16px 18px", display: "flex", flexDirection: "column", gap: 7 } }, [line("50%", "var(--rk-macaroni-500)", "a"), line("78%", "rgba(255,255,255,0.8)", "b")]),
          hp("div", { key: "body", style: { padding: 18, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 } }, [
            hp("div", { key: "x", style: { gridColumn: "1 / -1", height: 40, borderRadius: 8, background: "var(--rk-macaroni-100)", display: "flex", alignItems: "center", gap: 8, padding: "0 12px" } }, [hp("i", { key: "i", "data-lucide": "list-tree", width: 18, height: 18, style: { color: "var(--rk-macaroni-600)" } }), line("60%", "var(--rk-macaroni-300)", "ln")]),
            hp("div", { key: "a", style: { height: 34, borderRadius: 6, background: "var(--rk-gray-100)" } }),
            hp("div", { key: "c2", style: { height: 34, borderRadius: 6, background: "var(--rk-gray-100)" } }),
          ]),
        ]),
  ]);
  return hp("div", { style: { display: "flex", gap: 28, alignItems: "stretch" } }, [
    hp("div", { key: "b", style: { flex: 1 } }, panel("Before: static PDF", "before")),
    hp("div", { key: "arr", style: { display: "flex", alignItems: "center" } }, hp("i", { "data-lucide": "arrow-right", width: 28, height: 28, style: { strokeWidth: 2.5,  color: "var(--rk-tomato-500)" } })),
    hp("div", { key: "a", style: { flex: 1 } }, panel("After: interactive site", "after")),
  ]);
}

function ProjectProfile({ go }) {
  const { Button, Badge, Accordion, Callout, Tag } = RKp;
  const wrap = { maxWidth: 1080, margin: "0 auto", padding: "0 40px" };
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); });
  const stat = (n, l) => hp("div", { key: l, style: { display: "flex", flexDirection: "column", gap: 4 } }, [
    hp("span", { key: "n", style: { fontFamily: "var(--rk-font-display)", fontWeight: 800, fontSize: 42, color: "var(--rk-tomato-500)", letterSpacing: "-0.02em" } }, n),
    hp("span", { key: "l", style: { fontFamily: "var(--rk-font-body)", fontSize: 15, color: "var(--rk-text-muted)" } }, l),
  ]);
  return hp("div", null, [
    // back
    hp("div", { key: "back", style: { ...wrap, paddingTop: 28 } },
      hp("button", { onClick: () => go("work"), style: { all: "unset", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 7, fontFamily: "var(--rk-font-body)", fontWeight: 600, fontSize: 15, color: "var(--rk-text-muted)" } },
        [hp("i", { key: "i", "data-lucide": "arrow-left", width: 17, height: 17, style: { strokeWidth: 2.25 } }), "All work"])
    ),
    // hero
    hp("section", { key: "hero", style: { padding: "32px 0 56px" } },
      hp("div", { style: { ...wrap, display: "flex", flexDirection: "column", gap: 22 } }, [
        hp("div", { key: "tags", style: { display: "flex", gap: 8 } }, [hp(Tag, { key: "1", tone: "tomato" }, "Housing"), hp(Tag, { key: "2", tone: "muffin" }, "Toolkit")]),
        hp("span", { key: "cl", style: { fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 15, color: "var(--rk-text-muted)" } }, "Enterprise Community Partners"),
        hp("h1", { key: "h", style: { margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 800, fontSize: 56, lineHeight: 1.02, letterSpacing: "-0.03em", color: "var(--rk-text-strong)", maxWidth: 860, textWrap: "balance" } }, "Housing as a pathway to justice"),
        hp("p", { key: "p", style: { margin: 0, maxWidth: 680, fontFamily: "var(--rk-font-body)", fontSize: 20, lineHeight: 1.55, color: "var(--rk-text-muted)" } }, "Helping the housing industry better understand and serve the justice-impacted population — through an interactive national toolkit."),
        hp("div", { key: "cta", style: { display: "flex", gap: 12, marginTop: 4 } }, [hp(Button, { key: "a", iconRight: "external-link" }, "Visit the site"), hp(Button, { key: "b", variant: "secondary", onClick: () => go("custom") }, "Start a project like this")]),
      ])
    ),
    // before/after
    hp("section", { key: "ba", style: { background: "var(--rk-cream)", padding: "64px 0", borderTop: "1px solid var(--rk-border)", borderBottom: "1px solid var(--rk-border)" } },
      hp("div", { style: wrap }, hp(BeforeAfter))
    ),
    // stats + narrative
    hp("section", { key: "body", style: { padding: "64px 0" } },
      hp("div", { style: { ...wrap, display: "grid", gridTemplateColumns: "1fr 1.2fr", gap: 56, alignItems: "start" } }, [
        hp("div", { key: "stats", style: { display: "flex", flexDirection: "column", gap: 32 } }, [stat("80+", "pages of narrative content"), stat("50", "states of legal survey data"), stat("1", "searchable provider database"), stat("100%", "WCAG AA accessible")]),
        hp("div", { key: "narr", style: { display: "flex", flexDirection: "column", gap: 20 } }, [
          hp("h2", { key: "t", style: { margin: 0, fontFamily: "var(--rk-font-display)", fontWeight: 700, fontSize: 32, letterSpacing: "-0.02em", color: "var(--rk-text-strong)" } }, "The recipe"),
          hp("p", { key: "p1", style: { margin: 0, fontFamily: "var(--rk-font-body)", fontSize: 18, lineHeight: 1.65, color: "var(--rk-text-body)" } }, "We combined 80 pages of narrative content, a spreadsheet survey of state and local laws, and a database of service providers into a single interactive toolkit."),
          hp("p", { key: "p2", style: { margin: 0, fontFamily: "var(--rk-font-body)", fontSize: 18, lineHeight: 1.65, color: "var(--rk-text-body)" } }, "Layered content lets readers navigate, scan and filter to reach the most relevant material quickly. And as with every Report Kitchen site, admins get full analytics on what readers actually engage with — from accordions to expanding lists."),
          hp("div", { key: "acc", style: { marginTop: 8 } }, hp(Accordion, { items: [
            { q: "Layered navigation", a: "Accordions, modals and expanding lists keep a dense toolkit scannable without hiding depth." },
            { q: "Filterable law database", a: "Readers filter state and local laws to their jurisdiction in seconds." },
            { q: "Engagement analytics", a: "Site admins see exactly which sections and interactions readers open." },
          ] }))
        ]),
      ])
    ),
    // callout
    hp("section", { key: "cta", style: { padding: "0 0 88px" } },
      hp("div", { style: wrap }, hp(Callout, { tone: "tomato", eyebrow: "Your turn", title: "Does your organization produce toolkits or resource guides?", primaryLabel: "Get in touch", secondaryLabel: "See more work", onClickSecondary: () => go("work") }, "How much more engaging would they be if visitors could truly interact with your content instead of just downloading a PDF?"))
    ),
  ]);
}

window.RKSite = window.RKSite || {};
window.RKSite.ProjectProfile = ProjectProfile;
