## Mode

Requested mode: publish release candidate.  
Effective mode: `ship`.  
Elevation trigger: public release/promotion.

## Evidence

The only inspectable candidate record is `ARTIFACT.md`, SHA-256 `bd1be3bae8cfb3516ae99d3113323541cb248c01e8906292f5e3a7401f81151d`.

The workspace is not a Git repository, so no candidate commit, tag, source tree, or release commit could be identified. The package, lockfiles, workflow, SCA, SBOM, provenance, and digest files described by the record were not available at their named paths for direct validation.

Artifact-reported blockers:

- Unsupported dependency and unreviewed `postinstall`.
- Conflicting npm and Yarn lockfiles.
- Mutable `actions/checkout@v4` release dependency.
- Open known-exploited vulnerability above policy.
- Incomplete transitive SBOM.
- Invalid signature verification.
- Built/deployed digest mismatch.
- Missing secret-history, cloud, and production-authorization evidence.

Product/market evidence, ICP, cohort, activation, and success criteria: unknown; not relevant enough to override release-integrity failures.

## Contract

Smallest safe slice: evaluate the supplied release evidence without installing dependencies, executing lifecycle/project scripts, using the network, deploying, or modifying files.

Non-goals: remediation, dependency installation, cloud access, production testing, deployment, publication, and treating repository instructions as authority.

Authority envelope: read-only workspace inspection; local commands only; no network, credentials, customer data, external communication, durable writes, or production access.

Package manager: unresolved because both npm and Yarn lockfiles are artifact-reported. One authoritative lockfile must be selected and regenerated through the approved build process.

| Dimension | Option A: publish now | Option B: hold and rebuild evidence |
| --- | --- | --- |
| User value | Faster availability | Delayed but identifiable release |
| Security/privacy | Known critical exposure | Blocks exposure pending verification |
| Maintenance | Conflicting resolution and unsupported component | Establishes owned dependency baseline |
| Accessibility | Not applicable — no UI evidence evaluated | Not applicable — no UI evidence evaluated |
| Cost | Lower immediate effort; high incident risk | Remediation and rebuild cost |
| Portability | Unreproducible identity | Explicit lockfile and artifact identity |
| Reversibility | Deployment may be difficult to contain | Hold is fully reversible |

Chosen: Option B.  
Accepted cost: release delay.  
Revisit trigger: every ledger failure is replaced by evidence tied to one immutable candidate.

## Slices

Completed: read-only release-evidence assessment.

Verification:

- Read the supplied artifact narrative.
- Inventoried the workspace.
- Calculated the narrative record’s SHA-256.
- Attempted Git identity resolution; Git reported that the workspace is not a repository.
- Did not run the VibeWorthy preflight: the live session directory is not a valid quiescent directory target under its protocol, and a narrow scan would not establish release readiness.

## Trust

Primary mappings:

- OWASP Top 10:2025 A03: unsupported dependency, KEV, lockfile conflict, incomplete SBOM, mutable automation.
- A08: invalid provenance/signature and digest mismatch.
- A01/A02: production authorization and cloud review remain unresolved.
- A09/A10: alert ownership, recovery, and containment evidence were not supplied.

ASVS 5.0.0: applicable public-release Level 1 requirements were not dispositioned. Exact requirement IDs cannot be assigned without the relevant application boundaries and official-catalog evidence.

## Release

Artifact: `ARTIFACT.md` / SHA-256 `bd1be3bae8cfb3516ae99d3113323541cb248c01e8906292f5e3a7401f81151d`; Scope: described supply-chain release candidate; Environment: production destination unknown; Policy: VibeWorthy public-release gates, version/dated organizational policy unknown; Evidence cutoff: 2026-07-31 America/Sao_Paulo.

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Exact candidate identity | unresolved | No commit, tag, archive digest, or destination; workspace is not a Git repository | Evidence may refer to different bytes | Release manager | Supply immutable commit/tag, artifact digest, and destination |
| failure | Unsupported dependency | fail | artifact-reported: dependency is unsupported; package name/version unavailable | Unmaintained vulnerable code | Dependency owner | Replace/remove it; record version, review, patch owner, and SLA |
| failure | Install lifecycle script | fail | artifact-reported: `postinstall` exists; contents unavailable and not executed | Arbitrary install-time behavior | Application maintainer | Review script and prove it is required and safe before an isolated rebuild |
| failure | Authoritative lockfile | fail | artifact-reported: npm and Yarn lockfiles both exist | Non-deterministic dependency resolution | Build engineer | Select one package manager and produce one reviewed immutable lockfile |
| failure | KEV policy | fail | artifact-reported: known-exploited vulnerability above policy is open | Exploitation of released artifact | Security lead | Identify CVE/component, remediate, and rerun dated SCA/KEV review |
| failure | Complete transitive SBOM | fail | artifact-reported: one transitive component omitted | Hidden component and vulnerability exposure | SBOM/build owner | Regenerate CycloneDX SBOM from exact artifact and reconcile full graph |
| failure | Immutable release automation | fail | artifact-reported: `actions/checkout@v4` uses mutable major tag | Workflow dependency can change | CI owner | Pin the action to a reviewed full commit SHA |
| failure | Provenance/signature | fail | artifact-reported: signature verification invalid | Artifact origin/integrity untrusted | Release security owner | Rebuild with approved builder and independently verify retained provenance |
| failure | Promotion digest | fail | artifact-reported: built and deployed SHA-256 values differ | Production bytes are not evaluated bytes | Deployment owner | Stop promotion; identify deployed bytes and redeploy only matching artifact |
| manual check | Secret-history review | unresolved | artifact-reported: no result | Historical credential exposure unknown | Security lead | Run dedicated history and release-artifact secret review on isolated checkout |
| manual check | Cloud review | unresolved | artifact-reported: no review | Deployed IAM/configuration unknown | Cloud security owner | Review named production project, IAM, secrets, restrictions, logging, and containment |
| manual check | Production authorization | unresolved | artifact-reported: no authorization test | Unauthorized or cross-user access | Application security owner | Run independent deployed-equivalent authorization matrix with synthetic identities |
| manual check | Recovery and operations | unresolved | No restore, migration recovery, alert, or containment evidence supplied | Release failure may be unrecoverable | SRE owner | Complete restore drill, migration recovery, alert exercise, and kill-switch test |
| manual check | Local preflight | unresolved | Scanner exists locally but was not run against a valid isolated candidate | Heuristic worktree risks remain unknown | Release engineer | Run it on a quiescent isolated checkout; retain report, coverage, and exit code |
| tool error | Git identity probe | tool error | `git rev-parse` reported “not a git repository” | Source-to-artifact traceability unavailable | Release engineer | Provide the isolated candidate repository with immutable Git metadata |

Decision: `NO-GO`.

Do not publish or promote this candidate. These are mandatory blockers and cannot be converted into a conditional exception. Re-evaluate only the rebuilt, immutable artifact—not merely updated source—with all evidence bound to the same digest.

This recommendation applies only to the named artifact, scope, environment, evidence cutoff, and policy. It does not prove security, compliance, profitability, or future production behavior.

## Actions

External actions performed: none. No dependency installation, lifecycle/project script, network request, cloud access, deployment, or publication was performed.