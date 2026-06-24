// Adapter: our landing.json (source of truth) <-> Puck's Data shape. Keeping
// our own format means the editor stays swappable and the export/Python side
// never has to know about Puck.
import { TYPE_TO_PUCK, PUCK_TO_TYPE } from "./puckConfig.jsx";

const FONT = "'Public Sans', system-ui, -apple-system, sans-serif";

// ---- theme <-> Puck root props ----
function themeToRoot(theme) {
  const v = theme?.vars || {};
  const pv = theme?.preview || {};
  return {
    contentWidth: theme?.contentWidth || 800,
    pageBg: v["--lp-page-bg"] || "#ffffff",
    contentBg: v["--lp-content-bg"] || "#ffffff",
    textColor: v["--lp-text"] || "#111111",
    headingColor: v["--lp-heading"] || "#111111",
    accent: v["--lp-accent"] || "#1b4965",
    leftSidebar: !!pv.leftSidebar,
    rightSidebar: !!pv.rightSidebar,
  };
}

function rootToTheme(p = {}) {
  return {
    version: 1,
    source: "system",
    contentWidth: p.contentWidth || 800,
    vars: {
      "--lp-page-bg": p.pageBg || "#ffffff",
      "--lp-content-bg": p.contentBg || "#ffffff",
      "--lp-text": p.textColor || "#111111",
      "--lp-heading": p.headingColor || "#111111",
      "--lp-accent": p.accent || "#1b4965",
      "--lp-font": FONT,
    },
    // preview-only page context (sidebars); never used by the export
    preview: { leftSidebar: !!p.leftSidebar, rightSidebar: !!p.rightSidebar },
  };
}

// ---- per-block prop shape differences (Puck array fields store objects) ----
function propsToPuck(type, props) {
  if (type === "highlights") {
    return { ...props, items: (props.items || []).map((v) => ({ value: v })) };
  }
  return { ...props };
}

function propsFromPuck(type, props) {
  const { id, ...rest } = props;
  if (type === "highlights") {
    return { ...rest, items: (rest.items || []).map((i) => (typeof i === "string" ? i : i.value)) };
  }
  return rest;
}

// ---- public API ----
export function toPuck(config, theme) {
  return {
    root: { props: themeToRoot(theme) },
    content: (config?.blocks || []).map((b) => ({
      type: TYPE_TO_PUCK[b.type],
      props: { id: b.id, ...propsToPuck(b.type, b.props || {}) },
    })).filter((c) => c.type),
    zones: {},
  };
}

export function fromPuck(data) {
  const config = {
    version: 1,
    template: "default",
    blocks: (data?.content || []).map((item) => {
      const type = PUCK_TO_TYPE[item.type];
      if (!type) return null;
      return { id: item.props?.id, type, props: propsFromPuck(type, item.props || {}) };
    }).filter(Boolean),
  };
  const theme = rootToTheme(data?.root?.props);
  return { config, theme };
}
