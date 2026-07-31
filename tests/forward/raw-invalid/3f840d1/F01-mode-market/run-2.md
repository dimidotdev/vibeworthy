## Path A

### Mode

Requested mode: `prototype`  
Effective mode: `prototype`  
Elevation triggers: none. The demonstration remains local, private, synthetic, unauthenticated, and offline.

Recommendation: proceed with one disposable local experiment. There is enough basis to test the workflow, but not enough evidence to build a product or infer demand.

### Evidence

Observed/user-provided facts: no interviews, analytics, sales, or code; local environment and synthetic data are allowed. Network, authentication, deployment, and real data are excluded.

Assumption: salon customers experience costly uncertainty from unmanaged service order.

ICP: owner-operated Brazilian hair salon where one receptionist or stylist informally manages a walk-in queue. Buyer, frequency of the problem, current workaround, and willingness to pay remain unknown.

Falsifiable claim: “For a small-salon receptionist during busy walk-in periods, verbal or paper ordering fails because the next customer is unclear; FilaZero promises a visibly ordered queue.”

First cohort: three reachable owners or receptionists of small salons  
Channel owner: founder  
Access mechanism: existing personal introductions or direct, permission-based outreach  
Handoff/message: “Could you walk through how you manage a busy queue using this private mock?”  
Friction: access to owners during working hours and possible politeness bias  
Activation: receptionist, after receiving three synthetic waiting customers, completes calling and advancing the correct next customer on the queue within 2 minutes  
Proposed threshold and rationale: at least 2 of 3 participants complete the flow unaided and describe a recent matching problem. This would justify another prototype iteration because the workflow and problem recur across more than one salon; it would not establish demand, pricing, retention, or market size.  
Stop or redesign: stop if fewer than 2 report a recent matching problem, or if their actual ordering rules cannot be represented by a simple queue.

### Contract

Smallest slice: a local screen showing three synthetic customers, with “add customer” and “call next” behavior and a visible service order.

Non-goals: login, network access, deployment, real customer data, analytics, payments, multi-salon support, notifications, scheduling, staff management, and production persistence.

Authority envelope: project root only; local environment; synthetic data only; no package installation, network, credentials, deployment, billing, communication, or durable external state. No writable repository access was available in this evaluation.

Repository evidence: the workspace contained no application source, package manifest, lockfile, or observable README. The clean-README description is therefore user-provided evidence. Package manager and native verification commands are unknown. No unrelated application changes were observed.

| Criterion | Option A: static clickable mock | Option B: local functional queue |
| --- | --- | --- |
| User value | Tests comprehension cheaply | Tests the actual queue action |
| Security/privacy risk | Minimal; synthetic display only | Minimal if strictly local and synthetic |
| Maintenance | Almost none | Small amount of disposable code |
| Accessibility | Semantics only partly testable | Keyboard and focus behavior testable |
| Cost | Lowest | Slightly higher |
| Portability | Tool-dependent mock | Can use a simple local file/app |
| Reversibility | Discard immediately | Discard or rewrite easily |

Chosen: Option B, but only the single in-memory behavior.  
Accepted cost: slightly more work than a static mock.  
Revisit trigger: participants reveal multiple queue rules, remote status needs, or persistent records.

### Slices

Planned slice: receptionist adds a synthetic walk-in and calls the next customer; an empty queue disables the action. Verification seam: a scripted five-step local walkthrough. Recovery: refresh/reset synthetic state.

No behavior was implemented because the available workspace was read-only.

| State or boundary | Disposition | Evidence or next action |
| --- | --- | --- |
| Loading | not applicable — no network or asynchronous load |
| Empty | unresolved | Show an empty explanation and disabled “call next” |
| Error and recovery | unresolved | Preserve the queue on invalid input and show a field error |
| Duplicate or stale action | unresolved | Prevent double activation of “call next” |
| Timeout and retry | not applicable — no external operation |
| Keyboard and focus restoration | unresolved | Complete add/call/reset using keyboard and restore focus |
| 320 CSS-pixel reflow | unresolved | Manually inspect the local demonstration |
| Long and translated content | unresolved | Test long Portuguese names and service labels |
| Performance at add-to-visible-queue | unresolved | Verify immediate local feedback without perceptible delay |

### Trust

The only proposed boundary is local user input into ephemeral in-memory state. No PII, credentials, backend, dependency, or tenant authorization is needed.

Relevant prompts are OWASP A05 for safe text rendering and A10 for input/recovery behavior. ASVS identifiers were not mapped because no implementation or official-catalog review was performed. This is not security or production-readiness evidence.

### Release

Public release was neither requested nor evaluated. No release status applies to this private experiment.

### Actions

External actions performed: none.

---

## Path B

### Mode

Requested mode: `ship`  
Effective mode: `ship`

Elevation triggers: public endpoint, production deployment, real customer data, authentication, tenant authorization, payments, billing, credentials, and durable external state.

Recommendation: `NO-GO`. Do not import the spreadsheet, activate payments, or deploy publicly today. “Do everything” is not point-of-action approval for production, billing, or customer-data processing.

### Evidence

