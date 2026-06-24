export const ENGINE = "pdfium";

async function json(res) {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const getDocuments = () => fetch("/api/documents").then(json);

export const startConvert = (slug, force = false) =>
  fetch(`/api/convert/${slug}${force ? "?force=true" : ""}`, { method: "POST" }).then(json);

export const getFeedback = (slug) => fetch(`/api/feedback/${slug}`).then(json);

export const postFeedback = (slug, entry) =>
  fetch(`/api/feedback/${slug}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(entry),
  }).then(json);

export const deleteFeedback = (slug, id) =>
  fetch(`/api/feedback/${slug}/${id}`, { method: "DELETE" }).then(json);

export const clearFeedback = (slug, id) =>
  fetch(`/api/feedback/${slug}/${id}/clear`, { method: "POST" }).then(json);

export const emptyTrash = (slug) =>
  fetch(`/api/feedback/${slug}/empty-trash`, { method: "POST" }).then(json);

export const getOps = (slug) => fetch(`/api/ops/${slug}`).then(json);

export const postOp = (slug, op) =>
  fetch(`/api/ops/${slug}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(op),
  }).then(json);

export const deleteOp = (slug, opKind, nid) =>
  fetch(`/api/ops/${slug}/${opKind}/${nid}`, { method: "DELETE" }).then(json);

export const getIr = (slug) =>
  fetch(`/output/${ENGINE}/${slug}/ir.json`).then(json);

export const docUrl = (slug) => `/output/${ENGINE}/${slug}/index.html`;

// landing page maker
export const assetBase = (slug) => `/output/${ENGINE}/${slug}`;
export const sourceUrl = (slug) => `/api/source/${slug}`;

export const getLanding = (slug) => fetch(`/api/landing/${slug}`).then(json);
export const getLandingTheme = (slug) => fetch(`/api/landing-theme/${slug}`).then(json);
export const getLandingTemplate = (slug, archetype) =>
  fetch(`/api/landing/${slug}/template/${archetype}`).then(json);
export const getArchetypes = () => fetch(`/api/landing-archetypes`).then(json);

export const postLanding = (slug, config) =>
  fetch(`/api/landing/${slug}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  }).then(json);

export const postLandingTheme = (slug, theme) =>
  fetch(`/api/landing-theme/${slug}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(theme),
  }).then(json);

export const pageUrl = (slug, p) =>
  `/output/${ENGINE}/${slug}/pages/page-${String(p).padStart(4, "0")}.png`;
