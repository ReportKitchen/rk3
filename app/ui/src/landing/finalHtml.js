import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import landingCss from "./landingPage.css?raw";
import { LandingRenderer } from "./LandingRenderer.jsx";
import { assetBase, sourceUrl } from "../api.js";

// The ONE builder of the final page (Preview's iframe and the export zip both
// call it), so what the user previews and what they download can never drift.
// Renders the config with the real block components, re-applies the Wordsmith
// per-section edits, and wraps it in a full document with the SEO/social head.

const esc = (s) =>
  String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

// a structural signature per editable block — an edit is only re-applied while
// the structure it was made against is unchanged (else the fresh render wins).
// Shared by Wordsmith (capture) and this builder (re-apply).
export function editSignatures(config) {
  const m = {};
  for (const b of config?.blocks || []) {
    if (b.type === "coverBand") { m.__band__ = "coverBand"; continue; }  // skey is on the band's body div
    const sk = b.props?.skey;
    if (!sk) continue;
    m[sk] = b.type === "section"
      ? `${b.props.presentation}|${b.props.treatment || ""}|${b.props.coverLayout || ""}`
      : b.type;
  }
  return m;
}

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

export const titleOf = (config) => {
  const p = (config?.blocks || []).find((b) => b.type === "title")?.props || {};
  return p.title || p.text || ""; // text: back-compat with single-field titles
};

// the page's cover image (raw config src), wherever the layout put it — feeds og:image
export function coverSrcOf(config) {
  for (const b of config?.blocks || []) {
    if ((b.type === "cover" || b.type === "hero") && b.props?.src) return b.props.src;
    if ((b.type === "section" || b.type === "coverBand") && b.props?.cover?.src) return b.props.cover.src;
  }
  return null;
}

// apply the Wordsmith edits into a rendered DOM tree (sig must still match)
function applyEdits(root, edits, sigs) {
  Object.entries(edits || {}).forEach(([sk, rec]) => {
    if (!rec || rec.sig !== sigs[sk]) return;
    const el = root.querySelector(`[data-skey="${sk}"]`);
    if (el) el.innerHTML = rec.html;
  });
}

// Edited HTML was captured in the editor, where images/downloads resolve to OUR
// server (/output/…, /api/source/…). Re-point them at this build's context so an
// export references its bundled images/PDF, not the app.
function retargetAssets(root, { slug, resolveAsset, downloadHref }) {
  const prefix = `${assetBase(slug)}/`;
  root.querySelectorAll("img").forEach((img) => {
    const src = img.getAttribute("src") || "";
    if (src.startsWith(prefix)) img.setAttribute("src", resolveAsset(src.slice(prefix.length)));
  });
  const bundled = sourceUrl(slug);
  root.querySelectorAll(`a[href="${bundled}"]`).forEach((a) => a.setAttribute("href", downloadHref));
}

// meta description: the opening words of the page's first prose section, as the
// visitor will actually read them (post-edits)
function descriptionOf(root, limit = 160) {
  const el = root.querySelector('.lp-section[data-pres="prose"] .lp-rich, .lp-rich');
  const text = (el?.textContent || "").replace(/\s+/g, " ").trim();
  if (text.length <= limit) return text;
  const cut = text.slice(0, limit);
  return cut.slice(0, cut.lastIndexOf(" ")) + "…";
}

// CSS custom-property value from user input (a colour picker) — keep it inert
const safeCssValue = (v) => String(v || "").replace(/[^#a-zA-Z0-9(),.%\s-]/g, "");

// Build the page BODY as a DOM element: render, re-apply edits, retarget assets.
// Browser-only (edits need a DOM); both callers run client-side. Parsed with
// DOMParser because its documents are INERT — a detached createElement div
// eagerly fetches every <img>, so export-relative images/… paths would 404
// against the app origin on every zip build. `cmsSafe` compensates for the two
// ::after float-clearfixes, which inline styles can't carry — real clear divs.
export function buildPageRoot({ config, edits, slug, resolveAsset, downloadHref, cmsSafe = false }) {
  const html = renderToStaticMarkup(
    React.createElement(LandingRenderer, { config, resolveAsset, downloadHref }),
  );
  const doc = new DOMParser().parseFromString(
    `<div id="lp-root">${html}</div>`, "text/html");
  const root = doc.getElementById("lp-root");
  applyEdits(root, edits, editSignatures(config));
  retargetAssets(root, { slug, resolveAsset, downloadHref });
  if (cmsSafe) {
    root.querySelectorAll(".lp-docsum-body, .lp-section.lp-has-float").forEach((el) => {
      const clear = doc.createElement("div");
      clear.setAttribute("style", "clear:both");
      el.appendChild(clear);
    });
  }
  return root;
}

// The complete standalone document. `withShareJs` is off for the Publish
// iframe (a srcdoc page has no real URL to share) and on for the export.
// `shareImage` overrides the og:/twitter: preview image (the generated social
// graphic, already resolved for this build's context); default = the cover.
export function buildDocumentHtml({ config, edits, accent, slug, docName,
  resolveAsset, downloadHref, withShareJs = false, shareImage = null, cmsSafe = false }) {
  const root = buildPageRoot({ config, edits, slug, resolveAsset, downloadHref, cmsSafe });

  const title = titleOf(config) || docName || "";
  const description = descriptionOf(root);
  const cover = coverSrcOf(config);
  const ogImage = shareImage || (cover ? resolveAsset(cover) : null);
  // the generated graphic is always the standard 1200x630 social-card size
  const ogDims = shareImage
    ? `<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
` : "";
  const hasShare = (config?.blocks || []).some((b) => b.type === "share");

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title || docName)}</title>
${description ? `<meta name="description" content="${esc(description)}">` : ""}
<meta property="og:type" content="article">
<meta property="og:title" content="${esc(title || docName)}">
${description ? `<meta property="og:description" content="${esc(description)}">` : ""}
${ogImage ? `<meta property="og:image" content="${esc(ogImage)}">
${ogDims}<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="${esc(ogImage)}">` : ""}
<style>
${landingCss}
:root { --lp-accent: ${safeCssValue(accent) || "#1E3A5F"}; }
</style>
</head>
<body class="lp-body">
<div class="lp-page">
${root.innerHTML}
</div>
${hasShare && withShareJs ? `<script>${SHARE_JS}</script>` : ""}
</body>
</html>
`;
}

// The CMS-safe variant: the same document with every rule folded into inline
// style attributes (server does the cascade via css-inline; custom properties
// are resolved to concrete values first, so sanitizers can't break them).
export async function buildInlineDocumentHtml(opts) {
  const html = buildDocumentHtml({ ...opts, cmsSafe: true });
  const res = await fetch("/api/inline-css", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ html, vars: { "--lp-accent": opts.accent || "" } }),
  });
  if (!res.ok) throw new Error(`inline-css failed: ${res.status}`);
  return (await res.json()).html;
}

// A paste-into-a-CMS fragment from the inlined document: just the .lp-page div,
// carrying the body's inherited styles (font/colour) on itself — minus
// min-height, which must not force a viewport-tall block inside someone's page.
export function extractCmsFragment(inlinedHtml) {
  const doc = new DOMParser().parseFromString(inlinedHtml, "text/html");
  const page = doc.querySelector(".lp-page");
  if (!page) return "";
  const merged = `${doc.body.getAttribute("style") || ""};${page.getAttribute("style") || ""}`
    .split(";")
    .map((d) => d.trim())
    .filter((d) => d && !/^min-height\s*:/i.test(d) && !/^margin\s*:/i.test(d));
  page.setAttribute("style", merged.join("; "));
  return page.outerHTML;
}
