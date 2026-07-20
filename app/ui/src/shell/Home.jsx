import React, { useCallback, useEffect, useRef, useState } from "react";
import { getReports, patchWorkspaceSettings, uploadReport } from "../api.js";
import { t } from "../content.js";
import { guard } from "../errorBus.js";
import WhiskLoader from "../landing/assemble/WhiskLoader.jsx";
import logoWhite from "./logo-white.svg";
import "../landing/assemble/assemble.css";  // whisk animation styles
import "./shell.css";

const AI_LEVELS = ["none", "analysis", "full"];

const initialsOf = (user) =>
  (user?.name || user?.email || "?").split(/[\s@.]+/).filter(Boolean)
    .slice(0, 2).map((w) => w[0].toUpperCase()).join("");

export function TopBar({ user, onHome, children }) {
  return (
    <div className="sh-bar">
      <button type="button" className="sh-bar-logo" onClick={onHome} disabled={!onHome}>
        <img src={logoWhite} alt="Report Kitchen" />
      </button>
      <span className="sh-bar-title">{t("lpm.door.title")}</span>
      <div className="sh-bar-mid">{children}</div>
      <span className="sh-bar-avatar">{initialsOf(user)}</span>
    </div>
  );
}

export default function Home({ me, onOpen }) {
  const user = me?.user;
  const [data, setData] = useState(null);   // {workspace, plan, reports}
  const [dragOver, setDragOver] = useState(false);
  const [uploadErr, setUploadErr] = useState(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  const refresh = useCallback(() => {
    getReports().then(setData).catch(guard("home: reports", null));
  }, []);
  useEffect(() => { refresh(); }, [refresh]);

  // poll while anything is still converting, so the whisk resolves on its own
  const busy = (data?.reports || []).some((r) =>
    r.status === "uploaded" || r.status === "processing");
  useEffect(() => {
    if (!busy) return undefined;
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [busy, refresh]);

  const atLimit = data?.plan?.max != null && data.plan.used >= data.plan.max;

  const takeFile = (file) => {
    if (!file || uploading || atLimit) return;
    setUploadErr(null);
    setUploading(true);
    uploadReport(file)
      .then(() => refresh())
      .catch((e) => setUploadErr(e.detail || e.message))
      .finally(() => setUploading(false));
  };

  const aiLevel = data?.workspace?.aiLevel || "full";
  const pickAi = (level) => {
    if (!data || level === aiLevel) return;
    setData({ ...data, workspace: { ...data.workspace, aiLevel: level } });
    patchWorkspaceSettings(data.workspace.id, { aiLevel: level })
      .catch(guard("home: ai level", null));
  };

  const fmtDate = (iso) => new Date(iso).toLocaleDateString(undefined,
    { month: "short", day: "numeric", year: "numeric" });

  return (
    <div className="sh-root">
      <TopBar user={user} />
      <main className="sh-home">
        <aside className="sh-rail">
          <div className="sh-help">
            <div className="sh-help-title">{t("lpm.home.help_title")}</div>
            <p>{t("lpm.home.help_body")}</p>
          </div>
          <div className="sh-ai">
            <h2>{t("lpm.home.ai_title")}</h2>
            <p className="sh-ai-sub">{t("lpm.home.ai_sub")}</p>
            {AI_LEVELS.map((lv) => (
              <button
                key={lv} type="button"
                className={"sh-ai-opt" + (aiLevel === lv ? " is-on" : "")}
                onClick={() => pickAi(lv)}
              >
                {lv === "full" && <span className="sh-ai-badge">{t("lpm.home.ai_default_badge")}</span>}
                <span className="sh-ai-dot" />
                <span className="sh-ai-t">{t(`lpm.home.ai.${lv}.title`)}</span>
                <span className="sh-ai-d">{t(`lpm.home.ai.${lv}.desc`)}</span>
              </button>
            ))}
          </div>
        </aside>

        <div className="sh-main">
          <div>
            <div className="sh-kicker">
              {user?.name ? t("lpm.home.kicker_name", { name: user.name.split(" ")[0] })
                : t("lpm.home.kicker")}
            </div>
            <h1 className="sh-h1">{t("lpm.home.h1")}</h1>
            <p className="sh-intro">{t("lpm.home.intro")}</p>
          </div>

          <div
            className={"sh-drop" + (dragOver ? " is-over" : "") + (atLimit ? " is-disabled" : "")}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              takeFile(e.dataTransfer.files?.[0]);
            }}
            onClick={() => !atLimit && fileRef.current?.click()}
          >
            <input
              ref={fileRef} type="file" accept="application/pdf" hidden
              onChange={(e) => { takeFile(e.target.files?.[0]); e.target.value = ""; }}
            />
            {uploading ? (
              <>
                <WhiskLoader size={72} />
                <div className="sh-drop-t">{t("lpm.home.uploading")}</div>
              </>
            ) : atLimit ? (
              <div className="sh-drop-t">{t("lpm.home.limit_reached", { max: data.plan.max })}</div>
            ) : (
              <>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="sh-drop-ico">
                  <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
                  <path d="M14 2v4a2 2 0 0 0 2 2h4" /><path d="M12 18v-6" /><path d="m15 15-3-3-3 3" />
                </svg>
                <div className="sh-drop-t">{t("lpm.home.drop_title")}</div>
                <p className="sh-drop-s">
                  {t("lpm.home.drop_or")} <a onClick={(e) => e.preventDefault()} href="#browse">{t("lpm.home.drop_browse")}</a>
                  {data?.plan ? <> · {t("lpm.home.drop_limit", { mb: 50 })}</> : null}
                </p>
              </>
            )}
          </div>
          {uploadErr && <div className="sh-error">{uploadErr}</div>}

          <div>
            <div className="sh-reports-head">
              <h2>{t("lpm.home.reports_title")}</h2>
              {data?.plan?.max != null && (
                <span className="sh-plan">
                  {t("lpm.home.plan_counter", { used: data.plan.used, max: data.plan.max })}
                </span>
              )}
            </div>
            <div className="sh-table">
              {(data?.reports || []).length === 0 && (
                <div className="sh-empty">{t("lpm.home.empty")}</div>
              )}
              {(data?.reports || []).map((r) => {
                const processing = r.status === "uploaded" || r.status === "processing";
                const open = r.status === "converted" && r.documentId;
                return (
                  <div key={r.projectId} className="sh-row">
                    <span className="sh-thumb">
                      {processing ? <WhiskLoader size={40} />
                        : r.thumb ? <img src={r.thumb} alt="" />
                          : <span className="sh-thumb-blank" />}
                    </span>
                    <span className="sh-row-main">
                      {open ? (
                        <button type="button" className="sh-row-title" onClick={() => onOpen(r.documentId)}>
                          {r.title}
                        </button>
                      ) : (
                        <span className="sh-row-title is-static">{r.title}</span>
                      )}
                      <span className="sh-row-sub">
                        {processing ? t("lpm.home.processing")
                          : r.status === "failed" ? t("lpm.home.failed")
                            : r.pages ? t("lpm.home.pages", { n: r.pages }) : null}
                      </span>
                    </span>
                    <span className="sh-row-date">{fmtDate(r.lastModified)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
