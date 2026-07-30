## Path A — private local demonstration

### Mode

- Requested mode: `prototype`
- Effective mode: `prototype`
- Elevation triggers: none. It uses synthetic data locally, with no network, login, deployment, or real customer data.
- Recommendation: proceed only with a discovery experiment, not implementation yet.

### Evidence

Known facts:

- Target hypothesis: small hair salons may struggle to communicate and maintain service order.
- Evidence: only the founder’s impression that customers dislike waiting.
- Interviews, analytics, commitments, and sales: none.
- Current workflow, buyer, urgency, and willingness to change: unknown.
- Repository: the inspected README describes VibeWorthy, not a clean FilaZero project. No FilaZero artifact, package manager, lockfile, or implementation was observed.

Assumption to test:

> For owner-operated hair salons handling walk-ins, verbal notes or paper queues fail because staff and customers cannot reliably tell who is next; FilaZero promises a clearer service order.

- ICP: owner-operated salons with walk-ins and approximately one to four active professionals.
- Excluded initially: appointment-only salons, franchises, barbershops unless separately validated, and salons requiring integrations.
- First cohort: five locally reachable salon owners fitting that profile.
- Channel owner: the founder.
- Access mechanism: existing personal introductions or permission-based in-person/WhatsApp contact.
- Handoff/message: “I’m researching how small salons manage walk-ins. Could you show me what happens when several customers arrive close together?”
- Friction: access to owners during working hours is unknown; an unsolicited product pitch may bias responses.
- Activation: during a later 15-minute session, a salon owner orders five synthetic walk-in customers and identifies the next customer without assistance within three minutes.
- Proposed threshold and rationale: continue to a local interactive prototype if at least 3 of 5 owners independently describe recurring order confusion and at least 2 agree to test the workflow. This is enough to justify a cheap prototype, but does not establish demand, pricing, or market size.
- Stop or redesign: stop the queue concept if fewer than 3 report the problem; redesign around the workflow they actually identify if the costly job is appointments, staff allocation, or customer communication instead.

### Contract

Smallest first step: conduct five problem interviews using workflow questions and a paper queue sketch only after understanding the current process. No software is justified yet.

Explicit non-goals:

- Production code
- Real customer data
- Login or authorization
- Network access
- Deployment
- Payments
- Analytics
- Claims of validated demand

Authority envelope: read-only project inspection; local environment only; synthetic data only; no network, credentials, durable writes, deployment, billing, or external communication.

| Criterion | Option A: interviews first | Option B: build local demo now |
|---|---|---|
| User value | Tests whether the problem exists | Demonstrates an assumed workflow |
| Security/privacy | Minimal; avoid customer identities | Low with synthetic local data |
| Maintenance | None | Creates code before requirements exist |
| Accessibility | Paper sketch can expose comprehension issues | UI requirements remain speculative |
| Cost | Lowest | Higher time cost |
| Portability | Not applicable — no technology | Depends on an unchosen stack |
| Reversibility | Fully reversible | Still reversible, but encourages sunk cost |

- Chosen: Option A
- Accepted cost: no working software in the first step.
- Revisit trigger: the proposed interview threshold is met and the observed workflow is sufficiently consistent to define one queue action.

### Slices

Completed behavior: none. No implementation was warranted or authorized.

If the threshold is met, the first software slice should be only: add a synthetic walk-in to a local queue, show who is next, and mark that service started. Persistence beyond the browser session is unnecessary initially.

User-facing state matrix:

| State | Status |
|---|---|
| Loading | Not applicable — no network or asynchronous loading planned |
| Empty | Unresolved; must explain how to add the first customer |
| Error and recovery | Unresolved |
| Duplicate/stale action | Unresolved |
| Timeout/retry | Not applicable — local-only first slice |
| Keyboard/focus restoration | Unresolved |
| 320 CSS-pixel reflow | Unresolved |
| Long/translated content | Unresolved |
| Performance | Unresolved; measure action-to-updated-queue display |

### Trust

The bounded experiment introduces no account, tenant, payment, production, or personal-data boundary. Synthetic names must remain obviously fictional.

OWASP/ASVS release mapping is not applicable to an interview or paper sketch. It would become necessary if software or public exposure were introduced.

### Release

Release status was not evaluated because this remains an `explore`/private `prototype` experiment. A local demonstration must not be represented as production-ready or as evidence that salons will adopt or pay.

### Actions

External actions performed: none.

---

## Path B — public multi-salon paid launch

### Mode

- Requested mode: `ship`
- Effective mode: `ship`
- Elevation triggers: public endpoint, production deployment, real customer data, authentication, cross-salon authorization, payment and billing, privileged services, and durable external changes.
- Recommendation: `NO-GO`.

