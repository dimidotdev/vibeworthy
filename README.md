# VibeWorthy

VibeWorthy is an open Agent Skill for deciding whether an AI-assisted product is worth building,
maintaining, trusting, and releasing. It prompts for market evidence, turns the intended change into
a bounded engineering slice, and makes security and release unknowns visible before they become
launch claims.

It is a decision aid, not an autonomous product team or a security certification. The bundled
preflight scanner catches a deliberately small set of common repository mistakes. A clean scan does
not establish demand, prove authorization, inspect Git history or cloud configuration, or make an
application production-ready.

## What it does

VibeWorthy classifies work as `explore`, `prototype`, or `ship`, then applies four connected lenses:

1. **Market:** identify the user, painful moment, current alternative, evidence, distribution path,
   smallest experiment, success signal, and stop condition.
2. **Engineering:** inspect the actual project, define the build contract and non-goals, compare
   consequential options, and deliver verifiable vertical slices.
3. **Trust:** map assets and boundaries, keep privileged credentials out of clients and prompts, and
   require negative authorization evidence where data crosses users or roles.
4. **Release:** separate automated results from manual evidence and return a scoped `GO`,
   `CONDITIONAL`, or `NO-GO` recommendation.

Requests involving public endpoints, real user data, authentication, payments, privileged
integrations, destructive actions, or other external side effects receive the `ship` safety gates
even when they are described as prototypes.

## Review before installing

An Agent Skill can influence tool use and may include executable files. Read every file under
[`skill/vibeworthy`](skill/vibeworthy) before enabling it, confirm that its requested access fits
your environment, and record the exact 40-character commit SHA you reviewed. Branches and tags are
mutable labels; the commit SHA (or a verified package digest) is the version identity.

The canonical repository is `https://github.com/dimidotdev/vibeworthy`. Treat it as an installation
source only while it resolves publicly and the exact commit or verified release package you reviewed
is still available there.

The release workflow is configured to publish the Agent Skill ZIP, CycloneDX SBOM, release manifest,
`SHA256SUMS`, and two GitHub provenance bundles for a verified annotated tag. Verify `SHA256SUMS`
with its checksum-index attestation, verify the ZIP separately with its archive-provenance bundle, and
constrain both `gh attestation verify` checks to the expected repository, release workflow signer,
source commit, and tag ref. Then verify every digest listed in `SHA256SUMS` before installing the ZIP.
The automatically generated GitHub “Source code” archives are host-created repository snapshots; they
are outside the workflow-managed six-file inventory and are not the attested Agent Skill package.
Until a release run and these durable assets exist, treat this as the intended release contract rather
than evidence that publication already succeeded.

## Compatibility snapshot

Verified against the linked public documentation on **2026-07-30**. Platform behavior can change;
recheck the source documentation before a release or workspace-wide install.

| Host | Install or import | Invocation | Bundled references | Bundled scanner | Important limitation |
| --- | --- | --- | --- | --- | --- |
| Lovable | Native public-GitHub skill import from the `skill/vibeworthy` subdirectory | Automatic when enabled, or `/vibeworthy` | Imported with the skill | Run locally; host-side Python execution is not documented | The documented subdirectory URL uses a branch. Record the full SHA reviewed at import time. |
| Bolt | Native public-GitHub repository import; select `skill/vibeworthy` | Automatic when enabled, or select the skill manually | Imported with the skill | Run locally; host-side Python execution is not documented | The import UI documents a repository URL, not an immutable revision selector, and imports are detached snapshots. Record the reviewed SHA and re-import deliberately for updates. |
| Codex CLI / IDE | Agent Skill directory in `.agents/skills/` or `~/.agents/skills/` | `$vibeworthy`, or automatic matching | Loaded on demand | Available when Python and tool permissions allow it | Local installation is not an approval for production, network, billing, or destructive access. |
| Claude Code | Agent Skill directory in `.claude/skills/` or `~/.claude/skills/` | `/vibeworthy`, or automatic matching | Loaded on demand | Available when Python and tool permissions allow it | Review the skill before granting workspace trust or command permissions. |
| claude.ai | Upload the reviewed skill archive where custom Skills are available | Select or let Claude match the Skill | Included in the uploaded archive | Execution depends on the product container and account capabilities | Availability and execution controls differ from Claude Code. |
| v0 | No documented native Agent Skills import; manually copy the reduced Instruction | Enable the saved Instruction in the prompt bar | Not loaded | Not run | The adapter preserves only core stop rules. References, templates, and the scanner remain separate manual steps. |

