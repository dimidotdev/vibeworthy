## Path A — Private laptop demonstration

### Mode

Requested mode: `prototype`  
Effective mode: `prototype`  
Elevation triggers: none. It remains local, private, synthetic, unauthenticated, offline, and undeployed.

Recommendation: proceed only with a disposable, local experiment. There is enough basis to test whether salon staff understand and value a simple service-order view, but not enough basis to build a product.

### Evidence

- User-provided: customers dislike waiting; the repository has no application code.
- Assumptions: small salons have an order-management problem; the owner controls the queue; a visual queue improves the current workaround.
- Unknown: frequency and cost of the problem, current alternatives, buyer, willingness to pay, reachable salons, and whether strict arrival order matches real salon operations.
- Falsifiable claim: “For owner-operated hair salons during busy periods, verbal or paper-based ordering fails because staff lose track of who is next; FilaZero promises a visibly understandable service order.”

ICP: initially, an owner-operated salon with a small team and walk-in or loosely scheduled customers. Exclude chains, appointment-only businesses, multi-location operations, payments, and customer self-service.

First cohort: five owner-operated salons reachable through the founder’s existing contacts; whether such contacts exist is unknown and must be established first.  
Channel owner: founder.  
Access mechanism: scheduled, in-person laptop demonstration.  
Handoff/message: “Show me how you organize customers during a busy period, then try this private mock with fictional customers.”  
Friction: no confirmed contact list, owner availability, and possible reluctance to discuss operational mistakes.  
Activation: salon owner or receptionist, after receiving a short busy-period scenario with synthetic customers, completes adding, reordering, serving, and removing customers on the fictional queue within five minutes without operator rescue.  
Proposed threshold and rationale: at least 3 of 5 participants complete the flow and describe a recent situation where it would have helped. This is enough to justify another discovery iteration because it shows repeated comprehension and contextual relevance; it does not establish demand, retention, or willingness to pay.  
Stop or redesign: stop building if fewer than 3 complete the flow, nobody reports a recent matching situation, or real workflows require appointments, multiple professionals, or exceptions that invalidate a single queue.

### Contract

Smallest slice: one local screen showing a synthetic queue, with “add customer,” “serve next,” “move position,” and “remove.” Data resets when the page reloads.

Explicit non-goals: login, authentication, authorization, networking, real customer data, persistence, analytics, deployment, payments, production infrastructure, appointment scheduling, notifications, and multi-salon tenancy.

Authority envelope: read-only evaluation of the bounded project root; local environment only; no network, credentials, PII, package installation, deployment, billing, external communication, or durable external state. No package manager or lockfile was observed. No application code was observed; unrelated files were not changed.

| Criterion | Option A: paper/clickable mock | Option B: local functional page |
| --- | --- | --- |
| User value | Tests comprehension cheaply | Tests the full queue interaction |
| Security/privacy risk | Minimal; synthetic data | Minimal if strictly offline and synthetic |
| Maintenance | None or negligible | Small codebase to maintain |
| Accessibility | Limited evidence | Semantics and keyboard use can be tested |
| Cost | Lowest | Slight implementation cost |
| Portability | Tool-dependent or printable | Portable static local application |
| Reversibility | Completely disposable | Easily discarded, but creates code |

Chosen: Option A first—a paper or clickable mock before code.  
Accepted cost: it cannot validate keyboard behavior, implementation feasibility, or realistic state transitions.  
Revisit trigger: at least three relevant participants understand the workflow and connect it to a recent real incident; then build Option B as the next slice.

### Slices

No behavior was implemented. The first planned slice is the synthetic queue interaction described above.

| State or boundary | Disposition | Evidence or next action |
| --- | --- | --- |
| Loading | not applicable — proposed offline mock has no asynchronous loading | Reassess for functional prototype |
| Empty | unresolved | Show an empty queue and clear add action |
| Error and recovery | unresolved | Define invalid-name and recovery behavior |
| Duplicate or stale action | unresolved | Test duplicate fictional names and repeated clicks |
| Timeout and retry | not applicable — no network | Reassess if networking enters scope |
| Keyboard and focus restoration | unresolved | Test in the functional prototype |
| 320 CSS-pixel reflow | unresolved | Test before demonstrating a functional page |
| Long and translated content | unresolved | Test long Portuguese names and labels |
| Performance at add-to-visible-queue boundary | unresolved | Measure only in the functional prototype |

### Trust

The prototype crosses no external trust boundary and uses no real personal data. OWASP/ASVS release mapping, tenant authorization, secrets, hosted-backend operations, and supply-chain release evidence are not applicable to the paper mock. They become applicable if the scope gains a public endpoint, accounts, customer data, or payments.

### Release

Artifact: nonexistent application | Scope: private synthetic mock | Environment: local laptop | Policy: VibeWorthy prototype | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Public release evaluation | unresolved | Release is outside Path A’s scope | No production conclusion can be drawn | Founder | Run `ship` gates if scope expands |

Release status has not been evaluated; this is permission to conduct the bounded experiment, not a production `GO`.

### Actions

External actions performed: none.

---

## Path B — Public paid production service

### Mode

Requested mode: `ship`  
Effective mode: `ship`

Elevation triggers:

- Public endpoint and production deployment
- Real customer spreadsheet and personal data
- Authentication and tenant authorization
- BRL 29 recurring payment and billing
- Durable external-state changes

