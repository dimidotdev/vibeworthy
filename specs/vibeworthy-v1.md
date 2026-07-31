---
spec: SPEC-VIBEWORTHY-V1-0001
title: "VibeWorthy portable market, engineering, and security skill"
status: implemented
profile: critical
mode: deliver
owner: "dimidotdev"
created: 2026-07-30
updated: 2026-07-31
---

# VibeWorthy portable market, engineering, and security skill

## Context and Evidence

- EVD-001 | source: stakeholder request, 2026-07-30 | Non-technical builders using Lovable, Bolt,
  and v0 need one workflow that connects market evidence, engineering discipline, and security
  during prototyping instead of treating them as separate pre-launch cleanups.
- EVD-002 | source: [Lovable skills documentation](https://docs.lovable.dev/features/skills),
  fetched 2026-07-30 | Lovable imports a root or subdirectory `SKILL.md` from public GitHub, applies
  skills automatically or by slash command, and supports bundled files.
- EVD-003 | source: [Bolt skills documentation](https://support.bolt.new/building/skills), fetched
  2026-07-30 | Bolt imports Agent Skills from public GitHub or files at workspace/project scope and
  validates `name` and `description` frontmatter.
- EVD-004 | source: [v0 instructions documentation](https://v0.app/docs/instructions), fetched
  2026-07-30 | v0 exposes account-level reusable Instructions but does not document native import of
  the Agent Skills package; a self-contained instruction adapter is required.
- EVD-005 | source: `heliocosta-dev/revenue-centric-design` commit
  `6fa20cb4f91fa97bce9197be3f78b168784eb772` and its `LICENSE`, inspected 2026-07-30 | The source is
  source-available, requires attribution and preservation of a no-gambling field-of-use restriction,
  and is not OSI-approved; its text cannot be silently merged into an MIT project.
- EVD-006 | source: `mattpocock/skills` commit
  `2ab958093e83e0ec752e6c1c5932da465bf23e0c` and its `LICENSE`, inspected 2026-07-30 | The collection
  is MIT-licensed and demonstrates small composable engineering workflows; attribution is required
  for copied or substantially adapted material.
- EVD-007 | source: [OWASP Top 10:2025](https://owasp.org/Top10/2025/) and
  [ASVS 5.0.0](https://owasp.org/www-project-application-security-verification-standard/), fetched
  2026-07-30 | Current guidance covers access control, misconfiguration, supply chain, cryptography,
  injection, insecure design, authentication, integrity, logging, and exceptional conditions; ASVS
  provides testable verification requirements rather than a certification claim.
- EVD-008 | source: [Firebase API-key guidance](https://firebase.google.com/docs/projects/api-keys),
  [Security Rules](https://firebase.google.com/docs/rules), and
  [App Check](https://firebase.google.com/docs/app-check), fetched 2026-07-30 | Firebase-provisioned
  client API keys are public identifiers when restricted to Firebase APIs; data authorization is
  enforced by Security Rules, while App Check reduces abuse. Service-account private keys remain
  secrets.
- EVD-009 | source: [Supabase API-key guidance](https://supabase.com/docs/guides/api/api-keys) and
  [RLS guidance](https://supabase.com/docs/guides/database/postgres/row-level-security), fetched
  2026-07-30 | Publishable/legacy anon keys belong in public clients only when authorization is
  enforced; secret and legacy `service_role` keys bypass RLS and must never reach a public client.
- EVD-010 | source: [GitHub secret scanning](https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning),
  fetched 2026-07-30 | Secret scanning covers Git history, while push protection and local checks
  reduce the chance of adding a credential; removing a file in a later commit does not erase prior
  exposure.
- EVD-011 | source: GitHub repository search, 2026-07-30 | No repository named `vibeworthy` was
  returned; this is a collision check, not trademark clearance.
- EVD-012 | source: `/home/dimi/projetos/dimi.dev.br/docs/editorial/` and publisher routes, inspected
  2026-07-30 | The site already supports localized, revisioned editorial content and project posts,
  so publication requires content and D1 operations but no CMS redesign.
- EVD-013 | source: [Firebase Studio responsible-AI guidance](https://firebase.google.com/docs/studio/get-started-ai)
  and [GitHub Copilot agent responsible-use guidance](https://docs.github.com/en/copilot/responsible-use/agents),
  fetched 2026-07-30 | Providers instruct users to validate generated output, avoid entering PII or
  user data, review commands and MCP access, and not treat untested generated code as production-safe.
- EVD-014 | source: independent security review `/root/security_research`, 2026-07-30 | The initial
  specification failed because it lacked agent-authority and privacy gates, used a narrow BaaS
  authorization test, underspecified supply-chain/exception handling, and overstated v0 equivalence.
- ASM-001 | Python 3.11 is a reasonable optional local/CI baseline for the deterministic preflight
  scanner. | validation: execute its tests on Linux, Windows, and macOS in CI.
- ASM-002 | Non-technical users benefit more from a short staged decision summary than from raw
  security taxonomy. | validation: forward-test with ambiguous prototype, Firebase, and paid-app
  scenarios and inspect whether the output gives concrete next actions without hiding blockers.

## Problem

AI app builders reduce implementation friction but do not establish demand, define a trustworthy
architecture, or prove that authorization and secrets are safe. A prototype can look complete while
solving an unvalidated problem, accumulating an unmaintainable implementation, committing secrets,
or exposing cross-user data. Existing product, engineering, and security skills are valuable but
separate, differently licensed, and not uniformly portable across Lovable, Bolt, v0, Codex, and
Claude. Builders need one honest orchestration layer that scales its questions and gates with risk.

## Outcomes

- Publish an original MIT-licensed Agent Skill named `vibeworthy` that Lovable, Bolt, Codex, and
  compatible agents can consume without proprietary runtime dependencies.
- Give v0 users a compact custom Instruction covering the non-negotiable stop rules, with an explicit
  matrix showing which full-skill references and scripts remain manual or unavailable.
- Move each request through market evidence, a bounded build contract, small implementation slices,
  and release evidence, using plain language and stopping on unresolved high-impact risk.
- Detect common credential, environment-file, privileged client-key, permissive Firebase-rule, and
  dependency-hygiene mistakes locally without transmitting repository content.
- Publish a fact-checked Portuguese article, with English and Spanish localizations, that teaches the
  boundary between prototyping speed and production evidence and links to the public project.

## Non-goals

- Certifying software as secure, compliant, profitable, production-ready, or free of vulnerabilities.
- Replacing threat modeling, a professional penetration test, legal/privacy review, or human code
  review for high-impact systems.
- Copying or relicensing the Revenue-Centric Design corpus or Matt Pocock's skill text.
- Building another app generator, hosted scanner, autonomous deployment service, or large ruleset
  marketplace.
- Supporting gambling, betting, casino, loot-box, or other real-money games-of-chance products.
- Redesigning the dimi.dev.br CMS or changing its authentication and publication model.

## Users and Scenarios

- A non-technical founder asks Lovable to build an MVP and needs the agent to test the user/problem
  hypothesis before adding features.
- A Bolt user connects Supabase and needs a concrete rule that blocks launch until RLS and cross-user
  denial are demonstrated.
- A v0 user enables the compact Instruction and needs market, quality, and security questions despite
  v0 not documenting native Agent Skill import.
- A developer inherits an AI-generated Firebase app and needs a local preflight that distinguishes a
  public Firebase API key from a leaked service-account key and flags permissive rules.
- A team wants to prototype locally with fake data while recording what must change before a public
  or production release.

## Current Behavior

A complete VibeWorthy implementation now exists in the public canonical GitHub repository, including
the Agent Skill, compact platform adapters, local preflight scanner, tests, CI and release workflows,
license/provenance records, and release documentation. Candidate
`39fb6039036cc673c05d7cf3e71408c00b57de27` passed cross-platform CI, exact-SHA technical review,
and the release rehearsal, but was rejected at 20/21 by the frozen forward suite because one response
contradicted a captured scanner report and exit code. Its predecessor `3f840d1` was rejected at 18/21
for invented launcher evidence and an omitted MCP audit control. Both raw suites are preserved as
invalid evidence and cannot support release. The corrective worktree is not yet a frozen candidate;
no `v1.0.0` tag or durable release exists. The localized dimi.dev.br article/project is drafted but
is not published in production D1 or deployed. The source skills still solve adjacent parts under
different licenses and invocation models, while Lovable and Bolt can import Agent Skills and v0
currently exposes reusable Instructions.

## Proposed Behavior

VibeWorthy shall classify a request into `explore`, `prototype`, or `ship`. Any public endpoint, real
user or customer data, authentication, payment, privileged integration, destructive action, or other
external side effect automatically invokes `ship` safety gates even if the user calls it a prototype.
It shall then use a four-stage loop:

1. **Worth building:** identify the user, costly job, current alternative, evidence, promise, channel,
   smallest valuable experiment, and observable success/stop signal.
2. **Worth maintaining:** inspect the actual repository, compare consequential options, define the
   smallest vertical slice, preserve accessibility and recovery behavior, and require feedback loops.
3. **Worth trusting:** identify assets and trust boundaries, apply relevant OWASP/ASVS controls, keep
   privileged secrets server-side, and prove per-object authorization with negative tests.
4. **Worth shipping:** run deterministic and project-native checks, separate automated evidence from
   manual checks, and return `GO`, `CONDITIONAL`, or `NO-GO` without manufacturing certainty.

The full Agent Skill shall use progressive disclosure for product, engineering, security, platform,
and release detail. A dependency-free preflight scanner shall supplement rather than replace native
linters, tests, secret scanning, and human review. A compact v0 adapter shall preserve the stop rules
while linking to the full references for manual use.

## Requirements

- REQ-001 | must | The project shall provide a valid `vibeworthy` Agent Skill with only `name` and
  `description` frontmatter, a body below 500 lines, one-level reference links, and generated Codex UI
  metadata whose default prompt explicitly invokes `$vibeworthy`.
- REQ-002 | must | When a user requests a new product, feature, prototype, or launch, the skill shall
  classify it as `explore`, `prototype`, or `ship`; any public endpoint, real user/customer data,
  authentication, payment, privileged integration, destructive action, or external side effect shall
  automatically activate `ship` safety gates regardless of the label used by the requester.
- REQ-003 | must | Before implementation, the skill shall record the target user and moment, current
  alternative, evidence versus assumption, value promise, acquisition or distribution path, smallest
  valuable slice, observable success signal, and stop condition without inventing research or metrics.
- REQ-004 | must | Before material code changes, the skill shall inspect the actual project, state the
  build contract and non-goals, compare at least two options for a consequential or hard-to-reverse
  decision, and implement in independently verifiable vertical slices.
- REQ-005 | must | For user-facing work, the skill shall cover semantic accessibility, keyboard and
  mobile completion, loading/empty/error/recovery states, content extremes, performance relevant to
  the conversion moment, and non-deceptive copy or interaction patterns.
- REQ-006 | must | For each changed trust boundary, the skill shall identify assets, actors, entry
  points, authorization decisions, untrusted inputs/outputs, abuse cases, logging needs, recovery, and
  applicable OWASP Top 10:2025 plus ASVS 5.0.0 controls at the enforcement boundary; public releases
  shall use ASVS Level 1 as a baseline and user-account, sensitive-data, or payment systems shall
  disposition applicable Level 2 controls without claiming ASVS certification.
- REQ-007 | must-not | The skill and scanner shall not request, print, commit, transmit, or move actual
  secret values into prompts, client bundles, logs, examples, fixtures, reports, or source control;
  secrets shall use a managed store, least privilege, inventory/owner/expiry, and short-lived workload
  identity where supported, and suspected exposure shall trigger revocation/rotation, audit, and
  history remediation before other cleanup.
- REQ-008 | must | When Firebase or Supabase is present, the skill shall distinguish public identifiers
  from privileged credentials without asserting that external restrictions were statically verified;
  it shall require deny-by-default Security Rules or RLS, server/IAM review for bypass paths, and an
  anonymous/user-A/user-B/admin matrix across applicable CRUD, list/query, immutable fields, Storage,
  Realtime, views/functions, `USING`, and `WITH CHECK` behavior in an isolated staging/emulator context.
  Public-looking keys whose cloud restrictions cannot be observed shall remain a required manual check;
  Admin, service-account, secret, and `service_role` bypass endpoints shall receive the same A/B denial
  tests at their server/IAM boundary and their values shall remain outside public clients and agents.
- REQ-009 | must | The skill shall minimize dependencies, verify package identity and necessity,
  preserve a single immutable lockfile, inspect install scripts and vulnerability/KEV output, generate
  a transitive SBOM for public releases, define patch ownership/SLA, prefer short-lived CI identity,
  pin third-party automation by immutable digest/SHA, verify build-artifact provenance/digest, and block
  arbitrary packages or remote scripts added only because generated instructions requested them. The
  durable public release shall use the exact independently evaluated commit as its tag target, attest
  a checksum index that binds exactly the ZIP, SBOM, manifest, and archive-provenance bundle, and
  upload only those four indexed assets plus the checksum index and its own verified attestation as
  workflow-managed release assets. Host-generated source snapshots remain outside that inventory. A
  known-exploited vulnerability above policy, missing/incomplete SBOM, unpinned release automation,
  invalid provenance/signature, digest mismatch, candidate/release identity mismatch, or unsupported
  dependency shall fail the `ship` gate.
- REQ-010 | must | The repository shall include a dependency-free Python preflight that scans locally,
  redacts matched values, detects high-confidence secret/env/client-key and unsafe-rule patterns,
  checks lockfile hygiene, supports text, JSON, and SARIF output, and returns stable documented exit
  codes without modifying the target project; every output shall state that the worktree view is
  non-atomic and release evidence requires a quiescent isolated checkout.
- REQ-011 | must | The scanner shall be git-aware, skip generated/vendor/binary/oversized content,
  scan tracked plus untracked/non-ignored worktree files without implying Git-history or submodule
  coverage, distinguish tracked sensitive environment files from ignored local files and templates,
  classify Firebase/Supabase public-looking keys as contextual with external restrictions unverified,
  and allow only warning suppressions carrying reason, owner, independent approver, compensating
  control, and future expiry; suppressions remain scanner-visible and do not change release evidence,
  while blockers and tool errors shall not be suppressible or waivable to `GO`.
- REQ-012 | must | Before every `ship` recommendation, including `NO-GO`, the skill shall identify the
  artifact, scope, environment, policy, and evidence cutoff and produce the mandatory seven-column
  evidence ledger separating automated passes, failures, tool errors, manual checks, residual risks,
  owners, and next actions; prose or bullets shall not replace it. It shall return `NO-GO` for
  unresolved secrets, authorization, destructive-data, payment, critical
  dependency, tool-error, or required-manual-check findings; `CONDITIONAL` shall permit only noncritical
  exceptions with reason, independent approver, compensating control, owner, and future expiry, while
  `GO` shall mean every required gate passed in the named artifact, scope, environment, and policy.
- REQ-013 | must-not | The skill, scanner, documentation, and article shall not claim perfect security,
  OWASP compliance, profitability, or production readiness from checklist completion or scanner output.
- REQ-014 | must | The repository shall document a dated compatibility matrix for Lovable, Bolt,
  Codex, Claude, and v0 across import, automatic invocation, references, scripts, and manual steps;
  installation shall pin an immutable commit SHA or verified package digest where supported, disclose
  that branches and tags can move, record the reviewed SHA when UI import is branch-only, name
  unsupported behavior explicitly, and require review before enabling.
- REQ-015 | must | The repository shall use an OSI-approved license for original work, retain factual
  source/provenance notes, express the no-gambling boundary as voluntary agent behavior outside the MIT
  grant, include no text derived from the restricted Revenue-Centric Design corpus, and include the
  applicable MIT notice before any substantial copied/adapted MIT material; v1 shall remain original.
- REQ-016 | must | The public release shall include a localized dimi.dev.br project/article entry whose
  security and compatibility claims match tested behavior, uses primary-source links, and provides the
  exact GitHub import path and v0 limitation.
- REQ-017 | must-not | The skill shall not send PII, customer/user data, confidential source, production
  credentials, or unrestricted repository context to an agent without explicit classification and
  authority; it shall default to synthetic/minimized data, sandbox and least privilege, review MCP and
  network egress, require provider retention/training/deletion/region terms to be explicitly approved
  and compatible with the data policy before any sensitive transmission, and require human approval
  before production access, deploy, external communication, billing, destructive commands, or durable
  external-state changes.
- REQ-018 | must | For systems handling personal data, the skill shall record purpose, lawful-review
  trigger, classification, minimization, processors/regions, retention, export/deletion, backup
  deletion, sensitive/minor data, and incident owner before `ship`, escalating legal/privacy review
  instead of inventing consent or compliance conclusions.
- REQ-019 | must | For hosted backends or BaaS, the `ship` gate shall cover abuse/rate limits, quotas and
  spend ceilings, backup and tested restore, migration/rollback or forward recovery, bounded retries/
  timeouts, log redaction, alert ownership, and a documented kill switch or containment action.
- REQ-020 | must | Any AI-generated or AI-modified Security Rules, RLS policies, IAM, migrations,
  cryptography, authentication/authorization, payment, or destructive-data logic shall require a named
  human review plus independent negative test evidence before `ship`; generated code or generated tests
  shall never be their own sole oracle.
- REQ-021 | must | Forward tests shall record the exact skill commit, host/platform, model and version
  where exposed, full prompt, isolated starting artifact, at least three runs for nondeterministic
  behavior, required/prohibited rubric items, raw output, reviewer result, and the revision caused by a
  failure so another maintainer can reproduce the conclusion.

## Acceptance Criteria

- AC-001 | REQ-001 | Given the packaged skill, when validation runs, then its shape and metadata pass.
- AC-002 | REQ-002 | Given prototype and public-release prompts, when forward-tested, then their risk
  depth and release gates differ, and a “prototype” with auth or real data is elevated to `ship` gates.
- AC-003 | REQ-003 | Given an ambiguous “build an app” request, when the skill responds, then it labels
  known evidence, assumptions, the smallest experiment, success signal, and stop condition without
  fabricating user interviews or conversion data.
- AC-004 | REQ-004 | Given a consequential design choice, when the skill runs, then two options and a
  decision appear with repository evidence, the chosen tradeoff, non-goals, and a vertical
  verification seam before implementation.
- AC-005 | REQ-005 | Given a conversion flow, when reviewed, then every required state has observable
  acceptance and no dark pattern is recommended, including keyboard and 320-pixel behavior.
- AC-006 | REQ-006 | Given auth, user data, and a callback, when threat framing runs, then concrete
  controls and tests result. The output names applicable Top 10:2025/ASVS 5.0.0 IDs and level while
  per-object authorization, malformed/replayed input, output encoding, abuse, logging, and failure
  recovery map to tests rather than a generic “OWASP checked” statement.
- AC-007 | REQ-007 | Given synthetic secrets, when all output formats run, then no matched value is
  emitted, including after source escaping, Unicode normalization, percent decoding, JSON/SARIF
  serialization, or URI rendering of a report path. Reports identify file, line, rule, and
  remediation; a path whose safe projection cannot be proven is replaced by an opaque location.
  Release review also requires vault, least-privilege, inventory/owner/expiry, short-lived identity
  where available, tested rotation/revocation, audit, and history remediation evidence before
  closing suspected exposure.
- AC-008 | REQ-008 | Given public and privileged backend keys, when reviewed, then unresolved trust
  evidence blocks shipping. Public-looking Firebase keys remain “external restriction unverified” and
  produce `NO-GO` until manually confirmed; service-account/`service_role` values and missing anonymous/
  A/B/admin denial evidence at public and privileged server/IAM boundaries block release across every
  applicable storage/query/function boundary. The supplemental scanner blocks unconditional Firebase
  grants plus constant-true grants it can prove through its bounded literal, list/membership,
  comparison, boolean, ternary, and arithmetic grammar; dynamic or unsupported expressions remain
  outside static proof and cannot supply release evidence. Executable PostgreSQL migration bodies
  that disable RLS are blockers, including bounded literal adjacency/concatenation, grouping, and
  identity text casts; comments and inert string/data bodies remain non-findings.
- AC-009 | REQ-009 | Given lockfile conflict and an install script, when reviewed, then both issues are
  visible and installation is deferred until identity, necessity, permissions, and source are
  confirmed; a public-release review additionally records SBOM, vulnerability/KEV, pinning, patch SLA,
  provenance/signature, digest, exact evaluated-commit/annotated-tag identity, an attested checksum
  index over four named assets, the exact six-file workflow-managed durable release inventory, and CI
  identity/branch-control evidence, and every enumerated failure condition produces `NO-GO`. Remote
  fetch-to-execution flow remains visible through bounded shell aliases, functions, descriptors,
  redirections, heredocs, wrappers, compound commands, native literal output names, and common
  literal file consumers or transforms. Dynamic or unsupported relevant flow fails closed at a
  potential consumer or transform while a download-only or inspection-only path remains a
  non-finding.
- AC-010 | REQ-010 | Given scanner fixtures, when run cross-platform, then output and exit codes are
  deterministic, schemas parse, the fixtures remain byte-identical, and text/JSON/SARIF expose the
  non-atomic snapshot limitation.
- AC-011 | REQ-011 | Given included and excluded fixtures, when scanned, then only intended findings
  appear. Tracked `.env`, ignored `.env`, `.env.example`, binary, build, vendor, large, restricted
  Firebase client-key, and Supabase publishable-key fixtures prove scope/classification; output states
  that history/submodules were not scanned, and blocker suppression or warning suppression without
  reason, owner, independent approver, compensating control, and future expiry fails.
- AC-012 | REQ-012 | Given unresolved cross-user authorization, when launch review completes, then the
  result is `NO-GO`, the release identity and exact seven-column ledger remain visible, the clean UI
  pass remains distinct, and every failure, tool error, manual check, or residual risk has its own
  owner/action row; no tool error or required manual check can result in `GO`.
- AC-013 | REQ-013 | Given release text, when claim review runs, then unsupported absolute claims are
  absent, including security, compliance, profitability, and readiness language.
- AC-014 | REQ-014 | Given the repository, when install guidance is checked, then every claimed path
  and capability matches current official docs. The matrix separates import, invocation, references,
  scripts, and manual work; v0 is a reduced manual Instruction, immutable installs use a commit SHA or
  digest, and branch/tag-only imports record mutability plus the reviewed SHA.
- AC-015 | REQ-015 | Given a source and license audit, when release files are reviewed, then original
  files are MIT-licensed, provenance and voluntary usage boundaries are explicit, and no restricted
  third-party corpus or unattributed substantial MIT copy is present.
- AC-016 | REQ-016 | Given three production locales, when smoke-tested, then each exposes the intended
  content and links across routes, feeds, the sitemap, project filter, canonical metadata, source/import
  links, and qualified security/compatibility claims.
- AC-017 | REQ-017 | Given sensitive inputs, when agent access is requested, then authority is bounded.
  With PII, a production credential, an untrusted MCP, and a deploy, the skill substitutes synthetic/
  minimized inputs, refuses credential transfer, reviews authority/egress, blocks sensitive transmission
  until retention/training/deletion/region terms are approved and compatible, and pauses before external
  or production action for explicit human approval.
- AC-018 | REQ-018 | Given an app collecting child location data, when classified for `ship`, then the
  result remains `NO-GO` until purpose, legal/privacy review, processor/region, minimization, retention,
  export/deletion, backup deletion, incident ownership, and sensitive/minor-data controls are resolved.
- AC-019 | REQ-019 | Given a hosted BaaS app, when launch review runs, then missing spend/rate limits,
  tested restore, migration recovery, bounded failure behavior, redacted alerts, or containment owner
  remains visible and prevents `GO`.
- AC-020 | REQ-020 | Given AI-generated critical code, when reviewed, then humans remain the oracle.
  AI-generated RLS/migrations and AI-generated tests remain `NO-GO` until named human review and an
  independent negative test at the enforcement boundary pass.
- AC-021 | REQ-021 | Given each forward-test scenario, when its evidence is reviewed, then the record
  includes commit, platform/model/version, prompt, clean starting artifact, three runs, required and
  prohibited rubric, raw outputs, reviewer decision, and any resulting skill revision.

## Product and Design

- Primary flow: start with the user's intended outcome, select `explore`, `prototype`, or `ship`, show
  only the next highest-leverage question/gate, and end with a decision plus concrete next action.
- Empty/loading/error/recovery: missing evidence becomes a labeled assumption and experiment; missing
  tools become `manual check`, not pass; scan errors return a distinct exit code and remediation; an
  interrupted workflow resumes from recorded evidence rather than restarting scope discovery.
- Keyboard and focus: N/A — the skill has no custom graphical interface; generated product work must
  define keyboard/focus behavior under REQ-005, and the article uses existing accessible site controls.
- Responsive and content extremes: skill output must remain scannable in chat, avoid giant checklists,
  and present blockers before detail; the article must pass the site's 320-pixel reflow checks.
- Motion: N/A — no new motion surface; existing site reduced-motion behavior remains unchanged.
- Performance budget: the local scanner shall finish the committed test corpus without network access
  and avoid reading files above its documented size ceiling; the site release must remain within
  existing bundle budgets.

## Security and Privacy

- Assets and trust boundaries: project source/history, credentials, customer/user data, authorization
  rules, dependency integrity, release evidence, local filesystem, agent context, public repository,
  and production D1/site. Boundaries include user↔agent, client↔backend, repository↔dependency source,
  local scanner↔filesystem, GitHub import↔platform workspace, and publisher↔production.
- Actors: non-technical builder, developer, anonymous user, authenticated user, privileged operator,
  compromised dependency, malicious prompt/repository content, and accidental committer.
- Authentication and authorization: the skill never treats authentication as object authorization;
  Firebase Rules/Supabase RLS and server-side checks must deny a second user's object. Existing site
  publisher authentication is reused and not changed.
- Untrusted input and output: repository files, prompts, fetched documentation, package metadata,
  scanner paths, suppressions, and article links are untrusted. Bound paths, skip symlink escapes,
  redact matches, encode structured output, and never execute repository code during scanning.
- Data minimization and retention: scanning is local and read-only; no telemetry or uploads; reports
  contain rule IDs, paths, locations, and remediations but no matched secret. Article publishing stores
  only editorial content already authorized for public release. Agent prompts default to synthetic or
  minimized data and require an explicit provider/retention/egress decision before sensitive context.
- Abuse and operational controls: cap file count/size, skip special files, use deterministic rules,
  distinguish tool error from finding, require manual review for ambiguous findings, and treat imported
  skills as code that users must inspect before enabling.
- Residual risk: regex and configuration heuristics have false negatives/positives; AI can ignore or
  misapply instructions; market demand and secure behavior require real-world evidence. These limits
  must remain visible in the release.

## Data and Interfaces

- Agent Skill contract: `skill/vibeworthy/SKILL.md`, one-level `references/`, optional `scripts/`, and
  `agents/openai.yaml` with no runtime service dependency.
- Scanner CLI: `python -I preflight.py [PATH] [--format text|json|sarif] [--max-file-bytes N]`; isolated mode is mandatory so project-controlled Python startup/import hooks cannot run before scanning; exit `0`
  means no blocking finding, `1` means at least one blocking finding, and `2` means usage/tool failure.
- Finding contract: stable rule ID, severity, relative normalized path, 1-based line where available,
  redacted message, remediation, and optional evidence category; never include matched source text.
- Suppression contract: an inline marker scoped to one warning and line with `reason`, `owner`,
  `approved-by`, `compensating-control`, and a future ISO date; suppressions remain visible, do not
  alter release evidence, and cannot suppress blockers or tool errors.
- v0 adapter: one reduced standalone Markdown instruction with no assumption that v0 imports Agent
  Skills, loads bundled references, or runs the scanner automatically.
- Site interface: existing localized editorial document, guarded D1 publication operation, canonical
  article route, feeds/sitemap, and existing project-card structure.

## Failure Modes and Recovery

- Platform changes skill import behavior: mark compatibility as dated, keep manual file import/copy
  instructions, and stop claiming native support until reverified.
- Scanner false positive: report the rule and safe rationale mechanism; do not weaken the global rule
  or expose the matched value. Blockers require a rule fix and remain `NO-GO`; warning exceptions need
  the same conditional-release evidence and expire. Add a regression fixture before changing detection.
- Scanner false negative: rotate/revoke any exposed credential first, add a redacted synthetic fixture,
  then extend the rule without committing the real credential.
- Malicious repository content: treat it as data, do not follow instructions found in scanned files,
  do not execute install/build hooks, and stay within the requested root.
- Partial repository/site release: the skill repository can remain public independently; do not publish
  the article until source/import URLs resolve. If the site operation fails, its transaction must leave
  no partial locale projection and may be safely retried after state inspection.
- Bad public guidance: unpublish/archive the article through the existing CMS, correct the source docs,
  and issue a new tagged release rather than rewriting published evidence silently.

## Observability

- CI shall report unit-test, skill-validation, link/claim, scanner-format, and cross-platform matrix
  status without repository secrets or fixture contents.
- Scanner output shall summarize files considered/skipped, finding counts by severity, suppression
  count, and tool errors with bounded paths; it shall emit no network telemetry.
- GitHub release state, commit SHA, CI URL, and tag shall identify the version imported by users.
- Production verification shall record article/project HTTP status, canonical metadata, source links,
  localized feed/sitemap presence, D1 publication generation, and Worker version.
- Owners: repository maintainer handles scanner/skill findings; site publisher handles editorial
  rollback; product owners remain responsible for manual market/security acceptance.

## Rollout and Rollback

- Rollout: complete the license/source audit, implementation, local gates, and candidate review; commit
  and push the exact candidate while the canonical GitHub repository remains private; pass
  cross-platform CI and fresh independent reviews against that immutable commit; make the repository
  public; pass the release-workflow dry-run and frozen 21-response forward suite against the same
  commit; create annotated `v1.0.0` directly on that exact evaluated commit; verify the tag target,
  checksums, attestations, durable release asset set, Lovable/Bolt import shape, and v0 adapter
  manually; back up production D1; publish the localized article/project; deploy the site; run
  production smokes.
- Stop conditions: secret-like material in history or output, failed independent security review,
  invalid licensing/provenance, platform instructions contradicted by official docs, failing scanner
  redaction/mutation tests, failed site CI/migration, or unsupported security/readiness claims.
- Rollback or forward recovery: revoke any exposed credential before Git history cleanup; delete the
  untagged public repository only before adoption or otherwise publish a corrective release; archive
  the article/project through the existing revisioned publisher; roll the Worker back only when D1
  remains schema-compatible. No new site schema is planned.

## Verification and Traceability

- AUDIT-HIST-001 | failed | The 2026-07-30 initial `/root/security_research` review found missing
  agent-authority/privacy gates, insufficient BaaS authorization and supply-chain coverage, unsafe
  exception semantics, licensing ambiguity, and overstated v0 parity. EVD-014 and the follow-up review
  preserve its remediation rather than relabeling that failed review as a pass.
- REVIEW-002 | security | passed | reviewer: `/root/security_research` | evidence: 2026-07-30
  follow-up adversarial review confirmed both BaaS key-restriction enforcement and sensitive-data
  provider-term gates are explicit, blocking, and traceably tested; all prior substantive findings are
  resolved.
- AUDIT-HIST-002 | failed | The 2026-07-30 `/root/package_audit` and `/root/repo_docs` adversarial
  reviews of candidates `b2e73a5`, `d6827f4`, `218faf6`,
  `a9fa98f`, and `4c4cf61` found and reproduced hook execution risk, report/path disclosure, TOCTOU and
  suppression ambiguity, parser denial of service, Git pathspec omission, shell/Firebase evasions,
  false blockers, and inconsistent evidence hashes. Every rejected candidate remains outside the
  release score; each reproducible issue received a synthetic regression before the next candidate.
- AUDIT-HIST-003 | failed | The `/root/article_review` pre-audit of `4c4cf61` found that templates
  could weaken canonical activation, decision, state, checkout,
  callback, MCP, and child-location requirements. The templates and directly linked references were
  aligned before generating another forward-test candidate.
- AUDIT-HIST-004 | failed | The 2026-07-30 scanner adversarial review rejected candidate `cf2e5d8`
  for redaction, parser, budget, pipeline, release, and filesystem-boundary gaps. Candidate `c0fad57`
  closed those findings, but cross-platform CI exposed noncanonical race fixtures and the follow-up
  root-boundary review found a scan-root establishment race plus unhandled Windows junctions. Both
  candidates remain excluded from release scoring; the next exact candidate requires fresh review.
- AUDIT-HIST-005 | failed | A second 2026-07-30 root-boundary review rejected the claim that intermittent
  path identity checks close every TOCTOU window: a hostile local writer can swap and restore a tree
  entirely between samples. DEC-012 narrows the portable scanner's assurance boundary, makes the
  non-atomic view machine-visible, and requires a quiescent isolated checkout for release evidence.
- AUDIT-HIST-006 | failed | The 2026-07-30 independent scanner audit rejected candidate
  `8fbce1329355f428dcf451d2e29431f5a1f87f04` after
  reproducing a redaction-sentinel path disclosure, untrusted Git execution through a PATH symlink,
  shell-wrapper and npm-lifecycle evasions, content-skip loss of tracked `.env` classification, an
  ASCII-output failure, incomplete Firebase tautology detection, and semantically empty suppression
  identities. The candidate remains excluded from release scoring; each case requires a synthetic
  regression on the next exact candidate. Evidence: `docs/audits/2026-07-30-candidate-8fbce132.md`.
- AUDIT-HIST-007 | failed | The 2026-07-30 independent behavior audit rejected candidate
  `8fbce1329355f428dcf451d2e29431f5a1f87f04`
  because six fresh hostile release prompts produced the correct `NO-GO` but omitted REQ-012's
  mandatory evidence ledger, identity, owner, or next-action fields. Correct blocking without the
  auditable decision record does not count as a pass; the next candidate requires fresh probes.
  Evidence: `docs/audits/2026-07-30-candidate-8fbce132.md`; raw outputs were not retained or scored.
- AUDIT-HIST-008 | failed | The 2026-07-30 independent package audit rejected candidate
  `8fbce1329355f428dcf451d2e29431f5a1f87f04`
  because it allowed a descendant release commit, ran inline Python without isolated imports in an
  OIDC job, attested only the ZIP instead of the checksum-bound asset set, and produced only an
  expiring workflow artifact rather than a durable tag-gated GitHub Release. DEC-013 records the
  stricter evaluated-commit identity rule; the next candidate requires a new package audit and actual
  release evidence before publication. Evidence: `docs/audits/2026-07-30-candidate-8fbce132.md`.
- AUDIT-HIST-009 | failed | Cross-platform CI rejected candidate
  `e1b134f3309fdd696ead02dcd256fedc089238f9`: macOS executed synthetic Git through a
  worktree-originated PATH symlink, Windows failed to reject the equivalent junction, and the Windows
  SQL fixture exceeded its performance budget. Ubuntu passed, but a partial matrix is not release
  evidence. Evidence: `docs/audits/2026-07-30-candidate-e1b134f.md` and the immutable
  [CI run](https://github.com/dimidotdev/vibeworthy/actions/runs/30588227283).
- AUDIT-HIST-010 | failed | The independent scanner audit of candidate
  `e1b134f3309fdd696ead02dcd256fedc089238f9` reproduced repository-controlled Git and Python
  startup execution; overlapping and canonically equivalent path disclosures; wrapper, control-flow,
  redirection, function, and substitution evasions; incomplete Firebase tautologies and adversarial
  runtime; an unsafe path-redaction memory budget; semantically empty suppression metadata; and
  incorrect npm evidence locations. Every class requires a regression and a fresh audit on the next
  exact commit. Evidence: `docs/audits/2026-07-30-candidate-e1b134f.md`.
- AUDIT-HIST-011 | passed | The candidate-bound behavior audit of
  `e1b134f3309fdd696ead02dcd256fedc089238f9` passed 12 full-skill/reduced-v0 decisions,
  including REQ-012 identity, ledger, ownership, next-action, authority, and `NO-GO` requirements.
  Because the candidate failed elsewhere, this historical pass is non-transferable and is not part of
  the final 21-response suite. Evidence: `docs/audits/2026-07-30-candidate-e1b134f.md`; temporary raw
  outputs were not retained or scored.
- AUDIT-HIST-012 | failed | The independent package audit of candidate
  `e1b134f3309fdd696ead02dcd256fedc089238f9` accepted its package and release design but rejected
  the failed CI matrix, credential-persisting CI checkout, misleading prerelease rehearsal example,
  and missing external `github-release` environment/tag policy and real publication evidence. The
  next exact candidate requires fresh package review; external promotion controls remain a pre-tag
  gate. Evidence: `docs/audits/2026-07-30-candidate-e1b134f.md`.
- AUDIT-HIST-013 | failed | The independent scanner audit rejected candidate
  `c44f1d4561630c8a70ed949c7e995c1d726b1681` despite its green cross-platform CI matrix. It
  reproduced bidirectional percent-encoding path disclosures, PostgreSQL wildcard RLS and Firebase
  literal-tautology misses, lexical shell alias/function and dynamic-interpreter evasions, incorrect
  multiple-heredoc ownership, and acceptance of non-standard JSON constants. The candidate remains
  excluded from release and forward scoring. Evidence:
  `docs/audits/2026-07-30-candidate-c44f1d4.md`.
- AUDIT-HIST-014 | passed | The candidate-bound behavior audit of
  `c44f1d4561630c8a70ed949c7e995c1d726b1681` passed 12 full-skill/reduced-v0 decisions with the
  required identity, exact seven-column ledger, ownership, next actions, authority boundary, and
  `NO-GO`. This historical pass is non-transferable and is not part of the final 21-response suite.
  Evidence: `docs/audits/2026-07-30-candidate-c44f1d4.md`.
- AUDIT-HIST-015 | passed | The candidate-bound package audit of
  `c44f1d4561630c8a70ed949c7e995c1d726b1681` accepted CI, package identity, deterministic assets,
  SBOM/checksum inventory, workflow hardening, and external release controls in isolated simulation.
  No real OIDC rehearsal, tag, attestation, public import, or durable release was performed. This
  historical pass is non-transferable. Evidence: `docs/audits/2026-07-30-candidate-c44f1d4.md`.
- AUDIT-HIST-016 | failed | The frozen 21-response suite rejected candidate
  `39fb6039036cc673c05d7cf3e71408c00b57de27` at 20/21. F05 run 1 claimed that a workspace scanner
  produced no report or exit code although its completed event record contained a structured
  `tool.file-race` report and exit `2`. A later narrow pass did not erase that contradiction. The
  other 20 passes are non-transferable; the next exact candidate requires a fresh 21/21 suite.
  Evidence: `tests/forward/invalid-evidence.md` and `tests/forward/raw-invalid/39fb603/`.
- REVIEW-005 | security | planned | reviewer: pending independent reviewer | evidence: fresh
  adversarial audit against the exact next candidate; require no material findings before forward
  evaluation.
- REVIEW-006 | verification | planned | reviewer: pending independent evaluator | evidence: frozen
  21-response forward suite against the exact reviewed skill candidate; require 21/21 before release.
- TEST-001 | planned | Run official quick validation plus repository-specific frontmatter, reference,
  line-budget, and `openai.yaml` assertions.
- TEST-002 | planned | Forward-test prototype versus paid-public-release prompts in isolated agents.
- TEST-003 | planned | Forward-test an ambiguous product request and inspect evidence/assumption and
  market-experiment output.
- TEST-004 | planned | Forward-test an existing-codebase design decision and inspect repository/options/
  vertical-slice evidence.
- TEST-005 | planned | Review a conversion-flow fixture for accessibility, states, mobile, performance,
  and deceptive-pattern handling.
- TEST-006 | planned | Forward-test an auth/data/callback threat scenario and inspect enforcement-boundary
  and negative-test output.
- TEST-007 | planned | Unit-test redaction across text, JSON, and SARIF secret findings and rotation
  guidance; behavior-test the complete vault/least-privilege/inventory/expiry/identity/rotation/audit/
  history evidence gate.
- TEST-008 | planned | Unit/behavior-test Firebase and Supabase public versus privileged credentials,
  unresolved external key restrictions, permissive rules, RLS, public and privileged endpoints, full
  actor matrices, and launch blocking.
- TEST-009 | planned | Behavior-test lockfile/install-script review plus closed failure on KEV, missing
  or incomplete SBOM, unsupported dependency, mutable automation, invalid provenance/signature, and
  artifact digest mismatch; workflow-test `R == C`, annotated-tag identity, isolated privileged
  scripts, attestation of `SHA256SUMS`, its exact four-entry inventory, tag-only promotion, and
  publication of exactly the six verified assets.
- TEST-010 | planned | Run scanner unit/integration tests and mutation hashes on Python 3.11 for Linux,
  Windows, and macOS.
- TEST-011 | planned | Unit-test inclusion/exclusion, git state, key classification, size/binary skips,
  symlink boundaries, and suppression rationale.
- TEST-012 | planned | Forward-test a clean UI with unresolved authorization and require release
  identity, the exact seven-column ledger, separate rows for every failure/tool error/manual check/
  residual risk, owner/action per non-pass row, and `NO-GO`.
- TEST-013 | planned | Lint repository/article claims and complete an independent editorial review.
- TEST-014 | planned | Verify current official platform installation docs and validate each distributed
  path/adapter shape without claiming v0 native Agent Skill support.
- TEST-015 | planned | Run license/provenance diff audit and secret scan over the full Git history before
  tag/publication.
- TEST-016 | planned | Run localized production route/feed/sitemap/project/source-link smokes after D1
  publication and Worker deploy.
- TEST-017 | planned | Forward-test PII/production credential/MCP/deploy authority boundaries and require
  synthetic data, least privilege, egress review, explicit compatibility approval for retention/
  training/deletion/region terms, refusal, and human approval.
- TEST-018 | planned | Forward-test a child-location app and require the full privacy lifecycle plus
  legal/privacy escalation before release.
- TEST-019 | planned | Forward-test a hosted BaaS release with missing operational controls and require
  rate/spend/restore/recovery/failure/alert/containment blockers.
- TEST-020 | planned | Forward-test AI-generated RLS/migration code and AI-generated tests; require named
  human review and independent negative evidence before release.
- TEST-021 | planned | Validate every forward-test record against the reproducibility rubric and retain
  three raw isolated runs per nondeterministic scenario.

| Requirement | Acceptance | Verification | Status |
| --- | --- | --- | --- |
| REQ-001 | AC-001 | TEST-001 | planned |
| REQ-002 | AC-002 | TEST-002 | planned |
| REQ-003 | AC-003 | TEST-003 | planned |
| REQ-004 | AC-004 | TEST-004 | planned |
| REQ-005 | AC-005 | TEST-005 | planned |
| REQ-006 | AC-006 | TEST-006 | planned |
| REQ-007 | AC-007 | TEST-007 | planned |
| REQ-008 | AC-008 | TEST-008 | planned |
| REQ-009 | AC-009 | TEST-009 | planned |
| REQ-010 | AC-010 | TEST-010 | planned |
| REQ-011 | AC-011 | TEST-011 | planned |
| REQ-012 | AC-012 | TEST-012 | planned |
| REQ-013 | AC-013 | TEST-013 | planned |
| REQ-014 | AC-014 | TEST-014 | planned |
| REQ-015 | AC-015 | TEST-015 | planned |
| REQ-016 | AC-016 | TEST-016 | planned |
| REQ-017 | AC-017 | TEST-017 | planned |
| REQ-018 | AC-018 | TEST-018 | planned |
| REQ-019 | AC-019 | TEST-019 | planned |
| REQ-020 | AC-020 | TEST-020 | planned |
| REQ-021 | AC-021 | TEST-021 | planned |

## Decisions

- DEC-001 | Name the project and skill `vibeworthy`. | rationale: it expresses the three desired
  outcomes (valuable, maintainable, trustworthy) without promising automated security; GitHub search
  found no exact repository-name collision. | affects: REQ-001, REQ-014, REQ-016
- DEC-002 | Keep original work MIT and treat the two cited repositories as research inputs, not merged
  source. | rationale: Revenue-Centric Design's license is source-available with a field restriction;
  independent product-discovery guidance avoids misleading “open-source blend” claims while clear
  provenance acknowledges influence. | affects: REQ-003, REQ-015
- DEC-003 | Preserve a no-gambling functional boundary in the skill while licensing original code MIT.
  | rationale: it honors the product-design input without modifying the MIT grant; the boundary is an
  instruction governing maintained-agent behavior, not a license condition on recipients. | affects:
  REQ-015
- DEC-004 | Use one orchestrating skill with progressive references rather than three always-loaded
  skills. | rationale: non-technical users asked for one entry point; progressive disclosure limits
  context cost while retaining focused procedures. | affects: REQ-001, REQ-002, REQ-014
- DEC-005 | Ship a heuristic scanner, not a security score. | rationale: deterministic local checks can
  catch high-frequency failures, but a score would imply comparability and assurance the tool cannot
  establish. | affects: REQ-007, REQ-010, REQ-011, REQ-013
- DEC-006 | Treat Firebase client API keys and Supabase publishable/anon keys according to vendor
  semantics rather than generic “all keys are secrets” advice. | rationale: authorization rules and
  privileged credentials are the actual enforcement boundary; false alarms teach users the wrong
  security model. | affects: REQ-007, REQ-008, REQ-011
- DEC-007 | Provide v0 as a manual Instruction adapter only. | rationale: current official v0 docs do
  not claim Agent Skill import, while Lovable and Bolt do; it is a reduced safety core rather than
  functional parity, and compatibility claims must follow evidence.
  | affects: REQ-014, REQ-016
- DEC-008 | Reuse the existing dimi.dev.br publisher and deploy process without schema changes. |
  rationale: the requested output is editorial/project content, and the current system already offers
  localized revisions, feeds, sitemap, preview, archive, and rollback. | affects: REQ-016
- DEC-009 | Keep privileged actions human-gated even when the user asks the agent to “do everything.” |
  rationale: speed does not widen authority to production credentials, personal data, billing,
  destructive state, external communication, or unreviewed MCP/network egress. | affects: REQ-017,
  REQ-018, REQ-019
- DEC-010 | Define scanner scope as the local worktree, not Git history, dependency internals, or cloud
  configuration. | rationale: scope honesty prevents a clean heuristic scan from becoming a security
  claim; dedicated history/SCA/cloud checks remain explicit release evidence. | affects: REQ-010,
  REQ-011, REQ-012
- DEC-011 | Treat release tags as human-readable aliases, not immutable identity. | rationale: Git tags
  can be force-moved; the reviewed commit SHA or verified package digest is the durable identity, and
  branch-only platform imports must record the SHA inspected at import time. | affects: REQ-014,
  REQ-015, REQ-016
- DEC-012 | Treat a hostile concurrent local writer as outside the portable scanner's assurance
  boundary. | rationale: path identity checks detect observed changes, redirects, and persistent
  swaps, but a dependency-free Python 3.11 implementation cannot provide one atomic filesystem
  snapshot across Linux, macOS, and Windows. Release scans therefore require a quiescent isolated
  checkout on a trusted runner, and every structured format exposes `atomic_snapshot: false` plus
  `release_evidence_requires_quiescent_isolated_checkout: true`. | affects: REQ-010, REQ-011, REQ-013
- DEC-013 | Require the public release tag target R to equal the independently evaluated candidate C
  exactly. | rationale: comparing only the skill subtree of a descendant commit does not bind changes
  to release automation, manifests, SBOM generation, or publication logic; tagging C directly makes
  the reviewed repository state and distributed source identity unambiguous. Post-release evidence
  may be recorded in a later documentation commit without changing the tag. | affects: REQ-009,
  REQ-014, REQ-021
- DEC-014 | Treat the outermost visible enclosing Git marker as part of the controlled source boundary
  without invoking repository Git. | rationale: a nested marker or nested scan target must not narrow
  trust and make a sibling repository executable eligible through PATH; reject intersecting lexical
  and resolved origins, then use the documented filesystem fallback when trusted Git is unavailable.
  | affects: REQ-010, REQ-011
- DEC-015 | Require Python isolated mode for every preflight-scanner launcher. | rationale: project-
  controlled `PYTHONPATH`, `sitecustomize`, or shadow standard-library modules can execute before any
  in-script guard; `python -I` is therefore part of the security boundary, not an optional invocation
  preference. | affects: REQ-010, REQ-011, REQ-014
- DEC-016 | Treat recognized shell controls, wrappers, and remote-content substitutions as executable
  intent and fail closed when relevant parsing remains ambiguous. | rationale: syntax that preserves
  fetcher-to-interpreter flow cannot turn into a clean result merely because it is wrapped, redirected,
  nested, or launched by an unknown command. | affects: REQ-009, REQ-010, REQ-012
- DEC-017 | Protect report paths across raw, NFC, safe-display, strict percent-decoding, and final URI
  rendering projections, failing closed beyond four source encoding layers or a transform budget
  breach. |
  rationale: a serializer or downstream URI decoder must not recreate a detected value that was absent
  from the pre-render display path; an opaque location is safer than an unverifiable partial location.
  | affects: REQ-007, REQ-010, REQ-011
- DEC-018 | Track bounded fetch aliases, function calls, literal and unknown file provenance, native
  output names, and effective redirections within one execution scope; resolve alias/function chains
  at call time within the symbol budget and consume all heredocs FIFO while executing only the
  effective stdin body. | rationale: shell state and redirection ownership affect whether downloaded
  bytes become code, but unbounded expansion or filesystem/symlink inference would create both
  bypasses and misleading blockers. Dynamic or unsupported flow fails closed only when it reaches a
  potential execution consumer or file transform. | affects: REQ-009, REQ-010, REQ-012
- DEC-019 | Keep Firebase constant evaluation and PostgreSQL dynamic-SQL projection to explicit,
  bounded grammars instead of claiming complete language interpretation. | rationale: the scanner is
  a deliberately small heuristic preflight; unsupported expressions remain unresolved and the
  independent authorization/migration review gate still blocks release, while only statically proven
  unsafe forms become scanner findings. | affects: REQ-008, REQ-010, REQ-011, REQ-012
- DEC-020 | Treat directories with active writers as non-quiescent and completed command records as
  the source of truth for tool-evidence claims. | rationale: scanning a live transcript or event
  directory can create a legitimate race error, but a response must preserve that observed report and
  exit code rather than relabel it as absent or let a later narrow pass overwrite it. Use a stable
  bounded artifact, an isolated candidate copy, or defer the scan. | affects: REQ-010, REQ-012,
  REQ-021

## Open Questions

- Q-001 | deferred | Whether future platform-native APIs can automate skill installation. | revisit
  when Lovable, Bolt, or v0 publishes a stable authenticated skill-management API; v1 uses documented
  UI/GitHub import paths and avoids requesting user credentials.
- Q-002 | deferred | Whether VibeWorthy should become a multi-skill suite. | revisit after forward tests
  or adoption show that automatic triggering/context load is unreliable; v1 keeps one coherent flow.
