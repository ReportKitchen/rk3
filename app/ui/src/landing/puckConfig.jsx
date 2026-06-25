import React from "react";
import { themeProps } from "./css.js";
import {
  Title, Summary, Cover, Hero, Toc, Highlights, Share, Download, SecondaryCta,
} from "./LandingRenderer.jsx";

const FONT = "'Public Sans', system-ui, -apple-system, sans-serif";

// content-width slider (Puck's number field is a plain input)
const widthField = {
  type: "custom",
  label: "Content width",
  render: ({ value, onChange }) => (
    <div className="lp-field-width">
      <input type="range" min="600" max="1200" step="20" value={value || 800}
        onChange={(e) => onChange(+e.target.value)} />
      <input type="number" min="600" max="1200" value={value || 800}
        onChange={(e) => onChange(Math.min(1200, Math.max(600, +e.target.value || 800)))} />
      <span>px</span>
    </div>
  ),
};

const onOff = (label) => ({
  type: "radio",
  label,
  options: [{ label: "Off", value: false }, { label: "On", value: true }],
});

// A custom color-swatch field (Puck has no built-in color type).
const color = (label) => ({
  type: "custom",
  label,
  render: ({ value, onChange, name }) => (
    <label className="lp-field-color">
      <input type="color" name={name} value={value || "#000000"}
        onChange={(e) => onChange(e.currentTarget.value)} />
      <span>{value || "#000000"}</span>
    </label>
  ),
});

// resolve a config image src to a server URL using the slug passed via metadata
const resolver = (puck) => {
  const base = puck?.metadata?.assetBase;
  return base ? (src) => `${base}/${src}` : (src) => src;
};
const dlHref = (puck) => puck?.metadata?.downloadHref || "#";

// prepopulate a freshly-dragged block from the document-aware defaults
// (metadata.blockDefaults is keyed by Puck type, already in Puck prop shape)
const insertDefaults = (key) => ({ props }, { trigger, metadata }) =>
  trigger === "insert" && metadata?.blockDefaults?.[key]
    ? { props: { ...props, ...metadata.blockDefaults[key] } }
    : { props };

// image picker: a select over the document's figures (from metadata)
const imageField = {
  type: "custom",
  label: "Image",
  render: ({ value, onChange, puck }) => {
    const imgs = puck?.metadata?.images || [];
    return (
      <select value={value || ""} onChange={(e) => onChange(e.target.value)}>
        <option value="">— none —</option>
        {imgs.map((im) => <option key={im.src} value={im.src}>{im.label}</option>)}
      </select>
    );
  },
};

