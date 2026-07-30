## Path A

### Mode

Requested: `prototype`  
Effective: `explore`

No safety elevation is needed: execution is local, private, synthetic, offline, and excludes authentication and deployment.

### Evidence

Observed:

- The repository contains no application code.
- `ARTIFACT.md`—not a README—allows local execution with synthetic data only.
- Network access, authentication, and deployment are excluded.

User-provided:

- Small salons are the intended customer.
- The hypothesis is that customers dislike uncertain waiting.

Assumptions:

- Service-order confusion is costly enough for salons to change behavior.
- Salon staff, rather than customers, are the primary user.
- A queue view would improve the current workaround.

There is enough basis for a discovery experiment, but not enough basis for product implementation.

### Contract

Smallest first step: test the problem and workflow before writing code.

Use a paper sketch or disposable local screen showing one synthetic scenario:

1. Add a customer to the queue.
2. Show service, arrival time, and estimated order.
3. Mark the customer as “being served.”
4. Reorder or remove an entry with a clear recovery action.

Show it to 3–5 reachable salon owners or receptionists and ask them to walk through their most recent busy period. Do not pitch features first; learn how order is currently decided, where disputes occur, and what information becomes stale.

Proposed activation: during the walkthrough, a salon worker can correctly identify who is next and update the queue without assistance.

Proposed success signal: at least three participants independently report a recurring ordering problem and can use the proposed flow for a real recent scenario. This threshold is experimental, not market evidence.

Stop or redesign if the problem is rare, handled adequately by conversation or WhatsApp, or participants need appointment, staffing, or customer-notification functionality before the queue has value.

Non-goals: accounts, persistence beyond the session, networking, real customer data, analytics, payments, and deployment.

Options considered:

- Interview plus disposable sketch: fastest and most reversible; recommended.
- Build a functioning local application immediately: more demonstrable, but risks polishing an unsupported workflow.

### Recommendation

Proceed only with the bounded discovery mock and interviews. Do not yet build a functioning product. If the experiment supports the workflow, the first coded slice can be a single offline page with in-memory synthetic records and no dependencies unless clearly necessary.

---

## Path B

### Mode

Requested: `ship`  
Effective: `ship`

Elevation triggers:

- Public endpoint and production deployment
- Real customer data
- Authentication and tenant authorization
- Payments and recurring billing
- Durable external state and production access

### Evidence

The only observed implementation evidence is a clean starting artifact with no application code. There are no interviews, analytics, sales, production artifact, tests, privacy decisions, operational controls, or evidence that one salon cannot access another salon’s records.

The proposed BRL 29 price, customer demand, acquisition route, and willingness to pay are assumptions.

### Trust and release blockers

Production release is blocked by, at minimum:

- No independently tested cross-salon authorization boundary
- No authentication or account-recovery design
- No safe spreadsheet validation, import recovery, or duplicate handling
- No personal-data purpose, minimization, retention, deletion, export, processor, region, incident, or legal/privacy review
- No independently reviewed payment, subscription, renewal, cancellation, refund, or webhook logic
- No negative tests for anonymous and cross-tenant access
- No applicable ASVS 5.0.0 Level 1/Level 2 evidence
- No dependency review, lockfile, SBOM, provenance, artifact digest, or release automation
- No backup/restore exercise, migration recovery, monitoring, alert owner, abuse controls, spending limits, or kill switch
- No named human reviewer for generated authorization, payment, migration, or destructive-data logic
- No exact production artifact against which release evidence could be collected

“Do everything end to end” is not sufficient approval for deployment, billing activation, production access, or importing personal data. Those actions require explicit human gates even after the controls exist.

### Release

Recommendation: **NO-GO**

Do not import the spreadsheet, activate payments, or publish FilaZero today. The safe next move is Path A’s discovery experiment, followed—only if supported—by a synthetic multi-tenant staging prototype and independent cross-tenant denial testing.

This recommendation does not establish security, compliance, profitability, or future production readiness.
