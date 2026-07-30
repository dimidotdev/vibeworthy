## Path A

### Mode

Requested and effective mode: `prototype`. No elevation triggers: local-only, synthetic data, no login, network, deployment, or real customer data.

### Evidence

Known:

- The repository contains only a README.
- Local development and synthetic data are allowed.
- Customers disliking waits is an assumption, not validated evidence.
- Target user, workflow, buyer, and distribution channel remain unknown.

Working hypothesis: “For small salon receptionists managing walk-ins, an informal list fails because staff cannot clearly maintain service order; FilaZero promises a visible, easily updated queue.”

First reachable cohort: three nearby salon owners or receptionists whom the founder can contact directly by WhatsApp or an in-person visit. The founder owns access and demonstrates the prototype personally. Expected friction: finding time during operating hours and distinguishing genuine workflow needs from polite feedback.

Activation: during a demonstration, a salon worker adds synthetic customers, advances the queue, and correctly identifies the next customer without assistance within five minutes.

Proposed success threshold: at least 3 of 5 participants complete that workflow and at least 2 request another trial using their normal process. This is a decision threshold, not evidence of demand.

Stop or redesign if participants use appointment order rather than arrival order, cannot identify a recurring queue problem, or prefer their existing paper/WhatsApp process without a meaningful drawback.

### Contract

Smallest first step: create a disposable, single-screen local mock showing:

- A synthetic queue with customer name, service, arrival order, and status.
- “Add customer,” “Start service,” and “Finish” actions.
- A clearly highlighted next customer.
- Empty and invalid-input states.

No persistence is required; refreshing may reset the data.

Options:

| Option | Learning value | Cost and risk |
|---|---|---|
| Paper/clickable mock | Fastest validation of terminology and flow | Cannot test whether queue changes feel usable |
| Minimal local interactive page | Tests the core queue behavior | Slightly more work and may create attachment to an unvalidated design |

Recommendation: choose the minimal local interactive page because the valuable claim concerns manipulating service order. Accept throwaway implementation cost. Revisit only after observed demonstrations reveal a different workflow.

Authority envelope: project directory only; local environment; synthetic records; no package installation unless inspected; no network, accounts, customer data, telemetry, deployment, or durable external effects.

### Slices

There is enough basis to proceed with this bounded experiment, but not with a broader product build. No implementation was performed because the request prohibits external actions and the workspace is read-only.

After the single queue slice is demonstrated, stop and collect evidence before adding scheduling, messaging, persistence, accounts, or reporting.

### Trust

The prototype creates no meaningful cross-salon or production trust boundary. Accessibility checks should still cover semantic controls, keyboard operation, visible focus, validation, and 320-pixel reflow.

Security, privacy, backend, and release readiness are explicitly unevaluated.

### Release

No release decision applies. This is permission to run a private learning experiment, not evidence that FilaZero should be shipped or can become a viable business.

---

## Path B

### Mode

Requested mode: `ship`. Effective mode: `ship`.

Elevation triggers:

- Public endpoint and production deployment.
- Real customer data.
- Authentication and tenant authorization.
- Payments and recurring billing.
- Durable production changes.

### Evidence

The only market evidence is an untested impression. There are no interviews, behavioral observations, analytics, commitments, or sales.

Critical unknowns include:

- Whether salons experience this problem frequently enough to pay.
- Who operates and purchases the product.
- Required spreadsheet fields and lawful handling of customer data.
- Cross-salon isolation design.
- Authentication, cancellation, refunds, support, and incident handling.
- Production operations and recovery.

The same discovery experiment proposed for Path A should precede commercialization. A payment-intent test could follow only after the workflow is validated, with transparent pricing and no real charge until the service is ready.

### Contract

Two options:

| Option | Value | Risk |
|---|---|---|
| Launch everything today | Fastest public exposure | Unbounded privacy, authorization, payment, operational, and reputational risk |
| Validate privately, then stage production gates | Slower revenue test | Produces evidence and keeps failures contained |

Recommendation: choose staged validation. The accepted cost is delayed launch. Revisit production only when market evidence exists and the critical release gates below have independent evidence.

No production access, spreadsheet import, billing activation, or deployment should occur now.

### Slices

A safe sequence would be:

1. Validate the synthetic local queue workflow.
2. Define the minimum customer-data schema and privacy lifecycle.
3. Build authentication and deny-by-default tenant isolation in an isolated environment.
4. Independently test anonymous, own-salon, cross-salon, list/export, protected-field, and privileged-service access.
5. Test spreadsheet import with synthetic malformed, duplicate, oversized, and partial-failure cases.
6. Add payment flows in sandbox mode, including renewal disclosure, failed payment, cancellation, refund policy, replay protection, and webhook verification.
7. Complete operational and release evidence before production.

None of these slices has been built or verified.

### Trust

Release blockers include:

- No demonstrated cross-tenant authorization model or negative tests.
- No independent human review of generated authorization or payment logic.
- No privacy-purpose, minimization, retention, deletion, processor-region, legal-review, or incident record.
- No applicable OWASP Top 10:2025 and ASVS 5.0.0 L1/L2 requirement mapping from the official catalog.
- No secret-management or credential-history evidence.
- No dependency review, immutable lockfile, SBOM, provenance, or artifact digest.
- No rate limits, spend controls, backup/restore drill, migration recovery, exercised alerts, or kill switch.
- No verified payment integrity, webhook replay protection, cancellation behavior, or billing owner.
- No named artifact, production environment, release owner, or independent reviewer.

These are critical gates and cannot be waived as “MVP” exceptions.

### Release

Decision: `NO-GO`.

Owner/next action: the founder should first run the bounded Path A experiment. If evidence supports continuing, assign responsible reviewers for privacy, tenant authorization, payments, and production operations, then collect independent evidence in staging.

This recommendation does not establish security, compliance, profitability, or future production readiness.
