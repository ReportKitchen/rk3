"""Vision loop driver (webified §4.2–4.4).

The loop the plan specifies (§4.3):

    triage -> hard pages -> cluster -> for each cluster representative:
      iter 1..3: scan (vision issues); no medium+ -> PASS, break
                 prescribe -> apply overrides (safety-railed) -> reconvert
      after reps converge: apply doc-level lessons, scan siblings once

Prescriber lives in rk3.visionqa.prescribe (§4.1). This module is the outer
loop + the safety rails (§4.2: known-lever-only, page-scope guard, provenance
stamping, oscillation ledger, owner-entry preservation) + convergence
bookkeeping to output/pdfium/<slug>/visionloop.jsonl (§4.4).

    python tools/visionloop.py <slug> --page N [--iters 3] [--model ...]
    python tools/visionloop.py <slug> [--budget 40]     # full doc loop
    python tools/visionloop.py <slug> --page N --dry-run  # scan+prescribe only
"""

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rk3 import triage                                            # noqa: E402
from rk3.ai import usage_summary                                  # noqa: E402
from rk3.documents import output_dir, source_for_slug            # noqa: E402
from rk3.visionqa import LEVER_NAMES, prescribe, qa_page, shoot   # noqa: E402

# structure levers whose config value is a LIST we append to; styleTokens is a
# dict-merge lever handled separately. tablePins/figureBands/etc. all list.
LIST_LEVERS = set(LEVER_NAMES)
SEVERE = ("critical", "high", "medium")   # medium+ = a page does NOT pass


def _today():
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


def _config_path(slug):
    src = source_for_slug(slug)
    return src.with_name(src.stem + ".config.json") if src else None


def _load_config(slug):
    p = _config_path(slug)
    if p and p.exists():
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _target_sig(lever, entry):
    """A stable identity for an override's TARGET (not its value) — so we can
    detect a later prescription flipping the same target (oscillation)."""
    if "nid" in entry:
        return (lever, "nid", entry["nid"])
    if "textPrefix" in entry:
        return (lever, "pre", entry["textPrefix"][:40])
    if "page" in entry and "bbox" in entry:
        return (lever, "box", entry["page"],
                tuple(round(v / 10) for v in entry["bbox"]))
    if "page" in entry:
        return (lever, "page", entry["page"])
    return (lever, "raw", json.dumps(entry, sort_keys=True)[:60])


def _value_sig(lever, entry):
    return json.dumps({k: v for k, v in entry.items()
                       if not k.startswith("_")}, sort_keys=True)


def apply_prescription(slug, prescription, page, iteration):
    """Safety-railed apply (§4.2): merge the prescription's overrides into the
    doc's config.json. Returns (applied, refused). Rails:
      - known lever types only;
      - a page-scoped entry must target THIS page (never touches others);
      - stamp _source provenance on every entry;
      - never delete owner entries (append-only merge);
      - oscillation: refuse an entry that flips a prior vision-loop entry's
        value on the same target;
      - idempotence: skip an exact-duplicate vision-loop entry."""
    cfg = _load_config(slug)
    structure = cfg.setdefault("structure", {})
    src = f"vision-loop {_today()} p{page} iter{iteration}"
    applied, refused = [], []
    for ov in prescription.get("overrides", []):
        lever, entry = ov.get("lever"), dict(ov.get("entry") or {})
        if lever not in LIST_LEVERS or not entry:
            refused.append({"lever": lever, "why": "unknown lever / empty entry"})
            continue
        if "page" in entry and entry["page"] != page:
            refused.append({"lever": lever, "why": f"out-of-scope page {entry['page']}"})
            continue
        lst = structure.setdefault(lever, [])
        tsig, vsig = _target_sig(lever, entry), _value_sig(lever, entry)
        prior_vl = [e for e in lst if str(e.get("_source", "")).startswith("vision-loop")
                    and _target_sig(lever, e) == tsig]
        if any(_value_sig(lever, e) == vsig for e in prior_vl):
            continue  # exact duplicate → idempotent no-op
        if prior_vl:   # same target, different value → oscillation
            refused.append({"lever": lever, "why": "oscillation (flips prior vision entry)"})
            prescription.setdefault("residuals", []).append(
                {"issue": f"oscillation on {lever} {tsig}", "missingLever": "oscillation"})
            continue
        entry["_source"] = src
        lst.append(entry)
        applied.append({"lever": lever, "entry": entry})
    if applied:
        _config_path(slug).write_text(json.dumps(cfg, indent=2) + "\n")
    return applied, refused


