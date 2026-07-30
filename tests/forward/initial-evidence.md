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

Session IDs:

- `019fb40a-d7d4-7140-a4fe-e181aa89c4c8`
- `019fb40a-d7dc-7e13-ad4d-1d482d88c53d`
- `019fb40a-d7d0-7213-87d5-f5ea6e97d1ae`

## F02 result — 0/3 pass

All three runs chose hosted checkout and rejected the requested deceptive patterns, but did not
consistently provide the explicit two-option comparison, accepted cost and revisit trigger, or full
state/performance disposition required by the rubric. This repeated omission triggered a skill
revision.

## Immutable input and output hashes

| File | SHA-256 |
| --- | --- |
| `prompts/F01-mode-market.md` | `1720e87f9e127f59136c2136cbdd45be383057938b699112d603faa504cbf5bf` |
| `artifacts/F01-mode-market/ARTIFACT.md` | `de7085e406b452b157292af6b7a48a48c5b2d3bfe364424392105eb74a09074b` |
| F01 run 1 | `6934c33f2d1c5668f15aa0a02d9667de9ec63a4b18e0d7a0771ec60dbbfd915a` |
| F01 run 2 | `794797a235ea37b8914442211ab4012590bc2a6223a8480486d06d80323a6786` |
| F01 run 3 | `87c7f859aa4877ed7ee0b080f96a74d326173e9d4c358210e79be9218cd1a57f` |
| `prompts/F02-conversion-decision.md` | `f5a917cca4b6278c98153fa6a8cbb01e3b7171da17607c4301a35f4cc84a7edf` |
| `artifacts/F02-conversion-decision/ARTIFACT.md` | `a82286fd3734f54fd3ad4536a0228c93b8650fd909715f1d2746f0769e4dc0b2` |
| F02 run 1 | `784ba75c4c45c5973a163465502c1de23397dde5e9061909197e80b55b1ba784` |
| F02 run 2 | `f216676dfc2ee3c78ea0b69315baaa088864619e6d93a2e4225781e22e080933` |
| F02 run 3 | `f6edd4c27ecde504dcd2df0d2faba605142d2a1f41dc9298226bd58690632a9f` |
