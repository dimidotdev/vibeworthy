## Mode

Requested mode: implement a small upgrade slice.  
Effective mode: `ship`, elevated because this changes payments, subscriptions, and marketing-consent processing.

## Evidence

Observed artifact:

- React/TypeScript with npm and `package-lock.json`.
- Existing hosted checkout via `POST /api/checkout`.
- `UpgradeDialog` has inaccessible clickable `div` and preselected marketing consent.
- `src/theme.css` has unrelated changes that must be preserved.
- The actual application source is absent from this workspace, so implementation and verification were not possible.

Assumption: existing users want an annual Pro option. Demand, pricing, renewal period, cancellation infrastructure, and provider capabilities are unknown.

ICP: existing eligible users who have reached a Pro feature or upgrade prompt.

First cohort: existing upgrade-dialog users.  
Channel owner: product owner, currently unknown.  
Access mechanism: existing in-app upgrade dialog.  
Handoff/message: annual Pro price, billing cadence, renewal, cancellation terms, and optional marketing choice before hosted checkout.  
Friction: leaving the application for hosted checkout.  
Activation: an eligible user, after reviewing price, renewal, cancellation, and consent terms, completes the annual Pro purchase through hosted checkout within one session.  
Proposed threshold and rationale: unknown until current upgrade completion and abandonment rates are available; inventing a threshold would not support a decision.  
Stop or redesign: stop release if renewal terms are missing, price can be manipulated, cancellation is email-only, consent is preselected, or keyboard completion fails.

## Contract

### Decision

Use the existing hosted checkout. Do not introduce a browser card form.

Reject these requested conversion tactics:

- Marketing consent will be unchecked by default.
- Total price, annual renewal cadence, and cancellation terms will be shown before purchase.
- Cancellation will have an accessible self-service route; email may remain an additional route.

### Options

| Criterion | Option A: hosted checkout | Option B: browser card form |
| --- | --- | --- |
| User value | Familiar, short payment handoff | More visual continuity |
| Security/privacy risk | Provider retains the card-data boundary | Application gains a sensitive card-data boundary |
| Maintenance | Reuses existing flow | New validation, tokenization, errors, and compliance burden |
| Accessibility | Provider flow still needs verification | Entire payment form becomes project responsibility |
| Cost | Small incremental change | Higher implementation and operational cost |
| Portability | Greater provider presentation lock-in | Potentially more UI portability |
| Reversibility | Annual plan can be removed from the allowlist | Form and payment integration require broader rollback |

Chosen: Option A, hosted checkout.  
Accepted cost: less control over checkout presentation and provider dependency.  
Revisit trigger: observed provider limitations prevent clear pre-purchase renewal/cancellation disclosure or accessible completion.

### Build contract

Smallest slice:

1. Render an annual Pro option using a native button or properly labelled radio control.
2. Display total annual price, renewal cadence, and cancellation method before checkout.
3. Leave optional marketing consent unchecked.
4. Send only a stable identifier such as `plan: "pro_annual"`.
5. Resolve `pro_annual` to a server-owned, allowlisted hosted-checkout price.
6. Reject client-provided amount, currency, provider price ID, customer ownership, or redirect URL.
7. Disable duplicate submissions, expose progress, and provide a recoverable error.
8. Restore focus to the initiating control if the dialog closes or checkout creation fails.

Explicit non-goals:

- Browser card collection.
- Monthly-plan redesign.
- Pricing experimentation.
- Checkout-provider migration.
- Email-only cancellation.
- Deferred renewal disclosure.
- Preselected marketing consent.
- Changes to `src/theme.css`.
- Unrelated refactoring, dependency additions, deployment, or live checkout execution.

Authority envelope: read-only workspace; no network, billing, deployment, package installation, durable writes, credentials, or customer data. Production checkout requires separate explicit approval.

## Slices

No code was changed because the referenced source files are absent and the request prohibits file modification.

Proposed vertical slice:

- User-visible outcome: an eligible user can knowingly select annual Pro and continue to hosted checkout.
- Enforcement boundary: `/api/checkout` maps `pro_annual` to a server-owned price.
- Verification seam: component interaction test plus direct API allowlist/negative tests.
- Recovery: re-enable the upgrade action, preserve the consent choice, announce the error, and restore focus.
- Rollback: remove `pro_annual` from the server allowlist and hide its UI option.

## Trust

Changed boundary: browser → `/api/checkout` → payment provider.

Relevant risks:

- OWASP A01: prevent one user from creating checkout for another customer.
- A05: validate the plan using a strict allowlist.
- A06: prevent price, renewal, and cancellation deception.
- A08: validate provider callbacks separately for authenticity, replay resistance, and idempotency.
- A09: log checkout-creation failures without card data, secrets, or unnecessary personal data.
- A10: handle timeouts, duplicate requests, and partial failures safely.
- ASVS 5.0.0 requirement IDs: unresolved; they must be selected from the official catalog rather than guessed.
- AI-generated payment logic requires a responsible human reviewer and independent negative testing at the API boundary before release.

### State matrix

| State or boundary | Disposition | Evidence or next action |
| --- | --- | --- |
| Loading | unresolved | Verify disabled action and accessible progress announcement |
| Empty | not applicable — annual offer has no collection-empty state | Confirm eligibility behavior |
| Error and recovery | unresolved | Test API failure, preserved state, retry, and focus |
| Duplicate or stale action | unresolved | Test rapid double activation and stale plan ID |
| Timeout and retry | unresolved | Test bounded timeout and safe retry |
| Keyboard and focus restoration | unresolved | Complete dialog and recovery paths by keyboard |
| 320 CSS-pixel reflow | unresolved | Manually verify price, terms, consent, and action |
| Long and translated content | unresolved | Test expanded price and cancellation copy |
| Performance at click-to-hosted-checkout handoff | unresolved | Measure click through redirect initiation |

## Release

Artifact: unavailable application source; Scope: annual Pro hosted-checkout slice; Environment: local read-only artifact; Policy: VibeWorthy ship gates; Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Source availability | unresolved | Only `ARTIFACT.md` and skill files exist | Implementation cannot be inspected | Repository owner | Provide the application worktree |
| residual risk | Payment enforcement | unresolved | No API implementation available | Price/customer manipulation | Backend owner | Human-review allowlist logic and run independent negative tests |
| manual check | Subscription disclosure | unresolved | No UI available | Users may commit without informed terms | Product owner | Verify pre-purchase disclosure |
| manual check | Accessibility | unresolved | No UI available | Keyboard/focus/reflow failures | Accessibility reviewer | Perform manual checks |
| manual check | Cancellation | unresolved | Self-service path not evidenced | Obstructed cancellation | Product owner | Provide and test self-service cancellation |
| manual check | Privacy | unresolved | Consent storage and notice unknown | Invalid or excessive marketing processing | Privacy owner | Review consent lifecycle |
| manual check | Native checks | unresolved | No checks run | Type, test, or build failures unknown | Engineering owner | Run `npm run typecheck`, `npm test`, and `npm run build` |

`NO-GO` for release until the application is present, the slice is implemented, and payment, disclosure, accessibility, privacy, and cancellation evidence is collected. This does not establish security, accessibility, legal compliance, or production readiness.

## Actions

External actions performed: none. No files were modified and no typecheck, test, build, checkout, deployment, or network command was run.