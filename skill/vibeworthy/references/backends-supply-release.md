# Backends, dependencies, payments, and release

Load only the relevant section. Keep the user-facing result to blockers, completed checks, and the
next safest action.

## Firebase

- Treat Firebase client configuration and its client API key as public identifiers, not authorization.
  Verify API/application restrictions in the intended cloud project.
- Never place a service-account key, Admin credential, private key, or privileged token in source,
  browser code, prompts, fixtures, or reports.
- Deny by default in Firestore, Realtime Database, and Storage Rules. Validate ownership, allowed
  fields, types, sizes, immutable fields, list/query behavior, and paths.
- Test anonymous, user A on own data, user A on user B's data, and the intended admin/service path in an
  emulator or isolated staging project with synthetic records.
- Review every Admin SDK or IAM bypass path independently; Rules do not constrain privileged server
  credentials.
- Before release, confirm that the reviewed Rules and IAM are deployed to the named production project.

## Supabase

- Treat publishable and legacy `anon` keys as public. They are acceptable in a client only when the
  intended role is protected by effective RLS and related policies.
- Never place `service_role`, secret keys, database passwords, or privileged tokens in a public
  client or repository.
- Enable RLS on every exposed table. Review grants, `USING`, `WITH CHECK`, views, functions, RPC,
  `SECURITY DEFINER`, Storage, and Realtime.
- Prevent callers from changing owner, tenant, role, price, or protected status.
- Test anonymous, user A on own rows, user A on user B's rows, list/count leakage, and each privileged
  server path in isolated staging.
- Before release, confirm the reviewed schema, grants, policies, functions, and secrets are deployed to
  the named production project.

## Payments and webhooks

- Prefer a maintained hosted checkout when it meets the product need; avoid collecting card data
  directly.
- Send a stable plan identifier from the client. Resolve amount, currency, interval, customer, tenant,
  and redirect destination from server-owned allowlists.
- Verify webhook authenticity over the exact received payload, freshness, expected account and event,
  replay resistance, and atomic idempotency.
- Test forged, stale, duplicate, reordered, malformed, and wrong-account callbacks.
- Bound retries and record reconciliation, redacted logs, alert ownership, and recovery from partial
  processing.

## Dependencies and automation

Before adding a dependency:

1. State why existing code or platform capability is insufficient.
2. Verify the exact package, publisher, source, license, maintenance, and typo risk.
3. Inspect install/build scripts, native binaries, permissions, and network behavior before execution.
4. Preserve the project's package manager and one authoritative lockfile.
5. Review direct and transitive vulnerabilities using the project's existing tooling.

Do not execute remotely fetched content through a shell pipeline. Pin third-party CI actions and
containers to immutable revisions when feasible. Give CI jobs minimum permissions and keep release
credentials short-lived and environment-scoped.

## Migrations and destructive changes

- Take an appropriate backup and prove it can be restored before relying on it.
- Prefer compatible expand/migrate/contract sequencing.
- Validate partial execution, retry, concurrency, rollback or forward recovery, and old/new version
  compatibility.
- Stop before production if recovery is only theoretical.

## Efficient release checkpoint

Run one checkpoint after the candidate is stable. Do not repeat unchanged evidence.

Check:

- no tracked or unignored sensitive `.env` file and no privileged value in source or client output;
- focused authorization denial at the real boundary;
- dependency/lockfile review when dependencies changed;
- native tests and build relevant to the change;
- production configuration that cannot be inferred from source;
- backup/recovery for destructive state changes;
- monitoring, rate limits, and rollback proportionate to impact.

Report:

- **Blockers:** only issues that should stop release.
- **Checked:** exact checks completed for this candidate.
- **Not checked:** meaningful cloud, runtime, privacy, or operational unknowns.
- **Next:** the smallest action that resolves the highest risk.

Do not require a large evidence ledger for routine work. Use a detailed audit only when the user asks
for one, regulation or organizational policy requires it, or a critical decision needs traceability.
A local scanner pass never overrides an authorization failure, exposed secret, unsafe migration,
payment flaw, required privacy/legal decision, or known exploitable dependency.
