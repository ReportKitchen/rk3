import React, { useEffect, useState } from "react";
import { devLogin, getMe } from "../api.js";
import { loadContent } from "../content.js";

// The boot fork (multiuser): who is this, and which app do they get?
//   anonymous + oidc  -> the Front Door (sign-in/sign-up buttons)
//   anonymous + dev   -> auto dev-login (this box's frictionless mode)
//   staff             -> the internal corpus app (unchanged)
//   everyone else     -> the customer LPM shell (Home / Editor)
const StaffApp = React.lazy(() => import("../App.jsx"));
const FrontDoor = React.lazy(() => import("./FrontDoor.jsx"));
const CustomerShell = React.lazy(() => import("./CustomerShell.jsx"));

export default function Root() {
  const [me, setMe] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        await loadContent("lpm");
        let m = await getMe();
        if (!m.user && m.authMode === "dev") {
          await devLogin();
          m = await getMe();
        }
        if (alive) setMe(m);
      } catch {
        if (alive) setMe({ user: null, workspaces: [], authMode: "oidc" });
      }
      if (alive) setReady(true);
    })();
    return () => { alive = false; };
  }, []);

  if (!ready) return null;
  const role = me?.user?.platformRole;
  return (
    <React.Suspense fallback={null}>
      {!me?.user ? <FrontDoor />
        : role === "platform_admin" || role === "support" ? <StaffApp />
          : <CustomerShell me={me} />}
    </React.Suspense>
  );
}
