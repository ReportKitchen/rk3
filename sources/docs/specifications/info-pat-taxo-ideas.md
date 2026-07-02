
# Could we identify activities related to some of our client's core concerns?

- Workforce: hiring, firing, training, expansion, recruitment
- Housing: 
- Education:
- Health:


## What about specific terms/keywords

- Social Determinants of Health
- Trauma-informed
- Deeper Learning

---

*(main agent, from the 2026-07-02 review session — registry-ready sketches)*

## funding_event (Layer 2 compound) — the baystate find

> "In 2020, Baystate Health received $125,000 in grant funding from the
> Ascend at the Aspen Institute 'Family Prosperity Innovation Community'"

**Frame:** [funder] gave/awarded → [recipient] received — [amount] — for
[purpose] — in [period]. Directional verbs tell the entities apart
(received/from vs awarded/granted to).

**Why it's strong:** it assembles entirely from atoms Stage A already
detects — two named_entities + a currency statistic + a date_time_period +
a purpose clause — exactly what Stage D (compound assembly) exists for. No
new detector, just a grouping rule.

**Fields:** funder, recipient, amount, currency, period, purpose,
program_name (the quoted program title — note: quoted program names are a
third naming-flavored quotation false positive, after scare quotes and
mission statements).

**Component candidates:** funding table / funder-acknowledgment block /
"our funders" grid / funding timeline.

**Market-research kicker:** funding events aggregated across a corpus of
foundation reports = a who-funds-what dataset straight from published
documents.

## The generalization: domain EVENT FRAMES

funding_event is one instance of [actor] [verb-frame] [object/amount]
[time] [purpose]. The client-concern list above is the same shape with
per-domain verb lexicons:

- workforce_event: hired/trained/recruited/expanded — baystate's "goals to
  increase local hiring between five and ten percent annually" is one (and
  it's a COMMITMENT, not a result: tense/modality is a field worth
  capturing — achieved vs pledged).
- housing_event: built/preserved/financed N units…
- education_event: enrolled/graduated/served N students…
- health_event: screened/vaccinated/treated N patients…

Registry idea: ONE event-frame machinery, per-domain verb lexicons as
config — which also makes "client core concerns" a per-org setting (same
per-org pattern as assistance levels). The keyword list above then becomes
the cheapest tier of the same thing: term-watch patterns with no frame,
just presence + context.

## partnership / collaboration (Layer 2) — the relational sibling

> "…a regional anchor collaborative, the Western Massachusetts Anchor
> Collaborative (WMAC), which Baystate Health launched in 2022 in
> partnership with the Economic Development Council and several large
> local employers. 'Each of us has pledged to…' Keroack stated."

**Frame:** [convener] launched/founded/joined [collaborative] in [period]
in partnership with [partners…]. Signals: "in partnership with",
"in collaboration with", "co-founded", "member of", "convened by",
"coalition/collaborative/alliance/network" head nouns.

**What makes it different from funding_event:** the payload is a
RELATIONSHIP SET (edges among entities), not a transaction — and it often
MINTS a new entity (WMAC is born in this sentence, with its acronym).
Fields: collaborative_name (+acronym), convener, partners[] (incl.
unnamed classes like "several large local employers"), period, purpose.

**Specimen bonus — it's a compound of compounds:** the attached quote is a
REAL quotation (speaker: Keroack ✓ the positive case for the quotation
detector) whose content is a PLEDGE ("Each of us has pledged…") — the
commitment modality again. partnership + quotation + commitment stacked in
two sentences.

**Component candidates:** partners grid/logo block, "who's involved"
sidebar, collaborative profile card.

**Market-research kicker, squared:** funding_event gives the money graph;
partnership gives the relationship graph. Across a corpus: who works with
whom, who convenes, who joins — sector network maps from published
reports.


