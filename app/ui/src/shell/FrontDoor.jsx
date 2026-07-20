import React from "react";
import { t } from "../content.js";
import logoWhite from "./logo-white.svg";
import "./shell.css";

const Check = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="2.2"><path d="M20 6L9 17l-5-5" /></svg>
);

// The unauthenticated front door (round-1 "01 Front Door"). Credentials are
// never typed here — the buttons hand off to the identity provider. No top bar.
export default function FrontDoor() {
  return (
    <div className="sh-door">
      <div className="sh-door-l">
        <img src={logoWhite} alt="Report Kitchen" style={{ height: 30, alignSelf: "flex-start" }} />
        <h1>{t("lpm.door.title")}</h1>
        <p>{t("lpm.door.pitch")}</p>
        <div className="sh-door-feat">
          <span><Check />{t("lpm.door.feat1")}</span>
          <span><Check />{t("lpm.door.feat2")}</span>
          <span><Check />{t("lpm.door.feat3")}</span>
        </div>
        <span className="sh-door-learn">
          {t("lpm.door.learn_lead")} <a href="https://www.reportkitchen.com">{t("lpm.door.learn_link")} →</a>
        </span>
      </div>
      <div className="sh-door-r">
        <div className="sh-door-card">
          <h2>{t("lpm.door.card_title")}</h2>
          <a className="sh-door-cta" href="/api/auth/login">{t("lpm.door.signin")}</a>
          <p className="sh-door-alt">
            {t("lpm.door.signup_lead")}{" "}
            <a href="/api/auth/login?signup=1">{t("lpm.door.signup")}</a>
          </p>
        </div>
      </div>
    </div>
  );
}
