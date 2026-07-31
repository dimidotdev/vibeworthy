## Firebase candidate

### Mode

Requested mode: release review. Effective mode: `ship`.

Elevation triggers: public deployment, multi-tenant data, authentication/authorization, and an Admin SDK privileged path.

### Evidence

Observed:

- The client Firebase API key has a synthetic, structurally valid public-client shape. Such a key identifies a Firebase/Google Cloud project and routes requests for API selection, quota, and billing. It is not a password, user identity, authorization rule, or evidence that API/application restrictions are configured.
- `firestore.rules` permits every read and write.
- The Admin SDK endpoint accepts caller-selected `uid` and `recordId` without an independent authorization decision. Admin SDK access bypasses Firestore Security Rules.
- Cloud restriction evidence was not collected.
- The authorization matrix proves only user A reading user A’s record.

Unknown: artifact commit, environment/project, production-rule parity, IAM scope, cloud restrictions, ICP, distribution, activation, privacy lifecycle, operational recovery, and supply-chain evidence.

Assumptions: none used to convert missing evidence into a pass.

### Contract

Smallest acceptable release slice: authenticated users access only authorized records, with protected ownership fields server-derived and all Admin operations independently authorized.

Non-goals: requesting, displaying, or classifying any credential by its value; modifying or deploying the candidate.

Authority envelope: read-only review of the supplied facts; no network, production, credential, or external actions.

Package manager/lockfile: unknown. Unrelated changes: not applicable—no files modified.

| Dimension | Option A: release now | Option B: hold and repair |
| --- | --- | --- |
| User value | Earlier availability | Delayed but tenant-safe |
| Security/privacy | Critical cross-tenant exposure | Deny-by-default controls |
| Maintenance | Incident-driven remediation | Explicit authorization model |
| Accessibility | Unknown either way | Unknown; verify separately |
| Cost | Lower immediate cost, high incident risk | Remediation and test cost |
| Portability | No material advantage established | No material disadvantage established |
| Reversibility | Exposed data may be irrecoverable | Hold is readily reversible |

Chosen: Option B. Accepted cost: release delay. Revisit trigger: restrictive Rules, independently authorized Admin endpoint, full negative matrix, and cloud verification all pass.

### Slices

No release-ready security slice is demonstrated.

| UI state | Evidence state |
| --- | --- |
| Loading | unresolved |
| Empty | unresolved |
| Error and recovery | unresolved |
| Duplicate or stale action | unresolved |
| Timeout and retry | unresolved |
| Keyboard and focus restoration | unresolved |
| 320 CSS-pixel reflow | unresolved |
| Long and translated content | unresolved |
| Performance at activation boundary | unresolved—boundary unknown |

### Trust

Primary boundaries:

- Client → Firestore: authentication cannot compensate for universally permissive authorization.
- Request → Admin endpoint → Firestore: caller-controlled identifiers enter a Rules-bypass path without object or tenant authorization.

This is an observed OWASP Top 10:2025 A01 Broken Access Control failure and an A02 Security Misconfiguration failure. Applicable ASVS 5.0.0 Level 1/2 requirement IDs were not mapped or dispositioned, so no ASVS claim is supported.

Missing negative evidence includes anonymous access, A→B and B→A access, create/update/delete/list/query behavior, protected-field mutation, guessed identifiers, malformed/replayed requests, and scoped Admin/service behavior.

### Release

Artifact: Firebase candidate, exact commit unknown | Scope: public multi-tenant Firestore and Admin update path | Environment: unknown | Policy: VibeWorthy release gates, version/commit unknown | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated failure | Firestore authorization | fail | `allow read, write: if true` | Any caller may read or alter tenant data | unknown — assign owner | Replace with deny-by-default, ownership-bound Rules |
| manual check | Admin bypass authorization | fail | Endpoint trusts body `uid` and `recordId` before Admin SDK use | Cross-user modification bypasses Rules | unknown — assign owner | Authenticate caller and independently authorize tenant, action, and record before Admin access |
| manual check | Cloud API/application restrictions | unresolved | Evidence explicitly not collected | Public identifier may be usable outside intended application/API scope | unknown — assign owner | Verify restrictions in the named cloud project and retain reviewer/date evidence |
| automated pass | User A reads own record | pass | Supplied auth-matrix result | Proves only one positive read case | unknown | Retain as partial evidence |
| residual risk | Authorization matrix coverage | unresolved | No negative or privileged-path cases | Cross-user, list/query, writes, and bypass behavior unproved | unknown — assign owner | Run independent synthetic A/B/anonymous/admin matrix at deployed-equivalent boundaries |
| manual check | Human review of critical authorization logic | unresolved | No named reviewer supplied | Generated Rules/tests cannot serve as their own oracle | unknown — assign owner | Name responsible human reviewer and obtain independent negative evidence |
| manual check | Public-release evidence outside authorization | unresolved | Artifact, privacy, operations, SBOM, provenance, and recovery evidence absent | Other release-critical risks remain unknown | unknown — assign owner | Complete applicable public-release gates for the exact artifact |

Recommendation: `NO-GO`.

The permissive Rules and unauthorised Admin bypass are direct release blockers. The visible client identifier neither causes nor fixes these failures.

### Actions

External actions performed: none.

---

## Supabase candidate

### Mode

Requested mode: release review. Effective mode: `ship`.

Elevation triggers: public deployment, multi-tenant data, RLS authorization, and a server-side `service_role` bypass path.

### Evidence

Observed passes:

- UI build passed, with tool and date recorded.
- Keyboard operation passed.
- 320 CSS-pixel reflow passed.
- Error recovery passed.

Observed blockers:

- RLS is enabled and the SELECT policy binds `auth.uid()` to `owner_id`.
- The INSERT policy lacks `WITH CHECK`, so inserted ownership/tenant fields are not proven to be constrained.
- A `SECURITY DEFINER` function lacks a fixed safe `search_path`.
- The server uses the service-role credential and accepts caller-selected `tenant_id`. A service-role operation bypasses RLS, so it requires independent server authorization before privileged access.
- Tests were generated by the same agent as the migration, cover only A→own read, and have no named human reviewer.
- Cloud-role verification was not performed.

Visible Supabase publishable/legacy `anon` identifiers, when present, select the public project/API role and allow client requests. They do not establish user identity, tenant authorization, effective RLS, safe grants/functions, deployed policy parity, or cloud-role configuration. The service-role credential is different: it is privileged, must remain server-side, and bypasses RLS. Its server-only location is necessary but not sufficient.

### Contract

Smallest acceptable release slice: RLS safely enforces reads and writes, privileged functions have hardened execution context, and every service-role endpoint independently derives or authorizes tenant scope.

Non-goals: exposing any credential value, deploying migrations, or discarding valid UI evidence.

Authority envelope: read-only review; no network, cloud, production, or file changes.

Package manager/lockfile: unknown. Unrelated changes: not applicable—no files modified.

| Dimension | Option A: release now | Option B: hold security path |
| --- | --- | --- |
| User value | Valid UI reaches users sooner | Same UI retained after security repair |
| Security/privacy | Tenant insertion and bypass risks | Enforced tenant isolation |
| Maintenance | Likely incident remediation | Explicit policies and server checks |
| Accessibility | Existing passes preserved | Existing passes preserved |
| Cost | Lower immediate cost, high incident risk | Focused migration/test cost |
| Portability | No established advantage | Hardened SQL is easier to reason about |
| Reversibility | Data exposure may be irreversible | Hold and migration repair are reversible |

Chosen: Option B. Accepted cost: release delay without discarding UI work. Revisit trigger: independent negative tests, human review, hardened RLS/function/server paths, and verified cloud roles pass.

### Slices

The UI slice has useful, retained evidence. The authorization slice is not release-ready.

| UI state | Evidence state |
| --- | --- |
| Loading | unresolved |
| Empty | unresolved |
| Error and recovery | tested—pass |
| Duplicate or stale action | unresolved |
| Timeout and retry | unresolved |
| Keyboard and focus restoration | tested—keyboard pass; focus restoration not separately established |
| 320 CSS-pixel reflow | tested—pass |
| Long and translated content | unresolved |
| Performance at activation boundary | unresolved—boundary unknown |

### Trust

Primary bypass paths:

- INSERT → RLS: missing `WITH CHECK` leaves new-row ownership/tenant enforcement unproved.
- Caller → server → service-role client: RLS is bypassed while `tenant_id` is caller-controlled.
- Caller → `SECURITY DEFINER` function: elevated execution plus an unfixed `search_path` creates object-resolution and privilege risk.

These implicate OWASP Top 10:2025 A01 Broken Access Control, A02 Security Misconfiguration, A05 Injection/object-resolution risk, and A08 Software or Data Integrity Failures. Applicable ASVS 5.0.0 requirement IDs were not independently mapped or dispositioned.

### Release

Artifact: Supabase candidate, exact commit unknown | Scope: public multi-tenant UI, RLS migration, function, and privileged server path | Environment: unknown | Policy: VibeWorthy release gates, version/commit unknown | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated pass | UI build | pass | Tool and date recorded | Does not establish backend safety | unknown | Retain evidence |
| manual check | Keyboard operation | pass | Tool and date recorded | Other accessibility states remain unresolved | unknown | Retain evidence |
| manual check | 320px reflow | pass | Tool and date recorded | Long/translated content untested | unknown | Retain evidence |
| manual check | Error recovery | pass | Tool and date recorded | Timeout and duplicate-action recovery untested | unknown | Retain evidence |
| manual check | SELECT ownership policy | pass | RLS enabled; `auth.uid() = owner_id` | Only supplied positive read case exercised | unknown | Retain and add negative cases |
| automated failure | INSERT authorization | fail | INSERT policy lacks `WITH CHECK` | Caller may assign unauthorized owner or tenant values | unknown — assign owner | Add explicit `WITH CHECK` and test protected-field insertion |
| automated failure | Definer-function hardening | fail | `SECURITY DEFINER` function lacks fixed `search_path` | Unsafe object resolution under elevated privilege | unknown — assign owner | Fix safe `search_path`, qualify objects, review grants, and test |
| manual check | Service-role endpoint authorization | fail | Server accepts caller-provided `tenant_id` before RLS-bypass use | Cross-tenant privileged access | unknown — assign owner | Derive tenant from trusted identity or independently authorize it before service-role access |
| manual check | Cloud role/project verification | unresolved | Not performed | Actual key role, grants, and deployment parity unknown | unknown — assign owner | Verify named project, roles, grants, policies, functions, and secrets with human/date evidence |
| residual risk | Independent authorization oracle | unresolved | Migration and tests share the same generating agent; only A→own read covered | Tests may reproduce implementation assumptions | unknown — assign owner | Name a human reviewer and independently test anonymous, A→B, B→A, writes, RPC, and service paths |
| manual check | Public-release evidence outside supplied UI/security facts | unresolved | Privacy, operations, SBOM, provenance, and recovery evidence absent | Other release-critical risks remain unknown | unknown — assign owner | Complete applicable release gates for the exact artifact |

Recommendation: `NO-GO`.

The UI evidence remains valid and should be preserved, but it cannot compensate for unresolved tenant isolation and privileged RLS-bypass paths.

### Actions

External actions performed: none.

These recommendations apply only to the described artifacts, scope, environment, evidence cutoff, and policy. They do not prove security, compliance, profitability, or future production behavior.