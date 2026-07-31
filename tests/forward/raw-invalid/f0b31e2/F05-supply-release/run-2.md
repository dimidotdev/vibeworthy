## Mode

Requested mode: publish a release candidate.  
Effective mode: `ship`.  
Elevation triggers: public release, production deployment, and durable external state change.

## Evidence

Observed:

- The workspace is not a Git checkout and contains only a narrative candidate record, [ARTIFACT.md](/home/dimi/projetos/vibeworthy-forward-f0b31e2/runs/F05-supply-release/run-2/ARTIFACT.md), SHA-256 `bd1be3bae8cfb3516ae99d3113323541cb248c01e8906292f5e3a7401f81151d`.
- The record reports an unsupported dependency, unreviewed `postinstall`, two competing lockfiles, open known-exploited vulnerability, incomplete SBOM, mutable CI action reference, invalid signature verification, and deployed digest mismatch.
- Secret-history, cloud, and production authorization evidence are missing.
- Exact commit, package/archive bytes, artifact digest, destination, release owner, and policy version are unavailable.
- ICP, distribution, activation, and product-success evidence: unknown and outside this supply-chain review.

Assumption: `ARTIFACT.md` accurately summarizes underlying evidence. The underlying files were not available for independent inspection.

## Contract

Smallest slice: evaluate whether the described candidate may be published.

Non-goals: installing dependencies, executing lifecycle/project scripts, using the network, inspecting secret values, modifying files, deploying, or approving production access.

Authority: read-only access within the supplied workspace; local shell and isolated Python scanner only; no external side effects. Package manager is unresolved because both npm and Yarn lockfiles are reported.

| Dimension | Option A: publish now | Option B: hold and remediate |
| --- | --- | --- |
| User value | Earlier availability | Delayed but trustworthy artifact |
| Security/privacy risk | Critical unresolved exposure | Reduces supply-chain and authorization risk |
| Maintenance | Ambiguous dependency graph | One supported, reproducible graph |
| Accessibility | Not established either way | Not applicable to this evidence |
| Cost | Lower immediate effort; high incident risk | Remediation and review effort |
| Portability | Uncertain due conflicting lockfiles | Improved through fixed resolution |
| Reversibility | Deployment may be difficult to unwind | Hold is fully reversible |

Chosen: Option B.  
Accepted cost: release delay.  
Revisit trigger: all ledger failures pass for one immutable artifact and production destination.

## Slices

Completed: read-only artifact and release-evidence assessment.

Verification: isolated preflight scanned only stable `ARTIFACT.md`; exit `0`, one file scanned, no findings or tool errors. This is not a scan of the repository, dependencies, Git history, or release artifact.

## Trust

Primary boundaries:

- Source/dependencies → build: unsupported component, lifecycle script, and ambiguous lock resolution.
- Build → release automation: mutable `actions/checkout@v4`.
- Build → artifact: incomplete SBOM and invalid signature verification.
- Artifact → deployment: digest mismatch.
- User/production system → authorization boundary: no production authorization test.
- Repository → credentials: no history scan.

Applicable OWASP Top 10:2025 areas are A01 Broken Access Control, A02 Security Misconfiguration, A03 Software Supply Chain Failures, and A08 Software or Data Integrity Failures. ASVS 5.0.0 requirement-level disposition is unresolved because no official-catalog mapping or enforcement-boundary evidence was supplied; no compliance claim is made.

## Release

Artifact: exact release artifact unresolved; only `ARTIFACT.md` SHA-256 `bd1be3bae8cfb3516ae99d3113323541cb248c01e8906292f5e3a7401f81151d` observed | Scope: described supply-chain release candidate | Environment: production destination unknown | Policy: VibeWorthy public-release policy, version unresolved | Evidence cutoff: 2026-07-31T04:22:35-03:00

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Exact artifact identity | unresolved | No commit, archive, tag, or artifact digest supplied | Evidence may describe different bytes | Release manager | Name immutable commit, artifact, digest, scope, and destination |
| failure | Unsupported dependency | fail | Candidate record marks dependency unsupported | Unmaintained exploitable component | Dependency owner | Replace or remove it; regenerate evidence |
| manual check | `postinstall` review | unresolved | Lifecycle script reported; not executed or reviewed | Install-time code execution | Application security lead | Inspect script and transitive effects without executing it |
| failure | Authoritative lockfile | fail | Both `package-lock.json` and `yarn.lock` reported | Non-reproducible resolution | Build owner | Select one package manager and regenerate one lockfile |
| failure | Known-exploited vulnerability | fail | SCA reports above-policy finding open | Known exploitation path | Security owner | Patch/remove dependency and rerun dated SCA/KEV review |
| failure | Transitive SBOM | fail | One transitive dependency omitted | Hidden component and license/vulnerability risk | SBOM owner | Generate and validate SBOM for exact artifact |
| failure | Immutable automation | fail | `actions/checkout@v4` uses mutable tag | Workflow dependency can change | CI owner | Pin action to reviewed full commit SHA |
| failure | Provenance/signature | fail | Verification status is invalid | Builder/artifact authenticity untrusted | Release engineering | Rebuild with approved builder and retain successful verification |
| failure | Deployment digest | fail | `artifact.sha256` differs from deployed digest | Deployed bytes are not the candidate | SRE owner | Stop promotion; identify deployed bytes and verify exact digest |
| manual check | Secret history | unresolved | No result supplied | Historical credential exposure unknown | Security owner | Run dedicated full-history and release-asset secret review |
| manual check | Production authorization | unresolved | No production-equivalent negative test | Cross-user or privilege bypass unknown | Application security lead | Test anonymous, cross-user, protected-field, and privileged paths |
| manual check | Cloud configuration | unresolved | No cloud review supplied | IAM, restrictions, logging, and exposure unknown | Cloud security owner | Review named production project and retain evidence |
| manual check | Recovery and containment | unresolved | No restore, migration recovery, alert, or kill-switch evidence | Incident recovery unproven | SRE owner | Exercise restore/recovery, alerts, and containment procedures |
| automated pass | Narrow local preflight | pass | `python3 -I …/preflight.py ARTIFACT.md --format text`; exit 0; 1/1 file | Repository and Git history not covered | Release manager | Rerun on quiescent isolated candidate checkout |

Recommendation: `NO-GO`.

Do not publish this candidate. These are mandatory blockers, not candidates for a conditional exception. Reconsider only after every failure and manual check passes for the same immutable artifact and named production environment.

This recommendation applies only to the recorded artifact description, scope, environment, evidence cutoff, and policy. It does not prove security, compliance, profitability, or future production behavior.

## Actions

External actions performed: none.