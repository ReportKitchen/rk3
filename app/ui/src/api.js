export const ENGINE = "pdfium";

// client-only "document" id for the Admin → All Feedback view (never hits the
// server; the slug regex there rejects the colon anyway)
export const ADMIN_FEEDBACK = "admin:all-feedback";

async function json(res) {
  if (!res.ok) {
    // pull the server's body (FastAPI {detail}, or a raw traceback) into the
    // error so the UI can show *why*, not just the status code
    let body = "";
    try { body = await res.text(); } catch { /* ignore */ }
    let detail = body;
    try { detail = JSON.parse(body)?.detail ?? body; } catch { /* not json */ }
    const err = new Error(`${res.status} ${res.statusText} — ${res.url}`);
    err.detail = typeof detail === "string" ? detail : JSON.stringify(detail, null, 2);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const getDocuments = () => fetch("/api/documents").then(json);

export const startConvert = (slug, force = false) =>
  fetch(`/api/convert/${slug}${force ? "?force=true" : ""}`, { method: "POST" }).then(json);

export const getBuildStatus = (slug) =>
  fetch(`/api/build-status/${slug}`, { cache: "no-store" }).then(json);

export const getSnapshot = (slug, nid) =>
  fetch(`/api/assertions/${slug}/snapshot?nid=${encodeURIComponent(nid)}`,
        { cache: "no-store" }).then(json);

export const validateAssertion = (slug, check) =>
  fetch(`/api/assertions/${slug}/validate`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(check),
  }).then(json);

export const saveAssertion = (slug, check, force = false) =>
  fetch(`/api/assertions/${slug}${force ? "?force=true" : ""}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(check),
  }).then(json);

export const getFeedback = (slug) => fetch(`/api/feedback/${slug}`).then(json);

export const getAllFeedback = () => fetch(`/api/feedback`).then(json);

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
export const getBlockDefaults = (slug) =>
  fetch(`/api/landing/${slug}/block-defaults`).then(json);
export const getArchetypes = () => fetch(`/api/landing-archetypes`).then(json);
export const getAiSummary = (slug, style, length) =>
  fetch(`/api/landing/${slug}/ai-summary?style=${style}&length=${length}`)
    .then(json).then((d) => d.text);
export const getAiMode = () => fetch(`/api/ai-mode`).then(json).then((d) => d.mode);

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
