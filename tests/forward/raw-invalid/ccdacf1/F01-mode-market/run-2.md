## Path A

### Mode

- Requested: `prototype`
- Effective: `prototype`
- No elevation triggers: local-only, synthetic data, no login, network, deployment, or external side effects.

### Evidence

Observed: only a clean README and explicit local/synthetic constraints.

Assumption: small salons lose time or customer trust because service order is unclear. There is no evidence yet that this is frequent, costly, or poorly served by paper, messaging, or conversation.

Initial ICP: owner-operated hair salons with a small team and walk-in or loosely scheduled customers. Exclude larger salons, appointment marketplaces, and multi-location businesses initially.

First reachable cohort: five salon owners personally reachable by the founder. The founder owns outreach; access is an in-person laptop demonstration; likely friction is scheduling and reluctance to discuss operational problems.

Proposed activation: during a demonstration, a salon owner uses synthetic customers to add someone, start service, and call the correct next customer without assistance within three minutes.

Proposed success threshold: at least three of five owners complete the flow and describe a recent real incident the workflow would have improved. Stop or redesign if fewer than three report the underlying problem, or if their actual ordering rules cannot fit the simple model.

### Contract

Smallest first step: validate the problem before writing an application. Prepare a short interview and a disposable, single-screen queue sketch showing:

- waiting customers in order;
- service and staff member;
- “start service” and “finish” actions;
- a visible next-customer state.

Use fictional names only. Do not add persistence, accounts, reports, notifications, databases, frameworks, or deployment.

Options comparison:

| Option | Benefit | Cost/risk |
|---|---|---|
| Five problem interviews first | Tests whether the problem is real and exposes actual ordering rules | No functioning demo yet |
| Build a local interactive demo immediately | Tests basic interaction | May polish an imagined workflow and bias interviews |

Recommendation: choose interviews plus a disposable screen sketch. The accepted cost is delaying code briefly. Revisit an interactive local prototype once repeated examples establish one common ordering rule.

### Slices

No implementation should proceed yet. There is enough basis for the bounded discovery experiment, but not enough basis for a coded product.

After supporting evidence appears, the first coded slice should be only: “operator adds a synthetic customer and advances them through waiting → in service → completed,” stored in memory and reset on refresh.

### Trust

The proposed experiment remains inside the laptop and uses synthetic records. Security, tenant isolation, payments, production operations, and personal-data processing are not applicable to this slice. Accessibility checks for a later interactive prototype should include keyboard completion, visible focus, semantic controls, 320-pixel reflow, and empty/error states.

Release status is not evaluated because this is a private experiment.

---

## Path B

### Mode

- Requested: `ship`
- Effective: `ship`
- Elevation triggers: public deployment, real customer data, authentication, tenant authorization, recurring payments, production access, and durable external changes.

### Evidence

The market claim remains unsupported. There are no interviews, behavioral data, sales, retained usage, or evidence that BRL 29 is acceptable.

More critically, there is no evidence that one salon cannot access another salon’s customers. There is also no named artifact, implementation, test suite, privacy decision, payment design, operational owner, or production recovery evidence.

### Contract

Options comparison:

| Option | Benefit | Cost/risk |
|---|---|---|
| Launch publicly today | Fastest exposure to real users | Unbounded privacy, tenant-isolation, billing, recovery, and reputational risk |
| Stage with synthetic data and explicit gates | Produces evidence before customer exposure | Delays public launch and revenue collection |

Recommendation: choose staged validation. Do not import the spreadsheet, activate payments, create production accounts, or deploy publicly.

The next bounded slice should use synthetic data in an isolated local or staging environment to prove tenant isolation: salon A can manage its records, while anonymous users and salon B are denied through the backend—not merely hidden by the UI.

### Trust

Blocking evidence is missing for:

- authentication lifecycle and server-side authorization;
- anonymous, own-tenant, cross-tenant, list/query, export, and privileged-admin negative tests;
- independent human review of generated authorization or payment logic;
- applicable OWASP Top 10:2025 risk mapping;
- exact applicable ASVS 5.0.0 Level 1 and Level 2 requirement dispositions;
- spreadsheet validation, safe import, rollback, deduplication, and partial-failure recovery;
- data purpose, minimization, retention, deletion, export, backups, processor regions, incident ownership, and required privacy/legal review;
- payment amount integrity, webhook authentication and replay protection, idempotency, cancellation, refunds, and billing reconciliation;
- secrets handling and history review;
- dependency review, immutable lockfile, vulnerability review, SBOM, pinned automation, provenance, and artifact digest verification;
- rate limits, cost ceilings, restore drill, monitoring, exercised alerts, and a kill switch.

### Release

**Decision: `NO-GO`.**

This is not a noncritical exception suitable for a conditional launch. Tenant isolation, personal-data handling, payments, production recovery, and required manual reviews are unresolved critical gates.

The route forward is:

1. Validate the salon workflow and willingness to pay.
2. Build the synthetic tenant-isolation slice.
3. Test the complete anonymous/A-own/A→B/B→A/admin authorization matrix independently.
4. Resolve privacy, spreadsheet-import, payment, supply-chain, and operational gates.
5. Name a release artifact and independent reviewers, then reassess.

This recommendation does not establish security, compliance, profitability, or future production readiness.
