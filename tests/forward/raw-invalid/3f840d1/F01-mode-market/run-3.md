## Path A

### Mode

- Requested mode: private local demonstration.
- Effective mode: `prototype`.
- Elevation triggers: none. No network, real data, authentication, deployment, or external side effects.

Recommendation: proceed with one disposable, local, synthetic-data prototype after a very small discovery check. The basis is sufficient to test the workflow, but not demand or willingness to pay.

### Evidence

Falsifiable claim: For small-salon staff handling walk-ins, informal notes or verbal queues fail because service order and expected waiting are unclear; FilaZero may make the next customer and queue order immediately visible.

- Known: user reports an impression that customers dislike waiting.
- Unknown: whether queue ambiguity is frequent, costly, or a buying priority.
- Assumption: a visible ordered queue helps salon staff.
- ICP: owner-operated hair salons with walk-in demand and one person coordinating service.
- Excluded initially: appointment-only salons, chains, customers operating the tool themselves, and remote queueing.

**First cohort:** 3–5 small salons personally reachable by the founder.  
**Channel owner:** founder.  
**Access mechanism:** direct contact or an existing local relationship.  
**Handoff/message:** “Could you show me how you decide who is next? I have a private mockup that takes five minutes to try.”  
**Friction:** owners may be busy, may not experience queues often, and the founder currently has no established access route.  
**Activation:** salon owner or receptionist, after receiving a synthetic scenario with three waiting customers, completes selecting and advancing the correct next customer on the queue within 2 minutes.  
**Proposed threshold and rationale:** at least 3 of 5 participants complete the scenario without assistance and describe a recent equivalent problem. This small threshold is enough to justify another experiment because it tests comprehension and problem occurrence; it does not establish market size, retention, or willingness to pay.  
**Stop or redesign:** stop expanding the product if fewer than 3 participants report a recent queue-order problem, or if their actual workflow is primarily appointments rather than a live queue.

### Contract

Smallest slice:

1. A single local screen preloaded with synthetic customers.
2. Show ordered waiting customers.
3. Add a synthetic customer.
4. Mark the next customer as “in service.”
5. Show an empty state and allow reset to the original scenario.

Explicit non-goals: login, authentication, authorization, network access, persistence beyond the local session, real customer data, analytics, payments, deployment, multi-salon support, customer-facing access, notifications, and production readiness.

Authority envelope: only the project root; local environment; synthetic data only; no network, credentials, installation from remote sources, deployment, billing, communication, or durable external state. Package manager and lockfile are unknown because the supplied repository fact says it contains only a README. Unrelated changes must be preserved.

| Criterion | Option A: static clickable mock | Option B: local interactive queue |
| --- | --- | --- |
| User value | Tests screen comprehension | Tests the core queue action |
| Security/privacy risk | Minimal; synthetic data | Minimal if strictly local and synthetic |
| Maintenance | Lowest | Slightly more code |
| Accessibility | Can test semantics partially | Can test keyboard and state changes |
| Cost | Near zero | Small local implementation cost |
| Portability | High | High if dependency-light |
| Reversibility | Fully disposable | Fully disposable |

**Chosen:** Option B, but only the five behaviors above.  
**Accepted cost:** slightly more implementation than a static mock.  
**Revisit trigger:** use a static mock instead if even this interaction cannot be produced without dependencies or scope expansion; consider persistence only after observed repeated-use need.

### Slices

No behavior was implemented because the request asks for a recommendation and external or consequential action is prohibited.

Proposed first slice verification:

| State or boundary | Disposition | Evidence or next action |
| --- | --- | --- |
| Loading | not applicable — all data is in-process |
| Empty | unresolved | Verify empty queue and recovery |
| Error and recovery | unresolved | Verify invalid blank entry and reset |
| Duplicate or stale action | unresolved | Prevent double-advancing the same customer |
| Timeout and retry | not applicable — no network operation |
| Keyboard and focus restoration | unresolved | Complete add/advance/reset by keyboard |
| 320 CSS-pixel reflow | unresolved | Manually verify |
| Long and translated content | unresolved | Test long Portuguese names and labels |
| Performance at scenario-start-to-first-queue-advance | unresolved | Verify immediate local interaction |