Sources: [Lovable Skills](https://docs.lovable.dev/features/skills),
[Bolt Skills](https://support.bolt.new/building/skills),
[Codex Skills](https://developers.openai.com/codex/skills),
[Claude Code Skills](https://code.claude.com/docs/en/skills), and
[v0 Instructions](https://v0.app/docs/instructions).

### Lovable

1. Inspect the repository at the exact commit that you intend to trust and save that SHA with your
   review notes.
2. In **Settings > Skills > Add**, choose **Import from GitHub**.
3. Import
   `https://github.com/dimidotdev/vibeworthy/tree/main/skill/vibeworthy`.
4. Confirm the imported files match the SHA you recorded. If they do not, stop and review again.
5. Keep automatic use enabled only if that behavior is appropriate for every project in the
   workspace; otherwise invoke `/vibeworthy` explicitly.

Lovable's documented URL shape names a branch and does not document an immutable revision selector.
Do not treat `main` or a release tag as proof of what was reviewed.

### Bolt

1. Inspect and record the full commit SHA from the public repository.
2. Open the workspace Skills library or a project's Skills page, select **Add skill > From GitHub**,
   and enter `https://github.com/dimidotdev/vibeworthy`.
3. Select the `skill/vibeworthy` folder and create the skill.
4. Verify the imported content against the recorded SHA, then enable it only in the intended
   projects.

Bolt documents that an imported GitHub skill is a snapshot, not a live link. Re-importing is an
update operation and requires a new review and SHA record.

### Codex

Clone and detach at the reviewed commit before copying the complete skill directory:

```bash
git clone https://github.com/dimidotdev/vibeworthy.git
cd vibeworthy
git checkout --detach <FULL_COMMIT_SHA>
git rev-parse HEAD
```

Copy `skill/vibeworthy` to either `.agents/skills/vibeworthy` for one repository or
`~/.agents/skills/vibeworthy` for your user. Do not merge it over an existing directory; review and
move the old installation first. Codex discovers the packaged references and scanner with the skill.
Invoke it explicitly with `$vibeworthy` or use a request that matches its description.

### Claude

Use the same detached checkout, then copy `skill/vibeworthy` to `.claude/skills/vibeworthy` for one
project or `~/.claude/skills/vibeworthy` for your user. Claude Code can match the description or be
invoked with `/vibeworthy`. On claude.ai accounts that support custom Skills, create an archive from
the reviewed `skill/vibeworthy` directory and upload that archive; do not upload the whole repository
or secrets from a working project.

### v0: reduced manual Instruction

v0's public documentation describes reusable account Instructions, not native Agent Skills package
import. Review and copy the contents of
[`skill/vibeworthy/assets/v0-instructions.md`](skill/vibeworthy/assets/v0-instructions.md) into
**Prompt bar > + > Instructions > New Instruction**, then enable it for the conversation.

This is intentionally reduced and is not feature parity with the full skill. v0 will not
automatically load VibeWorthy's references or templates and will not run the Python scanner. Consult
those files and run the scanner locally as separate steps.

## Local preflight scanner

The scanner uses Python 3.11 or newer and only the standard library. It reads the selected worktree,
redacts matched values, and emits text, JSON, or SARIF:

```bash
python -I skill/vibeworthy/scripts/preflight.py /path/to/project
python -I skill/vibeworthy/scripts/preflight.py /path/to/project --format json
python -I skill/vibeworthy/scripts/preflight.py /path/to/project --format sarif
```

Keep `-I`: isolated mode prevents project-controlled Python startup and import hooks from running
before the scanner can inspect the target.

Exit codes are stable:

- `0`: no blocking finding in the scanner's limited scope;
- `1`: at least one blocking finding;
- `2`: invalid usage or a tool/runtime failure.

Exit `0` is not a release decision. The scanner does not examine Git history, submodule contents,
deployed infrastructure, cloud-side key restrictions, live authorization behavior, dependency
provenance, or market evidence. It skips generated, vendor, binary, and oversized content and does
not transmit repository data. Run project-native tests, dedicated history and dependency checks, and
the manual evidence gates described by the skill.

The scanner reads a non-atomic view of the worktree. It rejects filesystem redirects and fails closed
when it observes a root or file changing, but it cannot defeat a local process with write access that
swaps and restores paths entirely between checks. Stop editors, generators, builds, and other writers
before scanning. For release evidence, use a quiescent isolated checkout on a trusted runner and
discard the result if anything else could have modified that checkout during the scan.

When Git is available, the scanner disables repository fsmonitor execution and uses Git only to
enumerate tracked plus untracked, non-ignored files. Without Git it falls back to an explicitly labeled
filesystem scope; that fallback cannot distinguish tracked, ignored, or historical files.

When Git metadata is available, the worktree scope is tracked files plus untracked, non-ignored
files. An ignored local environment file is outside that scope; a tracked environment file is not.
The scanner does not follow this into a claim about repository history or remote state.

Only a warning can carry a line-scoped exception, using the complete marker below on the same line:

```text
vibeworthy:ignore <RULE_ID> reason="..." owner="..." approved-by="..." compensating-control="..." expires="2099-01-01"
```

The metadata must name different owner and approver identifiers, and the expiry must be a future ISO
date. The scanner cannot verify organizational independence; record that evidence separately. The
warning remains visible as suppressed and as a required manual check. A blocker, tool error, expired
or incomplete marker, or exception without a compensating control remains active and cannot produce
`GO`.

## Development

No third-party Python packages are required:

```bash
python --version
python -m unittest discover -s tests -p "test_*.py" -v
```

CI runs the same suite with Python 3.11 on Linux, Windows, and macOS. Scanner-rule changes need
synthetic fixtures that prove detection, redaction in every output format, stable exit behavior, and
no mutation of the scanned fixture. Package changes must preserve the two-field frontmatter, direct
resource links, and the `SKILL.md` line budget.

[`sbom.cdx.json`](sbom.cdx.json) records the release's empty third-party runtime dependency graph;
the scanner uses only the Python standard library. Git is an optional external scope-enhancement tool,
not a required runtime package. CI actions are development infrastructure rather than runtime
components and remain pinned to reviewed full commit SHAs in the workflow.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow,
[SECURITY.md](SECURITY.md) for private reporting guidance, and
[docs/provenance.md](docs/provenance.md) for source and license boundaries.

## License and use boundary

Original VibeWorthy material is available under the [MIT License](LICENSE). The maintained skill
declines gambling, betting, casino, loot-box, and other real-money games-of-chance work as a project
behavior. That behavior is not an extra condition on the MIT license or on recipients' legal rights.

VibeWorthy does not guarantee security, compliance, profitability, or production readiness. It does
not replace threat modeling, penetration testing, legal/privacy advice, human review of critical
logic, or evidence from the deployed enforcement boundary.
