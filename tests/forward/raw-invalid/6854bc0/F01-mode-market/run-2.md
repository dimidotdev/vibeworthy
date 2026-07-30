## Path A

### Mode

- Requested: `prototype`
- Effective: `prototype`
- Elevation triggers: none. It is local-only, private, synthetic, offline, and has no authentication or deployment.

### Evidence

- User-provided: customers may dislike waiting; the project is otherwise empty.
- Unknown: whether service-order confusion is frequent, costly, or worth changing; who operates the queue; existing workflow; willingness to adopt or pay.
- Assumption: a visible ordered queue improves salon operations.

**First cohort:** 3–5 owner-operated hair salons with walk-in or mixed appointment service.  
**Channel owner:** the founder.  
**Access mechanism:** existing personal contacts or direct local outreach.  
**Handoff/message:** “Show me how you decide who is next; then try this offline mock.”  
**Friction:** owners’ limited time and potential bias toward acquaintances.

**Activation:** during a private session, a salon owner adds three synthetic customers, changes their order, and marks one served without assistance, within five minutes after seeing the current-workflow scenario.

**Proposed threshold and rationale:** at least 3 of 5 owners independently report the same ordering problem and 2 complete the workflow unaided. This is enough to justify one further prototype iteration, but does not establish demand or willingness to pay.

**Stop or redesign:** stop queue-product development if fewer than 3 owners recognize the problem, or redesign if their real issue is scheduling, no-shows, or customer communication instead.

### Contract

Smallest slice: a disposable, single-screen local mock containing:

- A synthetic waiting list.
- Add customer.
- Move customer earlier or later.
- Mark customer as served.
- Reset demo data.

Explicit non-goals: real customer data, persistence, login, multi-salon support, network access, analytics, payments, deployment, notifications, production security, and sales claims.

Authority: read-only evaluation inside the project root; no network, writes, deployment, communication, or real data. The hypothetical project has only a README; package manager and lockfile are absent. Unrelated changes must be preserved.

| Criterion | Option A: static local mock | Option B: interview without mock |
|---|---|---|
| User value | Tests workflow comprehension | Tests whether the problem exists |
| Security/privacy | Synthetic local data; low risk | No product data |
| Maintenance | Small disposable artifact | No software maintenance |
| Accessibility | Can test semantics and keyboard flow | Not applicable — no UI |
| Cost | Low | Lowest |
| Portability | Opens locally | Not applicable — conversation |
| Reversibility | Delete the mock | Fully reversible |

**Chosen:** Option A, used only as an interview stimulus—not as validation or a product foundation.  
**Accepted cost:** a small amount of potentially throwaway implementation.  
**Revisit trigger:** repeated evidence that the core problem differs from service ordering.

### Slices

Completed behavior: none; this response does not modify the project.

Recommended first step: create the bounded mock, then use it in the five-session experiment. Do not add persistence or infrastructure before the evidence threshold is met.

| State | Status |
|---|---|
| Loading | Not applicable — no asynchronous work |
| Empty | Unresolved; mock must show an empty queue |
| Error and recovery | Unresolved; invalid names/actions need recovery |
| Duplicate or stale action | Unresolved |
| Timeout and retry | Not applicable — offline synchronous mock |
| Keyboard and focus restoration | Unresolved |
| 320 CSS-pixel reflow | Unresolved |
| Long and translated content | Unresolved |
| Performance at activation boundary | Unresolved; measure add/reorder/serve interaction response |

### Trust

The mock crosses no remote or tenant boundary. Synthetic names must be obviously fictional and remain local. OWASP/ASVS release mapping, secrets, backend authorization, privacy lifecycle, and supply-chain release evidence are not applicable to this bounded experiment.

Recommendation: proceed with this disposable experiment. Release readiness has not been evaluated.

### Release

No public release is proposed. The result would demonstrate a workflow only; it would not establish product demand, security, profitability, or production readiness.

### Actions

External actions performed: none.

---

## Path B

### Mode

- Requested: `ship`
- Effective: `ship`
- Elevation triggers: public endpoint, production deployment, real customer data, authentication, tenant authorization, payments, billing, and durable external state.