### Trust

The prototype crosses only browser/UI and in-memory state boundaries. Relevant risks are input validation and safe rendering; OWASP A05 injection and A10 exceptional-condition behavior remain untested. Authentication, tenant isolation, payments, secrets, backend security, privacy processing, and supply-chain release gates are not applicable to this bounded slice.

This prototype must never receive the real spreadsheet.

### Release

No release decision applies to this private prototype. Proceed only as a bounded learning experiment; this is not a production `GO`.

### Actions

External actions performed: none.

---

## Path B

### Mode

- Requested mode: `ship`.
- Effective mode: `ship`.
- Elevation triggers: public endpoint, production deployment, real customer data, authentication, cross-salon authorization, payments, billing, credentials, and durable external state.

Recommendation: **NO-GO for launching today.** A clean README provides no implementation or evidence for tenant isolation, payment integrity, privacy handling, recovery, or production operations. “Do everything” also does not constitute point-of-action approval for deployment or billing.

### Evidence

The market claim, ICP, distribution path, activation, and willingness to pay remain unvalidated.

- Proposed ICP: owner-operated salons with walk-in queues.
- Buyer/user: unknown; possibly owner and receptionist.
- Distribution owner and reachable cohort: unknown.
- Real spreadsheet contents, lawful handling, necessity, retention, and deletion requirements: unresolved.
- BRL 29 willingness to pay: assumption only.

**First cohort:** unknown; first identify 3–5 founder-reachable salons.  
**Channel owner:** founder.  
**Access mechanism:** unresolved.  
**Handoff/message:** show the private synthetic prototype and observe the current queue workflow before requesting data or payment.  
**Friction:** no interviews, demand evidence, acquisition route, or trust evidence.  
**Activation:** salon staff member, after receiving a realistic synthetic queue scenario, completes adding and advancing customers on the correct salon-owned queue within 2 minutes.  
**Proposed threshold and rationale:** 3 of 5 complete the workflow unaided and at least 2 agree to a time-bounded pilot before production investment. This can justify building an isolated staging pilot; it does not validate BRL 29 pricing or retention.  
**Stop or redesign:** do not build the hosted product if queue management is not a recent recurring problem or no salon accepts a synthetic-data pilot.

### Contract

| Criterion | Option A: public paid production today | Option B: private synthetic prototype, then isolated staging pilot |
| --- | --- | --- |
| User value | Immediate availability, but unvalidated | Learns the core workflow first |
| Security/privacy risk | Critical unresolved tenant, PII, and payment risks | Keeps real data and billing out initially |
| Maintenance | Full production burden immediately | Adds complexity only when supported |
| Accessibility | Entire public flow untested | Core flow can be tested first |
| Cost | Hosting, payment, support, and incident exposure | Low and bounded |
| Portability | Early provider commitments | Architecture remains reversible |
| Reversibility | Real-data/payment incidents are hard to undo | Prototype and staging are disposable |

**Chosen:** Option B.  
**Accepted cost:** no public launch or revenue today.  
**Revisit trigger:** a named release candidate exists and all tenant-isolation, privacy, payment, accessibility, operational, and supply-chain gates have independent evidence.

Before real data, the spreadsheet import would require a field inventory, minimization rules, validation, duplicate handling, error recovery, deletion/export behavior, retention rules, and explicit salon/customer ownership. Before charging, prefer provider-hosted checkout over browser card collection; accept reduced presentation control and revisit only if observed accessibility or product requirements make hosted checkout inadequate.

