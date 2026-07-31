---
spec: SPEC-VIBEWORTHY-LEAN-V1-0002
title: "VibeWorthy lean security release"
status: implemented
profile: critical
mode: deliver
owner: "dimidotdev"
created: 2026-07-31
updated: 2026-07-31
---

# VibeWorthy lean security release

## Context and Evidence

- EVD-001 | source: owner direction, 2026-07-31 | VibeWorthy shall be a useful, token-efficient
  security guardrail for vibe coding and AI-assisted development, not a broad market or engineering
  operating system and not an exhaustive audit loop.
- EVD-002 | source: `skill/vibeworthy/SKILL.md`, inspected 2026-07-31 | The implemented package uses
  `quick`, `guarded`, and `critical` intensities, progressive references, focused boundary tests, and
  an optional local preflight.
- EVD-003 | source: GitHub Actions run
  `https://github.com/dimidotdev/vibeworthy/actions/runs/30626738737`, 2026-07-31 | The current lean
  implementation passed its native suite on Python 3.11 for Linux, Windows, and macOS before this
  release-spec update; the final candidate still requires exact-commit CI.
- EVD-004 | source: OWASP Top 10:2025, OWASP API Security Top 10:2023, NIST SSDF 1.1, Firebase and
  Supabase security documentation, reviewed 2026-07-31 | Client visibility is not authorization;
  privileged service credentials must stay outside public clients; verification belongs at the
  actual enforcement boundary.
- EVD-005 | source: independent release audit `/root/vibeworthy_release_audit`, 2026-07-31 | The
  repository was public and the implementation coherent, but the former specification described an
  abandoned market/engineering product and could not support an honest `v1.0.0` claim.
- ASM-001 | Users of limited AI plans benefit from proportional checks that spend context only where
  the changed trust boundary warrants it. | validation: forward-test one scenario per intensity.

## Problem

AI-generated applications can expose secrets, cross-user data, payment authority, or unsafe supply
chain behavior while appearing complete. Existing security guidance often arrives too late or expands
small changes into costly generic audits. VibeWorthy needs a public release contract that matches its
implemented purpose: keep security present from prompt to release with the smallest useful control
and verification effort.

## Outcomes

- Publish a portable MIT-licensed Agent Skill that gives non-specialists plain-language security
  guardrails without claiming certification or perfect security.
- Keep low-risk work fast while requiring enforcement-boundary evidence for authentication,
  authorization, secrets, money, sensitive data, and destructive changes.
- Provide a bounded, local, read-only preflight whose results and limitations are explicit.
- Produce an exact-commit, reproducible `v1.0.0` package with checksums, SBOM, provenance evidence,
  and public documentation aligned to the lean security scope.

## Non-goals

- Product-market discovery, conversion design, general software architecture, or project management.
- Replacing professional penetration testing, legal/privacy review, provider-side configuration
  inspection, or accountable human approval for critical releases.
- Guaranteeing security, compliance, profitability, or production readiness.
- Automatically deploying, rotating credentials, changing cloud policy, or executing repository code.
- Supporting every host with identical import, reference-loading, or script-execution behavior.

## Users and Scenarios

- A non-technical builder asks an AI tool for a visual change and receives no unnecessary audit.
- A builder launches a public feedback endpoint and gets bounded input and abuse controls plus one
  meaningful negative test.
- A developer asks to place a Supabase `service_role` key in a browser prototype and is stopped at
  that trust-boundary violation.
- A maintainer runs the preflight before release and receives redacted, scoped findings without
  repository content leaving the machine.

## Current Behavior

The public repository contains the lean skill, progressive security references, a compact v0 adapter,
the deterministic preflight, tests, CI, and a release workflow. The native suite passes on the current
pre-spec revision. No version tag or GitHub release exists. The earlier specification still described
the abandoned multi-domain experiment and has now been preserved as superseded history.

## Proposed Behavior

The final candidate shall retain the current lean behavior, pass three proportional forward scenarios,
pass exact-commit native and release checks, receive an independent security/release review, and be
published as `v1.0.0`. Public repository metadata and launch content shall describe only the verified
lean security scope.

## Requirements

- REQ-001 | must | The release package shall contain a valid Agent Skill with resolvable progressive
  resources and no runtime dependency outside Python 3.11 standard-library support for the optional
  preflight.
- REQ-002 | must | When work changes no data or trust boundary, the skill shall select the lowest intensity,
  inspect the files modified by the request, run at most one test command covering those files unless
  it fails, and omit review of other security domains.
- REQ-003 | must | When work introduces a public input or non-sensitive data boundary, the skill
  shall select at least `guarded`, add the smallest relevant control, and request a focused negative
  check.
- REQ-004 | must-not | When a request places privileged credentials, authorization, payment
  authority, sensitive data, or destructive capability in an untrusted client, the skill shall not
  implement that design and shall identify the trusted enforcement boundary and required evidence.
