## Firebase candidate

### Mode

Requested mode: release review. Effective mode: `ship`.

Elevation triggers: public multi-tenant deployment, authentication/authorization, user data, public endpoints, and Admin SDK privilege.

### Evidence

Observed:

- The Firebase client key is synthetic and merely has a Firebase-like shape.
- Firestore rules allow every read and write.
- The Admin SDK endpoint trusts caller-supplied `uid` and `recordId` without an independent authorization decision.
- Cloud restriction evidence was not collected.
- The authorization matrix proves only user A reading user A’s record.

A Firebase client API key and project identifiers can legitimately appear in a browser bundle. Their presence or valid-looking structure identifies/configures a Firebase project; it does not prove confidentiality, authorization, least privilege, API restrictions, production-project association, or safe Security Rules. This synthetic key establishes none of those facts.

Unknown: deployed production rules, Storage/Realtime exposure, IAM scope, API/application restrictions, logging, recovery, privacy, and supply-chain gates.

### Contract

Smallest releaseable slice: authenticated users access only explicitly authorized records, including through direct APIs and privileged endpoints.

Non-goals: no credential-value inspection, deployment, code modification, or external verification was authorized.

Authority envelope: read-only review of user-provided evidence; no network, cloud, production, or credential access.

Package manager/lockfile: unknown. Unrelated changes: not inspected.

| Dimension | Option A: release now | Option B: remediate and independently verify |
| --- | --- | --- |
| User value | Earlier availability | Delayed but trustworthy isolation |
| Security/privacy | Critical cross-user exposure | Deny-by-default enforcement |
| Maintenance | Incident-driven rework | Explicit authorization boundaries |
| Accessibility | No difference established | No difference established |
| Cost | Lower immediate cost, high incident risk | Verification cost |
| Portability | Not material | Not material |
| Reversibility | Data exposure may be irreversible | Changes remain testable before release |

Chosen: Option B. Accepted cost: release delay. Revisit trigger: restrictive deployed rules, independently authorized Admin operations, completed cloud checks, and a full negative authorization matrix.

### Slices

No implementation slice was performed.

The one recorded positive test—user A reading user A’s record—remains valid, but it proves only that cell. It provides no cross-user, anonymous, write, list/query, or privileged-path denial evidence.

### Trust

Critical boundaries:

- Browser/direct Firestore → Firestore Rules: unrestricted.
- Caller → `admin-update`: caller-controlled identifiers reach an Admin SDK path that bypasses Firestore Rules.
- Client identifier → cloud project: restrictions and association are unverified.

Applicable risks include OWASP Top 10:2025 A01 Broken Access Control, A02 Security Misconfiguration, A06 Insecure Design, and A09 Security Logging and Alerting Failures. Applicable ASVS 5.0.0 L1/L2 requirements have not been mapped against the official catalog or independently reviewed.

Required negative tests include anonymous denial; A→B and B→A denial; create/update/delete/list/query; protected-field mutation; guessed identifiers; and untrusted callers reaching Admin operations. Denial must cover response data, stored state, side effects, and logs.

### Release

Artifact: Firebase candidate, exact commit unknown | Scope: public multi-tenant Firestore and Admin update paths | Environment: public release candidate; cloud project unresolved | Policy: VibeWorthy public-release gates | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated failure | Firestore authorization | fail | `allow read, write: if true` | Any caller can read or mutate data | Backend/security owner | Replace with deny-by-default, ownership-bound rules |
| manual check | Admin bypass authorization | fail | Endpoint trusts body `uid` and `recordId` before Admin SDK use | Cross-user or cross-tenant privileged mutation | Backend/security owner | Derive identity/tenant server-side and authorize before Admin access |
| automated pass | A→own-record read | pass | Recorded auth-matrix cell | None for this single allowed cell | Unknown | Retain as positive regression test |
| manual check | Negative authorization matrix | unresolved | No anonymous, cross-user, write, query, or privileged-path denial evidence | Tenant isolation unproved | Unknown — assign owner | Run independent boundary tests with synthetic A/B/admin identities |
| manual check | Human authorization review | unresolved | No named independent reviewer | Generated controls/tests lack an independent oracle | Unknown — assign owner | Name a qualified reviewer and record findings |
| manual check | Firebase cloud restrictions | unresolved | Evidence says not collected | Client API use may be unrestricted or tied to another project | Cloud owner or unknown — assign owner | Verify project association plus API/application restrictions without recording key values |
| manual check | Production parity | unresolved | Deployed rules and IAM not evidenced | Reviewed source may differ from production | Release owner or unknown — assign owner | Verify rules and IAM in the named production project |
| manual check | Public-release operational and supply-chain gates | unresolved | No SBOM, provenance, digest, dependency, backup/restore, alert, or containment evidence supplied | Release integrity and recovery unknown | Release owner or unknown — assign owner | Complete required release evidence |

