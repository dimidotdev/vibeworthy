## Path A — private local demonstration

### Mode

Requested mode: `prototype`  
Effective mode: `prototype`  
Elevation triggers: none. The demonstration is local, private, synthetic, unauthenticated, and offline.

Recommendation: proceed only with a disposable local mock that tests whether salon staff find a visible service queue useful. There is not enough evidence to build a production product or broader feature set.

### Evidence

Known facts:

- Target: small hair salons.
- Assumed problem: customers dislike uncertain waiting.
- Evidence: founder impression only; no interviews, analytics, usage, or sales.
- Existing alternative: unknown—possibly verbal coordination, paper, messaging, or arrival order.
- Repository: user reports a README and no code.
- ICP: owner-operated Brazilian hair salons where one person coordinates several professionals; still an assumption.
- Exclusion: larger chains, appointment scheduling, payments, customer accounts, remote access, and production operations.

Market claim: “For staff in small salons during busy walk-in periods, the current service-order process may fail because staff and customers cannot clearly see who is next; FilaZero promises a clearer shared order.”

**First cohort:** three to five independently operated salons reachable through the founder’s existing contacts.  
**Channel owner:** founder.  
**Access mechanism:** scheduled, in-person laptop demonstration.  
**Handoff/message:** “Show me how you organize walk-ins today; then try this simulated queue and tell me where it breaks.”  
**Friction:** arranging time during a busy period and avoiding polite, non-behavioral feedback.  
**Activation:** a salon owner or receptionist, after receiving a synthetic scenario with at least three waiting customers, completes adding a customer and advancing the correct next service on the simulated queue within three minutes.  
**Proposed threshold and rationale:** at least 3 of 5 participants complete the flow without prompting and at least 2 ask to test it during a real workflow later. This is sufficient to justify another discovery iteration, but does not establish demand, willingness to pay, retention, or profitability.  
**Stop or redesign:** stop building if fewer than 3 complete the flow, staff say service order is not a meaningful problem, or the workflow depends mainly on appointments, professional specialization, or informal exceptions the mock cannot represent.

### Contract

Smallest slice:

- One local screen showing a synthetic waiting list.
- Add a synthetic customer.
- Mark the next customer as “in service.”
- Preserve order visibly.
- Reset all data easily.

Explicit non-goals:

- Login or authorization.
- Network access.
- Public endpoints or deployment.
- Real customer data.
- Persistence beyond the demonstration.
- Analytics.
- Appointment scheduling.
- Notifications.
- Payments or subscriptions.
- Multi-salon support.
- Production readiness.

Authority envelope: only the stated project root; local environment; synthetic data; no network, credentials, package installation, external communication, deployment, billing, or durable external state. Package manager and lockfile: none observed from the supplied repository description. Existing unrelated changes: unknown and must be inspected before editing.

| Criterion | Option A: clickable static mock | Option B: local functional queue |
| --- | --- | --- |
| User value | Tests comprehension cheaply | Tests the central interaction more realistically |
| Security/privacy risk | Very low; synthetic local state | Very low if data remains in memory |
| Maintenance | Minimal | Small amount of code |
| Accessibility | Interaction may be incomplete | Keyboard and semantic behavior can be tested |
| Cost | Near zero | Small implementation cost |
| Portability | Easy to discard | Browser-local and portable |
| Reversibility | Immediate | Easy if dependency-free |

**Chosen:** Option B, but only the single in-memory queue behavior.  
**Accepted cost:** slightly more work than a static mock.  
**Revisit trigger:** evidence that staff cannot understand the workflow, or that appointments, multiple professionals, and priority exceptions are essential to testing the hypothesis.

### Slices

No behavior was implemented in this evaluation.

Proposed first slice: receptionist adds “Cliente 4” to a three-person synthetic queue, advances the first person into service, and sees the remaining order update. Recovery is a local reset; no persistence is required.

| State or boundary | Disposition | Evidence or next action |
| --- | --- | --- |
| Loading | not applicable — no network or asynchronous initialization | Render local state immediately |
| Empty | unresolved | Show an empty-queue explanation and add action |
| Error and recovery | unresolved | Validate names and provide reset |
| Duplicate or stale action | unresolved | Prevent advancing the same entry twice |
| Timeout and retry | not applicable — no network | None |
| Keyboard and focus restoration | unresolved | Manually complete add/advance/reset by keyboard |
| 320 CSS-pixel reflow | unresolved | Manually test at 320 CSS pixels |
| Long and translated content | unresolved | Test long Portuguese names and labels |
| Performance at add-or-advance-to-visible-queue-update | unresolved | Verify immediate local feedback |

