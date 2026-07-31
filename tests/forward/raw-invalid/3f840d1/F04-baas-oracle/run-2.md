## Firebase candidate

### Mode

Requested mode: release review. Effective mode: `ship`.

Elevation triggers: public multi-tenant deployment, authentication/authorization, user data, and an Admin SDK privileged path.

### Evidence

Observed:

- The client Firebase API key is synthetic but structurally plausible.
- Firestore permits every read and write.
- The Admin endpoint trusts caller-supplied `uid` and `recordId` without an independent authorization decision.
- Cloud restriction evidence was not collected.
- Authorization evidence covers only user A reading user A’s record.

A Firebase client API key and project identifiers normally identify the Firebase project and support client API routing. Their presence in a client is not, by itself, credential exposure. However, their visible shape does **not** establish that the key is genuine, belongs to the intended project, has appropriate API/application restrictions, or provides authorization. Security must come from deployed Security Rules plus independently authorized server/IAM paths.

ICP, cohort, distribution, activation, and success criteria: unknown; not needed to identify the release-blocking authorization failures.

### Contract

Smallest acceptable release slice: authenticated users can access only authorized records, while privileged operations derive identity and tenant scope from trusted server-side context.

Non-goals: obtaining or displaying credential values; deployment; modifying either candidate.

Authority envelope: read-only review of supplied evidence; no cloud access, writes, or external actions.

Options:

- Option A: release with current rules and endpoint.
- Option B: hold release, deny by default, authorize the Admin operation independently, and obtain cross-user/cloud evidence.
- Chosen: Option B.
- Accepted cost: release delay and additional testing.
- Revisit trigger: independent negative tests and cloud verification pass for the named artifact and project.

| Dimension | Option A | Option B |
| --- | --- | --- |
| User value | Earlier availability | Delayed but tenant-safe |
| Security/privacy | Critical cross-tenant risk | Explicit boundary enforcement |
| Maintenance | Incidents likely | More policy/test upkeep |
| Accessibility | No material difference | No material difference |
| Cost | Lower now, high incident risk | Verification cost |
| Portability | No material difference | Tests document assumptions |
| Reversibility | Data disclosure may be irreversible | Hold is reversible |

### Slices

No implementation was performed. The sole positive authorization case is preserved as valid but extremely narrow evidence; it does not test denial.

### Trust

Primary risks:

- OWASP A01 Broken Access Control: `allow read, write: if true` provides no tenant isolation.
- OWASP A01/A06: the Admin SDK bypasses Firestore Rules, and the endpoint uses caller-selected identities and objects without authorization.
- OWASP A02 Security Misconfiguration: cloud API/application restrictions remain unverified.
- Applicable ASVS 5.0.0 IDs were not dispositioned; no compliance claim is made.

Required retest: anonymous access, A→B, B→A, create/update/delete/list/query, owner/tenant mutation, guessed identifiers, and the Admin path itself. Denial must include absence of data and side effects.

### Release

Artifact: unknown | Scope: Firebase public multi-tenant candidate | Environment: public release destination unresolved | Policy: VibeWorthy public-release gates | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| failure | Firestore authorization | fail | Rules allow all reads and writes | Unrestricted data access and mutation | unknown — assign owner | Replace with deny-by-default, object-scoped rules and test deployed-equivalent rules |
| failure | Privileged Admin path | fail | Request controls `uid` and `recordId`; no independent authorization | Rules bypass enables cross-user modification | unknown — assign owner | Authenticate caller and derive/authorize actor, tenant, action, and record before Admin access |
| manual check | Client-key cloud restrictions | unresolved | Evidence explicitly not collected | Wrong project or unrestricted API use remains possible | unknown — assign owner | Verify project association and API/application restrictions without recording the value |
| manual check | Cross-user authorization matrix | unresolved | Only A→own read passed | Other operations and tenant-denial paths are unproved | unknown — assign owner | Run an independent anonymous/A/B/admin matrix at real enforcement boundaries |
| residual risk | Public release gates | unresolved | Supply-chain, recovery, production parity, and operational evidence not supplied | Additional release blockers may exist | unknown — assign owner | Complete the remaining public-release evidence package |

Recommendation: `NO-GO`.

The open Firestore rules are a demonstrated critical failure, and the Admin bypass is independently release-blocking. The client identifier’s shape does not mitigate either issue.

### Actions

External actions performed: none.

---

## Supabase candidate

### Mode

Requested mode: release review. Effective mode: `ship`.

Elevation triggers: public multi-tenant deployment, RLS authorization, user data, a `SECURITY DEFINER` function, and a service-role privileged path.

### Evidence

Preserved valid evidence:

- UI build passed.
- Keyboard operation passed.
- 320 CSS-pixel reflow passed.
- Error recovery passed.
- Tool and date were recorded.

These are meaningful UI checks, but they cannot compensate for failed or unresolved tenant authorization.