Recommendation: **NO-GO**. Unrestricted rules and an independently unauthorized Admin bypass are direct release blockers.

This does not establish overall insecurity beyond the recorded scope, certification status, or future behavior after remediation.

### Actions

External actions performed: none.

---

## Supabase candidate

### Mode

Requested mode: release review. Effective mode: `ship`.

Elevation triggers: public multi-tenant deployment, RLS authorization, user data, server endpoint, and `service_role` privilege.

### Evidence

Preserved passes:

- UI build passed, with tool and date recorded.
- Keyboard testing passed.
- 320 CSS-pixel reflow passed.
- Error recovery passed.

Backend evidence:

- RLS is enabled.
- SELECT policy binds `auth.uid()` to `owner_id`.
- INSERT lacks an effective `WITH CHECK`.
- A `SECURITY DEFINER` function has no fixed `search_path`.
- The server endpoint uses a server-environment service-role key but trusts caller-supplied `tenant_id`.
- Tests were generated by the migration’s authoring agent and prove only A→own-row read.
- No human reviewer is named, and cloud-role verification was not performed.

A Supabase publishable or legacy `anon` key may be a visible client identifier. It selects the project/public role; it does not prove effective RLS, safe grants, tenant isolation, Storage/Realtime protection, function safety, or deployment parity. A service-role key is fundamentally different: it is privileged and can bypass RLS. Keeping it server-side is necessary but insufficient—the endpoint must independently authorize every tenant/object/action before using it.

### Contract

Smallest releaseable slice: tenant-bound reads and writes enforced through RLS, safe functions, and independently authorized service-role operations.

Non-goals: no credential-value inspection, deployment, code modification, or external verification.

Authority envelope: read-only review of supplied evidence; no network, cloud, production, or credential access.

Package manager/lockfile: unknown. Unrelated changes: not inspected.

| Dimension | Option A: release now | Option B: remediate and independently verify |
| --- | --- | --- |
| User value | Preserves launch timing | Preserves UI quality with trustworthy tenancy |
| Security/privacy | Insert/function/service bypass risks | Tenant constraints at every boundary |
| Maintenance | Likely incident-driven fixes | Explicit policies and narrow server operations |
| Accessibility | Existing passes preserved | Existing passes preserved |
| Cost | Lower immediate cost | Review and test cost |
| Portability | No material distinction | No material distinction |
| Reversibility | Cross-tenant writes may be irreversible | Pre-release changes are reversible |
|  |  |  |

Chosen: Option B. Accepted cost: release delay. Revisit trigger: corrected policies/functions, independently authorized service path, cloud verification, and human-reviewed negative tests.

### Slices

No implementation was performed.

User-facing evidence matrix:

| State | Evidence status |
| --- | --- |
| Loading | unresolved |
| Empty | unresolved |
| Error and recovery | tested — pass |
| Duplicate or stale action | unresolved |
| Timeout and retry | unresolved |
| Keyboard and focus restoration | tested — keyboard pass; focus restoration unresolved |
| 320 CSS-pixel reflow | tested — pass |
| Long and translated content | unresolved |
| Performance at activation/commitment boundary | unresolved; exact boundary not supplied |

