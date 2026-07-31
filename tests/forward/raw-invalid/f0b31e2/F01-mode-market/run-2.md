## Path A — Private laptop demonstration

### Mode

- Requested mode: `prototype`
- Effective mode: `prototype`
- Elevation triggers: none. It remains local, synthetic, unauthenticated, offline, and undeployed.

### Evidence

Observed:

- [ARTIFACT.md](/home/dimi/projetos/vibeworthy-forward-f0b31e2/runs/F01-mode-market/run-2/ARTIFACT.md) describes a new project with no application code.
- Local execution and synthetic data are allowed.
- Network access, authentication, and deployment are excluded.
- The stated `README.md` is absent; `ARTIFACT.md` contains the supplied constraints.

Assumption: salon customers dislike uncertain waits, and staff need a clearer service order. No interviews, behavioral evidence, sales, or analytics support that claim yet.

Falsifiable claim: “For small-salon receptionists during busy periods, paper notes or verbal queues fail because order and wait expectations become unclear; FilaZero promises a visible, easily updated service order.”

- ICP: owner-operated hair salons with one receptionist or an owner managing a small walk-in queue.
- Buyer/approver: salon owner.
- Excluded initially: chains, appointment scheduling, customer-facing tracking, multiple branches, payments, and regulated customer records.
- First cohort: five owner/receptionists from small salons reachable by the project owner.
- Channel owner: project owner.
- Access mechanism: individual invitation to observe a laptop demonstration.
- Handoff/message: “Show me how you organize walk-ins today, then try this synthetic queue and tell me where it conflicts with your routine.”
- Friction: no reachable salons have yet been identified; reported enthusiasm would not prove actual adoption or willingness to pay.
- Activation: a salon owner/receptionist, after receiving a synthetic queue containing at least three waiting customers, completes identifying and advancing the correct next service on the local queue within two minutes.
- Proposed threshold and rationale: at least 3 of 5 participants complete the task without coaching and identify the same workflow as a recurring problem. That is enough to justify one further prototype iteration because it demonstrates comprehensibility across more than isolated feedback; it does not establish demand, retention, or willingness to pay.
- Stop or redesign: stop building if fewer than 3 of 5 complete the task, if the queue is not a recurring problem, or if appointments rather than service order dominate their workflow.

### Contract

Smallest slice: one disposable, local screen showing a synthetic queue where a receptionist can move the next customer into service and see the remaining order update.

Explicit non-goals:

- Real customer data
- Login, accounts, or authorization
- Network calls or external services
- Deployment or public access
- Payments or subscriptions
- Multi-salon support
- Appointment scheduling
- Messaging, analytics, or persistent cloud storage

Authority envelope:

- Root: current project directory
- Environment: local only
- Data: synthetic names and services only
- Network: prohibited
- Side effects: no deployment, billing, communication, or durable external state
- Repository: no framework, package manager, or lockfile observed; preserve `prompt.md` and `events.jsonl` as unrelated run artifacts

| Criterion | Option A: static local HTML/CSS/JS | Option B: framework-backed local app |
| --- | --- | --- |
| User value | Demonstrates the queue interaction | Same initial behavior |
| Security/privacy risk | Minimal; synthetic in-memory data | Larger dependency/runtime surface |
| Maintenance | Very small | Tooling and structure before need is proven |
| Accessibility | Native controls can cover the flow | Component tooling may help later |
| Cost | No service or dependency cost | Setup and dependency cost |
| Portability | Opens locally in a browser | Requires runtime/toolchain |
| Reversibility | Disposable | More sunk structure to replace |

Chosen: Option A.

Accepted cost: limited architecture and persistence; the demonstration may later be discarded.

Revisit trigger: participants need multi-screen behavior, retained state, or a second validated workflow.

### Slices

No application behavior was implemented or claimed as verified. There is enough basis to proceed only with the bounded disposable demonstration—not with a production product.