// Each landing block as a Puck component. render reuses our block components;
// fields give contextual editing — inline contentEditable for text, scoped
// color swatches for per-element colors.
export const puckConfig = {
  root: {
    // page-wide theme + page-context preview (the surrounding site chrome is a
    // preview aid only — it is never part of the export)
    fields: {
      contentWidth: { ...widthField },
      pageBg: { ...color("Page background") },
      contentBg: { ...color("Content background") },
      textColor: { ...color("Body text") },
      headingColor: { ...color("Headings") },
      accent: { ...color("Accent / links") },
      leftSidebar: { ...onOff("Left sidebar (your site)") },
      rightSidebar: { ...onOff("Right sidebar (your site)") },
    },
    defaultProps: {
      contentWidth: 800, pageBg: "#ffffff", contentBg: "#ffffff",
      textColor: "#111111", headingColor: "#111111", accent: "#1b4965",
      leftSidebar: false, rightSidebar: false,
    },
    render: ({ contentWidth, pageBg, contentBg, textColor, headingColor, accent,
               leftSidebar, rightSidebar, children }) => {
      const style = themeProps({
        contentWidth,
        vars: {
          "--lp-page-bg": pageBg, "--lp-content-bg": contentBg,
          "--lp-text": textColor, "--lp-heading": headingColor, "--lp-accent": accent,
          "--lp-font": FONT,
        },
      });
      // simulate how the content sits inside a host page: grey header/footer
      // always, optional left/right sidebars; our content column is centered
      // and width-constrained, everything else is the host site's chrome
      return (
        <div className="lp-sim">
          <div className="lp-sim-bar lp-sim-header">Site header</div>
          <div className="lp-sim-mid">
            {leftSidebar ? <div className="lp-sim-side">Sidebar</div> : null}
            <div className="lp-sim-area">
              <div className="lp-sim-content" style={style}>
                <div className="lp-page">{children}</div>
              </div>
            </div>
            {rightSidebar ? <div className="lp-sim-side">Sidebar</div> : null}
          </div>
          <div className="lp-sim-bar lp-sim-footer">Site footer</div>
        </div>
      );
    },
  },
  components: {
    Title: {
      label: "Title",
      fields: {
        eyebrow: { type: "text", label: "Eyebrow (kicker)", contentEditable: true },
        title: { type: "text", label: "Main title", contentEditable: true },
        subtitle: { type: "text", label: "Subtitle / deck", contentEditable: true },
      },
      defaultProps: { eyebrow: "", title: "Document title", subtitle: "" },
      resolveData: insertDefaults("Title"),
      render: ({ eyebrow, title, subtitle }) => <Title eyebrow={eyebrow} title={title} subtitle={subtitle} />,
    },
    Summary: {
      label: "Summary",
      fields: {
        source: {
          type: "radio",
          label: "Version",
          options: [
            { label: "Report intro", value: "intro" },
            { label: "Summary", value: "neutral" },
            { label: "Hard sell", value: "hardsell" },
            { label: "Heuristic", value: "heuristic" },
          ],
        },
        heading: { type: "text", label: "Heading (optional)" },
        text: { type: "textarea", label: "Summary", contentEditable: true },
      },
      defaultProps: { source: "intro", heading: "", text: "A short summary of the document." },
      // switching Version swaps the text to the chosen variant. Source of truth
      // is the live extraction (metadata.summaryVariants), so it works even for
      // saved configs that predate this field. If the chosen version doesn't
      // exist (e.g. the heuristics found nothing), go blank — never silently
      // substitute a different version.
      resolveData: ({ props }, { changed, trigger, metadata }) => {
        if (trigger === "insert") {
          const d = metadata?.blockDefaults?.Summary;
          return d ? { props: { ...props, ...d } } : { props };
        }
        if (changed?.source) {
          const v = metadata?.summaryVariants || {};
          return { props: { ...props, text: v[props.source] || "" } };
        }
        return { props };
      },
      render: ({ text, source, heading }) => <Summary text={text} source={source} heading={heading} />,
    },
    Cover: {
      label: "Report cover",
      fields: { src: imageField, alt: { type: "text" } },
      defaultProps: { src: "pages/page-0001.png", alt: "Document cover" },
      resolveData: insertDefaults("Cover"),
      render: ({ src, alt, puck }) => <Cover src={src} alt={alt} resolveAsset={resolver(puck)} />,
    },
    Hero: {
      label: "Hero image",
      fields: { src: imageField, alt: { type: "text" } },
      defaultProps: { src: "", alt: "Hero image" },
      resolveData: insertDefaults("Hero"),
      render: ({ src, alt, puck }) => <Hero src={src} alt={alt} resolveAsset={resolver(puck)} />,
    },
    Toc: {
      label: "Table of contents",
      fields: {
        items: {
          type: "array",
          getItemSummary: (it) => it.text || "item",
          arrayFields: {
            text: { type: "text" },
            level: { type: "number", min: 2, max: 4 },
            anchor: { type: "text" },
          },
        },
      },
      defaultProps: { items: [] },
      resolveData: insertDefaults("Toc"),
      render: ({ items }) => <Toc items={items} />,
    },
    Highlights: {
      label: "Highlights",
      fields: {
        heading: { type: "text", label: "Heading" },
        items: {
          type: "array",
          label: "Points — 3–5 outcomes a reader cares about",
          getItemSummary: (it) => it.value || "point",
          arrayFields: { value: { type: "text" } },
        },
        bgColor: { ...color("Box color") },
      },
      defaultProps: { heading: "Highlights", items: [], bgColor: "#eef3fa" },
      resolveData: insertDefaults("Highlights"),
      // array fields store objects; map to strings for the renderer
      render: ({ items, bgColor, heading }) => (
        <Highlights heading={heading} bgColor={bgColor}
          items={(items || []).map((i) => (typeof i === "string" ? i : i.value))} />
      ),
    },
    Share: {
      label: "Social share",
      fields: {},
      defaultProps: {},
      render: () => <Share />,
    },
    Download: {
      label: "Download CTA",
      fields: {
        label: { type: "text", label: "Button text", contentEditable: true },
        bgColor: { ...color("Button color") },
        textColor: { ...color("Text color") },
      },
      defaultProps: { label: "Download the full report (PDF)", bgColor: "#1b4965", textColor: "#ffffff" },
      resolveData: insertDefaults("Download"),
      render: ({ label, bgColor, textColor, puck }) => (
        <Download label={label} bgColor={bgColor} textColor={textColor} downloadHref={dlHref(puck)} />
      ),
    },
    SecondaryCta: {
      label: "Secondary CTA",
      fields: {
        label: { type: "text", label: "Button text", contentEditable: true },
        url: { type: "text", label: "Link URL" },
        bgColor: { ...color("Button color") },
        textColor: { ...color("Text color") },
      },
      defaultProps: { label: "Learn more", url: "", bgColor: "#ffffff", textColor: "#1b4965" },
      resolveData: insertDefaults("SecondaryCta"),
      render: ({ label, url, bgColor, textColor }) => (
        <SecondaryCta label={label} url={url} bgColor={bgColor} textColor={textColor} />
      ),
    },
  },
};

// component type <-> our block type (Puck keys are capitalized)
export const TYPE_TO_PUCK = {
  title: "Title", summary: "Summary", cover: "Cover", hero: "Hero",
  toc: "Toc", highlights: "Highlights", share: "Share", download: "Download",
  secondaryCta: "SecondaryCta",
};
export const PUCK_TO_TYPE = Object.fromEntries(
  Object.entries(TYPE_TO_PUCK).map(([k, v]) => [v, k]));
