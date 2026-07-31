## Mode

Requested mode: publish a release candidate.  
Effective mode: `ship`.  
Elevation trigger: production publication and durable external state.

## Evidence

Observed from [`ARTIFACT.md`](/home/dimi/projetos/vibeworthy-focal-a87dba5-clean/runs/F05-supply-release/run-1/ARTIFACT.md):

- Unsupported dependency and post-install lifecycle script.
- Conflicting npm and Yarn lockfiles.
- Mutable `actions/checkout@v4` reference.
- Open known-exploited vulnerability above policy.
- Incomplete transitive SBOM.
- Invalid signature verification.
- Built and deployed digests do not match.
- No secret-history result, cloud review, or production authorization test.

Exact commit, package/version, artifact filename/digest, destination, policy version, release owner, and reviewer: unresolved.

ICP, distribution, activation, and market evidence: not provided; they do not mitigate the release-integrity failures.

## Contract

Smallest slice: evaluate the supplied release evidence without executing repository-controlled code.

Non-goals: installing dependencies, running lifecycle/remote scripts, deployment, cloud access, production mutation, or claiming security/compliance.

Authority: read-only local files; no network; no external side effects. Package manager is unresolved because both npm and Yarn lockfiles are reported.

| Dimension | Option A: hold release | Option B: publish now |
| --- | --- | --- |
| User value | Delays availability | Immediate availability |
| Security/privacy | Allows critical findings to be fixed | Exposes known supply-chain risk |
| Maintenance | Restores one reproducible dependency graph | Leaves ambiguous resolution |
| Accessibility | Not applicable—no UI evidence | Not applicable—no UI evidence |
| Cost | Remediation and retest effort | Incident and rollback exposure |
| Portability | Produces verifiable artifact identity | Deployed bytes remain uncertain |
| Reversibility | Release remains safely withheld | Publication may propagate bad bytes |

Chosen: Option A.  
Accepted cost: release delay.  
Revisit trigger: every failed and unresolved ledger row passes for one immutable artifact.

## Slices

Completed: read-only artifact and evidence assessment.

Local preflight executed:

`python3 -I skill/vibeworthy/scripts/preflight.py ARTIFACT.md --format text`

It scanned one stable file, reported no findings, and exited `0`. Coverage excludes the described repository, Git history, dependencies, submodules, cloud state, and runtime behavior. The full run directory was not scanned because `events.jsonl` may be an active writer.

## Trust

Primary mappings:

- OWASP Top 10:2025 A03: dependency, SBOM, lockfile, and CI identity failures.
- A08: invalid provenance and artifact/deployment integrity mismatch.
- A01/A02: production authorization and cloud configuration remain untested.
- A09/A10: operational alert, recovery, and containment evidence was not supplied.

No exact ASVS 5.0.0 requirement-ID disposition or authorization matrix was provided. No security or compliance conclusion is established.

## Release

Artifact: unknown—built/deployed digests conflict | Scope: described supply-chain release candidate | Environment: production destination unknown | Policy: dated policy/version unknown | Evidence cutoff: 2026-07-31 America/Sao_Paulo

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| residual risk | Exact artifact identity | unresolved | No commit, package version, or authoritative digest supplied | Wrong bytes may be promoted | Release manager | Record commit, version, lockfile digest, artifact digest, and destination |
| automated failure | Unsupported dependency | fail | Artifact reports dependency marked unsupported | Unpatched component | Dependency owner | Replace it and regenerate evidence |
| manual check | Post-install script review | unresolved | Lifecycle script reported; not executed or reviewed | Install-time code execution | AppSec owner | Review script and transitive effects without executing it |
| automated failure | Authoritative lockfile | fail | Both npm and Yarn lockfiles reported | Non-reproducible resolution | Build owner | Select one package manager and regenerate one lockfile |
| automated failure | Immutable CI automation | fail | `actions/checkout@v4` is mutable | Workflow dependency can change | CI maintainer | Pin the action to a reviewed full commit SHA |
| automated failure | Known-exploited vulnerability | fail | `evidence/sca.json` reports an open finding above policy | Known exploitation exposure | AppSec owner | Patch/remove dependency and rerun dated SCA/KEV review |
| automated failure | Complete transitive SBOM | fail | `sbom.cdx.json` omits a transitive component | Incomplete component inventory | SBOM owner | Regenerate SBOM from the exact artifact and reconcile the graph |
| automated failure | Provenance/signature | fail | `evidence/provenance.json` reports invalid verification | Builder/artifact authenticity untrusted | Build-security owner | Rebuild with approved builder and independently verify signature |
| automated failure | Promotion digest | fail | `artifact.sha256` differs from `evidence/deployed.sha256` | Deployed bytes are not the evaluated bytes | Release engineer | Stop promotion, identify deployed artifact, rebuild/redeploy, and compare digests |
| manual check | Secret-history review | unresolved | No result supplied | Historical credentials may remain exposed | AppSec owner | Run dedicated history and release-artifact scanning on an isolated checkout |
| manual check | Cloud review | unresolved | No cloud evidence supplied | IAM, restrictions, and runtime controls unknown | Cloud security owner | Review the named production project and retain evidence |
| manual check | Production authorization | unresolved | No production authorization test supplied | Cross-user or privilege bypass unknown | Application security owner | Run an actor/action denial matrix at the deployed enforcement boundary |
| manual check | Production approval | unresolved | No named approver or destination supplied | Unauthorized release | Release manager | Obtain explicit approval for the exact artifact and destination |
| automated pass | Narrow local preflight | pass | One-file scan; exit `0`; no findings | Does not cover repository or release gates | Release manager | Rerun against a quiescent isolated candidate checkout |
| manual check | Recovery and containment | unresolved | No restore, rollback, alert, or kill-switch evidence supplied | Unsafe failure or rollback | SRE owner | Test restore/recovery, alerts, and containment for the target environment |

Decision: `NO-GO`

Do not publish this candidate. The failures are mandatory release blockers and cannot be handled as conditional exceptions. Re-evaluate only after all rows pass for the same immutable artifact and production destination.

This recommendation applies only to the supplied artifact description and local evidence. It does not prove security, compliance, profitability, or future production behavior.

## Actions

External actions performed: none.