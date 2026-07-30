# Platform compatibility and safe import

Use this dated matrix before installing the skill or claiming host behavior. Reverify the named host's official documentation when the date, surface, or plan differs.

Evidence date: **2026-07-30**.

| Host | Import or placement | Invocation | Bundled references | Local script | Required manual work |
| --- | --- | --- | --- | --- | --- |
| Lovable | Use its documented public-GitHub skill import with the repository root or skill subdirectory. | Allow documented automatic selection or invoke by slash command; confirm the imported revision. | Treat bundled files as available to the imported skill under documented support. | Do not assume a Python script runs automatically; inspect and run it only when the workspace exposes an authorized terminal. | Record the reviewed commit SHA, check import scope, review permissions, run external/manual release checks, and reverify current docs. |
| Bolt | Import the Agent Skill from public GitHub or files at the documented workspace/project scope. | Let the description guide selection or request the skill explicitly; verify the active scope. | Keep references inside the imported package and confirm that the chosen import includes them. | Run only in an authorized project terminal after inspection; do not imply automatic execution. | Record the reviewed SHA or file digest, review workspace versus project exposure, and complete cloud/manual checks. |
| Codex | Copy or install the complete `vibeworthy` directory into the configured skills location or use the repository package supported by the environment. | Invoke `$vibeworthy` explicitly or allow metadata-based selection. | Load references progressively from the installed directory. | Inspect and run the bundled script subject to sandbox, approval, and filesystem boundaries. | Pin the installed source, review the package before enabling, and complete unobservable cloud/provider checks. |
| Claude | Follow current official instructions for the exact Claude surface; package and import behavior can differ between Claude Code, API, and hosted products. Do not claim a public-repository import without verifying it. | Treat automatic selection and explicit invocation as surface-dependent. | Confirm that the named surface packages or exposes referenced files. | Treat execution as unsupported until the named surface and permissions prove otherwise. | Record surface, version where exposed, imported files, reviewed digest/SHA, invocation test, and all unsupported behavior. |
| v0 | Do not claim native Agent Skill import. Paste the reduced `assets/v0-instructions.md` into v0 Instructions. | Apply the saved Instruction manually and restate it in the task when behavior is uncertain. | Do not assume references are loaded. Open the full package manually for detailed procedures. | Do not assume the bundled preflight is present or automatic. Run it separately in the local repository. | Perform full market, security, backend, supply-chain, privacy, and release evidence steps outside v0; treat the adapter as reduced guidance, not parity. |

Use the current primary documentation for [Lovable skills](https://docs.lovable.dev/features/skills), [Bolt skills](https://support.bolt.new/building/skills), and [v0 Instructions](https://v0.app/docs/instructions). Use the current official Codex and Claude documentation for the exact product surface rather than extrapolating from another host.

## Pin and review the imported package

1. Inspect the skill as code before enabling it. Review instructions, scripts, dependencies, external links, tool requests, and requested data access.
2. Prefer an immutable full commit SHA or verified package digest. Record the repository, skill subdirectory, reviewed SHA/digest, reviewer, and date.
3. Treat a branch and tag as movable labels. When a UI accepts only a branch or tag, record the commit SHA resolved and reviewed at import time, disclose mutability, and repeat review before accepting an update.
4. Verify the imported shape: `SKILL.md`, every linked reference and asset, and the expected script. Reject missing, extra, or redirected content until reviewed.
5. Grant the minimum workspace, filesystem, network, MCP, and secret access. Never paste a credential into an import dialog or skill instruction.
6. Test one harmless prompt for invocation and one prompt that should trigger effective `ship` gates. Record unsupported references, scripts, or automatic behavior explicitly.
7. Keep the compatibility statement tied to host, surface, date, source revision, and test result. Withdraw a claim when platform behavior changes until it is retested.

Do not describe installation success as evidence that the host will obey every instruction. Keep human review and release gates in place across all hosts.
