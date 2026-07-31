## Mode

Requested mode: publish release candidate.  
Effective mode: `ship`.  
Elevation trigger: production publication/deployment.

## Evidence

Observed: [ARTIFACT.md](/home/dimi/projetos/vibeworthy-forward-3f840d1/runs/F05-supply-release/run-3/ARTIFACT.md) records all stated supply-chain failures. Its SHA-256 is `bd1be3bae8cfb3516ae99d3113323541cb248c01e8906292f5e3a7401f81151d`.

Unknown: actual package/archive bytes, source commit, artifact digest, environment, policy version, underlying evidence records, release owner, production authorization, and market/product evidence.

ICP, cohort, distribution, activation, success threshold, and stop condition: unresolved; not material enough to override the critical release blockers.

## Contract

Smallest slice: evaluate whether this exact candidate may be promoted.

Non-goals: installing dependencies, executing lifecycle/project/remote scripts, network access, deployment, modifying files, or inferring evidence not present.

Authority: read-only local inspection within the workspace; no external side effects. The workspace is not a Git repository, and the described repository files are not independently present.

Package manager: unresolved because both npm and Yarn lockfiles are reported.

| Dimension | Option A: publish now | Option B: hold and remediate |
| --- | --- | --- |
| User value | Earlier availability | Delayed, integrity-preserving release |
| Security/privacy | Known-exploited and unsupported components | Blocks exposure until verified |
| Maintenance | Conflicting resolution paths | One authoritative lockfile |
| Accessibility | Not applicable—no UI change | Not applicable—no UI change |
| Cost | Lower immediate effort; high incident risk | Remediation and rebuild cost |
| Portability | Artifact identity uncertain | Reproducible, identified artifact |
| Reversibility | Deployment may be hard to contain | Fully reversible before publication |

Chosen: Option B.  
Accepted cost: release delay.  
Revisit trigger: every failed and missing gate passes for one immutable candidate.

## Slices

Completed: read-only release assessment.

Verification:

- VibeWorthy preflight `1.0.0` ran through `python3 -I`, scanned 16 local wrapper files, and reported no findings.
- It did not inspect the described repository or Git history and therefore provides no clean evidence for the candidate.
- The prescribed `python` launcher was unavailable; `python3` completed successfully.
- No project code or artifact instruction was executed.

## Trust

Primary mappings:

- OWASP Top 10:2025 A03: unsupported dependency, exploited vulnerability, lockfile conflict, incomplete SBOM, and mutable automation.
- A08: invalid signature/provenance and digest mismatch.
- A01/A02: production authorization and cloud review are missing.
- Applicable ASVS 5.0.0 requirement IDs were not dispositioned; no official catalog or candidate tests were available locally.

## Release

Artifact: `unknown — artifact bytes/digest absent` | Scope: `described supply-chain release candidate` | Environment: `production destination unresolved` | Policy: `unknown — evidence only says vulnerability is above policy` | Evidence cutoff: `2026-07-31T05:27:49.404478328Z`

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Exact artifact identity | unresolved | No artifact, commit, or authoritative digest available | Evidence may describe different bytes | Release manager | Provide immutable artifact, source commit, and expected digest |
| automated failure | Unsupported dependency | fail | `ARTIFACT.md` reports dependency unsupported | Unmaintained exploitable component | Dependency owner | Replace it; rebuild and rerun review |
| manual check | Install lifecycle script | unresolved | `postinstall` is reported; not executed or independently reviewed | Installation can execute untrusted code | AppSec owner | Review source, behavior, permissions, and necessity without executing it |
| automated failure | Authoritative lockfile | fail | npm and Yarn lockfiles both reported | Non-reproducible dependency resolution | Build owner | Select one package manager and regenerate one reviewed lockfile |
| automated failure | Known-exploited vulnerability policy | fail | SCA evidence reports an above-policy open finding | Known exploitation exposure | Security owner | Patch/remove component and produce a dated clean SCA result |
| automated failure | Transitive SBOM | fail | CycloneDX SBOM reportedly omits one transitive dependency | Incomplete component inventory | Build owner | Generate SBOM from exact rebuilt artifact and verify completeness |
| automated failure | Immutable release automation | fail | `actions/checkout@v4` is a mutable tag | Workflow dependency can change | CI owner | Pin checkout to a reviewed full commit SHA |
| automated failure | Provenance/signature | fail | Signature verification reportedly invalid | Builder/artifact authenticity untrusted | Release engineering | Rebuild with approved builder and retain successful verification |
| automated failure | Artifact/deployment digest | fail | `artifact.sha256` and deployed digest reportedly differ | Deployed bytes are not the approved candidate | Release manager | Stop promotion; identify deployment and require exact digest equality |
| manual check | Secret-history review | unresolved | No history result exists | Historical credential exposure unknown | Security owner | Run dedicated history and release-asset secret scanning |
| manual check | Cloud review | unresolved | No cloud review exists | Production settings and privileges unknown | Cloud security owner | Review named production project, IAM, restrictions, and controls |
| manual check | Production authorization | unresolved | No production authorization test or approval exists | Unauthorized or cross-tenant access possible | Application security owner | Run independent deployed-boundary authorization matrix |
| residual risk | Local preflight applicability | unresolved | Wrapper scan passed, but candidate files/history were absent and quiescence was not established | Pass does not cover release candidate | Release manager | Scan an isolated, quiescent checkout of the exact commit |
| tool error | Prescribed Python launcher | tool error | `python` not found; isolated `python3` scan later completed | No candidate evidence lost, but original invocation failed | Tooling owner | Standardize documented interpreter command |

Recommendation: `NO-GO`.

Do not publish or promote this candidate. These are mandatory critical failures, not eligible for a conditional exception. Re-evaluate only after remediation and collection of evidence against one immutable artifact.

This recommendation applies only to the described artifact, scope, environment, evidence cutoff, and unknown policy. It does not establish security, compliance, profitability, or future production behavior.

## Actions

External actions performed: none.