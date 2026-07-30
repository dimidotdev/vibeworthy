# VibeWorthy release evidence

Copy this file for one release candidate. Record facts for the named artifact and environment; do not paste credentials, PII, customer records, or confidential source.

## Release identity

- Artifact / commit / digest: `[immutable identity]`
- Included scope: `[features and data flows]`
- Excluded scope: `[explicit exclusions]`
- Environment and destination: `[staging/production; named project]`
- Evidence cutoff: `[ISO timestamp]`
- Release policy/version: `[policy]`
- Release owner: `[name/role]`
- Independent reviewer: `[name/role]`
- Effective safety mode: `ship`

## Blockers first

| Blocker | Affected gate | Evidence | Owner | Next action | Retest condition |
| --- | --- | --- | --- | --- | --- |
| `[unresolved fact or failure]` | `[auth/secrets/privacy/etc.]` | `[safe link or record]` | `[owner]` | `[action]` | `[observable condition]` |

Do not delete this section because other checks pass. Write `None observed in recorded scope` only after completing required gates.

## Verification ledger

| Gate | Artifact, scope, environment, and tool/version | Kind | Result | Evidence | Residual risk | Owner / next action |
| --- | --- | --- | --- | --- | --- | --- |
| `[gate]` | `[exact target]` | automated / manual | pass / fail / tool error / unresolved / N/A | `[command, reviewer, safe link]` | `[limitation]` | `[owner/action]` |

Keep automated passes, failures, tool errors, and manual checks distinct. Never turn “not run,” scanner suppression, or a tool error into a pass.

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
- MCP servers and capabilities reviewed: `[publisher, methods, scope, egress]`
- Agent/model data sent: `[classification and minimized fields; no values]`
- Provider retention/training/deletion/region approval: `[decision and owner]`
- Untrusted prompt/repository/tool-output controls: `[record]`

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

## Privacy lifecycle

| Purpose and classification | Minimization | Processor/region | Retention/backups | Export/deletion | Sensitive/minor data | Legal/privacy review | Incident owner | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `[record]` | `[record]` | `[record]` | `[record]` | `[record]` | `[record]` | `[named decision]` | `[owner]` | pass/fail/unresolved/N/A |

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
