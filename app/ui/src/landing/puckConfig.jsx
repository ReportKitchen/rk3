import React from "react";
import { FieldLabel, usePuck } from "@measured/puck";
import { themeProps } from "./css.js";
import { ensureFont, primaryFamily } from "./fonts.js";
import { useLandingOptions } from "./landingOptions.js";
import { getAiSummary } from "../api.js";
import {
  Title, Summary, DocSummary, Cover, Hero, Toc, Highlights, Findings, Share, Download, SecondaryCta,
} from "./LandingRenderer.jsx";

// Document Summary render: reads the global drag state so the empty media slot
// (the floated-image drop target) only appears while something is being dragged.
function DocSummaryRender({ heading, blocks, floatTop, media: Media }) {
  const { appState } = usePuck();
  return (
    <DocSummary heading={heading} blocks={blocks} floatTop={floatTop}
      dragging={appState?.ui?.isDragging}>
      {Media ? <Media /> : null}
    </DocSummary>
  );
}

// slider to place the floated image between paragraphs: text above it runs
// full-width, text from there wraps around it (a float only affects what
// follows it, so this avoids the whitespace gap a margin-offset would leave)
function FloatPosition({ value, onChange }) {
  const { selectedItem } = usePuck();
  const max = (selectedItem?.props?.blocks || []).length;
  const v = Math.min(value || 0, max);
  return (
    <div className="lp-field-width">
      <input type="range" min="0" max={max || 1} step="1" value={v}
        onChange={(e) => onChange(+e.target.value)} />
      <span>{v === 0 ? "top" : `after ¶${v}`}</span>
    </div>
  );
}
// Puck auto-labels only its built-in field types; custom fields must render
// their own label (FieldLabel), or the panel shows bare controls
const floatTopField = {
  type: "custom",
  label: "Floated image position",
  render: ({ value, onChange }) => (
    <FieldLabel label="Floated image position" el="div">
      <FloatPosition value={value} onChange={onChange} />
    </FieldLabel>
  ),
};

// the Document Summary's section picker: a radio list of the document's detected
// intro/summary sections (per-document, so they arrive via LandingOptions)
function SectionPicker({ value, onChange }) {
  const { summarySections: sections } = useLandingOptions();
  if (!sections.length) return null;
  return (
    <div className="lp-section-pick">
      {sections.map((s) => (
        <label key={s.id} className={value === s.id ? "active" : ""}>
          <input type="radio" name="lp-section" checked={value === s.id} onChange={() => onChange(s.id)} />
          <span className="lp-sec-h">{s.heading}</span>
          <span className="lp-sec-len">{Math.round((s.words || 0) / 25) * 25} words</span>
        </label>
      ))}
    </div>
  );
}
const sectionField = {
  type: "custom",
  label: "Section (from the document)",
  render: ({ value, onChange }) => (
    <FieldLabel label="Section (from the document)" el="div">
      <SectionPicker value={value} onChange={onChange} />
    </FieldLabel>
  ),
};

const FONT = "'Public Sans', system-ui, -apple-system, sans-serif";

