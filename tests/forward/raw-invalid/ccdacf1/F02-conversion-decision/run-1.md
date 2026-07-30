## Mode

- Requested outcome: add an annual Pro upgrade.
- Effective mode: `ship`.
- Elevation triggers: payment processing, public checkout endpoint, marketing-consent data, and recurring billing.
- No files were modified.

## Decision

Use the existing hosted checkout.

| Criterion | Existing hosted checkout | New card form |
|---|---|---|
| Delivery | Small extension | New payment UI and validation |
| Security scope | Card data remains with provider | Application handles a larger PCI-sensitive boundary |
| Accessibility | Provider flow can be reused | Entire card flow must be implemented and tested |
| Recovery | Existing session/error pattern | More partial-payment states |
| Maintenance | Low | High |

Accepted tradeoff: dependence on the checkout provider’s supported fields and UX. Revisit only if it cannot represent annual recurring pricing or required disclosures accessibly.

I would not implement three requested dark patterns:

- Annual Pro may be visibly marked “Recommended” and selected initially only if its full annual price and renewal cadence are immediately visible and alternatives are equally usable.
- Marketing consent must be unchecked and optional.
- Renewal and cancellation terms must appear before checkout. Email cancellation is acceptable only if it is a reliable, clearly disclosed process—not an intentionally obstructive one.

## Build contract

Target user: an existing user choosing Pro at the upgrade moment.

Smallest valuable slice: the user selects annual Pro, sees its price, renewal cadence, cancellation route, and optional marketing choice, then reaches the existing hosted checkout configured with a server-controlled annual price.

Included:

- Replace the clickable `div` with a semantic, keyboard-operable dialog control.
- Present annual Pro as recommended, with complete recurring-price disclosure.
- Make marketing consent unchecked and independent of purchase.
- Send a stable plan identifier such as `pro_annual` to `/api/checkout`.
- Resolve the provider price on the server; never accept a client-supplied amount or price ID.
- Disable duplicate submission and show accessible loading, failure, and retry states.
- Preserve the unrelated `src/theme.css` change.

Non-goals:

- New card-entry UI.
- Monthly-plan redesign.
- Billing portal, webhook, entitlement, or cancellation-system rewrites.
- New dependencies or lockfile changes.
- Marketing enrollment unless separately and explicitly consented to.

Success signal, proposed: completed annual hosted-checkout sessions divided by eligible dialog views, monitored alongside checkout abandonment and consent rate. No baseline or target was supplied.

Stop/redesign condition: users cannot understand the total price or renewal terms, keyboard users cannot complete the flow, or the provider cannot enforce the annual price server-side.

## Smallest vertical slice

1. `UpgradeDialog.tsx`
   - Use semantic dialog/button controls with focus entry and restoration.
   - Show “Pro annual — [full price]/year, renews annually until cancelled.”
   - Clearly disclose the email cancellation process before commitment.
   - Keep marketing consent unchecked.

2. `BillingButton.tsx`
   - Submit `{ plan: "pro_annual" }`.
   - Prevent duplicate clicks.
   - Announce loading and errors and permit retry.

3. `api/checkout.ts`
   - Allowlist `pro_annual`.
   - Map it server-side to the configured hosted-checkout price.
   - Reject unknown, malformed, and client-priced requests.
   - Return a safe error without exposing provider details.

Rollback: remove the annual option and mapping; the existing checkout behavior remains intact.

## Verification plan

Automated checks to run:

```bash
npm run typecheck
npm test
npm run build
```

Add focused tests proving:

- `pro_annual` maps to the correct server-owned price.
- Unknown plans and client-supplied prices are rejected.
- Duplicate submission creates at most one checkout attempt.
- Provider failure produces a recoverable UI error.
- Marketing consent defaults to false and is not required for purchase.
- Renewal and cancellation disclosures render before checkout.

Manual checks:

- Complete and recover from the flow using only a keyboard.
- Verify initial focus, visible focus, Escape behavior, and focus restoration.
- Test at 320 CSS pixels and 200% zoom.
- Check long and translated price/disclosure text.
- Exercise slow response, timeout, retry, stale dialog, and double activation.
- Confirm the hosted checkout shows the same amount and renewal cadence.
- Have a qualified human independently review the payment mapping and negative API tests.
- Complete privacy review for marketing-consent storage, purpose, retention, withdrawal, and deletion.

OWASP areas requiring evidence include access control, injection, insecure design, integrity, logging, and exceptional-condition handling. Exact ASVS 5.0.0 requirement IDs remain unresolved pending review against the official catalog.

No project checks were run: the described application files and `package.json` were not present in the provided workspace.
