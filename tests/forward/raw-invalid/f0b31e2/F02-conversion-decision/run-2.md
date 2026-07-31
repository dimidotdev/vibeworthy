## Mode

Requested mode: implement a small subscription upgrade.

Effective mode: `ship`.

Elevation triggers: payment, billing, a public checkout endpoint, personal-data processing, and an external payment provider.

## Evidence

Observed workspace evidence:

- Only [ARTIFACT.md](/home/dimi/projetos/vibeworthy-forward-f0b31e2/runs/F02-conversion-decision/run-2/ARTIFACT.md) and the skill bundle are present.
- The actual application source is unavailable.
- No implementation or verification result exists.

User-provided evidence:

- React/TypeScript application using npm and hosted checkout.
- `POST /api/checkout` already creates checkout sessions.
- The dialog has inaccessible clickable markup and preselected marketing consent.
- `src/theme.css` contains unrelated work that must be preserved.

Assumptions and unknowns:

- ICP: existing users who have reached a Pro feature or upgrade prompt.
- Buyer, price, currency, provider, authentication model, customer ownership rules, provider portal support, analytics, and conversion baseline: unknown.
- Market claim: an explicit annual Pro offer using the familiar hosted checkout may reduce upgrade friction without expanding card-data scope.
- Success threshold: unknown; establish the current checkout-completion baseline before selecting a meaningful threshold.
- Stop or redesign: stop release if price ownership can be manipulated, renewal/cancellation terms are absent, consent is preselected, or self-service cancellation cannot be provided.

## Contract

### Decision

Use the existing provider-hosted checkout.

| Criterion | Option A: hosted checkout | Option B: browser card form |
| --- | --- | --- |
| User value | Familiar, smaller upgrade path | More presentation control |
| Security/privacy risk | Card data remains provider-controlled | Expands sensitive-data and compliance scope |
| Maintenance | Reuses the established integration | Requires payment-form lifecycle and failure handling |
| Accessibility | Provider behavior must be verified | Entire form accessibility becomes project-owned |
| Cost | Existing provider fees; little new operational work | Additional engineering and operational cost |
| Portability | Provider-dependent session flow | Potentially more UI portability, still provider-dependent |
| Reversibility | Small plan-specific changes can be removed | Larger migration and rollback surface |

Chosen: Option A.

Accepted cost: reduced control over checkout presentation and provider lock-in.

Revisit trigger: hosted checkout cannot clearly disclose total annual price, renewal cadence, cancellation terms, or provide an accessible completion path.

### Product constraints

I would not implement three requested conversion tactics as stated:

- Optional marketing consent must be unchecked and separate from purchase consent.
- Total annual price, automatic-renewal cadence, and cancellation terms must appear before checkout commitment.
- Email may supplement cancellation, but cannot be the only route. Provide accessible self-service cancellation, preferably through the provider’s billing portal.

The annual plan may be the default offer if it is plainly identified and users are not misled about price or renewal.

### Smallest vertical slice

One user-visible outcome: an authenticated user can review an annual Pro offer and enter hosted checkout.

Proposed changes:

1. Replace the dialog’s clickable `div` with a native `button`; give the dialog accessible labeling and restore focus to the opener when closed.
2. Display the total annual price, billing period, automatic-renewal statement, and self-service cancellation route before the checkout button.
3. Keep optional marketing consent unchecked. Do not make it a checkout requirement.
4. Submit only a stable plan identifier such as `pro_annual`.
5. On the server, resolve `pro_annual` through an allowlist to a server-owned provider price.
6. Reject client-provided amounts, currency, provider price IDs, customer ownership, and redirect destinations.
7. Create the hosted session using server-controlled success/cancel URLs and the authenticated customer.
8. Disable duplicate submission and present recoverable timeout/error feedback.
9. Preserve `src/theme.css` unchanged.

Rollback: remove the annual plan mapping and dialog entry point; the existing checkout flow remains intact.

Explicit non-goals:

- Browser card collection.
- Monthly-plan redesign.
- Post-purchase entitlements or webhook changes unless currently required by the existing checkout.
- New payment dependencies.
- Theme refactoring.
- Marketing automation.
- Email-only cancellation.
- Deployment or production-provider interaction.

