## Mode

- Requested mode: `ship`
- Effective mode: `ship`
- Elevation triggers: subscription payment, hosted payment provider, public checkout endpoint, personal data, and durable billing state.
- Decision: use the existing hosted checkout.
- The requested preselected marketing consent, post-purchase renewal disclosure, and email-only cancellation are excluded. Consent stays unchecked; renewal and cancellation terms appear before checkout; cancellation is accessible and self-service.

## Evidence

Known, user-provided facts:

- React/TypeScript application using npm.
- `package-lock.json` is the sole lockfile.
- `POST /api/checkout` already creates hosted-checkout sessions.
- The upgrade dialog has inaccessible clickable `div` behavior and preselected marketing consent.
- `src/theme.css` contains unrelated work that must remain untouched.
- Native commands are `typecheck`, `test`, and `build`.

Unknown:

- Provider, configured annual price, authentication model, callback implementation, customer ownership rules, cancellation portal support, analytics, and production environment.
- The actual application files were absent from this workspace; only [ARTIFACT.md](/home/dimi/projetos/vibeworthy-forward-f0b31e2/runs/F02-conversion-decision/run-3/ARTIFACT.md) was available.

Assumption: existing Pro users or upgrade-eligible users are the initial ICP.

- First cohort: authenticated upgrade-eligible users already encountering the Pro prompt.
- Channel owner: product owner, currently unknown.
- Access mechanism: existing in-product upgrade dialog.
- Handoff/message: “Upgrade to Pro annually for [total price]/year; renews annually until canceled.”
- Friction: unknown price, provider behavior, and cancellation route.
- Activation: an eligible user, after reviewing total price, renewal cadence, and cancellation terms, completes an annual Pro purchase through hosted checkout within one upgrade session.
- Proposed threshold and rationale: no numeric conversion threshold without baseline traffic and conversion evidence. First establish a technically valid funnel from dialog view through confirmed activation.
- Stop or redesign: stop release if price authority reaches the browser, disclosures are absent, cancellation is not self-service, or provider callback integrity is unverified.

## Contract

Smallest valuable slice:

1. Present one clearly labeled annual Pro offer.
2. Show total annual price, renewal cadence, and cancellation terms before commitment.
3. Keep optional marketing consent unchecked and independent of purchase.
4. Submit only `{ plan: "pro_annual" }` to `/api/checkout`.
5. Resolve `pro_annual` server-side to an allowlisted provider price and authenticated customer.
6. Redirect to the existing hosted checkout.
7. Expose a keyboard-accessible self-service “Manage or cancel subscription” path.

Non-goals:

- Browser card collection.
- Monthly-plan redesign or pricing experimentation.
- Preselected marketing consent.
- Withholding renewal terms until after purchase.
- Email-only cancellation.
- Changes to `src/theme.css`.
- New payment dependencies or provider migration.
- Unrelated dialog or billing refactors.
- Deployment, live checkout creation, analytics rollout, and production configuration.

Authority envelope:

- Read-only access to the supplied workspace.
- No credentials, PII, customer records, network calls, package installation, deployment, provider mutation, or billing operation.
- Production checkout testing requires separate approval and synthetic provider-test data first.

### Options comparison

| Criterion | Option A: existing hosted checkout | Option B: browser card form |
| --- | --- | --- |
| User value | Reuses a familiar, short purchase path | More visual control |
| Security/privacy risk | Card data remains primarily at provider boundary | Expands card-data and client-validation exposure |
| Maintenance | Small extension to existing API | New form, validation, SDK, error, and compliance surface |
| Accessibility | Provider flow still requires verification | Entire card interaction becomes project responsibility |
| Cost | Low implementation/operational cost | Higher engineering and compliance cost |
| Portability | Provider presentation lock-in | Potentially more UI portability, but still provider-tokenization dependent |
| Reversibility | Remove plan mapping and UI entry | Must unwind new form and payment integration |

- Chosen: Option A, hosted checkout.
- Accepted cost: less control over checkout presentation and provider accessibility.
- Revisit trigger: observed provider checkout cannot deliver required accessibility, disclosure, localization, or annual-plan behavior after provider remediation is exhausted.

Server contract:

```text
POST /api/checkout
Authenticated request: { "plan": "pro_annual" }

Server:
- accepts only the stable plan identifier;
- maps it to server-owned price, currency, interval, and provider price ID;
- derives customer/tenant ownership from authentication;
- owns success/cancel destinations;
- rejects amount, currency, priceId, customerId, owner, and redirect URL supplied by clients.
```

## Slices

