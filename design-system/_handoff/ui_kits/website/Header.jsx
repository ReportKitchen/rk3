// Report Kitchen website — shared Header + Footer
// Reads primitives from the DS bundle; exposes RKSite.Header / RKSite.Footer.
const RKe = React.createElement;

function Header({ current, go }) {
  const { Button } = window.ReportKitchenDesignSystem_07c3a7;
  const [openMenu, setOpenMenu] = React.useState(false);
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); });
  const nav = [
    { id: "work", label: "Our Work" },
    { id: "insights", label: "Insights" },
    { id: "about", label: "About" },
  ];
  const services = [
    { id: "maker", label: "Landing Page Maker", note: "Available now", icon: "wand-sparkles",
      desc: "Upload a PDF and build a polished landing page for it — free for individuals, paid for teams." },
    { id: "express", label: "Report Kitchen Express", note: "Coming soon", icon: "globe",
      desc: "Upload a PDF and get a fully responsive HTML website, automatically. Free & paid tiers." },
    { id: "custom", label: "Report Kitchen Custom", note: "Available now", icon: "chef-hat",
      desc: "Hand us your PDF; we build you a bespoke, responsive, accessible website end to end." },
    { id: "consulting", label: "Consulting", note: "Available now", icon: "messages-square",
      desc: "Guidance at the intersection of nonprofit communications, long-form reports, and AI." },
  ];

  return RKe("header", {
    style: {
      position: "sticky", top: 0, zIndex: 50,
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "16px 40px",
      background: "rgba(251,247,240,0.86)", backdropFilter: "blur(10px)",
      borderBottom: "1px solid var(--rk-border)",
    },
  }, [
    RKe("a", { key: "logo", href: "#", onClick: (e) => { e.preventDefault(); go("home"); },
      style: { display: "flex", alignItems: "center" } },
      RKe("img", { src: "../../assets/logo-red.svg", alt: "Report Kitchen", style: { height: 38 } })
    ),
    RKe("nav", { key: "nav", style: { display: "flex", alignItems: "center", gap: 4 } }, [
      // SERVICES megamenu
      RKe("div", { key: "svc", style: { position: "static" },
        onMouseEnter: () => setOpenMenu(true), onMouseLeave: () => setOpenMenu(false) }, [
        RKe("button", { key: "b", style: navLink(openMenu), onClick: () => go("custom") }, [
          "Services",
          RKe("i", { key: "c", "data-lucide": "chevron-down", width: 15, height: 15, style: { strokeWidth: 2.25, marginLeft: 4, transform: openMenu ? "rotate(180deg)" : "none", transition: "transform var(--rk-dur)" } }),
        ]),
        openMenu ? RKe("div", { key: "m", style: {
          position: "absolute", top: "100%", left: 40, right: 40,
          background: "#fff", border: "1px solid var(--rk-border)", borderRadius: "var(--rk-radius-lg)",
          boxShadow: "var(--rk-shadow-lg)", padding: 20, marginTop: 8,
          display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8,
        } }, [
          RKe("div", { key: "hd", style: { gridColumn: "1 / -1", display: "flex", alignItems: "baseline", justifyContent: "space-between", padding: "2px 8px 10px", marginBottom: 4, borderBottom: "1px solid var(--rk-border)" } }, [
            RKe("span", { key: "t", style: { fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 12, textTransform: "uppercase", letterSpacing: ".08em", color: "var(--rk-tomato)" } }, "What's on the menu"),
            RKe("span", { key: "s", style: { fontFamily: "var(--rk-font-body)", fontSize: 13, color: "var(--rk-text-muted)" } }, "Four ways to serve your work"),
          ]),
          ...services.map((o) =>
            RKe("a", { key: o.id, href: "#", onClick: (e) => { e.preventDefault(); go(o.id); },
              style: { display: "flex", gap: 14, padding: "14px 12px", borderRadius: "var(--rk-radius-md)", textDecoration: "none" },
              onMouseEnter: (e) => e.currentTarget.style.background = "var(--rk-gray-100)",
              onMouseLeave: (e) => e.currentTarget.style.background = "transparent" }, [
              RKe("div", { key: "ic", style: { flexShrink: 0, width: 42, height: 42, borderRadius: "var(--rk-radius-md)", background: "var(--rk-tomato-100)", display: "flex", alignItems: "center", justifyContent: "center" } },
                RKe("i", { "data-lucide": o.icon, width: 22, height: 22, style: { strokeWidth: 2, color: "var(--rk-tomato-600)" } })),
              RKe("div", { key: "tx", style: { display: "flex", flexDirection: "column", gap: 3 } }, [
                RKe("div", { key: "top", style: { display: "flex", alignItems: "center", gap: 8 } }, [
                  RKe("span", { key: "l", style: { fontFamily: "var(--rk-font-display)", fontWeight: 700, fontSize: 16, color: "var(--rk-text-strong)" } }, o.label),
                  RKe("span", { key: "n", style: { fontSize: 10.5, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".05em", padding: "2px 7px", borderRadius: 999,
                    background: o.note === "Coming soon" ? "var(--rk-macaroni-100)" : "rgba(46,139,87,0.12)",
                    color: o.note === "Coming soon" ? "var(--rk-macaroni-600)" : "#1F6B41" } }, o.note),
                ]),
                RKe("span", { key: "d", style: { fontFamily: "var(--rk-font-body)", fontSize: 13.5, lineHeight: 1.45, color: "var(--rk-text-muted)" } }, o.desc),
              ]),
            ])
          ),
        ]) : null,
      ]),
      ...nav.map((n) => RKe("a", { key: n.id, href: "#",
        onClick: (e) => { e.preventDefault(); go(n.id); }, style: navLink(current === n.id) }, n.label)),
      // PATTERN LIBRARY — set off as a distinct free resource
      RKe("a", { key: "patterns", href: "#", onClick: (e) => { e.preventDefault(); go("patterns"); },
        style: { display: "inline-flex", alignItems: "center", gap: 7, marginLeft: 6, padding: "7px 14px",
          fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 15, textDecoration: "none",
          color: current === "patterns" ? "var(--rk-rhino-900)" : "var(--rk-rhino-700)",
          border: "1.5px solid var(--rk-border-strong)", borderRadius: "var(--rk-radius-pill)",
          transition: "border-color var(--rk-dur), background var(--rk-dur)" },
        onMouseEnter: (e) => { e.currentTarget.style.borderColor = "var(--rk-macaroni-500)"; e.currentTarget.style.background = "var(--rk-macaroni-100)"; },
        onMouseLeave: (e) => { e.currentTarget.style.borderColor = "var(--rk-border-strong)"; e.currentTarget.style.background = "transparent"; } }, [
        RKe("i", { key: "i", "data-lucide": "book-open", width: 16, height: 16, style: { strokeWidth: 2, color: "var(--rk-macaroni-600)" } }),
        "Pattern Library",
      ]),
      RKe("div", { key: "cta", style: { marginLeft: 10 } },
        RKe(Button, { size: "sm", iconRight: "arrow-right", onClick: () => go("custom") }, "Contact the Kitchen")),
    ]),
  ]);
}

