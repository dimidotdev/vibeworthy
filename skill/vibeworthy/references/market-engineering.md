# Market and engineering procedure

Use this procedure to turn an uncertain request into a bounded, testable build.

## Contents

- Frame the market claim
- Define the ICP and distribution path
- Define activation and an experiment
- Inspect the project and choose deliberately
- Implement vertical slices
- Verify UX and accessibility

## Frame the market claim

Write one falsifiable sentence: “For `[target user]` in `[triggering moment]`, `[current alternative]` fails because `[costly constraint]`; this change promises `[observable improvement]`.”

Separate inputs in an evidence ledger:

| Claim | Status | Source and date | What it supports | Contradiction or gap | Decision changed by it |
| --- | --- | --- | --- | --- | --- |
| `[claim]` | observed / user-provided / assumption / proposed test | `[traceable source]` | `[narrow inference]` | `[limit]` | `[build, revise, or stop]` |

Apply these rules:

- Prefer recent behavior, paid commitments, retained use, support records, search or workflow evidence, and direct observation over generic trend claims.
- Treat interviews and survey answers as evidence of language, context, and reported pain; do not silently convert them into purchasing behavior.
- Record counterevidence and selection bias. Do not hide a conflicting segment or failed test.
- Quote no metric without its source, definition, population, and time window. Label a threshold selected for an experiment as proposed, not observed.
- Ask for the smallest missing fact that could reverse the decision. Avoid research that cannot affect scope or a stop condition.

## Define the ICP and distribution path

Define the initial ideal customer profile narrowly enough to find:

- Identify the user, buyer, and approver when they differ.
- Name the triggering moment, job, stakes, current workaround, technical and budget constraints, and reason to act now.
- Name who is explicitly outside the first segment.
- Record where this cohort already gathers or searches and whether the builder can ethically reach it.
- State the competitive alternative, including manual work, a spreadsheet, an incumbent, or doing nothing.

Choose one primary distribution path for the first experiment. Record the first reachable cohort, channel owner, access mechanism, message, handoff into the product, expected friction, and observable response. Treat “social media,” “SEO,” and “word of mouth” as untested labels until a specific audience and route exist.

Check whether the value promise and channel fit each other. Do not build a product that requires a distribution capability the team neither owns nor plans to test.

## Define activation and an experiment

Define activation as the earliest user behavior that demonstrates received value, not account creation, page views, or button clicks by themselves. Give the event an exact actor, action, object, precondition, and time window.

Write it in this literal shape so the precondition cannot disappear:

`Activation: [actor], after [precondition], completes [action] on [object] within [time window]`

Examples of useful shapes:

- Complete the costly job with a valid result and no operator rescue.
- Return and reuse a saved result in the next natural work cycle.
- Invite the next required collaborator after receiving the first result.

Choose the smallest ethical experiment that tests the riskiest market assumption. Prefer a manual service, clickable flow, concierge test, landing-page commitment, or one end-to-end product slice when it can answer the question sooner than a broad build.

Record:

- the hypothesis and current evidence;
- the cohort and acquisition route;
- the experience shown and work performed manually;
- the activation event and instrumentation definition;
- a proposed success signal with rationale;
- a stop or redesign condition;
- the owner, time box, and decision after the result.

Do not use deceptive scarcity, fake testimonials, hidden enrollment, preselected consent, or an unusable cancellation path to improve an experiment.

## Inspect the project and choose deliberately

Before material edits, inspect only within the authorized root and record:

- repository status and unrelated user changes;
- framework, language, runtime, package manager, and one authoritative lockfile;
- source, test, generated, migration, infrastructure, and deployment boundaries;
- established components, design tokens, data access, authorization, validation, and error patterns;
- native format, lint, type, test, build, accessibility, and deployment commands;
- existing constraints, risky workarounds, and missing evidence.

Do not infer conventions from one file when the repository provides a canonical pattern. Do not rewrite unrelated code to make a small slice look cleaner.

Compare at least two viable options for a consequential or hard-to-reverse choice:

| Criterion | Option A | Option B |
| --- | --- | --- |
| User value | `[effect]` | `[effect]` |
| Security and privacy risk | `[boundary/risk]` | `[boundary/risk]` |
| Maintenance | `[cost]` | `[cost]` |
| Accessibility | `[effect]` | `[effect]` |
| Monetary or operational cost | `[effect]` | `[effect]` |
| Portability and lock-in | `[effect]` | `[effect]` |
| Reversibility and migration | `[exit path]` | `[exit path]` |

Select one option, cite repository and product evidence, and record the cost accepted. Prefer the simpler reversible option while evidence is weak. Revisit the decision when its stated trigger occurs.

## Implement vertical slices

Cut work by independently demonstrable behavior rather than horizontal layers. Include UI, data, enforcement, failure state, and observability only to the depth needed for that behavior.

For each slice:

1. State one actor, trigger, behavior, result, and non-goal.
2. Define acceptance through an observable example and at least one relevant failure or denial.
3. Identify the trust and data boundaries crossed.
4. Implement the smallest change using existing project patterns.
5. Verify close to the change, then run broader affected checks.
6. Demonstrate the behavior, record evidence, and keep a rollback or forward-recovery path.
7. Stop and reassess before adding the next slice.

Avoid introducing an abstraction, dependency, service, or configuration layer until the current slice proves its need. Keep schema and API changes backward-compatible where practical; otherwise stage migration and recovery explicitly.

## Verify UX and accessibility

For every user-facing slice, verify:

- Use native semantics first; preserve heading order, landmarks, labels, instructions, and programmatic relationships.
- Complete the primary and recovery paths with a keyboard; keep focus order logical, focus visible, and focus moved or restored intentionally after dialogs, errors, and navigation.
- Reflow at 320 CSS pixels without hidden actions or two-dimensional scrolling except where intrinsically necessary.
- Provide meaningful loading, empty, error, offline or timeout, success, retry, undo, and safe-recovery states where applicable.
- Handle long names, translated text, zero and large values, missing media, slow responses, duplicate submission, and stale state.
- Announce validation and asynchronous changes accessibly; connect each error to its field and preserve entered data on recoverable failure.
- Preserve contrast, target size, zoom, reduced-motion preference, and non-color cues according to the project's applicable accessibility target.
- Measure performance at the activation or conversion moment; avoid loading unrelated code, media, or third-party scripts on its critical path.
- Make price, renewal, data use, consent, destructive effects, and cancellation clear before commitment.

Record the following matrix for each user-facing slice. Use only `tested`, `unresolved`, or `not
applicable — <reason>`; a proposed test is not a tested result.

| State or boundary | Disposition | Evidence or next action |
| --- | --- | --- |
| Loading | `[state]` | `[record]` |
| Empty | `[state]` | `[record]` |
| Error and recovery | `[state]` | `[record]` |
| Duplicate or stale action | `[state]` | `[record]` |
| Timeout and retry | `[state]` | `[record]` |
| Keyboard and focus restoration | `[state]` | `[record]` |
| 320 CSS-pixel reflow | `[state]` | `[record]` |
| Long and translated content | `[state]` | `[record]` |
| Performance at `[exact activation or commitment boundary]` | `[state]` | `[budget/measurement]` |

Test with the project's accessibility tooling, but also perform keyboard, focus, reflow, and recovery checks manually. Record untested assistive-technology behavior as a manual check rather than a pass.
