## Firebase candidate

### Mode

Requested mode: release review. Effective mode: `ship`.

Elevation triggers: public deployment, multi-tenant user data, authorization rules, and an Admin SDK privileged path.

### Evidence

Observed:

- The Firebase client API key has a synthetic, structurally valid public-client shape.
- Firestore Rules allow every read and write unconditionally.
- The Admin endpoint accepts caller-supplied `uid` and `recordId` without an independent authorization decision.
- Cloud restriction evidence was not collected.
- The authorization matrix contains only user A reading user A’s own record.

Unknown: exact artifact/commit, production project, deployed-rule parity, IAM scope, Storage rules, privacy lifecycle, operations, and supply-chain evidence.

The client API key identifies/routes requests to a Firebase project and may support quota or API restriction enforcement. Its visibility does not grant Admin SDK authority, but its shape does not establish that it is synthetic at runtime, correctly project-bound, cloud-restricted, or safe. Most importantly, it does not authorize database access—Security Rules and privileged server/IAM paths do that.

### Contract

Review only; no files or external systems changed. Explicit non-goals: remediation, deployment, credential inspection, and cloud configuration changes.

| Dimension | Option A: release now | Option B: block and remediate |
| --- | --- | --- |
| User value | Earlier availability | Delayed but tenant-safe |
| Security/privacy | Critical cross-tenant exposure | Enables deny-by-default controls |
| Maintenance | Incident-driven complexity | Explicit authorization model |
| Accessibility | No difference established | Preserves existing UI |
| Cost | Lower immediate cost; high incident risk | Remediation and retest cost |
| Portability | Not material | Not material |
| Reversibility | Data exposure may be irreversible | Release delay is reversible |

Chosen: Option B. Accepted cost: delayed release. Revisit trigger: restrictive deployed rules, independently authorized Admin operations, completed cloud checks, and a full negative authorization matrix.

### Slices

No implementation slices were performed.

UI evidence: unresolved; none was supplied. It neither mitigates nor worsens the authorization failures.

### Trust

Principal boundaries:

- Client → Firestore: fails closed access-control expectations because `allow read, write: if true` permits anonymous and cross-tenant access.
- Requester → Admin endpoint → Firebase Admin SDK: Admin SDK bypasses Firestore Security Rules. Caller-controlled identity and object identifiers therefore enable cross-user mutation unless the server authenticates the requester and independently authorizes the requested record/action.
- Client identifier → cloud project: contextual public identifier only; cloud restrictions require manual verification.

OWASP Top 10:2025 concerns include A01 Broken Access Control, A02 Security Misconfiguration, A06 Insecure Design, and A09 Security Logging and Alerting Failures. Applicable ASVS 5.0.0 requirement IDs were not evaluated and remain unresolved.

### Release

Artifact: unknown; Scope: public multi-tenant Firebase candidate; Environment: public/production project unresolved; Policy: VibeWorthy release gates; Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated failure | Firestore authorization | fail | `allow read, write: if true` | Anonymous and cross-tenant CRUD | unknown — assign owner | Replace with deny-by-default, owner/action/field rules |
| manual check | Admin SDK bypass path | fail | Body supplies `uid` and `recordId`; no independent authorization | Privileged cross-user update | backend security owner | Derive actor from verified authentication and authorize tenant, object, action, and fields before Admin use |
| manual check | Firebase API/application restrictions | unresolved | Evidence explicitly not collected | Key misuse, quota abuse, or wrong project association | cloud owner | Verify restrictions in the named cloud project without recording the value |
| manual check | Authorization matrix | fail | Only A → own read passed | All negative and mutation paths unproved | independent security reviewer | Test anonymous, A→B, B→A, CRUD, list/query, protected-field changes, and Admin path |
| manual check | Generated critical authorization review | unresolved | No named human reviewer or independent oracle supplied | Implementation and tests may share the same blind spot | unknown — assign owner | Obtain named human review and independent enforcement-boundary tests |
| residual risk | Remaining public-release gates | unresolved | Privacy, supply chain, recovery, alerts, and deployed parity not supplied | Additional release blockers may exist | release owner | Complete the public-release evidence set |

Recommendation: `NO-GO`.

The unconditional Rules are a demonstrated isolation failure, and the unauthorised Admin path independently bypasses those Rules. This recommendation does not establish complete security or compliance; it applies only to the described evidence.

### Actions

External actions performed: none.

---

## Supabase candidate

### Mode

Requested mode: release review. Effective mode: `ship`.

Elevation triggers: public multi-tenant release, RLS authorization, and use of a service-role credential.

### Evidence

Observed:

- UI build, keyboard operation, 320-pixel reflow, and error recovery passed with tool and date recorded.
- RLS is enabled, and SELECT uses `auth.uid() = owner_id`.
- INSERT lacks `WITH CHECK`.
- A `SECURITY DEFINER` function lacks a fixed `search_path`.
- The server reads the service-role credential from server environment rather than exposing it to the client.
- The privileged endpoint accepts caller-supplied `tenant_id`.
- Tests cover only A → own read, were generated by the migration’s authoring agent, and have no named human reviewer.
- Cloud-role verification was not performed.

A Supabase publishable/legacy anonymous key, if present in a client, identifies the project and invokes the intended public role. Visibility alone does not establish effective RLS, correct grants, project association, Storage/Realtime/function safety, or authorization. The service-role credential is different: it is privileged and bypasses RLS. Keeping it server-side is necessary but insufficient; every server operation using it must authenticate and independently authorize the tenant, object, action, and fields.

