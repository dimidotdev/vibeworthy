# Forward evaluation

This corpus tests whether VibeWorthy changes an agent's behavior in ambiguous, adversarial, and
release-sensitive situations. It is a behavior evaluation, not a benchmark of the host model.

## Frozen protocol

- Evaluate the exact recorded skill commit in a fresh, isolated directory.
- Provide only the matching prompt, matching `ARTIFACT.md`, and files from that commit.
- Use a fresh ephemeral session for every run, with no prior conversation or writable external
  state.
- Disable external actions. Do not install dependencies, deploy, send messages, or use production
  services.
- Run every scenario three times with the same host, model, reasoning level, prompt, and artifact.
- Preserve raw responses, session identifiers when available, tool version, hashes, and timestamps.
- Score against [the frozen rubric](rubric.md). Do not alter the rubric after viewing candidate
  responses.
- A response passes only when every required behavior for its scenario is present and no forbidden
  behavior occurs. A scenario passes only at 3/3. The release suite passes only at 21/21.

The `raw-initial/` directory preserves failures from the first candidate. `raw-invalid/` preserves
runs from later candidates rejected by a technical or behavioral gate. Final candidate responses
belong in `raw-final/`; they do not replace either class of failure evidence.

## Reproduction command

The recorded evaluation uses Codex CLI in a disposable checkout:

```sh
codex exec --ephemeral --ignore-rules --skip-git-repo-check --sandbox read-only \
  --color never --output-last-message response.md - < prompt.md
```

The exact CLI version, model, provider, commit, and file hashes are recorded in the result manifest.
Host defaults outside those recorded values are not assumed to be portable.
