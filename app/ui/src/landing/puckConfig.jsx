import React from "react";
import { usePuck } from "@measured/puck";
import { themeProps } from "./css.js";
import { ensureFont, primaryFamily } from "./fonts.js";
import { useLandingOptions } from "./landingOptions.js";
import { getAiSummary } from "../api.js";
import {
  Title, Summary, DocSummary, Cover, Hero, Toc, Highlights, Findings, Share, Download, SecondaryCta,
} from "./LandingRenderer.jsx";

// One compact field wrapper for the whole modal, matching the design kit.
// It is BOTH Puck's fieldLabel override (built-in text/radio/textarea fields —
// stacked, for the block config) and the label for our custom fields, which
// pass `row` for the label-left / control-right rows the kit uses in Page setup.
// Same markup either way, so landing.css styles every field uniformly.
export function LpField({ label, row, children }) {
  return (
    <div className={"lp-field" + (row ? " row" : "")}>
      {label ? <span className="lp-field-lbl">{label}</span> : null}
      <div className="lp-field-ctl">{children}</div>
    </div>
  );
}

// Document Summary render: reads the global drag state so the empty media slot
// (the floated-image drop target) only appears while something is being dragged.
function DocSummaryRender({ heading, blocks, floatTop, paraLimit, media: Media }) {
  const { appState } = usePuck();
  return (
    <DocSummary heading={heading} blocks={blocks} floatTop={floatTop} paraLimit={paraLimit}
      dragging={appState?.ui?.isDragging}>
      {Media ? <Media /> : null}
    </DocSummary>
  );
}

// slider to cap how many chunks of a (often very long) section show. 0 = all.
function ParaLimit({ value, onChange }) {
  const { selectedItem } = usePuck();
  const max = (selectedItem?.props?.blocks || []).length || 1;
  const shown = value > 0 ? Math.min(value, max) : max;   // 0 => all
  return (
    <div className="lp-field-width">
      <input type="range" min="1" max={max} step="1" value={shown}
        onChange={(e) => onChange(+e.target.value >= max ? 0 : +e.target.value)} />
      <span className="lp-chip">{shown} of {max}</span>
    </div>
  );
}
const paraLimitField = {
  type: "custom",
  label: "Paragraphs shown",
  render: ({ value, onChange }) => (
    <LpField label="Paragraphs shown">
      <ParaLimit value={value || 0} onChange={onChange} />
    </LpField>
  ),
};

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
// their own label (LpField), or the panel shows bare controls
const floatTopField = {
  type: "custom",
  label: "Floated image position",
  // stacked (not a row): the label is long and would crash into the slider
  render: ({ value, onChange }) => (
    <LpField label="Floated image position">
      <FloatPosition value={value} onChange={onChange} />
    </LpField>
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
    <LpField label="Section (from the document)">
      <SectionPicker value={value} onChange={onChange} />
    </LpField>
  ),
};

const FONT = "'Public Sans', system-ui, -apple-system, sans-serif";

// content-width slider (Puck's number field is a plain input)
const widthField = {
  type: "custom",
  label: "Content width",
  render: ({ value, onChange }) => (
    <LpField label="Content width" row>
      <div className="lp-field-width">
        <input type="range" min="600" max="1200" step="20" value={value || 800}
          onChange={(e) => onChange(+e.target.value)} />
        <span className="lp-chip">{value || 800} px</span>
      </div>
    </LpField>
  ),
};

