# VibeWorthy release evidence

Copy this file for one release candidate. Record facts for the named artifact and environment; do not paste credentials, PII, customer records, or confidential source.

## Release identity

- Evaluated candidate commit (C): `[full 40-character commit SHA]`
- Evaluated `skill/vibeworthy` tree (T): `[full Git tree SHA from C]`
- Release/tag commit (R): `[full 40-character commit SHA]`
- Tag/ref: `[annotated SemVer tag for a public release; tags remain movable labels]`
- Skill archive (A): `[exact filename; archive root must be vibeworthy/]`
- Skill archive SHA-256 (D): `[64 lowercase hexadecimal characters]`
- Companion SBOM: `[exact filename and SHA-256]`
- Release manifest: `[exact filename and SHA-256]`
- Archive build provenance: `[GitHub attestation ID/URL and bundle filename/SHA-256]`
- Checksum index: `[SHA256SUMS filename and SHA-256]`
- Checksum-index provenance: `[GitHub attestation ID/URL and bundle filename/SHA-256]`
- Published asset inventory: `[the exact four checksum-listed assets plus SHA256SUMS and its provenance bundle]`
- Durable GitHub Release: `[release URL/ID]`
- Included scope: `[features and data flows]`
- Excluded scope: `[explicit exclusions]`
- Environment and destination: `[staging/production; named project]`
- Evidence cutoff: `[ISO timestamp]`
- Release policy/version: `[policy]`
- Release owner: `[name/role]`
- Independent reviewer: `[name/role]`
- Effective safety mode: `ship`

Record C and T before evaluation. At release time, require R to equal C exactly and verify that
`git rev-parse R:skill/vibeworthy` equals T. The annotated release tag must point directly to the
evaluated candidate; a descendant commit with an identical skill tree is not an acceptable release
substitute. A and D identify the distributed bytes. Do not manufacture a future commit SHA inside a
file that the future commit must contain: record tag, workflow-run, attestation, and final asset facts
in the generated release manifest or another post-build evidence record. A GitHub build provenance
attestation is provenance evidence; record signature verification only when it was actually
performed and retained.

For a public release, use an annotated SemVer tag and include exactly one trailer line:
`VibeWorthy-Candidate-Commit: <C>`. The workflow rejects lightweight tags, missing/duplicate
trailers, any candidate that differs from the tag target, and any R whose skill tree differs from T.
A `workflow_dispatch` run is only a build/attestation rehearsal and cannot support a public-release
`GO`; it must not publish or substitute for the annotated tag and durable GitHub Release.

## Blockers first

| Blocker | Affected gate | Evidence | Owner | Next action | Retest condition |
| --- | --- | --- | --- | --- | --- |
| `[unresolved fact or failure]` | `[auth/secrets/privacy/etc.]` | `[safe link or record]` | `[owner]` | `[action]` | `[observable condition]` |

Do not delete this section because other checks pass. Write `None observed in recorded scope` only after completing required gates.

## Verification ledger

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| `[automated pass / failure / tool error / manual check / residual risk / exception]` | `[one gate or fact]` | `[pass / fail / tool error / unresolved / accepted]` | `[exact target, environment, tool/version, command, reviewer, or safe link]` | `[specific limitation or none observed in scope]` | `[named person/role or unknown]` | `[specific action or none]` |

Keep automated passes, failures, tool errors, and manual checks distinct. Never turn “not run,” scanner suppression, or a tool error into a pass.
Give every distinct failure, tool error, required manual check, and residual risk its own row. Every
non-pass row requires an owner and concrete next action; bullets or prose do not replace this ledger.
`unknown` is an unresolved ownership blocker, not an assigned owner, and cannot satisfy a `GO` gate.

## Market and product fit for this release

- ICP and triggering moment: `[summary]`
- Evidence versus assumptions: `[safe build-brief link]`
- Distribution owner and path: `[summary]`
- Activation event and instrumentation definition: `[summary]`
- Success and stop signals: `[observed or explicitly proposed]`
- Scope response to evidence: `[what changed or remains unproven]`

## Authority and agent use

- Authorized roots, tools, environment, and network: `[record]`
- Production/deployment/external-action approval: `[named approval and exact action]`
- MCP servers and capabilities reviewed: `[enablement approval, verified publisher/update source, allowed methods, denied methods, destination allowlist, audit evidence]`
- Agent/model data sent: `[classification and minimized fields; no values]`
- Provider retention/training/deletion/backup-deletion/region/subprocessor approval: `[decision and owner]`
- Untrusted prompt/repository/tool-output controls: `[record]`
- Omitted fixture/canary handling: `[not read, requested, reproduced, or exposed]`

Return `NO-GO` when sensitive transmission terms are unresolved or required production authority is absent.

## Security verification

### Trust boundaries

| Boundary | Assets and actors | Authorization decision | Untrusted input/output | Abuse/failure case | Control and enforcement point | Test/evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `[boundary]` | `[assets/actors]` | `[decision]` | `[input/output]` | `[case]` | `[control]` | `[evidence]` |

