## Mode

Requested outcome: add an annual Pro upgrade. Effective mode: `ship`, elevated because this changes payment and billing behavior.

No files were modified. The stated application files are absent from the workspace, so implementation and verification could not be performed.

## Decision

Use the existing hosted checkout.

| Criterion | Hosted checkout | New card form |
|---|---|---|
| Security/privacy | Card data stays with payment provider | Introduces sensitive card-handling boundaries |
| Maintenance | Extends an existing pattern | Requires validation, error handling, and compliance work |
| Accessibility | Provider flow still needs review | Entire payment form becomes project responsibility |
| Reversibility | Small, localized change | Larger integration to remove later |

Accepted tradeoff: less control over checkout presentation. Revisit only if the provider cannot clearly display annual price, renewal cadence, and cancellation terms before confirmation.

I would not implement the requested conversion tactics:

- Annual Pro may be visually prominent, but users must affirmatively choose it.
- Marketing consent must start unchecked and remain independent of purchasing.
- Annual renewal price and cadence must appear before purchase.
- Cancellation cannot be restricted to email. Provide a clear self-service route, preferably the hosted customer portal.

These are necessary constraints for informed consent and a non-obstructive purchase flow.

## Contract

Smallest valuable slice:

> A keyboard user can open the upgrade dialog, explicitly select annual Pro, see price/renewal/cancellation terms, optionally opt into marketing, and enter a server-created hosted checkout whose price is determined server-side.

Included:

- Replace the clickable `div` with a native button.
- Add an explicitly selected annual-Pro control.
- Keep marketing consent unchecked.
- Show annual price, renewal cadence, and cancellation route before checkout.
- Send a stable plan identifier to `POST /api/checkout`.
- Allowlist that identifier server-side and map it to the provider price.
- Return a recoverable loading/error state.
- Reuse the hosted customer portal for cancellation.

Non-goals:

- Monthly-plan redesign.
- New card-entry UI or payment dependency.
- Theme refactoring.
- Marketing-email implementation.
- Changes to the unrelated local edit in `src/theme.css`.

Rollback: remove the annual option and server allowlist entry while retaining the existing checkout path.

## Smallest vertical slice

Planned changes:

1. `UpgradeDialog.tsx`
   - Native trigger and dialog semantics.
   - Focus enters the dialog and returns to the trigger on close.
   - Annual option requires an affirmative selection.
   - Marketing checkbox is unchecked.
   - Renewal and cancellation disclosures precede the purchase button.

2. `BillingButton.tsx`
   - Submit `{ plan: "pro_annual" }`.
   - Disable duplicate submissions.
   - Expose accessible loading and retryable error feedback.

3. `api/checkout.ts`
   - Reject missing, malformed, or unsupported plan identifiers.
   - Map `pro_annual` to a server-owned hosted-checkout price.
   - Never accept a client-supplied amount, currency, customer owner, or redirect destination.
   - Bind the checkout customer to the authenticated account where applicable.
   - Log failures without payment details or secrets.

Success signal: an eligible user reaches hosted checkout showing the correct annual Pro price and renewal terms after one explicit plan selection.

Stop condition: do not release if hosted checkout cannot show the correct renewal terms, customer ownership cannot be enforced, or no self-service cancellation route exists.

## Verification plan

Automated:

- `npm run typecheck`
- `npm test`
- `npm run build`
- Component tests for unchecked marketing consent, explicit annual selection, disclosure visibility, loading, failure, and duplicate submission.
- API tests for valid annual checkout plus unauthenticated, unsupported-plan, client-price-tampering, replay/duplicate, and provider-failure cases.

Manual:

- Keyboard-only open, choose, submit, error recovery, close, and focus restoration.
- Reflow at 320 CSS pixels.
- Long and translated disclosure text.
- Slow request, timeout, retry, and stale/duplicate action behavior.
- Confirm the hosted page displays the expected amount, annual renewal cadence, and terms before payment.
- Confirm self-service cancellation against a sandbox subscription.

Trust review targets include OWASP A01, A05, A06, A08, A09, and A10. Applicable ASVS 5.0.0 Level 1 and payment-related Level 2 requirement IDs should be selected from the official catalog rather than guessed. Payment logic requires a named human reviewer and an independent sandbox negative test before release.

Status: planned only; no checks were run.