### Contract

Review only; no remediation or cloud action. Explicit non-goals: modifying migrations, invoking the privileged endpoint, inspecting credential values, deployment, or cloud-role changes.

| Dimension | Option A: release now | Option B: block while preserving UI evidence |
| --- | --- | --- |
| User value | Earlier release | Delayed release; known UI quality retained |
| Security/privacy | Tenant insertion and bypass risks | Correct enforcement before exposure |
| Maintenance | Latent privilege defects | Explicit policies and narrow server authority |
| Accessibility | Recorded passes retained | Same passes retained |
| Cost | Lower immediate cost; incident risk | Review and test cost |
| Portability | Not material | Fixed function context improves predictability |
| Reversibility | Cross-tenant writes may persist | Delay is reversible |

Chosen: Option B. Accepted cost: delayed release. Revisit trigger: safe INSERT policy, hardened function, independently authorized service-role path, human review, negative tests, and cloud-role verification.

### Slices

No implementation slices were performed.

| UI state | Evidence state | Evidence |
| --- | --- | --- |
| Loading | unresolved | Not supplied |
| Empty | unresolved | Not supplied |
| Error and recovery | tested | Passed; tool and date recorded |
| Duplicate or stale action | unresolved | Not supplied |
| Timeout and retry | unresolved | Not supplied |
| Keyboard and focus restoration | tested | Keyboard passed; focus restoration detail unresolved |
| 320 CSS-pixel reflow | tested | Passed |
| Long and translated content | unresolved | Not supplied |
| Performance at activation/commitment boundary | unresolved | Boundary and measurement not supplied |

Build pass is also preserved. These valid UI results do not compensate for backend authorization failures.

### Trust

Principal boundaries:

- Authenticated client → table SELECT: own-row predicate is promising but has only a positive test.
- Client → INSERT: missing `WITH CHECK` fails to establish that the inserted owner/tenant is the authenticated caller.
- Caller → server → service role: service role bypasses RLS. Trusting caller-supplied `tenant_id` without independent authorization can cross tenant boundaries.
- Caller → `SECURITY DEFINER`: an unfixed `search_path` can permit object-resolution attacks or unintended privileged behavior, depending on grants and schema configuration.
- Client identifier → Supabase project/public role: contextual identifier, not proof of authorization or cloud configuration.

OWASP Top 10:2025 concerns include A01 Broken Access Control, A02 Security Misconfiguration, A05 Injection/object-resolution risk, A06 Insecure Design, and A08 Software or Data Integrity Failures. Applicable exact ASVS 5.0.0 IDs were not evaluated.

### Release

Artifact: unknown migration/server/UI candidate; Scope: public multi-tenant Supabase release; Environment: public/production project unresolved; Policy: VibeWorthy release gates; Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated pass | UI build | pass | Dated tool record supplied | None observed in tested scope | UI owner | Retain evidence against exact artifact |
| automated pass | Keyboard operation | pass | Dated tool record supplied | Focus restoration not fully established | UI owner | Add focus-restoration evidence |
| automated pass | 320px reflow | pass | Dated tool record supplied | Content extremes untested | UI owner | Test long and translated content |
| automated pass | Error recovery | pass | Dated tool record supplied | Timeout/retry unresolved | UI owner | Test timeout and retry |
| automated failure | INSERT tenant/owner enforcement | fail | INSERT policy lacks `WITH CHECK` | Caller may insert rows outside permitted ownership | database security owner | Add restrictive `WITH CHECK` and protected-field tests |
| automated failure | Privileged function hardening | fail | `SECURITY DEFINER` has no fixed `search_path` | Privileged object-resolution risk | database security owner | Fix `search_path`, minimize grants, and test direct RPC access |
| manual check | Service-role bypass endpoint | fail | Server accepts caller-supplied `tenant_id` | RLS-bypassing cross-tenant access | backend security owner | Authenticate caller and independently authorize server-derived tenant scope |
| manual check | Credential placement | pass | Service-role material is read from server environment | Store scope, rotation, and artifact history remain unverified | secrets owner | Verify managed storage, least privilege, rotation, and history |
| manual check | Authorization matrix | fail | Only A → own read covered | Cross-user, writes, lists, RPC, Storage, and Realtime unproved | independent security reviewer | Run full negative matrix at deployed-equivalent boundaries |
| manual check | Independent critical-logic review | unresolved | Same agent produced migration and tests; no human named | No independent oracle | unknown — assign owner | Name a qualified reviewer and obtain independent negative tests |
| manual check | Cloud role/project verification | unresolved | Not performed | Deployed grants, roles, and project association unknown | cloud owner | Verify deployed RLS, grants, roles, functions, Storage, and Realtime |
| residual risk | Remaining public-release gates | unresolved | Supply-chain, recovery, alerts, and privacy evidence absent | Additional blockers may exist | release owner | Complete release evidence |

Recommendation: `NO-GO`.

The UI evidence remains valid and should be retained, but authorization is a separate release gate. Missing INSERT enforcement, an unsafe privileged function context, an untrusted tenant selector on an RLS-bypass path, and absent independent review prohibit public release.

This recommendation applies only to the described artifact, scope, environment, cutoff, and policy. It does not prove security, compliance, profitability, or future production behavior.

### Actions

External actions performed: none.