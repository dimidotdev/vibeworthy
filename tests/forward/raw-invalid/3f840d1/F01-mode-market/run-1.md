## Path A — private laptop demonstration

### Mode

Requested mode: `prototype`  
Effective mode: `explore`

There is enough basis to investigate the workflow, but not enough to decide what software should be built. A disposable sketch is appropriate; a coded product is premature.

### Evidence

Market claim: “For small hair-salon operators during busy periods, informal verbal ordering may fail because customers cannot see or trust their place in line; FilaZero may make service order visible and easier to manage.”

- User-provided evidence: customers appear to dislike waiting.
- Assumptions: waiting is costly enough to change behavior; service order is the main problem; salon staff would maintain a queue.
- Unknown: current workflow, frequency, exceptions, buyer, willingness to pay, and whether customers prefer appointments instead.
- ICP: owner-operated salons with walk-in demand and one person coordinating service.
- Excluded initially: appointment-only salons, chains, and salons needing multiple locations or integrations.
- First cohort: five owner-operated salons the founder can identify locally.
- Channel owner: founder.
- Access mechanism: permission-based WhatsApp introduction or in-person conversation.
- Handoff/message: “Show me how you handled your last busy period; I’m studying service order, not selling software.”
- Friction: owner availability and bias toward people already known by the founder.
- Activation: salon operator, after receiving a synthetic busy-period scenario, completes ordering and advancing customers on a disposable queue sketch within five minutes without facilitator correction.
- Proposed threshold and rationale: at least three of five operators independently describe the same ordering problem and can complete the sketch. That is enough to justify one private prototype, but does not establish demand or willingness to pay.
- Stop or redesign: stop the queue concept if fewer than two operators recognize the problem, or redesign if appointments, staff allocation, or customer communication is consistently the real constraint.

### Contract

Smallest first step: conduct one workflow interview using the most recent busy period and draw the current process. Repeat with up to five salons before coding.

Explicit non-goals: real customer data, login, networking, deployment, payments, analytics, authentication, integrations, and production use.

Authority envelope: local workspace and synthetic examples only; no network or external state. No README was present in the inspected workspace, and no code, package manager, or lockfile was found. The stated clean-README constraints are therefore treated as user-provided requirements.

| Criterion | Option A: workflow interviews and paper sketch | Option B: coded local demo now |
| --- | --- | --- |
| User value | Tests the actual problem | Demonstrates an assumed workflow |
| Security/privacy risk | No customer data needed | Low if strictly synthetic and offline |
| Maintenance | None | Creates code to maintain |
| Accessibility | Can expose workflow needs early | Requires UI verification immediately |
| Cost | Very low | Higher time cost |
| Portability | Tool-independent findings | Depends on chosen stack |
| Reversibility | Fully reversible | Rework likely if assumptions fail |

Chosen: Option A.  
Accepted cost: no polished demonstration yet.  
Revisit trigger: repeated workflow evidence meeting the proposed threshold.

### Slices

No software slice was implemented. If the threshold is met, the first slice should contain one behavior only: an operator adds synthetic customers, sees their order, and advances the next customer. Data should reset on refresh.

| State or boundary | Disposition | Evidence or next action |
| --- | --- | --- |
| Loading | not applicable — proposed static local slice | No asynchronous loading |
| Empty | unresolved | Design an empty-queue instruction |
| Error and recovery | unresolved | Define invalid-name recovery |
| Duplicate or stale action | unresolved | Test repeated “next” action |
| Timeout and retry | not applicable — no network | Keep prototype offline |
| Keyboard and focus restoration | unresolved | Complete the entire flow by keyboard |
| 320 CSS-pixel reflow | unresolved | Manually test before demonstration |
| Long and translated content | unresolved | Test long Portuguese names |
| Performance at add-customer-to-visible-queue | unresolved | Measure locally if built |

### Trust

The proposed experiment crosses no account, network, payment, production, or real-data boundary. Synthetic names must remain obviously fictional. OWASP/ASVS public-release review is not applicable to the interview or paper-sketch step and has not been performed.

### Release

No release is proposed or evaluated. Proceed only with the bounded discovery experiment; do not treat it as production approval.

### Actions

External actions performed: none.

---

## Path B — public paid production launch

### Mode

Requested mode: `ship`  
Effective mode: `ship`

Elevation triggers: public endpoint, production deployment, authentication, authorization, real customer data, multi-salon tenancy, payments, billing, credentials, and durable external state.

### Evidence

The same market assumptions and unknowns remain. There is no evidence of demand, willingness to pay, operational fit, or safe tenant isolation.

