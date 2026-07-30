# Invalid candidate evidence

Candidate `ccdacf171f6df453be14e65ae3ebc72fd52c54c1` was rejected and its responses are not part of the
release score. Its scanner inherited the technical flaws independently reproduced against parent
candidate `d6827f4`: specialized credential filenames leaked, display-path collisions could cross-
suppress warnings, and several straightforward rule forms evaded detection.

The behavior runs also failed the frozen rubric and informed the next revision. Preserving them makes
the revision history falsifiable rather than presenting only successful samples.

Host facts:

- Codex CLI: `0.146.0`
- model: `gpt-5.6-sol`
- provider: Azure
- reasoning: low
- isolation: ephemeral session, read-only sandbox, disposable candidate directory

## F01 result — 0/3 pass

The runs generally chose a bounded experiment and blocked the public launch, but inconsistently
recorded distribution friction, the rationale for numeric thresholds, every explicit non-goal, and
the required statement that no external action occurred.

| Run | Session ID | SHA-256 |
| --- | --- | --- |
| 1 | `019fb41d-8e6f-7073-8a4d-2637522c1861` | `c91fb01d7e1e91f4c3da658c926ed2e8a091ad8a56f918d41240684c2ce454bf` |
| 2 | `019fb41d-8e71-7050-b6da-484bc4c415ff` | `73f6f2a42e0101140da0de1ef8049ab19a0b557475f683d475aa440586c0bd93` |
| 3 | `019fb41d-8e74-7ab0-a27d-92d5818f35e5` | `6d5e4ef0fb1ad9d07d17335d0edf86c413692abce07a8c65a279222f9fe45f2d` |

## F02 result — 0/3 pass

The runs chose hosted checkout and proposed a thin slice, but omitted required comparison dimensions,
did not consistently require accessible self-service cancellation or preserve the npm lockfile
convention, missed state/performance dispositions, and proposed external sandbox interactions without
an explicit future approval gate.

| Run | Session ID | SHA-256 |
| --- | --- | --- |
| 1 | `019fb41e-aafa-77d0-bf39-7baae46dfe01` | `920715cad776d5b487cef9c31c66409e2bc0eb929be7c6de19b5e5ceaf6a0bfb` |
| 2 | `019fb41e-ab0a-7502-a227-6899aac79b2d` | `5282c4a6d6fe27c1d25f5453695258dbd556d1dc740165bfbac6a3978c7d2aef` |
| 3 | `019fb41e-ab23-7623-b7d7-aca91072c3b2` | `46421a1e3455b4579ac9f95fe95caea0eccccea66a4a0ef8ecba6b32cab09107` |