### OWASP Top 10:2025 and ASVS 5.0.0

| Standard ID | Level/applicability | Enforcement point | Evidence | Result | Reviewer / action |
| --- | --- | --- | --- | --- | --- |
| `[A01–A10 / exact ASVS 5.0.0 requirement ID]` | `[Top10; L1/L2; rationale]` | `[boundary]` | `[test/manual record]` | pass / fail / unresolved / N/A | `[reviewer/action]` |

- Public-release ASVS target: `[applicable L1 requirements dispositioned: yes/no]`
- Account/sensitive-data/payment target: `[applicable L2 requirements dispositioned: yes/no/N/A]`
- Negative tests: `[anonymous; A-own; A→B; B→A; admin/service; malformed/replay/abuse as applicable]`
- Generated critical logic human reviewer: `[name/role or N/A]`
- Independent enforcement-boundary evidence: `[record or missing]`

Describe only requirements reviewed for this scope. Do not claim OWASP or ASVS compliance, verification, or certification.

## Secrets and privileged identity

| Credential class or identity | Store/binding | Least-privilege scope | Owner | Rotation/expiry | Exposure/history review | Result |
| --- | --- | --- | --- | --- | --- | --- |
| `[class—not value]` | `[managed location]` | `[scope]` | `[owner]` | `[record]` | `[safe evidence]` | pass/fail/unresolved |

- Client bundles and source maps checked for privileged values: `[evidence]`
- Logs and reports checked for disclosure: `[evidence]`
- Git history and release artifacts checked with dedicated tooling: `[evidence]`
- Suspected exposure handled in order—revoke/rotate, audit, history/artifact remediation, verify: `[N/A or incident record]`

Return `NO-GO` for suspected exposure until revocation/rotation and required investigation are complete.

## Firebase or Supabase authorization

- Platform/project and isolated test environment: `[record or N/A]`
- Public identifier classification and manual cloud restriction/project check: `[record]`
- Privileged credentials kept outside clients and agents: `[record]`
- Deny-by-default Rules/RLS and deployed parity: `[record]`

| Actor → target | CRUD | List/query | Immutable fields | Storage | Realtime | Views/functions/RPC | Privileged server/IAM path | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| anonymous | `[evidence]` | `[evidence]` | `[evidence]` | `[evidence]` | `[evidence]` | `[evidence]` | `[evidence]` | pass/fail/unresolved |
| user A → own | `[evidence]` | `[evidence]` | `[evidence]` | `[evidence]` | `[evidence]` | `[evidence]` | `[evidence]` | pass/fail/unresolved |
| user A → user B | `[denial]` | `[denial]` | `[denial]` | `[denial]` | `[denial]` | `[denial]` | `[denial]` | pass/fail/unresolved |
| user B → user A | `[denial]` | `[denial]` | `[denial]` | `[denial]` | `[denial]` | `[denial]` | `[denial]` | pass/fail/unresolved |
| admin/service → scoped target | `[evidence]` | `[evidence]` | `[evidence]` | `[evidence]` | `[evidence]` | `[evidence]` | `[evidence]` | pass/fail/unresolved |

- Supabase `USING` and `WITH CHECK`, grants, and bypass review: `[evidence or N/A]`
- Firebase get/list/query, proposed-data, Rules, Admin/IAM review: `[evidence or N/A]`

Return `NO-GO` for an untested applicable cell, cross-user failure, unresolved public-key restriction, or unaudited bypass path.

## Payment, checkout, and callback integrity

- Hosted checkout versus browser card collection decision: `[options, chosen path, accepted cost, revisit trigger]`
- Client request contract: `[stable plan identifier only]`
- Server-owned price mapping: `[allowlist and configured amount/currency/interval evidence]`
- Rejected client authority: `[amount, currency, price ID, customer owner, redirect destination]`
- Pre-commit disclosure: `[total price, renewal cadence, cancellation terms, unchecked optional consent]`
- Accessible self-service cancellation: `[end-to-end evidence]`

| Callback gate | Evidence | Result | Owner / next action |
| --- | --- | --- | --- |
| Authenticity at the receiver | `[signature/MAC or provider mechanism]` | pass/fail/unresolved | `[owner/action]` |
| Freshness and bounded clock tolerance | `[timestamp/age evidence]` | pass/fail/unresolved | `[owner/action]` |
| Replay resistance and idempotency | `[event identity and duplicate test]` | pass/fail/unresolved | `[owner/action]` |
| Bounded retry, safe failure, and reconciliation | `[failure/recovery evidence]` | pass/fail/unresolved | `[owner/action]` |

Return `NO-GO` while a client can choose price authority or an applicable callback gate is unresolved.

## Privacy lifecycle

