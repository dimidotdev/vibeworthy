# Security policy

## Supported versions

Until the first tagged release, security fixes apply only to the latest reviewed commit. After a
release, the newest release line receives fixes; older commits, moved branches, copied Instructions,
and third-party mirrors are not maintained automatically. Identify any affected installation by its
full commit SHA or verified package digest, not only by a branch or tag name.

## Report privately

After the canonical GitHub repository is published, use its private **Security > Advisories > New
draft advisory** flow. Do not open a public issue for a suspected credential exposure, scanner
redaction failure, path-boundary escape, unintended code execution, or other vulnerability. If the
private advisory channel is unavailable, open a public issue containing only a request for a private
contact channel and no vulnerability details.

Include, without including real secrets or personal data:

- affected commit SHA and host platform;
- impact and the trust boundary crossed;
- minimal reproduction using synthetic values in a disposable repository;
- expected versus observed behavior;
- whether output, files, Git history, or external systems may have been affected;
- any safe containment already performed.

Do not attach a production repository, credentials, customer data, raw scanner output containing
sensitive material, or an exploit against a system you do not own or have permission to test.

## Credential exposure

If a real credential may have been disclosed, revoke or rotate it at the provider first. Then review
provider audit logs and dependent systems, contain misuse, and remediate Git history or other copies.
Deleting the value in a later commit is not sufficient. Report only a redacted identifier and never
paste the value into an issue, advisory, chat, test, or fixture.

## What belongs here

Security reports for VibeWorthy include behavior that causes the scanner or skill package itself to:

- reveal matched source text or secret values;
- leave its selected root, follow unsafe filesystem boundaries, or mutate a target;
- execute scanned project content;
- produce structurally invalid JSON/SARIF or an incorrect blocking exit code;
- turn a tool error or required manual check into release approval;
- misclassify a privileged backend credential as safe for a public client.

A finding produced by VibeWorthy about another application normally belongs to that application's
security process. Detection gaps and false positives are still useful here when reported with a
synthetic regression case.

## Disclosure and fixes

Maintainers will validate scope, coordinate a fix and regression test, and agree on disclosure timing
with the reporter when practical. No response or remediation deadline is guaranteed. A fix is not
considered complete until the affected boundary is tested and release/install guidance identifies the
correct immutable revision.

The scanner is heuristic. Its inability to report an issue is not evidence that an application is
secure, compliant, or ready for production.