def _reconvert(slug):
    subprocess.run([sys.executable, "-m", "rk3", "convert", slug],
                   cwd=ROOT, capture_output=True, text=True, timeout=1800)


def _scan(slug, page, model=None):
    shots = shoot(slug, pages=[page])
    if page not in shots:
        return []
    return qa_page(slug, page, our_png=shots[page], model=model)


def _sev_counts(flags):
    c = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in flags:
        s = f.get("severity")
        if s in c:
            c[s] += 1
    return c


def _log_iter(slug, rec):
    p = output_dir(slug) / "visionloop.jsonl"
    with p.open("a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def converge_page(slug, page, max_iter=3, model=None, dry_run=False):
    """Per-page loop (§4.3): scan → (prescribe → apply → reconvert) until no
    medium+ issue or `max_iter`. Returns the iteration records. Model tiering
    (§0.7): scan on the scan tier, prescribe on the prescribe tier — unless an
    explicit `model` overrides both. Each record logs the models it ran."""
    from rk3.ai import model_for
    scan_m = model or model_for("scan")
    prescribe_m = model or model_for("prescribe")
    records = []
    for it in range(1, max_iter + 1):
        flags = _scan(slug, page, model=scan_m)
        before = _sev_counts(flags)
        severe = sum(before[s] for s in SEVERE)
        rec = {"page": page, "iter": it, "before": before, "severe": severe,
               "models": {"scan": scan_m, "prescribe": prescribe_m},
               "ts": datetime.datetime.now(datetime.timezone.utc)
                     .isoformat(timespec="seconds")}
        if severe == 0:
            rec["result"] = "PASS"
            records.append(rec)
            _log_iter(slug, rec)
            break
        pres = prescribe(slug, page, model=prescribe_m)
        rec["residuals"] = pres.get("residuals", [])
        rec["proposed"] = len(pres.get("overrides", []))
        if dry_run:
            rec["result"] = "dry-run"
            records.append(rec)
            _log_iter(slug, rec)
            break
        applied, refused = apply_prescription(slug, pres, page, it)
        rec["applied"] = applied
        rec["refused"] = refused
        rec["result"] = "applied" if applied else "no-lever"
        records.append(rec)
        _log_iter(slug, rec)
        if not applied:
            break   # nothing a lever can express → converge as-is (residuals stand)
        _reconvert(slug)
    return records


def run(slug, page=None, max_iter=3, model=None, budget=40, dry_run=False, quick=False):
    if page is not None:
        return {"pages": {page: converge_page(slug, page, max_iter, model, dry_run)}}
    if quick:  # webified §2.4: the representative ≤10-page set, not the full doc
        from tools.scoreboard import _scanned_pages
        sel = triage.quick_scan_pages(slug, scanned=_scanned_pages(slug))
        out = {p: converge_page(slug, p, max_iter, model, dry_run) for p, _w in sel}
        return {"quick": [{"page": p, "why": w} for p, w in sel], "pages": out}
    tri = triage.triage_doc(slug)
    hard = sorted(p for p, info in tri.items() if info["class"] == "hard")
    clusters = triage.clusters(slug)
    reps = sorted({pages[0] for pages in clusters.values()})   # one rep per cluster
    out, spent_pages = {}, 0
    for rep in reps:
        if spent_pages >= budget:
            out.setdefault("_parked", []).append(rep)
            continue
        out[rep] = converge_page(slug, rep, max_iter, model, dry_run)
        spent_pages += len(out[rep])
    return {"hard": hard, "reps": reps, "pages": out, "parked": out.get("_parked", [])}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--page", type=int)
    ap.add_argument("--iters", type=int, default=3)
    ap.add_argument("--budget", type=int, default=40)
    ap.add_argument("--model")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quick", action="store_true",
                    help="the §2.4 representative ≤10-page set instead of the full doc")
    a = ap.parse_args()
    before = usage_summary()["cost"]
    res = run(a.slug, a.page, a.iters, a.model, a.budget, a.dry_run, a.quick)
    print(json.dumps(res, indent=1, default=str)[:4000])
    print(f"\nvision spend this run: ${round(usage_summary()['cost'] - before, 3)}")


if __name__ == "__main__":
    main()