| Purpose and classification | Minimization, precision, and frequency | Processor/region | Retention and backup deletion | Export/deletion | Sensitive/minor data and guardian/child authorization | Named-jurisdiction privacy/legal review | Incident owner and raw-data logging | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `[record]` | `[record]` | `[record]` | `[record]` | `[record]` | `[record or N/A]` | `[Brazil/EU/other decision as applicable]` | `[owner and logging decision]` | pass/fail/unresolved/N/A |

Do not invent a lawful basis, consent conclusion, or jurisdictional answer. Return `NO-GO` while a required legal/privacy review or data-lifecycle control is unresolved.

## Supply chain and artifact integrity

| Gate | Evidence | Result | Owner / next action |
| --- | --- | --- | --- |
| Dependency identity, necessity, license, maintenance, and install scripts | `[record]` | pass/fail/unresolved | `[owner/action]` |
| One immutable lockfile and reproducible resolution | `[path/digest]` | pass/fail/unresolved | `[owner/action]` |
| Vulnerability and known-exploited review under dated policy | `[tool/version/policy]` | pass/fail/tool error | `[owner/action]` |
| Complete transitive SBOM for artifact | `[format/link/digest]` | pass/fail/unresolved | `[owner/action]` |
| Patch owner/SLA and unsupported-component review | `[record]` | pass/fail/unresolved | `[owner/action]` |
| Short-lived CI identity and minimum permissions | `[record]` | pass/fail/unresolved | `[owner/action]` |
| Third-party automation pinned by digest/full SHA | `[record]` | pass/fail/unresolved | `[owner/action]` |
| Provenance/signature verification | `[record]` | pass/fail/tool error | `[owner/action]` |
| Source, lockfile, artifact, and deployed digest match | `[digests]` | pass/fail/unresolved | `[owner/action]` |

For the VibeWorthy repository release, `SHA256SUMS` must contain exactly the ZIP, SBOM, release
manifest, and archive-provenance bundle. Its separately verified GitHub attestation authenticates that
finite index. The checksum index and its own attestation bundle are verification assets and are not
recursively listed in `SHA256SUMS`. Verify the ZIP's archive-provenance statement and the checksum-
index attestation separately against the expected repository, workflow signer, source commit, and tag
ref; checking only a bundle digest is insufficient. Verify the exact six workflow-managed files before
promotion. GitHub's automatic source archives are host-created snapshots outside this inventory.

Return `NO-GO` for every mandatory supply-chain failure named by the release policy.

## Hosted-backend operations

| Control | Test/evidence | Owner | Result |
| --- | --- | --- | --- |
| Abuse/rate limits and quotas/spend ceiling | `[record]` | `[owner]` | pass/fail/unresolved |
| Backup and isolated restore drill | `[record]` | `[owner]` | pass/fail/unresolved |
| Migration rollback or forward recovery | `[record]` | `[owner]` | pass/fail/unresolved |
| Bounded timeout/retry/idempotency/reconciliation | `[record]` | `[owner]` | pass/fail/unresolved |
| Redacted logs and exercised alerts | `[record]` | `[owner]` | pass/fail/unresolved |
| Kill switch or containment action | `[record]` | `[owner]` | pass/fail/unresolved |

## Time-bounded noncritical exceptions

| Gate | Reason | Independent approver | Compensating control and evidence | Owner | Future expiry | Recheck |
| --- | --- | --- | --- | --- | --- | --- |
| `[noncritical gate only]` | `[reason]` | `[not implementer]` | `[control]` | `[owner]` | `[ISO date]` | `[condition]` |

Do not enter secrets, authorization, destructive data, payment, critical dependency, privacy/legal review, tool error, required manual check, provenance/digest, or critical recovery failures here.

## Skill forward-test record, when used

- Exact skill commit/digest: `[immutable identity]`
- Host/platform and version: `[surface/version]`
- Model and version, when exposed: `[record]`
- Full prompt: `[safe verbatim link]`
- Isolated starting artifact and digest: `[record]`
- Required and prohibited rubric: `[record]`
- At least three raw runs for nondeterministic behavior: `[links]`
- Reviewer result per run: `[record]`
- Revision caused by a failure: `[commit or none]`

Do not reuse contaminated output artifacts between isolated runs.

## Recommendation

Decision: `GO | CONDITIONAL | NO-GO`

- Rationale: `[lead with unresolved critical evidence]`
- Conditions and expiry, if conditional: `[complete exception rows]`
- Residual risks: `[specific, owned, dated]`
- Next action and owner: `[action]`
- Decision scope limitation: `This recommendation applies only to the named artifact, scope, environment, evidence cutoff, and policy. It does not prove security, compliance, profitability, or future production behavior.`

Apply exactly one rule:

- Select `GO` only when every required gate passes and no required manual check remains.
- Select `CONDITIONAL` only for complete, noncritical, independently approved, time-bounded exceptions.
- Select `NO-GO` for any unresolved critical gate, required manual check, or tool error.

## Actions

State exactly which external or consequential actions were performed. A future plan, checklist, or
approval request is not an executed action. If none occurred, write:

`External actions performed: none`

Otherwise record the action, exact target and environment, named approval, result, and safe evidence.