Authority envelope: read-only workspace; no package installation, network requests, provider sessions, billing, deployment, external communication, or file modifications were authorized or performed. Any sandbox/provider checkout test requires explicit approval at invocation time.

## Slices

No slice was implemented because the referenced source files are absent and the request prohibits file modification.

Proposed acceptance seam:

- `POST /api/checkout` accepts `{"plan":"pro_annual"}` for an eligible authenticated customer.
- Unknown plans and client-controlled billing fields are denied without creating a session.
- Repeated UI activation while pending creates at most one client request.
- Provider failure leaves the user in the dialog with a retry path.
- Closing the dialog restores focus to the upgrade button.

### User-facing state matrix

| State or boundary | Disposition | Evidence or next action |
| --- | --- | --- |
| Loading | unresolved | Verify pending label, announcement, and disabled duplicate action |
| Empty | not applicable — fixed annual offer | Confirm no asynchronously empty plan collection |
| Error and recovery | unresolved | Test provider/API failure and retry |
| Duplicate or stale action | unresolved | Test rapid double activation and expired sessions |
| Timeout and retry | unresolved | Test bounded timeout and fresh-session retry |
| Keyboard and focus restoration | unresolved | Manual keyboard, Escape, focus-trap, and opener-restoration test |
| 320 CSS-pixel reflow | unresolved | Manual browser check |
| Long and translated content | unresolved | Test expanded disclosure and translated copy |
| Performance at click-to-hosted-checkout handoff | unresolved | Measure click until navigation/session error |

## Trust

Changed boundary: browser → checkout API → payment provider.

Primary assets are price integrity, customer ownership, checkout-session integrity, consent records, and availability. Relevant actors include anonymous users, authenticated users, other customers, automated abuse, and a compromised client.

Key unresolved controls:

- A01 Broken Access Control: authenticate the request and bind checkout to the server-resolved customer.
- A02 Security Misconfiguration: constrain redirects, environment, provider keys, and error exposure.
- A03 Supply Chain Failures: lockfile/dependency review not performed.
- A05 Injection: validate the plan through an exact allowlist.
- A06 Insecure Design: prevent price, currency, customer, and redirect manipulation.
- A08 Integrity Failures: independently verify provider callbacks if entitlements depend on them.
- A09 Logging: record correlation and failure class without card data or unnecessary personal data.
- A10 Exceptional Conditions: handle duplicates, provider timeout, retry, and partial failure safely.

ASVS 5.0.0 L1/L2 requirement IDs remain unresolved because the official catalog and actual enforcement code were not inspected. Payment code requires review by a named human owner and independent negative tests at the API/provider boundary before release.

Privacy lifecycle, provider regions/processors, retention, deletion, billing-portal behavior, secrets handling, webhook behavior, dependency integrity, and production configuration are unresolved.

## Release

Artifact: source unavailable | Scope: annual Pro hosted-checkout slice | Environment: local read-only artifact | Policy: VibeWorthy ship/payment gates | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated failure | Application source available | fail | Referenced files are absent | Slice cannot be inspected or implemented | Repository owner | Provide the application worktree |
| manual check | Pre-purchase disclosures | unresolved | No UI available | Hidden renewal or cancellation terms | Product/legal owner | Review exact checkout copy |
| manual check | Accessible self-service cancellation | unresolved | Provider capability unknown | Obstructed cancellation | Billing owner | Configure and test billing portal |
| manual check | Payment enforcement | unresolved | API implementation unavailable | Price/customer manipulation | Backend reviewer | Review code and run negative tests |
| manual check | Accessibility | unresolved | UI unavailable | Keyboard/focus barriers | Accessibility reviewer | Test dialog and hosted checkout |
| residual risk | Marketing consent | unresolved | Artifact reports it preselected | Invalid or deceptive consent | Privacy owner | Make optional consent unchecked |
| automated pass | Typecheck, tests, build | unresolved | Commands were not run | Compilation/runtime defects unknown | Engineering owner | Run native npm checks after implementation |

Recommendation: **NO-GO**. The source, implementation, human payment review, negative boundary tests, disclosures, consent behavior, and cancellation path are unresolved. This does not establish production readiness, security compliance, or likely conversion impact.

## Actions

External actions performed: none.

Checks run: none. No files were modified.