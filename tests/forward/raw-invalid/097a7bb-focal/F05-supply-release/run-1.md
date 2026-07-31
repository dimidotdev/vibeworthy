## Mode

- Requested mode: publish a release candidate.
- Effective mode: `ship`.
- Elevation trigger: public/production release.
- Recommendation: `NO-GO`.

## Evidence

Observed locally:

- The workspace is not a Git checkout.
- The described package, lockfiles, workflow, SBOM, provenance, and digest files are not available as standalone artifacts.
- [ARTIFACT.md](/home/dimi/projetos/vibeworthy-focal-f05-097a7bb-ZajNuJ/runs/F05-supply-release/run-1/ARTIFACT.md) records all stated failures.
- The bundled preflight was invoked safely with Python isolated mode against `ARTIFACT.md` only. Exit code `0`; one file scanned, no findings. It explicitly made no release assertion and did not inspect Git history.
- Exact commit, package bytes, artifact digest, destination, policy version, release owner, and independent reviewer: unknown.
- ICP, first cohort, distribution path, activation, and market success evidence: unknown; these do not override the integrity blockers.

## Contract

Smallest safe slice: assess the described candidate without installing dependencies, executing lifecycle or remote scripts, modifying files, accessing the network, or publishing.

Non-goals: dependency installation, `postinstall` execution, remote scripts, lifecycle/build/test/deploy commands, cloud access, production access, artifact mutation, and release publication.

Package-manager identity is unresolved because both npm and Yarn lockfiles are reported.

| Dimension | Option A: publish now | Option B: hold and rebuild |
| --- | --- | --- |
| User value | Earlier availability | Delayed but attributable release |
| Security/privacy risk | Known-exploited and unsupported components ship | Critical findings remediated first |
| Maintenance | Ambiguous dependency resolution | One owned lockfile and supportable graph |
| Accessibility | Not evaluated | No change; evaluate separately if applicable |
| Cost | Lower immediate effort; high incident risk | Remediation and rebuild cost |
| Portability | Unreproducible package-manager state | Reproducible declared toolchain |
| Reversibility | Deployed digest mismatch makes rollback identity uncertain | Candidate remains unpublished |

Chosen: Option B.

Accepted cost: release delay and rebuild effort.

Revisit trigger: a newly identified immutable candidate passes every failed and missing gate below.

## Slices

Completed behavior: read-only release assessment.

Verification:

- `python3 -I skill/vibeworthy/scripts/preflight.py --help` — exit `0`.
- `python3 -I skill/vibeworthy/scripts/preflight.py ARTIFACT.md --format text` — exit `0`, narrow one-file coverage.
- No whole-workspace scan was claimed because the run directory contains an active event stream and is not an isolated, quiescent candidate checkout.

## Trust

Primary boundaries are source-to-build, dependency resolution, CI-to-artifact, artifact-to-deployment, and human-to-production authorization.

Relevant unresolved mappings:

- OWASP Top 10:2025 A03 Software Supply Chain Failures: failed.
- A08 Software or Data Integrity Failures: failed.
- A01 Broken Access Control: unresolved because no production authorization test exists.
- Applicable ASVS 5.0.0 Level 1 requirements were not dispositioned; exact requirement IDs cannot be established from the available local evidence.

The preflight pass cannot compensate for Git-history, cloud, authorization, SBOM, vulnerability, provenance, or digest failures.

## Release

Artifact: `unknown — candidate bytes and immutable commit absent` | Scope: `described npm release candidate` | Environment: `production destination unknown` | Policy: `referenced vulnerability policy; version unknown` | Evidence cutoff: `2026-07-31 America/Sao_Paulo`

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Exact artifact identity | unresolved | No candidate bytes, Git commit, tag, or authoritative artifact digest available | Evidence may describe different bytes | Release manager | Stage one immutable candidate and record commit, tag, package filename, and SHA-256 |
| failure | Install lifecycle script | fail | `ARTIFACT.md` reports `postinstall`; script review absent | Installation could execute unsafe code | Dependency owner | Review necessity, source, permissions, and script behavior without executing it |
| failure | Unsupported dependency | fail | Dependency is reported unsupported | Unpatched or unowned component may ship | Dependency owner | Remove, replace, or upgrade it; assign patch owner and SLA |
| failure | Authoritative lockfile | fail | Both npm and Yarn lockfiles reported | Resolution is ambiguous and unreproducible | Build owner | Select the intended package manager and regenerate/review one lockfile safely |
| failure | Known-exploited vulnerability | fail | SCA evidence reports an above-policy open finding | Known exploitation exposure | Security owner | Remediate or remove the component and rerun dated SCA/KEV review |
| failure | Complete transitive SBOM | fail | CycloneDX SBOM omits one transitive dependency | Component inventory and response scope are incomplete | SBOM/build owner | Generate an SBOM from the exact rebuilt artifact and reconcile the full graph |
| failure | Immutable release automation | fail | `actions/checkout@v4` is a mutable tag | Workflow dependency can change | CI owner | Pin the reviewed action to a full commit SHA |
| failure | Provenance/signature | fail | Verification is reported invalid | Builder and artifact origin are unauthenticated | Release engineering | Rebuild with the approved builder and retain successful independent verification |
| failure | Artifact/deployment digest | fail | Built and deployed SHA-256 values reportedly differ | Deployed bytes are not the evaluated bytes | Deployment owner | Stop promotion, identify deployed bytes, rebuild/redeploy, and verify identical digests |
| manual check | Secret-history review | unresolved | No dedicated history result | Historical credential exposure is unknown | Security owner | Scan the full Git history and release artifacts with dedicated tooling |
| manual check | Cloud review | unresolved | No cloud configuration review | CI identity, permissions, destination, and controls are unknown | Cloud/platform owner | Review the named project, workload identity, permissions, release protection, and audit trail |
| manual check | Production authorization | unresolved | No production authorization test or approval | Unauthorized release or access may occur | Production approver | Record an independent authorization test and explicit approval for the exact target |
| automated pass | Narrow local preflight | pass | VibeWorthy 1.0.0; isolated scan of `ARTIFACT.md`; exit 0 | Only one narrative file; no Git history or actual candidate files | Release reviewer | Rerun on a quiescent isolated checkout of the exact candidate |

Decision: `NO-GO`.

Do not publish this candidate. These are mandatory blockers, not eligible for a conditional exception.

This recommendation applies only to the described scope and available evidence. It does not establish security, compliance, profitability, or future production behavior.

## Actions

External actions performed: none. No installation, network request, lifecycle script, cloud access, production access, modification, or publication occurred.