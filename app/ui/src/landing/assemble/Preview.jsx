import React, { useEffect, useMemo, useRef, useState } from "react";
import { t } from "../../content.js";
import { assetBase, sourceUrl } from "../../api.js";
import { buildDocumentHtml } from "../finalHtml.js";
import { buildSectionConfig } from "./model.js";
import { Icon } from "./icons.jsx";

// Preview: the finished page, exactly as a visitor gets it — the same document
// the export writes, rendered in an isolated iframe (its own head/CSS/fonts, no
// app chrome bleeding in) with a desktop/mobile width toggle. Just the page:
// the social kit and download options live on the Publish step.
export default function Preview({ slug, docName, title, coverAsset, cover, accent,
  sections, cta, ai, edits, onBack, onPublish }) {
  const [device, setDevice] = useState("desktop");
  const [scale, setScale] = useState(1);
  const stageRef = useRef(null);

  // the page keeps its true layout width and ZOOMS to fit a narrow window —
  // scaled down rather than reflowed
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

  // srcdoc inherits our base URL, so server paths (/output/…, /api/…) resolve —
  // the download button really downloads. Share buttons stay inert here: a
  // srcdoc page has no address to share (the export wires them for real).
  const srcdoc = useMemo(() => buildDocumentHtml({
    config, edits, accent, slug, docName,
    resolveAsset: (s) => (s?.startsWith("http") ? s : `${assetBase(slug)}/${s}`),
    downloadHref: sourceUrl(slug),
  }), [config, edits, accent, slug, docName]);

  return (
    <div className="asm-pub">
      <div className="asm-ws-bar">
        <button type="button" className="asm-ws-back" onClick={onBack}>
          <Icon name="chevron-left" size={14} />{t("lpm.preview.back_to_wordsmith")}
        </button>
        <span className="asm-ws-back-hint">{t("lpm.preview.back_hint")}</span>
        <div className="asm-pub-devices">
          {["desktop", "mobile"].map((d) => (
            <button
              key={d} type="button"
              className={"asm-pub-device" + (device === d ? " is-on" : "")}
              onClick={() => setDevice(d)}
            >
              <Icon name={d === "desktop" ? "monitor" : "smartphone"} size={14} />
              {t(`lpm.preview.device.${d}`)}
            </button>
          ))}
        </div>
        <button type="button" className="asm-ws-next" onClick={onPublish}>
          {t("lpm.preview.to_publish")}<Icon name="chevron-right" size={14} />
        </button>
      </div>

      <div className="asm-pub-canvas">
        <div className="asm-pub-stage" ref={stageRef}>
          <div
            className={"asm-pub-frame" + (device === "mobile" ? " is-mobile" : "")}
            style={{ width: frameW, height: `calc(100% / ${scale})`, transform: `scale(${scale})` }}
          >
            <iframe className="asm-pub-iframe" title={t("lpm.preview.frame_title")} srcDoc={srcdoc} />
          </div>
        </div>
      </div>
    </div>
  );
}
