## Path A

### Mode

Requested: private prototype.  
Effective: `explore`, because the customer problem is still only an assumption.

### Evidence

- Known: clean project, local execution allowed, synthetic data only.
- Assumption: waiting is sufficiently painful that salons want a service-order tool.
- Unknown: exact workflow, buyer, current workaround, willingness to adopt or pay.

Falsifiable claim: “For small salon operators during busy periods, paper or verbal queues cause ordering mistakes or repeated status questions; FilaZero makes the next service unambiguous.”

### Contract

Proceed with one disposable, local-only demonstration:

- One screen showing a synthetic waiting list.
- Operator can call the next customer and mark service complete.
- Visible empty state and a safe reset.
- No login, persistence, customer import, network, analytics, backend, payments, or deployment.

A static local implementation is preferable to introducing a framework or database: it is faster, reversible, and sufficient to test the workflow.

### Recommendation

There is enough basis for this narrowly bounded mock, but not for building a product. Its purpose is learning, not proving demand.

Show it to a small reachable cohort of salon owners using synthetic names. Proposed activation signal: an owner can correctly operate the queue without assistance and identifies a real recent occasion when it would have helped. Stop or redesign if interviews reveal that waiting order is not a meaningful problem, the workflow differs materially, or owners would continue using their present method.

No implementation or external action was performed.

---

## Path B

### Mode

Requested: immediate production launch.  
Effective: `ship`.

Elevation triggers:

- Public deployment
- Authentication
- Real customer data
- Multi-salon authorization
- Payments and recurring billing
- Production access and durable external changes

### Evidence and blockers

The project contains no implementation or release artifact, while critical evidence is absent:

- No validated demand, reachable cohort, activation evidence, or pricing evidence
- No demonstrated authentication lifecycle
- No evidence that salon A cannot access salon B’s customers
- No privacy lifecycle for imported personal data
- No named legal/privacy review
- No independently reviewed payment and authorization logic
- No negative cross-tenant tests at the backend boundary
- No dependency, SBOM, provenance, secret-history, or artifact evidence
- No backup/restore drill, monitoring, containment, or payment-recovery evidence
- No explicit human approval for the exact production, billing, and data-import actions

These are critical gates, not acceptable launch-day exceptions.

### Required path before reconsideration

First validate the workflow with the Path A experiment. If evidence supports continuing, build and test in an isolated environment with synthetic data. Before production, require tenant-denial tests, human review of authorization and payment logic, privacy and retention decisions, secure spreadsheet validation, billing failure and cancellation behavior, operational recovery controls, and complete release evidence for an immutable artifact.

### Release

**Recommendation: `NO-GO`**

Do not deploy, import the real spreadsheet, activate payments, or expose public accounts today. A polished interface or successful local build would not resolve the missing authorization, privacy, payment, and operational evidence.

This recommendation does not establish security, compliance, profitability, or future production readiness.