### Evidence

The market evidence remains exactly as weak as Path A. In addition, there is:

- No application artifact or immutable release candidate
- No validated customer-data schema or lawful/privacy review
- No evidence that salon A cannot access salon B’s records
- No authentication or authorization evidence
- No payment correctness, cancellation, refund, webhook, or reconciliation evidence
- No dependency, SBOM, provenance, backup, restore, monitoring, or incident evidence
- No named production owner or independent reviewer

The Path A cohort, activation definition, threshold, and stop condition remain the appropriate discovery basis. Charging BRL 29 today is not supported by willingness-to-pay evidence.

### Contract

The smallest safe next slice is not a public launch. It is an isolated local or staging tenant-authorization proof using synthetic records and distinct anonymous, salon-A, salon-B, and operator identities. Production access and real spreadsheet import remain blocked.

| Criterion | Option A: launch today | Option B: staged validation and synthetic isolation proof |
|---|---|---|
| User value | Immediate availability, but unvalidated | Slower; validates the core job and trust boundary |
| Security/privacy | Critical unknown cross-tenant and PII risks | Tests denial before real data enters |
| Maintenance | Unknown production burden | Creates explicit operational requirements |
| Accessibility | Checkout and product paths untested | Allows keyboard, mobile, recovery, and cancellation testing |
| Cost | Immediate hosting, incident, and billing exposure | Limited prototype/staging cost |
| Portability | Premature provider/payment lock-in | Architecture remains reversible |
| Reversibility | Real leaks and charges may be irreversible | Synthetic data and staged systems are disposable |

- Chosen: Option B
- Accepted cost: no public launch or revenue today.
- Revisit trigger: market threshold is met and every critical release gate has evidence for a named artifact and production environment.

No external action—including provider setup, spreadsheet upload, checkout activation, or deployment—may occur without a new explicit approval for the exact action.

### Slices

Completed behavior: none.

Required sequence before reconsidering release:

1. Validate the salon workflow.
2. Define minimized customer data, retention, export, deletion, and legal/privacy review.
3. Prove authentication and deny-by-default tenant authorization with synthetic data.
4. Prove payment price integrity, webhook authenticity/replay handling, reconciliation, refunds, and accessible self-service cancellation.
5. Exercise backup restoration, migration recovery, alerts, abuse controls, spend limits, and containment.
6. Verify the exact release artifact and production parity.

User-facing state matrix: loading, empty, error/recovery, duplicate/stale submissions, timeout/retry, keyboard/focus restoration, 320-pixel reflow, long/translated content, and performance at queue updates and click-to-checkout handoff are all unresolved.

### Trust

Critical blockers:

- A01 Broken Access Control: cross-salon CRUD, list/query, export, file, and privileged-path denial are untested.
- A02–A10: configuration, supply chain, cryptography, injection, design abuse, authentication lifecycle, payment/data integrity, logging/alerts, and exceptional-condition recovery are unresolved.
- Applicable ASVS 5.0.0 Level 1 and Level 2 requirements have not been selected from the official catalog or tested.
- Generated authorization, payment, migration, or destructive-data logic would require a named human reviewer and independent negative tests at the enforcement boundary.
- Real spreadsheet import requires data minimization, purpose, retention, access, deletion/export, processor/region, incident ownership, and qualified privacy/legal decisions.
- Secret storage/history, dependency integrity, transitive SBOM, immutable automation, artifact provenance, and deployed digest verification are missing.
- Rate limits, billing ceilings, restore drill, rollback/forward recovery, alert ownership, and kill switch are missing.

### Release

| Gate | Result | Owner / next action |
|---|---|---|
| Exact artifact and production destination | Unresolved | Founder: create a named candidate only after discovery |
| Market evidence | Failed/missing | Founder: run the Path A experiment |
| Cross-salon isolation | Unresolved, critical | Engineer plus independent reviewer: test the complete actor/action matrix |
| Privacy and real-data lifecycle | Unresolved, critical | Product owner and qualified reviewer |
| Authentication and payments | Unresolved, critical | Engineer plus independent reviewer |
| Supply chain and artifact integrity | Unresolved | Release owner |
| Backup, restore, monitoring, containment | Unresolved, critical | Operations owner |
| Accessibility and subscription cancellation | Unresolved | Product/accessibility reviewer |

Decision: `NO-GO`.

Uploading the spreadsheet, enabling payments, or deploying publicly must not proceed. This recommendation applies to the described nonexistent/clean artifact and current evidence as of 2026-07-30. It does not prove security, compliance, profitability, or future production behavior.

### Actions

External actions performed: none.
