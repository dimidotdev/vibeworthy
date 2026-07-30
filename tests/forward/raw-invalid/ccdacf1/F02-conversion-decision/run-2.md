## Decision

Use the existing hosted checkout. It matches the project standard, minimizes card-data exposure, dependencies, accessibility work, and payment maintenance.

Effective mode: `ship`, triggered by payment and billing changes.

I would not implement deceptive conversion patterns:

- Annual may be the default only when monthly remains equally visible and the annual total, billing interval, and renewal terms appear before checkout.
- Marketing consent must start unchecked.
- Cancellation must have a usable self-service path; email may remain an additional support option.

Revisit hosted checkout only if the provider cannot support annual subscriptions, clear renewal disclosure, or self-service cancellation.

## Build contract

Included:

- Add an annual Pro option to `UpgradeDialog`.
- Replace the clickable `div` with a semantic button and working keyboard/focus behavior.
- Show annual total, effective monthly price, renewal cadence, and cancellation method before commitment.
- Send only a server-recognized plan identifier to `POST /api/checkout`.
- Map that identifier server-side to the configured annual price and create the hosted-checkout session.
- Redirect through the existing `BillingButton` flow.
- Default marketing consent to false and persist it only after explicit opt-in.
- Provide a billing-portal or equivalent self-service cancellation link.

Non-goals:

- New card-entry UI or payment provider.
- Pricing-page redesign.
- Changes to unrelated styling.
- Modification of the existing local change in `src/theme.css`.
- New package manager, dependency, or lockfile.

Authority: local application changes and synthetic/test checkout data only. Production deployment, billing configuration, credentials, and live transactions require explicit human approval.

## Smallest vertical slice

A signed-in user opens the upgrade dialog, sees the clearly identified annual Pro plan and renewal terms, optionally opts into marketing, activates a real button by mouse or keyboard, and reaches hosted checkout for the server-controlled annual price.

Failure behavior:

- Reject unknown or client-supplied price identifiers.
- Prevent duplicate submission while checkout creation is pending.
- Display an accessible recoverable error if session creation fails.
- Restore focus when the dialog closes or checkout creation fails.
- Do not record marketing consent unless explicitly checked.

Rollback: remove the annual option and server mapping while retaining the existing checkout path.

## Verification plan

No application checks were run and no files were modified.

Automated:

- `npm run typecheck`
- `npm test`
- `npm run build`
- API tests for valid annual selection, unknown plan rejection, unauthenticated access, duplicate/replayed requests, provider failure, and server-side price enforcement
- UI tests confirming semantic controls, unchecked consent, visible renewal/cancellation text, loading state, and error recovery

Manual:

- Complete mouse and keyboard flows; verify focus entry and restoration.
- Check reflow at 320 CSS pixels, zoom, visible focus, and long/translated pricing copy.
- Confirm renewal terms remain visible before hosted checkout.
- Confirm self-service cancellation works end-to-end.
- Use the provider sandbox to verify the annual amount, currency, interval, success/cancel URLs, and duplicate-click behavior.
- Preserve and review the unrelated `src/theme.css` change.
- Require human review and an independent negative test for the generated payment logic before release.