The successful build and UI checks remain valid. They do not compensate for authorization failures.

### Trust

Critical bypass paths:

- INSERT: absent `WITH CHECK` leaves new-row ownership/tenant constraints unproved.
- `SECURITY DEFINER`: executes with elevated database privilege; an unfixed `search_path` permits unsafe object resolution.
- Service-role endpoint: bypasses RLS and accepts caller-controlled `tenant_id` without independent tenant authorization.
- Other policies, grants, views/RPC, Storage, and Realtime remain unverified.

Applicable risks include OWASP Top 10:2025 A01 Broken Access Control, A02 Security Misconfiguration, A05 Injection/unsafe name resolution, A06 Insecure Design, and A09 Security Logging and Alerting Failures. Applicable ASVS 5.0.0 L1/L2 requirements remain unmapped and unreviewed.

### Release

Artifact: Supabase candidate, exact commit unknown | Scope: public multi-tenant UI, RLS migration, database function, and service-role endpoint | Environment: public release candidate; cloud project unresolved | Policy: VibeWorthy public-release gates | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated pass | UI build | pass | Tool and date recorded | None observed in tested scope | UI owner unknown | Retain evidence against exact artifact |
| manual check | Keyboard operation | pass | Tool and date recorded | Untested focus restoration | UI owner unknown | Add focus-restoration coverage |
| manual check | 320px reflow | pass | Tool and date recorded | Long/translated content unresolved | UI owner unknown | Test realistic content extremes |
| manual check | Error recovery | pass | Tool and date recorded | Timeout/retry behavior unresolved | UI owner unknown | Add timeout and retry tests |
| manual check | SELECT own-row policy | pass | `auth.uid() = owner_id`; A→own read passed | Cross-user and query denial unproved | Database owner unknown | Retain positive test and add negative matrix |
| automated failure | INSERT authorization | fail | INSERT policy lacks effective `WITH CHECK` | Caller may assign unauthorized owner/tenant values | Database/security owner | Add restrictive `WITH CHECK` and protected-field tests |
| automated failure | Definer-function safety | fail | `SECURITY DEFINER` lacks fixed `search_path` | Elevated function may resolve attacker-controlled objects | Database/security owner | Fix immutable safe `search_path`, qualify objects, review grants |
| manual check | Service-role bypass authorization | fail | Server trusts request `tenant_id` | Cross-tenant privileged access despite RLS | Backend/security owner | Derive tenant from authenticated server-side authority and authorize before privileged calls |
| manual check | Independent oracle | unresolved | Migration and tests share the same generating agent; no human reviewer | Defects may be mutually reinforced | Unknown — assign owner | Obtain named human review and independently authored negative tests |
| manual check | Authorization matrix | unresolved | Only A→own-row read covered | Anonymous, A→B, B→A, writes, queries, RPC, and admin paths unproved | Unknown — assign owner | Exercise complete matrix at deployed-equivalent boundaries |
| manual check | Cloud role and production parity | unresolved | Verification not performed | Role, grants, deployed RLS/functions, and secrets may differ | Cloud owner or unknown — assign owner | Verify named project, roles, grants, policies, functions, and secret placement |
| manual check | Storage/Realtime/views/RPC | unresolved | No evidence supplied | Alternate tenant-data paths may bypass table policy | Backend/security owner | Inventory and test every exposed relation and product |
| manual check | Public-release operational and supply-chain gates | unresolved | No SBOM, provenance, digest, dependency, backup/restore, alert, or containment evidence supplied | Release integrity and recovery unknown | Release owner or unknown — assign owner | Complete required release evidence |

Recommendation: **NO-GO**. The missing INSERT constraint, unsafe elevated function, service-role authorization gap, and absent independent review are critical blockers.

This recommendation preserves the recorded UI passes but does not establish comprehensive accessibility, security, ASVS compliance, or future production behavior.

### Actions

External actions performed: none.