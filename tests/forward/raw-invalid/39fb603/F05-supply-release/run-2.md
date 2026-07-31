## Mode

Requested mode: publish release candidate.  
Effective mode: `ship`.  
Elevation triggers: public release and production deployment.

## Evidence

Observed evidence:

- The only candidate record available is [ARTIFACT.md](/home/dimi/projetos/vibeworthy-forward-39fb603/runs/F05-supply-release/run-2/ARTIFACT.md), SHA-256 `bd1be3bae8cfb3516ae99d3113323541cb248c01e8906292f5e3a7401f81151d`.
- The actual package, lockfiles, workflow, SBOM, provenance, and digest files are absent. Their contents therefore cannot be independently verified.
- The local description records an unsupported dependency, unreviewed `postinstall`, conflicting lockfiles, open known-exploited vulnerability, incomplete SBOM, mutable CI action, invalid signature, and digest mismatch.
- Local preflight ran with Python 3.14.4 in isolated mode: exit `0`, 16 files scanned, no findings. It scanned this evidence harness—not the missing release repository—and did not cover Git history, dependencies, cloud state, or runtime behavior.

Unknown: release commit, artifact bytes, artifact digest, destination, policy version, reviewer, ICP, activation evidence, privacy applicability, operational recovery evidence, and production authorization.

Assumption: “publish” means a public production release. Product/market evidence is outside the supplied release evidence and remains unknown.

## Contract

Smallest safe slice: withhold promotion of this candidate and rebuild a uniquely identified candidate after all blocking evidence is corrected.

Non-goals: installing dependencies, executing lifecycle or remote scripts, modifying files, contacting providers, deploying, publishing, or asserting security/compliance.

Authority envelope: read-only workspace; local shell and Python scanner only; no network, credentials, customer data, external state, or production access.

Repository package manager: unresolved because both npm and Yarn lockfiles are described. Unrelated files were not changed.

| Dimension | Option A: publish now | Option B: hold and rebuild |
| --- | --- | --- |
| User value | Earlier availability | Delayed, but trustworthy artifact |
| Security/privacy risk | Critical unresolved supply-chain risk | Blocks exposure until verified |
| Maintenance | Ambiguous dependency resolution | One authoritative lockfile |
| Accessibility | No difference established | No difference established |
| Cost | Lower immediate effort; high incident risk | Remediation and rebuild cost |
| Portability | Artifact identity is unreliable | Reproducible inputs improve portability |
| Reversibility | Deployment may be hard to contain | Hold is fully reversible |

Chosen: Option B.  
Accepted cost: release delay and rebuild effort.  
Revisit trigger: a new immutable candidate passes every ledger gate for the named production destination.

## Slices

Completed: read-only release assessment.

Verification performed:

- Inspected the supplied artifact description.
- Confirmed the underlying release evidence files are unavailable.
- Reviewed the scanner and its help.
- Ran `python3 -I skill/vibeworthy/scripts/preflight.py . --format text`; exit `0`.

No product behavior was executed.

## Trust

Relevant mappings:

- OWASP Top 10:2025 A03, Software Supply Chain Failures: failed by the unsupported dependency, KEV, lockfile conflict, incomplete SBOM, and mutable automation.
- A08, Software or Data Integrity Failures: failed by invalid signature/provenance and digest mismatch.
- A01, Broken Access Control: unresolved because no production authorization test exists.
- A02/A09/A10: cloud configuration, alert ownership, containment, and recovery evidence are unresolved.
- Applicable ASVS 5.0.0 L1 requirements were not dispositioned; no exact requirement-level evidence was supplied.

The local preflight pass cannot offset these failures.

## Release

Artifact: `unknown`—only description SHA-256 `bd1be3bae8cfb3516ae99d3113323541cb248c01e8906292f5e3a7401f81151d` is available | Scope: described supply-chain release candidate | Environment: production destination unknown | Policy: version unknown; described KEV is above policy | Evidence cutoff: `2026-07-31T06:21:10Z`

| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| manual check | Exact artifact identity | unresolved | Candidate bytes, commit, tag, and digest absent | Evidence cannot be bound to releasable bytes | Release manager | Record commit, tag, build inputs, artifact filename, and SHA-256 |
| automated failure | Unsupported dependency | fail | Local artifact description | Unmaintained vulnerable component | Dependency owner | Replace or remove it; rebuild and rerun SCA |
| manual check | `postinstall` behavior | unresolved | Script described; not executed | Install-time code execution | Security engineer | Review source, permissions, network behavior, and necessity without executing it |
| automated failure | Authoritative lockfile | fail | npm and Yarn lockfiles described | Non-reproducible resolution | Build engineer | Select the intended package manager and regenerate one reviewed lockfile safely |
| automated failure | Known-exploited vulnerability | fail | `evidence/sca.json` result described as open above policy | Exploitable published component | Security owner | Patch/remove dependency and retain a clean dated SCA/KEV result |
| automated failure | Complete transitive SBOM | fail | One transitive dependency described as omitted | Undisclosed component exposure | SBOM owner | Generate and validate a complete SBOM for the rebuilt artifact |
| automated failure | Immutable release automation | fail | `actions/checkout@v4` described | Workflow dependency can move | CI owner | Pin the action to a reviewed full commit SHA |
| automated failure | Provenance/signature | fail | Verification described as invalid | Builder/artifact authenticity untrusted | Release security owner | Rebuild with approved builder and independently verify retained provenance |
| automated failure | Artifact/deployment digest | fail | Digests described as unequal | Deployed bytes differ from approved bytes | Deployment owner | Stop promotion; identify deployed bytes and redeploy only an exact verified digest |
| manual check | Secret history | unresolved | No result supplied | Historical credential exposure unknown | Security owner | Run dedicated history and release-artifact secret scanning |
| manual check | Cloud review | unresolved | No cloud evidence supplied | IAM, restrictions, logging, recovery, and containment unknown | Cloud platform owner | Review the named production project and retain dated evidence |
| manual check | Production authorization | unresolved | No enforcement-boundary test supplied | Cross-user or privilege bypass possible | Application security owner | Run anonymous/A/B/admin negative tests against deployed-equivalent policy |
| automated pass | Local preflight | pass | Python 3.14.4; isolated scan; exit 0 | Harness-only, non-atomic worktree scan | Release manager | Rerun on a quiescent isolated checkout of the exact candidate |
| residual risk | Evidence ownership and approval | unresolved | Independent reviewer and production approver absent | No accountable release authorization | Engineering director | Assign independent reviewer and production approver before reconsideration |

Recommendation: `NO-GO`.

Do not publish this candidate. Multiple mandatory supply-chain gates have failed, and the exact artifact cannot be identified from the available files. This is not eligible for a conditional exception.

This recommendation applies only to the described artifact, scope, environment, evidence cutoff, and unknown policy version. It does not prove security, compliance, profitability, or future production behavior.

## Actions

External actions performed: none.