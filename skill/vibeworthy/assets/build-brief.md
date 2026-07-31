# VibeWorthy build brief

Copy this file for the work item. Replace bracketed prompts, delete instructional comments, and keep evidence links free of secrets and personal data.

## Identity

- Brief owner: `[name or role]`
- Date / last updated: `[ISO date]`
- Project and authorized root: `[project; bounded path]`
- Requested outcome: `[one sentence]`
- Requested mode: `explore | prototype | ship`
- Effective safety mode: `explore | prototype | ship`
- Elevation triggers: `[public endpoint / network or provider sandbox / real data / auth / payment / privileged integration / production / destructive or external side effect / none]`

## Authority envelope

| Dimension | Allowed | Prohibited or approval-gated |
| --- | --- | --- |
| Files and environments | `[root, sandbox/staging]` | `[paths, production]` |
| Data classes | `[synthetic/minimized]` | `[PII, customer data, credentials, confidential source]` |
| Tools, MCP, and network | `[scoped tools/hosts]` | `[unused methods/egress]` |
| Side effects | `[reversible local writes]` | `[deploy, billing, communication, destructive/durable writes]` |
| Human approval | `[named owner and approved actions]` | `[actions requiring fresh approval]` |

## Market evidence

### Problem claim

For `[target user]` in `[triggering moment]`, `[current alternative]` fails because `[costly constraint]`; this change promises `[observable improvement]`.

### ICP

- User / buyer / approver: `[identify differences]`
- Triggering moment and job: `[specific moment and job]`
- Stakes and constraints: `[time, money, risk, workflow, technology]`
- Current alternative: `[manual/incumbent/do nothing]`
- First excluded segment: `[who is not in scope]`

### Evidence ledger

| Claim | Status | Source and date | Narrow inference | Contradiction/gap | Decision affected |
| --- | --- | --- | --- | --- | --- |
| `[claim]` | observed / user-provided / assumption / proposed test | `[traceable source]` | `[what it supports]` | `[limit]` | `[build/revise/stop]` |

Do not invent a source or metric. Record missing evidence as missing.

### Value, distribution, and activation

- Value promise: `[specific improvement without unsupported superlative]`
- First cohort: `[bounded reachable group]`
- Channel owner: `[person or role]`
- Access mechanism: `[specific channel and permission path]`
- Handoff/message: `[message and route into the experience]`
- Friction: `[specific access, trust, timing, or handoff constraint]`
- Activation: `[actor], after [precondition], completes [action] on [object] within [time window]`
- Smallest experiment: `[what tests the riskiest assumption]`
- Proposed threshold and rationale: `[observable number; why it changes this decision; what it does not establish]`
- Stop or redesign condition: `[observable condition]`

## Build contract

- Smallest valuable slice: `[one end-to-end behavior]`
- Included: `[bounded behaviors and artifacts]`
- Non-goals: `[explicit exclusions]`
- Constraints: `[time, stack, data, accessibility, security, privacy, budget]`
- Completion evidence: `[observable behavior and checks]`
- Recovery or rollback: `[how to restore safe state]`

## Repository evidence

- Existing user changes to preserve: `[status/evidence]`
- Stack, runtime, and package manager: `[observed files]`
- Authoritative lockfile: `[path]`
- Relevant architecture and trust boundaries: `[paths/components]`
- Existing patterns to reuse: `[paths]`
- Native verification commands: `[format/lint/type/test/build/a11y]`
- Unknowns: `[manual or proposed checks]`

## Consequential option decision

Decision: `[what must be chosen]`

| Criterion | Option A: `[name]` | Option B: `[name]` |
| --- | --- | --- |
| User value | `[effect]` | `[effect]` |
| Security / privacy risk | `[effect]` | `[effect]` |
| Maintenance | `[effect]` | `[effect]` |
| Accessibility | `[effect]` | `[effect]` |
| Cost | `[monetary or operational effect]` | `[monetary or operational effect]` |
| Portability | `[lock-in or exit effect]` | `[lock-in or exit effect]` |
| Reversibility | `[rollback or migration path]` | `[rollback or migration path]` |

- Choose: `[option]`
- Cite evidence: `[repository/product evidence]`
- Accept tradeoff: `[cost knowingly accepted]`
- Revisit when: `[observable trigger]`

## Vertical slices

| Slice | Actor and observable behavior | Failure/denial | Boundary | Verification seam | Recovery | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `[thin end-to-end behavior]` | `[negative case]` | `[trust/data boundary]` | `[test/demo]` | `[rollback/forward fix]` | planned |

## UX and accessibility acceptance

- Semantics, names, and instructions: `[criteria]`
- Validation and asynchronous announcements: `[criteria]`
- Honest pricing, consent, cancellation, and destructive effects: `[criteria]`

Use only `tested`, `unresolved`, or `not applicable — <reason>` in the disposition column.

| State or boundary | Disposition | Evidence, criterion, or owner/action |
| --- | --- | --- |
| Loading | `[state]` | `[record]` |
| Empty | `[state]` | `[record]` |
| Error and recovery | `[state]` | `[record]` |
| Duplicate or stale action | `[state]` | `[record]` |
| Timeout and retry | `[state]` | `[record]` |
| Keyboard and focus restoration | `[state]` | `[record]` |
| 320 CSS-pixel reflow | `[state]` | `[record]` |
| Long and translated content | `[state]` | `[record]` |
| Performance at `[exact activation or commitment boundary]` | `[state]` | `[budget or measurement]` |

## Trust and data flags

- Changed assets, actors, entry points, and authorization decisions: `[summary]`
- Untrusted inputs/outputs and abuse cases: `[summary]`
- Secrets or privileged identities: `[none or inventory location—not values]`
- Personal-data purpose and classification: `[none or summary]`
- Firebase/Supabase or hosted-backend review needed: `[yes/no and scope]`
- Applicable OWASP/ASVS review target: `[categories; ASVS 5.0.0 L1/L2 target]`
- Named human reviewer for generated critical logic: `[name/role or N/A]`

## Verification and blockers

| Item | Evidence needed | Automated or manual | Owner | Next action | Status |
| --- | --- | --- | --- | --- | --- |
| `[gate]` | `[specific artifact]` | `[kind]` | `[owner]` | `[action]` | missing |

Do not begin a consequential slice while a required authority decision is unresolved. Do not hide a market, security, privacy, or release blocker behind implementation progress.

## Actions

State exactly what happened, not what a plan proposes. When nothing external or consequential was
performed, write the literal sentence:

`External actions performed: none.`

End the section after that sentence; do not append a catalogue of actions that did not occur. Put
relevant completed local checks under verification. Otherwise record each action, exact target,
environment, approval, result, and safe evidence without including credentials or personal data.
