import React from "react";

// The block components. Each renders one enabled block; the same components
// feed the live preview (portaled into the iframe) and the static export
// (renderToStaticMarkup). `resolveAsset` maps a config image src to a usable
// URL (a server path in preview, a relative images/ path in export);
// `downloadHref` likewise differs between the two contexts.

function Title({ props }) {
  return <header className="lp-block lp-title"><h1>{props.text}</h1></header>;
}

function Summary({ props }) {
  return (
    <section className="lp-block lp-summary" data-source={props.source || undefined}>
      <p>{props.text}</p>
    </section>
  );
}

function Cover({ props, resolveAsset }) {
  if (!props.src) return null;
  return (
    <figure className="lp-block lp-cover">
      <img src={resolveAsset(props.src)} alt={props.alt || ""} />
    </figure>
  );
}

function Hero({ props, resolveAsset }) {
  if (!props.src) return null;
  return (
    <figure className="lp-block lp-hero">
      <img src={resolveAsset(props.src)} alt={props.alt || ""} />
    </figure>
  );
}

function Toc({ props }) {
  const items = props.items || [];
  if (!items.length) return null;
  return (
    <nav className="lp-block lp-toc" aria-label="Contents">
      <h2>Contents</h2>
      <ul>
        {items.map((it, i) => (
          <li key={i} className={`lvl-${it.level || 2}`}>
            {it.anchor ? <a href={`#${it.anchor}`}>{it.text}</a> : it.text}
          </li>
        ))}
      </ul>
    </nav>
  );
}

function Highlights({ props }) {
  const items = props.items || [];
  if (!items.length) return null;
  return (
    <section className="lp-block lp-highlights">
      <h2>Highlights</h2>
      <ul>{items.map((t, i) => <li key={i}>{t}</li>)}</ul>
    </section>
  );
}

function Share() {
  return (
    <div className="lp-block lp-share">
      <span className="lp-share-label">Share</span>
      <a href="#" data-share="link">Copy link</a>
      <a href="#" data-share="linkedin">LinkedIn</a>
      <a href="#" data-share="x">X</a>
    </div>
  );
}

function Download({ props, downloadHref }) {
  return (
    <div className="lp-block lp-download">
      <a className="lp-cta" href={downloadHref || "#"} download>
        {props.label || "Download the full report (PDF)"}
      </a>
    </div>
  );
}

const BLOCKS = {
  title: Title, summary: Summary, cover: Cover, hero: Hero,
  toc: Toc, highlights: Highlights, share: Share, download: Download,
};

export function LandingRenderer({ config, resolveAsset, downloadHref }) {
  return (
    <>
      {(config?.blocks || [])
        .filter((b) => b.enabled)
        .map((b) => {
          const Comp = BLOCKS[b.type];
          if (!Comp) return null;
          return (
            <Comp key={b.id} props={b.props || {}}
              resolveAsset={resolveAsset} downloadHref={downloadHref} />
          );
        })}
    </>
  );
}

// human labels for the controls panel
export const BLOCK_LABELS = {
  title: "Title", summary: "Summary", cover: "Report cover", hero: "Hero image",
  toc: "Table of contents", highlights: "Highlights", share: "Social share",
  download: "Download CTA",
};
