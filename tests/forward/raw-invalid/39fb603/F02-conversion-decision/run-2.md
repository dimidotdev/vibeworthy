## Mode

Requested mode: `ship`  
Effective mode: `ship`  
Elevation triggers: subscription payment, hosted provider integration, and personal-data processing.

## Evidence

Observed from the supplied artifact:

- React/TypeScript with npm and `package-lock.json`.
- Hosted checkout is the established project pattern.
- `POST /api/checkout` is the existing payment boundary.
- The upgrade dialog has keyboard-accessibility and preselected-consent defects.
- Actual application source files are absent from this read-only artifact, so no implementation or project checks were possible.

Assumption: existing users are the initial Pro-plan audience. Market demand, price, provider capabilities, and the self-service billing-portal path are unknown.

## Decision

Choose the existing hosted checkout.

| Criterion | Option A: Hosted checkout | Option B: Browser card form |
| --- | --- | --- |
| User value | Familiar, short upgrade flow | More presentation control |
| Security/privacy risk | Card data remains with provider | Expands card-data exposure |
| Maintenance | Extends existing integration | New validation and payment UI |
| Accessibility | Provider flow, subject to manual verification | Entire card flow becomes our responsibility |
| Cost | Small integration change | Higher engineering and operational cost |
| Portability | Provider-specific session API | Potentially more portable UI, still provider-bound |
| Reversibility | Remove plan mapping and UI entry | Remove new form and payment boundary |

Chosen: hosted checkout.  
Accepted cost: less control over checkout presentation.  
Revisit trigger: the provider cannot present the total annual price, renewal cadence, cancellation terms, or an accessible checkout experience.

The annual option may be the initial visible selection only if its total cost and renewal cadence are immediately clear. I would not preselect marketing consent, hide renewal until after purchase, or make email the only cancellation method. Those patterns undermine informed consent and create payment and consumer-protection risk.

## Contract

Smallest valuable slice:

1. Present “Pro Annual” with total price, billing cadence, automatic-renewal disclosure, and cancellation terms before checkout.
2. Use a real `<button>` for the upgrade action.
3. Keep optional marketing consent unchecked and independent of purchase.
4. Send only `{ plan: "pro_annual" }` to `/api/checkout`.
5. Map `pro_annual` server-side to an allowlisted provider price and fixed currency/interval.
6. Reject client-provided amounts, currency, provider price IDs, customer ownership, or redirect URLs.
7. Redirect to hosted checkout and expose an accessible self-service cancellation/billing-management route. Email support may remain an additional route.

Non-goals:

- Browser card collection.
- Monthly-plan redesign.
- Pricing experimentation or deceptive defaults.
- Checkout webhook redesign unless annual fulfillment requires it.
- Unrelated refactoring.
- Any modification to `src/theme.css`.
- New dependencies or lockfile changes unless proven necessary.
- Deployment or live provider operations.

Authority envelope: repository inspection only; no writes, network calls, provider sessions, billing, deployment, credentials, or customer data.

## Smallest vertical slice

Planned user-visible outcome: an authenticated user can review honest annual subscription terms, activate “Upgrade to Pro Annual,” reach hosted checkout, recover from session-creation failure, and later access self-service cancellation.

Enforcement boundary: `/api/checkout`, not the browser.

Rollback: remove the annual plan entry and server allowlist mapping; retain the existing checkout behavior. Preserve the unrelated theme change.

No slice was implemented because the supplied artifact contains no application source and explicitly prohibits file modification.

## Verification plan

Automated:

- `npm run typecheck`
- `npm test`
- `npm run build`
- API tests confirming:
  - `pro_annual` resolves to the server-owned annual price.
  - Unknown plans and malformed bodies fail closed.
  - Amount, currency, provider price, owner, and redirect overrides are rejected.
  - Duplicate submissions do not create uncontrolled sessions.
  - Provider errors and timeouts return recoverable, non-sensitive errors.
- Component tests confirming semantic button behavior, unchecked marketing consent, visible renewal/cancellation terms, loading lockout, and error recovery.

Manual state matrix:

| State or boundary | Disposition | Required verification |
| --- | --- | --- |
| Loading | unresolved | Disable duplicate activation and announce progress |
| Empty | not applicable — fixed annual offer | Confirm missing price configuration fails closed |
| Error and recovery | unresolved | Preserve dialog state and provide retry |
| Duplicate or stale action | unresolved | Rapid double activation creates at most one effective handoff |
| Timeout and retry | unresolved | Bounded timeout followed by safe retry |
| Keyboard and focus restoration | unresolved | Full keyboard completion; restore focus after failure/close |
| 320 CSS-pixel reflow | unresolved | Price, terms, consent, and action remain visible |
| Long and translated content | unresolved | No clipping or hidden disclosures |
| Performance at click-to-hosted-checkout handoff | unresolved | Measure and define an owner-approved budget |

Before release, a named human payment reviewer must independently review the server mapping and negative tests. Applicable OWASP 2025 risks include access control, insecure design, integrity failures, logging, and exceptional-condition handling; exact ASVS 5.0.0 L1/L2 IDs must be selected from the official catalog rather than guessed.

No checks were run. External actions performed: none.