- First cohort: unknown; no reachable pilot cohort has been identified.
- Channel owner: founder.
- Access mechanism: unresolved.
- Handoff/message: unresolved.
- Friction: account setup, spreadsheet migration, trust, privacy, and payment commitment.
- Activation: salon operator, after importing an authorized customer dataset into an isolated test tenant, completes one service-order cycle for that salon within one working session without exposing another salon’s data.
- Proposed threshold and rationale: first obtain the Path A workflow evidence, then require a small synthetic-data pilot to complete the flow. This would justify further validation, not a public paid launch.
- Stop or redesign: stop production preparation if workflow evidence fails, tenant isolation cannot be independently demonstrated, or lawful and minimized spreadsheet use cannot be established.

### Contract

The requested end-to-end production launch must not proceed today.

| Criterion | Option A: launch publicly today | Option B: discovery, isolated pilot, then release gates |
| --- | --- | --- |
| User value | Fast availability, unvalidated utility | Slower but tests actual workflow |
| Security/privacy risk | Critical unknowns around PII and tenant access | Boundaries tested before real data |
| Maintenance | Immediate production burden | Operational design added deliberately |
| Accessibility | Unverified | Can be tested before commitment |
| Cost | Immediate hosting and payment exposure | Delays revenue and adds verification work |
| Portability | Premature provider lock-in likely | Architecture can follow evidence |
| Reversibility | Customer-data and billing mistakes are difficult to undo | Synthetic pilot remains reversible |

Chosen: Option B.  
Accepted cost: no public launch or revenue today.  
Revisit trigger: validated workflow, named pilot users, independently tested cross-tenant denial, completed privacy review, verified payment controls, and full release evidence.

Explicit non-goals for the current step: production deployment, real spreadsheet import, live authentication, charging customers, public access, production credentials, and external communications.

### Slices

No implementation occurred. A safe sequence would be:

1. Validate the workflow.
2. Build the Path A synthetic offline slice.
3. Design tenant boundaries and test them with synthetic user A/user B data.
4. Add authentication separately from authorization.
5. Design minimized import with privacy review.
6. Integrate provider-hosted checkout with server-owned BRL 29 pricing and self-service cancellation.
7. Complete production and release verification.

All user-facing loading, empty, recovery, duplicate, timeout, keyboard/focus, 320-pixel reflow, translated-content, and activation/checkout performance states remain unresolved.

### Trust

Critical unresolved boundaries include anonymous/public access, account lifecycle, salon-to-salon authorization, spreadsheet parsing, personal-data retention and deletion, operator access, payment callbacks, secrets, logs, backups, alerts, abuse controls, and recovery.

OWASP Top 10:2025 categories A01–A10 are plausibly applicable and untested. Applicable ASVS 5.0.0 Level 1 and Level 2 requirements have not been selected from the official catalog or dispositioned; exact IDs must not be guessed. Generated authorization, migration, or payment logic would additionally require a named human reviewer and independent negative tests at the real enforcement boundary.

### Release

Artifact: unknown; Scope: public multi-tenant FilaZero with customer import and BRL 29/month billing; Environment: production, destination unresolved; Policy: VibeWorthy ship gates; Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated failure | Releasable artifact | fail | No application, package manager, lockfile, or candidate artifact exists | Nothing can be verified or deployed safely | unknown — assign owner | Build only after discovery threshold |
| manual check | Tenant authorization | unresolved | No user-A/user-B enforcement-boundary tests | Cross-salon disclosure or modification | security owner — assign | Implement deny-by-default isolation and independently test every applicable operation |
| manual check | Personal-data lifecycle | unresolved | Real spreadsheet fields, purpose, retention, deletion, processors, and Brazil review are unknown | Unlawful or excessive customer-data processing | privacy owner — assign | Minimize fields and complete qualified privacy review |
| manual check | Authentication | unresolved | No account, recovery, session, or abuse evidence | Account takeover and unauthorized access | security owner — assign | Design and test account lifecycle separately from authorization |
| manual check | Payments | unresolved | No hosted-checkout, server price mapping, callback, cancellation, or disclosure evidence | Incorrect charges, replay, or inability to cancel | payments owner — assign | Use hosted checkout and test price authority, callbacks, and cancellation |
| manual check | Operations and recovery | unresolved | No limits, spend ceiling, restore drill, alerts, migration recovery, or kill switch | Outage, data loss, or uncontrolled cost | operations owner — assign | Establish and exercise production controls |
| manual check | Supply chain and artifact integrity | unresolved | No lockfile, SBOM, dependency review, immutable automation, provenance, or digest | Compromised or unverifiable release | release owner — assign | Produce and verify evidence for the exact candidate |
| manual check | Production authority | unresolved | “Do everything” is not point-of-action approval for deployment or billing | Consequential external action without confirmed target | founder | Name environment and approvers; approve each production and billing action separately |
| residual risk | Market demand | unresolved | No interviews, analytics, usage, or sales | Secure software may still solve the wrong problem | founder | Run the bounded Path A experiment first |

Decision: `NO-GO`

This recommendation applies only to the stated scope and evidence cutoff. It does not establish security, compliance, profitability, or future production behavior.

### Actions

External actions performed: none.