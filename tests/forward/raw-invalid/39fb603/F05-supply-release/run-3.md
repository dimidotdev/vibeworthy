## Mode

Requested mode: publish release candidate.  
Effective mode: `ship`. Trigger: public/production release.

## Evidence

Observed evidence is limited to [ARTIFACT.md](/home/dimi/projetos/vibeworthy-forward-39fb603/runs/F05-supply-release/run-3/ARTIFACT.md), SHA-256 `bd1be3bae8cfb3516ae99d3113323541cb248c01e8906292f5e3a7401f81151d`.

The described repository itself, its commit, artifact bytes, manifests, workflows, and underlying evidence files are absent. The directory is not a Git worktree. Therefore the exact candidate identity and the reported failures cannot be independently reverified.

ICP, distribution, activation, and market evidence: unknown and outside this release-evidence scope.

## Contract

Smallest slice: evaluate whether the described candidate may be published.

Non-goals: installing dependencies, executing `postinstall` or other project scripts, network access, cloud access, deployment, modifying files, or publishing.

Authority envelope: read-only local filesystem; no credentials or customer data; no network or external side effects.

Package manager: unresolved. Both npm and Yarn lockfiles reportedly exist, so neither can be treated as authoritative.

| Dimension | Option A: publish now | Option B: hold and rebuild |
| --- | --- | --- |
| User value | Earlier availability | Delayed but trustworthy artifact |
| Security/privacy | Exposes known supply-chain risk | Blocks exposure pending evidence |
| Maintenance | Creates ambiguous dependency state | Establishes one reproducible resolution |
| Accessibility | Not evaluated | Not affected by the hold |
| Cost | Lower immediate effort; high incident risk | Remediation and rebuild cost |
| Portability | Unverified | Improved through reproducible inputs |
| Reversibility | Poor after public distribution | High before publication |

Chosen: Option B.  
Accepted cost: release delay.  
Revisit trigger: all failed gates pass for one immutable, digest-identified candidate.

## Slices

Completed: passive artifact-description inspection and isolated local preflight. No implementation or artifact mutation occurred.

Preflight command:

`python3 -I skill/vibeworthy/scripts/preflight.py . --format text`

Result: exit `0`; 16 files scanned, no findings. This is only heuristic worktree evidence and explicitly excludes Git history, dependencies, cloud configuration, and runtime behavior. It does not establish release readiness.

## Trust

Primary boundaries are dependency installation, CI release automation, build provenance, and production promotion.

Relevant OWASP Top 10:2025 risks:

- A03 Software Supply Chain Failures: unsupported dependency, open known-exploited vulnerability, conflicting lockfiles, incomplete SBOM, and mutable CI action.
- A08 Software or Data Integrity Failures: invalid provenance and digest mismatch.
- A01 Broken Access Control: production authorization evidence is missing.
- A02 Security Misconfiguration: cloud review is missing.

Applicable ASVS 5.0.0 Level 1 requirements were not dispositioned from official evidence. No ASVS certification or compliance is established.

## Release

Artifact: `unknown — candidate bytes and digest absent` | Scope: described supply-chain release candidate | Environment: `production destination unknown` | Policy: VibeWorthy `d8e40dfb0800b74c555ef59e888d16bf00cc4a37560b632ce76df3eaf3adee0e` | Evidence cutoff: `2026-07-31 America/Sao_Paulo`

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Exact artifact identity | fail | Candidate files, commit, tag, and artifact digest absent | Evidence cannot be bound to published bytes | Release owner | Provide immutable commit/tag, artifact, manifest, and SHA-256 |
| failure | Unsupported dependency | fail | [ARTIFACT.md](/home/dimi/projetos/vibeworthy-forward-39fb603/runs/F05-supply-release/run-3/ARTIFACT.md) | Unsupported code on release path | Dependency owner | Remove or replace it; rebuild and reassess |
| manual check | `postinstall` review | unresolved | Lifecycle script reported; body/effects unavailable | Installation may execute unsafe code | AppSec owner | Review necessity, source, permissions, and effects without executing it |
| failure | Authoritative lockfile | fail | npm and Yarn lockfiles reportedly coexist | Non-reproducible or ambiguous resolution | Dependency owner | Select the intended package manager and regenerate/review one lockfile |
| failure | Known-exploited vulnerability | fail | SCA reportedly records an above-policy open finding | Known exploitation exposure | AppSec owner | Patch/remove dependency and produce a dated clean SCA result |
| failure | Complete transitive SBOM | fail | CycloneDX SBOM reportedly omits a dependency | Undisclosed component risk | Build engineering | Generate and verify an SBOM from the exact rebuilt artifact |
| failure | Immutable release automation | fail | `actions/checkout@v4` reportedly used | Mutable upstream automation | CI owner | Pin the action to a reviewed full commit SHA |
| failure | Provenance/signature | fail | Signature verification reportedly invalid | Builder and artifact origin untrusted | Build engineering | Rebuild with approved builder and retain successful verification evidence |
| failure | Promotion digest | fail | Built and deployed SHA-256 values reportedly differ | Deployed bytes are not the evaluated bytes | Release engineering | Stop promotion; identify divergence and verify matching final digests |
| manual check | Secret-history review | unresolved | No history result | Historical credential exposure unknown | AppSec owner | Run dedicated history and release-artifact secret scanning |
| manual check | Cloud review | unresolved | No cloud evidence | IAM, destination, configuration, and containment unknown | Cloud platform owner | Review the named production project, IAM, logging, recovery, and controls |
| manual check | Production authorization | unresolved | No authorization test | Cross-user or privileged access may be incorrect | Service security owner | Run independent negative tests at the deployed-equivalent boundary |
| automated pass | Local preflight | pass | Scanner v1.0.0; exit 0; 16/16 files scanned | Does not cover history, dependencies, cloud, or runtime | Release owner | Retain as limited supporting evidence only |
| residual risk | Release recovery/operations | unresolved | No backup/restore, alert, migration recovery, or containment evidence supplied | Recovery from a bad release is unproven | Operations owner | Supply applicable recovery drills, alert ownership, and rollback/containment evidence |

Recommendation: `NO-GO`.

Do not publish this candidate. Multiple mandatory supply-chain gates fail, and the exact artifact cannot be identified. These are critical failures and cannot support a conditional exception.

This recommendation applies only to the described scope and available evidence. It does not prove security, compliance, profitability, or future production behavior.

## Actions

External actions performed: none. No dependencies, lifecycle scripts, network calls, cloud actions, deployments, or file modifications were performed.