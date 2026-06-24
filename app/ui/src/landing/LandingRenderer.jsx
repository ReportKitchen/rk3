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
  return (
    <header className="lp-block lp-title">
      {eyebrow ? <p className="lp-eyebrow">{eyebrow}</p> : null}
      <h1>{main}</h1>
      {subtitle ? <p className="lp-subtitle">{subtitle}</p> : null}
    </header>
  );
}

export function Summary({ text, source, heading }) {
  return (
    <section className="lp-block lp-summary" data-source={source || undefined}>
      {heading ? <h2>{heading}</h2> : null}
      <p>{text}</p>
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

export function Hero({ src, alt, resolveAsset = ident }) {
  if (!src) return null;
  return (
    <figure className="lp-block lp-hero">
      <img src={resolveAsset(src)} alt={alt || ""} />
    </figure>
  );
}

export function Toc({ items }) {
  const list = items || [];
  if (!list.length) return null;
  return (
    <nav className="lp-block lp-toc" aria-label="Contents">
      <h2>Contents</h2>
      <ul>
        {list.map((it, i) => (
          <li key={i} className={`lvl-${it.level || 2}`}>
            {it.anchor ? <a href={`#${it.anchor}`}>{it.text}</a> : it.text}
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function Highlights({ items, bgColor, heading }) {
  const list = items || [];
  if (!list.length) return null;
  return (
    <section className="lp-block lp-highlights" style={bgColor ? { background: bgColor } : undefined}>
      <h2>{heading || "Highlights"}</h2>
      <ul>{list.map((t, i) => <li key={i}>{t}</li>)}</ul>
    </section>
  );
}

export function Share() {
  return (
    <div className="lp-block lp-share">
      <span className="lp-share-label">Share</span>
      <a href="#" data-share="link">Copy link</a>
      <a href="#" data-share="linkedin">LinkedIn</a>
      <a href="#" data-share="x">X</a>
    </div>
  );
}

export function Download({ label, bgColor, textColor, downloadHref }) {
  return (
    <div className="lp-block lp-download">
      <a className="lp-cta" href={downloadHref || "#"} download
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

export const BLOCKS = {
  title: Title, summary: Summary, cover: Cover, hero: Hero,
  toc: Toc, highlights: Highlights, share: Share, download: Download,
  secondaryCta: SecondaryCta,
};

export const BLOCK_LABELS = {
  title: "Title", summary: "Summary", cover: "Report cover", hero: "Hero image",
  toc: "Table of contents", highlights: "Highlights", share: "Social share",
  download: "Download CTA", secondaryCta: "Secondary CTA",
};

// Render a whole config (used by the static export). Editing uses Puck, which
// renders these same components per block.
export function LandingRenderer({ config, resolveAsset, downloadHref }) {
  return (
    <>
      {(config?.blocks || []).map((b) => {
        const Comp = BLOCKS[b.type];
        if (!Comp) return null;
        return (
          <Comp key={b.id} {...(b.props || {})}
            resolveAsset={resolveAsset} downloadHref={downloadHref} />
        );
      })}
    </>
  );
}
