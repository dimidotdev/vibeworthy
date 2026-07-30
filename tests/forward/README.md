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

The candidate evaluation uses Codex CLI in a disposable checkout. Run this from one isolated
scenario directory so the response and complete JSONL event stream stay together:

```sh
codex --version | tee codex-version.txt
set -o pipefail
codex exec --ephemeral --ignore-rules --skip-git-repo-check \
  --sandbox read-only --color never --json \
  --model gpt-5.6-sol --config 'model_reasoning_effort="low"' \
  --output-last-message response.md - < prompt.md | tee events.jsonl
```

Capture the Codex thread ID from the `thread.started` event instead of recording a PTY or shell
process identifier:

```sh
python3 - <<'PY'
import json
from pathlib import Path

events = [json.loads(line) for line in Path("events.jsonl").read_text(encoding="utf-8").splitlines()]
thread_ids = {
    event["thread_id"]
    for event in events
    if event.get("type") == "thread.started" and event.get("thread_id")
}
if len(thread_ids) != 1:
    raise SystemExit(f"expected one Codex thread ID, found {len(thread_ids)}")
Path("thread-id.txt").write_text(next(iter(thread_ids)) + "\n", encoding="utf-8")
PY
```

Record the exact CLI version, model, provider, candidate commit, skill tree, prompt/artifact hashes,
thread ID, start/end timestamps, and response hash in the result manifest. Host defaults outside
those recorded values are not assumed to be portable.
