"""Vision loop driver (STUB — filled in during webified.md §4).

The outer loop the plan specifies (§4.3):

    triage -> hard pages -> cluster -> for each cluster representative:
      iter 1..3: scan (vision issues); if no medium+ issues -> PASS, break
                 prescribe -> apply overrides -> re-convert -> re-render
      after reps converge: apply doc-level lessons, scan siblings once

The prescriber itself lives in rk3.visionqa.prescribe() (added in §4.1). This
module is the outer loop + the safety rails (§4.2: known-lever-only, provenance
stamping, oscillation ledger) + convergence bookkeeping to
output/pdfium/<slug>/visionloop.jsonl (§4.4). It is deliberately empty until
§4 so nothing spends vision budget before the levers (§3) and pilots exist.
"""


def run(slug, pages=None, max_iter=3, budget=40):
    raise NotImplementedError(
        "tools/visionloop.py is a stub until webified.md §4 (needs §3 levers "
        "and rk3.visionqa.prescribe first)")


if __name__ == "__main__":
    raise SystemExit(__doc__)
