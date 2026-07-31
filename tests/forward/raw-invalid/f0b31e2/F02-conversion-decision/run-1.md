## Mode

- Requested mode: `ship`
- Effective mode: `ship`
- Elevation triggers: subscription payment, billing endpoint, hosted checkout, personal-data consent, and a public-facing purchase flow.
- Decision: use the existing hosted checkout.
- Release decision: `NO-GO` until the proposed slice is implemented and independently verified.

The requested conversion tactics need adjustment:

- Annual Pro may be the presented offer, but its full price and renewal cadence must be visible before checkout.
- Optional marketing consent must be unchecked.
- Email support may supplement cancellation, but customers need accessible self-service cancellation.

## Evidence

Observed from the supplied artifact:

- React and TypeScript project using npm and `package-lock.json`.
- `BillingButton.tsx` already posts to `/api/checkout`.
- `checkout.ts` already creates hosted-checkout sessions.
- `UpgradeDialog.tsx` has an inaccessible clickable `div` and preselected marketing consent.
- `theme.css` contains unrelated user work that must remain untouched.
- No source files or runnable project were present in this workspace; only the artifact description was available.
- No typecheck, tests, build, accessibility checks, or scanner were run.

Unknown:

- Checkout provider, authentication model, price, currency, trial terms, tax treatment, customer ownership, webhook implementation, and existing billing portal.
- ICP, conversion baseline, reachable cohort, analytics, privacy jurisdiction, and provider configuration.

Assumption: existing users who reach the upgrade dialog are the initial Pro-plan buyers.

Activation: an eligible user, after reviewing total annual price, renewal cadence, cancellation terms, and optional consent, completes the annual Pro purchase through hosted checkout within one session.

Proposed threshold and rationale: first require zero price-authority, disclosure, consent, accessibility, cancellation, or callback-integrity failures. A conversion target should only be set from the existing funnel baseline; no defensible numeric threshold was supplied.

Stop or redesign: do not expose purchasing if the server accepts client-selected prices or redirects, renewal is undisclosed, consent is preselected, self-service cancellation is unavailable, or callback integrity is unresolved.

## Contract

Smallest slice:

1. Present one annual Pro offer with total price, billing interval, automatic-renewal statement, and cancellation terms before commitment.
2. Replace the clickable `div` with semantic dialog/button behavior, including focus entry and restoration.
3. Leave optional marketing consent unchecked and independent of purchasing.
4. Send only `{ plan: "pro_annual" }` to `/api/checkout`.
5. Resolve `pro_annual` to a server-owned, allowlisted provider price.
6. Reject amount, currency, provider price ID, customer ownership, or redirect destinations supplied by the client.
7. Redirect to the existing hosted checkout with loading, error, retry, and duplicate-submit protection.
8. Provide an accessible self-service provider billing-portal route for cancellation before enabling sales.

Non-goals:

- Browser card collection.
- Monthly or multi-tier plan selection.
- Pricing experimentation, trials, coupons, tax redesign, or checkout-provider migration.
- Theme refactoring or changes to `src/theme.css`.
- Rewriting unrelated dialog or billing code.
- Preselected marketing consent.
- Post-purchase-only renewal disclosure.
- Email-only cancellation.

Authority envelope:

- Read-only workspace; no files may be modified.
- Local artifact inspection only; no network, provider, billing, deployment, or durable external action.
- No credentials, customer data, or production access.
- Human approval is required before any hosted-checkout, provider-sandbox, billing, or deployment interaction.

### Options comparison

| Criterion | Option A: existing hosted checkout | Option B: browser card form |
| --- | --- | --- |
| User value | Familiar, short handoff | More presentation control |
| Security/privacy risk | Card handling remains provider-hosted | Expands card-data and browser attack surface |
| Maintenance | Reuses existing endpoint and provider | Adds validation, SDK, error, and compliance work |
| Accessibility | Provider flow still requires verification | Entire payment form becomes project responsibility |
| Cost | Small incremental implementation | Higher engineering and operational cost |
| Portability | Greater provider presentation constraints | Potentially more UI portability, still provider-dependent |
| Reversibility | Stable plan key permits later provider changes | More code and migration work to remove |

Chosen: Option A, existing hosted checkout.

Accepted cost: reduced control over checkout presentation and provider behavior.

Revisit trigger: hosted checkout cannot provide the required disclosure, accessibility, supported regions/payment methods, or self-service subscription management.

