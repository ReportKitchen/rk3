export const ENGINE = "pdfium";

// client-only "document" ids for the Admin views (never hit the server; the
// slug regex there rejects the colon anyway)
export const ADMIN_FEEDBACK = "admin:all-feedback";
export const ADMIN_METADATA = "admin:pdf-metadata";
export const ADMIN_PATTERNS = "admin:patterns";

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

export const getAssertions = (slug) =>
  fetch(`/api/assertions/${slug}`, { cache: "no-store" }).then(json);

// live gold-stake board (webified §1.3): every eval check green/red + nid + page
export const getStakes = (slug) =>
  fetch(`/api/stakes/${slug}`, { cache: "no-store" }).then(json);

// live per-page scoreboard (webified §1.5a): status-ring inputs for the gallery
export const getScoreboard = (slug) =>
  fetch(`/api/scoreboard/${slug}`, { cache: "no-store" }).then(json);

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

export const getPdfMetadata = () => fetch(`/api/pdf-metadata`).then(json);

// toggle a document's opt-out of auto/batch runs (still manually runnable)
export const setBatchExcluded = (slug, exclude) =>
  fetch(`/api/documents/${slug}/batch`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ exclude }),
  }).then(json);

// read-only TOC ⇔ headings reconciliation (diagnostic)
export const getTocCompare = (slug) => fetch(`/api/toc-compare/${slug}`).then(json);

// vision-QA reviewer: run it over pages → issues land in the feedback queue
export const runVisionQa = (slug, pages) =>
  fetch(`/api/qa/${slug}/run`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pages }),
  }).then(json);

// triage an issue: open | fixed | accepted | dismissed
export const setDisposition = (slug, id, disposition, note) =>
  fetch(`/api/feedback/${slug}/${id}/disposition`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ disposition, note }),
  }).then(json);

// persist a per-document embedded-fonts choice (true/false, or null = auto)
export const setDocEmbedFonts = (slug, embedFonts) =>
  fetch(`/api/doc-config/${slug}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ embedFonts }),
  }).then(json);

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

// Reading-order tool. Save the corrected order two ways:
//  - gold set: an `order` eval assertion (text prefixes, forced so a still-wrong
//    page records as a regression target);
//  - reorder op: a page-scoped <name>.ops.json entry that fixes the output.
export const saveOrderAssertion = (slug, order, note) =>
  saveAssertion(slug, { order, note, stage: "analyze" }, true);

// doc-level reorder: ALL top-level nids in the corrected reading order
export const saveReorderOp = (slug, order) =>
  postOp(slug, { nid: "reorder-doc", op: "reorder", order });

// merge: fold node `frm` into node `into` (a rejoined split paragraph)
export const saveMergeOp = (slug, into, frm) =>
  postOp(slug, { nid: `merge-${frm}`, op: "merge", into, frm });

export const saveMergeAssertion = (slug, a, b) =>
  saveAssertion(slug, { merge: [a, b] }, true);

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

// pattern-identification worktrack (patterns/out reports + review decisions)
export const getPatternsIndex = () => fetch(`/api/patterns`).then(json);
export const getPatternsDoc = (slug) => fetch(`/api/patterns/${slug}`).then(json);
export const postPatternAnalyze = (slug) =>
  fetch(`/api/patterns/${slug}/analyze`, { method: "POST" }).then(json);
export const postPatternsAnalyzeAll = () =>
  fetch(`/api/patterns/analyze-all`, { method: "POST" }).then(json);
export const postPatternDecision = (slug, d) =>
  fetch(`/api/patterns/${slug}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(d),
  }).then(json);
