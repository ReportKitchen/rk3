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

export const getIr = (slug) =>
  fetch(`/output/${ENGINE}/${slug}/ir.json`).then(json);

export const docUrl = (slug) => `/output/${ENGINE}/${slug}/index.html`;

export const pageUrl = (slug, p) =>
  `/output/${ENGINE}/${slug}/pages/page-${String(p).padStart(4, "0")}.png`;
