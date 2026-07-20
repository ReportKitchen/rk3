import React, { useCallback, useEffect, useState } from "react";
import Home from "./Home.jsx";
import Editor from "./Editor.jsx";

// The signed-in customer app: Home (?nothing) or the editor (?report=<docId>).
// The URL is the router — reload lands you back where you were.
export default function CustomerShell({ me }) {
  const read = () => new URLSearchParams(window.location.search).get("report");
  const [reportDoc, setReportDoc] = useState(read);

  useEffect(() => {
    const onPop = () => setReportDoc(read());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const openReport = useCallback((docId) => {
    window.history.pushState({}, "", `?report=${docId}`);
    setReportDoc(docId);
  }, []);
  const goHome = useCallback(() => {
    window.history.pushState({}, "", window.location.pathname);
    setReportDoc(null);
  }, []);

  return reportDoc
    ? <Editor me={me} docId={reportDoc} onHome={goHome} />
    : <Home me={me} onOpen={openReport} />;
}