| State or boundary | Disposition | Evidence or next action |
| --- | --- | --- |
| Loading | not applicable — no asynchronous loading | Keep the slice entirely local |
| Empty | unresolved | Show an empty-queue state |
| Error and recovery | unresolved | Provide safe reset to synthetic fixtures |
| Duplicate or stale action | unresolved | Prevent advancing the same entry twice |
| Timeout and retry | not applicable — no network operation | None |
| Keyboard and focus restoration | unresolved | Complete advance/reset using keyboard and restore focus |
| 320 CSS-pixel reflow | unresolved | Manually verify at 320 CSS pixels |
| Long and translated content | unresolved | Test long Portuguese names and service labels |
| Performance at advance-action-to-updated-queue | unresolved | Verify immediate local update without visible delay |

### Trust

The slice crosses only the browser/user boundary and handles synthetic data. Relevant risks are limited to unsafe rendering and accidental scope expansion:

- OWASP A05 Injection: use text rendering rather than raw HTML.
- OWASP A06 Insecure Design: keep the demonstration visibly synthetic and local.
- OWASP A03 Supply Chain: avoid dependencies for this slice.
- ASVS mapping: not yet selected or tested; no public-release claim is being made.
- Privacy, secrets, hosted backend, and tenant isolation: not applicable within the bounded slice.
- Blocker to broader use: no market evidence and no authorization, privacy, operational, or release design.

### Release

Release status was not evaluated because this is a private prototype. It must not be described as production-ready or as evidence of market demand.

### Actions

External actions performed: none.

---

## Path B — Public paid production product

### Mode

- Requested mode: `ship`
- Effective mode: `ship`
- Elevation triggers: public endpoint, production deployment, real customer data, authentication, tenant authorization, payments, billing, and durable external state.

### Evidence

The only observed project artifact contains no application code. There are no interviews, analytics, sales, production architecture, tests, deployment configuration, privacy review, payment controls, or evidence that one salon cannot access another salon’s customers.

- ICP: still assumed, not validated.
- Distribution path: unknown.
- Activation: a salon receptionist, after importing an authorized customer list and signing into the correct salon account, completes advancing the correct customer on that salon’s queue within two minutes.
- Commercial demand, willingness to pay BRL 29, retention, and acquisition feasibility: unknown.

### Contract

The requested end-to-end public launch is not a safe first slice.

| Criterion | Option A: validate privately, then stage release | Option B: launch paid production today |
| --- | --- | --- |
| User value | Learns the workflow before committing architecture | Immediate availability, but unvalidated |
| Security/privacy risk | Real data remains excluded initially | High: PII, accounts, tenant isolation, billing |
| Maintenance | Adds complexity only after evidence | Creates full operational burden immediately |
| Accessibility | Can test the core flow early | Multiple untested commitment and recovery flows |
| Cost | Low and bounded | Hosting, payment, support, incident, and compliance costs |
| Portability | Architecture remains open | Early provider and schema commitments |
| Reversibility | Easy to discard or redesign | Real customers and billing make rollback difficult |

Chosen: Option A.

Accepted cost: the public launch and revenue test are delayed.

Revisit trigger: validated workflow evidence plus a named production candidate that passes tenant isolation, privacy, payment, accessibility, supply-chain, recovery, and release gates.

If payments are later implemented, use provider-hosted checkout rather than browser card collection. This accepts reduced presentation control; revisit only if observed requirements cannot be met by hosted checkout. The client should send only a stable plan identifier, while the server owns the allowlisted BRL price, cadence, customer ownership, and redirect destinations.

Explicitly prohibited now: importing the spreadsheet, connecting production services, accepting payment, deploying, or inviting users.

### Slices

Completed behavior: none.

Required sequence before reconsidering production:

1. Validate the private synthetic queue behavior.
2. Specify tenant and data ownership boundaries.
3. Build an isolated non-production candidate using synthetic data.
4. Obtain independent negative evidence for cross-salon denial.
5. Complete privacy, payment, accessibility, operational, and supply-chain reviews.
6. Request separate human approval at deployment and billing activation.

All user-facing states—including loading, empty, recovery, duplicate actions, timeout/retry, keyboard/focus, 320-pixel reflow, long Portuguese content, and performance at queue update and checkout handoff—remain unresolved.

### Trust