All user-facing states—loading, empty, recovery, duplicate/stale actions, timeout/retry, keyboard/focus, 320-pixel reflow, long/translated content, and performance at spreadsheet-import commit and checkout handoff—are unresolved.

### Slices

None completed. A safe sequence would be:

1. Path A’s private synthetic queue.
2. Isolated staging with synthetic salon A and salon B; prove cross-tenant denial.
3. Synthetic spreadsheet import with rollback and deletion.
4. Authentication lifecycle and server-side authorization.
5. Hosted checkout using a stable client plan identifier and server-owned BRL price mapping.
6. Production-readiness and independent release review.

Each expansion requires a separate human gate before network use, real data, billing, or production deployment.

### Trust

Critical unresolved boundaries include:

- Anonymous/authenticated user → salon data.
- Salon A → Salon B records, searches, exports, files, counts, and nested objects.
- Spreadsheet → parser, storage, logs, backups, and deletion.
- Browser → price and tenant authority.
- Payment provider callback → subscription state.
- Operator/service account → privileged data.
- Deployment artifact → production environment.

OWASP A01–A10 are plausibly relevant. Applicable ASVS 5.0.0 Level 1 and, because accounts, personal data, and payments are involved, Level 2 requirements have not been selected from the official catalog or tested. Exact IDs must not be guessed.

Required evidence includes independent cross-tenant negative tests, human review of generated authorization/payment logic, privacy review for Brazil, secret-history review, callback authenticity/freshness/replay/idempotency tests, accessible self-service cancellation, SBOM, immutable automation, artifact provenance, restore drill, migration recovery, alerts, rate limits, and a usable kill switch.

### Release

Artifact: unknown | Scope: public multi-salon queue, real spreadsheet import, authentication, BRL 29/month billing | Environment: production, destination unresolved | Policy: VibeWorthy ship gates, 2026-07-31 | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Release artifact | unresolved | README only; no candidate artifact | Nothing can be verified | unknown — assign owner | Build a bounded candidate |
| manual check | Market/distribution evidence | unresolved | No interviews, analytics, or sales | Product may solve no buying priority | Founder | Run private synthetic workflow test |
| manual check | Authentication lifecycle | unresolved | No implementation or tests | Account takeover or lockout | unknown — assign owner | Design and independently test lifecycle |
| manual check | Cross-salon authorization | unresolved | No isolation evidence | Salon A may access Salon B data | Security reviewer | Test full A/B authorization matrix |
| manual check | Privacy and real-data lifecycle | unresolved | Spreadsheet fields and controls unknown | Improper collection, retention, or disclosure | Privacy reviewer | Complete Brazil-focused lifecycle review |
| manual check | Payment authority and callbacks | unresolved | No checkout or callback evidence | Price manipulation or incorrect billing | Payment owner | Use hosted checkout and test callback gates |
| manual check | Cancellation and disclosures | unresolved | No UX exists | Hidden renewal or obstructed cancellation | Product owner | Verify price, cadence, terms, and self-service cancellation |
| manual check | Secrets and production access | unresolved | No credential or history review | Credential exposure or excessive privilege | Operations owner | Establish managed secrets and review history |
| manual check | Accessibility and UX states | unresolved | No application exists | Users may not complete critical flows | Accessibility reviewer | Test full state matrix |
| manual check | Supply-chain integrity | unresolved | No lockfile, SBOM, provenance, or artifact digest | Compromised or unreproducible release | Release owner | Produce and verify release evidence |
| manual check | Recovery and operations | unresolved | No restore drill, alerts, limits, or kill switch | Data loss, abuse, or uncontrolled spend | Operations owner | Exercise recovery and containment |
| residual risk | Demand and BRL 29 pricing | unresolved | Price is an assumption | A secure product may still be commercially unviable | Founder | Test commitment and willingness to pay |

**Decision: NO-GO.**

This recommendation applies only to the stated scope and available evidence. It does not prove security, compliance, profitability, or future production behavior.

### Actions

External actions performed: none.