import React, { useMemo, useState } from "react";
import { t } from "../../content.js";
import { assetBase, sourceUrl } from "../../api.js";
import { guard } from "../../errorBus.js";
import { buildDocumentHtml } from "../finalHtml.js";
import { exportZip } from "../exportZip.js";
import { buildSectionConfig } from "./model.js";
import { Icon } from "./icons.jsx";

// Preview: the finished page, exactly as a visitor gets it — the same document
// the export writes, rendered in an isolated iframe (its own head/CSS/fonts, no
// app chrome bleeding in). The publish/download options live in the right-rail
// card (the Wordsmith sticky-note spot); a separate Publish screen isn't needed.
export default function Preview({ slug, docName, title, coverAsset, cover, accent,
  sections, cta, ai, edits, onBack }) {
  const [device, setDevice] = useState("desktop");
  const [zipping, setZipping] = useState(false);

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

  const bundled = !!cta?.download && !cta?.downloadUrl;

  const download = () => {
    setZipping(true);
    exportZip(slug, { config, edits, accent, docName })
      .catch(guard("preview: export zip", null))
      .finally(() => setZipping(false));
  };

  return (
    <div className="asm-pv">
      <div className="asm-ws-bar">
        <button type="button" className="asm-ws-back" onClick={onBack}>
          <Icon name="chevron-left" size={14} />{t("lpm.preview.back_to_wordsmith")}
        </button>
        <span className="asm-ws-back-hint">{t("lpm.preview.back_hint")}</span>
        <div className="asm-pv-devices">
          {["desktop", "mobile"].map((d) => (
            <button
              key={d} type="button"
              className={"asm-pv-device" + (device === d ? " is-on" : "")}
              onClick={() => setDevice(d)}
            >
              <Icon name={d === "desktop" ? "monitor" : "smartphone"} size={14} />
              {t(`lpm.preview.device.${d}`)}
            </button>
          ))}
        </div>
      </div>

      <div className="asm-pv-canvas">
        <div className="asm-pv-stage">
          <div className={"asm-pv-frame" + (device === "mobile" ? " is-mobile" : "")}>
            <iframe className="asm-pv-iframe" title={t("lpm.preview.frame_title")} srcDoc={srcdoc} />
          </div>
        </div>
        <aside className="asm-pv-card">
          <div className="asm-pv-card-title">{t("lpm.preview.publish_title")}</div>
          <p className="asm-pv-card-body">
            {bundled ? t("lpm.preview.zip_bundled") : t("lpm.preview.zip_no_pdf")}
          </p>
          <button type="button" className="asm-pv-dl" onClick={download} disabled={zipping}>
            <Icon name="download" size={15} />
            {zipping ? t("lpm.preview.download_building") : t("lpm.preview.download_zip")}
          </button>
          <p className="asm-pv-card-hint">{t("lpm.preview.publish_hint")}</p>
        </aside>
      </div>
    </div>
  );
}
