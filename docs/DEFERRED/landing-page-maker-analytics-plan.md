# DEFERRED · Landing Page Maker analytics and session review

**Status:** deferred until signup, accounts, and per-user projects exist.  
**Primary scope:** Landing Page Maker (LPM). The rest of the site follows after
the LPM event model, identity model, and review tools have proved useful.  
**Goal:** understand how people arrive, what they try, where they struggle, how
their draft changes, and what they ultimately export—without depending on SPA
pageviews or collecting document content when content capture is disabled.

## Decisions already made

- The product will be multi-user. This plan assumes signup, authentication, a
  stable internal `user_id`, and user-owned projects already exist.
- Analytics is first-party and runs on our infrastructure. Data is not sent to
  Google Analytics or another third-party analytics service.
- Review is a structured event timeline, not video/session replay.
- Content capture is a per-user mode:
  - `metadata_only` is the production default. It records structure, choices,
    counts, timing, errors, and edit magnitude, but not entered/generated text.
  - `full_content` is explicitly enabled for a consenting research participant.
    It permits content-bearing project checkpoints and before/after diffs.
- “Demographics” means device and technical context plus coarse geography—not
  inferred or declared personal traits.
- Exact product definitions such as “tried a preview” may be settled later.
  Collection must preserve the lower-level facts needed to revise those
  definitions without re-instrumenting the product.

## Outcome

When this work is complete, we should be able to answer questions such as:

- Which acquisition source first brought each user to the site?
- Which later referrers or campaigns brought them back?
- On which visit did they sign up, and how many earlier visits did they make?
- Which templates, blocks, block options, images, variants, and page settings do
  people choose, preview, replace, reset, or remove?
- How many alternatives do they explore before exporting?
- How much focused working time do they spend overall and in each workflow stage?
- How much of the generated copy do they edit in the final editing stage?
- Where do they loop, cancel, undo, encounter errors, wait, or abandon the flow?
- What exactly happened in an individual research session, with content visible
  only when that participant's capture mode allowed it at that moment?

## Recommended architecture

Use the application database as the canonical analytics store:

```text
React SPA
  explicit interaction events + semantic Puck state diffs
             |
             v
FastAPI first-party collection endpoint
  authentication, validation, privacy filtering, enrichment, deduplication
             |
             v
PostgreSQL analytics schema
  visitors / visits / sessions / events / revisions / content checkpoints
       |                                      |
       v                                      v
Metabase (aggregate reports)          Custom review interface
read-only database role               session and project timelines
```

This is intentionally not a generic clickstream recorder. Explicit events tell
us user intent; semantic editor-state diffs catch real changes even if a UI path
was overlooked. Critical outcomes such as signup, successful saves, generated
variants, and exports are also emitted by the server so a closed tab, blocked
request, or client bug cannot invent success.

### Technology recommendation

1. **PostgreSQL is the source of truth.** Use ordinary typed columns for common
   filtering and a versioned `jsonb` properties field for event-specific data.
   PostgreSQL recommends `jsonb` for most applications and supports indexing it.
   Start with a normal table; add monthly time partitions when event volume or
   retention deletion warrants it. PostgreSQL supports declarative range
   partitioning and partition pruning.
2. **Build the collector in FastAPI and a small client module in React.** This is
   less machinery than adopting a second analytics identity/session model and is
   necessary anyway for privacy enforcement, project revisions, and review.
3. **Self-host Metabase Open Source for aggregate dashboards.** Connect it with a
   dedicated read-only PostgreSQL role and expose curated analytics views rather
   than raw content-bearing tables. Metabase supports self-hosting, PostgreSQL,
   SQL questions, dashboard filters, and dashboards.
4. **Build the structured review interface in the RK3 app.** Generic BI tools are
   suitable for cohorts and funnels, but not for reconstructing one editor session
   with revisions, diffs, research notes, and content permissions.

Umami is a reasonable self-hosted option for lightweight public-site analytics:
it supports SPA navigation, referrers, device/country data, UTMs, custom events,
funnels, and distinct IDs. Do not make it the LPM source of truth. Its tracker is
optimized for analytics properties (including a 500-character string limit and
50-property object limit), not versioned editor revisions or selectively stored
content. Running it alongside the canonical collector would also create two
definitions of visits and attribution. Reconsider it only if the public marketing
site later needs a separate low-effort analytics surface.

Current references:

- [PostgreSQL JSON types and indexing](https://www.postgresql.org/docs/18/datatype-json.html)
- [PostgreSQL declarative partitioning](https://www.postgresql.org/docs/18/ddl-partitioning.html)
- [Metabase documentation and self-hosting](https://www.metabase.com/docs/latest/)
- [Metabase recommendation for a read-only database user](https://www.metabase.com/docs/latest/databases/users-roles-privileges)
- [Umami capabilities](https://docs.umami.is/docs)
- [Umami tracker and event-data limits](https://docs.umami.is/docs/tracker-functions)

## Core measurement model

Keep these concepts distinct. Conflating them will make time, attribution, and
editor behavior reports disagree.

| Concept | Meaning |
|---|---|
| Visitor | A browser identity created before signup with a random first-party ID. It contains no email or fingerprint. |
| Visit | A site visit used for acquisition and the visits-to-signup count. A new visit begins after the configurable inactivity boundary (start with 30 minutes). |
| User | The stable signed-in account identity. Signup links the current visitor history to this ID. |
| Work session | A period of active LPM work, scoped to a user and usually a project. It may be shorter than a visit. |
| Project | The user-owned landing-page project/document being edited. Do not use the current global document slug as ownership. |
| Draft revision | A logical, semantic editor change. It is not an autosave request and not every keystroke. |
| Event | An immutable observed fact: an intent, result, error, lifecycle change, or derived exposure. |
| Checkpoint | A reconstructable project state captured at meaningful boundaries. It is structural in `metadata_only` and may include content in `full_content`. |
| Metric | A versioned interpretation of events, such as “option tried” or “draft abandoned.” Metrics can change without rewriting raw history. |

## Identity, first touch, returning visits, and signup

### Anonymous visitor identity

- On the first eligible request, issue a secure, first-party, same-site cookie
  containing a random UUID. Sign or MAC it; do not encode user data in it.
- Never fingerprint visitors. Do not combine fonts, canvas, installed software,
  IP, or similar signals to re-identify a deleted or cookie-cleared visitor.
- After signup, keep the anonymous visitor record and create an explicit identity
  link to `user_id`; do not rewrite old event rows.
- If a signed-in user appears with a new browser visitor ID, link it prospectively.
  Reports for a user may union all linked visitor IDs while preserving which
  device/visitor produced each event.

### Visit bootstrap

Call a same-origin `/api/analytics/bootstrap` endpoint once on application load
and again when the inactivity boundary has elapsed. It should atomically:

1. resolve or create the visitor;
2. resolve or create the current visit;
3. increment the visitor's `visit_count` only when a new visit is created;
4. store the immutable first-touch acquisition values if this is visit 1;
5. store acquisition values for this visit, including direct/none;
6. append a touchpoint when a new external referrer or campaign is present;
7. return `visitor_id`, `visit_id`, `visit_ordinal`, `session_id`, server time,
   effective capture mode, and event-schema version.

Use a database transaction and uniqueness constraint so reload races cannot
increment the visit count twice.

### Acquisition fields

For the first visit and every subsequent visit, collect:

- landing origin and path;
- external referrer domain and normalized URL;
- `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, and
  any later explicitly allowlisted campaign keys;
- known ad-click identifiers only if there is a defined reporting need and
  retention rule;
- occurred time, visit ordinal, and whether the touch was direct, referral,
  organic, campaign, or unknown.

Strip fragments, credentials, authentication/reset tokens, and non-allowlisted
query parameters before storage. Referrer query strings can contain personal or
sensitive data; default to domain plus path and retain only reviewed campaign
parameters.

The first-touch fields are immutable. Later touchpoints never overwrite them.
Keep per-visit acquisition as well so first-touch, last-non-direct, and full-path
attribution can be computed separately.

### Signup linkage and the requested report

The authoritative `signup_completed` event is written by the signup transaction,
not by a client button click. Store the current `visit_id` and `visit_ordinal` on
it. Publish an analytics view with:

- user ID and signup time;
- first visit time;
- first referrer domain/normalized URL;
- first UTM values;
- `prior_visits = signup_visit_ordinal - 1`;
- `signup_visit_number = signup_visit_ordinal`;
- days from first visit to signup;
- the referrer/campaign on the signup visit.

Providing both prior visits and inclusive visit number removes ambiguity in
“how many visits before signup.” A person who signs up on the first visit has
`prior_visits = 0` and `signup_visit_number = 1`.

### Consent constraint

The product cannot recover a person's true first visit at signup unless it stored
a stable pre-signup identifier and acquisition record at that first visit. The
public notice must therefore cover this minimal first-party acquisition tracking.
At signup, record acceptance of the current analytics/privacy notice and obtain
separate explicit consent before enabling `full_content` research capture.

Before launch, confirm the exact cookie/consent presentation for the jurisdictions
served. If prior opt-in is legally required, do not set the visitor cookie before
opt-in; reports must then label the observed first visit as “first consented
visit,” not claim it is necessarily the person's first site visit.

## Storage design

Names are illustrative; settle them with the account/project schema.

### Identity and acquisition tables

- `analytics_visitors`
  - `id`, `first_seen_at`, `last_seen_at`, `visit_count`
  - immutable first-touch referrer and UTM columns
  - first coarse geo/device fields
- `analytics_identity_links`
  - `visitor_id`, `user_id`, `linked_at`, `reason`
- `analytics_visits`
  - `id`, `visitor_id`, optional `user_id`, `ordinal`
  - `started_at`, `last_activity_at`, `ended_at`
  - landing path, normalized referrer, UTM fields, acquisition class
  - coarse country/region, device class, browser family, OS family, language,
    viewport bucket; keep versions where parsers/classifiers can change
- `analytics_touchpoints`
  - one row per meaningful referrer/campaign touch, linked to its visit

### Product-use tables

- `analytics_work_sessions`
  - `id`, `visit_id`, `user_id`, `project_id`
  - start/end, active seconds, idle seconds, heartbeat completeness, exit reason
- `analytics_events`
  - immutable `event_id` UUID supplied by the client for idempotency
  - schema version, event name, client occurrence time, server receipt time
  - visitor/user/visit/work-session/project IDs
  - workflow stage, draft revision, capture mode at occurrence
  - typed common dimensions plus validated `properties jsonb`
- `analytics_project_revisions`
  - revision ID/number, parent revision, reason/event, structural hash
  - block inventory/order and content-free edit summary; the structural hash is
    computed only from block structure and approved categorical settings, never text
- `analytics_content_checkpoints`
  - only rows permitted by `full_content`
  - encrypted serialized state or encrypted content-bearing diff
  - project/revision/session linkage, key version, expiry time
- `analytics_capture_preferences`
  - user ID, `metadata_only|full_content`, effective time, consent version/time,
    changed-by, optional research-study ID, expiry
- `analytics_review_annotations`
  - reviewer bookmarks, pain/error labels, notes, status, and linked events/range

Put identity/account data outside event properties. Content-bearing data belongs
in the separate checkpoint table so reporting credentials can be denied access
at the database level.

### Event envelope

Every client event should follow one versioned envelope:

```json
{
  "event_id": "uuid",
  "schema_version": 1,
  "name": "lpm.block_added",
  "occurred_at": "ISO-8601",
  "visit_id": "uuid",
  "work_session_id": "uuid",
  "project_id": "uuid",
  "workflow_stage": "assemble",
  "draft_revision": 14,
  "properties": {
    "block_id": "stable-instance-id",
    "block_type": "findings",
    "source": "library_drag",
    "position": 4
  }
}
```

The server derives `user_id` from authentication, verifies project ownership,
overrides the effective capture mode, rejects unknown event/property combinations,
and adds server context. Never trust a client-supplied user ID, consent mode, or
successful outcome.

## Client collection layer

Create one small analytics client rather than scattering `fetch()` calls through
components. It should provide:

- `track(name, properties)` for an explicit intent;
- `trackResult(name, properties)` for a client-observed result/error;
- work-session lifecycle and active-time tracking;
- an in-memory queue with small batches;
- idempotent event UUIDs and bounded retry;
- `sendBeacon`/`fetch(..., {keepalive: true})` flush on `pagehide` and visibility
  changes;
- automatic current visitor/visit/session/project/stage/revision context;
- development logging that shows the sanitized payload and effective capture mode;
- a single privacy transformer used before anything enters the queue.

Do not put content into a queued event and plan to redact it on the server. The
browser should omit it in `metadata_only`, and the server should independently
enforce the same allowlist as defense in depth.

## Measuring active work time

Elapsed wall-clock time overstates editing when a tab is left open. Track active
time using a small state machine:

- active only while the page is visible and focused and the user has interacted
  within the idle threshold (start with 60 seconds, version the definition);
- interactions include pointer, keyboard, drag, editor field changes, and modal
  actions, rate-limited so they are not individual analytics events;
- send a heartbeat approximately every 30 seconds only while active;
- close the active interval on blur, hidden, idle, project switch, logout, and
  `pagehide`;
- cap any missing interval server-side so a lost close event cannot create hours
  of work;
- report both wall time and derived active time, with a completeness flag.

Attribute active intervals to workflow stage and project so reports can separate
setup, generation/waiting, assembly, preview, and final editing.

## Instrumenting Landing Page Maker

### Two complementary signals

1. **Explicit command events:** instrument the handlers that know intent—for
   example template switch, reset, modal cancel, block remove, viewport choice,
   copy-site scan, and export.
2. **Semantic state diffs:** at the central Puck `onChange`, compare the prior and
   next normalized state and classify block add/remove/reorder/nesting and field
   changes. This catches edits from drag-and-drop, content-editable fields, Puck
   internals, and future controls.

The diff must ignore transient UI state, generated IDs, save timestamps, and
equivalent HTML formatting. Autosaves are operational events; they do not create
product “tries.” Coalesce typing into a field-edit session ending on blur, modal
Done/Cancel, block selection change, stage change, or a short idle timeout.

### Stable identifiers and baselines

- Give every project, block instance, revision, and option exposure a stable ID.
- Persist the initial generated draft as revision 0. All edit measurements need a
  baseline that is not overwritten by autosave.
- Record a structural checkpoint at editor load, stage transitions, template
  replacement/reset, successful generation, before export, after export, and
  graceful session end.
- Record the current template/generator/prompt/config version on the baseline so
  behavior can be compared across product changes.

### Interaction inventory

The implementation pass must walk the actual UI and cover every interaction in
these families. Event names below are examples, not a frozen schema.

#### Entry and lifecycle

- project created, opened, resumed, switched, and left;
- editor load requested/succeeded/failed and load duration;
- workflow stage entered/exited, including final editing;
- tab hidden/restored, inactivity, work-session ended, and exit reason when known;
- navigation away with unsaved work or unfinished generation.

#### Templates, generation, and source choices

- content settings opened/closed;
- template/archetype selected, applied, replaced, reset, or reverted;
- AI/guidance generation requested, completed, failed, timed out, retried, or
  cancelled, including model/config version and latency but no prompt text;
- summary style/length or other generated variant requested and returned;
- document section, image, or source asset selected/replaced/cleared;
- generated recommendation accepted unchanged, edited, removed, or restored.

#### Blocks and composition

- block-library item drag started/cancelled/dropped;
- block added, selected, configured, duplicated (when available), reordered,
  nested/unnested, or removed;
- block configuration opened and finished, cancelled, or removed from the modal;
- configuration cancellation records that changes were reverted, without counting
  the temporary values as final edits;
- nested media slot insert/remove/reorder;
- undo/redo when the editor exposes it;
- resulting ordered block-type inventory at checkpoints.

#### Field and content editing

- field edit started/committed/reverted, keyed by block type, block ID, stable
  field key, control type, and input source (modal, inline, generated resolver);
- enumerated option old/new values, including summary style/length, document
  section, image choice, network, button style, PDF source mode, and similar;
- text metrics: initial/final character and word counts, inserted/deleted character
  estimates, formatting operations, paste indicator, and whether the field changed;
- array item added/removed/reordered and item count;
- validation error shown/cleared and invalid attempts;
- rich-text changes normalized so harmless serialization differences are ignored.

In `metadata_only`, never store typed text, generated copy, URLs entered into
fields, image alt/caption text, document section text, or clipboard contents.
Categorical values from a reviewed allowlist are safe; freeform values are not.
For a URL field, record only state such as empty/non-empty, validity, and optionally
the destination's coarse class (same-site/external), not the URL.

#### Page setup and visual preview

- page setup opened, done, or cancelled;
- content width and color choices changed; metadata-only color values may be kept
  if approved, as they are product settings rather than document content;
- left/right sidebar and header/footer simulation toggled;
- Copy My Site toggled; scan requested/succeeded/failed/retried and latency;
- viewport changed between mobile/laptop/desktop;
- zoom changed/reset-to-fit;
- preview/canvas became visible after a semantic revision;
- scroll depth or block exposure only if it answers a defined question; do not
  collect high-frequency pointer movement or generic DOM clicks.

#### Persistence, errors, and completion

- autosave requested/succeeded/failed, revision saved, conflict detected/resolved,
  and latency; sample routine successes if volume is high, but keep all failures;
- API/JavaScript errors with normalized error code, surface, release/build ID, and
  request correlation ID—no stack values or messages containing user content;
- export requested, server/client build succeeded/failed, download initiated, and
  project revision exported;
- publish/complete actions when those replace or supplement export;
- server events for durable save, generated output, signup, and completed export.

### “Previewed,” “tried,” “discarded,” and “kept”

Do not emit these as unquestioned facts initially. Emit the underlying semantic
choice and exposure events, then calculate versioned classifications.

An initial definition to test:

- **Choice:** an option or structural state became the current draft state.
- **Previewed:** that revision was visible in the canvas while the tab was active
  for at least two seconds after rendering completed.
- **Tried:** a distinct choice was previewed; repeated selection of the same value
  without an intervening alternative is one try.
- **Discarded:** a tried choice was replaced/reverted/removed and is absent from
  the exported or final revision.
- **Kept:** the choice is present in the exported/final revision.
- **Abandoned:** the choice was current when the work session ended but no final
  revision was produced within the attribution window.

Store the metric-definition version with derived tables. Adjusting the exposure
duration or finalization window should require recomputation, not new collection.

### Measuring final-stage editing

Instrument an explicit `workflow_stage_entered` event; do not infer the final stage
from page titles or route names. At entry, save a baseline checkpoint. At every
export/publish, compare the current revision with that baseline.

Report at least:

- number and share of content-bearing fields touched;
- blocks with any content edit and blocks left unchanged;
- total edit sessions and active editing seconds;
- initial/final character and word counts plus additions/deletions;
- generated blocks retained unchanged, edited, or removed;
- structural changes made during the final stage;
- in `full_content`, readable before/after diffs and normalized text similarity;
- in `metadata_only`, only counts, booleans, deltas, and non-content structural
  fingerprints; never hash the text itself.

## Per-user content-capture mode

### Behavior

- Default every user to `metadata_only`.
- Provide an obvious account/research setting showing the effective mode and what
  it captures. Do not hide full-content recording behind vague “analytics” copy.
- Enabling `full_content` requires a specific consent action, consent-document
  version, timestamp, optional study identifier, and optional automatic expiry.
- Mode changes apply immediately to future events and checkpoints and are recorded
  as audit events. Every stored event/checkpoint carries the effective mode.
- Turning capture off does not silently erase previously consented data because
  that would break an active study; provide a separate, easy “delete previously
  captured content” action and honor account deletion/withdrawal policy.

### Enforcement

Create a schema-level field classification registry:

- `categorical`: safe reviewed enum/value;
- `metric`: count, length, duration, boolean, coarse bucket;
- `freeform`: user or generated content;
- `secret`: password, token, credential, signed URL—never collect in any mode.

Use the registry in client payload construction, server validation, tests, and
review rendering. Unknown properties are rejected, not stored opportunistically.
Full content goes only into encrypted checkpoints/diffs, never into ordinary
event properties, logs, exception reporting, or Metabase-accessible views.

## Structured review interface

Build this under an owner/researcher-only route protected independently from
ordinary user access.

### Session finder

Allow filtering by:

- date range, user/research participant, visitor, project, visit, and session;
- acquisition source/campaign and first-touch source;
- workflow stage reached, export/publish outcome, and signup cohort;
- capture mode;
- device class/browser/viewport bucket;
- errors, repeated retries, cancellation, abandonment, unusually long/short
  active time, many discarded tries, or large final-stage edits;
- app release, event-schema version, template, and generator/prompt version.

Each result row should summarize first touch, visit ordinal, active time, project,
stage reached, tries/discards, errors, final action, capture mode, and any reviewer
labels.

### Timeline view

Render a chronological, collapsible timeline grouped into readable episodes:

- visit/acquisition and signup context;
- work-session start/end and active/idle spans;
- workflow stage bands;
- template/generation operations with durations;
- block additions, removals, moves, and option explorations;
- coalesced field-edit sessions rather than keystrokes;
- preview exposures and which choices were later kept/discarded;
- saves, errors, retries, cancellations, exports, and abandonment;
- project checkpoints with a structural block-outline diff;
- full before/after content only when that checkpoint was captured in
  `full_content` and the reviewer has content-review permission.

Provide toggles for “all events” versus a default narrative view. Always show
event time, active-time offset, workflow stage, revision, source (client/server),
and capture mode. Mark gaps caused by offline/lost events instead of presenting a
false continuous narrative.

### Project state panel

At a selected event/revision, show:

- ordered block outline, types, nested relationships, and categorical options;
- additions/removals/moves versus the previous checkpoint;
- text length/edit summaries in metadata-only sessions;
- readable content and before/after diffs in permitted full-content sessions;
- the revision ultimately exported so the reviewer can compare an explored state
  with the outcome.

The review UI does not need pixel-perfect replay. Its purpose is to make choices,
state transitions, and pain visible without reproducing every cursor movement.

### Research notes and pain signals

- Let reviewers bookmark an event or time range, add a note, assign labels, and
  mark a finding resolved/expected/actionable.
- Suggested pain labels: confusing choice, repeated attempt, unexpected reset,
  validation, generation quality, wait/performance, save failure, export failure,
  navigation/wayfinding, abandonment, and accessibility.
- Automatically flag candidate pain patterns but do not call them errors without
  review: rapid add/remove, repeated option cycling, reset after long editing,
  multiple modal cancels, repeated invalid input, repeated generation, save/export
  failures, long active pauses around a control, and exit after an error.
- Export a reviewed research-session summary without exposing content from
  metadata-only sessions.

### Review access and auditing

- Separate permissions for aggregate analytics, session metadata review, and
  content-bearing research review.
- Audit every view of full-content checkpoints, including reviewer, time, user,
  project, and study.
- Never expose raw content through broad search, dashboard tools, exports, logs,
  or APIs used by aggregate reports.

## Aggregate reports and dashboards

Create stable SQL views/materialized views in an `analytics_reporting` schema.
Metabase receives read-only access to this schema only.

### Acquisition and signup

- requested first-touch signup report;
- signups by first-touch source/campaign and by signup-visit source/campaign;
- distribution of prior visits and days to signup;
- return touchpoints/campaigns before signup;
- landing path to signup funnel;
- unknown/direct attribution and cookie-loss rate indicators.

### LPM funnel

- signed up → project created → document ready → LPM opened → generated draft
  viewed → meaningful edit → preview → export/publish;
- conversion and median active time between stages;
- abandonment at each stage;
- breakdown by first-touch source, device class, template, release, and document
  characteristics where safe.

### Choice and exploration

- template and block-type selection/retention rates;
- option choices, tries per control, previewed candidates, discard rate, and final
  retained choice;
- blocks most often added then removed;
- generated variants requested per accepted/exported variant;
- viewport use and whether mobile preview was checked before export;
- reset, cancel, undo, and repeated-choice rates.

### Effort and editing

- wall time and active time by stage;
- sessions/visits needed before first export;
- final-stage fields touched, length deltas, generated-content retention, and
  structural changes;
- distributions rather than averages alone; segment out exceptionally long idle
  or incomplete sessions;
- relationship between exploration/edit effort and export/publish completion.

### Reliability and pain

- generation, save, scan, and export failure rates and latency percentiles;
- errors by release/browser/device/control;
- repeated retries and recovery rate;
- sessions flagged by candidate pain heuristics and reviewer-confirmed pain labels;
- event loss, duplicate rejection, late delivery, invalid payload, and missing
  context rates.

## Privacy, security, and retention baseline

Adopt conservative defaults and make final periods configuration, not code:

- never store raw passwords, auth/session tokens, reset links, API keys, cookies,
  clipboard contents, or arbitrary URL query strings;
- do coarse GeoIP enrichment at ingestion and discard the raw IP; store country
  and, if useful and sufficiently non-identifying, region—not precise location;
- parse browser/OS/device and avoid retaining the raw user-agent indefinitely;
- encrypt content checkpoints with a separable key and rotate keys;
- production default is metadata-only; full content has an automatic study expiry;
- suggested starting retention: aggregate events 18 months, visitor acquisition
  18 months or account lifetime (whichever policy chooses), full-content research
  checkpoints 90 days maximum unless a study explicitly needs less/more;
- support deletion by user, visitor, project, study, and date partition;
- on account deletion, remove identity links and content per policy; do not leave a
  user-reconstructable timeline mislabeled as anonymous;
- exclude known staff/test users and automated checks from product reports while
  optionally keeping them in a clearly marked test dataset;
- redact analytics payloads from application request logs and error logs;
- back up and restore analytics with the same discipline as account/project data.

First-party hosting reduces data sharing; it does not remove notice, consent,
access-control, retention, or deletion obligations.

## Event governance and data quality

Create a checked-in event catalog, for example `analytics/events.yml`, containing:

- event name, owner, description, source (`client|server|derived`), schema version;
- required/optional properties and type;
- field privacy class;
- when the event fires and when it explicitly must not fire;
- deduplication key and server counterpart if any;
- examples for metadata-only and full-content modes;
- associated metrics/reports and deprecation history.

Rules:

- use stable product concepts, not button labels, CSS selectors, or translated
  copy, in event and property names;
- never repurpose an existing property; add a version or new field;
- record application build/release and schema version on all events;
- validate in CI that emitted event names/properties exist in the catalog;
- provide a development event inspector and an admin data-quality dashboard;
- treat derived metrics as versioned code/SQL under source control;
- maintain a bot/staff/test marker and exclude it explicitly in reporting views.

## Implementation phases

### Phase 0 — prerequisites and measurement workshop

1. Confirm the account, organization, project, document, and membership model.
2. Replace the current shared per-document landing JSON/theme ownership with
   user/project-scoped persistence and revisions. Analytics cannot fix ambiguous
   project ownership.
3. Confirm workflow-stage identifiers, especially the final editing stage and
   the durable completion action (export, publish, or both).
4. Walk every LPM route, modal, field, drag target, async operation, keyboard
   command, error path, cancellation, and exit. Turn the interaction inventory
   above into the initial event catalog.
5. Agree on the first version of active-time and try/preview/discard definitions,
   while keeping them derived and replaceable.
6. Review public notice, pre-signup visitor storage, full-content research consent,
   and retention/deletion wording.

**Exit:** stable IDs and ownership exist; event catalog v1 and privacy classes are
approved; no code instrumentation yet depends on button text or transient UI.

### Phase 1 — identity, acquisition, and collector foundation

1. Add PostgreSQL analytics migrations, constraints, indexes, and reporting schema.
2. Implement visitor cookie, transactional bootstrap, visit/session boundary, first
   touch, subsequent touchpoints, and visit counter.
3. Link visitors to users in the authoritative signup transaction.
4. Implement event batch endpoint, authentication/ownership checks, allowlist
   validation, idempotency, clock-skew handling, and request-size/rate limits.
5. Build the React analytics client, privacy transformer, batching/retry/beacon,
   release context, and development inspector.
6. Add device/language/viewport and local coarse-GeoIP enrichment without storing
   raw IP.
7. Ship the requested first-touch-to-signup SQL view and verify it with scripted
   first visit, returning visit, campaign, and signup scenarios.

**Exit:** first and later acquisition touches survive SPA use and signup linkage;
visit counts are race-safe; no LPM content is collected.

### Phase 2 — LPM semantic instrumentation

1. Add work-session/active-time tracking.
2. Add explicit events at known LPM handlers and server outcome points.
3. Add normalized Puck state comparison at the central change boundary.
4. Add draft revisions and structural checkpoints at meaningful boundaries.
5. Coalesce text editing into sessions and calculate content-free edit metrics.
6. Add canvas exposure events needed to derive previews/tries/discards.
7. Cover failures, retries, cancels, reverts, abandonment, offline gaps, saves, and
   exports—not just happy-path clicks.
8. Add event-contract tests and end-to-end golden journeys.

**Exit:** a development journey can be reconstructed structurally from project
open through export, with active time and no captured text in metadata-only mode.

### Phase 3 — full-content research mode

1. Add per-user capture preference, consent version, expiry, visible setting, and
   immediate mode changes.
2. Add encrypted content checkpoints/diffs and separate content-review permission.
3. Add purge/withdrawal and retention jobs.
4. Test that metadata-only payloads, database rows, logs, errors, and reports contain
   no document/user-entered text, including mode changes mid-session.
5. Test and audit all content access.

**Exit:** a consented test session has readable diffs; switching the same user to
metadata-only immediately produces only structural/quantitative checkpoints.

### Phase 4 — review interface

1. Build session finder and candidate-pain filters.
2. Build grouped timeline with stage/active-time bands and raw-event expansion.
3. Build revision/block-outline comparison and exported-revision comparison.
4. Add permission-gated full-content diffs.
5. Add reviewer bookmarks, labels, notes, and access audit.
6. Conduct several moderated tests and change grouping/definitions based on whether
   reviewers can correctly explain what happened without watching the participant.

**Exit:** an owner can find a session, identify attempts/errors/abandonment, compare
explored and final structure, and review content only when explicitly permitted.

### Phase 5 — aggregate reporting and operating quality

1. Deploy Metabase with its own application database and a read-only RK3 reporting
   connection.
2. Create acquisition, funnel, choices, effort/editing, reliability, and data-quality
   dashboards from curated views.
3. Schedule materialized-view refreshes only after query load warrants them.
4. Add retention, partition maintenance if warranted, backup/restore tests, event
   volume/cost monitoring, and alerts for collector failures/schema rejection.
5. Document metric definitions beside dashboards and show definition version/date.

**Exit:** aggregate numbers reconcile with sampled review timelines and server
outcomes; the analytics system is monitored and deletions are testable.

### Phase 6 — extend beyond LPM

Reuse the visitor, visit, identity, collector, privacy, and reporting foundation.
Create separate event catalogs for other product areas. Do not enable generic
automatic click capture across the site; instrument meaningful domain actions and
add semantic state diffs only where the product has stateful workflows.

## Verification plan

### Automated contract and privacy tests

- unknown events/properties are rejected;
- user/project IDs cannot be spoofed across accounts;
- duplicate `event_id` is idempotent;
- event batches may arrive late/out of order without corrupting revisions;
- metadata-only events/checkpoints contain no seeded sentinel content;
- secret/token URL parameters are stripped;
- switching capture mode mid-session takes effect on the next event;
- content-checkpoint access is denied without the content-review role and logged
  when allowed;
- deletion removes the expected identity, event, annotation, and content rows;
- signup is linked once despite reload/race/retry;
- new visit creation and visit ordinal are race-safe.

### Golden user journeys

Automate and inspect at least these journeys:

1. first direct visit → signup on visit 1;
2. campaign visit → leave → referral return → signup on visit 2;
3. anonymous visits on one browser → signup → signed-in use on another browser;
4. open generated draft → change template twice → reset → export;
5. add, configure, reorder, nest, and remove blocks, including modal cancel/revert;
6. try several summary variants and images, preview them in multiple viewports,
   retain one, and export;
7. edit several content fields in final stage and compare baseline to export;
8. save/generation/scan/export failures followed by retry and recovery;
9. abandon after an error and abandon with no error;
10. repeat journeys in metadata-only and full-content mode, including a mode switch.

For each journey, assert event order only where order is meaningful, server outcome
agreement, active-time bounds, revision/checkpoint reconstruction, derived metric
classification, and expected report rows.

### Manual launch audit

- use the development event inspector while exercising every clickable control,
  field, drag/drop target, keyboard action, cancellation, error, and navigation exit;
- compare a session timeline with direct observation during a moderated test;
- reconcile a sample of dashboard aggregates back to event rows and timelines;
- inspect application/proxy/error logs for accidental content or tokens;
- test supported browsers, background tabs, abrupt closes, offline/reconnect, slow
  generation, back/forward navigation, and multiple concurrent project tabs.

## Initial indexes and scale posture

Start simple and measure. Likely indexes:

- unique event ID;
- events by `(user_id, occurred_at)`, `(project_id, occurred_at)`,
  `(work_session_id, occurred_at)`, and `(name, occurred_at)`;
- visits by `(visitor_id, ordinal)` and signup linkage;
- targeted expression indexes for frequently filtered event properties—not a broad
  GIN index by default;
- checkpoint lookup by project/revision/session and expiry.

Do not introduce ClickHouse, Kafka, or a warehouse initially. If PostgreSQL event
writes or dashboard queries become a measured constraint, first add batching,
reporting views/materialization, retention, and monthly partitions. A separate
warehouse is a later migration target because the canonical event envelope and
IDs are already independent of storage.

## Questions deliberately deferred until execution

- final visit inactivity threshold and whether campaign arrival always forces a
  new visit;
- exact preview exposure duration and abandonment/finalization window;
- final workflow stage names and whether export, publish, or an explicit Done action
  is the durable completion event;
- exact coarse geography granularity and GeoIP database;
- final retention periods and research-study expiry;
- event sampling thresholds for routine autosave/performance successes;
- whether staff can enable full-content mode for a participant or only the
  participant can, and the precise withdrawal behavior;
- when data volume justifies partitioning/materialized views;
- whether the later marketing site benefits enough from Umami to justify a second,
  clearly separated analytics surface.

These do not block the architecture. They should be decided before the associated
phase and recorded in the event catalog/metric definitions rather than embedded
as unexplained constants.