function navLink(active) {
  return {
    display: "inline-flex", alignItems: "center",
    background: "none", border: "none", cursor: "pointer",
    fontFamily: "var(--rk-font-body)", fontWeight: 600, fontSize: 15,
    color: active ? "var(--rk-tomato-600)" : "var(--rk-rhino-700)",
    textDecoration: "none", padding: "8px 14px", borderRadius: "var(--rk-radius-sm)",
  };
}

function Footer({ go }) {
  React.useEffect(() => { if (window.lucide) window.lucide.createIcons(); });
  const col = (title, links) => RKe("div", { key: title, style: { display: "flex", flexDirection: "column", gap: 12 } }, [
    RKe("span", { key: "t", style: { fontFamily: "var(--rk-font-body)", fontWeight: 700, fontSize: 13,
      textTransform: "uppercase", letterSpacing: ".07em", color: "var(--rk-macaroni-500)" } }, title),
    ...links.map((l, i) => RKe("a", { key: i, href: "#", onClick: (e) => { e.preventDefault(); l[1] && go(l[1]); },
      style: { fontFamily: "var(--rk-font-body)", fontSize: 15, color: "var(--rk-text-on-dark)", textDecoration: "none", opacity: 0.85 } }, l[0])),
  ]);
  return RKe("footer", { style: { background: "var(--rk-rhino-900)", color: "#fff", padding: "64px 40px 40px", position: "relative", overflow: "hidden" } }, [
    RKe("img", { key: "w", src: "../../assets/whisk-white.svg", alt: "", "aria-hidden": "true",
      style: { position: "absolute", right: -30, bottom: -20, width: 260, opacity: 0.08, transform: "rotate(-10deg)" } }),
    RKe("div", { key: "grid", style: { position: "relative", display: "grid", gridTemplateColumns: "1.6fr 1fr 1fr 1fr", gap: 40, maxWidth: 1200, margin: "0 auto" } }, [
      RKe("div", { key: "brand", style: { display: "flex", flexDirection: "column", gap: 16 } }, [
        RKe("img", { key: "l", src: "../../assets/logo-white.svg", alt: "Report Kitchen", style: { height: 40 } }),
        RKe("p", { key: "p", style: { margin: 0, maxWidth: 300, fontFamily: "var(--rk-font-body)", fontSize: 15, lineHeight: 1.6, color: "var(--rk-text-on-dark)", opacity: 0.85 } },
          "We turn dense PDFs into interactive, accessible websites your audience will actually use."),
        RKe("div", { key: "c", style: { fontFamily: "var(--rk-font-body)", fontSize: 15, lineHeight: 1.7, opacity: 0.85 } }, [
          RKe("div", { key: "e" }, "info@reportkitchen.com"),
          RKe("div", { key: "ph" }, "215-592-7673"),
        ]),
      ]),
      col("Offerings", [["Landing Page Maker", "maker"], ["RK Express", "express"], ["Report Kitchen Custom", "custom"], ["Consulting", "consulting"]]),
      col("Explore", [["Our Work", "work"], ["Pattern Library", "patterns"], ["Insights", "insights"], ["About", "about"]]),
      col("Company", [["How we use AI"], ["Privacy Policy"], ["Contact the Kitchen", "custom"]]),
    ]),
    RKe("div", { key: "base", style: { position: "relative", maxWidth: 1200, margin: "40px auto 0", paddingTop: 24, borderTop: "1px solid rgba(255,255,255,0.12)", display: "flex", justifyContent: "space-between", fontFamily: "var(--rk-font-body)", fontSize: 13, color: "rgba(255,255,255,0.55)" } }, [
      RKe("span", { key: "c" }, "© 2025 Report Kitchen"),
      RKe("span", { key: "m" }, "Baked with \u2764\uFE0F in Philadelphia"),
    ]),
  ]);
}

window.RKSite = window.RKSite || {};
window.RKSite.Header = Header;
window.RKSite.Footer = Footer;
window.RKSite.navLink = navLink;
