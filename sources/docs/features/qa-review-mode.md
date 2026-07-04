> **STATUS:** PARTIAL — a QA/review mode shipped via a DIFFERENT mechanism (vision-QA reviewer: rk3/visionqa.py, `/api/qa/{slug}/run`, ReviewBoard.jsx). The formatting toggles, deterministic checks, and "things we removed" list described here are NOT the shipped implementation.

# A mode for users to perform QA in

## tools for the user
- toggle(s) to show/hide formatting notes: h1/2/3, outline ol/ul

## auto suggestions
- broken UL/OL
- broken sentence?  <p> ends without punctuation and the next starts without a capital letter?
- missing ALT text (with auto suggest if AI enabled)
- Case problems: all caps and title case inconsistencies

## Anything that gets removed should show up on the "we removed these things" list, sorted by confidence.
- page numbers: high confidence
- some decorative graphic elements: med confidence 