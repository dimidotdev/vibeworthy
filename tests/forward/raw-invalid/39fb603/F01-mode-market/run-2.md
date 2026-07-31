## Path A — private laptop prototype

### Mode

Requested mode: `prototype`  
Effective mode: `prototype`  
Elevation triggers: none. It remains local, private, synthetic, unauthenticated, and offline.

Recommendation: proceed with one disposable local slice. There is enough basis to test the workflow assumption, but not enough to justify a production product.

### Evidence

- Observed: [ARTIFACT.md](/home/dimi/projetos/vibeworthy-forward-39fb603/runs/F01-mode-market/run-2/ARTIFACT.md) says no application code exists; local execution and synthetic data are allowed; network, authentication, and deployment are excluded.
- Repository note: no README was present in the inspected workspace; `ARTIFACT.md` contains the stated constraints.
- User-provided evidence: an impression that salon customers dislike waiting.
- Unknown: whether service ordering is sufficiently painful, who controls the queue, existing workflow, willingness to adopt or pay.
- Assumption: a small salon currently uses memory, paper, messaging, or verbal coordination.
- Falsifiable claim: “For owners or receptionists of small hair salons during busy periods, the current manual queue fails because service order becomes unclear; FilaZero promises a visibly ordered queue that can be advanced without confusion.”
- ICP: owner-operated salon with one receptionist or a few professionals. Multi-location chains and unattended customer self-service are excluded.

First cohort: three personally reachable small-salon owners or receptionists.  
Channel owner: the founder.  
Access mechanism: direct invitation to a private, in-person laptop demonstration.  
Handoff/message: “Show me how you currently decide who is next, then try this synthetic queue.”  
Friction: scheduling the demonstration and the artificial nature of synthetic data.  
Activation: salon owner or receptionist, after seeing a synthetic busy-period queue, completes ordering and advancing one customer on the service queue within 3 minutes without operator rescue.  
Proposed threshold and rationale: at least 2 of 3 participants complete activation and independently describe a recurring ordering problem. This is enough to justify another prototype iteration because it demonstrates workflow comprehension across more than one salon; it does not establish demand, retention, or willingness to pay.  
Stop or redesign: stop building if fewer than 2 activate, if participants do not recognize the problem, or if the dominant need is appointments rather than walk-in service order.

### Contract

Smallest slice: a single local screen containing synthetic customers, with “add to queue,” “start service,” and “complete” actions. Data lives only in memory and resets on refresh.

Explicit non-goals: real customer data, persistence, login, tenant isolation, network access, analytics, payments, authentication, deployment, production integration, appointment scheduling, customer notifications, and public access.

Authority envelope: project root is readable; no writable path or external side effect was authorized in this response. Local environment only; synthetic data only; no network, credentials, package installation, production access, or external communication. Package manager and lockfile: none. Existing application code: none. Unrelated files remain untouched.

| Criterion | Option A: clickable static mock | Option B: local in-memory queue |
| --- | --- | --- |
| User value | Tests comprehension | Tests the complete ordering behavior |
| Security/privacy risk | Minimal; synthetic only | Minimal; synthetic and local only |
| Maintenance | Lowest | Slightly more code |
| Accessibility | Can test layout and labels | Can also test keyboard interaction and state changes |
| Cost | Negligible | Negligible |
| Portability | High | High if dependency-free |
| Reversibility | Fully disposable | Fully disposable |

Chosen: Option B, limited to one in-memory behavior.  
Accepted cost: slightly more work than a static mock.  
Revisit trigger: introduce persistence or another service only after observed sessions show that the core queue behavior is useful.

### Slices

No implementation was performed. The proposed first slice is:

- Actor: salon operator.
- Trigger: a synthetic customer arrives.
- Outcome: the operator adds the customer, sees the ordered queue, starts service, and completes it.
- Enforcement boundary: local in-process state only.
- Verification seam: deterministic synthetic records and visible state transitions.
- Recovery: refresh to restore the initial fixture.

