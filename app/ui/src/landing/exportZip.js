import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import JSZip from "jszip";
import { themeCssVars } from "./css.js";
import { fontHrefForTheme } from "./fonts.js";
import landingCss from "./landingPage.css?raw";
import { LandingRenderer } from "./LandingRenderer.jsx";
import { assetBase, sourceUrl } from "../api.js";

const esc = (s) =>
  (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const basename = (src) => src.split("/").pop();

const titleOf = (config) => {
  const p = config.blocks.find((b) => b.type === "title")?.props || {};
  return p.title || p.text || ""; // text: back-compat with single-field titles
};

// Build a self-contained zip: index.html + images/ (relative paths) + the PDF.
// No data-URIs, no references back to our server.
export async function exportZip(slug, config, theme, docName) {
  const zip = new JSZip();

  // bundle the PDF only when a download button actually points at the bundled
  // file (not when the user hosts it at their own URL)
  const hasBundled = config.blocks.some(
    (b) => b.type === "download" && b.props?.pdf?.mode !== "url");
  const pdfHref = hasBundled ? `./${encodeURIComponent(docName)}` : "#";

  const html = renderToStaticMarkup(
    React.createElement(LandingRenderer, {
      config,
      resolveAsset: (src) => `images/${basename(src)}`,
      downloadHref: pdfHref,
    }),
  );

  const doc = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(titleOf(config) || docName)}</title>
<link rel="stylesheet" href="${fontHrefForTheme(theme)}">
<style>
${landingCss}
${themeCssVars(theme)}
</style>
</head>
<body class="lp-body">
<div class="lp-page">
${html}
</div>
</body>
</html>
`;
  zip.file("index.html", doc);

  // images used by enabled image blocks (incl. ones nested in a media slot)
  const imgFolder = zip.folder("images");
  const used = new Set();
  const collect = (blocks) => {
    for (const b of blocks || []) {
      if ((b.type === "cover" || b.type === "hero") && b.props?.src) used.add(b.props.src);
      if (Array.isArray(b.props?.media)) collect(b.props.media);
    }
  };
  collect(config.blocks);
  for (const src of used) {
    const res = await fetch(`${assetBase(slug)}/${src}`);
    if (res.ok) imgFolder.file(basename(src), await res.blob());
  }

  // bundle the source PDF so the Download button resolves locally
  if (hasBundled) {
    const res = await fetch(sourceUrl(slug));
    if (res.ok) zip.file(docName, await res.blob());
  }

  const blob = await zip.generateAsync({ type: "blob" });
  const base = docName.replace(/\.pdf$/i, "").replace(/[^a-z0-9]+/gi, "-").toLowerCase();
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