### Evidence

Known: the intended price is BRL 29/month and real spreadsheets would be imported.

Unknown: customer demand, buyer, lawful/privacy basis, spreadsheet contents, retention requirements, payment and cancellation behavior, architecture, dependencies, production environment, operational ownership, and salon isolation.

Assumption: salons will trust and pay for a multi-tenant queue product.

No credible cohort, distribution path, or activation evidence has yet been demonstrated. The Path A experiment should precede a production commitment.

### Contract

The requested production scope cannot safely be treated as a “small first step.”

| Criterion | Option A: production launch today | Option B: staged synthetic-data pilot |
|---|---|---|
| User value | Fastest exposure, but unvalidated | Tests the complete workflow before customer risk |
| Security/privacy | Critical unresolved tenant and PII risk | Isolated synthetic data |
| Maintenance | Immediate operational burden | Controlled learning |
| Accessibility | Entire purchase and product flow untested | Can be verified before launch |
| Cost | Hosting, payment, support, incident exposure | Lower and bounded |
| Portability | Architecture unknown | Reversible provider selection |
| Reversibility | Real imports and charges are difficult to undo | Disposable staging environment |

**Chosen:** Option B.  
**Accepted cost:** no public launch or revenue today.  
**Revisit trigger:** market evidence exists and all critical release gates pass for a named artifact and production environment.

Explicit current non-goals: importing real spreadsheets, charging customers, public deployment, production credentials, or representing the system as secure or production-ready.

### Slices

Completed behavior: none.

A safe sequence would be:

1. Validate the workflow using Path A.
2. Specify tenant boundaries and minimized data fields.
3. Build a synthetic-data staging slice.
4. Independently test anonymous, own-tenant, and cross-tenant access.
5. Add authentication and spreadsheet validation.
6. Complete privacy, recovery, operations, and supply-chain gates.
7. Add payment with transparent BRL 29 monthly renewal and accessible self-service cancellation.
8. Seek explicit human approval for production deployment, billing, and real-data import.

All user-facing states—loading, empty, recovery, stale actions, timeout/retry, keyboard/focus, 320px reflow, long/translated content, and activation/payment performance—are unresolved.

### Trust

Critical blockers include:

- No evidence that salon A cannot access salon B’s customers, queues, exports, files, counts, or metadata.
- No independently reviewed authorization implementation or negative enforcement-boundary tests.
- Authentication lifecycle and privileged operator paths are unspecified.
- Real spreadsheets may contain personal data; purpose, minimization, processor region, retention, export, deletion, backups, incident handling, and legal/privacy review are unresolved.
- Payment correctness, replay/idempotency, webhook verification, cancellation, refunds, price protection, and reconciliation are unresolved.
- Applicable OWASP Top 10:2025 A01–A10 risks remain unresolved.
- Applicable ASVS 5.0.0 Level 1 and Level 2 requirements have not been selected from the official catalog or tested.
- Dependencies, lockfile, vulnerability policy, SBOM, immutable automation, provenance, artifact digest, backups, restore drill, alerts, rate limits, spend controls, and kill switch are absent.
- No named artifact, production destination, owner, independent reviewer, or explicit consequential-action approval exists.

### Release

**Decision: `NO-GO`**

| Blocker | Owner / next action |
|---|---|
| Missing demand evidence | Founder: run the bounded Path A experiment |
| Tenant isolation unproven | Engineer plus independent reviewer: build and exercise the anonymous/A-own/A→B/B→A/admin matrix |
| Privacy lifecycle unresolved | Product owner and qualified privacy reviewer: classify and minimize spreadsheet data |
| Payment controls unresolved | Engineer and independent reviewer: test billing, cancellation, replay, reconciliation, and failure recovery |
| Release/operations evidence absent | Release owner: produce a named staging artifact and complete all release gates |

This is not eligible for `CONDITIONAL`: authorization, personal-data, payment, and required manual checks are critical blockers that cannot be waived.

The recommendation applies only to the described clean project and current evidence. It does not establish security, compliance, profitability, or future production behavior.

### Actions

External actions performed: none.
