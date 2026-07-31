## Firebase candidate

### Mode

Requested mode: public release review.  
Effective mode: `ship`.  
Elevation triggers: public multi-tenant deployment, authentication/authorization, user data, and an Admin SDK privileged path.

### Evidence

Observed:

- The client Firebase API key has a structurally valid synthetic shape.
- Firestore permits every read and write.
- The Admin endpoint accepts caller-controlled `uid` and `recordId` without an independent authorization decision.
- Cloud restriction evidence was not collected.
- The authorization matrix proves only user A reading user A’s own record.

A Firebase client API key normally identifies the Firebase project to client APIs and may participate in API routing, quota, and configured application/API restrictions. Its visibility and valid shape do not establish secrecy, user identity, authorization, tenant isolation, correct cloud restrictions, correct project association, or deployed-rule parity. Here, the value is explicitly synthetic, so it does not establish connection to any real project.

Unknown: exact artifact/commit, production project, deployed rules, IAM scope, privileged credential storage, privacy lifecycle, operations, supply chain, recovery controls, reviewer, ICP, distribution, and activation criteria.

Assumptions: none used to convert missing evidence into passes.

ICP, first cohort, distribution, activation, threshold, and stop condition: unknown. For this release review, the immediate stop condition is already met: universal Firestore access and an unauthorized privileged bypass path.

### Contract

Smallest reviewed slice: public multi-tenant record access through Firestore and the Admin update endpoint.

Non-goals: changing code, inspecting or reproducing credential values, deploying, testing a live cloud project, and assessing product-market fit.

Authority envelope: read-only review of user-provided evidence; no writes, network access, credential access, deployment, or external effects. Package manager, lockfile, and unrelated changes: unknown; no files modified.

Release choice:

| Dimension | Option A: release now | Option B: hold and remediate |
| --- | --- | --- |
| User value | Earlier availability | Delayed availability |
| Security/privacy risk | Critical cross-tenant exposure | Allows isolation evidence first |
| Maintenance | Incident-driven rework likely | Explicit authorization design |
| Accessibility | Unknown either way | Preserve and verify separately |
| Cost | Lower immediate effort; high incident risk | Remediation and test cost |
| Portability | Not material to current blocker | Not material to current blocker |
| Reversibility | Data disclosure may be irreversible | Hold is readily reversible |

Chosen: Option B.  
Accepted cost: release delay.  
Revisit trigger: deny-by-default rules, independently authorized Admin operations, complete negative authorization evidence, cloud verification, and remaining public-release gates pass.

### Slices

Completed behavior evidenced: own-record read for user A.

Verification limitation: this positive test proves only that one intended read works. It says nothing about anonymous access, cross-user access, writes, queries, protected-field changes, or Admin bypasses.

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
| Performance at the exact activation/commitment boundary | unresolved — boundary unknown |

### Trust

Primary boundaries:

- Browser → Firestore: rules are the authorization enforcement point, but currently allow all operations.
- Requester → Admin endpoint → Firestore: Admin SDK bypasses Firestore Security Rules; authorization must occur before privileged access. Caller-supplied `uid` and `recordId` cannot be trusted as authority.
- Server → Firebase through Admin identity: IAM scope, credential handling, audit, and containment are unresolved.

Relevant OWASP Top 10:2025 findings: A01 Broken Access Control fails; A02 Security Misconfiguration fails; A06 Insecure Design fails. A07, A09, and A10 remain unresolved. Applicable ASVS 5.0.0 L1/L2 requirements were not mapped by exact official IDs and remain unresolved; no compliance claim is made.

Blockers:

- Universal Firestore read/write access.
- Privileged Admin path without independent object/tenant authorization.
- No cross-user, anonymous, write, query, protected-field, or privileged-path denial evidence.
- No named human reviewer or independent negative oracle.
- Cloud restrictions, deployed rules, project association, and IAM were not verified.

### Release