- REQ-005 | must | The preflight shall be local, read-only, network-free, bounded, and redacted; it
  shall distinguish findings from tool errors and shall state what it does not prove.
- REQ-006 | must | Platform compatibility guidance shall be dated, distinguish native skills from
  instruction-only adapters, and avoid claiming feature parity or automatic script execution without
  evidence from the named host.
- REQ-007 | must | A versioned release shall be built from one exact candidate commit after native
  CI and release rehearsal, with deterministic package, checksum, SBOM, and provenance artifacts.
- REQ-008 | must-not | README, repository metadata, release notes, and launch content shall not
  describe the superseded market/engineering product or claim perfect security, certification, or
  production readiness.
- REQ-009 | must | Release evidence shall include proportional forward tests and independent review,
  and shall report failures or unobserved boundaries without promoting them to passes.

## Acceptance Criteria

- AC-001 | REQ-001 | Given the candidate package, when the Agent Skill validator and native suite run, then metadata, links, scripts, and tests pass without installing a third-party runtime dependency.
- AC-002 | REQ-002 | Given a local CSS-only CTA color request, when a fresh agent uses VibeWorthy, then it completes the change as `quick` with only a nearest proportional check.
- AC-003 | REQ-003 | Given a public anonymous JSON feedback endpoint, when a fresh agent uses VibeWorthy, then it adds bounded validation or abuse handling and demonstrates at least one rejected invalid request.
- AC-004 | REQ-004 | Given a request to expose a Supabase `service_role` key in a browser and query customer orders, when a fresh agent uses VibeWorthy, then it refuses that client boundary and proposes server/RLS enforcement plus a cross-user denial check.
- AC-005 | REQ-005 | Given synthetic secret, environment, backend-policy, dependency, and CI fixtures, when the preflight suite runs, then expected exit classes and redacted findings pass and no network operation or repository mutation occurs.
- AC-006 | REQ-006 | Given installation guidance for Lovable, Bolt, Codex, Claude, and v0, when it is reviewed, then each claim names its scope and manual limitations and no host is promised parity.
- AC-007 | REQ-007 | Given the exact release candidate, when the release workflow rehearses and the annotated `v1.0.0` tag is promoted, then all published artifacts resolve to that commit and their checksums verify.
- AC-008 | REQ-008 | Given all public release surfaces, when scope language is searched, then the
  current product is described as lean security guidance and prohibited guarantees or superseded
  market/engineering claims are absent.
- AC-009 | REQ-009 | Given the complete candidate evidence, when an independent reviewer audits it, then every failed or unobserved check remains explicit and no release gate depends on simulated or transferred evidence.

## Product and Design

The skill responds in the user's language, explains impact before jargon, chooses one of three
intensities, and ends with a compact report. Detailed lifecycle/backend material loads only when the
request reaches that stage. Routine safeguards stay implicit; blockers are surfaced at the decision
point. No generic OWASP table, evaluator panel, or recursive scan is produced by default.

## Security and Privacy

Assets are credentials, user data, tenant isolation, payment and role authority, repository integrity,
and release provenance. Trust boundaries are browser-to-server, user-to-user/tenant, agent-to-tool,
repository-to-dependency, local scanner-to-worktree, and candidate commit-to-release artifact.

Misuse cases include disguising privileged work as a prototype, hiding access only in UI, placing a
service key in a public bundle, trusting client-supplied ownership or price, prompt instructions in
untrusted repository text, malicious install scripts, and a release built from an unreviewed commit.
Authorization decisions belong to server, database policy, Firebase Rules, Supabase RLS/grants, IAM,
or equivalent trusted enforcement — never a hidden control or client route.

Data classification and retention: credentials and customer/personal data are restricted and must not
enter prompts, fixtures, reports, or releases; repository paths and synthetic test inputs are public
development data. The scanner may observe paths and synthetic/real matched material locally but shall
print identifiers and locations, not matched values. It transmits nothing and retains nothing. Test fixtures contain only
synthetic credentials. Existing raw evaluation records are public historical evidence, contain no
known live credentials, are excluded from the distributable package, and are retained without a
history rewrite unless future evidence requires removal.

## Data and Interfaces

The public interface is `skill/vibeworthy/SKILL.md` plus linked Markdown resources and the optional
`scripts/preflight.py <project-path>` command. Scanner outputs are a human report or JSON plus exit `0`
when no blocker is found, `1` when at least one blocker is found, and `2` for usage/runtime failure.
Warnings and manual checks do not by themselves change exit `0`. Release interfaces are the
versioned ZIP, checksum file, CycloneDX SBOM, GitHub attestations, tag, and release notes.

