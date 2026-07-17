import React from "react";

// The block components. Each takes FLAT props (matching Puck's render
// signature) so the same components feed Puck's canvas, the static export, and
// any preview. `resolveAsset` maps a config image src to a usable URL (a server
// path in the editor/preview, a relative images/ path in export); `downloadHref`
// likewise differs by context. Per-element colors arrive as props and are
// applied inline, so they're edited in context (and map 1:1 to Puck fields).

const ident = (s) => s;

export function Title({ eyebrow, title, subtitle, text }) {
  const main = title || text || ""; // text: back-compat with single-field titles
  // an emptied field collapses away — no empty tag taking space in the output
  if (!eyebrow && !main && !subtitle) return null;
  return (
    <header className="lp-block lp-title">
      {eyebrow ? <p className="lp-eyebrow">{eyebrow}</p> : null}
      {main ? <h1>{main}</h1> : null}
      {subtitle ? <p className="lp-subtitle">{subtitle}</p> : null}
    </header>
  );
}

export function Summary({ text, source, heading }) {
  return (
    <section className="lp-block lp-summary" data-source={source || undefined}>
      {heading ? <h2>{heading}</h2> : null}
      <div className="lp-rich" dangerouslySetInnerHTML={{ __html: text || "" }} />
    </section>
  );
}

// Verbatim Document Summary: a whole intro/exec-summary section (rich HTML),
// with an optional image floated in its media slot so the text wraps around it.
// `children` is the slot content (a Cover/Hero), floated via CSS.
export function DocSummary({ heading, blocks, floatTop, paraLimit, dragging, children }) {
  const all = blocks || [];
  // paraLimit 0 = show all; otherwise cap the number of chunks (these sections
  // can run very long)
  const chunks = paraLimit > 0 ? all.slice(0, paraLimit) : all;
  // place the floated image *between* blocks: blocks before it run full-width,
  // blocks from there wrap around it (a float only affects following content)
  const at = Math.max(0, Math.min(floatTop || 0, chunks.length));
  const media = children ? <div className="lp-docsum-media">{children}</div> : null;
  const Chunk = (h, i) => <div key={i} dangerouslySetInnerHTML={{ __html: h }} />;
  return (
    <section className={"lp-block lp-docsum" + (dragging ? " lp-dragging" : "")}>
      {heading ? <h2>{heading}</h2> : null}
      <div className="lp-docsum-body">
        {chunks.slice(0, at).map(Chunk)}
        {media}
        {chunks.slice(at).map((h, i) => Chunk(h, at + i))}
      </div>
    </section>
  );
}

export function Cover({ src, alt, resolveAsset = ident }) {
  if (!src) return null;
  return (
    <figure className="lp-block lp-cover">
      <img src={resolveAsset(src)} alt={alt || ""} />
    </figure>
  );
}

export function Hero({ src, alt, caption, resolveAsset = ident }) {
  if (!src) return null;
  return (
    <figure className="lp-block lp-hero">
      <img src={resolveAsset(src)} alt={alt || ""} />
      {caption ? <figcaption>{caption}</figcaption> : null}
    </figure>
  );
}

export function Toc({ items }) {
  const list = items || [];
  if (!list.length) return null;
  // just a list of what's inside — not linked (there's nothing to link to)
  return (
    <section className="lp-block lp-toc" aria-label="Contents">
      <h2>Contents</h2>
      <ul>
        {list.map((it, i) => (
          <li key={i} className={`lvl-${it.level || 2}`}>{it.text}</li>
        ))}
      </ul>
    </section>
  );
}

const escapeHtml = (s) =>
  String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// legacy highlights stored an array of bullet strings (or Puck's {value}
// wrappers); build the equivalent <ul> so old docs still render and can migrate
export function itemsToUl(items) {
  const strs = (items || []).map((i) => (typeof i === "string" ? i : i?.value)).filter(Boolean);
  return strs.length ? "<ul>" + strs.map((t) => `<li>${escapeHtml(t)}</li>`).join("") + "</ul>" : "";
}

