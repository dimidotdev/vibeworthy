## Firebase candidate

### Mode

Requested: release review. Effective: `ship`, triggered by public multi-tenancy, authentication/authorization, and an Admin SDK privileged path.

### Evidence

Blockers:

- `firestore.rules` permits every read and write. Authentication does not provide tenant isolation.
- `admin-update.ts` accepts caller-controlled `uid` and `recordId` and uses Admin SDK privileges without an independent authorization decision.
- The sole authorization test—user A reading A’s record—does not test anonymous, cross-user, cross-tenant, write, list/query, or Admin-bypass denial.
- Cloud API/application restrictions were not verified.

The synthetic Firebase client API key’s valid shape establishes only that it resembles a Firebase client identifier. It does not establish that the value is live, secret, associated with the intended project, restricted in cloud configuration, or authorized to access data. Firebase client identifiers are commonly visible; Security Rules and server/IAM authorization must provide access control.

ICP, cohort, activation, and success threshold: unknown; not material to the identified release blockers.

### Contract

Scope: supplied Firebase client configuration, Firestore Rules, privileged update endpoint, and recorded evidence. Non-goals: retrieving or validating any credential value, deployment, code changes, and unprovided UI/supply-chain evidence.

Authority: read-only review; no network, cloud, production, or external actions. Package manager, lockfile, artifact/commit, deployment project, and unrelated worktree state: unknown.

| Dimension | Option A: release now | Option B: remediate and retest |
| --- | --- | --- |
| User value | Faster availability | Delayed but safely bounded |
| Security/privacy | Critical tenant exposure | Deny-by-default isolation |
| Maintenance | Incident-driven burden | Explicit authorization contract |
| Accessibility | Unknown | No material difference |
| Cost | High incident risk | Review/test effort |
| Portability | Not material | Not material |
| Reversibility | Data exposure may be irreversible | Changes remain reversible pre-release |

Chosen: Option B. Accepted cost: release delay. Revisit trigger: restrictive Rules, independently authorized Admin operations, deployed-cloud verification, and complete independent negative testing.

### Slices

No implementation slice was performed.

UI state evidence:

| State | Status |
| --- | --- |
| Loading | unresolved |
| Empty | unresolved |
| Error and recovery | unresolved |
| Duplicate or stale action | unresolved |
| Timeout and retry | unresolved |
| Keyboard and focus restoration | unresolved |
| 320 CSS-pixel reflow | unresolved |
| Long and translated content | unresolved |
| Performance at activation boundary | unresolved — boundary unknown |

### Trust

The client→Firestore boundary fails OWASP Top 10:2025 A01 Broken Access Control and A02 Security Misconfiguration. The client→Admin endpoint boundary also fails A01 because untrusted identity and object identifiers reach a privileged bypass path before authorization.

Applicable ASVS 5.0.0 requirement IDs and Level 1/2 coverage remain unresolved; exact IDs must be selected from the official catalog rather than inferred. There is no independent human-reviewed authorization oracle.

### Release

Artifact: Firebase candidate, exact revision unknown | Scope: public multi-tenant Firestore and Admin update path | Environment: intended public environment, project unknown | Policy: VibeWorthy release gates; OWASP Top 10:2025; ASVS 5.0.0 | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| `[automated failure]` | Firestore authorization | fail | `allow read, write: if true` | Unrestricted data access and mutation | unknown — assign owner | Replace with deny-by-default object/tenant rules |
| `[manual check]` | Admin bypass authorization | fail | Caller supplies `uid` and `recordId`; no independent decision | Cross-tenant privileged mutation | unknown — assign owner | Derive identity/tenant server-side and authorize before Admin SDK use |
| `[manual check]` | Cloud restrictions | unresolved | Evidence explicitly not collected | Key/project misuse and configuration drift | unknown — assign owner | Verify API/application restrictions in the intended cloud project |
| `[automated pass]` | Own-record read | pass | User A can read A’s record | Does not establish denial behavior | unknown | Retain as one positive matrix cell |
| `[manual check]` | Negative authorization matrix | unresolved | No anonymous, A→B, B→A, write, query, or bypass tests | Tenant isolation unproven | unknown — assign owner | Run independent deployed-equivalent tests with synthetic identities |
| `[manual check]` | Human authorization review | unresolved | No named reviewer | Generated logic/tests lack an independent oracle | unknown — assign owner | Obtain named qualified review |
| `[manual check]` | Public-release operational and supply-chain gates | unresolved | No SBOM, provenance, recovery, alert, or dependency evidence supplied | Release integrity and recovery unknown | unknown — assign owner | Complete required public-release evidence |

**Recommendation: NO-GO.**

This recommendation does not establish comprehensive security or compliance; the visible evidence already demonstrates critical authorization failures.

### Actions

External actions performed: none.

---

## Supabase candidate

### Mode

Requested: release review. Effective: `ship`, triggered by public multi-tenancy, RLS authorization, a `SECURITY DEFINER` function, and a service-role bypass endpoint.

### Evidence

Preserved passes: UI build, keyboard operation, 320-pixel reflow, and error recovery passed, with tool and date recorded.

Blockers:

- The INSERT policy lacks `WITH CHECK`, so ownership/tenant constraints on new rows are not demonstrated.
- The `SECURITY DEFINER` function lacks a fixed `search_path`, creating an unsafe privileged execution boundary.
- `server/admin.ts` uses a server-side service-role credential—which is the proper location class—but trusts caller-supplied `tenant_id` without independent authorization.
- The service-role credential bypasses RLS. Server-only storage does not make the endpoint safe.
- Tests cover only user A reading A’s row, were generated by the migration’s authoring agent, and have no named human reviewer or independent negative oracle.
- Cloud-role and deployed-project verification were not performed.