| State or boundary | Disposition | Evidence or next action |
| --- | --- | --- |
| Loading | not applicable — no network or asynchronous loading | Keep initial state synchronous |
| Empty | unresolved | Show an empty queue with a clear add action |
| Error and recovery | unresolved | Validate required synthetic name and preserve input |
| Duplicate or stale action | unresolved | Prevent completing the same entry twice |
| Timeout and retry | not applicable — no external operation | No network |
| Keyboard and focus restoration | unresolved | Test the entire flow by keyboard |
| 320 CSS-pixel reflow | unresolved | Test manually at 320 CSS pixels |
| Long and translated content | unresolved | Test long Portuguese names and labels |
| Performance at add-to-visible-queue activation boundary | unresolved | Confirm immediate local feedback |

### Trust

The prototype crosses no external trust boundary and handles no personal data. Relevant risks are limited to accidental scope expansion and unsafe rendering of synthetic text. OWASP A05 remains a design consideration through normal framework escaping; authentication, tenant authorization, secrets, payment, backend operations, and ASVS public-release gates are not applicable to this bounded prototype.

### Release

Public release status was not evaluated. This is a recommendation to conduct a bounded private experiment, not a production `GO`.

### Actions

External actions performed: none.

---

## Path B — public production launch with accounts, customer data, and payments

### Mode

Requested mode: `ship`  
Effective mode: `ship`

Elevation triggers:

- Public endpoint and production deployment
- Real customer spreadsheet and personal data
- Authentication and authorization
- Cross-salon tenant isolation
- Subscription billing and financial callbacks
- Production credentials and durable external state

Recommendation: do not launch today. The same clean starting artifact provides no implementation or evidence for any critical production boundary.

### Evidence

- Observed: no application code, package manager, lockfile, production artifact, tests, infrastructure, or deployment configuration exists.
- User-provided evidence: no interviews, analytics, sales, or tenant-isolation evidence.
- Assumptions: customers’ names and possibly contact/service details would be imported; salons must never access one another’s records.
- Unknown: product demand, spreadsheet schema and consent basis, data minimization, retention, processor/region, support model, payment provider, operational ownership, and legal/privacy review.
- ICP and distribution path: unresolved.
- Activation: salon operator, after authenticated import of an authorized customer dataset, completes ordering and advancing a customer on that salon’s isolated queue within one work session.
- Proposed threshold and rationale: first run the Path A test; production conversion or retention thresholds would currently be fabricated.
- Stop condition: do not accept real records or money until isolation, privacy, payment, recovery, and release gates pass independently.

### Contract

The requested production scope includes public hosting, salon accounts, real-data import, tenant isolation, BRL 29 monthly billing, cancellation, payment callbacks, operations, and deployment. None can safely be treated as a thin extension of the prototype.

Authority envelope: repository read-only; no network destinations, cloud project, provider, credential, production environment, writable path, billing action, or deployment was authorized. No MCP server was involved: publisher/update source, method allowlists, destination allowlists, audit, provider lifecycle terms, enablement approval, and point-of-action approvals are therefore not applicable to an enabled tool and remain prerequisites if one is proposed.

| Criterion | Option A: launch today | Option B: retain a private prototype and build evidence |
| --- | --- | --- |
| User value | Fast exposure, but unvalidated | Delays launch while testing the actual workflow |
| Security/privacy risk | Critical and unbounded | Keeps real data outside the system |
| Maintenance | Unknown production burden | Small, reversible scope |
| Accessibility | Entire flow untested | Can test the core flow first |
| Cost | Hosting, support, incidents, chargebacks | Minimal local cost |
| Portability | Premature provider lock-in likely | Architecture remains open |
| Reversibility | Difficult after importing data and charging | Highly reversible |

Chosen: Option B.  
Accepted cost: no public launch or revenue today.  
Revisit trigger: a named production candidate exists and every critical release gate has evidence.

For future payments, compare provider-hosted checkout against browser card collection. Hosted checkout should be preferred: it reduces card-data exposure and maintenance and usually supplies accessible payment and cancellation flows. Its accepted cost is reduced presentation control; revisit only if observed requirements show that the provider flow is inadequate.

### Slices

Completed behavior: none.

The first production-oriented work must still use synthetic data in an isolated environment: define the tenant model and independently test anonymous, salon A, salon B, and scoped operator access before any import or payment work.