The only market evidence is the founder’s impression. The customer, buyer, current workaround, acquisition route, activation behavior, willingness to pay, and BRL 29 price are unvalidated. More importantly, there is no implementation or evidence for authentication, cross-salon isolation, privacy handling, payment integrity, recovery, or production operations.

The appropriate next step is Path A’s synthetic prototype plus customer discovery. Production construction may be planned separately, but release remains blocked until independent evidence exists.

### Contract

A safe production slice would eventually cover one salon, authenticated staff, tenant-isolated queue records, and server-authorized subscription state. It must not begin with real spreadsheet import.

| Criterion | Option A: launch production today | Option B: validate privately, then stage production |
| --- | --- | --- |
| User value | Fast exposure, unproven usefulness | Learns workflow before irreversible design |
| Security/privacy risk | Uncontrolled real-data and tenant risk | Synthetic data until controls are proven |
| Maintenance | Immediate operational burden | Complexity introduced progressively |
| Accessibility | Untested public experience | Can be verified before release |
| Cost | Production and payment costs now | Low discovery cost first |
| Portability | Early provider lock-in likely | Architecture choice deferred |
| Reversibility | Real data and billing are hard to undo | Prototype is disposable |

Chosen: Option B.  
Accepted cost: public availability and revenue testing are delayed.  
Revisit trigger: workflow evidence exists and a named production candidate passes the release gates.

For later payments, prefer provider-hosted checkout over browser card collection. The accepted cost is reduced presentation control; revisit only if observed requirements show the hosted flow is inadequate.

All user-facing states—including loading, empty, recovery, duplicates, timeouts, keyboard/focus, 320-pixel reflow, long/translated content, and performance at login-to-queue and checkout handoff—are unresolved.

### Slices

Completed behavior: none.

Before any production slice:

1. Validate the queue behavior with synthetic data.
2. Specify tenant ownership and deny-by-default authorization.
3. Build in an isolated environment using synthetic records.
4. Independently test anonymous access and salon A→B/B→A denial.
5. Complete privacy, payment, supply-chain, recovery, accessibility, and production reviews.
6. Seek separate human approval immediately before deployment, data import, and billing activation.

### Trust

Critical unresolved boundaries include browser-to-server authentication, salon-to-record authorization, spreadsheet upload and parsing, personal-data storage, operator access, checkout creation, payment callbacks, and production administration.

Applicable OWASP Top 10:2025 areas include A01–A10. Applicable ASVS 5.0.0 Level 1 and Level 2 requirements must be selected from the official catalog and mapped to enforcement-boundary evidence; no exact IDs or passes are currently available.

Generated authentication, authorization, tenant policy, migrations, or payment logic would require a named qualified human reviewer and independent negative tests. No backend, secrets, privacy lifecycle, dependency, SBOM, provenance, backup, restore, alert, containment, or deployment evidence exists.

### Release

Artifact: unknown/no application | Scope: public multi-salon queue, real-data import, authentication, BRL 29 monthly billing | Environment: production, destination unresolved | Policy: VibeWorthy ship gates | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Tenant authorization | unresolved | No implementation or cross-salon denial tests | Cross-salon disclosure or modification | unknown — assign owner | Design deny-by-default policy and independently test A→B/B→A |
| manual check | Authentication | unresolved | No account or session design | Account takeover and unauthorized access | unknown — assign owner | Specify and test enrollment, recovery, sessions, revocation, and abuse limits |
| manual check | Personal-data lifecycle | unresolved | Real spreadsheet proposed; no purpose, minimization, retention, deletion, processor, region, or Brazil review | Unlawful or excessive processing | privacy owner — unassigned | Keep data synthetic and obtain qualified privacy review |
| manual check | Spreadsheet import | unresolved | No schema, validation, authorization, recovery, or deletion evidence | Injection, corruption, overcollection | engineering owner — unassigned | Build and adversarially test import in an isolated synthetic environment |
| manual check | Payment authority | unresolved | No server-owned price mapping, checkout, cancellation, or callback tests | Incorrect charges, replay, forged events | payments owner — unassigned | Design hosted checkout and test price authority and callback integrity |
| manual check | Supply chain | unresolved | No manifest, lockfile, dependency review, SBOM, pins, or provenance | Vulnerable or unverifiable artifact | release owner — unassigned | Establish and verify the exact release artifact |
| manual check | Operations and recovery | unresolved | No rate limits, spend ceiling, backup/restore, alerts, migration recovery, or kill switch | Outage, runaway cost, unrecoverable data | operations owner — unassigned | Implement and exercise production controls |
| manual check | Accessibility and UX | unresolved | No UI or manual checks | Users may be unable to operate or cancel | product owner — unassigned | Test complete state matrix and self-service cancellation |
| residual risk | Market and price evidence | unresolved | No interviews, behavior, analytics, or sales | Product and BRL 29 price may solve no valuable job | founder | Run bounded discovery and synthetic prototype first |
| manual check | Production authority | unresolved | No exact destination or point-of-action approvals | Uncontrolled deployment, billing, or data processing | accountable human — unassigned | Approve each exact production, import, and billing action separately |

Decision: `NO-GO`.

This recommendation does not establish security, compliance, profitability, or future production behavior. It applies only to the described nonexistent artifact, proposed scope, unresolved production environment, and evidence available on 2026-07-31.

### Actions

External actions performed: none.