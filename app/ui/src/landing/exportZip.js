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

// Wires the share buttons at click time from the LIVE page URL, so a hosted
// copy shares its own address wherever it lands. Copy link / Instagram (no web
// share intent) copy the URL to the clipboard and flash "Copied!".
const SHARE_JS = `(function(){
  var b=function(u,t){return{
    linkedin:"https://www.linkedin.com/sharing/share-offsite/?url="+u,
    x:"https://twitter.com/intent/tweet?url="+u+"&text="+t,
    bluesky:"https://bsky.app/intent/compose?text="+t+"%20"+u,
    facebook:"https://www.facebook.com/sharer/sharer.php?u="+u
  };};
  Array.prototype.forEach.call(document.querySelectorAll("[data-share]"),function(a){
    a.addEventListener("click",function(e){
      e.preventDefault();
      var u=encodeURIComponent(location.href),t=encodeURIComponent(document.title||"");
      var net=a.getAttribute("data-share");
      if(net==="link"||net==="instagram"){
        if(navigator.clipboard)navigator.clipboard.writeText(location.href);
        a.classList.add("lp-share-copied");
        setTimeout(function(){a.classList.remove("lp-share-copied");},1400);
        return;
      }
      var url=b(u,t)[net];
      if(url)window.open(url,"_blank","noopener,noreferrer,width=600,height=540");
    });
  });
})();`;

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

  const hasShare = config.blocks.some((b) => b.type === "share");

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
${hasShare ? `<script>${SHARE_JS}</script>` : ""}
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
