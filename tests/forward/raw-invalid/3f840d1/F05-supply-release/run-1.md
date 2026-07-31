## Mode

Requested mode: publish release candidate.  
Effective mode: `ship`. Trigger: production/public release.

## Evidence

Observed: [ARTIFACT.md](/home/dimi/projetos/vibeworthy-forward-3f840d1/runs/F05-supply-release/run-1/ARTIFACT.md) describes critical supply-chain failures. Its SHA-256 is `bd1be3bae8cfb3516ae99d3113323541cb248c01e8906292f5e3a7401f81151d`.

The actual package, lockfiles, workflow, SBOM, provenance, and digest files are absent, so their exact contents and hashes could not be independently verified. Source commit, release tag, distributable filename, destination, policy version, release owner, reviewer, ICP, cohort, activation, and success criteria are unknown.

## Contract

Smallest slice: evaluate whether the described candidate may be promoted.

Non-goals: installing dependencies, executing lifecycle or remote scripts, modifying files, deploying, accessing production/cloud systems, or asserting broader security/compliance.

Authority: read-only local filesystem; no network, writes, secrets, production access, or external side effects.

Package-manager identity is unresolved because both npm and Yarn lockfiles are described.

| Dimension | Option A: publish now | Option B: hold and remediate |
| --- | --- | --- |
| User value | Faster availability | Delayed but trustworthy artifact |
| Security/privacy | Exposes known supply-chain risk | Blocks known exploitation and integrity failures |
| Maintenance | Carries unsupported dependency | Establishes supported dependency baseline |
| Accessibility | Not applicable — no UI evidence | Not applicable — no UI change |
| Cost | Lower immediate effort; high incident risk | Remediation and rebuild cost |
| Portability | Ambiguous lockfile resolution | One reproducible package-manager path |
| Reversibility | Deployment may be difficult to contain | Hold is immediately reversible |

Chosen: Option B.  
Accepted cost: release delay.  
Revisit trigger: every failed and unresolved ledger row passes for one exact rebuilt artifact.

## Slices

Completed: read-only release assessment.

Verification:

- `python3 -I skill/vibeworthy/scripts/preflight.py . --format text` scanned 16/16 local files with no findings or scanner tool errors.
- The scan did not cover Git history, dependencies, cloud configuration, runtime authorization, or the absent release artifacts.
- No build, test, installation, or lifecycle script was executed.

## Trust

Primary boundaries are dependency installation, CI automation, artifact signing/promotion, and production authorization.

Applicable OWASP Top 10:2025 risks:

- A03 Software Supply Chain Failures: failed.
- A08 Software or Data Integrity Failures: failed.
- A01 Broken Access Control: production authorization evidence unresolved.
- A02 Security Misconfiguration: cloud review unresolved.

ASVS 5.0.0 requirement IDs were not assigned because the official catalog was not locally available and IDs must not be guessed. Applicable public-release Level 1 review remains unresolved.

## Release

Artifact: described candidate identified by `ARTIFACT.md` SHA-256 `bd1be3…51d`; distributable digest/source commit unknown | Scope: described supply-chain release candidate | Environment: production destination unknown | Policy: local VibeWorthy public-release policy, version unknown | Evidence cutoff: 2026-07-31T02:23:02-03:00

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| automated failure | Unsupported dependency | fail | Artifact description records unsupported component | Unmaintained vulnerable code | Dependency owner | Replace it; rebuild and rerun SCA |
| manual check | `postinstall` review | unresolved | Lifecycle script exists; not executed or reviewed | Installation-time code execution | Security reviewer | Review source, permissions, network behavior, and necessity |
| automated failure | Authoritative lockfile | fail | Both npm and Yarn lockfiles described | Non-reproducible resolution | Build owner | Select package manager and retain one reviewed lockfile |
| automated failure | Known-exploited vulnerability | fail | SCA evidence records an above-policy open KEV | Exploitation of released component | Security lead | Patch/remove component and produce clean dated SCA evidence |
| automated failure | Complete transitive SBOM | fail | CycloneDX SBOM omits a transitive dependency | Incomplete component inventory | Release engineer | Regenerate SBOM from exact artifact and verify full graph |
| automated failure | Immutable automation | fail | `actions/checkout@v4` uses mutable tag | Workflow dependency substitution | CI owner | Pin reviewed action to full commit SHA |
| automated failure | Provenance/signature | fail | Evidence records invalid verification | Artifact origin cannot be trusted | Release engineer | Rebuild with approved builder and retain successful verification |
| automated failure | Promotion digest | fail | Built and deployed digests reportedly differ | Deployed bytes are not evaluated bytes | Release owner | Stop promotion; identify mismatch, rebuild, and compare exact SHA-256 values |
| manual check | Secret-history review | unresolved | No result exists | Historical credentials may be exposed | Security lead | Run dedicated history and release-artifact secret review |
| manual check | Cloud review | unresolved | No cloud evidence exists | CI identity, permissions, and destination controls unknown | Cloud owner | Review named project, least privilege, environment protection, and audit controls |
| manual check | Production authorization | unresolved | No production authorization test exists | Unauthorized production behavior | Application security owner | Run independent negative authorization matrix against deployed-equivalent policy |
| automated pass | Local preflight | pass | VibeWorthy 1.0.0 via isolated `python3`; 16/16 files, no findings | Does not cover absent artifacts, history, cloud, or runtime | Release reviewer | Retain as supplemental evidence only |
| tool error | Prescribed `python` invocation | tool error | `python` command unavailable; exit 127 | Interpreter alias/environment not reproducible | Build environment owner | Define approved interpreter and rerun on trusted isolated runner |
| residual risk | Exact artifact identity | unresolved | Distributable filename, source commit, tag, and exact hashes absent | Evidence cannot be bound to release bytes | Release owner | Record commit, tag, lockfile digest, builder, artifact digest, and destination |
| residual risk | Ownership and independent approval | unresolved | Named people not recorded | Remediation and approval accountability unclear | Engineering manager | Assign named owners and independent release reviewer |

Recommendation: `NO-GO`.

Do not publish this candidate. The known-exploited vulnerability, unsupported dependency, incomplete SBOM, mutable automation, invalid provenance, digest mismatch, conflicting lockfiles, unreviewed lifecycle script, and missing mandatory manual evidence are individually release blockers.

This recommendation applies only to the described artifact, scope, environment, evidence cutoff, and policy. It does not prove security, compliance, profitability, or future production behavior.

## Actions

External actions performed: none.