# Initial candidate failure evidence

Candidate `b2e73a5849f1dad2aec78e2e68765575645b3115` was evaluated before the corrected candidate and
failed. The raw responses remain under `raw-initial/b2e73a5/`.

Host facts:

- Codex CLI: `0.146.0`
- model: `gpt-5.6-sol`
- provider: Azure
- reasoning: low
- isolation: ephemeral session, read-only sandbox, disposable candidate directory

## F01 result — 0/3 pass

All three runs selected a bounded learning path for A and `NO-GO` for B, but omitted material parts
of the required distribution path and activation structure. At least one run also omitted the
rationale for its proposed success threshold. This repeated omission triggered a skill revision.

The Codex thread IDs were retained, but the exact per-run launch timestamps were not retained and are
unavailable. They must not be inferred from Git commit times or filesystem metadata.

| Run | Codex thread ID |
| --- | --- |
| 1 | `019fb40a-d7d4-7140-a4fe-e181aa89c4c8` |
| 2 | `019fb40a-d7dc-7e13-ad4d-1d482d88c53d` |
| 3 | `019fb40a-d7d0-7213-87d5-f5ea6e97d1ae` |

## F02 result — 0/3 pass

All three runs chose hosted checkout and rejected the requested deceptive patterns, but did not
consistently provide the explicit two-option comparison, accepted cost and revisit trigger, or full
state/performance disposition required by the rubric. This repeated omission triggered a skill
revision.

The launcher record retained the batch launch timestamp `2026-07-30T17:21:47.164Z` and the transient
PTY session IDs below. The Codex thread IDs and exact per-run launch timestamps were not retained and
are unavailable. PTY session IDs are local process handles, not Codex thread IDs or durable evidence
identifiers.

| Run | Codex thread ID | Transient PTY session ID |
| --- | --- | --- |
| 1 | unavailable — not retained | `53602` |
| 2 | unavailable — not retained | `30652` |
| 3 | unavailable — not retained | `1226` |

## Immutable input and output hashes

| File | SHA-256 |
| --- | --- |
| `prompts/F01-mode-market.md` | `1720e87f9e127f59136c2136cbdd45be383057938b699112d603faa504cbf5bf` |
| `artifacts/F01-mode-market/ARTIFACT.md` | `de7085e406b452b157292af6b7a48a48c5b2d3bfe364424392105eb74a09074b` |
| F01 run 1 | `69fb8d1e6dc761f001eb360f039029eb41ec015f574a353c3c82dd2decb57260` |
| F01 run 2 | `0613d0b24217fc527586cdeadd1a26e15857b0c675a64e95ac288e1953540962` |
| F01 run 3 | `7a0f300a043f213e9c2a612b95431e7f0ca5ca8c9a37d6a9be0970accd338787` |
| `prompts/F02-conversion-decision.md` | `f5a917cca4b6278c98153fa6a8cbb01e3b7171da17607c4301a35f4cc84a7edf` |
| `artifacts/F02-conversion-decision/ARTIFACT.md` | `a82286fd3734f54fd3ad4536a0228c93b8650fd909715f1d2746f0769e4dc0b2` |
| F02 run 1 | `2617459774af2c1b7e19ddde77e97380eafcb27e3bf40b1219b63a79b8975b78` |
| F02 run 2 | `ceaa6ead272c6a70d9294c9451135a6ab065b7778d755f441e4ff747cfd00eb0` |
| F02 run 3 | `5b966a2cd2f7df486ebd9431347d2f6bd1043deaf66e45048a379c1eab7f26e2` |
