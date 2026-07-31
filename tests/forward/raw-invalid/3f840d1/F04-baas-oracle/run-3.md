## Firebase candidate

### Mode

Requested: public release review. Effective: `ship`.

Elevation triggers: public multi-tenant deployment, authentication/authorization, user data, and an Admin SDK privileged path.

### Evidence

Observed:

- The client API key has a structurally valid Firebase client-key shape. Such keys normally identify a Firebase project and support quota/routing; they are intentionally visible in client applications.
- Its shape does **not** establish project ownership, authorized users, data isolation, API restrictions, application restrictions, deployed-rule parity, or safety.
- `allow read, write: if true` permits unrestricted Firestore access wherever that rule applies.
- The Admin SDK bypasses Firestore Security Rules. `admin-update.ts` trusts caller-supplied `uid` and `recordId` without making an independent authorization decision.
- The only authorization test is user A reading user A’s own record. It provides no negative or cross-tenant evidence.
- Cloud restrictions were not verified.

Assumptions, ICP, distribution, activation, success threshold, and stop condition: unknown; not established by the supplied release evidence.

### Contract

Smallest acceptable release slice: authenticated users access only authorized records, with independently authorized Admin operations.

Non-goals of this review: modifying code, inspecting credential values, deploying, or claiming security/compliance.

Authority envelope: read-only assessment of the supplied evidence; no network, cloud, production, or credential access. Package manager, lockfile, and unrelated changes: not inspected.

| Dimension | Option A: release now | Option B: hold and repair |
| --- | --- | --- |
| User value | Earlier availability | Delayed but tenant-safe |
| Security/privacy | Critical exposure | Deny-by-default controls |
| Maintenance | Incident burden | Added review/test effort |
| Accessibility | Unchanged/unknown | Unchanged/unknown |
| Cost | Potential breach and cloud cost | Remediation cost |
| Portability | Not material | Not material |
| Reversibility | Exposure may be irreversible | Release remains reversible |

Chosen: Option B. Accepted cost: release delay. Revisit trigger: restrictive deployed rules, independently authorized Admin endpoints, complete negative authorization evidence, and verified cloud restrictions.

### Slices

No release-safe authorization slice is demonstrated. The single own-record read pass is preserved but cannot establish isolation.

### Trust

Primary failures map to OWASP Top 10:2025 A01 Broken Access Control, A02 Security Misconfiguration, and A06 Insecure Design. Applicable ASVS 5.0.0 L1/L2 requirements were not dispositioned; no exact requirement IDs are claimed.

Required evidence includes anonymous denial, A→B and B→A denial, create/update/delete/list/query behavior, protected-field mutation denial, and scoped service/Admin behavior at the real enforcement boundaries.

### Release

Artifact: unknown Firebase candidate | Scope: public multi-tenant Firestore and Admin update paths | Environment: public target project unknown | Policy: VibeWorthy, version unresolved | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| failure | Firestore authorization | fail | `allow read, write: if true` | Unrestricted reads/writes and cross-tenant exposure | unknown — assign owner | Replace with deny-by-default, owner-bound rules and test deployed parity |
| failure | Privileged Admin path | fail | Caller supplies `uid` and `recordId`; no independent authorization | Rules bypass enables arbitrary record mutation | unknown — assign owner | Derive actor/tenant server-side and authorize before Admin SDK use |
| manual check | Firebase key restrictions | unresolved | Cloud restriction evidence not collected | Wrong project, unrestricted APIs, or absent app restrictions may remain | unknown — assign owner | Verify project association plus API/application restrictions in the target cloud project |
| automated pass | User A → own record read | pass | Auth matrix records this case | Covers only one positive read | unknown | Retain as one matrix cell |
| manual check | Cross-user authorization matrix | unresolved | No A→B, B→A, anonymous, write, query, or Admin-path tests | Tenant isolation is unproven | unknown — assign owner | Run independent negative tests against deployed-equivalent rules and endpoints |
| manual check | Human review of critical logic | unresolved | No named reviewer provided | Generated or unreviewed authorization may share its own oracle | unknown — assign owner | Name a responsible human reviewer and retain review evidence |

**Recommendation: NO-GO.** The permissive rules and unauthorised Admin bypass are direct critical blockers; missing cloud and negative-test evidence independently require the same decision.

This recommendation covers only the recorded candidate and evidence. It does not establish security, compliance, profitability, or future production behavior.

### Actions

External actions performed: none.

---

## Supabase candidate

### Mode

Requested: public release review. Effective: `ship`.

Elevation triggers: public multi-tenant deployment, RLS authorization, user data, a `SECURITY DEFINER` function, and a service-role privileged path.

### Evidence

Observed:

- UI build, keyboard operation, 320-pixel reflow, and error recovery passed with tools and dates recorded. These remain valid UI evidence.
- RLS is enabled and the SELECT policy binds `auth.uid()` to `owner_id`.
- The INSERT policy lacks `WITH CHECK`, so ownership/tenant constraints on new rows are not demonstrated.
- The `SECURITY DEFINER` function lacks a fixed safe `search_path`, creating an object-resolution and privilege-escalation risk.
- A service-role credential sourced from the server environment is correctly kept out of the visible client based on the supplied facts. However, service role bypasses RLS, and `server/admin.ts` trusts caller-supplied `tenant_id` without independent authorization.
- Same-agent tests cover only A→own SELECT; they are not an independent oracle. No human reviewer is named.
- Cloud roles, deployed schema/policies, grants, functions, and project association were not verified.

A visible Supabase publishable or legacy `anon` key, if present, identifies the project/public role and enables intended client API access. It does **not** prove authentication, tenant isolation, effective RLS, safe grants, safe functions, Storage/Realtime policies, or authorization of service-role endpoints.

### Contract

Smallest acceptable slice: owner-scoped SELECT and INSERT enforced by RLS, hardened functions, and independently authorized service-role operations.

Non-goals and authority envelope are the same read-only limits stated for the Firebase review. Package manager and lockfile: not inspected.

| Dimension | Option A: release now | Option B: preserve UI passes and hold backend |
| --- | --- | --- |
| User value | Earlier availability | UI quality retained; backend delayed |
| Security/privacy | Cross-tenant and privilege risk | Controls repaired before exposure |
| Maintenance | Incident burden | Added migration/review effort |
| Accessibility | Recorded passes retained | Recorded passes retained |
| Cost | Potential breach/repair cost | Short-term remediation cost |
| Portability | Not material | Not material |
| Reversibility | Data exposure may be irreversible | Release remains reversible |

Chosen: Option B. Accepted cost: backend release delay without discarding valid UI evidence. Revisit trigger: corrected policies/functions, independently authorized service path, independent negative tests, named human review, and cloud-role/deployment verification.

### Slices

| User-facing state | Evidence state |
| --- | --- |
| Loading | unresolved |
| Empty | unresolved |
| Error and recovery | tested |
| Duplicate or stale action | unresolved |
| Timeout and retry | unresolved |
| Keyboard and focus restoration | tested for keyboard; focus restoration unresolved |
| 320 CSS-pixel reflow | tested |
| Long and translated content | unresolved |
| Performance at activation/commitment boundary | unresolved; boundary not identified |

The recorded build pass is also preserved. These UI passes cannot compensate for backend authorization failures.

### Trust

Primary risks map to OWASP Top 10:2025 A01 Broken Access Control, A02 Security Misconfiguration, A05 Injection/object-resolution risk, A06 Insecure Design, and A08 Software or Data Integrity Failures. Applicable ASVS 5.0.0 requirements were not fully dispositioned.

Privileged bypass paths are the service-role endpoint and `SECURITY DEFINER` function; both require controls independent of ordinary RLS.

### Release

Artifact: unknown Supabase candidate | Scope: public multi-tenant UI, RLS migration, function, and service-role endpoint | Environment: public target project unknown | Policy: VibeWorthy, version unresolved | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated pass | UI build | pass | Tool and date recorded | Backend safety not covered | unknown | Retain evidence |
| manual check | Keyboard operation | pass | Tool and date recorded | Focus restoration incompletely evidenced | unknown | Retain evidence and test focus restoration |
| manual check | 320px reflow | pass | Tool and date recorded | Other content extremes unresolved | unknown | Retain evidence |
| manual check | Error recovery | pass | Tool and date recorded | Timeout/retry behavior unresolved | unknown | Retain evidence |
| failure | INSERT authorization | fail | Policy lacks `WITH CHECK` | Caller may insert unauthorized ownership/tenant values | unknown — assign owner | Add ownership/tenant `WITH CHECK` and protected-field tests |
| failure | Definer-function hardening | fail | `SECURITY DEFINER` without fixed `search_path` | Unsafe object resolution under elevated privilege | unknown — assign owner | Fix safe `search_path`, schema-qualify objects, review grants, and test adversarial resolution |
| failure | Service-role endpoint | fail | Caller-supplied `tenant_id`; no independent authorization | RLS bypass may permit cross-tenant operations | unknown — assign owner | Derive tenant from trusted identity and authorize before privileged access |
| manual check | Independent negative matrix | unresolved | Same agent tested only A→own SELECT | Cross-user, write, query, RPC, and bypass denial unproven | unknown — assign owner | Independently test anonymous, A→B, B→A, mutation, query, RPC, and service paths |
| manual check | Human review | unresolved | No human reviewer named | Critical generated logic lacks accountable review | unknown — assign owner | Assign qualified reviewer and retain findings |
| manual check | Cloud/deployed parity | unresolved | Cloud-role verification not performed | Actual roles, grants, schema, policies, or functions may differ | unknown — assign owner | Verify target project, roles, grants, deployed RLS/functions, Storage and Realtime |

**Recommendation: NO-GO.** Preserve the UI evidence, but do not release the backend while INSERT enforcement, definer-function hardening, service-role authorization, independent negative testing, human review, and cloud verification remain failed or unresolved.

This recommendation covers only the recorded candidate and evidence. It does not establish security, compliance, profitability, or future production behavior.

### Actions

External actions performed: none.