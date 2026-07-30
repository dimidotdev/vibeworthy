## Decision

Use the existing hosted checkout. It minimizes card-data exposure, follows the project standard, and is easier to reverse than introducing a browser card form.

I would not implement:

- Preselected marketing consent.
- Renewal disclosure only after purchase.
- Email-only cancellation.

These are deceptive or obstructive patterns. Marketing must be unchecked and optional; annual price, renewal cadence, and cancellation terms must appear before checkout; cancellation should have a self-service path.

Effective mode: `ship`, elevated because this changes payment and personal-data behavior.

## Build contract

- Add one clearly identified Annual Pro option.
- Show total annual price, billing period, automatic-renewal terms, and cancellation method before commitment.
- Use a semantic button instead of the clickable `div`, with visible focus and keyboard operation.
- Keep marketing consent separate, unchecked, and non-blocking.
- Send only a server-recognized plan identifier to `POST /api/checkout`.
- Resolve the trusted annual price server-side; never accept a client-supplied amount or checkout URL.
- Redirect to the hosted checkout with loading, duplicate-submit prevention, and recoverable error handling.
- Preserve `src/theme.css` and all unrelated work.
- Add no dependency and retain npm/package-lock conventions.

Non-goals: custom card collection, pricing-page redesign, unrelated refactoring, or subscription-management implementation beyond exposing/linking the provider’s available self-service cancellation route.

## Smallest vertical slice

1. `UpgradeDialog.tsx` presents Annual Pro with transparent renewal and cancellation text.
2. Its native upgrade button invokes the existing `BillingButton` flow.
3. `BillingButton.tsx` posts an allowlisted annual-plan ID and handles pending/error states.
4. `checkout.ts` maps that ID to trusted server-side hosted-checkout configuration and rejects unknown or malformed plans.
5. Marketing consent remains unchecked and is recorded only after explicit selection.

Acceptance example: a keyboard user can review the annual terms, leave marketing unchecked, activate upgrade once, and reach hosted checkout for the correct annual product.

Negative cases: unknown plan IDs are rejected without creating a session; repeated clicks create at most one active request; checkout failure restores an actionable button and reports an accessible error.

Rollback: remove the annual option and server mapping; the existing checkout path remains intact.

## Verification plan

No implementation or checks were run because the supplied workspace contains only `ARTIFACT.md`, not the referenced source files.

When the source tree is available:

- Review the diff to confirm `src/theme.css` and unrelated changes remain untouched.
- Run `npm run typecheck`, `npm test`, and `npm run build`.
- Test valid annual checkout plus malformed, unknown, duplicate, timeout, and provider-error requests.
- Confirm the server controls product and price and that authentication/authorization requirements cannot be bypassed through direct API calls.
- Manually verify keyboard operation, focus visibility/restoration, accessible error announcements, and 320px reflow.
- Confirm annual price, renewal, cancellation, and optional marketing choice are visible before checkout.
- Have a responsible human independently review the generated payment logic and test it against the real sandbox enforcement boundary before release.
