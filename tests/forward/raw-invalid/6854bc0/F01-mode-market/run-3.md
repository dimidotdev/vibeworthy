## Path A

### Mode

- Requested mode: `prototype`
- Effective mode: `prototype`
- Elevation triggers: none. It is local-only, private, synthetic, and has no authentication, network, deployment, or real data.

Recommendation: proceed only with a disposable workflow mock, not a product implementation. There is enough basis to test the waiting-order concept, but not enough evidence to select features, architecture, or a commercial product direction.

### Evidence

Known facts:

- User-provided evidence: salon customers may dislike waiting.
- Repository: README only; no code.
- Interviews, analytics, sales, and observed workflow evidence: none.

Assumption: salon staff need help deciding and communicating who is served next. The current alternative is unknown—possibly memory, conversation, paper, or messaging.

- ICP: owner-operated hair salons with a small team and walk-in or mixed appointment demand. Buyer, approver, budget, and urgency are unknown.
- Excluded initially: chains, appointment booking, customer self-service, payments, and workforce management.
- First cohort: five independently owned salons reachable locally.
- Channel owner: the FilaZero founder.
- Access mechanism: direct personal introduction or permission-based visit; availability is unresolved.
- Handoff/message: “Show me how you decide who is next; then try this local mock using fictional customers.”
- Friction: owners may have little time, and the assumed problem may not match their actual workflow.
- Activation: within one observed session, a salon owner or receptionist, after seeing a synthetic queue, correctly identifies and changes the next customer without assistance in under two minutes.
- Proposed threshold and rationale: at least 3 of 5 participants must independently describe service-order confusion as recurring and complete the activation behavior. This is enough to justify one more prototype iteration because it shows repeated pain and comprehensible interaction across multiple salons; it does not establish demand, willingness to pay, retention, or market size.
- Stop or redesign: stop the queue-tool direction if fewer than 3 identify recurring order confusion, or if their real problem is primarily appointments, staffing, or customer communication.

### Contract

Smallest slice: a disposable, local screen containing five synthetic customers, their arrival/service state, and one action to mark or move the next customer. No persistence is necessary.

Explicit non-goals: real customer data, login, authorization, network access, analytics, package installation, backend, deployment, payments, appointments, messaging, and production readiness.

Authority envelope: read-only project access; local environment only; synthetic data only; no network or external side effects. Package manager and lockfile: none observed from the supplied README description. Unrelated changes: unknown and must be preserved.

| Criterion | Option A: static clickable mock | Option B: locally coded prototype |
|---|---|---|
| User value | Tests comprehension and workflow | Tests working interaction |
| Security/privacy | Synthetic data; minimal boundary | Synthetic data, but more code surface |
| Maintenance | Disposable | Creates code to maintain |
| Accessibility | Semantics can be designed and manually checked | Can be tested more completely |
| Cost | Lowest | Higher build and verification cost |
| Portability | Easy to recreate | Depends on chosen stack |
| Reversibility | Immediate disposal | Rework may be needed |

- Chosen: Option A, followed by interviews or observed walkthroughs.
- Accepted cost: it will not test persistence or technical feasibility.
- Revisit trigger: repeated workflow evidence meeting the proposed threshold.

Planned user-facing state matrix:

| State | Disposition |
|---|---|
| Loading | Not applicable — no asynchronous work |
| Empty | Unresolved; mock must show a clear empty queue |
| Error and recovery | Not applicable — no network or persistence |
| Duplicate or stale action | Unresolved; prevent or explain repeated completion |
| Timeout and retry | Not applicable — no external operation |
| Keyboard and focus restoration | Unresolved; must be manually checked |
| 320 CSS-pixel reflow | Unresolved; must be manually checked |
| Long and translated content | Unresolved; test long Portuguese names and labels |
| Performance | Unresolved; measure action-to-visible-order-update |

### Slices

No slice was implemented or executed. The first slice is planned only because the request prohibits external action and the market basis is insufficient for broader construction.

Verification, if created, should cover the primary reorder action, empty queue, duplicate action, keyboard completion, visible focus, 320-pixel reflow, and immediate visible update.

### Trust

The mock introduces no account, tenant, production, or personal-data boundary. OWASP/ASVS release mapping is not applicable to this disposable private mock. Any later use of real salon records, accounts, or public access would change the mode to `ship`.

### Release

Release status is not evaluated for this private experiment. This recommendation establishes only that a small learning exercise is proportionate; it does not establish demand, security, profitability, or production readiness.

### Actions

External actions performed: none.

---

## Path B

### Mode

- Requested mode: `ship`
- Effective mode: `ship`
- Elevation triggers: public endpoint, production deployment, real customer data, authentication, cross-salon authorization, subscriptions, billing, and durable external changes.

Recommendation: `NO-GO`. Do not import the spreadsheet, activate payments, create production accounts, or deploy publicly today.

