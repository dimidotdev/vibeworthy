# Contributing to VibeWorthy

VibeWorthy should make AI-assisted development safer without making normal work slow or noisy.
Contributions are welcome when they prevent or detect a credible failure with proportionate effort.

## Design rules

- Keep the core skill concise and written for an intelligent agent.
- Explain user impact in plain language; avoid unexplained security jargon.
- Load detailed references only for the stage or platform that needs them.
- Prefer one boundary-level test over several shallow checklist items.
- Do not add recurring scans, evidence tables, or approval steps without a concrete threat they address.
- Never claim that a checklist or scanner proves security, compliance, or production readiness.
- Preserve human approval for production, billing, communication, destructive actions, and real
  sensitive data.

## Skill changes

- Keep `skill/vibeworthy/SKILL.md` below 500 lines; smaller is preferred.
- Limit YAML frontmatter to `name` and `description`.
- Link every packaged reference and asset directly from `SKILL.md`.
- Update `agents/openai.yaml` when the skill's purpose or activation changes.
- Keep the compact v0 adapter self-contained and honest about reduced capabilities.
- Test at least one harmless `quick` scenario and one security-critical scenario when behavior
  changes. A single pass per scenario is enough unless it exposes a real defect.

## Scanner changes

The scanner uses Python 3.11+ and the standard library.

- Keep it local, read-only, bounded, and free of network or package-install side effects.
- Use only synthetic fixtures. Never copy a real incident credential into a test.
- Never print matched values; report a rule identifier, redacted path, line, and remediation.
- Add a focused regression test for new or changed behavior.
- Keep blocker and tool-error exits fail-closed.
- Document false-positive tradeoffs and scanner limitations.

Run:

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

For documentation-only changes, the package tests and skill validator are normally sufficient. Do not
run the entire scanner regression suite repeatedly when relevant code and fixtures did not change.

## Pull requests

Describe:

1. the credible misuse or failure being addressed;
2. the smallest control added or changed;
3. the focused evidence that verifies it;
4. any remaining limitation or false-positive risk.

Inspect the diff for actual credentials, personal/customer data, unnecessary generated files,
misleading assurance language, and mutable automation references.

## Security reports

Use the private process in [SECURITY.md](SECURITY.md) for vulnerabilities. Do not publish a credential,
customer data, or an exploit against a system you do not own or have permission to test.

## License

Contributions must be compatible with the MIT license and must be yours to submit. Identify and retain
the notice for any substantially adapted third-party material.
