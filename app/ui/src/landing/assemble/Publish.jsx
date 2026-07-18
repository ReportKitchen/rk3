import React, { useEffect, useMemo, useRef, useState } from "react";
import { t } from "../../content.js";
import { assetBase, sourceUrl, getSocialPost } from "../../api.js";
import { guard } from "../../errorBus.js";
import { buildDocumentHtml, titleOf } from "../finalHtml.js";
import { exportZip } from "../exportZip.js";
import { buildSocialDocx } from "../socialDocx.js";
import { buildSectionConfig, SOCIAL_MODE } from "./model.js";
import WhiskLoader from "./WhiskLoader.jsx";
import { Icon } from "./icons.jsx";

// Publish: the finished page, exactly as a visitor gets it — the same document
// the export writes, rendered in an isolated iframe (its own head/CSS/fonts, no
// app chrome bleeding in). The right rail is the promotion kit: the social
// graphic (the PDF cover reformatted to a 1200x630 card, warmed in the
// background on open), the four suggested social posts, and the download card.
// The handle between page and rail is a focus toggle: wide mode grows the rail
// and ZOOMS the page (scales it — same desktop layout, smaller), never reflows it.
export default function Publish({ slug, docName, title, coverAsset, cover, accent,
  sections, cta, ai, edits, noai, socialPosts, shareImage, onShareImage,
  socialDoc, onSocialDoc, onBack }) {
  const [device, setDevice] = useState("desktop");
  const [zipping, setZipping] = useState(false);
  const [wide, setWide] = useState(false);      // focus the cards (rail wide, page zoomed)
  const [social, setSocial] = useState(null);   // openai-reformat status {status,url}
  const [copied, setCopied] = useState(null);   // index of the just-copied post
  const [scale, setScale] = useState(1);
  const stageRef = useRef(null);

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

  // the page keeps its true layout width and ZOOMS to fit the stage — wide mode
  // (and narrow windows) scale the page down rather than reflowing it
  const frameW = device === "mobile" ? 393 : 1060;
  useEffect(() => {
    const el = stageRef.current;
    if (!el) return undefined;
    const measure = () => setScale(Math.min(1, el.clientWidth / frameW));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [frameW]);

  const config = useMemo(() => buildSectionConfig({
    title,
    cover: coverAsset ? { src: coverAsset.src, alt: coverAsset.alt, layout: cover } : null,
    sections, cta, ai,
  }), [title, coverAsset, cover, sections, cta, ai]);

  const socialReady = social?.status === "ready" && !!social.url;
  const socialCooking = !noai && !!social && !socialReady && social.status !== "failed";
  const useSocial = shareImage === "social" && socialReady;
  const posts = socialPosts || [];

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

  const copyPost = (text, i) => {
    navigator.clipboard?.writeText(text);
    setCopied(i);
    setTimeout(() => setCopied((c) => (c === i ? null : c)), 1600);
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
        socialUrl: useSocial ? social.url : null, socialDocx: blob }))
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
        <div className="asm-pub-stage" ref={stageRef}>
          <div
            className={"asm-pub-frame" + (device === "mobile" ? " is-mobile" : "")}
            style={{ width: frameW, height: `calc(100% / ${scale})`, transform: `scale(${scale})` }}
          >
            <iframe className="asm-pub-iframe" title={t("lpm.publish.frame_title")} srcDoc={srcdoc} />
          </div>
        </div>

        {/* the focus toggle: give the rail room (and zoom the page), or take it back */}
        <button
          type="button" className="asm-pub-handle"
          title={wide ? t("lpm.publish.focus_page") : t("lpm.publish.focus_cards")}
          onClick={() => setWide((w) => !w)}
        >
          <Icon name={wide ? "chevrons-right" : "chevrons-left"} size={15} />
        </button>

        <aside className={"asm-pub-rail" + (wide ? " is-wide" : "")}>
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

          {posts.length > 0 && (
            <div className="asm-pub-card">
              <span className="asm-pub-card-title">{t("lpm.publish.posts_title")}</span>
              <p className="asm-pub-card-body">{t("lpm.publish.posts_blurb")}</p>
              {wide ? (
                <>
                  <div className="asm-pub-posts">
                    {posts.map((p, i) => (
                      <div key={i} className="asm-pub-post">
                        <div className="asm-pub-post-head">
                          <span className="asm-pub-post-week">{t("lpm.publish.posts_week", { n: i + 1 })}</span>
                          <button type="button" className="asm-pub-copy" onClick={() => copyPost(p, i)}>
                            <Icon name={copied === i ? "check" : "copy"} size={12} />
                            {copied === i ? t("lpm.publish.posts_copied") : t("lpm.publish.posts_copy")}
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
              ) : (
                // a taste of the posts, fading out — the full set lives in wide mode
                <button type="button" className="asm-pub-posts-teaser" onClick={() => setWide(true)}>
                  <span className="asm-pub-teaser-text">{posts[0]}</span>
                  <span className="asm-pub-teaser-more">{t("lpm.publish.posts_teaser_more")}</span>
                </button>
              )}
            </div>
          )}

          <div className="asm-pub-card">
            <span className="asm-pub-card-title">{t("lpm.publish.publish_title")}</span>
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
