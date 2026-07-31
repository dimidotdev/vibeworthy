## Mode

Requested mode: publish a release candidate.  
Effective mode: `ship`.  
Elevation triggers: public publication, deployment/artifact promotion, production authorization, and supply-chain integrity.

## Evidence

Observed workspace evidence:

- [ARTIFACT.md](/home/dimi/projetos/vibeworthy-focal-a87dba5-clean/runs/F05-supply-release/run-3/ARTIFACT.md) reports all listed failures.
- Outside `skill/`, the workspace contains only `ARTIFACT.md` and run metadata. The described manifests, lockfiles, workflow, SCA report, SBOM, provenance, and digest files are not available for direct verification.
- The directory is not a Git repository; no commit, tag, or source-tree identity could be established.
- Python 3.14.4 was observed.
- Narrow preflight: `python3 -I skill/vibeworthy/scripts/preflight.py ARTIFACT.md --format text` scanned one stable file, found no findings or tool errors, and exited `0`. It did not scan the described artifact, Git history, dependencies, or cloud configuration.

Artifact-reported evidence:

- Unsupported dependency and unreviewed `postinstall`.
- Conflicting npm and Yarn lockfiles.
- Mutable `actions/checkout@v4` reference.
- Open known-exploited vulnerability above policy.
- Incomplete transitive SBOM.
- Invalid signature verification.
- Built/deployed digest mismatch.
- No secret-history, cloud review, or production authorization evidence.

ICP, cohort, activation, and product success evidence: unknown and not relevant to resolving these release-integrity blockers.

## Contract

Smallest safe slice: evaluate the supplied release evidence without executing artifact code.

Non-goals: installing dependencies, selecting a lockfile automatically, running lifecycle/build/test scripts, accessing cloud or production, deploying, approving exceptions, or repairing evidence.

Authority envelope: read-only local files under the supplied root; no network, writes, secrets, external communication, or production actions. The active run directory was not scanned as a whole because `events.jsonl` may be written during this session.

Package manager: unresolved. Both npm and Yarn lockfiles are artifact-reported, with no authoritative choice established.

| Dimension | Option A: publish now | Option B: halt promotion |
| --- | --- | --- |
| User value | Earlier availability | Delayed availability |
| Security/privacy risk | Exposes known supply-chain and authorization uncertainty | Contains current risk |
| Maintenance | Starts from unsupported/conflicting dependencies | Requires remediation first |
| Accessibility | Not evaluated | Not applicable to this evidence-only decision |
| Cost | Lower immediate delay; potentially high incident cost | Remediation and retest cost |
| Portability | Artifact identity is not reproducible | Establishes reproducible inputs |
| Reversibility | Deployment may be difficult to contain | Fully reversible before promotion |

Chosen: Option B.  
Accepted cost: release delay.  
Revisit trigger: all failed gates pass for one immutable artifact and production destination.

## Slices

Completed slice: read-only evidence inspection and narrow local preflight.

Verification: one-file preflight passed, but its release assertion explicitly says `none`. No lifecycle or project scripts ran.

## Trust

Relevant mappings:

- OWASP Top 10:2025 A03: dependency, lockfile, SBOM, and automation failures.
- A08: invalid provenance and digest mismatch.
- A01/A02: production authorization and cloud review unresolved.
- A09/A10: alert ownership and recovery evidence unavailable.
- ASVS 5.0.0: applicable public-release Level 1 requirements were not dispositioned; exact requirement IDs cannot be assigned without the official catalog and product boundaries.

The principal assets are release integrity, production availability, and customer trust. Threat actors include a compromised dependency, build system, mutable CI action, and unauthorized production caller. The current evidence does not establish that the evaluated, built, signed, and deployed bytes are identical.

## Release

