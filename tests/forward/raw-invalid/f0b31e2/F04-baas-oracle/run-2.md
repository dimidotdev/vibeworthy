## Firebase candidate

### Mode

Requested mode: release review. Effective mode: `ship`.

Elevation triggers: public multi-tenant deployment, authentication/authorization, user data, public endpoints, and Firebase Admin privileges.

### Evidence

Observed:

- The client API key is synthetic and merely has the shape of a Firebase key.
- Firestore permits every read and write.
- The Admin endpoint accepts caller-controlled `uid` and `recordId` without an independent authorization decision.
- Cloud restriction evidence was not collected.
- The authorization matrix proves only user A reading user A’s record.

Unknown: exact artifact/commit, production project, deployed-rule parity, IAM scope, API/application restrictions, UI evidence, privacy lifecycle, operations, and supply-chain gates.

A Firebase client API key and project identifiers normally identify the Firebase project so browser code can call Firebase services. Their visibility does not establish secrecy, authentication, authorization, project ownership, cloud restrictions, deployed rules, or production safety. Here, the synthetic value does not even establish association with a live project.

ICP, first cohort, distribution path, activation, and success/stop signals: unknown; no product evidence was supplied.

### Contract

Smallest reviewed slice: client → Firestore and request → Admin SDK authorization boundaries.

Non-goals: credential-value inspection, deployment, code modification, and claims of complete security or compliance.

Authority envelope: read-only assessment of supplied evidence; no credential access, network calls, cloud changes, or deployment.

Package manager/lockfile and unrelated changes: unknown; no files modified.

Options:

- Option A: release with current rules and endpoint.
- Option B: deny by default, derive identity/ownership from authenticated server context, constrain Admin operations, and verify a complete independent actor/action matrix.
- Chosen: Option B before release.
- Accepted cost: additional policy design, human review, and staging tests.
- Revisit trigger: only after deployed-equivalent rules, IAM, and every privileged endpoint pass independent tests.

| Dimension | Option A | Option B |
| --- | --- | --- |
| User value | Faster release | Slight delay; preserves tenant trust |
| Security/privacy | Critical cross-tenant exposure | Explicit boundary enforcement |
| Maintenance | Incidents likely | Policies/tests require upkeep |
| Accessibility | No material difference established | No material difference established |
| Cost | Lower immediate cost | Higher verification cost |
| Portability | Firebase-coupled | Firebase-coupled |
| Reversibility | Data exposure may be irreversible | Rules and endpoints can be revised safely |

### Slices

No implementation occurred.

UI state evidence is unresolved for loading, empty, error/recovery, duplicate/stale actions, timeout/retry, keyboard/focus restoration, 320-pixel reflow, long/translated content, and performance at the activation boundary.

### Trust

Principal blockers:

- `allow read, write: if true` is an observed A01 Broken Access Control and A02 Security Misconfiguration failure.
- The Admin SDK bypasses Firestore Rules. Trusting request-body `uid` and `recordId` permits object/tenant selection before any independent authorization.
- Anonymous, cross-user, reverse cross-user, create/update/delete/list/query, protected-field, malformed/replay, and privileged-path tests are missing.
- Cloud API/application restrictions, deployed rules, and IAM were not manually verified.
- Applicable ASVS 5.0.0 L1/L2 requirement IDs and evidence were not mapped from the official catalog.

### Release

Artifact: Firebase candidate, exact commit unknown | Scope: Firestore and Admin update path | Environment: public multi-tenant release, project unknown | Policy: VibeWorthy supplied version | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated failure | Firestore deny-by-default | fail | `allow read, write: if true` | Any caller may access or alter data | unknown — assign owner | Replace with scoped rules and test deployed equivalent |
| automated failure | Admin authorization | fail | Body controls `uid` and `recordId`; no independent decision | Rules bypass enables cross-tenant writes | unknown — assign owner | Authenticate caller and authorize target before Admin access |
| manual check | Cloud restrictions/project association | unresolved | Evidence explicitly not collected | Key abuse and wrong-project configuration remain possible | unknown — assign owner | Verify restrictions in the named cloud project |
| manual check | Authorization matrix | unresolved | Only A → own read passed | Other actors/actions and bypass paths unproved | unknown — assign owner | Run independent anonymous/A/B/admin negative matrix |
| residual risk | Synthetic client identifier | accepted | Structurally valid synthetic shape only | Establishes no live configuration or security property | release reviewer | Keep classified as contextual public configuration |

Recommendation: **NO-GO**. The permissive Rules and unauthorised Admin bypass are release-blocking failures. This decision does not establish complete security, compliance, or future production behavior.

### Actions

External actions performed: none.

---

## Supabase candidate

### Mode

Requested mode: release review. Effective mode: `ship`.

Elevation triggers: public multi-tenant deployment, user data, RLS authorization, privileged server credentials, and a public server endpoint.

### Evidence

Preserved passes: UI build, keyboard operation, 320-pixel reflow, and error recovery passed, with tool and date recorded.

Observed blockers:

- RLS is enabled and SELECT binds `auth.uid()` to `owner_id`.
- INSERT lacks `WITH CHECK`.
- A `SECURITY DEFINER` function lacks a fixed `search_path`.
- The server uses a service-role credential and accepts caller-controlled `tenant_id`.
- Generated tests share an oracle with the generated migration and cover only A → own read.
- No human reviewer is named; cloud-role verification was not performed.

A Supabase publishable or legacy `anon` key, if present in a client, identifies the project and invokes the intended public role. Visibility alone does not prove effective RLS, grants, project association, Storage/Realtime/function safety, or authorization. The service-role credential is different: it is privileged, must remain server-side, and bypasses RLS. Reading it from server environment avoids direct client exposure but does not make an endpoint safe.

ICP, first cohort, distribution path, activation, and success/stop signals: unknown.

### Contract

Smallest reviewed slice: browser → RLS and request → service-role server boundary.

Non-goals: credential-value inspection, deployment, code modification, and claims of complete security or compliance.

Authority envelope: read-only evidence assessment; no network, cloud, database, or deployment actions.

Package manager/lockfile and unrelated changes: unknown; no files modified.

Options:

- Option A: release based on SELECT policy and current generated tests.
- Option B: add explicit write checks, secure definer execution, authorize tenant selection before privileged access, and obtain human-reviewed independent negative evidence.
- Chosen: Option B before release.
- Accepted cost: migration revision and broader staging verification.
- Revisit trigger: complete actor/action and bypass-path evidence against the deployed-equivalent schema.

| Dimension | Option A | Option B |
| --- | --- | --- |
| User value | Faster launch | Safer tenant isolation |
| Security/privacy | Write and privileged bypass risks | Explicit enforcement |
| Maintenance | Hidden policy debt | More reviewed policy/test upkeep |
| Accessibility | Existing passes preserved | Existing passes preserved |
| Cost | Lower immediate cost | Additional review/testing |
| Portability | Supabase/Postgres-coupled | Supabase/Postgres-coupled |
| Reversibility | Cross-tenant writes may be irreversible | Migration can use planned recovery |

### Slices

No implementation occurred.

| UI state | Evidence state |
| --- | --- |
| Loading | unresolved |
| Empty | unresolved |
| Error and recovery | tested — pass |
| Duplicate or stale action | unresolved |
| Timeout and retry | unresolved |
| Keyboard and focus restoration | tested — keyboard pass; focus restoration unresolved |
| 320 CSS-pixel reflow | tested — pass |
| Long and translated content | unresolved |
| Performance at exact activation boundary | unresolved — boundary not defined |

Build evidence is also preserved as a pass.

### Trust

- Missing INSERT `WITH CHECK` leaves new-row ownership/tenant constraints unproved.
- An unfixed `SECURITY DEFINER` `search_path` creates an A05 Injection/A08 Integrity risk through object resolution and is a privileged RLS-bypass path.
- The service-role endpoint bypasses RLS. Caller-controlled `tenant_id` needs an authorization decision derived from the authenticated principal before privileged access.
- Same-agent code and tests are insufficient for generated authorization logic.
- Anonymous, A→B, B→A, write, list/count, Storage, Realtime, function/RPC, protected-field, and service-path tests are missing.
- Cloud role, grants, deployed parity, and applicable ASVS 5.0.0 IDs remain unresolved.

### Release

Artifact: Supabase candidate, exact commit unknown | Scope: UI, RLS migration, definer function, and service-role endpoint | Environment: public multi-tenant release, project unknown | Policy: VibeWorthy supplied version | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated pass | UI build | pass | Tool and date recorded | None observed in tested scope | recorded tester | none |
| manual check | Keyboard | pass | Tool and date recorded | Focus restoration remains unresolved | recorded tester | Test focus restoration separately |
| manual check | 320-pixel reflow | pass | Tool and date recorded | Long/translated content unresolved | recorded tester | Test content extremes |
| manual check | Error recovery | pass | Tool and date recorded | Timeout/retry unresolved | recorded tester | Test bounded timeout and retry |
| automated failure | INSERT authorization | fail | Policy has no `WITH CHECK` | Caller may assign unauthorized ownership/tenant fields | unknown — assign owner | Add explicit check and negative tests |
| automated failure | Definer-function safety | fail | No fixed `search_path` | Privileged object-resolution attack | unknown — assign owner | Fix search path, qualify objects, review privileges |
| automated failure | Service-role endpoint | fail | Caller supplies `tenant_id` before privileged access | Cross-tenant RLS bypass | unknown — assign owner | Derive/authorize tenant from authenticated context |
| manual check | Independent authorization oracle | unresolved | Migration and tests generated by same agent; no human named | False confidence in critical logic | unknown — assign owner | Name reviewer and run independent boundary tests |
| manual check | Cloud roles and deployed parity | unresolved | Not performed | Repository policies may not match production | unknown — assign owner | Verify roles, grants, schema, RLS, functions, and secrets |
| manual check | Authorization matrix | unresolved | Only A → own read covered | Cross-user and privileged paths unproved | unknown — assign owner | Exercise full anonymous/A/B/admin matrix |

Recommendation: **NO-GO**. Preserve the valid UI evidence, but it cannot offset authorization and privileged-bypass blockers. This decision does not establish complete security, compliance, or future production behavior.

### Actions

External actions performed: none.