// content-width slider (Puck's number field is a plain input)
const widthField = {
  type: "custom",
  label: "Content width",
  render: ({ value, onChange }) => (
    <FieldLabel label="Content width" el="div">
      <div className="lp-field-width">
        <input type="range" min="600" max="1200" step="20" value={value || 800}
          onChange={(e) => onChange(+e.target.value)} />
        <input type="number" min="600" max="1200" value={value || 800}
          onChange={(e) => onChange(Math.min(1200, Math.max(600, +e.target.value || 800)))} />
        <span>px</span>
      </div>
    </FieldLabel>
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
    <FieldLabel label={label} el="div">
      <label className="lp-field-color">
        <input type="color" name={name} value={value || "#000000"}
          onChange={(e) => onChange(e.currentTarget.value)} />
        <span>{value || "#000000"}</span>
      </label>
    </FieldLabel>
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

// image picker: a select over the document's figures. Reads LandingOptions, not
// `puck.metadata` — a custom field's render never receives `puck`, so the old
// `puck?.metadata?.images` silently resolved to [] and this only ever offered
// "— none —".
function ImagePicker({ value, onChange }) {
  const { images } = useLandingOptions();
  return (
    <select value={value || ""} onChange={(e) => onChange(e.target.value)}>
      <option value="">— none —</option>
      {images.map((im) => <option key={im.src} value={im.src}>{im.label}</option>)}
    </select>
  );
}
const imageField = {
  type: "custom",
  label: "Image",
  render: ({ value, onChange }) => (
    <FieldLabel label="Image" el="div">
      <ImagePicker value={value} onChange={onChange} />
    </FieldLabel>
  ),
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
      // font has no UI control yet (set by the theme / Copy my site), but it is
      // a registered field so Puck round-trips the prop through root.props
      font: { type: "custom", render: () => null },
      leftSidebar: { ...onOff("Left sidebar (your site)") },
      rightSidebar: { ...onOff("Right sidebar (your site)") },
    },
    defaultProps: {
      contentWidth: 800, pageBg: "#ffffff", contentBg: "#ffffff",
      textColor: "#111111", headingColor: "#111111", accent: "#1b4965",
      font: FONT, leftSidebar: false, rightSidebar: false,
    },
    render: ({ contentWidth, pageBg, contentBg, textColor, headingColor, accent,
               font, leftSidebar, rightSidebar, children }) => {
      const { appState } = usePuck();
      // load the body font in the canvas iframe (this render runs inside it)
      React.useEffect(() => { ensureFont(primaryFamily(font), document); }, [font]);
      const style = themeProps({
        contentWidth,
        vars: {
          "--lp-page-bg": pageBg, "--lp-content-bg": contentBg,
          "--lp-text": textColor, "--lp-heading": headingColor, "--lp-accent": accent,
          "--lp-font": font || FONT,
        },
      });
      // simulate how the content sits inside a host page: grey header/footer
      // always, optional left/right sidebars; our content column is centered
      // and width-constrained, everything else is the host site's chrome
      return (
        <div className={"lp-sim" + (appState?.ui?.isDragging ? " lp-dragging" : "")}>
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
      label: "AI Summary",
      fields: {
        style: {
          type: "radio",
          label: "Style",
          options: [
            { label: "Report intro", value: "intro" },
            { label: "Summary", value: "neutral" },
            { label: "Hard sell", value: "hardsell" },
          ],
        },
        length: {
          type: "radio",
          label: "Length",
          options: [
            { label: "Short", value: "short" },
            { label: "Medium", value: "medium" },
            { label: "Long", value: "long" },
          ],
        },
        heading: { type: "text", label: "Heading (optional)" },
        text: { type: "textarea", label: "Summary", contentEditable: true },
      },
      defaultProps: { style: "intro", length: "medium", heading: "", text: "A short summary of the document." },
      // changing Style/Length swaps in that variant. Combos already generated
      // live in metadata.summaryVariants (keyed "style:length"); others are
      // generated lazily on the backend (async) and cached there.
      resolveData: async ({ props }, { changed, trigger, metadata }) => {
        if (trigger === "insert") {
          const d = metadata?.blockDefaults?.Summary;
          return d ? { props: { ...props, ...d } } : { props };
        }
        if (changed?.style || changed?.length) {
          const key = `${props.style}:${props.length}`;
          const v = metadata?.summaryVariants || {};
          if (v[key] != null) return { props: { ...props, text: v[key] } };
          if (!metadata?.slug) return { props };
          try {
            const text = await getAiSummary(metadata.slug, props.style, props.length);
            return { props: { ...props, text } };
          } catch { return { props }; }
        }
        return { props };
      },
      render: ({ text, style, heading }) => <Summary text={text} source={style} heading={heading} />,
    },
    DocSummary: {
      label: "Document Summary",
      fields: {
        sectionId: sectionField,
        heading: { type: "text", label: "Heading" },
        // drag a Cover or Hero in here to float it inside the text
        media: { type: "slot", label: "Floated image (drag a cover/hero here)", allow: ["Cover", "Hero"] },
        floatTop: floatTopField,
      },
      defaultProps: { sectionId: "", heading: "Summary", blocks: [], media: [], floatTop: 0 },
      // picking a Section swaps in that section's verbatim blocks + heading
      resolveData: ({ props }, { changed, trigger, metadata }) => {
        if (trigger === "insert") {
          const d = metadata?.blockDefaults?.DocSummary;
          return d ? { props: { ...props, ...d } } : { props };
        }
        if (changed?.sectionId) {
          const s = (metadata?.summarySections || []).find((x) => x.id === props.sectionId);
          return s ? { props: { ...props, blocks: s.blocks, heading: s.heading } } : { props };
        }
        return { props };
      },
      render: DocSummaryRender,
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
    Findings: {
      label: "Findings",
      fields: {
        heading: { type: "text", label: "Heading" },
        items: {
          type: "array",
          label: "Findings — a figure + the fact it belongs to",
          getItemSummary: (it) => [it.stat, it.text].filter(Boolean).join(" ").slice(0, 40) || "finding",
          arrayFields: {
            stat: { type: "text", label: "Stat (e.g. 47%, $2.3M)" },
            text: { type: "textarea", label: "Finding" },
          },
        },
      },
      defaultProps: { heading: "Key findings", items: [] },
      resolveData: insertDefaults("Findings"),
      render: ({ heading, items }) => <Findings heading={heading} items={items} />,
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
  title: "Title", summary: "Summary", docSummary: "DocSummary", cover: "Cover", hero: "Hero",
  toc: "Toc", highlights: "Highlights", findings: "Findings", share: "Share", download: "Download",
  secondaryCta: "SecondaryCta",
};
// props that hold slot content (nested blocks), by Puck type
export const SLOT_PROPS = { DocSummary: ["media"] };
export const PUCK_TO_TYPE = Object.fromEntries(
  Object.entries(TYPE_TO_PUCK).map(([k, v]) => [v, k]));
