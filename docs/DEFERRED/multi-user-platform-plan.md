# DEFERRED · Multi-user platform, teams, entitlements, and billing

**Status:** proposal only; implementation is deferred.  
**Written:** 2026-07-18.  
**Immediate product priority:** launch a functional Landing Page Maker (LPM)
that requires a free account. Team management and paid signup follow without
requiring a second account-system redesign.

## Recommendation

Evolve RK3 into a multi-tenant modular monolith. Do not rewrite it as
microservices.

Use:

- React and FastAPI for the product application;
- self-hosted Keycloak for credentials, login, verification, recovery, MFA,
  and identity sessions;
- PostgreSQL as the source of truth for users, workspaces/teams, roles,
  products, entitlements, projects, billing state, jobs, audit events, and
  analytics;
- private S3 storage for uploaded documents and generated artifacts;
- a durable worker queue for PDF conversion and AI work;
- Stripe Checkout, Billing, and Customer Portal only when paid signup launches;
- EC2 initially, with RDS PostgreSQL, S3, and SES.

Keep teams, subscriptions, tool access, and projects in the application
database—not in Keycloak or Stripe. This preserves a realistic path to replace
either service later.

```text
                        Keycloak
                identity / recovery / MFA
                            |
                            v
Browser -> FastAPI backend-for-frontend -> PostgreSQL
           secure session cookie           users
           authorization                   workspaces / memberships
           product API                     plans / entitlements
                  |                         projects / jobs / audit
                  |
                  +----> private S3
                  |      sources / artifacts / exports
                  |
                  +----> worker queue -> conversion/AI workers
                  |
                  +----> Stripe later
                         payment and subscription events
```

## Where the application is now

This is a larger transition than adding authentication. The current application
has five fundamental single-user assumptions:

1. Documents are discovered by scanning one shared `sources/` directory, and
   document identity comes from folder and filename rather than a database
   record (`rk3/documents.py`).
2. User-editable LPM state is stored in sidecar JSON files beside the source
   PDF (`app/main.py`).
3. Conversion status and concurrency are tracked in process-memory sets. A
   restart loses that coordination state.
4. Generated files are exposed through a public
   `/output/<engine>/<slug>` path. The frontend fetches IR and preview assets
   directly rather than through an ownership check (`app/ui/src/api.js`).
5. Admin screens are client-side sentinel selections in the same SPA; there is
   no server-enforced admin boundary (`app/ui/src/App.jsx`).

There is also no upload flow, database, account model, team model, durable job
queue, billing model, or private asset-delivery mechanism.

The conversion pipeline, LPM generation, rendering, content extraction, and
much of the React UI can remain. Their surrounding storage and execution
context must change.

## Keep three concepts separate

### Identity

Who is this person?

- Password and login methods
- Email verification
- Password recovery
- MFA/passkeys
- Login sessions
- External identity-provider links

This belongs in Keycloak.

### Authorization

What may this person do in this workspace or project?

- Workspace owner
- Billing administrator
- Administrator
- Editor
- Viewer
- Platform administrator/support roles

This belongs in the application database.

### Entitlements

Which products and capabilities has the workspace obtained?

- Landing Page Maker
- RK Express
- Future tools
- Usage quotas
- Paid features
- Trials
- Bundles
- Temporary grants

This also belongs in the application database.

A role must not imply a subscription, and a subscription must not imply
permission. An editor might have permission to operate LPM, but the workspace
must also have an LPM entitlement.

## Account and team model

Call the tenant a `workspace` internally, even if the UI calls it a team or
organization.

Every signup gets a personal workspace with one owner. This avoids separate
“individual account” and “team account” implementations. A personal workspace
can later invite members or be renamed.

Core records:

```text
users
  id
  identity_subject       # Keycloak/OIDC subject
  email/display profile
  platform status

workspaces
  id
  name
  type                   # personal | team
  status

memberships
  workspace_id
  user_id
  role                   # owner | billing_admin | admin | editor | viewer
  status

invitations
  workspace_id
  email
  role
  token hash
  invited_by
  expires_at
  accepted_at

workspace_groups         # later, if departments/project groups are needed
group_memberships

projects
  id
  workspace_id
  tool_key               # lpm | rk_express | future tool
  status
  version

documents
artifacts
project_revisions
jobs
```

A user may belong to several workspaces and switch between them. Projects
belong to workspaces, not directly to users.

For the initial free LPM launch, the UI can hide team creation entirely. The
schema still begins with a one-member personal workspace, so enabling
invitations later is additive.

## Identity-provider options

| Option | Fit | Assessment |
|---|---|---|
| Self-hosted Keycloak | Best overall fit | Recommended |
| Self-hosted ZITADEL | Strong alternative | Worth a proof of concept |
| Logto OSS | Attractive UX but notable OSS limitation | Not recommended here |
| Application-written auth | Maximum control | Too much security-sensitive work |
| Auth0/Clerk/WorkOS | Fastest managed route | Conflicts with the dependency preference |

### Keycloak

