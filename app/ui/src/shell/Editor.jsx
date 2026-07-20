import React, { useEffect, useState } from "react";
import { getReports } from "../api.js";
import { guard } from "../errorBus.js";
import AssembleMaker from "../landing/assemble/AssembleMaker.jsx";

// The customer editor: the SAME Assemble/Wordsmith/Preview/Publish engine the
// staff app uses, pointed at a platform document (UUID slug via the docbridge)
// with the shell's dark chrome. Nothing is regenerated on return — every
// artifact is cached with the document.
export default function Editor({ me, docId, onHome }) {
  const [doc, setDoc] = useState(null);

  useEffect(() => {
    let alive = true;
    getReports()
      .then((rep) => {
        if (!alive) return;
        const row = (rep.reports || []).find((r) => r.documentId === docId);
        setDoc({ slug: docId, name: row ? row.title : "" });
      })
      .catch(guard("shell: report lookup", null));
    return () => { alive = false; };
  }, [docId]);

  if (!doc) return null;
  return <AssembleMaker doc={doc} dark onHome={onHome} user={me?.user} />;
}