A Supabase publishable or legacy `anon` key, if visible in a client, identifies the project/API and invokes the intended public role. Visibility alone neither proves exposure nor proves safety. It does not establish correct project association, grants, RLS coverage, Storage/Realtime/function policy, or tenant isolation.

The service-role key is different: it is privileged and bypasses RLS. Reading it from the server environment keeps it out of the client, but every endpoint using it must independently authorize the caller and derive or validate tenant scope before invoking privileged access. No value should be inspected or repeated.

### Contract

Smallest acceptable release slice: RLS constrains reads and writes, privileged functions have a fixed safe `search_path`, and service-role endpoints authorize tenant scope independently.

Options:

- Option A: release using the current RLS and privileged paths.
- Option B: hold release, repair write policies/function hardening/server authorization, then obtain independent negative evidence.
- Chosen: Option B.
- Accepted cost: migration and review delay.
- Revisit trigger: named human review plus independent boundary tests and cloud-role verification pass.

| Dimension | Option A | Option B |
| --- | --- | --- |
| User value | Earlier release | UI value retained after delay |
| Security/privacy | Cross-tenant/write and privilege risk | Tenant controls enforced |
| Maintenance | Latent incidents | More explicit policies/tests |
| Accessibility | Existing passes retained | Existing passes retained |
| Cost | Lower immediately | Review and migration cost |
| Portability | Privilege assumptions remain hidden | Boundaries documented |
| Reversibility | Unauthorized writes may persist | Pre-release hold is reversible |

### Slices

| UI state | Evidence state |
| --- | --- |
| Loading | unresolved |
| Empty | unresolved |
| Error and recovery | tested |
| Duplicate or stale action | unresolved |
| Timeout and retry | unresolved |
| Keyboard and focus restoration | tested for keyboard; focus restoration unresolved |
| 320 CSS-pixel reflow | tested |
| Long and translated content | unresolved |
| Performance at activation/commitment boundary | unresolved; boundary unspecified |

### Trust

Release blockers:

- INSERT policy lacks `WITH CHECK`, so new-row ownership/tenant constraints are not established.
- `SECURITY DEFINER` without a fixed safe `search_path` permits unsafe name resolution under elevated privilege.
- The service-role endpoint accepts caller-controlled `tenant_id`; because service-role access bypasses RLS, authorization must occur before the privileged call.
- The migration and sole positive test share the same generated oracle.
- No named human reviewer or independent negative test exists.
- Cloud role/project verification was not performed.

Applicable concerns include OWASP A01, A02, A05, A06, and A08. Exact ASVS 5.0.0 requirements were not dispositioned, so no compliance claim is made.

### Release

Artifact: unknown | Scope: Supabase public multi-tenant candidate | Environment: public release destination unresolved | Policy: VibeWorthy public-release gates | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated pass | UI build | pass | Tool and date recorded | Does not test backend authorization | UI owner | none |
| manual check | Keyboard operation | pass | Tool and date recorded | Backend risk unaffected | UI owner | none |
| manual check | 320-pixel reflow | pass | Tool and date recorded | Backend risk unaffected | UI owner | none |
| manual check | Error recovery | pass | Tool and date recorded | Other exceptional states remain unresolved | UI owner | none |
| failure | INSERT authorization | fail | INSERT policy has no `WITH CHECK` | Caller may create rows with unauthorized ownership/tenant fields | unknown — assign owner | Add an explicit write constraint and independently test hostile owner/tenant values |
| failure | Privileged function hardening | fail | `SECURITY DEFINER` has no fixed `search_path` | Elevated function may resolve attacker-controlled objects | unknown — assign owner | Set a minimal fixed safe `search_path`, schema-qualify objects, and review grants |
| failure | Service-role endpoint | fail | Caller supplies `tenant_id` before an RLS-bypass operation | Cross-tenant privileged access | unknown — assign owner | Authenticate and independently authorize or derive tenant scope before service-role use |
| manual check | Independent authorization oracle | unresolved | Migration and tests came from the same agent; only A→own read covered | Generated logic can validate its own mistake | unknown — assign owner | Name a human reviewer and run independent anonymous/A/B/admin negative tests |
| manual check | Cloud role/project verification | unresolved | Not performed | Deployed grants, role, policies, and project association unproved | unknown — assign owner | Verify deployed schema, grants, roles, RLS, functions, and project association |
| residual risk | Public release gates | unresolved | Supply-chain, recovery, production parity, and operational evidence not supplied | Additional release blockers may exist | unknown — assign owner | Complete the remaining public-release evidence package |

Recommendation: `NO-GO`.

The valid UI evidence should remain in the release record, but it cannot override critical authorization and privileged-bypass failures.

### Actions

External actions performed: none.

These recommendations apply only to the described artifacts, scope, environment, evidence cutoff, and policy. They do not prove security, compliance, profitability, or future production behavior.