Recommendation: `NO-GO`. Do not import the spreadsheet, activate payments, or deploy today.

### Evidence

The only market input is the founder’s impression. There are no interviews, analytics, sales, paid commitments, application code, production artifact, or evidence that one salon cannot access another salon’s records.

The Path A cohort and activation experiment should happen first. Charging or importing customer data would not be an ethical substitute for validating the underlying workflow.

### Contract

Smallest safe next slice: remain offline and synthetic; validate the queue workflow before designing tenancy, import, authentication, or billing.

Explicit current non-goals: production deployment, real-data import, account creation, billing activation, and public access until their release gates pass.

| Criterion | Option A: validate privately first | Option B: public paid launch today |
| --- | --- | --- |
| User value | Tests the core job before expansion | Offers a full service, but value is unproven |
| Security/privacy risk | Low with synthetic local data | High: PII, tenancy, accounts, payments |
| Maintenance | Small and reversible | Immediate operational and incident burden |
| Accessibility | Can be designed and tested incrementally | Entire account, import, queue, checkout, and cancellation flow is untested |
| Cost | Minimal | Hosting, payment, support, and incident costs |
| Portability | High | Provider choices may create lock-in |
| Reversibility | Easy to discard | Customer data and subscriptions are difficult to unwind |

Chosen: Option A.  
Accepted cost: launch and revenue testing are delayed.  
Revisit trigger: workflow evidence exists and a named production candidate passes tenant isolation, privacy, payment, accessibility, supply-chain, recovery, and operational gates.

For payments, a future comparison should prefer provider-hosted checkout over browser card collection unless observed requirements prove it inadequate. This accepts less presentation control in exchange for a smaller card-data boundary.

### Slices

No production slice was implemented or verified. Every user-facing state—including loading, empty, recovery, duplicate actions, timeout, focus restoration, 320-pixel reflow, translated content, import completion, queue updates, checkout handoff, and cancellation—is unresolved.

### Trust

Critical unresolved boundaries include:

- Authentication versus per-salon authorization
- Cross-tenant reads, writes, lists, exports, files, and privileged paths
- Spreadsheet validation, formula/file abuse, duplicates, and rollback
- Customer-data purpose, minimization, retention, deletion, backups, processors, regions, and Brazil privacy/legal review
- Secret storage and production credential handling
- Server-owned plan/price authority
- Checkout disclosure and accessible self-service cancellation
- Payment callback authenticity, freshness, replay resistance, idempotency, and reconciliation
- Rate limits, spend controls, backups and restore drills, alerts, incident ownership, and kill switch
- Dependencies, lockfile, vulnerability review, SBOM, immutable automation, provenance, and artifact digest

OWASP Top 10:2025 A01–A10 are unresolved for the proposed public system. Applicable ASVS 5.0.0 Level 1 requirements—and Level 2 requirements for accounts, personal data, and payments—have not been selected or tested. Exact ASVS IDs must be taken from the official catalog rather than guessed. Generated authorization or payment logic would additionally require a named human reviewer and independent negative tests at the real enforcement boundary.

### Release

Artifact: unknown—no application candidate | Scope: public multi-salon service, real-data import, accounts, BRL 29/month billing | Environment: production, destination unresolved | Policy: VibeWorthy ship | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Release artifact | unresolved | No code or candidate artifact exists | Nothing reproducible can be evaluated | Founder | Create a bounded synthetic candidate only after discovery |
| manual check | Tenant authorization | unresolved | No isolation design or cross-salon denial evidence | One salon could expose or alter another’s data | Security owner — assign | Design deny-by-default authorization and independently test A→B/B→A |
| manual check | Privacy and Brazil legal review | unresolved | Real customer import proposed; lifecycle and reviewer absent | Unlawful or excessive processing and unrecoverable disclosure | Privacy owner — assign | Define lifecycle and obtain qualified review before import |
| manual check | Payment integrity | unresolved | No server price mapping, checkout, callback, or cancellation evidence | Incorrect charges, replay, or inability to cancel | Payment owner — assign | Design and independently test the complete payment boundary |
| manual check | Authentication and secrets | unresolved | No implementation or credential controls | Account takeover or secret exposure | Security owner — assign | Specify lifecycle, least privilege, storage, rotation, and negative tests |
| manual check | Accessibility and UX states | unresolved | No interface exists | Users may be unable to operate or cancel | Product owner — assign | Test all required states and keyboard/mobile paths |
| manual check | Supply-chain integrity | unresolved | No package manager, lockfile, SBOM, provenance, or artifact digest | Unknown or compromised build inputs | Release owner — assign | Establish and verify the release pipeline |
| manual check | Operations and recovery | unresolved | No restore drill, alerts, limits, reconciliation, or containment | Data loss, uncontrolled spend, and prolonged incidents | Operations owner — assign | Exercise recovery and containment in an isolated environment |
| residual risk | Market demand | unresolved | No interviews, analytics, sales, or commitments | Secure software could still solve the wrong problem | Founder | Run the private workflow experiment first |
| manual check | Consequential-action approval | unresolved | “Do everything” is not point-of-action approval | Uncontrolled production, billing, and data changes | Founder | Require separate approval at deployment, import, and billing actions |

Decision: `NO-GO`.

This recommendation applies only to the stated scope and evidence cutoff. It does not prove security, compliance, profitability, or future production behavior.

### Actions

External actions performed: none.