### Evidence

The project has no implementation or release artifact, and there is no evidence for:

- Customer demand or willingness to pay BRL 29
- Data fields, purpose, minimization, retention, deletion, or privacy/legal review
- Authentication lifecycle and account recovery
- Cross-salon isolation
- Payment correctness, cancellation, refunds, webhook integrity, or reconciliation
- Dependency integrity, SBOM, provenance, backups, restore, monitoring, containment, or production parity

A public launch is not a suitable first experiment because failure could expose customer data or incorrectly charge salons.

The cheapest decision-changing test remains the Path A workflow test, followed by an explicit price conversation or non-charging commitment test. A payment launch should not be used to discover the basic problem while critical trust controls are absent.

### Contract

The requested end-to-end production scope is blocked. A safe next scope would be a synthetic-data staging system only, with no public launch or live billing, after workflow evidence exists.

Explicit non-goals for the next safe step: production deployment, public access, real spreadsheet import, live payments, real credentials, customer communication, and billing activation.

Authority envelope: repository inspection and local planning only. Production, network, customer data, billing, deployment, and durable external changes require separate explicit human approval after their gates pass. Package manager and lockfile: none. There is no artifact to release.

| Criterion | Option A: launch production today | Option B: validate, then build isolated staging |
|---|---|---|
| User value | Earliest availability, but unvalidated | Slower; tests the actual workflow first |
| Security/privacy | Critical unresolved exposure and tenant risks | Synthetic data and controlled boundaries |
| Maintenance | Immediate operational burden | Architecture can follow evidence |
| Accessibility | Entire journey untested | Can be tested before commitment |
| Cost | Production, support, and payment costs begin now | Bounded validation cost |
| Portability | Premature provider choices likely | Choices remain reversible |
| Reversibility | Customer exposure and charges are difficult to undo | Staging can be discarded |

- Chosen: Option B.
- Accepted cost: delayed launch and revenue testing.
- Revisit trigger: workflow evidence exists and all public-release, privacy, isolation, payment, recovery, and supply-chain gates have recorded evidence.

Required state matrix—all unresolved: loading; empty; error and recovery; duplicate/stale actions; timeout/retry; keyboard/focus restoration; 320-pixel reflow; long/translated content; and performance at queue-update confirmation and click-to-checkout handoff.

### Slices

Completed behavior: none.

Required sequence before launch:

1. Validate the salon workflow using synthetic data.
2. Build a synthetic staging slice with deny-by-default tenant isolation.
3. Independently test anonymous, own-salon, and cross-salon access at the backend boundary.
4. Design and review the personal-data lifecycle and spreadsheet import recovery.
5. Add sandbox billing with independently reviewed price, webhook, cancellation, refund, replay, and reconciliation logic.
6. Collect complete release and operational evidence before considering production.

### Trust

Critical blockers:

- OWASP A01/A06/A07: authorization, tenant isolation, insecure-design, and authentication evidence are absent.
- A02/A04/A05: production configuration, cryptographic handling, import validation, query safety, and output encoding are unresolved.
- A03/A08: lockfile, dependencies, SBOM, immutable automation, provenance, callback integrity, and migration integrity are absent.
- A09/A10: redacted logging, alerts, timeouts, retries, recovery, and containment are absent.
- Applicable ASVS 5.0.0 Level 1 and Level 2 requirements have not been selected from the official catalog or tested.
- The anonymous/user-A/user-B/admin authorization matrix is entirely untested.
- A named independent human reviewer and negative tests are required for generated authorization, authentication, migration, and payment logic.
- Privacy purpose, lawful/privacy review, processors, regions, retention, deletion, export, backup deletion, incident response, and operator access are unresolved.
- Backup restoration, migration recovery, billing limits, alerts, and kill switches are missing.

### Release

| Gate | Evidence | Result | Owner/action |
|---|---|---|---|
| Exact artifact/commit | None | Blocked | Founder: create a reviewed artifact |
| Demand and pricing | Impression only | Unresolved | Founder: run workflow and commitment tests |
| Tenant isolation | No design or tests | Blocked | Engineering/security reviewer |
| Privacy and real-data import | No lifecycle review | Blocked | Product owner and qualified privacy reviewer |
| Authentication | Not implemented | Blocked | Engineering and independent reviewer |
| Payments/cancellation | Not implemented or tested | Blocked | Engineering and payment reviewer |
| Supply chain/provenance | No code, lockfile, SBOM, or artifact | Blocked | Release owner |
| Operations/recovery | No backup, restore, alerts, or containment | Blocked | Operations owner |

`NO-GO` for public production deployment, real-data import, and live payments.

This does not establish that FilaZero is unviable. It means the requested production release lacks the minimum evidence needed to expose customer data or charge users safely.

### Actions

External actions performed: none.