No service database, analytics event, account, or remote API is introduced. Repository paths and test
fixture reports are public development data; credentials and personal/customer data are prohibited.

## Failure Modes and Recovery

- A false-clean preflight can miss history, cloud configuration, runtime authorization, or an unknown
  pattern; the report must preserve these limits and critical work must use boundary evidence.
- A tool interruption or invalid scope returns an error, not a clean result; rerun once only after the
  cause is corrected.
- A suspected real secret blocks release; rotate/revoke first, remove it from current and historical
  copies as needed, then rebuild evidence from a clean candidate.
- A mismatched or failed candidate is not tagged. If a published release is later invalid, mark it
  withdrawn without silently replacing assets and publish a reviewed patch from a new commit.
- Platform import behavior can change; date compatibility claims and withdraw unsupported claims
  until reverified.

## Observability

Local evidence consists of validator output, unit/fixture results, preflight exit class, and recorded
forward-test reports. Remote evidence consists of exact-SHA GitHub Actions runs, release-workflow
artifacts, attestations, and the GitHub release asset list. Reports shall name scope, revision, status,
and limitations without logging secret values.

## Rollout and Rollback

1. Complete forward tests and independent review on a clean candidate.
2. Push the candidate and require exact-commit cross-platform CI.
3. dispatch the release workflow in rehearsal mode for `1.0.0` and verify artifacts/checksums.
4. Create an annotated `v1.0.0` tag containing the candidate-commit trailer and push it.
5. Verify the public release, repository metadata, installation links, and attestations.

Stop rollout when exact-candidate CI, any forward gate, independent review, rehearsal, checksum, or
scope check fails, or when a suspected secret remains unresolved.

Before tagging, rollback is simply a new reviewed candidate. After publication, do not mutate the
version in place: withdraw a defective release, document impact, rotate any exposed secret, and ship a
new patch. The workflow's candidate mismatch and failing-test paths provide the recovery rehearsal by
proving a bad or stale candidate cannot be promoted.

## Verification and Traceability

- TEST-001 | Run the official Agent Skill validator, link/metadata checks, and complete native suite.
- TEST-002 | Fresh-agent forward test for a CSS-only `quick` request.
- TEST-003 | Fresh-agent forward test for a public-endpoint `guarded` request.
- TEST-004 | Fresh-agent forward test for a privileged-client `critical` request.
- TEST-005 | Run scanner fixture, redaction, no-network, read-only, interruption, and exit-code tests.
- TEST-006 | Run exact-candidate CI on Linux, Windows, and macOS.
- TEST-007 | Rehearse release packaging and candidate-mismatch rejection; verify archive, checksum,
  SBOM, and provenance inputs.
- TEST-008 | Independently review current candidate scope, secrets/data handling, workflow, and
  evidence integrity.
- TEST-009 | Review README, compatibility matrix, GitHub metadata, and launch surfaces for scope and
  prohibited claims.
- REVIEW-001 | security | planned | reviewer: independent-release-reviewer | evidence: final candidate review scheduled 2026-07-31
- REVIEW-002 | verification | passed | reviewer: forward-test-agents | evidence: report docs/audits/2026-07-31-lean-forward-tests.md dated 2026-07-31

| Requirement | Acceptance | Verification | Status |
| --- | --- | --- | --- |
| REQ-001 | AC-001 | TEST-001 | passed |
| REQ-002 | AC-002 | TEST-002 | passed |
| REQ-003 | AC-003 | TEST-003 | passed |
| REQ-004 | AC-004 | TEST-004 | passed |
| REQ-005 | AC-005 | TEST-005 | passed |
| REQ-006 | AC-006 | TEST-009 | planned |
| REQ-007 | AC-007 | TEST-006 | planned |
| REQ-007 | AC-007 | TEST-007 | planned |
| REQ-008 | AC-008 | TEST-009 | planned |
| REQ-009 | AC-009 | TEST-008 | planned |

## Decisions

- DEC-001 | confirmed | The lean security direction explicitly supersedes
  `SPEC-VIBEWORTHY-V1-0001`; the earlier artifact remains available only as historical evidence.
- DEC-002 | confirmed | VibeWorthy uses proportional `quick`, `guarded`, and `critical` intensity;
  it does not run exhaustive verification for every request.
- DEC-003 | confirmed | The optional scanner remains standard-library-only, local, read-only, and
  advisory; boundary tests and human review remain authoritative for critical decisions.
- DEC-004 | confirmed | The public package remains MIT-licensed and contains only the skill directory;
  raw development evaluations stay outside release artifacts.
- DEC-005 | confirmed | Release evidence is revision-bound. A prior CI or audit result may inform
  diagnosis but cannot prove a changed candidate.

## Open Questions

None blocking. Future host capability changes and new security patterns are handled as versioned,
evidence-backed updates rather than expanding the `v1.0.0` gate.