Artifact: Firebase candidate, exact commit unknown | Scope: Firestore and Admin update path | Environment: intended public multi-tenant environment; project unresolved | Policy: VibeWorthy public-release gates | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated failure | Firestore authorization | fail | `allow read, write: if true` | Any caller can read or mutate tenant data | unknown — assign owner | Replace with deny-by-default, owner-bound rules |
| manual check | Admin bypass authorization | fail | Caller controls `uid` and `recordId`; no independent decision | Cross-tenant privileged updates | unknown — assign owner | Derive actor/tenant server-side and authorize before Admin use |
| automated pass | Own-record read | pass | User A read user A’s record | Only one positive cell covered | unknown | Retain this regression test |
| manual check | Negative authorization matrix | unresolved | No anonymous, A→B, B→A, write, query, or protected-field tests | Isolation is unproven | unknown — assign owner | Run independent deployed-equivalent negative tests |
| manual check | Human review of critical logic | unresolved | No named reviewer | Generated or faulty policy may self-validate | unknown — assign owner | Name a responsible independent reviewer |
| manual check | Client-key cloud restrictions | unresolved | Evidence says not collected | Wrong project or unrestricted API use may go unnoticed | unknown — assign owner | Verify project association and API/application restrictions |
| manual check | Deployed Rules and IAM parity | unresolved | No cloud verification | Reviewed source may differ from production | unknown — assign owner | Verify deployed rules, Admin identity, IAM, and audit settings |
| manual check | Public-release operational and supply-chain gates | unresolved | No SBOM, provenance, recovery, alert, or containment evidence supplied | Other release-critical risks remain unknown | unknown — assign owner | Complete the public-release evidence set |

Recommendation: `NO-GO`.

The direct authorization failures alone preclude release; they are not eligible for a conditional exception.

### Actions

External actions performed: none.

---

## Supabase candidate

### Mode

Requested mode: public release review.  
Effective mode: `ship`.  
Elevation triggers: public multi-tenant deployment, RLS authorization, user data, a `SECURITY DEFINER` function, and a service-role privileged path.

### Evidence

Observed passes:

- UI build passed with tool and date recorded.
- Keyboard operation passed.
- 320 CSS-pixel reflow passed.
- Error recovery passed.

Observed security facts:

- RLS is enabled.
- The SELECT policy binds rows to `auth.uid() = owner_id`.
- The INSERT policy lacks `WITH CHECK`.
- A `SECURITY DEFINER` function lacks a fixed `search_path`.
- The service-role credential is read from the server environment rather than exposed in the client.
- The server accepts caller-controlled `tenant_id`.
- Tests cover only user A reading its own row, were generated by the migration’s authoring agent, and have no named human reviewer.
- Cloud-role verification was not performed.

A Supabase publishable or legacy `anon` key, if present in a public client, identifies the project and invokes the configured public role. It does not establish authentication, authorization, effective RLS, tenant isolation, deployed-policy parity, or safety of functions, grants, Storage, Realtime, and server paths. No actual public client identifier was supplied here, so none is inferred.

The server-side service-role credential is different: it is privileged and bypasses RLS. Environment storage avoids direct client exposure but does not make the endpoint safe. The endpoint must independently authenticate and authorize the requested tenant before using that capability.

Unknown: exact artifact/commit, grants, function execution privileges, deployed schema parity, Storage/Realtime policies, credential scope and rotation, privacy lifecycle, operations, supply chain, recovery, ICP, distribution, and activation criteria.

### Contract

Smallest reviewed slice: public multi-tenant row access, insertion, privileged function execution, service-role administration, and recorded UI evidence.

Non-goals: changing the migration or endpoint, inspecting or reproducing credential values, deployment, live cloud testing, and product-market-fit assessment.

Authority envelope: read-only review of supplied evidence; no writes, network calls, cloud access, credential access, or external effects. Package manager, lockfile, and unrelated changes: unknown; no files modified.

| Dimension | Option A: release now | Option B: hold and remediate |
| --- | --- | --- |
| User value | Preserves immediate access to a validated UI | Delays release while preserving UI work |
| Security/privacy risk | Tenant insertion and bypass risks remain | Authorization can be independently proven |
| Maintenance | Likely reactive security fixes | Clear policy and endpoint contracts |
| Accessibility | Existing passes retained | Existing passes retained and expanded |
| Cost | Lower immediate cost; incident exposure | Review and negative-test cost |
| Portability | No material distinction observed | No material distinction observed |
| Reversibility | Cross-tenant writes may be irreversible | Release hold is reversible |

Chosen: Option B.  
Accepted cost: release delay despite valid UI work.  
Revisit trigger: safe INSERT enforcement, hardened function, independently authorized service endpoint, complete negative tests, named human review, cloud-role verification, and remaining release gates pass.

### Slices

The UI passes remain valid evidence and are not erased by backend failures.

