# Rejected candidate audit — 8fbce1329355f428dcf451d2e29431f5a1f87f04

- Date: 2026-07-30
- Decision: **rejected; excluded from release and forward-evaluation scoring**
- Reviewed repository commit: `8fbce1329355f428dcf451d2e29431f5a1f87f04`
Reviewed skill tree: recover with
`git rev-parse 8fbce1329355f428dcf451d2e29431f5a1f87f04:skill/vibeworthy`

This record preserves the independent audit reports that stopped candidate `8fbce132`. It contains no
credentials, customer data, or production output. The reports were delivered through the local agent
review channel; the original conversational transcripts and behavior-probe outputs are not release
artifacts and were not retained in this repository. Reproduction cases below use only synthetic data
and must become regression tests before a later candidate can be considered.

## Scanner audit — failed

The independent scanner reviewer first confirmed the committed baseline: 88 tests passed on Linux and
one Windows-only junction test was skipped. The candidate then failed on these synthetic cases:

| Severity | Reproduction contract | Observed gap | Required regression |
| --- | --- | --- | --- |
| high | Put a secret-like assignment value containing the literal redaction sentinel in one filename, then scan text, JSON, and SARIF. | The value was omitted from the path-redaction automaton and remained reversible in output paths. | The value is absent from all formats, including URI-decoded SARIF locations. |
| high | Put a marker-writing synthetic `git` outside the root and reach it through a PATH directory symlink originating inside the root. | Resolution discarded the lexical controlled origin and executed the synthetic binary. | Both lexical and resolved origins are rejected and the marker is never created. |
| medium | Scan a shell-negated remote-fetch pipeline into a command interpreter. | Shell negation hid the fetcher from the remote-execution rule. | Shell wrappers remain classified or fail closed. |
| medium | Track oversized, NUL-containing, and invalid-UTF-8 `.env` fixtures. | Content skips occurred before sensitive-path classification. | `VW-ENV-TRACKED` is emitted independently of content readability. |
| medium | Emit a warning with `PYTHONIOENCODING=ascii`. | A non-ASCII separator caused an uncaught encoding error and incomplete report. | Text output and exit behavior remain valid under ASCII stdout. |
| medium | Scan Firestore and Realtime Database rules with literal self-equality such as `0 == 0`. | The bounded tautology detector covered only a narrower literal. | Equivalent numeric literal comparisons block without an unbounded regex. |
| medium | Put a remote pipeline in npm `prepublish`, `preprepare`, or `postprepare`, and in an arbitrary script value. | Lifecycle coverage and JSON script-value analysis were incomplete. | All script values receive remote-execution analysis; named lifecycle hooks also receive the install-script finding. |
| low | Use a suppression owner containing only a format character. | Raw non-emptiness passed even though normalized identity was empty. | Every required field is semantically non-empty and owner differs from approver after normalization. |

The reviewer accepted the explicitly documented non-atomic worktree boundary and quiescent-isolated-
checkout requirement; it was not counted as a defect.

## Behavior audit — failed

Three fresh hostile full-skill release probes and three reduced-v0 probes correctly refused release,
but all omitted one or more mandatory decision-record fields. The missing contract included a compact
identity (`Artifact`, `Scope`, `Environment`, `Policy`, and evidence cutoff), the exact seven-column
ledger, separate rows for automated passes/failures/tool errors/manual checks/residual risks, and an
owner plus next action for every non-pass item. Correct `NO-GO` behavior without auditable evidence did
not satisfy REQ-012. These six outputs were not counted as forward tests.

## Package and release audit — failed

The package reviewer confirmed the Agent Skill shape, metadata, links, compatibility documentation,
MIT/provenance boundary, immutable action pins, reproducible skill-only ZIP, CycloneDX SBOM, clean Git
object graph, and a history scan of 15 commits / 108 blobs with no usable credential found. Release was
still rejected because:

- a descendant release commit could replace the evaluated commit when only the skill subtree matched;
- inline Python in the OIDC-enabled build job did not use isolated import mode;
- only the ZIP was attested, leaving the manifest/SBOM/checksum relationship without a trust anchor;
- the workflow retained an expiring Actions artifact but did not create a durable, tag-gated GitHub
  Release; and
- no actual public tag, release assets, import verification, or production evidence existed.

Decision DEC-013 selects exact `R == C`. A later candidate must independently revalidate the complete
workflow and produce real release evidence; this failed record cannot be promoted to a pass.
