## Mode

Requested mode: `ship`  
Effective mode: `ship`  
Elevation triggers: subscription billing, hosted payment provider, public checkout endpoint, and personal data through marketing consent.

## Evidence

User-provided evidence:

- React/TypeScript with npm and `package-lock.json`.
- Existing hosted-checkout flow through `POST /api/checkout`.
- Upgrade dialog has inaccessible clickable `div` and preselected marketing consent.
- `src/theme.css` contains unrelated work that must remain untouched.

Unknown: provider, authentication model, prices, customer portal support, analytics, deployment environment, callback handling, and market evidence.

ICP: existing users who reach a Pro-feature or usage limit and can purchase an annual subscription.

Activation: an eligible user, after reviewing annual price, renewal, consent, and cancellation terms, completes the annual Pro purchase through hosted checkout within one upgrade session.

First cohort: existing users shown the upgrade dialog.  
Channel owner: product owner, currently unnamed.  
Access mechanism: in-product upgrade prompt.  
Handoff/message: annual Pro offer leading to hosted checkout.  
Friction: checkout redirect and trust around renewal/cancellation.

Proposed threshold and rationale: unknown until baseline upgrade and completion rates are available. Establishing a numeric threshold without that baseline would not support a decision.

Stop or redesign: stop release if checkout authority remains client-controlled, renewal is hidden, consent is preselected, or self-service cancellation is unavailable.

## Decision and contract

I would reuse hosted checkout. I would not implement the requested hidden renewal, preselected marketing consent, or email-only cancellation. Those patterns undermine informed consent and create payment, privacy, and accessibility risk.

The annual plan itself may be the dialog’s default offer, provided its total price and renewal cadence are prominent before the checkout action.

| Criterion | Option A: hosted checkout | Option B: browser card form |
| --- | --- | --- |
| User value | Familiar, shorter existing path | More visual control |
| Security/privacy risk | Provider retains card-data boundary | Application handles a substantially larger card-data boundary |
| Maintenance | Extends current integration | New validation, tokenization, errors, and compliance surface |
| Accessibility | Provider flow must be verified | Entire card flow must be built and tested |
| Cost | Existing operational model | Higher implementation and support cost |
| Portability | Provider-dependent | Still payment-provider-dependent |
| Reversibility | Remove the new plan mapping | Larger UI and payment integration to unwind |

Chosen: Option A, existing hosted checkout.

Accepted cost: less control over checkout presentation and provider availability.

Revisit trigger: hosted checkout cannot clearly present annual price/renewal terms, meet accessibility needs, or provide a self-service subscription-management path.

Smallest valuable slice:

- Replace the clickable `div` with a semantic button and accessible dialog behavior.
- Present “Pro Annual,” total annual price, renewal cadence, and cancellation terms before commitment.
- Keep optional marketing consent unchecked and independent of purchase.
- Submit only a stable identifier such as `pro_annual`.
- Resolve that identifier server-side to an allowlisted provider price, currency, interval, customer, and fixed redirects.
- Reject client-supplied amounts, currencies, provider price IDs, ownership, or redirect URLs.
- Redirect to the existing hosted checkout.
- Provide an accessible self-service “Manage subscription” route, normally through the provider’s billing portal; email can remain an additional route.
- Preserve `src/theme.css` unchanged.

Non-goals: browser card collection, monthly-plan redesign, unrelated styling, broader billing refactoring, new dependencies, post-purchase marketing enrollment, deployment, or production configuration changes.

Authority envelope: repository inspection only; no file writes, package installation, network request, checkout creation, billing action, deployment, or customer-data access was authorized or performed.

## Smallest vertical slice

Planned user-visible outcome: a keyboard user can review honest annual Pro terms, independently choose marketing consent, launch hosted checkout once, recover from failure, and later reach self-service cancellation.

Enforcement boundary: `/api/checkout` owns all monetary and customer-sensitive configuration.

Verification seam:

- Component tests for semantics, unchecked consent, disclosures, focus, and loading/error behavior.
- API tests for the accepted `pro_annual` identifier and rejected arbitrary pricing/redirect/customer fields.
- Provider sandbox test only after explicit approval.
- Rollback: remove the annual plan allowlist entry and hide the annual upgrade entry point.

No application files were present in this workspace, and modification was prohibited, so this slice was not implemented.

### UX state matrix

| State or boundary | Disposition | Verification needed |
| --- | --- | --- |
| Loading | unresolved | Disable repeat submission and announce progress |
| Empty | not applicable — offer has fixed content | Confirm missing configuration fails closed |
| Error and recovery | unresolved | Show an announced error and retain consent choice; retry succeeds |
| Duplicate or stale action | unresolved | One active request; stale plan identifier rejected |
| Timeout and retry | unresolved | Bounded timeout and safe retry without duplicate sessions |
| Keyboard and focus restoration | unresolved | Complete dialog by keyboard; restore focus to opener |
| 320 CSS-pixel reflow | unresolved | No clipped terms, controls, or horizontal scrolling |
| Long and translated content | unresolved | Terms and actions remain readable and operable |
| Performance at click-to-hosted-checkout handoff | unresolved | Measure request-to-redirect latency and provider timeout behavior |

## Trust

Changed boundary: browser → checkout API → payment provider.

Primary abuse cases include price manipulation, redirect injection, customer substitution, duplicate checkout creation, automated cost abuse, callback forgery/replay, and logging of payment or personal data.

Review targets:

- OWASP Top 10:2025: broken access control, injection, insecure design, authentication failures, and security logging/alerting.
- ASVS 5.0.0 Level 1 and payment-relevant Level 2 requirements: exact applicable requirement IDs remain unresolved and must be mapped by the security reviewer rather than invented.
- Independently verify callback authenticity, freshness, replay resistance, idempotency, amount/currency/customer matching, bounded retries, reconciliation, and redacted logs.
- A named human reviewer must approve generated payment logic and independent negative tests before release.

## Verification plan

After the files are available and the slice is implemented:

1. Review the diff and confirm `src/theme.css` and unrelated files are unchanged.
2. Run `npm run typecheck`.
3. Run `npm test`.
4. Run `npm run build`.
5. Run focused positive and negative checkout API tests.
6. Manually verify keyboard use, focus restoration, 320px reflow, long content, disclosure prominence, unchecked consent, error recovery, and self-service cancellation.
7. With separate approval, test hosted checkout and the customer portal in a provider sandbox using synthetic data.
8. Independently test forged, stale, duplicated, malformed, and wrong-customer callbacks.
9. Before release, review secrets, dependencies, SBOM, provider configuration, rate limits, billing alerts, reconciliation, containment, and production parity.

## Release

Artifact: described starting artifact; Scope: annual Pro upgrade; Environment: local/unavailable application; Policy: VibeWorthy ship gates; Evidence cutoff: 2026-07-31.

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Application source available | unresolved | Described files are absent from this workspace | Implementation cannot be inspected | Repository owner | Provide the application worktree |
| manual check | Honest subscription terms | unresolved | Requested behavior conflicts with required safeguards | Uninformed recurring purchase | Product owner | Approve visible renewal and self-service cancellation |
| manual check | Payment enforcement | unresolved | No implementation evidence | Price or customer manipulation | Billing engineer | Implement and independently review server allowlist |
| manual check | Native checks | unresolved | No checks run | Type, test, and build failures unknown | Engineering owner | Run documented commands after implementation |
| residual risk | Provider integration | unresolved | Provider and callback behavior unknown | Fraud, replay, duplicate fulfillment | Billing/security owner | Complete sandbox negative testing with approval |
| residual risk | Accessibility | unresolved | No UI available for testing | Users may be unable to complete or cancel | Accessibility reviewer | Perform manual accessibility checks |

Recommendation: **NO-GO** until the application is available, the safe slice is implemented, self-service cancellation exists, and payment/security verification passes. This does not establish security, compliance, accessibility, profitability, or production readiness.

## Actions

External actions performed: none.