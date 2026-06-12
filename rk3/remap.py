"""Re-anchor feedback entries after a conversion changes node identities.

nids are content-derived and survive most pipeline changes, but text fixes do
change text. Whenever analyze produces a new IR, this pass matches the
previous IR's nodes to the new ones (exact normalized text, then similarity
with position tiebreak) and rewrites feedback/<slug>.jsonl anchors in place.
Entries whose targets genuinely vanished are flagged "orphaned" rather than
silently left pointing at nothing.
"""

import difflib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEEDBACK = ROOT / "feedback"


def _norm(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())[:120]


def _features(ir):
    feats = {}

    def add(node):
        if node.get("nid"):
            feats[node["nid"]] = (node["type"], node["page"],
                                  _norm(node.get("text")), node.get("bbox"))

    for n in ir.get("body", []):
        add(n)
        for c in n.get("children", []):
            add(c)
    return feats


def _match(old_feat, new_feats, taken):
    otype, opage, otext, obbox = old_feat
    cands = [(nid, f) for nid, f in new_feats.items()
             if nid not in taken and f[0] == otype and f[1] == opage]
    if otext:
        exact = [nid for nid, f in cands if f[2] == otext]
        if len(exact) == 1:
            return exact[0]
        best, score = None, 0.0
        for nid, f in cands:
            if not f[2]:
                continue
            r = difflib.SequenceMatcher(None, otext, f[2]).ratio()
            if r > score:
                best, score = nid, r
        if score >= 0.6:
            return best
    elif obbox:  # geometric nodes (figures): nearest center
        ox = (obbox[0] + obbox[2]) / 2
        oy = (obbox[1] + obbox[3]) / 2
        best, dist = None, 1e9
        for nid, f in cands:
            if not f[3]:
                continue
            d = abs((f[3][0] + f[3][2]) / 2 - ox) + abs((f[3][1] + f[3][3]) / 2 - oy)
            if d < dist:
                best, dist = nid, d
        if best is not None and dist < 80:
            return best
    return None


def remap_feedback(slug, old_ir, new_ir, log):
    path = FEEDBACK / f"{slug}.jsonl"
    if not path.exists():
        return
    old_f, new_f = _features(old_ir), _features(new_ir)
    new_qids = {q["qid"] for q in new_ir.get("questions", [])}
    old_q = {q["qid"]: q for q in old_ir.get("questions", [])}
    new_q_by_nid = {}
    for q in new_ir.get("questions", []):
        new_q_by_nid.setdefault((q["kind"], q["nid"]), q)

    entries = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    taken = set()
    changed = False
    for rec in entries:
        nid = rec.get("nid")
        if nid and nid not in new_f:
            old_feat = old_f.get(nid)
            new_nid = _match(old_feat, new_f, taken) if old_feat else None
            if new_nid:
                taken.add(new_nid)
                log.entry("remap-nid", old=nid, new=new_nid,
                          note=(rec.get("text") or "")[:50])
                rec["nid"] = new_nid
                rec.pop("orphaned", None)
                changed = True
            elif not rec.get("orphaned"):
                log.entry("orphan", nid=nid, note=(rec.get("text") or "")[:50])
                rec["orphaned"] = True
                changed = True

        qid = rec.get("qid")
        if qid and qid not in new_qids:
            oldq = old_q.get(qid)
            kind = oldq["kind"] if oldq else None
            newq = new_q_by_nid.get((kind, rec.get("nid"))) if kind else None
            if newq:
                log.entry("remap-qid", old=qid, new=newq["qid"], kind=kind)
                rec["qid"] = newq["qid"]
                rec.pop("orphaned", None)
                changed = True
            elif not rec.get("orphaned"):
                log.entry("orphan-qid", qid=qid)
                rec["orphaned"] = True
                changed = True

    if changed:
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                                for r in entries))
