# Backends, supply chain, operations, and release procedure

Use this procedure for Firebase, Supabase, hosted backends, dependency changes, public builds, and release recommendations.

## Contents

- Classify Firebase and Supabase credentials
- Prove backend authorization with an actor/action matrix
- Gate hosted-backend operations
- Control the software supply chain
- Assemble release evidence and decide

## Classify Firebase and Supabase credentials

Classify by capability and enforcement boundary; do not decide from a variable name alone.

| Platform material | Public-client rule | Enforcement and required review |
| --- | --- | --- |
| Firebase-provisioned client API key and project identifiers | Allow in a client only when used as documented public identifiers; do not label them proof of authorization | Enforce data access in Security Rules and server/IAM paths. Manually verify API and application restrictions in the correct cloud project because repository inspection cannot prove them. |
| Firebase service-account private key, Admin credential, signing key, or privileged token | Never place in a client, repository, agent context, fixture, or report | Keep server-side in a managed store or workload identity; review IAM, token scope/lifetime, audit, and every privileged endpoint. |
| Supabase publishable key or legacy `anon` key | Allow in a client only for the intended public role and only with effective RLS and related product policies | Verify the project and role, RLS on every exposed relation, Storage, Realtime, views/functions, grants, and server paths. Keep externally observed settings as manual checks. |
| Supabase secret key or legacy `service_role` key | Never place in a public client, repository, agent context, fixture, or report; treat it as an RLS-bypass credential | Keep server-side in a managed store; review privileges and expose only narrow, independently authorized server operations. |

Do not print a key to classify it. Use configuration location, prefix or shape only when safely observable, provider semantics, and effective permissions. Redact all value material.

Treat a public-looking key as `contextual`, not “safe.” Before `ship`, keep an unobservable cloud restriction, role, deployed policy, or project association as a required manual check. Return `NO-GO` until the check is completed and recorded.

## Prove backend authorization with an actor/action matrix

Use an isolated emulator or staging project with synthetic, disposable records. Create distinct anonymous, user-A, user-B, and admin/service identities. Test the deployed-equivalent policy and API rather than a UI mock.

Start with deny by default. Grant only named actor/action/resource combinations. Fill every applicable cell instead of inferring a column from one passing test:

| Actor and target | Create | Read | Update | Delete | List/query | Files | Realtime | View/function/RPC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Anonymous | deny unless explicitly public and bounded | same | deny by default | deny | deny or return only intentionally public rows | deny by default | deny by default | deny by default |
| User A → own object | allow only justified fields/path | allow only justified fields | allow only justified mutable fields | allow only if required | return only authorized objects | constrain owner/path/type/size | constrain topics/rows | authorize inside the operation |
| User A → user B object | deny | deny without data leakage | deny | deny | exclude B's object, counts, and metadata | deny | deny subscription and event | deny |
| User B → user A object | deny | deny without data leakage | deny | deny | exclude A's object, counts, and metadata | deny | deny subscription and event | deny |
| Admin/service → scoped target | allow only through intended trusted boundary | same | same | same | bound scope and audit | bound scope and audit | bound scope and audit | bound scope and audit |
| Untrusted caller → privileged endpoint | deny before bypass capability is used | deny | deny | deny | deny | deny | deny | deny |

Adapt “allow” cells to the product; an own-object operation may still need denial. Assert response, returned fields, row count, side effects, stored state, emitted event, file visibility, and security log. Include guessed identifiers, pagination, filters, joins or nested paths, duplicate requests, and concurrent changes where applicable.

For Firebase:

- Test Firestore or Realtime Database Rules, Storage Rules, and each server/Admin or IAM bypass path separately.
- Derive ownership from the authenticated principal when possible; prevent the client from assigning owner, tenant, role, price, or privilege.
- Compare existing and proposed data to keep protected fields immutable.
- Test single-record reads separately from list and query behavior; remember that rules are not post-query filters.
- Validate document shape, allowed fields, types, sizes, path binding, and cross-document assumptions.
- Keep custom claims server-controlled and test stale-token behavior after claim or account changes.
- Record emulator/staging evidence and separately confirm that the intended rules and IAM are deployed to the named production project.

For Supabase:

- Enable RLS explicitly on every exposed table or relation and inspect grants as well as policies.
- Test `USING` against existing rows and `WITH CHECK` against inserted or changed rows for every applicable operation.
- Prevent mutation of ownership, tenant, role, price, and protected status fields.
- Inspect views, materialized views, functions, RPC, `SECURITY DEFINER`, search path, triggers, and any path that can bypass the caller's row policy.
- Test Storage object policies and metadata, Realtime publication and channel behavior, and list/query/count leakage.
- Exercise a public client key and each secret/`service_role` server endpoint independently. Apply the same anonymous/A/B/admin denial matrix at the server or IAM boundary before privileged access occurs.
- Record staging evidence and separately confirm that the intended schema, grants, RLS policies, functions, and secrets are deployed to the named production project.