Keycloak provides self-registration, email verification, password recovery,
roles, groups, organization membership, invitation management, admin events,
OIDC, SAML, and identity brokering. Its current organization support includes
invitations and organization-scoped groups.
[Keycloak administration documentation](https://www.keycloak.org/docs/latest/server_admin/)

Use it primarily for identity. Keep product workspaces and permissions in RK3
because:

- workspace billing and entitlements are application concepts;
- team changes need to participate in application transactions;
- Keycloak remains replaceable through standard OIDC;
- subscription state does not have to be synchronized into identity tokens;
- membership or billing changes take effect immediately rather than waiting for
  token expiry.

Use OIDC Authorization Code with PKCE, but place FastAPI in a
backend-for-frontend role:

- FastAPI performs the code exchange;
- the browser receives an `HttpOnly`, `Secure`, same-site session cookie;
- OIDC tokens remain server-side, not in `localStorage`;
- state-changing requests receive CSRF protection;
- the local `users` row is created or refreshed from the stable OIDC subject.

### ZITADEL

ZITADEL is more organization-oriented and includes self-service registration,
profile management, account deletion, MFA/passkeys, organization
administrators, and delegated multi-tenant management. It can also be
self-hosted.
[ZITADEL self-service documentation](https://zitadel.com/docs/concepts/features/selfservice)

It is a credible alternative if its UX and operating model feel better in a
small prototype. Its current AGPL licensing deserves legal review for the
intended distribution/deployment model.
[ZITADEL licensing FAQ](https://help.zitadel.com/zitadel-licensing-faqs)

### Why not Logto OSS

Logto has polished account-center and organization APIs, but its current
self-hosted OSS documentation says it supports only one administrative account.
That is an awkward limitation for the platform-management requirements.
[Logto OSS documentation](https://docs.logto.io/logto-oss/get-started-with-oss)

## Multi-product and subscription model

Do not create a single `account_level` column.

Use a product catalog:

```text
tools
  lpm
  rk_express
  future_tool_x

plans
  lpm_free
  lpm_pro
  rk_express_pro
  all_tools_pro

plan_versions
plan_entitlements
subscriptions
subscription_items
entitlement_grants
usage_ledger
```

A plan version grants feature keys such as:

```text
lpm.access
lpm.projects.max = 5
lpm.pages_per_document.max = 150
lpm.ai_generations.monthly = 20
lpm.team_editing
rk_express.access
```

Access becomes:

```text
authenticated user
+ active workspace membership
+ role permits action
+ workspace entitlement permits tool/feature
+ quota remains
= allowed
```

Bundles can grant several tool entitlements. A customer can also hold multiple
subscription items. Future tools do not require redesigning the account system.

Trials and manual grants should use the same entitlement system:

- `source = free_plan | subscription | trial | discount | admin_grant`
- `valid_from`
- `valid_until`
- `reason`
- `provider_reference`

This makes timed trials possible before Stripe exists and lets support grant
temporary access without fabricating billing records.

## Paid accounts

For the first free launch, do not integrate Stripe. Give every new personal
workspace an `lpm_free` entitlement.

When paid signup is ready, direct Stripe integration is the right first step:

- Stripe Checkout for starting paid subscriptions;
- Stripe Customer Portal for payment methods, invoices, cancellation, and
  upgrades/downgrades;
- promotion codes for discounts;
- signed webhooks for authoritative subscription changes;
- internal entitlement projection based on webhook state.

Stripe’s customer portal supports subscription changes, cancellations, payment
methods, tax IDs, and invoices.
[Stripe Customer Portal](https://docs.stripe.com/customer-management)
Promotion codes support eligibility, expiry, and redemption limits.
[Stripe discounts and promotion codes](https://docs.stripe.com/billing/subscriptions/coupons)

Never grant paid access solely because the browser returned from Checkout.
Stripe subscription activity is asynchronous; process and verify webhooks.
[Stripe subscription webhooks](https://docs.stripe.com/billing/subscriptions/webhooks)

Recommended behavior:

- upgrades are normally effective immediately after confirmed payment;
- downgrades are scheduled for the next renewal;
- cancellation retains access through the paid-through date unless explicitly
  immediate;
- failed renewal gets a configurable grace period, then restricted access
  without deleting projects;
- seat reduction is scheduled and excess members are identified before renewal;
- free accounts do not receive Stripe customers until entering a paid flow.

Keep Stripe IDs and raw provider-event records, but map them to internal
subscriptions and entitlements. This makes migration possible even though
moving stored card credentials between processors is never completely
frictionless.

### Lago

Lago is useful if pricing later becomes complicated—usage billing, many
products, multiple payment processors, or invoice-heavy enterprise contracts.
It supports self-hosting, plans, trials, coupons, entitlements, usage events,
and Stripe payments.
[Lago documentation](https://getlago.com/docs/guide/introduction/welcome-to-lago)

It is premature for the free launch and initial straightforward subscriptions.
It would add another critical service while Stripe still processes payments.
Reconsider it when billing complexity is demonstrated rather than anticipated.

## Project and document persistence

Move structured state into PostgreSQL:

- project metadata and ownership;
- LPM assembled state;
- theme/configuration;
- autosave revision number;
- current revision;
- edit lease or optimistic concurrency version;
- job and processing status;
- usage counts;
- AI-generation metadata and cost.

Keep large binary/generated assets in private object storage:

```text
workspaces/<workspace-id>/
  projects/<project-id>/
    documents/<document-id>/source.pdf
    runs/<run-id>/ir.json
    runs/<run-id>/pages/...
    runs/<run-id>/images/...
    exports/<export-id>/landing.zip
```

The S3 bucket remains private. The API checks membership and entitlement before
issuing short-lived download/upload URLs. AWS supports time-limited presigned
uploads and downloads without giving users AWS credentials.
[AWS S3 presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)

Do not place workspace or user-supplied identifiers directly into paths. Use
generated UUIDs.

For simultaneous team editing, do not start with CRDTs. Use:

- project revision numbers/ETags;
- optimistic concurrency on save;
- a visible editing lease or conflict message;
- immutable checkpoints before destructive resets and exports.

Real-time co-editing can follow if there is demonstrated demand.

## Preserving the conversion pipeline

The pipeline can continue to believe it works in a directory. A worker will:

1. Claim a database job.
2. Create an isolated temporary workspace.
3. Download the source and relevant configuration from storage/database.
4. Run the existing pipeline against that workspace.
5. Upload outputs to private object storage.
6. Commit run/artifact metadata and status.
7. Remove the temporary workspace.

The main refactor is changing pipeline entry from “find a global slug under
`sources/`” to “run this explicit document context in this working directory.”

User-uploaded PDFs are untrusted input. Public launch should process them in a
separate non-root worker container or host with:

- CPU, memory, disk, file-size, and wall-time limits;
- maximum pages and decompressed output;
- no access to the web application filesystem;
- minimal storage credentials;
- controlled outbound network access;
- cleanup after success or failure;
- a dependency/security update process.

The public web process and PDF parser should not share a process or writable
filesystem.

## Durable jobs

Replace process-memory job sets with:

- a PostgreSQL `jobs` record as durable truth;
- a dedicated worker service;
- idempotent job handlers;
- retry and cancellation rules;
- per-workspace and global concurrency limits;
- progress/status API;
- dead-job administration.

Dramatiq is a reasonable Python option: it supports workers, Redis/RabbitMQ
brokers, automatic retries, and concurrency controls.
[Dramatiq guide](https://dramatiq.io/guide.html)

Run Redis as a broker, not as the sole record of a job. PostgreSQL retains the
durable status and enough input to recover or resubmit jobs.

A PostgreSQL-only queue such as Procrastinate would reduce infrastructure, but
its current documentation says it is seeking maintainers. Do not select it as a
critical dependency without reevaluating that situation.
[Procrastinate documentation](https://procrastinate.readthedocs.io/en/main/)

## Roles

Start with a small role vocabulary.

Platform roles:

- `platform_admin`
- `support`
- `analyst`
- `researcher`

Workspace roles:

- `owner` — full workspace control and transfer/delete authority;
- `billing_admin` — billing and plan management;
- `admin` — members, projects, and tool settings;
- `editor` — create and edit projects;
- `viewer` — read/export where permitted.

Translate roles into permissions in code:

```text
workspace.members.invite
workspace.billing.manage
lpm.project.create
lpm.project.edit
lpm.project.export
rk_express.project.review
```

Do not scatter checks such as `if role == "owner"` through endpoints.
Centralize authorization and test the permission matrix.

Every query or service operation must scope resources through the authorized
workspace. Merely checking that a project UUID exists is insufficient.

## Administration and logging

Keep three systems distinct:

1. Audit log: security/business changes.
2. Product analytics: how people use the tools.
3. Operational logs: errors, latency, workers, emails, and external-provider
   failures.

The audit log should be append-only and record:

- acting user or system;
- workspace and target;
- action;
- timestamp;
- request/correlation ID;
- relevant before/after identifiers;
- reason for admin overrides;
- IP/device context where appropriate.

Admin functions should include:

- search users and workspaces;
- suspend/reactivate users;
- revoke sessions;
- inspect memberships and invitations;
- view and override entitlements with reason and expiry;
- inspect subscriptions and provider-event reconciliation;
- inspect usage and AI cost;
- retry/cancel jobs;
- review storage and quota use;
- review audit history;
- flag staff/test accounts;
- process deletion/export requests.

Avoid unrestricted “log in as user” initially. If impersonation is added, make
it explicit, time-limited, visibly bannered, and heavily audited.

The first-party analytics/event-ledger plan in
`docs/DEFERRED/landing-page-maker-analytics-plan.md` can use this PostgreSQL
foundation, with content-blind capture as the production default.

## Hosting options

### Recommended initial production shape

- EC2 web host: reverse proxy, React assets, FastAPI, Keycloak, Redis;
- separate EC2 worker host: PDF/AI job containers;
- RDS PostgreSQL: separate databases or schemas and credentials for RK3 and
  Keycloak;
- private S3 bucket: user documents and generated artifacts;
- SES: verification, recovery, invitations, and product email;
- Stripe: added only for paid launch;
- CloudWatch or another centralized log destination;
- automated deployment of versioned containers.

RDS provides automated backups and point-in-time recovery while remaining
ordinary PostgreSQL.
[AWS RDS backup and recovery](https://docs.aws.amazon.com/AmazonRDS/latest/gettingstartedguide/managing-backup-restore.html)

SES exposes SMTP as well as its API, so email can sit behind an adapter and be
replaced later.
[AWS SES sending options](https://docs.aws.amazon.com/ses/latest/dg/send-email.html)

One worker is enough initially. Separating it is about untrusted document
processing and resource isolation, not scale.

### Simpler private-beta alternative

Run all containers on one EC2 instance while keeping RDS and S3 managed. This is
acceptable for a small invited beta if worker containers are isolated and
resource-limited. Split the worker before accepting arbitrary public uploads.

### More managed alternative

Run the app and worker containers on ECS/Fargate with RDS/S3/SES. Fargate
removes server maintenance and supports container tasks without managing EC2
capacity.
[AWS ECS/Fargate overview](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html)

It adds deployment, IAM, networking complexity, and more AWS coupling.
Containerizing for EC2 preserves this as an upgrade path.

## Delivery sequence

### Stage 1 — free LPM account foundation

Build only what the first public version needs:

- Keycloak signup/login/logout;
- email verification and password recovery;
- backend-for-frontend sessions;
- personal workspace automatically created;
- `lpm_free` entitlement;
- private project list;
- document upload;
- durable processing job;
- LPM state in PostgreSQL;
- private artifact access;
- free-tier quotas and rate limits;
- account profile and deletion request;
- minimal platform admin and audit log;
- product analytics bootstrap;
- terms/privacy acceptance.

Do not include Stripe, discount codes, paid trials, bundles, or self-service
team UI yet.

### Stage 2 — teams and roles

- Workspace creation/renaming
- Workspace switcher
- Invitations, expiry, resend, revoke, and acceptance
- Member/role management
- Ownership transfer
- Project access rules
- Seat limits
- Concurrent-edit conflict behavior
- Team-level audit log

### Stage 3 — paid LPM

- Versioned plan catalog
- Stripe Checkout
- Customer Portal
- Webhook inbox and reconciliation
- Upgrades/downgrades/cancellation/grace periods
- Promotion codes
- Timed trials
- Seat billing if desired
- Internal entitlement projection
- Billing administration

### Stage 4 — RK Express

Move the existing non-LPM surface into a separate tool route and entitlement.

The present corpus, evaluation tools, feedback boards, metadata, patterns, and
administrative document set should initially become a private internal
workspace accessible only to platform staff. Do not expose today’s global
corpus to customer accounts.

Then decide which RK Express capabilities are customer-facing and tenantize
those resources deliberately.

### Stage 5 — additional tools

Each new tool gets:

- a tool key and route;
- a permission namespace;
- entitlement definitions;
- project type and state schema;
- usage events and quotas.

It reuses identity, workspaces, invitations, billing, jobs, audit, analytics,
and storage.

## Options to reject initially

- A full rewrite in Django, Rails, or Node solely to obtain account packages
- Microservices per tool
- Building password authentication ourselves
- Using Stripe as the live authorization database
- Storing team roles entirely in OIDC tokens
- Keeping private artifacts under the current public `/output` mount
- A single global `paid/free/pro` account flag
- Adding Lago before billing complexity exists
- Running public PDF parsing inside the web server
- Implementing live collaborative editing before ordinary conflict handling

## Decisions to settle before implementation

1. Are subscriptions always workspace-owned? **Recommendation: yes.**
2. Can a user belong to multiple workspaces? **Recommendation: yes.**
3. Does every signup receive a personal workspace? **Recommendation: yes.**
4. Can free users create teams, or only paid users?
5. What are the free LPM limits for projects, pages, storage, AI generations,
   and retention?
6. Do paid plans charge per workspace, per seat, by usage, or a hybrid?
7. Does a project belong to the whole workspace or selected members/groups?
8. When a paid plan ends, are projects read-only, exportable, or unavailable?
9. How long are source documents and generated artifacts retained?
10. Is public sharing/publishing part of LPM, or is export the only outward
    action?

The strongest near-term path is therefore: self-host Keycloak, introduce an
app-owned workspace/entitlement model in PostgreSQL, move documents to private
object storage and durable workers, launch LPM with personal free workspaces,
then add team management and Stripe-backed paid entitlements.
