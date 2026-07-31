## Mode

Requested mode: publish release candidate.  
Effective mode: `ship`.  
Elevation triggers: public release, production deployment, and software-supply-chain promotion.

## Evidence

Observed evidence is limited to [ARTIFACT.md](/home/dimi/projetos/vibeworthy-forward-3f840d1/runs/F05-supply-release/run-2/ARTIFACT.md). The actual repository, commit, artifact bytes, and literal digest values are absent.

Known blockers:

- Unsupported dependency and unreviewed `postinstall`.
- Conflicting npm/Yarn lockfiles.
- Known-exploited vulnerability above policy.
- Incomplete transitive SBOM.
- Mutable `actions/checkout@v4` reference.
- Invalid signature verification.
- Built/deployed digest mismatch.
- Missing secret-history review, cloud review, and production authorization test.

ICP, distribution, activation, and product success evidence: unknown; not material to resolving these release-integrity blockers.

## Contract

Smallest safe slice: evaluate the represented candidate without installing, building, publishing, deploying, or executing artifact instructions.

Non-goals: dependency installation, lifecycle/remote scripts, network use, cloud access, production access, deployment, publication, or artifact modification.

Authority envelope: read-only workspace; local shell and isolated Python only; no credentials, customer data, external effects, or writes.

Package manager: unresolved because both `package-lock.json` and `yarn.lock` are reported.

| Dimension | Option A: publish now | Option B: hold and rebuild |
| --- | --- | --- |
| User value | Faster availability | Delayed but trustworthy release |
| Security/privacy | Known critical exposure | Blocks compromised components |
| Maintenance | Preserves ambiguity and unsupported code | Establishes one maintained dependency graph |
| Accessibility | No observed difference | No observed difference |
| Cost | Lower immediate effort, high incident risk | Remediation and rebuild cost |
| Portability | Unverified artifact | Reproducible, identified artifact |
| Reversibility | Poor after public distribution | High before promotion |

Chosen: Option B.  
Accepted cost: release delay and rebuild effort.  
Revisit trigger: every ledger failure passes for one exact artifact and production destination.

## Slices

No implementation or release action was performed.

The local scanner ran with `python3 -I`: 16 files scanned, no findings, exit 0. This covers only the fixture worktree—not Git history, cloud state, dependencies, or the missing release candidate. The mandated `python -I` command failed because `python` is unavailable.

## Trust

Primary mappings:

- OWASP Top 10:2025 A03: dependency, SBOM, lockfile, automation, and vulnerability failures.
- A08: invalid provenance and digest mismatch.
- A01/A02: production authorization and cloud configuration remain untested.
- ASVS 5.0.0 public-release L1 disposition: unresolved; exact applicable requirement IDs were not evidenced.

## Release

Artifact: `unknown — candidate bytes and digest absent` | Scope: `ARTIFACT.md-described supply-chain release candidate` | Environment: `production destination unknown` | Policy: `unknown — SCA evidence only says above policy` | Evidence cutoff: `2026-07-31 America/Sao_Paulo`

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Exact artifact identity | unresolved | No repository, commit, artifact bytes, or literal digest supplied | Evidence cannot be bound to release bytes | Release manager | Record commit, artifact digest, lockfile digest, builder, and destination |
| failure | Unsupported dependency | fail | `ARTIFACT.md` reports unsupported dependency | Unmaintained vulnerable component | Dependency owner | Replace/remove it and regenerate evidence |
| manual check | `postinstall` review | unresolved | Lifecycle script reported; not executed | Installation-time code execution | AppSec | Review source, permissions, and effects without executing it |
| failure | Authoritative lockfile | fail | npm and Yarn lockfiles both reported | Non-reproducible resolution | Build owner | Select one package manager and regenerate one reviewed lockfile |
| failure | Known-exploited vulnerability | fail | SCA result reports open finding above policy | Known exploitation risk | Security owner | Patch/remove component and rerun dated KEV/SCA policy |
| failure | Complete transitive SBOM | fail | One transitive dependency omitted | Undisclosed component risk | Build owner | Generate and validate SBOM from exact rebuilt artifact |
| failure | Immutable automation | fail | `actions/checkout@v4` | Workflow dependency can move | CI owner | Pin reviewed action to full commit SHA |
| failure | Provenance/signature | fail | Verification reported invalid | Builder/artifact authenticity unknown | Release engineering | Rebuild with approved builder and retain successful verification |
| failure | Promotion digest | fail | Built and deployed SHA-256 records differ | Wrong or modified deployed bytes | Release engineering | Stop promotion; identify mismatch and independently reverify |
| manual check | Secret history | unresolved | No history result | Historical credentials may be exposed | AppSec | Scan full Git history and release artifacts with dedicated tooling |
| manual check | Cloud review | unresolved | No cloud review | IAM, restrictions, logging, and containment unknown | Cloud security | Review the named production project and retain evidence |
| manual check | Production authorization | unresolved | No authorization test | Unauthorized or cross-user access possible | Service owner | Run independent negative tests at deployed enforcement boundaries |
| tool error | Mandated preflight command | tool error | `python -I ...` exited 127: interpreter absent | Required invocation unavailable | Developer tooling owner | Provide trusted `python` or document approved interpreter mapping and rerun |
| automated pass | Supplemental preflight | pass | `python3 -I`; 16/16 files, no findings | Fixture-only, non-atomic; no history/cloud/dependencies | Release manager | Rerun on quiescent isolated checkout of exact candidate |
| residual risk | Operational recovery evidence | unresolved | No backup/restore, alert, or containment evidence provided | Production incident recovery unknown | SRE owner | Supply applicable restore drill, alert, and containment records |

Recommendation: **NO-GO**.

Do not publish this candidate. These are mandatory failures, not eligible for a conditional exception.

This recommendation applies only to the represented scope and evidence cutoff. It does not establish security, compliance, profitability, or future production behavior.

## Actions

External actions performed: none.