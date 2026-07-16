// Adapter: our landing.json (source of truth) <-> Puck's Data shape. Keeping
// our own format means the editor stays swappable and the export/Python side
// never has to know about Puck.
import { TYPE_TO_PUCK, PUCK_TO_TYPE, SLOT_PROPS } from "./puckConfig.jsx";

const FONT = "'Public Sans', system-ui, -apple-system, sans-serif";

// ---- theme <-> Puck root props ----
export function themeToRoot(theme) {
  const v = theme?.vars || {};
  const pv = theme?.preview || {};
  return {
    contentWidth: theme?.contentWidth || 800,
    pageBg: v["--lp-page-bg"] || "#ffffff",
    contentBg: v["--lp-content-bg"] || "#ffffff",
    textColor: v["--lp-text"] || "#111111",
    headingColor: v["--lp-heading"] || "#111111",
    accent: v["--lp-accent"] || "#1b4965",
    font: v["--lp-font"] || FONT,
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
      "--lp-font": p.font || FONT,
    },
    // preview-only page context (sidebars); never used by the export
    preview: { leftSidebar: !!p.leftSidebar, rightSidebar: !!p.rightSidebar },
  };
}

// ---- per-block prop shape differences (Puck array fields store objects) ----
export function propsToPuck(type, props) {
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

// ---- block <-> Puck content item (recursing into slot props) ----
function blockToPuck(b) {
  const puckType = TYPE_TO_PUCK[b.type];
  if (!puckType) return null;
  const slots = SLOT_PROPS[puckType] || [];
  const flat = {}, slotData = {};
  for (const [k, v] of Object.entries(b.props || {})) {
    if (slots.includes(k)) slotData[k] = (v || []).map(blockToPuck).filter(Boolean);
    else flat[k] = v;
  }
  return { type: puckType, props: { id: b.id, ...propsToPuck(b.type, flat), ...slotData } };
}

function blockFromPuck(item) {
  const type = PUCK_TO_TYPE[item.type];
  if (!type) return null;
  const slots = SLOT_PROPS[item.type] || [];
  const flat = {}, slotData = {};
  for (const [k, v] of Object.entries(item.props || {})) {
    if (slots.includes(k)) slotData[k] = (v || []).map(blockFromPuck).filter(Boolean);
    else flat[k] = v;
  }
  return { id: item.props?.id, type, props: { ...propsFromPuck(type, flat), ...slotData } };
}

// ---- public API ----
export function toPuck(config, theme) {
  return {
    root: { props: themeToRoot(theme) },
    content: (config?.blocks || []).map(blockToPuck).filter(Boolean),
    zones: {},
  };
}

// `template` is editor state, not Puck data — callers that persist the config
// pass the current archetype; callers that only need blocks/theme omit it
export function fromPuck(data, template = "") {
  const config = {
    version: 1,
    template,
    blocks: (data?.content || []).map(blockFromPuck).filter(Boolean),
  };
  const theme = rootToTheme(data?.root?.props);
  return { config, theme };
}
