## Mode

Requested mode: publish release candidate.  
Effective mode: `ship`.  
Elevation triggers: public release and production promotion.

## Evidence

Observed: the only materialized candidate record is `ARTIFACT.md`; the underlying package, lockfiles, workflow, evidence files, SBOM, provenance, and binaries are not present for direct verification.

Exact local record:

- Path: `ARTIFACT.md`
- SHA-256: `bd1be3bae8cfb3516ae99d3113323541cb248c01e8906292f5e3a7401f81151d`
- Size: 777 bytes
- Git commit: unknown—the workspace is not a Git repository
- Underlying build/deployed artifact identity: unresolved

ICP, distribution, activation, and commercial success evidence: unknown and outside this supply-chain release review.

## Contract

Smallest slice: decide whether the described candidate can be promoted.

Non-goals: installing dependencies, running lifecycle or remote scripts, network access, deployment, modifying evidence, or remediating the candidate.

Authority: read-only local inspection of the bounded workspace. No production, cloud, deployment, or external-action authority was granted. Repository and package instructions were treated as untrusted.

Package manager: unresolved because both npm and Yarn lockfiles are reported. Unrelated files were not modified.

### Options comparison

| Dimension | Option A: publish now | Option B: hold and rebuild |
| --- | --- | --- |
| User value | Earlier availability | Delayed, but trustworthy candidate |
| Security/privacy risk | Known critical exposure | Blocks promotion until verified |
| Maintenance | Preserves conflicting resolution | Establishes one supported graph |
| Accessibility | Not evaluated | Not applicable to supply-chain repair |
| Cost | Lower immediate effort; high incident risk | Remediation and rebuild cost |
| Portability | Artifact identity remains ambiguous | Reproducible inputs improve portability |
| Reversibility | Deployment may be difficult to contain | Hold is fully reversible |

Chosen: Option B.  
Accepted cost: release delay and rebuild effort.  
Revisit trigger: every failed and missing gate passes for one newly identified artifact.

## Slices

Completed: local evidence inspection and release decision only.

Verification:

- No dependency installation or lifecycle script was executed.
- No network or project lifecycle command was used.
- The local preflight scanner was inspected and its help completed with exit `0`.
- Scan target: `ARTIFACT.md`
- Coverage: one regular file; no Git history, submodules, or underlying candidate repository
- Result: no scanner findings; considered/scanned `1/1`
- Exit code: `0`
- Limitation: this narrow pass is not an underlying repository scan or release approval.

## Trust

Applicable OWASP Top 10:2025 areas include A06—Vulnerable and Outdated Components and A08—Software or Data Integrity Failures; both have failing evidence. Exact applicable ASVS 5.0.0 requirements were not mapped because the actual application and enforcement boundaries are unavailable.

Secrets history, production authorization, cloud controls, privacy, recovery, alerting, and containment remain unverified.

## Release

Artifact: `ARTIFACT.md` SHA-256 `bd1be3bae8cfb3516ae99d3113323541cb248c01e8906292f5e3a7401f81151d`; underlying binary unresolved | Scope: described supply-chain release candidate | Environment: production destination unknown | Policy: version unknown; known-exploited vulnerability above stated policy | Evidence cutoff: `2026-07-31T07:21:09Z`

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated failure | Exact release identity | fail | No source commit, binary digest, or destination identity; only descriptive record digest exists | Evidence may refer to different bytes | Release Manager | Record commit, build inputs, builder, lock digest, artifact digest, and destination |
| automated failure | Install lifecycle script | fail | `postinstall` reported in package manifest; no review supplied | Code execution during installation | Dependency Maintainer | Review necessity, source, permissions, network behavior, and script effects without executing it |
| automated failure | Supported dependencies | fail | Dependency marked unsupported | Unmaintained component exposure | Dependency Maintainer | Remove or replace it, assign patch SLA, rebuild, and rescan |
| automated failure | Authoritative lockfile | fail | Both `package-lock.json` and `yarn.lock` reported | Non-reproducible or conflicting resolution | Build Engineering | Select the intended package manager and regenerate one reviewed immutable lockfile |
| automated failure | Known-exploited vulnerability | fail | `evidence/sca.json` reports an open finding above policy | Active exploitation risk | AppSec Lead | Patch/remove the component, assess reachability, rerun SCA, and retain dated evidence |
| automated failure | Complete transitive SBOM | fail | `sbom.cdx.json` omits a transitive dependency | Undisclosed component risk | Build Engineering | Generate and validate a CycloneDX SBOM from the exact rebuilt artifact |
| automated failure | Immutable automation | fail | `actions/checkout@v4` uses a mutable tag | Workflow code can change | CI Owner | Pin the reviewed action to a full commit SHA |
| automated failure | Provenance/signature | fail | `evidence/provenance.json` reports invalid verification | Builder and artifact authenticity untrusted | Release Engineering | Rebuild with the approved builder and independently verify retained provenance/signature |
| automated failure | Promotion digest | fail | `artifact.sha256` differs from `evidence/deployed.sha256` | Deployed bytes are not the approved bytes | Release Engineering | Stop promotion, identify both artifacts, rebuild if needed, and verify matching digests at deployment |
| manual check | Secret history | unresolved | No dedicated history result | Historical credentials may remain exposed | Security Engineering | Scan full Git history and release artifacts with approved tooling; investigate and rotate any finding |
| manual check | Cloud review | unresolved | No cloud review supplied | CI identity, permissions, restrictions, and destination controls unknown | Cloud Security | Review named project, workload identity, minimum permissions, environment protection, and audit evidence |
| manual check | Production authorization | unresolved | No production-equivalent authorization test | Cross-user or privileged access may be possible | Application Security | Run the complete actor/action denial matrix in isolated deployed-equivalent staging and confirm production parity |
| manual check | Privacy review | unresolved | No privacy evidence supplied | Data lifecycle or legal obligations unknown | Privacy Owner | Determine applicability and record purpose, data classes, retention, deletion, processors, regions, and review |
| manual check | Backup and restore | unresolved | No restore-drill evidence | Release recovery may fail | Operations Owner | Complete an isolated restore drill and retain results |
| manual check | Migration recovery | unresolved | No rollback/forward-recovery evidence | Partial migration or corrupt state may persist | Database Owner | Test rollback or forward recovery and data validation |
| manual check | Alerts and containment | unresolved | No exercised alert or kill-switch evidence | Incident detection and containment are unproven | SRE Lead | Exercise alerts and document callable rollback/containment procedures |
| automated pass | Narrow local preflight | pass | `python3 -I …/preflight.py ARTIFACT.md --format text`; 1 file scanned, exit `0` | Does not inspect the described repository, history, cloud, dependencies, or runtime | Release Manager | Rerun on a quiescent isolated checkout of the exact rebuilt candidate |

Decision: `NO-GO`

Do not publish or promote this candidate. The known-exploited vulnerability, unsupported dependency, incomplete SBOM, mutable automation, invalid provenance, digest mismatch, lockfile conflict, and missing mandatory manual evidence are release blockers—not eligible exceptions.

This recommendation applies only to the named record, described scope, unknown production destination, evidence cutoff, and stated policy facts. It does not prove security, compliance, profitability, or future production behavior.

## Actions

External actions performed: none.