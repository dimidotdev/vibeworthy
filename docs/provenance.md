# Provenance and license boundaries

This record describes the research inputs and authorship boundary for VibeWorthy v1. It is a factual
source ledger, not a claim that any referenced project endorses VibeWorthy.

## Authorship statement

VibeWorthy v1 is original work released under MIT. It is not a fork, compilation, or relicensed blend
of the sources below. No prose or code from the Revenue-Centric Design corpus was copied or adapted,
and no substantial material from the MIT-licensed Matt Pocock collection is included in v1. Common
interface names, public facts, standards identifiers, and independently written workflow ideas do not
change that boundary.

If a later release substantially copies or adapts third-party material, its applicable notice and
license must be added before that material enters the repository. This ledger must then name the file,
source revision, and nature of the adaptation.

## Repository research inputs

| Source | Immutable revision inspected | License status | How it informed v1 | Material included |
| --- | --- | --- | --- | --- |
| [heliocosta-dev/revenue-centric-design](https://github.com/heliocosta-dev/revenue-centric-design/tree/6fa20cb4f91fa97bce9197be3f78b168784eb772) | `6fa20cb4f91fa97bce9197be3f78b168784eb772` | Source-available with attribution and a field-of-use restriction; not represented here as OSI-approved | Research context for connecting product evidence to implementation decisions and for the maintained no-gambling behavior | None; no text or code copied or adapted |
| [mattpocock/skills](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c) | `2ab958093e83e0ec752e6c1c5932da465bf23e0c` | MIT | Research context for small, composable, progressively disclosed engineering workflows | None; no substantial text or code copied or adapted |

The two repositories were inspected at the commits above on 2026-07-30, including their license
files. Commit identifiers are recorded because branches and tags can be moved.

## Standards and product documentation

The implementation and compatibility statements were independently written from public facts in
these primary sources, inspected on 2026-07-30:

- [Agent Skills specification](https://agentskills.io/specification)
- [Lovable Skills](https://docs.lovable.dev/features/skills)
- [Bolt Skills](https://support.bolt.new/building/skills)
- [OpenAI Codex Skills](https://developers.openai.com/codex/skills)
- [Claude Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [v0 Instructions](https://v0.app/docs/instructions)
- [OWASP Top 10:2025](https://owasp.org/Top10/2025/) and
  [ASVS 5.0.0](https://owasp.org/www-project-application-security-verification-standard/)
- [Firebase API keys](https://firebase.google.com/docs/projects/api-keys),
  [Security Rules](https://firebase.google.com/docs/rules), and
  [App Check](https://firebase.google.com/docs/app-check)
- [Supabase API keys](https://supabase.com/docs/guides/api/api-keys) and
  [Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [GitHub secret scanning](https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning)

These sources support compatibility and security-model facts. Their text is not redistributed as part
of the skill.

## No-gambling boundary

The maintained VibeWorthy agent declines gambling, betting, casino, loot-box, and other real-money
games-of-chance work. This is voluntary project behavior inspired by the desired product boundary. It
is outside the MIT grant and is not a license condition: recipients receive the unmodified rights in
[`LICENSE`](../LICENSE).

## Release identity and publication state

A full commit SHA or verified package digest is the identity of reviewed content. A branch or tag is a
mutable convenience label, even when a hosting platform presents it as a version. When a platform can
only import a branch or tag, review the resolved files, record the full SHA, and repeat the review if
the label resolves differently.

At this ledger's initial 2026-07-30 review, the local repository had no commits and no configured
remote. This historical observation is retained; the repository was subsequently initialized and
staged privately at `https://github.com/dimidotdev/vibeworthy` while release gates were still open.
A URL, branch, or tag alone is not publication evidence.

Every public release must bind the exact independently evaluated commit to its annotated tag and CI
run. `SHA256SUMS` binds the ZIP, SBOM, release manifest, and archive-provenance bundle; a separate
GitHub attestation authenticates that checksum index. Those four indexed assets plus the index and its
attestation form the exact six-file workflow-managed release inventory; GitHub's automatic source
archives are host-created snapshots outside that inventory. Post-release evidence may record resulting
digests, attestations, and durable GitHub Release identifiers in a later documentation commit without
changing the evaluated tag target.
