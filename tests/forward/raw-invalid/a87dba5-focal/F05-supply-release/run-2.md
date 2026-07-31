## Mode

Requested mode: publish release candidate.  
Effective mode: `ship`.  
Elevation trigger: public/production release.

## Evidence

Observed local evidence: [ARTIFACT.md](/home/dimi/projetos/vibeworthy-focal-a87dba5-clean/runs/F05-supply-release/run-2/ARTIFACT.md) describes the candidate, but contains no immutable artifact name, version, commit, or digest. The underlying `package.json`, lockfiles, workflow, SCA, SBOM, provenance, and digest files are not present in the inspected run directory.

Artifact-reported blockers:

- Unsupported dependency and unreviewed post-install execution.
- npm and Yarn lockfiles conflict.
- Mutable `actions/checkout@v4` reference.
- Open known-exploited vulnerability above policy.
- Incomplete transitive SBOM.
- Invalid signature verification.
- Built and deployed digests differ.
- No secret-history result, cloud review, or production authorization test.

ICP, cohort, activation, and market success criteria: not applicable—this is a release-integrity review.

## Contract

Smallest slice: assess whether the represented candidate can be published using safe, read-only local checks.

Non-goals: installing dependencies, executing lifecycle or remote scripts, using the network, modifying files, deploying, or granting production approval.

Authority envelope: read-only access to the supplied run directory; local shell and isolated Python only; no production, cloud, credential, or external access.

Package manager: unresolved because both npm and Yarn lockfiles are artifact-reported. No unrelated files were changed.

| Dimension | Option A: publish now | Option B: hold and rebuild |
| --- | --- | --- |
| User value | Earlier availability | Delayed but trustworthy artifact |
| Security/privacy risk | Critical supply-chain risks remain | Risks can be remediated and independently verified |
| Maintenance | Ambiguous resolution and unsupported dependency | One lockfile and supported dependency baseline |
| Accessibility | Not applicable—no UI change evaluated | Not applicable—no UI change evaluated |
| Cost | Lower immediate effort; high incident risk | Remediation and rebuild cost |
| Portability | Artifact identity cannot be reproduced | Identity and inputs can be recorded |
| Reversibility | Deployment may expose a mismatched artifact | Hold is fully reversible |

Chosen: Option B.  
Accepted cost: release delay.  
Revisit trigger: every failed or unresolved ledger row passes for one immutable candidate.

## Slices

Completed: bounded release-evidence assessment.

Verification:

- Inspected the artifact representation.
- Inspected preflight help successfully.
- Ran isolated preflight only against stable `ARTIFACT.md`; report: 1 file scanned, no findings, exit code 0.
- The whole run directory was not scanned because `events.jsonl` may be session-written. No build, test, install, or lifecycle command was run.

## Trust

Primary mapping: OWASP Top 10:2025 A03, Software Supply Chain Failures. Exact ASVS 5.0.0 requirement mapping is unresolved because no official catalog evidence was supplied and IDs were not guessed.

The enforcement boundaries needing evidence are dependency resolution/install execution, CI source selection, builder/signature verification, artifact promotion, deployment digest verification, secret history, cloud configuration, and production authorization.

No security, compliance, or production-readiness claim can be derived from the narrow preflight pass.

## Release

Artifact: unknown immutable identity; represented only by `ARTIFACT.md` | Scope: described supply-chain release candidate | Environment: intended production/public release; exact destination unknown | Policy: VibeWorthy public-release gates; artifact’s dated vulnerability policy unknown | Evidence cutoff: 2026-07-31

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| residual risk | Exact artifact identity | unresolved | No version, commit, builder, or artifact digest in supplied representation | Evidence cannot be bound to a unique candidate | Release manager | Record source commit, version/tag, builder, lockfile digest, artifact digest, and destination |
| automated failure | Unsupported dependency | fail | Artifact reports dependency as unsupported | Unmaintained vulnerable component | Dependency owner | Replace or remove it; rebuild and rerun policy checks |
| manual check | Post-install script review | unresolved | Lifecycle script reported; underlying script unavailable | Installation may execute unsafe code | AppSec reviewer | Inspect package/source, permissions, network behavior, and script without executing it |
| automated failure | Authoritative lockfile | fail | Both npm and Yarn lockfiles reported | Non-reproducible dependency graph | Build owner | Select one package manager and regenerate/review one immutable lockfile |
| automated failure | Known-exploited vulnerability | fail | SCA record is artifact-reported as open above policy | Known exploitation exposure | Security owner | Patch/remove dependency, assign SLA, and produce a passing dated SCA record |
| automated failure | Complete transitive SBOM | fail | CycloneDX SBOM reportedly omits one transitive dependency | Components and vulnerabilities may be missed | Release engineer | Regenerate SBOM from the exact rebuilt artifact and verify full transitive coverage |
| automated failure | Immutable CI automation | fail | `actions/checkout@v4` reportedly uses a mutable tag | Workflow dependency can change | CI owner | Pin the reviewed action to a full commit SHA |
| automated failure | Provenance/signature | fail | Evidence reportedly says verification is invalid | Builder and artifact authenticity untrusted | Build security owner | Rebuild using the approved builder and independently verify signature/provenance |
| automated failure | Promotion digest | fail | Built and deployed SHA-256 values reportedly differ | Deployed bytes are not the reviewed bytes | Release manager | Stop promotion; identify deployed bytes, rebuild if needed, and verify an exact digest match |
| manual check | Secret-history review | unresolved | No result supplied | Historical credentials may remain exposed | Security owner | Run dedicated history scanning on an isolated trusted checkout; remediate and rotate findings |
| manual check | Cloud review | unresolved | No cloud review supplied | CI identity, permissions, destination, and controls unknown | Cloud security owner | Review named project, least privilege, release protection, logging, recovery, and containment |
| manual check | Production authorization | unresolved | No production authorization test supplied | Unauthorized or cross-user access may ship | Application security owner | Run deployed-equivalent actor/action denial tests with synthetic identities |
| manual check | Production release approval | unresolved | No named approver or destination supplied | Consequential release lacks accountable authorization | Release authority | Approve the exact artifact, destination, evidence set, and promotion window after all gates pass |
| automated pass | Narrow local preflight | pass | Isolated scanner: `ARTIFACT.md`, considered/scanned 1/1, no findings, exit 0 | Does not cover source files, Git history, dependencies, cloud, or runtime | Release manager | Retain only as supplemental evidence; rerun on a quiescent isolated candidate checkout |

Recommendation: `NO-GO`.

Do not publish this candidate. Multiple mandatory release gates have explicit failures, and the artifact’s immutable identity is unresolved. This recommendation applies only to the named representation, scope, environment, evidence cutoff, and policy. It does not prove security, compliance, profitability, or future production behavior.

## Actions

External actions performed: none. No files were modified, dependencies installed, scripts executed, network requests made, or deployments attempted.