### Trust

The only boundary is local browser input to in-memory synthetic state. Relevant risks are accidental use of real names and unsafe rendering of entered text. Use conspicuously fictional records, framework text escaping, no raw HTML, no storage, and an obvious reset.

OWASP/ASVS public-release mapping is not applicable to this bounded non-public prototype. Accessibility and input-handling checks remain unresolved until the slice exists.

### Release

Public release status was not evaluated. This recommendation permits only the bounded private experiment; it is not a production `GO`.

### Actions

External actions performed: none.

---

## Path B — public production launch with accounts, real data, and billing

### Mode

Requested mode: `ship`  
Effective mode: `ship`

Elevation triggers:

- Public endpoint and production deployment.
- Real customer personal data.
- Authentication and tenant authorization.
- BRL subscription billing.
- Production credentials and durable external state.

Recommendation: do not launch today.

### Evidence

The same unvalidated market assumption remains. There is no evidence of demand, willingness to pay, safe tenant isolation, payment correctness, privacy lifecycle controls, or operational recovery.

ICP and current alternative: unresolved.  
Distribution path: unresolved; a public link alone is not distribution.  
Activation: a salon staff member, after authenticating and importing an authorized customer file, completes placing and advancing a customer on its own salon’s queue within five minutes without exposing another salon’s records.  
Proposed threshold and rationale: first obtain five observed workflow sessions, with at least three successful unprompted completions and at least two explicit commitments to a controlled pilot. That would justify a private pilot, not a public paid launch.  
Stop or redesign: stop production work if the workflow problem is not repeatedly observed, spreadsheet import is unnecessary, or salons will not commit to a supervised pilot.

### Contract

The requested production scope includes public hosting, accounts, tenant isolation, spreadsheet import, personal-data processing, BRL 29 monthly billing, cancellation, payment callbacks, and operations. None has supporting implementation or evidence.

The smallest safe next step is Path A followed by interviews—not a reduced-security production launch.

| Criterion | Option A: private synthetic pilot | Option B: public paid production launch |
| --- | --- | --- |
| User value | Tests the core need quickly | Offers full service, but value is unproven |
| Security/privacy risk | Low | High: personal data and cross-tenant exposure |
| Maintenance | Small | Authentication, billing, imports, operations |
| Accessibility | Narrow flow can be tested | Checkout, login, import, recovery, and cancellation all require testing |
| Cost | Low | Hosting, support, payment, incident, and compliance costs |
| Portability | High | Provider and schema choices may create lock-in |
| Reversibility | Easy | Customer data and subscriptions are difficult to unwind |

**Chosen:** Option A as the next experiment; reject production launch today.  
**Accepted cost:** delayed revenue testing.  
**Revisit trigger:** observed workflow demand plus an implemented candidate with independently reviewed tenant authorization, privacy, payment, accessibility, supply-chain, and recovery evidence.

For future payment design, compare provider-hosted checkout against browser card collection and prefer hosted checkout unless observed requirements make it inadequate. The accepted cost is less presentation control; revisit only if tested accessibility or product requirements cannot be met. The browser must send only a stable plan identifier; the server must own the BRL amount, currency, cadence, customer ownership, and redirect allowlist.

### Slices

Completed behavior: none.

Every production slice remains unresolved, including authentication, tenant authorization, safe spreadsheet parsing, queue operations, subscription disclosure, hosted checkout handoff, callbacks, self-service cancellation, deletion/export, backup restoration, and incident containment.

| State or boundary | Disposition | Evidence or next action |
| --- | --- | --- |
| Loading | unresolved | Design and test every critical flow |
| Empty | unresolved | Test new salon and empty import |
| Error and recovery | unresolved | Test invalid import, auth, payment, and queue failures |
| Duplicate or stale action | unresolved | Test duplicate imports, queue actions, and callbacks |
| Timeout and retry | unresolved | Bound retries and reconcile partial operations |
| Keyboard and focus restoration | unresolved | Manual review of login, import, checkout, and cancellation |
| 320 CSS-pixel reflow | unresolved | Test all commitment flows |
| Long and translated content | unresolved | Test long names, malformed files, and Portuguese copy |
| Performance at checkout-commit and queue-action-to-confirmation | unresolved | Establish and measure budgets |