| Slice | Observable behavior | Failure/denial | Verification seam | Recovery | Status |
| --- | --- | --- | --- | --- | --- |
| Annual hosted upgrade | Eligible user reviews honest terms and enters annual Pro checkout | Unknown plan, unauthenticated request, or client-owned pricing is rejected | UI tests plus direct API negative tests | Remove `pro_annual` mapping and hide entry point | Planned; not implemented |
| Self-service cancellation | Subscriber opens provider portal and can cancel without email | User cannot access another customer’s subscription | Ownership and cross-user tests at server/provider boundary | Disable portal entry while preserving support route | Planned; required for release |

### UX state matrix

| State or boundary | Disposition | Evidence or next action |
| --- | --- | --- |
| Loading | unresolved | Disable repeated activation and announce checkout creation |
| Empty | not applicable — dialog has a fixed annual offer | Confirm missing price configuration fails closed |
| Error and recovery | unresolved | Preserve dialog state and offer an explicit retry |
| Duplicate or stale action | unresolved | Test double-click and expired checkout session |
| Timeout and retry | unresolved | Add bounded timeout and safe retry behavior |
| Keyboard and focus restoration | unresolved | Replace clickable `div` with native controls; test Escape, Tab order, visible focus, and opener focus restoration |
| 320 CSS-pixel reflow | unresolved | Manually verify disclosures and actions remain visible |
| Long and translated content | unresolved | Test expanded price, renewal, and cancellation copy |
| Performance at click-to-hosted-checkout-handoff | unresolved | Measure request-to-redirect latency without adding third-party UI code |

## Trust

Changed boundary: browser → `/api/checkout` → payment provider, plus browser/server → subscription-management portal.

Key controls:

- A01 Broken Access Control: derive customer ownership server-side; test user A cannot create or manage user B’s subscription.
- A05 Injection: strict request schema and allowlisted plan identifier.
- A06 Insecure Design: prevent browser-controlled price, currency, ownership, or redirects.
- A08 Software/Data Integrity: verify payment callback authenticity, freshness, expected account and amount, and idempotency.
- A09 Logging: record safe correlation and failures without payment details or secrets.
- A10 Exceptional Conditions: bounded timeouts/retries, duplicate handling, reconciliation, and safe failure.
- ASVS 5.0.0: applicable Level 1 and payment-related Level 2 requirements must be selected from the official catalog; exact IDs remain unresolved and are not guessed.
- Privacy: marketing consent purpose, processor, retention, withdrawal, and deletion lifecycle remain unresolved.
- Supply chain: no new dependency is proposed; lockfile and dependency-release evidence remain unverified.
- Generated payment changes require a named human reviewer and independent negative tests at the real server boundary.

## Release

Artifact: unimplemented annual Pro slice; Scope: annual hosted upgrade and self-service cancellation; Environment: unknown; Policy: VibeWorthy ship gates; Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Application source available | unresolved | Only `ARTIFACT.md` was present | Implementation cannot be inspected | unknown — assign owner | Provide the application worktree |
| manual check | Honest pre-commit terms | unresolved | Required contract only | Users could commit without informed terms | Product owner | Implement and review disclosure |
| residual risk | Self-service cancellation | unresolved | No cancellation path available for inspection | Obstructed cancellation | Billing owner | Implement and test customer-owned portal access |
| manual check | Server-owned pricing | unresolved | Proposed API contract only | Price or ownership manipulation | Backend reviewer | Add allowlist and direct negative tests |
| manual check | Callback integrity | unresolved | Provider/callback code unavailable | Forged or replayed billing events | Billing owner | Test authenticity, freshness, idempotency, retry, and reconciliation |
| manual check | Accessibility states | unresolved | Existing clickable `div` reported | Keyboard users may not complete the flow | Frontend owner | Test semantics, focus, reflow, errors, and translated content |
| manual check | Payment logic review | unresolved | No named independent reviewer | Generated critical logic lacks an independent oracle | unknown — assign owner | Assign reviewer and retain boundary-test evidence |
| manual check | Native verification | unresolved | `typecheck`, `test`, and `build` were not run | Compile or regression failures remain unknown | Engineering owner | Run after implementation |
| residual risk | Release artifact and supply chain | unresolved | No candidate artifact, SBOM, provenance, or dependency review | Release integrity unknown | Release owner | Assemble evidence for the exact candidate |

Decision: `NO-GO`.

This is a build decision and contract, not an implemented or releasable change. Release remains blocked until the source is available, the slice is implemented, and payment, accessibility, privacy, and release gates are independently verified. It does not establish security, compliance, profitability, or production readiness.

## Actions

External actions performed: none. No files were modified, no checkout was created, and no verification scripts were run.