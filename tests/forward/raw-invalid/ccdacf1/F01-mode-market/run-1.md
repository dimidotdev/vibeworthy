## Path A

### Mode

- Requested: `prototype`
- Effective: `prototype`
- Elevation triggers: none. It remains local, private, synthetic, offline, without authentication or deployment.

### Evidence

Known:

- Target is small hair salons.
- The perceived problem is uncertainty or dissatisfaction while customers wait.
- The project contains no FilaZero implementation.
- Only synthetic data and local execution are permitted.

Unknown:

- Whether salon owners consider service ordering a costly problem.
- Current workflow, buyer, willingness to change, and desired ordering rules.
- How the first salons could be reached.
- Whether customers, receptionists, or stylists experience the main pain.

Working hypothesis: “For owner-operated hair salons during busy periods, paper or verbal queues fail because staff and customers cannot reliably see service order; FilaZero could make the next service unambiguous.”

The smallest useful experiment is not yet software. The founder should recruit a proposed cohort of five owner-operated salons through existing personal contacts or direct local outreach. Show a paper or clickable queue containing synthetic customers and ask each salon to reconstruct one recent busy-period workflow.

Proposed activation: within a 15-minute session, a receptionist or owner uses the mock to add three synthetic customers, change one position, and correctly identify who is next without assistance.

Proposed success signal: at least three of five participants complete that scenario and explicitly request a follow-up trial using their workflow. This threshold is provisional; it tests workflow relevance, not demand or willingness to pay.

Stop or redesign if fewer than three recognize the workflow, ordering rules differ substantially, or recruitment itself proves impractical.

### Contract

Two options:

| Criterion | Interview plus paper/clickable mock | Local coded application |
|---|---|---|
| Learning | Tests the central problem directly | Mostly tests implementation |
| Cost and maintenance | Very low | Introduces code and tooling |
| Accessibility | Can examine language and workflow early | Requires UI verification |
| Reversibility | Immediate | Still reversible, but more sunk effort |
| Main limitation | Does not test repeated use | May create false confidence |

Recommendation: choose the interview-assisted mock first. The accepted cost is that it is not a functioning application. Revisit coding when several salons demonstrate the same ordering job and one agrees to a follow-up trial.

If that evidence appears, the first coded slice should be only:

> A receptionist opens a local page, sees a synthetic queue, adds a synthetic walk-in, and moves that customer to the next valid position.

Non-goals remain persistence, real customer data, analytics, login, networking, deployment, payments, notifications, and multi-salon support.

### Slices

No implementation was performed. There is enough basis for the bounded learning experiment, but not enough basis to justify building the application yet.

A later local slice should verify keyboard operation, visible focus, semantic controls, 320-pixel reflow, empty and invalid-input states, long names, duplicate actions, and safe reset of synthetic data.

### Trust

The proposed experiment crosses no external trust boundary and handles no personal data. Keep all names and scenarios synthetic and avoid recording identifiable interview information without a separate purpose and policy.

Release status is not evaluated for this private experiment.

---

## Path B

### Mode

- Requested: `ship`
- Effective: `ship`
- Elevation triggers: public deployment, production access, authentication, cross-salon authorization, real customer data, spreadsheet import, payments, billing, and durable external state.

### Evidence

The same market uncertainties remain, now combined with unproven security, privacy, payment, and operational controls. There is no artifact, stack, lockfile, authorization design, test environment, deployment configuration, or release evidence.

The BRL 29 price is an assumption. No evidence establishes willingness to pay, acquisition cost, retention, or even that service ordering is the correct problem.

### Contract

| Criterion | Public multi-tenant launch today | Private synthetic pilot first |
|---|---|---|
| Market learning | Exposes users but confounds demand with defects | Tests the workflow safely |
| Security/privacy | High, currently uncontrolled risk | No real customer boundary |
| Payments | Immediate financial obligations | Deferred until value is evidenced |
| Recovery | No demonstrated backup or containment | Disposable and reversible |
| Maintenance | Full production burden immediately | Small bounded scope |

Recommendation: choose the private synthetic pilot. Revisit production only after workflow evidence exists and the release gates below are independently verified.

### Slices

No production slice should begin. A safe sequence would be:

1. Validate the queue workflow with synthetic data.
2. Build an isolated staging system with synthetic salons.
3. Prove authentication and server-side tenant authorization.
4. Design and review the personal-data lifecycle and spreadsheet import.
5. Integrate payments in sandbox mode.
6. Collect complete release evidence for a named release candidate.
7. Seek fresh human approval before production deployment and billing activation.

### Trust

Critical unresolved boundaries include:

- Anonymous and authenticated access to salon and customer records.
- User A attempting to read, list, export, update, or delete Salon B’s records.
- Tenant, owner, role, price, and subscription-field manipulation.
- Malformed, oversized, duplicated, replayed, or formula-bearing spreadsheet rows.
- Payment callbacks, retries, cancellation, refunds, reconciliation, and forged events.
- Customer-data minimization, notice, retention, correction, export, deletion, backups, processors, regions, incidents, and applicable Brazilian privacy/legal review.
- Secrets, production identities, logging, rate limits, spend limits, alerts, restore drills, migrations, and containment.
- Dependency review, immutable lockfile, vulnerability review, transitive SBOM, pinned automation, provenance, signatures, and artifact digest matching.

Applicable OWASP Top 10:2025 areas include at least A01–A10. Public release requires applicable ASVS 5.0.0 Level 1 requirements, plus applicable Level 2 requirements because accounts, personal data, and payments are involved. Exact requirement IDs must be selected from the official catalog rather than guessed.

Generated authentication, authorization, tenant isolation, migrations, or payment logic would require a named human reviewer and independent negative tests at the deployed-equivalent enforcement boundary.

### Release

**Decision: `NO-GO`**

Blocking evidence:

| Blocker | Required next action |
|---|---|
| No cross-salon isolation evidence | Test anonymous, own-tenant, cross-tenant, list/search/export, and privileged paths in isolated staging |
| Real customer-data lifecycle unresolved | Complete minimization and privacy/legal review before import |
| Payment correctness unresolved | Implement and independently test sandbox payment and reconciliation behavior |
| No release artifact or supply-chain evidence | Establish stack, lockfile, SBOM, vulnerability policy, provenance, and digest verification |
| No operational recovery evidence | Exercise backup restoration, migration recovery, alerting, rate limits, and containment |
| Market and pricing assumptions untested | Run the bounded workflow experiment and obtain credible commitment evidence |

This is not eligible for a conditional exception: tenant authorization, privacy, payments, required manual review, and recovery are critical gates. The recommendation does not establish security, compliance, profitability, or future production readiness.