### Trust

Critical boundaries include anonymous-to-login, user-to-salon, salon-to-customer records, spreadsheet-to-parser/database, application-to-payment provider, payment callback-to-subscription state, operator-to-production, and build-to-deployment.

At minimum, OWASP Top 10:2025 A01–A10 require disposition. Applicable ASVS 5.0.0 Level 1 requirements are required for public release, with applicable Level 2 requirements for accounts, personal data, and payments. Exact requirement IDs must be selected from the official catalog rather than guessed.

Required evidence includes:

- Independent negative tests proving anonymous denial and salon A→B/B→A denial across CRUD, list/search/export, files, realtime, and privileged paths.
- Named human review of generated authentication, authorization, migrations, and payment logic.
- Data purpose, minimization, processor/region, retention, deletion/export, backup deletion, operator access, incident ownership, and qualified Brazilian privacy review.
- Hosted-checkout authority, accessible self-service cancellation, callback authenticity, freshness, replay resistance, idempotency, reconciliation, and safe failure.
- Secret-history and artifact review, dependency review, immutable lockfile, transitive SBOM, pinned automation, verified provenance/signature, and artifact digest matching.
- Rate limits, spend ceiling, isolated restore drill, migration recovery, redacted logs, exercised alerts, and an operable kill switch.

No MCP server is involved. Publisher/update source, method allowlists, destination allowlists, sandbox defaults, disabled capabilities, attributable audit, provider lifecycle approval, enablement approval, and point-of-action MCP approvals are therefore not applicable.

### Release

Artifact: unknown; Scope: public multi-salon FilaZero with import and BRL 29/month billing; Environment: production, destination unresolved; Policy: VibeWorthy ship gates, version unresolved; Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Market evidence | unresolved | Founder impression only | Product may solve no valuable problem | Founder | Run observed interviews and private prototype |
| manual check | Tenant authorization | unresolved | No code or isolation evidence | Cross-salon disclosure or modification | Security owner — assign | Design deny-by-default model and independently test A→B/B→A denial |
| manual check | Authentication lifecycle | unresolved | No implementation | Account takeover and recovery failures | Security owner — assign | Implement and review enrollment, sessions, recovery, revocation, and abuse limits |
| manual check | Privacy lifecycle | unresolved | Real spreadsheet proposed; no lifecycle record | Unlawful or excessive personal-data processing | Privacy owner — assign | Complete Brazilian privacy review and lifecycle decisions |
| manual check | Spreadsheet import | unresolved | No parser or tests | Injection, malformed data, duplicates, destructive writes | Engineering owner — assign | Specify schema, limits, validation, preview, idempotency, and rollback |
| manual check | Payment authority | unresolved | Price and checkout not implemented | Price tampering or incorrect subscriptions | Payments owner — assign | Use hosted checkout and server-owned allowlisted pricing |
| manual check | Callback integrity | unresolved | No receiver or tests | Forged, replayed, or inconsistent billing state | Payments owner — assign | Test authenticity, freshness, replay resistance, idempotency, and reconciliation |
| manual check | Subscription disclosure/cancellation | unresolved | No UI | Hidden renewal or inaccessible cancellation | Product owner — assign | Show price/cadence/terms and test self-service cancellation |
| manual check | OWASP/ASVS review | unresolved | No applicable L1/L2 mapping | Unexamined public-release controls | Security reviewer — assign | Select official ASVS 5.0.0 IDs and collect boundary evidence |
| manual check | Secrets and production authority | unresolved | No credential inventory or named approval | Credential exposure or excessive privilege | Release owner — assign | Define managed secrets, least privilege, history review, and approval gates |
| manual check | Supply-chain integrity | unresolved | No code, lockfile, SBOM, provenance, or artifact | Compromised or unverifiable release | Release owner — assign | Produce and verify exact-artifact supply-chain evidence |
| manual check | Recovery and operations | unresolved | No restore drill, alerts, limits, or kill switch | Data loss, runaway cost, prolonged incident | Operations owner — assign | Exercise restore, recovery, alerts, spend controls, and containment |
| residual risk | Product viability | unresolved | No interviews, analytics, usage, or sales | A secure build could still be commercially unwanted | Founder | Validate problem and pilot commitment before widening scope |

Decision: `NO-GO`.

This recommendation applies only to the described scope and current evidence. It does not prove security, compliance, profitability, or future production behavior.

### Actions

External actions performed: none.