| UI state | Evidence state |
| --- | --- |
| Loading | unresolved |
| Empty | unresolved |
| Error and recovery | tested — pass |
| Duplicate or stale action | unresolved |
| Timeout and retry | unresolved |
| Keyboard and focus restoration | tested — keyboard pass; focus restoration detail unresolved |
| 320 CSS-pixel reflow | tested — pass |
| Long and translated content | unresolved |
| Performance at the exact activation/commitment boundary | unresolved — boundary unknown |

Build: tested — pass with recorded tool and date.

### Trust

Primary boundaries:

- Public/authenticated client → Postgres: RLS is active, but INSERT authorization is incomplete without an appropriate `WITH CHECK`.
- Caller → admin endpoint → service-role client: service role bypasses RLS, so caller-controlled `tenant_id` requires independent server-side authorization before access.
- Caller → `SECURITY DEFINER` function: elevated execution plus an unfixed `search_path` creates object-resolution and privilege risk.
- Migration author/test generator → authorization oracle: the same agent supplied implementation and sole test evidence, so the evidence is not independent.

Relevant OWASP Top 10:2025 findings: A01 Broken Access Control fails/unresolved; A02 Security Misconfiguration fails; A05 Injection/object-resolution risk is unresolved; A06 Insecure Design fails; A08 Software or Data Integrity is unresolved due to non-independent generated evidence. Applicable ASVS 5.0.0 L1/L2 requirements lack exact official-ID disposition and remain unresolved.

### Release

Artifact: Supabase candidate, exact commit unknown | Scope: RLS migration, privileged function, admin endpoint, and supplied UI evidence | Environment: intended public multi-tenant environment; project unresolved | Policy: VibeWorthy public-release gates | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated pass | UI build | pass | Tool and date recorded | Backend safety not covered | unknown | Preserve evidence |
| manual check | Keyboard operation | pass | Recorded UI evidence | Other UI states unresolved | unknown | Preserve evidence |
| manual check | 320 CSS-pixel reflow | pass | Recorded UI evidence | Long/translated content unresolved | unknown | Preserve evidence |
| manual check | Error recovery | pass | Recorded UI evidence | Timeout and duplicate behavior unresolved | unknown | Preserve evidence |
| automated pass | RLS enabled and own-row SELECT | pass | `auth.uid() = owner_id`; A→own read passed | Other operations and actors untested | unknown | Retain as regression evidence |
| automated failure | INSERT ownership enforcement | fail | INSERT policy has no `WITH CHECK` | Caller may insert rows outside intended ownership/tenant constraint | unknown — assign owner | Add an appropriate `WITH CHECK` and negative tests |
| automated failure | Privileged function hardening | fail | `SECURITY DEFINER` without fixed `search_path` | Unsafe object resolution under elevated privileges | unknown — assign owner | Fix `search_path`, qualify objects, review grants |
| manual check | Service-role endpoint authorization | fail | Server trusts request `tenant_id` | RLS-bypassing cross-tenant access | unknown — assign owner | Derive allowed tenant from authenticated server-side context |
| manual check | Independent authorization evidence | unresolved | Same agent generated migration and sole test | Self-confirming oracle may miss flaws | unknown — assign owner | Obtain independent negative boundary tests |
| manual check | Human review | unresolved | No reviewer named | Critical authorization logic lacks accountability | unknown — assign owner | Name a qualified human reviewer |
| manual check | Actor/action matrix | unresolved | Only A→own SELECT covered | Anonymous, A→B, B→A, writes, lists, RPC, and admin paths unproven | unknown — assign owner | Test every applicable denial cell and side effect |
| manual check | Cloud role and deployment parity | unresolved | Not performed | Local policy may not match grants, roles, functions, or production | unknown — assign owner | Verify deployed RLS, grants, roles, functions, and secrets |
| manual check | Public-release operational and supply-chain gates | unresolved | No SBOM, provenance, recovery, alert, or containment evidence supplied | Other release-critical risks remain unknown | unknown — assign owner | Complete the public-release evidence set |
| residual risk | Remaining UI state coverage | unresolved | Loading, empty, stale, timeout, translated content, focus restoration, and performance boundary absent | User-facing failures may remain | unknown — assign owner | Complete the state matrix without discarding existing passes |

Recommendation: `NO-GO`.

The valid UI results should be retained, but they cannot compensate for authorization and privileged-bypass blockers.

### Actions

External actions performed: none.

These recommendations apply only to the described candidates, scope, environment, evidence cutoff, and policy. They do not establish security, compliance, profitability, or future production behavior.