## Mode

Requested mode: implementation.  
Effective mode: `ship`, elevated because this changes payment, subscription, personal-data, and public API behavior.

No files were modified because the supplied workspace contains only the starting-artifact description, not the application source.

## Evidence

User-provided facts:

- React/TypeScript project using npm and `package-lock.json`.
- Existing `POST /api/checkout` hosted-checkout flow.
- Upgrade dialog has inaccessible clickable `div`.
- Marketing consent is currently preselected.
- `src/theme.css` has unrelated local changes that must be preserved.

Unknown: provider API, authentication/customer ownership, price, currency, renewal date, billing-portal support, tests, deployment configuration, and market evidence.

Assumption: existing users considering Pro are the initial buyer cohort. The first useful signal is a successfully confirmed annual Pro subscription—not merely opening checkout.

## Contract

### Decision

Choose the existing hosted checkout.

| Criterion | Option A: hosted checkout | Option B: browser card form |
| --- | --- | --- |
| User value | Familiar, short upgrade flow | More presentation control |
| Security/privacy risk | Card data stays with provider | Expands card-data and browser attack boundaries |
| Maintenance | Extends an existing integration | New validation, tokenization, failure, and compliance work |
| Accessibility | Provider flow plus local dialog must be verified | Entire card experience becomes our responsibility |
| Cost | Existing operational model | Higher implementation and support cost |
| Portability | Provider-dependent | Potentially more portable, still processor-dependent |
| Reversibility | Plan mapping can be changed server-side | Larger migration surface |

Chosen: Option A.

Accepted cost: less control over checkout presentation and provider dependency.

Revisit trigger: the hosted checkout cannot show the total annual price, renewal cadence, cancellation terms, or accessible completion flow before payment.

### Conversion constraints

I would not implement three requested patterns:

- Marketing consent remains unchecked and optional.
- Total price and automatic-renewal cadence are disclosed before checkout commitment.
- Cancellation has an accessible self-service route; email may remain an additional route.

The annual plan may be the initially selected plan if its price and cadence are prominent and users can clearly choose another available option.

### Smallest slice

Proposed changes:

1. Replace the clickable upgrade `div` with a semantic button and accessible dialog behavior.
2. Present annual Pro with total price, billing cadence, renewal disclosure, and cancellation terms.
3. Keep marketing consent unchecked and separate from purchase acceptance.
4. Send only `{ plan: "pro_annual" }` to `POST /api/checkout`.
5. Resolve `pro_annual` on the server through an allowlist to a server-owned provider price.
6. Reject unknown plans and ignore/reject client-supplied price IDs, amounts, currencies, customer ownership, and redirect URLs.
7. Redirect to the hosted checkout with duplicate-submit protection and recoverable errors.
8. Expose a keyboard-accessible self-service “Manage subscription” route for cancellation.
9. Preserve `src/theme.css` and avoid new dependencies.

Non-goals: monthly-plan redesign, custom card collection, pricing experimentation, unrelated styling, webhook redesign, analytics expansion, and provider migration.

Rollback: remove the annual plan mapping and UI entry while retaining the existing checkout path.

## Slices

One proposed vertical slice:

> An eligible user opens the accessible upgrade dialog, sees complete annual subscription terms, optionally chooses marketing consent, and reaches hosted checkout for the server-approved annual Pro price.

Enforcement boundary: `POST /api/checkout`, where the stable plan identifier is mapped to the provider price.

Acceptance examples:

- `pro_annual` creates a session using the configured annual Pro price.
- An unknown plan or browser-supplied price/redirect value is rejected.
- Repeated clicks create at most one active request.
- A checkout error restores the enabled action and provides a retry.
- Dialog close or redirect failure restores focus appropriately.
- Cancellation is available without contacting support.

## Trust

Changed boundary: browser → checkout API → payment provider.

Priority checks:

- OWASP A01: authenticate the buyer and derive customer ownership server-side.
- A05/A06: allowlist the plan and prevent price or redirect manipulation.
- A08: verify provider callbacks, freshness, replay resistance, and idempotency if subscription state depends on webhooks.
- A09: log checkout failures without card data, secrets, or unnecessary personal data.
- A10: bound provider timeouts and retries; recover safely from duplicate requests.

Applicable ASVS 5.0.0 Level 1 and Level 2 payment requirements remain unresolved until their exact IDs are selected from the official catalog and independently reviewed. Generated payment code and tests cannot be their own release oracle.

## Release

Release status was not evaluated. Source code, provider configuration, authentication, callbacks, tests, and runtime behavior were unavailable. No `GO`, `CONDITIONAL`, or `NO-GO` recommendation is issued.

## Verification plan

Run after implementation:

- `npm run typecheck`
- `npm test`
- `npm run build`

Add tests for:

- Annual plan allowlist mapping.
- Unknown/malformed plan rejection.
- Rejection of client-controlled price, currency, customer, and redirect data.
- Authentication and customer ownership.
- Provider error, timeout, retry, and duplicate submission.
- Accessible dialog name, keyboard operation, focus trap/return, and unchecked consent.
- Pre-commit renewal, price, and cancellation disclosure.
- Self-service cancellation access.
- Confirmation that `src/theme.css` remains unchanged.

| State or boundary | Disposition | Next action |
| --- | --- | --- |
| Loading | unresolved | Verify disabled action and announced progress |
| Empty | not applicable — dialog always has plan content | Confirm invariant |
| Error and recovery | unresolved | Test API/provider failure and retry |
| Duplicate or stale action | unresolved | Test double-click and expired session |
| Timeout and retry | unresolved | Test bounded timeout and safe retry |
| Keyboard and focus restoration | unresolved | Manual keyboard and focus test |
| 320 CSS-pixel reflow | unresolved | Manual reflow test |
| Long and translated content | unresolved | Test expanded disclosure copy |
| Performance at click-to-hosted-checkout handoff | unresolved | Measure request-to-redirect latency |

External actions performed: none.