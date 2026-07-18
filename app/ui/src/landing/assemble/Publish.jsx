import React, { useEffect, useMemo, useRef, useState } from "react";
import { t } from "../../content.js";
import { assetBase, sourceUrl, getSocialPost } from "../../api.js";
import { guard } from "../../errorBus.js";
import { buildInlineDocumentHtml, extractCmsFragment, titleOf } from "../finalHtml.js";
import { exportZip, triggerDownload } from "../exportZip.js";
import { buildSocialDocx } from "../socialDocx.js";
import { buildSectionConfig, SOCIAL_MODE } from "./model.js";
import WhiskLoader from "./WhiskLoader.jsx";
import { Icon } from "./icons.jsx";

// Publish: the dedicated export surface. Left column = the promotion kit (the
// social graphic warmed in the background on open, the share-image choice, the
// four weekly posts). Right column = getting the page out: an inline-styled
// HTML fragment to paste into a CMS (some CMSes strip <style> blocks — the
// email-HTML problem), and the full-page ZIP with an embedded ⇄ inline-styles
// choice. The page itself is previewed on the step before.
export default function Publish({ slug, docName, title, coverAsset, cover, accent,
  sections, cta, ai, edits, noai, socialPosts, postsPending, shareImage, onShareImage,
  socialDoc, onSocialDoc, dlStyle, onDlStyle, onBack }) {
  const [zipping, setZipping] = useState(false);
  const [social, setSocial] = useState(null);     // openai-reformat status {status,url}
  const [copied, setCopied] = useState(null);     // "post-N" | "cms"
  const [fragment, setFragment] = useState(null); // the CMS paste HTML (null = building)
  const [fragErr, setFragErr] = useState(false);
  const copyTimer = useRef(null);

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
  const posts = socialPosts || [];

  // build the CMS fragment (inline styles, absolute URLs — it leaves our app)
  useEffect(() => {
    let alive = true;
    setFragment(null);
    setFragErr(false);
    buildInlineDocumentHtml({
      config, edits, accent, slug, docName,
      resolveAsset: (s) => (s?.startsWith("http") ? s : new URL(`${assetBase(slug)}/${s}`, window.location.origin).href),
      downloadHref: new URL(sourceUrl(slug), window.location.origin).href,
    })
      .then((html) => { if (alive) setFragment(extractCmsFragment(html)); })
      .catch((e) => { if (alive) { setFragErr(true); guard("publish: cms html", null)(e); } });
    return () => { alive = false; };
  }, [config, edits, accent, slug, docName]);

  const flash = (key) => {
    setCopied(key);
    clearTimeout(copyTimer.current);
    copyTimer.current = setTimeout(() => setCopied(null), 1600);
  };
  const copyPost = (text, i) => { navigator.clipboard?.writeText(text); flash(`post-${i}`); };
  const copyCms = () => {
    if (!fragment) return;
    navigator.clipboard?.writeText(fragment);
    flash("cms");
  };

  // the cover image as a file — the CMS fragment ships without images, so the
  // user downloads the cover here and re-inserts it with their CMS's image tool
  const downloadCover = () => {
    const src = coverAsset?.src;
    if (!src) return;
    fetch(`${assetBase(slug)}/${src}`)
      .then((r) => (r.ok ? r.blob() : Promise.reject(new Error(`cover fetch ${r.status}`))))
      .then((blob) => triggerDownload(blob, `report-cover.${(src.split(".").pop() || "png").toLowerCase()}`))
      .catch(guard("publish: cover download", null));
  };

  const download = () => {
    setZipping(true);
    const docx = socialDoc && posts.length
      ? buildSocialDocx({
        title: t("lpm.publish.docx_title", { title: titleOf(config) || docName }),
        intro: t("lpm.publish.docx_intro"),
        weekLabel: (n) => t("lpm.publish.posts_week", { n }),
        posts,
      })
      : Promise.resolve(null);
    docx
      .then((blob) => exportZip(slug, { config, edits, accent, docName,
        socialUrl: useSocial ? social.url : null, socialDocx: blob,
        inlineCss: dlStyle === "inline" }))
      .catch(guard("publish: export zip", null))
      .finally(() => setZipping(false));
  };

  return (
    <div className="asm-pub">
      <div className="asm-ws-bar">
        <button type="button" className="asm-ws-back" onClick={onBack}>
          <Icon name="chevron-left" size={14} />{t("lpm.publish.back_to_preview")}
        </button>
        <span className="asm-ws-back-hint">{t("lpm.publish.back_hint")}</span>
      </div>

      <div className="asm-pubx">
        <div className="asm-pubx-cols">
          <div className="asm-pubx-col">
            {(socialReady || socialCooking) && (
              <div className="asm-pub-card">
                <span className="asm-pub-card-title">{t("lpm.publish.social_title")}</span>
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

            {(posts.length > 0 || postsPending) && (
              <div className="asm-pub-card">
                <span className="asm-pub-card-title">{t("lpm.publish.posts_title")}</span>
                <p className="asm-pub-card-body">{t("lpm.publish.posts_blurb")}</p>
                {posts.length === 0 ? (
                  <div className="asm-pub-social-cooking">
                    <WhiskLoader size={84} />
                    <p>{t("lpm.publish.posts_generating")}</p>
                  </div>
                ) : (
                  <>
                    <div className="asm-pub-posts">
                      {posts.map((p, i) => (
                        <div key={i} className="asm-pub-post">
                          <div className="asm-pub-post-head">
                            <span className="asm-pub-post-week">{t("lpm.publish.posts_week", { n: i + 1 })}</span>
                            <button type="button" className="asm-pub-copy" onClick={() => copyPost(p, i)}>
                              <Icon name={copied === `post-${i}` ? "check" : "copy"} size={12} />
                              {copied === `post-${i}` ? t("lpm.publish.posts_copied") : t("lpm.publish.posts_copy")}
                            </button>
                          </div>
                          <p className="asm-pub-post-text">{p}</p>
                        </div>
                      ))}
                    </div>
                    <label className="asm-pub-docopt">
                      <input
                        type="checkbox" checked={!!socialDoc}
                        onChange={(e) => onSocialDoc(e.target.checked)}
                      />
                      {t("lpm.publish.posts_include_doc")}
                    </label>
                    <p className="asm-pub-card-hint">{t("lpm.publish.posts_cadence_hint")}</p>
                  </>
                )}
              </div>
            )}
          </div>

          <div className="asm-pubx-col">
            <div className="asm-pub-card">
              <span className="asm-pub-card-title">{t("lpm.publish.cms_title")}</span>
              <p className="asm-pub-card-body">{t("lpm.publish.cms_blurb")}</p>
              {fragErr ? (
                <p className="asm-pub-card-hint">{t("lpm.publish.cms_failed")}</p>
              ) : (
                <>
                  <textarea
                    className="asm-pub-cms-box" readOnly
                    value={fragment || t("lpm.publish.cms_building")}
                    onFocus={(e) => fragment && e.target.select()}
                  />
                  <ol className="asm-pub-cms-steps">
                    <li>{t("lpm.publish.cms_step1")}</li>
                    {coverAsset?.src ? <li>{t("lpm.publish.cms_step2")}</li> : null}
                    <li>{t("lpm.publish.cms_step3")}</li>
                    <li>{t("lpm.publish.cms_step4")}</li>
                  </ol>
                  <div className="asm-pub-btnrow">
                    <button type="button" className="asm-pub-dl" disabled={!fragment} onClick={copyCms}>
                      <Icon name={copied === "cms" ? "check" : "copy"} size={14} />
                      {copied === "cms" ? t("lpm.publish.cms_copied") : t("lpm.publish.cms_copy")}
                    </button>
                    {coverAsset?.src ? (
                      <button type="button" className="asm-pub-dl asm-pub-dl-ghost" onClick={downloadCover}>
                        <Icon name="download" size={14} />
                        {t("lpm.publish.cms_cover_download")}
                      </button>
                    ) : null}
                  </div>
                </>
              )}
            </div>

            <div className="asm-pub-card">
              <span className="asm-pub-card-title">{t("lpm.publish.dl_title")}</span>
              <p className="asm-pub-card-body">
                {bundledText(cta)}
              </p>
              <div className="asm-pub-share" style={{ borderTop: 0, paddingTop: 0 }}>
                <span className="asm-pub-share-label">{t("lpm.publish.dl_style_label")}</span>
                <div className="asm-pub-seg">
                  <button
                    type="button"
                    className={"asm-pub-seg-opt" + (dlStyle !== "inline" ? " is-on" : "")}
                    onClick={() => onDlStyle("embedded")}
                  >
                    {t("lpm.publish.dl_embedded")}
                  </button>
                  <button
                    type="button"
                    className={"asm-pub-seg-opt" + (dlStyle === "inline" ? " is-on" : "")}
                    onClick={() => onDlStyle("inline")}
                  >
                    {t("lpm.publish.dl_inline")}
                  </button>
                </div>
                <p className="asm-pub-share-hint">
                  {dlStyle === "inline" ? t("lpm.publish.dl_inline_hint") : t("lpm.publish.dl_embedded_hint")}
                </p>
              </div>
              <button type="button" className="asm-pub-dl" onClick={download} disabled={zipping} style={{ marginTop: 12 }}>
                <Icon name="download" size={15} />
                {zipping ? t("lpm.publish.download_building") : t("lpm.publish.download_zip")}
              </button>
              <p className="asm-pub-card-hint">{t("lpm.publish.publish_hint")}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const bundledText = (cta) =>
  (cta?.download && !cta?.downloadUrl)
    ? t("lpm.publish.zip_bundled") : t("lpm.publish.zip_no_pdf");