// A custom color-swatch field (Puck has no built-in color type).
const color = (label) => ({
  type: "custom",
  label,
  render: ({ value, onChange, name }) => (
    <LpField label={label} row>
      <label className="lp-field-color">
        <span className="lp-swatch" style={{ background: value || "#000000" }}>
          <input type="color" name={name} value={value || "#000000"}
            onChange={(e) => onChange(e.currentTarget.value)} />
        </span>
        <span className="lp-hex">{value || "#000000"}</span>
      </label>
    </LpField>
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

// for image blocks (Cover/Hero): insert defaults, and when the picked image
// changes, prefill alt (and caption, if the block has one) from that figure
const imageMeta = (key) => ({ props }, { changed, trigger, metadata }) => {
  if (trigger === "insert" && metadata?.blockDefaults?.[key]) {
    return { props: { ...props, ...metadata.blockDefaults[key] } };
  }
  if (changed?.src) {
    const img = (metadata?.images || []).find((im) => im.src === props.src);
    if (img) {
      const next = { ...props, alt: img.alt || props.alt || "" };
      if ("caption" in props) next.caption = img.caption || "";
      return { props: next };
    }
  }
  return { props };
};

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
    <LpField label="Image" row>
      <ImagePicker value={value} onChange={onChange} />
    </LpField>
  ),
};

// Where the download button points: the PDF bundled into the export, or a URL
// the user hosts it at. One control for the mode + (when URL) the address.
function PdfSource({ value, onChange }) {
  const v = value || { mode: "bundle", url: "" };
  const set = (patch) => onChange({ ...v, ...patch });
  return (
    <div className="lp-pdfsource">
      <label className={"lp-radio-row" + (v.mode !== "url" ? " on" : "")}>
        <input type="radio" checked={v.mode !== "url"} onChange={() => set({ mode: "bundle" })} />
        Include the PDF in my download
      </label>
      <label className={"lp-radio-row" + (v.mode === "url" ? " on" : "")}>
        <input type="radio" checked={v.mode === "url"} onChange={() => set({ mode: "url" })} />
        Use my URL
      </label>
      {v.mode === "url" ? (
        <input className="lp-pdf-url" type="url" placeholder="https://…/report.pdf"
          value={v.url || ""} onChange={(e) => set({ url: e.target.value })} />
      ) : null}
    </div>
  );
}
const pdfSourceField = {
  type: "custom",
  label: "Where's your PDF?",
  render: ({ value, onChange }) => (
    <LpField label="Where's your PDF?">
      <PdfSource value={value} onChange={onChange} />
    </LpField>
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
      headingColor: { ...color("Title") },
      accent: { ...color("Accent / links") },
      // one colour for every section heading (H2), set here not per block
      h2Color: { ...color("Section headings") },
      // font has no UI control yet (set by the theme / Copy my site), but it is
      // a registered field so Puck round-trips the prop through root.props
      font: { type: "custom", render: () => null },
      // sidebars + "show my header/footer" are edited via combined controls in
      // Page setup, not as Puck fields; null fields keep the props round-tripping
      leftSidebar: { type: "custom", render: () => null },
      rightSidebar: { type: "custom", render: () => null },
      showChrome: { type: "custom", render: () => null },
    },
    defaultProps: {
      contentWidth: 800, pageBg: "#ffffff", contentBg: "#ffffff",
      textColor: "#111111", headingColor: "#111111", accent: "#1b4965",
      h2Color: "#111111",
      font: FONT, leftSidebar: false, rightSidebar: false, showChrome: true,
    },
    render: ({ contentWidth, pageBg, contentBg, textColor, headingColor, accent,
               h2Color, font, leftSidebar, rightSidebar, showChrome, children, puck }) => {
      const { appState } = usePuck();
      // load the body font in the canvas iframe (this render runs inside it)
      React.useEffect(() => { ensureFont(primaryFamily(font), document); }, [font]);
      // fade the block toolbar in ~1s after hover (less flicker sweeping across
      // blocks); fade out immediately. Injected into the iframe — Puck's action
      // overlay lives here, not in the app document where landing.css loads.
      React.useEffect(() => {
        const id = "lp-toolbar-fade";
        if (typeof document === "undefined" || document.getElementById(id)) return;
        const s = document.createElement("style");
        s.id = id;
        s.textContent =
          '[class*="DraggableComponent-actionsOverlay"]{transition:opacity .18s ease !important;transition-delay:0s !important}'
          + '[class*="isSelected"] [class*="DraggableComponent-actionsOverlay"],'
          + '[class*="--hover"] [class*="DraggableComponent-actionsOverlay"]{transition-delay:1s !important}';
        document.head.appendChild(s);
      }, []);
      const style = themeProps({
        contentWidth,
        vars: {
          "--lp-page-bg": pageBg, "--lp-content-bg": contentBg,
          "--lp-text": textColor, "--lp-heading": headingColor, "--lp-accent": accent,
          "--lp-h2-color": h2Color,
          "--lp-font": font || FONT,
        },
      });
      // "Copy my site styles" also crops the client's page chrome; when present,
      // ghost those crops in place of the grey placeholders so the content is
      // seen inside a faded picture of the real site. Not part of the export.
      const ghost = puck?.metadata?.siteGhost || null;
      const bar = (cls, region, label) =>
        region
          ? <div className={"lp-sim-bar " + cls + " ghosted"}><img className="lp-ghost-img" src={region.src} alt="" /></div>
          : <div className={"lp-sim-bar " + cls}>{label}</div>;
      // a host sidebar only fits beside the content on a wide (desktop) host;
      // narrower hosts (laptop/mobile) stack or drop it, so hide the sim sidebars
      // there — matching how the real site would render responsively
      const hostWide = (appState?.ui?.viewports?.current?.width ?? 1200) >= 1000;
      const side = (on, region) => {
        if (!on || !hostWide) return null;
        return region
          ? <div className="lp-sim-side ghosted"><img className="lp-ghost-img" src={region.src} alt="" /></div>
          : <div className="lp-sim-side">Sidebar</div>;
      };
      const ghostSide = ghost?.sidebar;
      // simulate how the content sits inside a host page: header/footer (grey, or
      // a ghost of the real one), optional left/right sidebars; our content
      // column is centered and width-constrained
      return (
        // theme vars on the sim root so they reach BOTH the content column and
        // the full-width area behind it (the page background)
        <div className={"lp-sim" + (appState?.ui?.isDragging ? " lp-dragging" : "")} style={style}>
          {bar("lp-sim-header", showChrome !== false ? ghost?.header : null, "Site header")}
          <div className="lp-sim-mid">
            {side(leftSidebar, ghostSide?.side === "left" ? ghostSide : null)}
            <div className="lp-sim-area">
              <div className="lp-sim-content">
                <div className="lp-page">{children}</div>
              </div>
            </div>
            {side(rightSidebar, ghostSide?.side === "right" ? ghostSide : null)}
          </div>
          {bar("lp-sim-footer", showChrome !== false ? ghost?.footer : null, "Site footer")}
        </div>
      );
    },
  },
  components: {
    Title: {
      label: "Title",
      // textareas, not single-line inputs: report titles are long and were
      // truncated in the narrow field column — these wrap and show the whole line
      fields: {
        eyebrow: { type: "textarea", label: "Eyebrow (kicker)", contentEditable: true },
        title: { type: "textarea", label: "Main title", contentEditable: true },
        subtitle: { type: "textarea", label: "Subtitle / deck", contentEditable: true },
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
        paraLimit: paraLimitField,
        // drag a Cover or Hero in here to float it inside the text
        media: { type: "slot", label: "Floated image (drag a cover/hero here)", allow: ["Cover", "Hero"] },
        floatTop: floatTopField,
      },
      defaultProps: { sectionId: "", heading: "Summary", blocks: [], media: [], floatTop: 0, paraLimit: 0 },
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
      fields: { src: imageField, alt: { type: "text", label: "Alt text" } },
      defaultProps: { src: "pages/page-0001.png", alt: "Document cover" },
      resolveData: imageMeta("Cover"),
      render: ({ src, alt, puck }) => <Cover src={src} alt={alt} resolveAsset={resolver(puck)} />,
    },
    Hero: {
      label: "Hero image",
      fields: {
        src: imageField,
        caption: { type: "text", label: "Caption", contentEditable: true },
        alt: { type: "text", label: "Alt text (for screen readers)" },
      },
      defaultProps: { src: "", caption: "", alt: "Hero image" },
      resolveData: imageMeta("Hero"),
      render: ({ src, caption, alt, puck }) => (
        <Hero src={src} caption={caption} alt={alt} resolveAsset={resolver(puck)} />
      ),
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
      label: "Download Button",
      fields: {
        label: { type: "text", label: "Button text", contentEditable: true },
        pdf: pdfSourceField,
        bgColor: { ...color("Button color") },
        textColor: { ...color("Text color") },
      },
      defaultProps: {
        label: "Download the full report (PDF)", pdf: { mode: "bundle", url: "" },
        bgColor: "#1b4965", textColor: "#ffffff",
      },
      resolveData: insertDefaults("Download"),
      render: ({ label, pdf, bgColor, textColor, puck }) => (
        <Download label={label} mode={pdf?.mode} url={pdf?.url}
          bgColor={bgColor} textColor={textColor} downloadHref={dlHref(puck)} />
      ),
    },
    SecondaryCta: {
      label: "Secondary Button",
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
