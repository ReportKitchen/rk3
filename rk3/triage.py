"""Page triage (webified §2): a deterministic, cheap easy/moderate/hard call
per page, so the vision loop (§4) spends only where the tail is.

No ML, no vision — thresholds over evidence that already exists per doc:
ir.json (node types per page) and debug-analyze.jsonl events (figure reasons
carrying label-soup/assembled/hero, `table`/`region-dissolved`/`callout`/
`figure-grown` events, `column-model` ncols+confidence, region `question`s).

    python -m rk3.triage            # print triage for every converted doc
    python -m rk3.triage <slug>     # one doc, per-page signals + class

The class is written into output/pdfium/<slug>/scoreboard.json by
tools/scoreboard.py, which calls triage_doc().
"""

import collections
import json
import sys

from . import irwalk
from .documents import list_documents, output_dir

CLASSES = ("easy", "moderate", "hard")


def _events(slug):
    p = output_dir(slug) / "debug-analyze.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def _blank():
    return {"n_figures": 0, "n_tables": 0, "n_asides": 0, "n_lists": 0,
            "n_para": 0, "n_head": 0, "n_callouts": 0,
            "label_soup": 0, "assembled": 0, "hero": 0, "grown": 0,
            "dissolve": 0, "questions": 0, "uncertain": 0, "fig_anatomy": 0,
            "ncols": 1, "colconf": 1.0}


def page_signals(slug):
    """Per-page signal dict for a doc: {page: {...signals...}}."""
    ir_path = output_dir(slug) / "ir.json"
    ir = json.loads(ir_path.read_text()) if ir_path.exists() else {}
    body = ir.get("body", [])
    nid_page = {n["nid"]: n.get("page") for n in irwalk.walk(body) if n.get("nid")}
    S = collections.defaultdict(_blank)

    for n in irwalk.walk(body):
        p, t = n.get("page"), n.get("type")
        if p is None:
            continue
        s = S[p]
        if t == "figure":
            s["n_figures"] += 1
        elif t == "table":
            s["n_tables"] += 1
        elif t == "aside":
            s["n_asides"] += 1
        elif t == "list":
            s["n_lists"] += 1
        elif t == "paragraph":
            s["n_para"] += 1
        elif t == "heading":
            s["n_head"] += 1

    for e in _events(slug):
        ev, p = e.get("event"), e.get("page")
        if ev == "figure" and p is not None:
            r = (e.get("reason") or "").lower()
            if "label-soup" in r:
                S[p]["label_soup"] += 1
            if "assembled" in r:
                S[p]["assembled"] += 1
            if "hero" in r:
                S[p]["hero"] += 1
        elif ev == "callout" and p is not None:
            S[p]["n_callouts"] += 1
        elif ev == "figure-grown" and p is not None:
            S[p]["grown"] += 1
        elif ev == "region-dissolved" and p is not None:
            S[p]["dissolve"] += 1
        elif ev == "figure-model" and p is not None:
            if e.get("uncertain"):
                S[p]["uncertain"] += 1
            if (e.get("title") or e.get("caption")):
                S[p]["fig_anatomy"] += 1
        elif ev == "column-model" and p is not None:
            S[p]["ncols"] = max(S[p]["ncols"], e.get("ncols", 1))
            S[p]["colconf"] = min(S[p]["colconf"], e.get("conf", 1.0))
        elif ev == "question":
            p2 = nid_page.get(e.get("nid"))
            if p2 is not None:
                S[p2]["questions"] += 1
    return dict(S)


def classify(s):
    """easy | moderate | hard from one page's signals (see §2.1)."""
    hard = (s["label_soup"] or s["assembled"] or s["grown"] or s["hero"]
            or s["dissolve"] or s["questions"] or s["uncertain"]
            or s["n_tables"] >= 1
            or s["n_callouts"] >= 2
            or s["n_figures"] > 4
            or (s["ncols"] >= 2 and s["colconf"] < 0.55))
    if hard:
        return "hard"
    # NB clean multi-column text is EASY (plan §2.1: "single column or clean
    # 2-col"); a bare column count does NOT make a page moderate — asides,
    # figures or callouts do. Low-confidence multi-column is caught as hard above.
    moderate = (s["n_figures"] >= 2 or s["n_callouts"] >= 1 or s["n_asides"] >= 1
                or (s["n_figures"] == 1 and s["fig_anatomy"]))
    return "moderate" if moderate else "easy"


def cluster_signature(s):
    """The §2.3 template signature for a hard page: pages sharing it form a
    cluster the loop can learn once and apply to siblings."""
    return (s["n_figures"], s["n_tables"], s["n_callouts"], s["ncols"],
            bool(s["assembled"] or s["fig_anatomy"]), bool(s["hero"]))


def triage_doc(slug):
    """{page: {'class':..., 'signals':{...}}} for every page with signals."""
    sig = page_signals(slug)
    return {p: {"class": classify(s), "signals": s} for p, s in sig.items()}


def clusters(slug):
    """{signature: [pages]} over this doc's HARD pages only (§2.3)."""
    out = collections.defaultdict(list)
    for p, info in triage_doc(slug).items():
        if info["class"] == "hard":
            out[cluster_signature(info["signals"])].append(p)
    return {k: sorted(v) for k, v in out.items()}


def _print_doc(slug):
    t = triage_doc(slug)
    counts = collections.Counter(v["class"] for v in t.values())
    print(f"\n{slug}  easy={counts['easy']} moderate={counts['moderate']} hard={counts['hard']}")
    for p in sorted(t):
        info = t[p]
        s = info["signals"]
        hot = [k for k in ("label_soup", "assembled", "hero", "grown", "dissolve",
                           "questions", "uncertain") if s[k]]
        extra = (f" fig={s['n_figures']} tbl={s['n_tables']} call={s['n_callouts']} "
                 f"cols={s['ncols']}({s['colconf']:.2f})")
        print(f"  p{p:<4} {info['class']:<9}{extra}  {'|'.join(hot)}")
    return counts


def main():
    args = sys.argv[1:]
    if args:
        for slug in args:
            _print_doc(slug)
    else:
        total = collections.Counter()
        for d in list_documents():
            if d.get("status") == "done":
                total += _print_doc(d["slug"])
        print(f"\nCORPUS: easy={total['easy']} moderate={total['moderate']} hard={total['hard']}")


if __name__ == "__main__":
    main()
