## Mode

- Requested mode: `ship`
- Effective mode: `ship`
- Elevation triggers: payment, hosted checkout, public API endpoint, marketing-consent processing.
- Decision: use the existing hosted checkout.
- The requested hidden renewal, preselected marketing consent, and email-only cancellation are excluded. Renewal and cancellation terms must appear before purchase; optional consent remains unchecked; cancellation must be self-service.

## Evidence

Known from the user-provided artifact description:

- React/TypeScript with npm and `package-lock.json`.
- `POST /api/checkout` and hosted checkout already exist.
- `UpgradeDialog.tsx` has inaccessible clickable `div` behavior and preselected marketing consent.
- `src/theme.css` contains unrelated work to preserve.
- `typecheck`, `test`, and `build` scripts reportedly exist.

Observed in this workspace:

- The application files, `package.json`, lockfile, and README are absent.
- The workspace is not a Git checkout, so the theme change and artifact identity cannot be independently inspected.
- Market evidence, price, provider, authentication model, and existing cancellation facilities are unknown.

Assumption: existing users encountering the upgrade dialog are the initial cohort. The conversion effect remains unproven; use completed annual checkout and subsequent refund/cancellation rates as evidence, without employing deceptive defaults.

## Contract

Smallest slice:

1. Present annual Pro as an explicit choice, not an automatically accepted subscription.
2. Show total annual price, billing cadence, automatic renewal, and cancellation terms before checkout.
3. Leave marketing consent unchecked and independent of purchase.
4. Replace clickable `div` behavior with native button/dialog semantics and restore focus on close.
5. Send only `{ plan: "pro_annual" }` to `/api/checkout`.
6. Resolve `pro_annual` server-side to an allowlisted provider price, currency, and annual interval.
7. Reject client-supplied amount, currency, provider price ID, customer owner, and redirect URLs.
8. Provide an accessible self-service “Manage subscription” route; email may remain an additional option.
9. Preserve `src/theme.css`, add no dependency, and retain npm plus `package-lock.json`.

Explicit non-goals:

- Browser card collection.
- Monthly-plan redesign.
- Custom payment fields.
- New payment provider.
- Preselected marketing consent.
- Hidden renewal disclosures.
- Email-only cancellation.
- Unrelated styling or theme cleanup.
- Deployment, live checkout creation, webhook changes, or production billing.

### Options

| Criterion | Option A: existing hosted checkout | Option B: browser card form |
| --- | --- | --- |
| User value | Familiar, smaller upgrade path | Greater presentation control |
| Security/privacy risk | Card data remains provider-hosted | Adds card-data and client-validation boundaries |
| Maintenance | Reuses current integration | Requires payment-element lifecycle and error handling |
| Accessibility | Provider flow must be verified | Entire card flow becomes project responsibility |
| Cost | Minimal implementation/operations | Higher engineering and compliance burden |
| Portability | Provider-dependent | Still provider-dependent unless handling cards directly |
| Reversibility | Remove plan mapping and UI | More code and boundaries to unwind |

Chosen: Option A.

Accepted cost: less control over checkout presentation and provider UX.

Revisit trigger: the provider cannot display annual price/renewal terms accessibly, support authenticated customer ownership, or provide self-service subscription management.

Authority envelope: read-only local inspection only; no network, credentials, customer data, checkout session, billing, deployment, or external communication authorized.

## Slices

Planned vertical slice: an authenticated user selects annual Pro, reviews honest terms, optionally opts into marketing, and reaches hosted checkout for the server-owned annual price.

Enforcement boundary: `/api/checkout`, not the browser.

Failure behavior:

- Unknown or malformed plan → `400`, no provider session.
- Unauthenticated or mismatched customer → deny before provider access.
- Duplicate click → disable while pending; one recoverable request.
- Provider timeout/error → retain dialog state, announce the error, allow bounded retry.
- Portal unavailable → show an actionable error, without removing the self-service route.

Rollback: remove the annual option and server allowlist entry; retain the existing checkout behavior. No database migration should be needed.

No application code was changed because the referenced project files are unavailable and the request prohibited file modification.

### UX state matrix