Artifact: `unknown — no commit, tag, filename, or verified digest` | Scope: `described supply-chain release candidate` | Environment: `production destination unresolved` | Policy: `VibeWorthy public-release gates; version unknown` | Evidence cutoff: `2026-07-31 America/Sao_Paulo`

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Exact artifact identity | unresolved | No candidate bytes, commit, tag, or verified digest available | Evidence may concern different bytes | Release manager | Freeze and record commit, tag, artifact name, lockfile digest, builder, and SHA-256 |
| automated failure | Unsupported dependency | fail | `ARTIFACT.md` reports unsupported component | Unpatched component on release path | Dependency maintainer | Replace or remove it; regenerate and review evidence |
| manual check | `postinstall` behavior | unresolved | Lifecycle script reported; not executed or directly inspected | Install-time code may mutate or execute unsafe behavior | AppSec lead | Review script source and effects without executing it |
| automated failure | Authoritative lockfile | fail | npm and Yarn lockfiles reported | Non-reproducible dependency resolution | Build engineer | Select one package manager, remove conflict, regenerate deterministically |
| automated failure | Known-exploited vulnerability | fail | SCA reports an open finding above policy | Exploitable dependency may ship | AppSec lead | Patch/remove dependency, assign SLA, rerun SCA under dated policy |
| automated failure | Transitive SBOM | fail | CycloneDX SBOM omits a dependency | Incomplete component inventory | Release engineer | Generate SBOM from exact artifact and reconcile the full graph |
| automated failure | Immutable automation | fail | `actions/checkout@v4` reported | Workflow dependency can change | CI owner | Pin checkout and every third-party action to reviewed full commit SHAs |
| automated failure | Provenance/signature | fail | Verification reported invalid | Builder/artifact origin is untrusted | Build-security owner | Rebuild with approved builder and retain successful independent verification |
| automated failure | Promotion digest | fail | Built and deployed SHA-256 values differ | Deployed bytes are not the approved artifact | Production release owner | Stop promotion; identify deployed bytes and redeploy only an independently verified digest |
| manual check | Secret-history review | unresolved | No result supplied | Historical credentials may remain exposed | Security operations | Run dedicated history and release-artifact secret scanning; remediate any exposure |
| manual check | Cloud review | unresolved | No cloud review supplied | IAM, environment protection, and runtime settings unknown | Cloud security owner | Review the named production project, CI identity, permissions, and environment protections |
| manual check | Production authorization | unresolved | No authorization test supplied | Unauthorized access or privilege bypass may exist | Backend security owner | Run independent negative authorization tests against deployed-equivalent policy |
| manual check | Recovery and containment | unresolved | No restore, migration recovery, alert, or kill-switch evidence | A bad release may be unrecoverable or undetected | SRE owner | Exercise restore/recovery, alerts, rollback or forward recovery, and containment |
| manual check | Privacy applicability | unresolved | Product data flows and destination are unidentified | Required privacy review may be missed | Privacy owner | Classify data and jurisdictions; record review or justified N/A |
| manual check | ASVS public baseline | unresolved | Applicable L1 requirements not dispositioned | Security boundaries remain untested | AppSec lead | Map applicable ASVS 5.0.0 IDs to independent tests and reviewers |
| automated pass | Narrow local preflight | pass | One-file scan of `ARTIFACT.md`; exit `0`; 1 file scanned | Does not cover candidate, history, dependencies, cloud, or runtime | Release manager | Repeat on a quiescent isolated checkout of the exact candidate |
| residual risk | Evidence is narrative-only | unresolved | Underlying evidence files unavailable | Reported results cannot be independently authenticated | Release manager | Supply immutable raw evidence tied to the frozen artifact |

Recommendation: `NO-GO`.

The candidate has multiple mandatory blockers that cannot be waived conditionally: a known-exploited vulnerability above policy, unsupported dependency, incomplete SBOM, mutable CI automation, invalid provenance, digest mismatch, unresolved lockfile conflict, and missing required manual evidence.

This recommendation applies only to the described artifact, scope, environment, evidence cutoff, and policy. It does not establish security, compliance, profitability, or future production behavior.

## Actions

External actions performed: none. No files were changed, dependencies installed, lifecycle scripts run, network calls made, or production systems accessed.