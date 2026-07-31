#!/usr/bin/env python3
"""Capture exactly one reproducible Codex forward-evaluation session."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback


MODEL = "gpt-5.6-sol"
REASONING_EFFORT = "low"
ASSEMBLY_FAILURE = 70
REFUSED_RERUN = 64

PROMPT = Path("prompt.md")
ARTIFACT = Path("ARTIFACT.md")
RESPONSE = Path("response.md")
EVENTS = Path("events.jsonl")
CODEX_STDERR = Path("codex-stderr.txt")
EVALUATOR_STDERR = Path("evaluator-stderr.txt")
CODEX_VERSION = Path("codex-version.txt")
CODEX_EXIT = Path("cli-exit-code.txt")
EVALUATOR_EXIT = Path("evaluator-exit-code.txt")
STARTED_AT = Path("started-at.txt")
ENDED_AT = Path("ended-at.txt")
THREAD_ID = Path("thread-id.txt")
CAPTURE = Path("session-capture.json")
RUN_LOCK = Path(".vibeworthy-forward-capture.lock")

OUTPUTS = (
    RESPONSE,
    EVENTS,
    CODEX_STDERR,
    EVALUATOR_STDERR,
    CODEX_VERSION,
    CODEX_EXIT,
    EVALUATOR_EXIT,
    STARTED_AT,
    ENDED_AT,
    THREAD_ID,
    CAPTURE,
    RUN_LOCK,
)


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def portable_exit(status: int) -> int:
    if status < 0:
        return min(255, 128 + abs(status))
    return min(255, status)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one Codex forward-evaluation session and preserve its exact evidence."
    )
    parser.add_argument(
        "--codex-bin",
        default="codex",
        help="Codex executable path (default: codex from PATH)",
    )
    parser.add_argument(
        "--codex-prefix-arg",
        action="append",
        default=[],
        help="argument inserted after the executable and before --version/exec (repeatable)",
    )
    return parser.parse_args()


def validate_inputs() -> None:
    missing = [str(path) for path in (PROMPT, ARTIFACT) if not path.is_file()]
    if missing:
        raise ValueError(f"missing required regular input file(s): {', '.join(missing)}")


def refuse_overwrite() -> None:
    existing = [str(path) for path in OUTPUTS if path.exists()]
    if existing:
        raise FileExistsError(
            "refusing to overwrite or rerun a captured session; existing output(s): "
            + ", ".join(existing)
        )


def acquire_lock() -> None:
    descriptor = os.open(RUN_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as lock:
        lock.write("claimed\n")


def load_and_validate_events() -> tuple[list[dict[str, object]], str, str]:
    events: list[dict[str, object]] = []
    for line_number, line in enumerate(EVENTS.read_text(encoding="utf-8").splitlines(), start=1):
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"events.jsonl line {line_number} is not valid JSON") from error
        if not isinstance(event, dict):
            raise ValueError(f"events.jsonl line {line_number} is not an object")
        events.append(event)

    if not events:
        raise ValueError("events.jsonl contains no events")
    thread_ids = {
        str(event["thread_id"])
        for event in events
        if event.get("type") == "thread.started" and event.get("thread_id")
    }
    if len(thread_ids) != 1:
        raise ValueError(f"expected one Codex thread ID, found {len(thread_ids)}")
    for event_type in ("thread.started", "turn.started", "turn.completed"):
        count = sum(event.get("type") == event_type for event in events)
        if count != 1:
            raise ValueError(f"expected one {event_type} event, found {count}")
    if events[-1].get("type") != "turn.completed":
        raise ValueError("the final event is not turn.completed")

    messages = [
        str(item["text"])
        for event in events
        if event.get("type") == "item.completed"
        and isinstance((item := event.get("item")), dict)
        and item.get("type") == "agent_message"
        and "text" in item
    ]
    if not messages:
        raise ValueError("no completed agent message was captured")
    if not RESPONSE.is_file():
        raise ValueError("Codex did not write response.md")
    response = RESPONSE.read_text(encoding="utf-8")
    if response != messages[-1]:
        raise ValueError("response.md differs from the final completed agent message")
    return events, next(iter(thread_ids)), response


def main() -> int:
    args = parse_args()
    try:
        validate_inputs()
        refuse_overwrite()
        acquire_lock()
    except (FileExistsError, ValueError) as error:
        print(f"forward evaluator: {error}", file=sys.stderr)
        return REFUSED_RERUN

    codex_status: int | None = None
    evaluator_status = 0
    EVALUATOR_STDERR.write_bytes(b"")
    STARTED_AT.write_text(utc_now() + "\n", encoding="utf-8")

    try:
        input_hashes_before = {
            "prompt": sha256(PROMPT),
            "artifact": sha256(ARTIFACT),
        }
        codex_command = [args.codex_bin, *args.codex_prefix_arg]
        version = subprocess.run(
            [*codex_command, "--version"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        CODEX_VERSION.write_bytes(version.stdout)
        with EVALUATOR_STDERR.open("ab") as evaluator_stderr:
            evaluator_stderr.write(version.stderr)
        if version.returncode != 0:
            raise RuntimeError(f"Codex version command exited {version.returncode}")

        command = [
            *codex_command,
            "exec",
            "--ephemeral",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "--json",
            "--model",
            MODEL,
            "--config",
            f'model_reasoning_effort="{REASONING_EFFORT}"',
            "--output-last-message",
            str(RESPONSE),
            "-",
        ]
        with (
            PROMPT.open("rb") as prompt,
            EVENTS.open("wb") as events,
            CODEX_STDERR.open("wb") as codex_stderr,
        ):
            completed = subprocess.run(
                command,
                check=False,
                stdin=prompt,
                stdout=events,
                stderr=codex_stderr,
            )
        codex_status = completed.returncode
        CODEX_EXIT.write_text(str(codex_status) + "\n", encoding="utf-8")
        ENDED_AT.write_text(utc_now() + "\n", encoding="utf-8")

        events, thread_id, _response = load_and_validate_events()
        THREAD_ID.write_text(thread_id + "\n", encoding="utf-8")
        input_hashes_after = {
            "prompt": sha256(PROMPT),
            "artifact": sha256(ARTIFACT),
        }
        if input_hashes_after != input_hashes_before:
            raise RuntimeError("prompt.md or ARTIFACT.md changed during the Codex session")
        capture = {
            "schema_version": "1.0",
            "model": MODEL,
            "reasoning_effort": REASONING_EFFORT,
            "thread_id": thread_id,
            "started_at": STARTED_AT.read_text(encoding="utf-8").strip(),
            "ended_at": ENDED_AT.read_text(encoding="utf-8").strip(),
            "codex_exit": codex_status,
            "event_counts": {
                "thread_started": sum(event.get("type") == "thread.started" for event in events),
                "turn_started": sum(event.get("type") == "turn.started" for event in events),
                "turn_completed": sum(event.get("type") == "turn.completed" for event in events),
            },
            "response_matches_last_agent_message": True,
            "inputs_unchanged": True,
            "sha256": {
                **input_hashes_before,
                "response": sha256(RESPONSE),
                "events": sha256(EVENTS),
                "codex_stderr": sha256(CODEX_STDERR),
            },
        }
        CAPTURE.write_text(
            json.dumps(capture, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except KeyboardInterrupt:
        evaluator_status = 130
        with EVALUATOR_STDERR.open("a", encoding="utf-8") as evaluator_stderr:
            evaluator_stderr.write("forward evaluator interrupted\n")
            traceback.print_exc(file=evaluator_stderr)
    except Exception:  # Preserve all evaluator failures without replacing the Codex record.
        evaluator_status = ASSEMBLY_FAILURE
        with EVALUATOR_STDERR.open("a", encoding="utf-8") as evaluator_stderr:
            evaluator_stderr.write("forward evaluator assembly failure\n")
            traceback.print_exc(file=evaluator_stderr)
    finally:
        if not ENDED_AT.exists():
            ENDED_AT.write_text(utc_now() + "\n", encoding="utf-8")
        if codex_status is None and not CODEX_EXIT.exists():
            CODEX_EXIT.write_text("unavailable\n", encoding="utf-8")
        EVALUATOR_EXIT.write_text(str(evaluator_status) + "\n", encoding="utf-8")

    if evaluator_status != 0:
        return evaluator_status
    assert codex_status is not None
    return portable_exit(codex_status)


if __name__ == "__main__":
    raise SystemExit(main())
