# VibeWorthy

VibeWorthy is an open Agent Skill that keeps security present throughout AI-assisted development,
from the first prompt to deployment, without turning every change into a heavyweight audit.

It is designed for vibe-coding tools, coding agents, and people who may not have a security
background. The skill applies secure defaults while the agent works, explains blockers in plain
language, and spends extra validation only where the risk justifies it.

## Why this exists

AI builders are very good at producing a working interface quickly. They can also make dangerous
choices look harmless:

- committing a real `.env` file;
- putting privileged keys in frontend variables;
- treating a hidden button as authorization;
- publishing permissive Firebase Rules or Supabase RLS;
- trusting client-supplied prices, owners, roles, or redirect URLs;
- installing an unnecessary package or executing a remote shell script;
- logging personal data or sending it to a model;
- deploying a destructive migration without a recovery path.

VibeWorthy moves those checks into the development flow instead of postponing them until after the
application is built.

## The lean security loop

The skill selects one intensity:

| Level | Typical work | Effort |
| --- | --- | --- |
| `quick` | Styling, copy, local UI, or pure logic | Inspect the touched area and run its nearest existing check |
| `guarded` | Public forms/APIs, storage, uploads, dependencies, external services, or user data | Add focused negative tests and one final checkpoint |
| `critical` | Auth, authorization, secrets, payments, sensitive data, Rules/RLS/IAM, migrations, destructive actions, or untrusted code | Verify at the real enforcement boundary and require human review before release |

Then it follows four steps:

1. Identify the protected data or capability, untrusted actor/input, and real enforcement boundary.
2. Build the smallest useful security control into the implementation.
3. Run one meaningful check at that boundary.
4. Stop only for a concrete release blocker; otherwise continue with a clearly stated residual risk.

The skill does not emit a generic OWASP table, repeat the same checklist after every edit, launch
multiple evaluator loops, or rerun equivalent scans by default.

## Security coverage

The core guidance covers:

- secret handling and `.env` hygiene;
- authentication, server-side authorization, tenant and object isolation;
- input validation, output encoding, uploads, redirects, SSRF, and injection;
- data minimization, retention, deletion, logging, and model-provider exposure;
- Firebase Rules, Firebase Admin paths, Supabase RLS, grants, Storage, Realtime, and functions;
- payment authority, webhook authenticity, replay, and idempotency;
- dependencies, lockfiles, install scripts, CI pins, and remote-script execution;
- rate and size limits, safe errors, timeouts, rollback, backup, and recovery;
- agent/MCP least privilege, prompt injection, egress, and point-of-action approval.

VibeWorthy is a decision aid, not a security certification. It cannot prove cloud configuration,
runtime authorization, legal compliance, or production readiness without evidence from those
boundaries.

## Install or use

Review the skill before enabling it. The complete package is
[`skill/vibeworthy`](skill/vibeworthy).

### Lovable and Bolt

Import the public GitHub repository and select the `skill/vibeworthy` directory where the host
supports Agent Skills. Confirm the imported revision and permissions before enabling it.

Repository:

`https://github.com/dimidotdev/vibeworthy`

See the dated [platform compatibility notes](skill/vibeworthy/references/platform-compatibility.md)
and recheck the host's current documentation because import behavior can change.

### Codex and Claude Code

Copy the complete `skill/vibeworthy` directory into the project- or user-level skills directory
supported by the host. Invoke it explicitly as `$vibeworthy` or `/vibeworthy` where supported.

Example request:

> Use VibeWorthy while building this feature. Keep the security pass concise and stop me only for a
> real blocker.

### v0 and other instruction-only hosts

Paste the compact
[`assets/v0-instructions.md`](skill/vibeworthy/assets/v0-instructions.md) into the host's reusable
Instructions. This adapter cannot automatically load the detailed references or run the local
scanner.

## Local preflight

The optional scanner uses Python 3.11+ and the standard library. It is local, read-only, does not use
the network, and never prints matched secret values.

```bash
python3 -I skill/vibeworthy/scripts/preflight.py /path/to/project
```

It detects a deliberately bounded set of common mistakes, including:

- a tracked or unignored sensitive `.env` file;
- high-confidence credential and private-key patterns;
- privileged Firebase or Supabase material in source/client configuration;
- unconditional Firebase access and explicitly disabled Supabase RLS;
- conflicting or missing JavaScript lockfiles;
- install lifecycle scripts and remote fetch-to-shell flows;
- mutable third-party CI actions and containers.

Run it once after scanner-relevant files stabilize for a guarded/critical change, explicit security
review, or release. After a fix, rerun only the affected check unless scanner-relevant files changed.

Exit codes:

- `0`: no blocking finding in the scanner's limited scope;
- `1`: at least one blocking finding;
- `2`: invalid usage or tool/runtime failure.

A clean result does not inspect Git history, cloud settings, deployed policies, runtime authorization,
submodules, or every vulnerability class. Use focused boundary tests and human review for critical
logic.

### If `.env` was committed

Do not paste or print it. Revoke or rotate the exposed values first. Then remove the file from
tracking, add the correct ignore rule, retain only a redacted template, and remediate Git history,
artifacts, caches, forks, logs, and mirrors as applicable. Deleting it in a later commit is not enough.

## Package design

```text
skill/vibeworthy/
├── SKILL.md
├── agents/openai.yaml
├── assets/
│   ├── security-checkpoint.md
│   └── v0-instructions.md
├── references/
│   ├── backends-supply-release.md
│   ├── platform-compatibility.md
│   └── security-privacy.md
└── scripts/preflight.py
```

The core instruction stays short. Detailed lifecycle and backend guidance loads only when relevant,
and the deterministic scanner performs cheap repository checks without spending model context on
manual file-by-file review.

## Development

The scanner and tests have no third-party Python dependency.

```bash
python3 -m unittest discover -s tests -p "test_*.py"
# If the Agent Skills validator is installed locally:
python3 /path/to/quick_validate.py skill/vibeworthy
```

Contributions should remain practical, explain risk in plain language, and avoid adding ceremony that
does not prevent or detect a credible failure. Report potential vulnerabilities through the private
process in [SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).