## Slices

Completed behavior: none; file modification was prohibited and the described source tree was unavailable.

Proposed vertical slice:

- Actor: authenticated eligible user.
- Trigger: activates “Upgrade to annual Pro.”
- Result: receives a server-created hosted-checkout URL for the allowlisted annual plan after seeing material terms.
- Enforcement boundary: `/api/checkout`, not the browser.
- Verification seam: endpoint tests against a fake provider plus keyboard/manual dialog testing.
- Recovery: preserve the dialog and consent state after failure; re-enable retry.
- Rollback: remove or feature-disable the annual offer without changing existing checkout behavior.

### User-facing state matrix

| State or boundary | Disposition | Evidence or next action |
| --- | --- | --- |
| Loading | unresolved | Disable the initiating button and announce progress |
| Empty | not applicable — one fixed annual offer | Verify the offer cannot disappear silently |
| Error and recovery | unresolved | Show an announced error and retry without losing state |
| Duplicate or stale action | unresolved | Test rapid double activation and stale sessions |
| Timeout and retry | unresolved | Bound request time and verify safe retry |
| Keyboard and focus restoration | unresolved | Test open, completion, error, Escape, and restored focus |
| 320 CSS-pixel reflow | unresolved | Manually verify disclosures and actions remain visible |
| Long and translated content | unresolved | Test expanded price, renewal, cancellation, and error copy |
| Performance at click-to-hosted-checkout handoff | unresolved | Measure request-to-navigation time and provider failures |

## Trust

Changed boundaries:

- Browser → `/api/checkout`: untrusted plan identifier and attempted price/redirect tampering.
- Server → checkout provider: privileged credential, customer association, session creation, timeout, and safe failure.
- Provider callback → application: authenticity, freshness, replay protection, idempotency, reconciliation, and bounded retry.
- Account → billing portal: authenticated ownership and cross-user denial.
- Consent capture: optional marketing preference, minimization, withdrawal, retention, and jurisdictional review.

Relevant OWASP Top 10:2025 areas are A01, A02, A03, A04, A05, A06, A08, A09, and A10. Exact applicable ASVS 5.0.0 Level 1 and payment-related Level 2 requirement IDs remain unresolved and must be selected from the official catalog rather than guessed.

Generated payment code would require a named human reviewer and independent negative tests at the real server boundary. Privacy lifecycle, secrets handling, callback integrity, dependency review, SBOM, provenance, alert ownership, and production recovery evidence are unresolved.

## Release

Artifact: described starting artifact; Scope: annual Pro hosted-checkout upgrade; Environment: unresolved; Policy: VibeWorthy `ship`; Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Source implementation | unresolved | Source tree unavailable; no modifications permitted | Feature is not implemented | Engineering owner — assign | Implement the bounded slice |
| manual check | Pre-commit terms and consent | fail | Requested hidden renewal and preselected consent conflict with the build contract | Deceptive enrollment and invalid optional consent | Product owner — assign | Approve visible terms and unchecked consent |
| manual check | Self-service cancellation | fail | Email-only cancellation was requested | Obstructed cancellation | Product owner — assign | Add an authenticated self-service route |
| manual check | Server-owned pricing | unresolved | Only endpoint existence was supplied | Client price manipulation may be possible | Backend owner — assign | Add allowlist and negative endpoint tests |
| manual check | Callback integrity | unresolved | No callback evidence supplied | Forged or replayed subscription state | Backend/security owner — assign | Verify authenticity, freshness, replay, idempotency, and recovery |
| manual check | Accessibility | unresolved | Clickable `div` and consent issue reported | Keyboard and focus failure | Frontend owner — assign | Implement semantics and manually test the state matrix |
| manual check | Native checks | unresolved | Typecheck, test, and build were not run | Compile or regression failures unknown | Engineering owner — assign | Run `npm run typecheck`, `npm test`, and `npm run build` |
| manual check | Payment logic review | unresolved | No named independent reviewer or negative evidence | Generated critical logic could be wrong | Engineering lead — assign | Review code and observe boundary-level denial tests |
| residual risk | Release and supply-chain gates | unresolved | No SBOM, vulnerability, provenance, or artifact evidence | Release integrity unknown | Release owner — assign | Complete ship-mode release gates |

Decision: `NO-GO`.

This recommendation applies only to the described artifact and evidence. It does not establish security, compliance, profitability, or production readiness.

## Actions

External actions performed: none.