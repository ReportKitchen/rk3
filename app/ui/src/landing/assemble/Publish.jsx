import React, { useEffect, useMemo, useState } from "react";
import { t } from "../../content.js";
import { assetBase, sourceUrl, getSocialPost } from "../../api.js";
import { guard } from "../../errorBus.js";
import { buildDocumentHtml } from "../finalHtml.js";
import { exportZip } from "../exportZip.js";
import { buildSectionConfig, SOCIAL_MODE } from "./model.js";
import WhiskLoader from "./WhiskLoader.jsx";
import { Icon } from "./icons.jsx";

// Publish: the finished page, exactly as a visitor gets it — the same document
// the export writes, rendered in an isolated iframe (its own head/CSS/fonts, no
// app chrome bleeding in). The right rail carries the social graphic (the PDF
// cover reformatted into a 1200x630 card, warmed in the background on open) and
// the download card. The share-image toggle decides which image the page embeds
// for og:/twitter: link previews.
export default function Publish({ slug, docName, title, coverAsset, cover, accent,
  sections, cta, ai, edits, noai, shareImage, onShareImage, onBack }) {
  const [device, setDevice] = useState("desktop");
  const [zipping, setZipping] = useState(false);
  const [wide, setWide] = useState(false);      // expanded social graphic rail
  const [social, setSocial] = useState(null);   // openai-reformat status {status,url}

  // watch the social graphic: poll while it's still cooking (the warm-up fired
  // back when Assemble loaded the sections, so usually it's ready by now)
  useEffect(() => {
    if (noai) return undefined;
    let alive = true;
    let timer = null;
    const tick = () => {
      getSocialPost(slug)
        .then((st) => {
          if (!alive) return;
          const m = st?.modes?.[SOCIAL_MODE] || null;
          setSocial(m);
          if (m && (m.status === "empty" || m.status === "in_progress")) {
            timer = setTimeout(tick, 2000);
          }
        })
        .catch(guard("publish: social graphic status", null));
    };
    tick();
    return () => { alive = false; clearTimeout(timer); };
  }, [slug, noai]);

  const config = useMemo(() => buildSectionConfig({
    title,
    cover: coverAsset ? { src: coverAsset.src, alt: coverAsset.alt, layout: cover } : null,
    sections, cta, ai,
  }), [title, coverAsset, cover, sections, cta, ai]);

  const socialReady = social?.status === "ready" && !!social.url;
  const socialCooking = !noai && !!social && !socialReady && social.status !== "failed";
  const useSocial = shareImage === "social" && socialReady;

  // srcdoc inherits our base URL, so server paths (/output/…, /api/…) resolve —
  // the download button really downloads. Share buttons stay inert here: a
  // srcdoc page has no address to share (the export wires them for real).
  const srcdoc = useMemo(() => buildDocumentHtml({
    config, edits, accent, slug, docName,
    resolveAsset: (s) => (s?.startsWith("http") ? s : `${assetBase(slug)}/${s}`),
    downloadHref: sourceUrl(slug),
    shareImage: useSocial ? social.url : null,
  }), [config, edits, accent, slug, docName, useSocial, social]);

  const bundled = !!cta?.download && !cta?.downloadUrl;

  const download = () => {
    setZipping(true);
    exportZip(slug, { config, edits, accent, docName,
      socialUrl: useSocial ? social.url : null })
      .catch(guard("publish: export zip", null))
      .finally(() => setZipping(false));
  };

  return (
    <div className="asm-pub">
      <div className="asm-ws-bar">
        <button type="button" className="asm-ws-back" onClick={onBack}>
          <Icon name="chevron-left" size={14} />{t("lpm.publish.back_to_wordsmith")}
        </button>
        <span className="asm-ws-back-hint">{t("lpm.publish.back_hint")}</span>
        <div className="asm-pub-devices">
          {["desktop", "mobile"].map((d) => (
            <button
              key={d} type="button"
              className={"asm-pub-device" + (device === d ? " is-on" : "")}
              onClick={() => setDevice(d)}
            >
              <Icon name={d === "desktop" ? "monitor" : "smartphone"} size={14} />
              {t(`lpm.publish.device.${d}`)}
            </button>
          ))}
        </div>
      </div>

      <div className="asm-pub-canvas">
        <div className="asm-pub-stage">
          <div className={"asm-pub-frame" + (device === "mobile" ? " is-mobile" : "")}>
            <iframe className="asm-pub-iframe" title={t("lpm.publish.frame_title")} srcDoc={srcdoc} />
          </div>
        </div>

        <aside className={"asm-pub-rail" + (wide ? " is-wide" : "")}>
          {(socialReady || socialCooking) && (
            <div className="asm-pub-card asm-pub-social">
              <div className="asm-pub-card-head">
                <span className="asm-pub-card-title">{t("lpm.publish.social_title")}</span>
                {socialReady && (
                  <button type="button" className="asm-pub-expand" onClick={() => setWide((w) => !w)}>
                    <Icon name={wide ? "minimize-2" : "maximize-2"} size={13} />
                    {wide ? t("lpm.publish.social_shrink") : t("lpm.publish.social_expand")}
                  </button>
                )}
              </div>
              {socialReady ? (
                <img className="asm-pub-social-img" src={social.url} alt={t("lpm.publish.social_title")} />
              ) : (
                <div className="asm-pub-social-cooking">
                  <WhiskLoader size={84} />
                  <p>{t("lpm.publish.social_generating")}</p>
                </div>
              )}
              <p className="asm-pub-card-body">{t("lpm.publish.social_blurb")}</p>
              <div className="asm-pub-share">
                <span className="asm-pub-share-label">{t("lpm.publish.share_image_label")}</span>
                <div className="asm-pub-seg">
                  <button
                    type="button"
                    className={"asm-pub-seg-opt" + (shareImage !== "social" ? " is-on" : "")}
                    onClick={() => onShareImage("cover")}
                  >
                    {t("lpm.publish.share_image_cover")}
                  </button>
                  <button
                    type="button"
                    className={"asm-pub-seg-opt" + (shareImage === "social" ? " is-on" : "")}
                    disabled={!socialReady}
                    onClick={() => onShareImage("social")}
                  >
                    {t("lpm.publish.share_image_social")}
                  </button>
                </div>
                <p className="asm-pub-share-hint">{t("lpm.publish.share_image_hint")}</p>
              </div>
            </div>
          )}

          <div className="asm-pub-card">
            <div className="asm-pub-card-title">{t("lpm.publish.publish_title")}</div>
            <p className="asm-pub-card-body">
              {bundled ? t("lpm.publish.zip_bundled") : t("lpm.publish.zip_no_pdf")}
            </p>
            <button type="button" className="asm-pub-dl" onClick={download} disabled={zipping}>
              <Icon name="download" size={15} />
              {zipping ? t("lpm.publish.download_building") : t("lpm.publish.download_zip")}
            </button>
            <p className="asm-pub-card-hint">{t("lpm.publish.publish_hint")}</p>
          </div>
        </aside>
      </div>
    </div>
  );
}