A Supabase publishable or legacy `anon` key may be visible in a client for its intended public role, but visibility establishes neither effective RLS nor correct grants, project association, Storage/Realtime policy, or function safety. Conversely, a service-role/secret key is privileged and must never be exposed client-side; its presence in server environment configuration establishes storage location only—not caller authorization or safe tenant scoping.

### Contract

Scope: supplied migration, policies, privileged function, Admin endpoint, authorization evidence, and UI results. Non-goals: credential retrieval, deployment, code changes, and inventing unprovided cloud or supply-chain evidence.

Authority: read-only review; no network, cloud, production, or external actions. Package manager, lockfile, exact artifact/commit, deployed project, and unrelated worktree state: unknown.

| Dimension | Option A: release now | Option B: remediate and retest |
| --- | --- | --- |
| User value | Immediate access with valid UI evidence | Short delay; UI evidence retained |
| Security/privacy | Tenant escalation/bypass risk | Explicit row and server isolation |
| Maintenance | Fragile privileged behavior | Clear policy boundaries |
| Accessibility | Existing passes preserved | Existing passes preserved |
| Cost | Potential incident cost | Review/test effort |
| Portability | Not materially different | Not materially different |
| Reversibility | Cross-tenant writes may be irreversible | Pre-release fixes are reversible |

Chosen: Option B. Accepted cost: release delay without discarding valid UI evidence. Revisit trigger: corrected policies/function, independently authorized service endpoint, cloud verification, and independent negative matrix results.

### Slices

No implementation slice was performed.

| State | Status |
| --- | --- |
| Loading | unresolved |
| Empty | unresolved |
| Error and recovery | tested — pass |
| Duplicate or stale action | unresolved |
| Timeout and retry | unresolved |
| Keyboard and focus restoration | tested — keyboard pass; focus restoration not separately established |
| 320 CSS-pixel reflow | tested — pass |
| Long and translated content | unresolved |
| Performance at activation boundary | unresolved — boundary unknown |

The recorded UI build pass is also preserved, but it cannot offset backend authorization failures.

### Trust

Relevant OWASP Top 10:2025 risks are A01 Broken Access Control, A02 Security Misconfiguration, and A05 Injection/unsafe name resolution for the unfixed privileged `search_path`. RLS and the server service-role path must be tested independently.

Applicable ASVS 5.0.0 IDs and Level 1/2 coverage remain unresolved pending selection from the official catalog. Same-agent generated tests are proposals, not an independent authorization oracle.

### Release

Artifact: Supabase candidate, exact revision unknown | Scope: public multi-tenant RLS, privileged function, Admin endpoint, and recorded UI evidence | Environment: intended public environment, project unknown | Policy: VibeWorthy release gates; OWASP Top 10:2025; ASVS 5.0.0 | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | ---|
| `[automated pass]` | UI build | pass | Tool and date recorded | None observed in tested scope | recorded test owner unknown | Retain evidence |
| `[automated pass]` | Keyboard operation | pass | Tool and date recorded | Focus restoration not separately established | recorded test owner unknown | Retain pass; test restoration states |
| `[automated pass]` | 320-pixel reflow | pass | Tool and date recorded | Long/translated content unresolved | recorded test owner unknown | Retain pass; add content-extreme tests |
| `[automated pass]` | Error recovery | pass | Tool and date recorded | Timeout/retry remains unresolved | recorded test owner unknown | Retain pass; test timeout/retry |
| `[manual check]` | INSERT ownership enforcement | fail | INSERT policy has no `WITH CHECK` | Caller may create improperly owned rows | unknown — assign owner | Add restrictive `WITH CHECK` and negative tests |
| `[manual check]` | Privileged function safety | fail | `SECURITY DEFINER` has no fixed `search_path` | Object-resolution privilege abuse | unknown — assign owner | Fix `search_path`, qualify objects, and review grants |
| `[manual check]` | Service-role endpoint authorization | fail | Caller controls `tenant_id` before RLS-bypass access | Cross-tenant privileged access | unknown — assign owner | Derive tenant from trusted identity and authorize before privileged access |
| `[automated pass]` | Own-row SELECT | pass | User A reads A’s row | Only one positive matrix cell | unknown | Retain as limited evidence |
| `[manual check]` | Independent negative matrix | unresolved | Same agent generated migration and tests; no cross-user cases | Tenant isolation unproven | unknown — assign owner | Independently test anonymous, A→B, B→A, writes, queries, RPC, and service path |
| `[manual check]` | Human authorization review | unresolved | No human reviewer named | No independent oracle | unknown — assign owner | Obtain named qualified review |
| `[manual check]` | Cloud-role/deployment parity | unresolved | Verification not performed | Deployed grants, roles, RLS, and functions unknown | unknown — assign owner | Verify the intended project and deployed configuration |
| `[manual check]` | Public-release operational and supply-chain gates | unresolved | No SBOM, provenance, recovery, alert, or dependency evidence supplied | Release integrity and recovery unknown | unknown — assign owner | Complete required public-release evidence |

**Recommendation: NO-GO.**

The UI evidence remains valid for its recorded scope, but it cannot compensate for authorization and privileged-bypass blockers. This recommendation is not proof of complete security, ASVS compliance, or future production behavior.

### Actions

External actions performed: none.