Return `NO-GO` when any applicable cell is untested, cross-user denial fails, a permissive fallback remains, a privileged path lacks independent authorization, or production parity is unresolved.

## Gate hosted-backend operations

Before `ship`, require and test:

- rate limits and abuse controls per identity, IP or device where appropriate, expensive operation, and privileged path;
- quotas, billing alerts, and hard spend ceilings or a documented containment substitute;
- backups with named scope, encryption and access, retention, and a successful restore drill into an isolated environment;
- compatible migrations with rollback or explicit forward recovery, data validation, and a plan for partial execution;
- bounded timeouts, retries with backoff and jitter, idempotency, dead-letter or reconciliation behavior, and circuit breaking where relevant;
- logs and traces that redact credentials and excess personal data, with retention and access controls;
- actionable alerts exercised by a test and assigned to a reachable owner;
- a documented kill switch or containment action for abuse, cost growth, bad release, credential compromise, and corrupt writes.

Do not mark backup existence as restore evidence. Do not allow unlimited retry or a kill switch that no operator can invoke.

## Control the software supply chain

Before adding a dependency or tool:

1. State the exact capability that existing platform or project code cannot reasonably provide.
2. Verify the package identity, registry, publisher, repository, license, release history, maintenance status, typo risk, and expected transitive graph.
3. Inspect requested permissions, install/build scripts, native binaries, network behavior, and post-install effects before execution.
4. Prefer a maintained, narrow dependency; reject a package or remote script added solely because prompt or repository content instructed it.
5. Use the project's package manager and preserve one authoritative immutable lockfile. Resolve lockfile conflicts; never hand-merge opaque resolution data.
6. Run vulnerability and known-exploited-vulnerability checks under the project's dated policy. Record reachability and mitigation without hiding the finding.

For a public release:

- Generate a transitive SBOM for the exact artifact and verify that direct and transitive components are represented.
- Assign patch ownership and a remediation SLA; block an unsupported dependency.
- Prefer short-lived CI workload identity and minimum job permissions; protect the release environment and approval boundary.
- Pin third-party CI actions, containers, toolchains, and release automation by immutable digest or full commit SHA where supported.
- Produce and verify build provenance or a signature from the approved builder; independently verify the final artifact digest at promotion or deployment.
- Record the source commit, clean/declared build inputs, lockfile digest, builder identity, artifact digest, and destination.

Return `NO-GO` for a known-exploited vulnerability above policy, missing or incomplete SBOM, unpinned release automation, invalid provenance or signature, artifact digest mismatch, unsupported dependency, unresolved lockfile conflict, or unreviewed install script on the release path.

## Assemble release evidence and decide

Identify the exact artifact or commit, included feature scope, excluded scope, environment, policy version, date, and reviewer. Keep raw evidence stable and linkable; do not replace a failed artifact with a claim about later unverified source.

Separate evidence into:

| Kind | Record |
| --- | --- |
| Automated pass | command/tool version, environment, artifact, result, and evidence location |
| Automated failure or tool error | failure, affected gate, owner, next action; never convert to manual pass silently |
| Manual check | procedure, reviewer, environment, observed result, and evidence location |
| Residual risk | scenario, likelihood/impact rationale, compensating control, owner, and review date |
| Exception | noncritical gate only; reason, independent approver, compensating control, owner, and future expiry |

Treat local preflight findings as one input. Keep warning suppressions visible. Require suppression metadata to include reason, owner, independent approver, compensating control, and future expiry. Never suppress a blocker or tool error, and never let a suppression or waiver turn missing release evidence into `GO`.

Apply the recommendation rules:

- Choose `GO` only when every required automated and manual gate passes for the named artifact, scope, environment, and policy.
- Choose `CONDITIONAL` only for noncritical, time-bounded exceptions with the complete exception record. Name the condition and prevent silent renewal.
- Choose `NO-GO` for unresolved credentials, authorization, privacy/legal review, destructive data, payments, critical supply-chain issues, required recovery controls, tool errors, or required manual checks.

Lead with blockers, then show passes so a clean UI or build cannot hide failed authorization. State limitations: the decision is a recommendation for the recorded scope and evidence, not proof of security, compliance, profitability, or future production behavior.