export function Highlights({ content, items, bgColor, heading }) {
  const html = content || itemsToUl(items);
  if (!html) return null;
  return (
    <section className="lp-block lp-highlights" style={bgColor ? { background: bgColor } : undefined}>
      <h2>{heading || "Highlights"}</h2>
      <div className="lp-rich" dangerouslySetInnerHTML={{ __html: html }} />
    </section>
  );
}

// Concrete findings: a headline figure (stat) + the fact it belongs to. The
// stat is isolated so it can later drive infographics/charts.
export function Findings({ heading, items }) {
  const list = (items || []).filter((it) => it && (it.stat || it.text));
  if (!list.length) return null;
  return (
    <section className="lp-block lp-findings">
      {heading ? <h2>{heading}</h2> : null}
      <ul>
        {list.map((it, i) => (
          <li key={i}>
            {it.stat ? <span className="lp-finding-stat">{it.stat}</span> : null}
            {it.text ? (
              <span className="lp-finding-text" dangerouslySetInnerHTML={{ __html: it.text }} />
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

// A pulled story or case study: a verbatim quote (when the story has one),
// a short narrative, and an attribution. Personal stories lead with the quote;
// a case study (no personal quote) leads with the narrative.
export function Storytelling({ subject, quote, narrative, attribution, page }) {
  if (!quote && !narrative) return null;
  const initial = (subject || attribution || "").trim().charAt(0).toUpperCase();
  return (
    <section className="lp-block lp-story">
      {page ? <p className="lp-story-src">From the report · {page}</p> : null}
      {quote ? <blockquote className="lp-story-quote">{quote}</blockquote> : null}
      {narrative ? <p className="lp-story-body">{narrative}</p> : null}
      {attribution ? (
        <p className="lp-story-attr">
          {initial ? <span className="lp-story-avatar" aria-hidden="true">{initial}</span> : null}
          <span>{attribution}</span>
        </p>
      ) : null}
    </section>
  );
}

// Monochrome brand glyphs (fill: currentColor, so they take the link colour in
// "plain" style and white on the filled buttons). Same set feeds the block, the
// network picker, and the style preview.
const SHARE_ICONS = {
  linkedin: "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.225 0z",
  x: "M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z",
  bluesky: "M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566.944 1.561 1.266.902 1.565.139 1.908 0 3.08 0 3.768c0 .69.378 5.65.624 6.479.815 2.736 3.713 3.66 6.383 3.364.136-.02.275-.039.415-.056-.138.022-.276.04-.415.056-3.912.58-7.387 2.005-2.83 7.078 5.013 5.19 6.87-1.113 7.823-4.308.953 3.195 2.05 9.271 7.733 4.308 4.267-4.308 1.172-6.498-2.74-7.078a8.741 8.741 0 01-.415-.056c.14.017.279.036.415.056 2.67.297 5.568-.628 6.383-3.364.246-.828.624-5.79.624-6.478 0-.69-.139-1.861-.902-2.206-.659-.298-1.664-.62-4.3 1.24C16.046 4.748 13.087 8.687 12 10.8z",
  facebook: "M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z",
  instagram: "M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z",
  link: "M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z",
};

// order shown in the block and the picker; "link"/"instagram" copy the page URL
// (Instagram has no web share intent), the rest open a share dialog
export const SHARE_NETWORKS = [
  { key: "linkedin", label: "LinkedIn" },
  { key: "x", label: "X" },
  { key: "bluesky", label: "Bluesky" },
  { key: "facebook", label: "Facebook" },
  { key: "instagram", label: "Instagram" },
  { key: "link", label: "Copy link" },
];
export const DEFAULT_NETWORKS = { linkedin: true, x: true, link: true };

export function ShareGlyph({ net, size = 20 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor" aria-hidden="true">
      <path d={SHARE_ICONS[net]} />
    </svg>
  );
}

// Share row. Buttons carry data-share; the export injects a click handler that
// builds each share URL from the LIVE page URL (so it works wherever the page
// is hosted). In the editor/preview there's no such script — clicks are inert.
export function Share({ heading = "Share", networks, style = "plain" }) {
  const on = networks || DEFAULT_NETWORKS;
  const items = SHARE_NETWORKS.filter((n) => on[n.key]);
  if (!items.length) return null;
  return (
    <div className={"lp-block lp-share lp-share-" + (style || "plain")}>
      {heading ? <span className="lp-share-label">{heading}</span> : null}
      <div className="lp-share-btns">
        {items.map((n) => (
          <a key={n.key} className="lp-share-btn" href="#" data-share={n.key}
            aria-label={n.label} title={n.label} onClick={(e) => e.preventDefault()}>
            <ShareGlyph net={n.key} size={(style || "plain") === "plain" ? 22 : 19} />
          </a>
        ))}
      </div>
    </div>
  );
}

export function Download({ label, mode, url, bgColor, textColor, downloadHref }) {
  // bundle => the exported/hosted PDF (download attr); url => the user's own
  // hosted PDF (a plain link)
  const useUrl = mode === "url";
  const href = useUrl ? (url || "#") : (downloadHref || "#");
  return (
    <div className="lp-block lp-download">
      <a className="lp-cta" href={href} {...(useUrl ? {} : { download: true })}
        style={{ background: bgColor || "#1b4965", color: textColor || "#fff" }}>
        {label || "Download the full report (PDF)"}
      </a>
    </div>
  );
}

export function SecondaryCta({ label, url, bgColor, textColor }) {
  return (
    <div className="lp-block lp-secondary">
      <a className="lp-cta lp-cta-outline" href={url || "#"}
        style={{ background: bgColor || "#ffffff", color: textColor || "#1b4965" }}>
        {label || "Learn more"}
      </a>
    </div>
  );
}

// A content SECTION (the AI-sections model, BACKLOG/61): one meaningful unit of
// the document, in its own heading + words, rendered with one presentation
// primitive. Styling lives in landingPage.css (.lp-sec-*) and is deliberately
// RELATIVE (em/%, inherits font + colour) so the exported section drops into the
// host site's own CSS.
// Stat treatments (design-system/stats): greyscale + one settable accent
// (--lp-accent), each reflowing from 1 to many stats. `bars` is percentage-only.
const STAT_TREATMENTS = ["cards", "list", "tiles", "band", "hero", "bars"];
const pctOf = (v) => {
  const m = String(v || "").match(/(\d[\d.,]*)\s*%/);
  return m ? Math.max(0, Math.min(100, parseFloat(m[1].replace(/,/g, "")))) : null;
};
export const allPercent = (cards) =>
  (cards || []).length > 0 && cards.every((c) => pctOf(c.value) !== null);
// which treatments are offered for this many cards / this data
export function statTreatmentsFor(cards) {
  const n = (cards || []).length;
  return STAT_TREATMENTS.filter((t) => {
    if (t === "bars") return allPercent(cards);
    if (t === "hero") return n >= 1;
    return true;
  });
}

function StatCards({ cards, treatment = "cards" }) {
  const list = (cards || []).filter((c) => c && (c.value || c.label));
  if (!list.length) return null;
  const t = statTreatmentsFor(list).includes(treatment) ? treatment : "cards";
  const cols = Math.min(list.length, 3);
  const V = ({ c }) => <span className="lp-stat-v">{c.value}</span>;
  const L = ({ c }) => <span className="lp-stat-l" dangerouslySetInnerHTML={{ __html: c.label || "" }} />;

  if (t === "list") {
    return (
      <ul className="lp-stat-list">
        {list.map((c, i) => (
          <li key={i}><span className="lp-stat-tick" /><span><strong>{c.value}</strong>{c.label ? " " : ""}<span dangerouslySetInnerHTML={{ __html: c.label || "" }} /></span></li>
        ))}
      </ul>
    );
  }
  if (t === "tiles") {
    return (
      <div className="lp-stat-tiles" style={{ "--cols": cols }}>
        {list.map((c, i) => <div key={i} className="lp-stat-tile"><V c={c} /><L c={c} /></div>)}
      </div>
    );
  }
  if (t === "band") {
    return (
      <div className="lp-stat-band" style={{ "--cols": cols }}>
        {list.map((c, i) => <div key={i} className="lp-stat-bandcell"><V c={c} /><L c={c} /></div>)}
      </div>
    );
  }
  if (t === "hero") {
    const [head, ...rail] = list;
    return (
      <div className="lp-stat-hero">
        <div className="lp-stat-herolead"><span className="lp-stat-v">{head.value}</span><L c={head} /></div>
        {rail.length ? (
          <div className="lp-stat-rail">
            {rail.map((c, i) => <div key={i} className="lp-stat-railrow"><span className="lp-stat-railv">{c.value}</span><L c={c} /></div>)}
          </div>
        ) : null}
      </div>
    );
  }
  if (t === "bars") {
    return (
      <div className="lp-stat-bars">
        {list.map((c, i) => {
          const pct = pctOf(c.value) ?? 0;
          return (
            <div key={i} className="lp-stat-bar">
              <div className="lp-stat-barhd"><L c={c} /><span className="lp-stat-v">{c.value}</span></div>
              <div className="lp-stat-track"><div className="lp-stat-fill" style={{ width: `${pct}%` }} /></div>
            </div>
          );
        })}
      </div>
    );
  }
  // cards (default)
  return (
    <div className="lp-stat-cards" style={{ "--cols": cols }}>
      {list.map((c, i) => <div key={i} className="lp-stat-card"><V c={c} /><L c={c} /></div>)}
    </div>
  );
}

export function Section({ heading, presentation, prose, bullets, cards, quote, steps, treatment }) {
  const q = quote || {};
  const hasContent =
    (presentation === "prose" && prose) ||
    (presentation === "bullets" && (bullets || []).length) ||
    (presentation === "statCards" && (cards || []).length) ||
    (presentation === "quote" && q.text) ||
    (presentation === "steps" && (steps || []).length);
  if (!heading && !hasContent) return null;
  return (
    <section className="lp-block lp-section" data-pres={presentation}>
      {heading ? <h2>{heading}</h2> : null}
      {presentation === "prose" && (
        <div className="lp-rich" dangerouslySetInnerHTML={{ __html: prose || "" }} />
      )}
      {presentation === "bullets" && (bullets || []).length ? (
        <ul className="lp-sec-bullets">
          {bullets.map((b, i) => <li key={i} dangerouslySetInnerHTML={{ __html: b }} />)}
        </ul>
      ) : null}
      {presentation === "statCards" && (cards || []).length ? (
        <StatCards cards={cards} treatment={treatment} />
      ) : null}
      {presentation === "quote" && q.text ? (
        <figure className={"lp-sec-quote" + (q.pull ? " is-pull" : "")}>
          <blockquote>{q.text}</blockquote>
          {q.attribution ? <figcaption>{q.attribution}</figcaption> : null}
        </figure>
      ) : null}
      {presentation === "steps" && (steps || []).length ? (
        <ol className="lp-sec-steps">
          {steps.map((s, i) => (
            <li key={i}>
              {s.label ? <span className="lp-sec-step-l">{s.label}</span> : null}
              {s.body ? <span className="lp-sec-step-b" dangerouslySetInnerHTML={{ __html: s.body }} /> : null}
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}

export const BLOCKS = {
  title: Title, summary: Summary, docSummary: DocSummary, cover: Cover, hero: Hero,
  toc: Toc, highlights: Highlights, findings: Findings, storytelling: Storytelling,
  share: Share, download: Download, secondaryCta: SecondaryCta, section: Section,
};

// Render one block, recursing into the media slot (nested blocks become the
// component's children — e.g. a cover floated inside a Document Summary).
function renderBlock(b, ctx) {
  const Comp = BLOCKS[b.type];
  if (!Comp) return null;
  const { media, ...props } = b.props || {};
  const children = (media || []).map((m) => renderBlock(m, ctx));
  return (
    <Comp key={b.id} {...props} resolveAsset={ctx.resolveAsset} downloadHref={ctx.downloadHref}>
      {children.length ? children : null}
    </Comp>
  );
}

// Render a whole config (used by the static export). Editing uses Puck, which
// renders these same components per block.
export function LandingRenderer({ config, resolveAsset, downloadHref }) {
  const ctx = { resolveAsset, downloadHref };
  return <>{(config?.blocks || []).map((b) => renderBlock(b, ctx))}</>;
}
