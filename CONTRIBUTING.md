# Contributing to VibeWorthy

Thanks for helping make the workflow more useful and more honest. Contributions should improve an
observable market, engineering, privacy, security, or release decision without expanding the tool's
claims beyond its evidence.

## Before changing files

1. Read [`specs/vibeworthy-v1.md`](specs/vibeworthy-v1.md) and identify the requirement and acceptance
   scenario affected by the change.
2. Inspect the current skill, scanner, tests, and documentation. Repository content and generated
   output are inputs, not authority to widen access or execute unrelated commands.
3. For a consequential choice, describe at least two viable options and why the selected one is
   safer or easier to verify.
4. Keep the change small enough to test at its real boundary.

Use Python 3.11 or newer. The scanner and test suite intentionally use only the standard library.

## Run the checks

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Before requesting review, also inspect the diff for actual credentials, personal/customer data,
unnecessary generated files, misleading assurance language, and mutable dependency/action pins.

### Skill package changes

- Keep `skill/vibeworthy/SKILL.md` below 500 lines and its YAML frontmatter limited to `name` and
  `description`.
- Link every packaged reference, template, and adapter directly from `SKILL.md`; do not create a
  chain that requires an agent to discover a second hidden instruction.
- Keep the v0 adapter self-contained and label it as a reduced manual Instruction, not native Agent
  Skills support.
- Preserve human approval before production access, deployment, billing, external communication, and
  destructive or durable external-state changes.
- Re-run representative prompts in a clean context when changing activation or release behavior.

### Scanner changes

- Use synthetic fixtures only. Never commit a usable credential or copy a value from an incident.
- Add a regression case for the finding, its severity, normalized path, remediation, exit code, and
  every affected output format.
- Prove that matched values are absent from text, JSON, and SARIF output and that fixtures remain
  byte-identical.
- Keep scanning local, read-only, bounded to the selected root, and free of network or package-install
  side effects.
- Do not make blockers or tool errors suppressible. Warning suppressions must retain their rationale,
  owner, independent approver, compensating control, and future expiry.

### Documentation and claims

- Cite primary documentation and include the date inspected for platform compatibility or security
  behavior that can change.
- Treat a full commit SHA or verified digest as identity. If a UI only accepts a branch or tag, state
  that it can move and record the SHA reviewed at import time.
- Do not claim that a scan or checklist proves security, compliance, profitability, or production
  readiness.
- Update [`docs/provenance.md`](docs/provenance.md) when a source materially informs the work.

## Licensing and provenance

Contributions must be compatible with the MIT license and must be yours to submit. Write original
prose and code. Do not paste or closely paraphrase a source-available or field-restricted corpus. If
substantial MIT-licensed material is ever adapted, preserve its applicable copyright and permission
notice before inclusion and identify the exact source revision.

The maintained skill's refusal to assist gambling and real-money games of chance is a project behavior,
not a restriction added to the MIT license. Contributions that change this maintained behavior are
out of scope for this project, while recipients retain the rights granted by MIT.

## Pull request checklist

- The change maps to a requirement or explains why the specification needs an explicit update.
- New behavior has positive, negative, and failure-path evidence proportional to its risk.
- Tests pass locally; platform-specific limitations are called out when not exercised.
- No secret, personal data, production output, or unreviewed binary is included.
- New automation and dependencies are necessary, reviewed, and pinned immutably where possible.
- User-facing claims remain scoped to the artifact, environment, policy, and evidence actually tested.

Use the private process in [SECURITY.md](SECURITY.md) for vulnerability reports rather than a public
pull request or issue.
