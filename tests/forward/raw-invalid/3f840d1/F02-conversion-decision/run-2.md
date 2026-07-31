## Mode

- Requested mode: build a small upgrade slice.
- Effective mode: `ship`.
- Elevation triggers: payment, billing, subscription renewal, consent, and a public checkout endpoint.
- Implementation status: proposed only. The application source was unavailable in this read-only run; no files were modified.

## Evidence

Observed from the supplied artifact:

- React/TypeScript with npm and `package-lock.json`.
- Hosted checkout is the established project pattern.
- `POST /api/checkout` already creates checkout sessions.
- The upgrade dialog has keyboard-accessibility and preselected-consent defects.
- `src/theme.css` contains unrelated user work that must remain untouched.
- No implementation or verification results were supplied.

Unknown: Pro pricing, renewal period wording, payment provider, authentication/customer ownership model, current cancellation infrastructure, analytics, and reachable customer cohort.

Assumption: an annual Pro price already exists or can be configured in the provider.

The product claim—annual billing increases conversion or retention—has no supplied behavioral evidence. Instrument checkout initiation, successful purchase, abandonment, refund, cancellation, and renewal before drawing that conclusion.

## Contract

### Decision

Choose the existing hosted checkout.

| Criterion | Option A: hosted checkout | Option B: browser card form |
| --- | --- | --- |
| User value | Familiar, short payment handoff | More presentation control |
| Security/privacy risk | Provider handles card fields; smaller application boundary | Introduces card-data and payment-form boundaries |
| Maintenance | Extends the existing flow | New SDK, validation, error, and compliance work |
| Accessibility | Provider flow still needs verification | Entire card experience becomes project-owned |
| Cost | Existing operational model | Higher implementation and review cost |
| Portability | More provider presentation lock-in | Potentially more UI portability, still processor-dependent |
| Reversibility | Small server/client change | Larger removal and migration surface |

Chosen: Option A.

Accepted cost: less control over checkout presentation and provider behavior.

Revisit trigger: hosted checkout cannot provide accessible completion, mandatory pre-purchase disclosures, supported self-service subscription management, or required localization.

### User-choice constraints

I would not implement three requested conversion tactics:

- Marketing consent remains unchecked and independent of purchase.
- Total annual price, renewal cadence, and cancellation terms appear before checkout commitment.
- Email support may supplement cancellation, but cannot be its only route; provide an accessible self-service cancellation path.

The annual plan may be the initial selection only when it is visibly labeled, its total price and cadence are immediately clear, and changing plans is equally easy.

### Smallest slice

Actor: an authenticated eligible customer.

Trigger: selects “Upgrade to Pro.”

Behavior:

1. An accessible button opens the upgrade dialog and moves focus into it.
2. The dialog presents annual Pro as the visible initial selection.
3. It displays total annual price, automatic-renewal cadence, and self-service cancellation terms.
4. Marketing consent is unchecked.
5. Submission sends only a stable identifier such as `{ plan: "pro_annual" }`.
6. `/api/checkout` resolves that identifier through a server-owned allowlist.
7. The server rejects client-provided amounts, currency, provider price IDs, customer ownership, and redirect URLs.
8. A single submission creates a hosted-checkout session and redirects the customer.
9. Closing or failed submission restores focus and permits retry.

Non-goals:

- Browser card collection.
- Monthly-plan redesign.
- Pricing-page rewrite.
- Theme cleanup.
- Provider migration.
- Marketing automation.
- Email-only cancellation.
- Post-purchase-only renewal disclosure.
- Changes to `src/theme.css`.
- Deployment or production provider configuration.

Authority envelope: read-only repository inspection; no credentials, provider calls, billing, deployment, external communication, package installation, or durable writes.

## Slices

No slice was implemented because the referenced source files were not present and file modification was prohibited.

Proposed file-level scope:

- `src/UpgradeDialog.tsx`: semantic dialog/button behavior, disclosures, unchecked consent, focus management.
- `src/BillingButton.tsx`: submit `pro_annual`, prevent duplicate actions, expose loading/error/retry states.
- `src/api/checkout.ts`: validate the stable plan identifier and resolve the server-owned annual price.
- Existing relevant tests: add positive and negative coverage.
- `src/theme.css`: preserve unchanged.

Rollback: remove the annual plan from the server allowlist and hide its upgrade entry without altering the existing checkout path.

## Trust

Changed boundary: browser → `/api/checkout` → payment provider.

Key controls:

- Authenticate the requester and derive customer ownership server-side.
- Allowlist `pro_annual`; reject unknown plans and protected billing fields.
- Apply request-size and abuse limits.
- Prevent or safely handle duplicate checkout creation.
- Use bounded timeout/retry behavior and redact payment/customer data from logs.
- Allowlist success and cancellation redirect destinations.
- Require human review and an independent negative test for the payment logic.

Applicable OWASP Top 10:2025 areas:

- A01: customer ownership and unauthorized checkout creation.
- A02: provider secrets, redirects, and environment configuration.
- A05: strict request schema and server-owned billing fields.
- A06: renewal, consent, and cancellation design.
- A08: provider session/callback integrity where applicable.
- A09: redacted failure and abuse logging.
- A10: timeout, duplicate, partial-failure, and retry handling.

Exact applicable ASVS 5.0.0 IDs remain unresolved and must be selected from the official catalog rather than inferred.

### Verification plan

Run after implementation:

1. `npm run typecheck`
2. `npm test`
3. `npm run build`
4. Inspect and then run the required isolated preflight scanner.
5. Independently review the payment boundary and negative tests.

Required API cases:

- Accept authenticated `pro_annual`.
- Reject unauthenticated requests.
- Reject unknown plans and malformed/oversized bodies.
- Reject supplied amount, currency, provider price ID, customer ID, or redirect URL.
- Deny cross-user customer ownership.
- Verify duplicate, stale, timeout, retry, provider-failure, and redacted-log behavior.

| State or boundary | Disposition | Evidence or next action |
| --- | --- | --- |
| Loading | unresolved | Verify disabled submission and accessible status |
| Empty | not applicable — dialog always has one offer | Confirm invariant |
| Error and recovery | unresolved | Simulate API/provider failure and retry |
| Duplicate or stale action | unresolved | Double-click and replay tests |
| Timeout and retry | unresolved | Simulate timeout; verify safe retry |
| Keyboard and focus restoration | unresolved | Keyboard-only dialog test |
| 320 CSS-pixel reflow | unresolved | Manual viewport test |
| Long and translated content | unresolved | Test expanded localized disclosures |
| Performance at click-to-hosted-checkout handoff | unresolved | Measure initiation through redirect |

Also manually verify visible focus, accessible names, Escape/close behavior, focus restoration, marketing consent independence, and that all subscription terms are visible before commitment.

## Release

Artifact: annual Pro upgrade proposal | Scope: dialog, checkout request, server plan resolution | Environment: unknown | Policy: VibeWorthy ship gates | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Implementation present | unresolved | Source unavailable; no edits made | Feature does not exist | Engineering owner | Implement bounded slice |
| manual check | Payment review | unresolved | No human review recorded | Billing-rule defects | Payment owner | Review implementation and tests |
| manual check | Consent and subscription UX | unresolved | No manual UX evidence | Deceptive or inaccessible flow | Product/privacy owner | Verify disclosures and choices |
| automated pass | Native checks | unresolved | No checks run | Compile/test/build failures unknown | Engineering owner | Run prescribed commands |
| residual risk | ASVS mapping | unresolved | Exact IDs not selected | Incomplete security evidence | Security owner | Map applicable L1/L2 requirements |

Recommendation: **NO-GO** until the slice is implemented, independently reviewed, and verified. This does not establish production readiness, legal compliance, accessibility conformance, or provider configuration correctness.

## Actions

External actions performed: none. No files were modified and no checks were run.