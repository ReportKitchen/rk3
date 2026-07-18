import JSZip from "jszip";
import { buildDocumentHtml, titleOf } from "./finalHtml.js";
import { assetBase, sourceUrl } from "../api.js";

const basename = (src) => src.split("/").pop();

// every download button on the page, wherever the layout put it: the CTA row,
// a boxed cover's embedded button, the cover band's button
function collectDownloads(config) {
  const out = [];
  for (const b of config?.blocks || []) {
    if (b.type === "download" && b.props) out.push(b.props);
    if (b.type === "coverBand" && b.props?.download) out.push(b.props.download);
    if (b.type === "section" && b.props?.coverDownload) out.push(b.props.coverDownload);
  }
  return out;
}

// every image the page shows: bare cover/hero blocks (legacy), a cover floated
// into a section, the cover band's cover, and legacy media slots
function collectImages(blocks, used = new Set()) {
  for (const b of blocks || []) {
    if ((b.type === "cover" || b.type === "hero") && b.props?.src) used.add(b.props.src);
    if ((b.type === "section" || b.type === "coverBand") && b.props?.cover?.src) used.add(b.props.cover.src);
    if (Array.isArray(b.props?.media)) collectImages(b.props.media, used);
  }
  return used;
}

// Build a self-contained zip: index.html + images/ (relative paths) + the PDF.
// No data-URIs, no references back to our server. Renders through the same
// finalHtml builder as the Publish preview, so the download matches what was
// shown. `socialUrl` (the generated social graphic, when the user picked it as
// the share image) is bundled and becomes the og:/twitter: preview image.
export async function exportZip(slug, { config, edits, accent, docName, socialUrl }) {
  const zip = new JSZip();

  // bundle the PDF only when a download button actually points at the bundled
  // file (not when the user hosts it at their own URL)
  const hasBundled = collectDownloads(config).some((d) => d.mode !== "url");
  const pdfHref = hasBundled ? `./${encodeURIComponent(docName)}` : "#";

  // the graphic must actually fetch before the head may reference it
  const imgFolder = zip.folder("images");
  let socialFile = null;
  if (socialUrl) {
    const res = await fetch(socialUrl);
    if (res.ok) {
      socialFile = "social-card.png";
      imgFolder.file(socialFile, await res.blob());
    }
  }

  const html = buildDocumentHtml({
    config, edits, accent, slug, docName,
    resolveAsset: (src) => `images/${basename(src)}`,
    downloadHref: pdfHref,
    withShareJs: true,
    shareImage: socialFile ? `images/${socialFile}` : null,
  });
  zip.file("index.html", html);

  for (const src of collectImages(config?.blocks)) {
    const res = await fetch(`${assetBase(slug)}/${src}`);
    if (res.ok) imgFolder.file(basename(src), await res.blob());
  }

  // bundle the source PDF so the Download button resolves locally
  if (hasBundled) {
    const res = await fetch(sourceUrl(slug));
    if (res.ok) zip.file(docName, await res.blob());
  }

  const blob = await zip.generateAsync({ type: "blob" });
  const base = (titleOf(config) || docName).replace(/\.pdf$/i, "")
    .replace(/[^a-z0-9]+/gi, "-").replace(/^-+|-+$/g, "").toLowerCase() || "landing";
  triggerDownload(blob, `${base}-landing.zip`);
}

function triggerDownload(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