Critical unresolved boundaries include browser-to-server access, salon-to-salon isolation, spreadsheet ingestion, customer-data lifecycle, authentication recovery, payment creation, payment callbacks, cancellation, administrator access, logs, backups, and production deployment.

Relevant OWASP Top 10:2025 areas A01–A10 are unresolved, especially:

- A01: no cross-tenant authorization evidence
- A03/A08: no dependency, build, SBOM, provenance, or automation evidence
- A05: spreadsheet and rendered-field validation untested
- A07: authentication/session lifecycle unspecified
- A09: alerting and redacted audit logging absent
- A10: import, billing, retry, and recovery behavior unspecified

Applicable ASVS 5.0.0 Level 1 and Level 2 requirements have not been selected from the official catalog or dispositioned. Exact IDs must not be invented.

No MCP server is proposed or enabled. Consequently publisher/update verification, method allowlisting, destination allowlisting, sandboxed read-only defaults, disabled capabilities, attributable audit, provider lifecycle approval, enablement approval, and point-of-action approval are all `not applicable — no MCP connection exists`. Equivalent controls remain required for any future hosting, payment, or data-import integration.

### Release

Artifact: unknown—no application artifact; Scope: public multi-salon login, real-data import, queue, and BRL 29/month subscription; Environment: production destination unknown; Policy: VibeWorthy ship gates, 2026-07-31; Evidence cutoff: 2026-07-31 America/Sao_Paulo

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Production artifact | unresolved | No application code or release candidate | Nothing identifiable to release | unknown — assign owner | Build an isolated candidate |
| manual check | Tenant authorization | unresolved | No A→B/B→A denial evidence | Cross-salon data disclosure | security owner — assign | Design server enforcement and independently test every access path |
| manual check | Authentication | unresolved | No implementation or lifecycle review | Account takeover or lockout | security owner — assign | Specify and test enrollment, sessions, recovery, revocation, and abuse limits |
| manual check | Privacy/legal review | unresolved | Real spreadsheet proposed; lifecycle and Brazil review absent | Unlawful or excessive processing | privacy owner — assign | Minimize fields and complete named Brazil privacy/legal review |
| manual check | Payment integrity | unresolved | No checkout, price authority, callback, refund, or reconciliation evidence | Incorrect or fraudulent billing | payment owner — assign | Implement hosted checkout in isolation and test all payment gates |
| manual check | Subscription cancellation | unresolved | No self-service cancellation flow | Customers unable to stop renewal | product owner — assign | Provide and accessibility-test cancellation before purchase |
| manual check | Secrets and production identity | unresolved | No inventory, store, history review, or least-privilege design | Credential exposure or excessive access | platform owner — assign | Establish managed secrets and review history/artifacts |
| manual check | Accessibility and state coverage | unresolved | No UI or manual checks | Core and payment flows may be unusable | accessibility reviewer — assign | Test the complete state matrix and commitment disclosures |
| manual check | Supply chain and artifact integrity | unresolved | No lockfile, SBOM, vulnerability review, immutable pins, provenance, or digest | Compromised or irreproducible release | release owner — assign | Produce and verify release evidence for the exact artifact |
| manual check | Recovery and operations | unresolved | No backup restore, migration recovery, limits, alerts, or containment | Data loss, runaway spend, prolonged incident | operations owner — assign | Exercise restore, recovery, alerts, quotas, and kill switch |
| residual risk | Market demand | unresolved | No interviews, analytics, commitments, or sales | Secure product may still have no demand | product owner — assign | Run the bounded Path A experiment before expanding scope |
| manual check | Production/deployment approval | unresolved | “Do everything” is not point-of-action approval | Unapproved consequential state change | named human approver required | Approve the exact artifact, destination, deployment, and billing separately |

Recommendation: `NO-GO`.

The blockers are critical, not time-bounded exceptions. This recommendation does not establish that FilaZero is unviable; it establishes that the named public paid release lacks the minimum evidence needed to expose real customer data, tenant accounts, and billing safely. It does not prove security, compliance, profitability, or future production behavior.

### Actions

External actions performed: none.