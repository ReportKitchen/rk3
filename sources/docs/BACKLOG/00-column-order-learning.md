

On columns — straight answer: no, we did not nail them, and I won't pretend the join passes are the fix. What I built is geometric heuristics (same-column-below, next-column-overlap, mid-sentence+lowercase) — exactly the instance-patching you're wary of. The root issue is that reading order itself is inferred, and our inference is a pile of join passes rather than one principled column-flow model. That deserves the same treatment we just gave bold: find the deterministic signal (struct tags where present; a real column-segmentation model where not), build it once, and stop patching. I'm deliberately tabling it until emphasis is locked so we finish one element completely instead of half-finishing two — and when we pick it up, you'll get the full root-cause analysis first, not a fix.

should we attempt to learn to get better at this?  Or, build a dedicated learning model that examines 100+ pdfs to understand how columns exist in the wild?