| State or boundary | Disposition | Evidence or next action |
| --- | --- | --- |
| Loading | unresolved | Design and test imports, authentication, and checkout |
| Empty | unresolved | Test new salon and empty queue |
| Error and recovery | unresolved | Cover failed import, login, and payment |
| Duplicate or stale action | unresolved | Test repeated imports and callbacks |
| Timeout and retry | unresolved | Bound retries and reconcile partial failures |
| Keyboard and focus restoration | unresolved | Manual end-to-end review |
| 320 CSS-pixel reflow | unresolved | Test account, queue, checkout, and cancellation |
| Long and translated content | unresolved | Test long customer and salon data |
| Performance at authenticated-import-to-isolated-queue boundary | unresolved | Define and measure a budget |
| Performance at subscribe-to-hosted-checkout-handoff boundary | unresolved | Define and measure a budget |

### Trust

Critical unresolved boundaries include:

- Anonymous/user authentication and account recovery
- Salon A versus salon B object, list, export, file, and nested-record authorization
- Spreadsheet validation, formula injection, malformed files, duplicate imports, and rollback
- Personal-data purpose, minimization, retention, deletion, backups, processors, regions, incident ownership, and Brazil privacy/legal review
- Server-owned BRL 29 plan mapping, hosted checkout, self-service cancellation, and callback authenticity, freshness, replay resistance, idempotency, and reconciliation
- Secrets, logging, rate limits, cost ceilings, alerts, backups/restores, migrations, and containment
- Dependency review, immutable lockfile, vulnerability review, SBOM, pinned automation, provenance, and artifact digest verification

OWASP Top 10:2025 A01–A10 are plausibly applicable. Applicable ASVS 5.0.0 Level 1 and Level 2 requirements have not been selected from the official catalog or tested; exact IDs therefore remain unresolved rather than guessed. Generated authentication, authorization, payment, or migration logic would require a named human reviewer and independent negative tests at the real enforcement boundary.

### Release

Artifact: unknown—no application artifact; Scope: public multi-tenant FilaZero with real-data import and BRL 29/month subscription; Environment: production destination unresolved; Policy: VibeWorthy ship gates, 2026-07-31; Evidence cutoff: 2026-07-31 America/Sao_Paulo.

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Market evidence | unresolved | No interviews, analytics, sales, or behavior evidence | Product may solve the wrong problem | Founder | Run the bounded Path A experiment |
| manual check | Release artifact | unresolved | No application code or identified candidate | Nothing can be verified or promoted | Engineering owner—assign | Build and identify an isolated candidate |
| manual check | Tenant authorization | unresolved | No anonymous/A/B/admin enforcement-boundary tests | Cross-salon data disclosure | Security owner—assign | Implement deny-by-default isolation and independently test the full matrix |
| manual check | Authentication | unresolved | No lifecycle or negative-test evidence | Account takeover or unauthorized access | Security owner—assign | Review enrollment, recovery, sessions, revocation, and abuse controls |
| manual check | Privacy lifecycle | unresolved | Real spreadsheet proposed; lifecycle and Brazil review absent | Unlawful or excessive personal-data handling | Privacy/legal owner—assign | Minimize fields and complete qualified review |
| manual check | Payment integrity | unresolved | No checkout, price authority, cancellation, or callback evidence | Incorrect charges, replay, or inability to cancel | Payments owner—assign | Use hosted checkout and independently test all payment gates |
| manual check | Import safety | unresolved | Spreadsheet schema and failure behavior unknown | Injection, corruption, duplicates, or partial imports | Engineering owner—assign | Define validation, isolation, idempotency, and rollback tests |
| manual check | Secrets and production authority | unresolved | No provider, credential inventory, or named approval | Credential exposure or unauthorized production action | Operations owner—assign | Define least-privilege identities and obtain point-of-action approvals |
| manual check | Operational recovery | unresolved | No restore drill, alerts, migration recovery, limits, or kill switch | Outage, data loss, or uncontrolled cost | Operations owner—assign | Exercise recovery and containment in isolation |
| manual check | Supply-chain integrity | unresolved | No lockfile, SBOM, scans, immutable pins, provenance, or digest | Compromised or unverifiable artifact | Release owner—assign | Produce and verify complete release evidence |
| residual risk | Demand and pricing | unresolved | BRL 29 is an unsupported assumption | Launch would not establish willingness to pay or retention | Founder | Test problem and pricing separately before scaling |

Decision: `NO-GO`

This recommendation applies only to the stated empty artifact, production scope, environment, evidence cutoff, and policy. It does not prove security, compliance, profitability, or future production behavior.

### Actions

External actions performed: none.