| State or boundary | Disposition | Verification needed |
| --- | --- | --- |
| Loading | unresolved | Disabled button plus accessible progress announcement |
| Empty | not applicable — fixed plan content | No collection result is rendered |
| Error and recovery | unresolved | Provider/API failure preserves choices and permits retry |
| Duplicate or stale action | unresolved | Double-click and stale-dialog tests |
| Timeout and retry | unresolved | Bounded timeout and single retry path |
| Keyboard and focus restoration | unresolved | Native controls, focus trap, Escape/close, opener restoration |
| 320 CSS-pixel reflow | unresolved | Manual browser check |
| Long and translated content | unresolved | Price, renewal, cancellation, and error-content fixtures |
| Performance at click-to-hosted-checkout handoff | unresolved | Measure request start through redirect assignment |

## Trust

Changed boundary:

`UpgradeDialog → BillingButton → /api/checkout → payment provider`

Primary risks:

- Price or customer ownership controlled by the client.
- Duplicate checkout sessions and cost abuse.
- Open redirects.
- Consent bundled with purchase.
- Missing renewal/cancellation disclosure.
- Inaccessible checkout or cancellation.
- Provider callback forgery/replay if callbacks affect entitlement.

Applicable OWASP Top 10:2025 review targets: A01, A02, A03, A05, A06, A08, A09, and A10. Exact ASVS 5.0.0 L1/L2 requirement IDs remain unresolved and must be selected from the official catalog rather than guessed.

Before release, payment logic needs a named human reviewer and independent negative tests at the real server/provider boundary. Any applicable webhook must demonstrate signature authenticity, freshness, replay resistance, idempotency, bounded retry, reconciliation, and safe failure.

Marketing-consent purpose, processor, retention, withdrawal, deletion, and jurisdictional review are unresolved.

## Release

Artifact: unknown; Scope: annual Pro hosted-checkout slice; Environment: local artifact only; Policy: VibeWorthy 1.0.0 workflow; Evidence cutoff: 2026-07-31.

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| failure | Application artifact available | fail | Referenced source and package files are absent | Implementation cannot be inspected or verified | Repository owner | Provide the complete application workspace |
| tool error | Local preflight | tool error | Scanner exit 2: file changed between passes | Scan produced no valid clean result | Repository owner | Rerun in a quiescent isolated checkout |
| manual check | Payment design review | unresolved | No named reviewer or boundary tests | Price/customer manipulation | Payment owner — assign owner | Review server mapping and negative tests |
| manual check | Renewal and cancellation UX | unresolved | No runnable UI | Deceptive or inaccessible commitment | Product/accessibility owner — assign owner | Test disclosure and self-service cancellation |
| manual check | Marketing privacy lifecycle | unresolved | No policy or processing evidence | Invalid or poorly controlled consent | Privacy owner — assign owner | Review notice, withdrawal, retention, and deletion |
| manual check | Native checks | unresolved | `typecheck`, `test`, and `build` could not run because `package.json` is absent | Compile/test failures unknown | Engineering owner — assign owner | Run `npm run typecheck`, `npm test`, and `npm run build` |
| residual risk | Callback integrity | unresolved | Callback implementation unavailable | Forged or replayed entitlement events | Payment owner — assign owner | Test authenticity, freshness, replay, and reconciliation |
| residual risk | Supply-chain release evidence | unresolved | No lockfile, SBOM, provenance, or artifact digest available | Dependency/artifact integrity unknown | Release owner — assign owner | Evaluate the exact release artifact |

Decision: **NO-GO** for release. The design decision is ready, but implementation and payment-critical evidence are unavailable.

## Verification plan

After the complete project is available:

1. Review the diff to confirm only the dialog, billing button, checkout handler, focused tests, and—if absent—the self-service billing-portal seam changed; verify `src/theme.css` is untouched.
2. Unit-test the server allowlist and rejection of unknown plans and all client-controlled pricing/customer/redirect fields.
3. Integration-test annual checkout creation using synthetic data in an isolated provider sandbox, only after explicit approval for that external interaction.
4. Test unauthenticated, duplicate, malformed, replayed, timeout, and provider-failure requests.
5. Verify annual total, renewal cadence, and cancellation terms before commitment; consent starts unchecked and purchase works without it.
6. Complete keyboard, focus restoration, accessible naming, screen-reader announcement, 320px reflow, translated-content, and click-to-checkout-handoff performance checks.
7. Verify self-service cancellation end to end.
8. Run `npm run typecheck`, `npm test`, and `npm run build`.
9. Rerun `python3 -I skill/vibeworthy/scripts/preflight.py . --format text` in a quiescent isolated checkout.

External actions performed: none.