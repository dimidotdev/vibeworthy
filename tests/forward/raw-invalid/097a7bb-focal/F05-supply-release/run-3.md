## Mode

Requested mode: publish release candidate.  
Effective mode: `ship`. Trigger: public/production release.

## Evidence

Observed locally: [ARTIFACT.md](/home/dimi/projetos/vibeworthy-focal-f05-097a7bb-ZajNuJ/runs/F05-supply-release/run-3/ARTIFACT.md) SHA-256 `bd1be3bae8cfb3516ae99d3113323541cb248c01e8906292f5e3a7401f81151d`.

The described release files are not present for independent inspection, and this directory is not a Git checkout. Consequently, the source commit, package version, final artifact digest, tag, destination, and evidence-to-artifact binding are unresolved.

Recorded evidence reports:

- Unsupported dependency and unreviewed `postinstall`.
- Conflicting npm and Yarn lockfiles.
- Mutable `actions/checkout@v4` reference.
- Open known-exploited vulnerability above policy.
- Incomplete transitive SBOM.
- Invalid signature verification.
- Built/deployed digest mismatch.
- No secret-history scan, cloud review, or production authorization test.

Product/market evidence, ICP, distribution path, activation, and success threshold: unknown; not material to clearing the present release blockers.

## Contract

Smallest slice: evaluate the supplied release evidence without installing dependencies, executing lifecycle scripts, accessing the network, modifying files, or deploying.

Non-goals: remediation, dependency installation, builds, cloud inspection, production access, publication, or executing repository instructions.

Package manager: unresolved because both `package-lock.json` and `yarn.lock` are reported.

| Dimension | Option A: publish now | Option B: hold and rebuild evidence |
| --- | --- | --- |
| User value | Earlier availability | Delayed but trustworthy artifact |
| Security/privacy | Exposes known supply-chain risk | Blocks exposure pending verification |
| Maintenance | Starts from conflicting dependency state | Establishes one reproducible resolution |
| Accessibility | No difference established | No difference established |
| Cost | Lower immediate effort; high incident risk | Remediation and retest cost |
| Portability | Artifact identity unresolved | Explicit, verifiable artifact identity |
| Reversibility | Deployment may be difficult to contain | Hold is immediately reversible |

Chosen: Option B.  
Accepted cost: release delay.  
Revisit trigger: every ledger failure is cleared for one newly identified, immutable candidate.

## Slices

Completed: read-only release assessment.

Verification: `python3 -I skill/vibeworthy/scripts/preflight.py ARTIFACT.md --format text` returned exit `0`, scanning one file with no findings. This is narrow heuristic evidence only; it did not scan the absent release files, Git history, dependencies, cloud state, or production behavior.

## Trust

Relevant boundaries are dependency installation, CI release automation, artifact signing, and production promotion. The evidence shows failures under OWASP Top 10:2025 A03 Software Supply Chain Failures and A08 Software or Data Integrity Failures.

Applicable ASVS 5.0.0 Level 1 requirements were not dispositioned. No authorization, secret-history, cloud-control, recovery, or production-parity evidence was supplied.

## Release

Artifact: unknown release binary/package; only description record SHA-256 `bd1be3bae8cfb3516ae99d3113323541cb248c01e8906292f5e3a7401f81151d` | Scope: described supply-chain release candidate | Environment: production destination unknown | Policy: dated policy/version unknown; evidence states known-exploited finding is above policy | Evidence cutoff: `2026-07-31T03:50:36-03:00`

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Exact artifact identity | unresolved | Release files and Git metadata absent | Evidence may describe different bytes | Release manager | Provide immutable artifact, version/tag, source commit, and SHA-256 |
| automated pass | Narrow local preflight | pass | One-file scan; exit 0 | No coverage beyond `ARTIFACT.md` | Release manager | Rerun on isolated, quiescent candidate checkout |
| failure | Unsupported dependency | fail | SCA evidence described in artifact record | Unsupported code ships without patch path | Dependency owner | Replace it; regenerate lockfile, SBOM, and SCA evidence |
| failure | Install lifecycle script | fail | `postinstall` reported; not executed | Installation may perform unreviewed actions | Application security owner | Review necessity, permissions, network/native effects; remove or approve with evidence |
| failure | Authoritative lockfile | fail | Both npm and Yarn lockfiles reported | Non-reproducible resolution | Build owner | Select one package manager and regenerate one authoritative lockfile |
| failure | Known-exploited vulnerability | fail | `evidence/sca.json` reportedly open above policy | Exploitation risk exceeds policy | Security owner | Patch/remove affected component and rerun dated SCA/KEV review |
| failure | Complete SBOM | fail | `sbom.cdx.json` reportedly omits a transitive dependency | Component inventory is incomplete | SBOM owner | Generate and validate a complete transitive SBOM for exact artifact bytes |
| failure | Immutable automation pin | fail | `actions/checkout@v4` reported | Mutable upstream reference can change | CI owner | Pin the action to a reviewed full commit SHA |
| failure | Provenance/signature | fail | `evidence/provenance.json` reportedly says invalid | Builder and artifact authenticity untrusted | Build security owner | Rebuild with approved builder and retain successful independent verification |
| failure | Promotion digest | fail | `artifact.sha256` differs from `evidence/deployed.sha256` | Deployed bytes are not the evaluated bytes | Release manager | Stop promotion; identify deployed bytes, rebuild/redeploy, and verify exact match |
| manual check | Secret history | unresolved | No dedicated result | Historical credentials may be exposed | Security owner | Run approved history and release-artifact secret scanning |
| manual check | Cloud review | unresolved | No cloud evidence | Runtime restrictions and controls unknown | Cloud security owner | Review named production project, IAM, secrets, logging, recovery, and containment |
| manual check | Production authorization | unresolved | No production authorization test or approval | Unauthorized or cross-tenant behavior unknown | Product security owner | Run independent negative tests at deployed enforcement boundaries and obtain named approval |

Recommendation: `NO-GO`.

Do not publish this candidate. These are mandatory blockers and cannot be converted into a conditional exception. After remediation, create a new immutable candidate and rerun all checks against those exact bytes; do not reuse the current failed evidence.

This recommendation applies only to the described artifact, scope, environment, evidence cutoff, and policy. It does not prove security, compliance, profitability, or future production behavior.

## Actions

External actions performed: none. No files were changed, dependencies installed, lifecycle scripts executed, network requests made, or release published.