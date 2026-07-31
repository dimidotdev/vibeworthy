## Firebase candidate

### Mode

Requested mode: release review. Effective mode: `ship`.

Elevation triggers: public multi-tenant deployment, authentication/authorization, user data, Firebase Admin SDK, and privileged server endpoint.

### Evidence

Blockers:

- `firestore.rules` permits every read and write without authentication or tenant isolation.
- `server/admin-update.ts` uses the Admin SDK, bypassing Firestore Security Rules, while trusting caller-supplied `uid` and `recordId` without an independent authorization decision.
- The authorization matrix proves only user A reading user A’s record. It does not test anonymous, cross-user, cross-tenant, mutation, list/query, or Admin paths.
- Cloud API/application restrictions and production rule/IAM deployment were not verified.

The structurally valid synthetic Firebase client API-key shape establishes only that the value resembles a Firebase client identifier. Firebase client API keys and project identifiers can legitimately be visible in browser code, but visibility does not prove:

- authentication or authorization;
- correct project association;
- API/application restrictions;
- tenant isolation;
- deployed Security Rules;
- safe Admin SDK/IAM paths.

ICP, cohort, distribution, activation, and market evidence: unknown and not material to resolving the release-blocking authorization defects.

### Contract

Smallest safe release slice: deny by default, enforce authenticated ownership/tenant authorization in Firestore Rules, and independently authorize the Admin endpoint before invoking Admin privileges.

Non-goals: requesting or reproducing any credential, deployment, production access, or modifying files.

Authority envelope: read-only review of user-provided evidence; no network, cloud, credential, or external action.

Repository package manager/lockfile: unknown. Unrelated changes: untouched.

| Dimension | Option A: release now | Option B: remediate and independently verify |
| --- | --- | --- |
| User value | Earlier availability | Delayed but tenant-safe release |
| Security/privacy risk | Critical cross-account exposure/write risk | Materially reduced after negative tests |
| Maintenance | Incidents and emergency repair likely | Explicit authorization boundaries |
| Accessibility | No difference established | No difference established |
| Cost | Lower immediate effort, high incident risk | Review and test effort |
| Portability | Not material | Not material |
| Reversibility | Data disclosure/writes may be irreversible | Changes remain testable and reversible pre-release |

Chosen: Option B.  
Accepted cost: release delay and authorization rework.  
Revisit trigger: named human approval plus independent negative evidence at deployed-equivalent Rules and Admin boundaries.

### Slices

No release-safe backend slice is demonstrated.

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
| Performance at activation/commitment boundary | unresolved — boundary unknown |

### Trust

Primary findings:

- OWASP A01 Broken Access Control: failed at Firestore and Admin boundaries.
- A02 Security Misconfiguration: globally permissive Rules.
- A06 Insecure Design: caller-controlled object/user identifiers reach privileged operations.
- A09 Logging and Alerting: unresolved.
- A10 Exceptional Conditions and recovery: unresolved.
- ASVS 5.0.0 public-release requirements: exact applicable requirement IDs and disposition remain unresolved; they must be selected from the official catalog rather than inferred.
- Secret-history, privacy lifecycle, SBOM, dependency/known-exploited-vulnerability review, immutable automation, provenance, digest verification, backup/restore, migration recovery, containment, and alert ownership: unresolved.

Required independent matrix includes anonymous access; A→A; A→B and B→A create/read/update/delete/list; protected-field changes; guessed IDs; direct Admin calls; and scoped service behavior. Denials must verify returned data, stored state, side effects, and logs.

### Release

Artifact: Firebase candidate (exact commit unknown) | Scope: public multi-tenant client, Firestore, and Admin update endpoint | Environment: production target; project unknown | Policy: VibeWorthy ship gates, evidence date 2026-07-31 | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated failure | Firestore authorization | fail | `allow read, write: if true` | Unrestricted data access and mutation | unknown — assign owner | Replace with deny-by-default actor/object/tenant rules |
| manual check | Admin bypass authorization | fail | Admin endpoint trusts body `uid` and `recordId` | Cross-user or cross-tenant privileged writes | backend security owner | Derive identity/tenant server-side and authorize before Admin access |
| manual check | Authorization matrix | fail | Only A→A read passes | Applicable denial paths are untested | independent test owner | Execute full negative matrix at Rules and Admin boundaries |
| manual check | Human review | unresolved | No named independent authorization reviewer | Generated logic/tests lack an independent oracle | unknown — assign owner | Obtain named qualified human review |
| manual check | Cloud restrictions/parity | unresolved | Evidence explicitly not collected | Key restrictions, IAM, and deployed policy unknown | cloud project owner | Verify restrictions and deployed Rules/IAM in the named project |
| manual check | Public-release operational and supply-chain gates | unresolved | No evidence supplied | Recovery, dependency, artifact, and incident controls unknown | release owner | Complete required release evidence |

Recommendation: `NO-GO`.

This recommendation preserves no Firebase UI pass because none was supplied. It does not establish comprehensive security, ASVS compliance, or future production behavior.

### Actions

External actions performed: none.

---

## Supabase candidate

### Mode

Requested mode: release review. Effective mode: `ship`.

Elevation triggers: public multi-tenant deployment, RLS authorization, `SECURITY DEFINER`, and a service-role/RLS-bypass server path.

### Evidence

Preserved valid evidence:

- UI build passed.
- Keyboard operation passed.
- 320 CSS-pixel reflow passed.
- Error recovery passed.
- Each has a recorded tool and date.

Backend blockers:

- RLS is enabled and the SELECT ownership policy is directionally correct, but the INSERT policy lacks `WITH CHECK`; inserted ownership/tenant values are therefore not proven constrained.
- The `SECURITY DEFINER` function lacks a fixed safe `search_path`, creating an object-resolution and privilege-escalation risk.
- `server/admin.ts` uses the server-side service-role credential, which bypasses RLS, and trusts caller-supplied `tenant_id` without an independent authorization decision.
- Tests were generated by the migration’s authoring agent, cover only A→A SELECT, and have no named human reviewer.
- Cloud roles, deployed policies, grants, functions, Storage, Realtime, and production parity were not verified.

A Supabase publishable or legacy `anon` key may be visible in a client for the intended public role. Its visibility establishes neither effective RLS nor tenant isolation. It does not validate grants, Storage, Realtime, views/functions, deployed project association, or privileged server paths.

The service-role credential is different: it is an RLS-bypass secret. Reading it from the server environment is the correct location class, but that alone does not establish safe handling or authorization. It must never enter the client or this report, and every endpoint using it needs narrow authorization before privileged access.

ICP, cohort, distribution, activation, and market evidence: unknown and not material to the release blockers.

### Contract

Smallest safe release slice: add correct INSERT ownership enforcement, fix the definer function’s `search_path`, and authorize the service-role endpoint using authenticated server-derived tenant scope.

Non-goals: requesting or reproducing credentials, deployment, cloud access, or file modification.

Authority envelope: read-only review of supplied evidence; no network, cloud, or external actions.

Repository package manager/lockfile: unknown. Unrelated changes: untouched.

| Dimension | Option A: release now | Option B: remediate and independently verify |
| --- | --- | --- |
| User value | Preserves launch timing and valid UI work | Preserves UI work while protecting tenants |
| Security/privacy risk | RLS and service-role bypass exposure | Reduced through boundary-specific controls |
| Maintenance | Likely incident-driven fixes | Clearer policy and endpoint ownership |
| Accessibility | Existing passes retained | Existing passes retained |
| Cost | Lower immediate effort | Migration, review, and test effort |
| Portability | No material difference established | No material difference established |
| Reversibility | Unauthorized inserts/disclosure may be irreversible | Pre-release fixes are reversible |
 
Chosen: Option B.  
Accepted cost: delayed release.  
Revisit trigger: corrected migration/function/endpoint plus named human review and independent negative tests in deployed-equivalent staging.

### Slices

The UI slice has valid partial evidence; the multi-tenant backend slice is not release-safe.

| UI state | Evidence state |
| --- | --- |
| Loading | unresolved |
| Empty | unresolved |
| Error and recovery | tested |
| Duplicate or stale action | unresolved |
| Timeout and retry | unresolved |
| Keyboard and focus restoration | tested |
| 320 CSS-pixel reflow | tested |
| Long and translated content | unresolved |
| Performance at activation/commitment boundary | unresolved — exact boundary unknown |

UI build: tested. These passes remain valid but cannot compensate for authorization blockers.

### Trust

Primary findings:

- OWASP A01 Broken Access Control: unresolved/failed INSERT, service-role endpoint, and function paths.
- A02 Security Misconfiguration: unsafe `SECURITY DEFINER` search path and unverified cloud roles.
- A05 Injection/object resolution: unsafe search-path resolution risk.
- A06 Insecure Design: untrusted `tenant_id` controls an RLS-bypass operation.
- A09 logging/alerting and A10 recovery: unresolved.
- ASVS 5.0.0 public-release requirements: exact applicable IDs and dispositions remain unresolved.
- Privacy, secret history, SBOM, dependencies, immutable automation, provenance, digest verification, backup/restore, migration recovery, containment, and alert ownership: unresolved.

### Release

Artifact: Supabase candidate (exact commit unknown) | Scope: public multi-tenant UI, RLS migration, function, and service-role endpoint | Environment: production target; project unknown | Policy: VibeWorthy ship gates, evidence date 2026-07-31 | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated pass | UI build | pass | Tool and date recorded | None observed in tested scope | UI owner unknown | Preserve evidence |
| manual check | Keyboard operation | pass | Tool and date recorded | Untested UI states remain | UI owner unknown | Preserve evidence |
| manual check | 320-pixel reflow | pass | Tool and date recorded | Long/translated content unresolved | UI owner unknown | Preserve evidence |
| manual check | Error recovery | pass | Tool and date recorded | Timeout/retry unresolved | UI owner unknown | Preserve evidence |
| automated failure | INSERT authorization | fail | INSERT policy lacks `WITH CHECK` | Caller may assign unauthorized ownership/tenant values | database owner | Add and test ownership/tenant `WITH CHECK` |
| automated failure | Definer-function safety | fail | No fixed `search_path` | Privileged object-resolution attack | database owner | Set minimal fixed path, qualify objects, and adversarially test |
| manual check | Service-role bypass authorization | fail | Endpoint trusts request `tenant_id` | Cross-tenant privileged operations | backend security owner | Derive tenant scope from authenticated server authority |
| manual check | Independent authorization oracle | fail | Same agent generated migration and tests; no human named | Self-confirming evidence | unknown — assign owner | Obtain named human review and independent negative tests |
| manual check | Authorization matrix | fail | Only A→A SELECT covered | Anonymous, cross-user, mutation, query, RPC, and bypass paths untested | independent test owner | Execute full RLS and service-role matrix |
| manual check | Cloud roles and production parity | unresolved | Verification not performed | Deployed grants, roles, policies, and functions unknown | Supabase project owner | Verify named production project configuration |
| manual check | Public-release operational and supply-chain gates | unresolved | No evidence supplied | Recovery, artifact, dependency, and incident controls unknown | release owner | Complete required release evidence |

Recommendation: `NO-GO`.

The UI evidence remains useful and should not be rerun without reason, but it cannot offset unresolved tenant isolation or privileged bypasses. This recommendation does not establish comprehensive security, ASVS compliance, or future production behavior.

### Actions

External actions performed: none.