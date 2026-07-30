## Decision

Choose the existing hosted checkout. It matches the project standard, minimizes card-data exposure, avoids a new payment form, and is the smallest reversible change.

Requested mode: implementation. Effective mode: `ship`, elevated because this changes billing and marketing consent.

I would not implement these conversion requests:

- Marketing consent preselected — consent must be an unchecked, optional choice.
- Renewal disclosed after purchase — annual price, renewal cadence, and cancellation terms must appear before checkout.
- Email-only cancellation — cancellation must be reasonably accessible, preferably through the hosted provider’s customer portal.

The annual Pro option itself may be selected by default if its full annual price and renewal terms are prominent.

## Build contract

User-provided repository facts:

- React and TypeScript using npm.
- Hosted checkout already exists through `POST /api/checkout`.
- `typecheck`, `test`, and `build` scripts exist.
- `src/theme.css` has unrelated work that must remain untouched.

Observable limitation: the workspace contains only `ARTIFACT.md` and the skill files—not the application, package manifest, lockfile, or Git repository. Therefore no implementation or checks were possible.

Contract for the change:

- Add one accessible annual Pro upgrade action.
- Display total annual price, billing period, automatic-renewal terms, and cancellation method before checkout.
- Make marketing consent optional and unchecked; declining must not prevent purchase.
- Use a semantic `<button>` instead of the clickable `<div>`.
- Disable duplicate submission and show accessible loading and recoverable error states.
- Create the annual checkout session server-side using a fixed, allowlisted price identifier. Never accept a client-supplied amount or price ID.
- Redirect only to provider-generated checkout URLs.
- Provide a visible self-service cancellation/customer-portal route.
- Preserve `src/theme.css` and avoid new dependencies.

Non-goals: custom card collection, pricing-system refactoring, unrelated styling changes, monthly-plan redesign, deployment, or production checkout execution.

## Smallest vertical slice

1. Update `UpgradeDialog.tsx` with an accessible annual Pro selection, complete renewal disclosure, an unchecked marketing checkbox, and keyboard/focus-safe controls.
2. Update `BillingButton.tsx` to submit only the intended annual-plan key and explicit consent value, while handling loading, duplicate clicks, errors, and retry.
3. Update `api/checkout.ts` to authenticate the customer where applicable, map the annual-plan key to a server-owned hosted-checkout price, reject malformed or unsupported input, and return only a validated checkout URL.
4. Add the existing provider’s customer-portal link or endpoint for self-service cancellation.

Acceptance example: a user sees the full annual commitment and renewal terms, independently chooses whether to receive marketing, starts hosted checkout once, and can later reach cancellation without emailing support.

## Verification plan

Automated checks to run once the application is available:

```bash
npm run typecheck
npm test
npm run build
python skill/vibeworthy/scripts/preflight.py . --format text
```

Targeted tests:

- Annual plan maps to the fixed server-side price.
- Unknown plans, client-supplied prices, malformed bodies, unauthenticated requests, and duplicate/replayed submissions are rejected safely.
- Marketing consent defaults to `false` and does not affect checkout eligibility.
- Provider failures produce a recoverable error without duplicate sessions.
- Checkout redirects cannot be supplied by the client.

Manual checks:

- Complete dialog, checkout initiation, error recovery, and cancellation with keyboard only.
- Verify focus placement/restoration and accessible status announcements.
- Reflow at 320 CSS pixels and test zoom/long text.
- Confirm price, renewal, consent, and cancellation disclosures appear before commitment.
- Have a responsible human independently review payment enforcement and negative tests before release.

No checks were run because the application files are absent.
