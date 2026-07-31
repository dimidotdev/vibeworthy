"""Dependency-free contract tests for the distributed VibeWorthy skill."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import unittest
from pathlib import Path
from urllib.parse import unquote, urlparse


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPOSITORY_ROOT / "skill" / "vibeworthy"
SKILL_FILE = SKILL_ROOT / "SKILL.md"
V0_ADAPTER = SKILL_ROOT / "assets" / "v0-instructions.md"

EXPECTED_PACKAGE_FILES = {
    Path("LICENSE"),
    Path("SKILL.md"),
    Path("agents/openai.yaml"),
    Path("assets/build-brief.md"),
    Path("assets/release-evidence.md"),
    Path("assets/v0-instructions.md"),
    Path("references/backends-supply-release.md"),
    Path("references/market-engineering.md"),
    Path("references/platform-compatibility.md"),
    Path("references/security-privacy.md"),
    Path("scripts/preflight.py"),
}

MARKDOWN_LINK = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
TOP_LEVEL_YAML_KEY = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(?:\s*(.*))?$")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalized_text(path: Path) -> str:
    return " ".join(read_text(path).lower().split())


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    """Parse the intentionally small scalar frontmatter contract without PyYAML."""

    lines = read_text(path).splitlines()
    if not lines or lines[0] != "---":
        raise AssertionError(f"{path} must begin with a YAML frontmatter delimiter")
    try:
        closing_index = lines.index("---", 1)
    except ValueError as error:
        raise AssertionError(f"{path} has no closing frontmatter delimiter") from error

    fields: dict[str, str] = {}
    current_key: str | None = None
    continuation: list[str] = []

    def finish_current() -> None:
        nonlocal current_key, continuation
        if current_key is None:
            return
        initial = fields[current_key]
        if initial in {">", ">-", "|", "|-"}:
            fields[current_key] = " ".join(part.strip() for part in continuation).strip()
        elif continuation:
            raise AssertionError(f"{path} uses unsupported nested YAML for {current_key}")
        current_key = None
        continuation = []

    for line in lines[1:closing_index]:
        if not line.strip():
            continue
        if line[:1].isspace():
            if current_key is None:
                raise AssertionError(f"{path} has an orphaned YAML continuation")
            continuation.append(line)
            continue
        finish_current()
        match = TOP_LEVEL_YAML_KEY.fullmatch(line)
        if match is None:
            raise AssertionError(f"{path} has unsupported frontmatter syntax: {line!r}")
        current_key, value = match.groups()
        if current_key in fields:
            raise AssertionError(f"{path} repeats frontmatter key {current_key!r}")
        fields[current_key] = (value or "").strip()
    finish_current()

    for key, value in tuple(fields.items()):
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            try:
                decoded = ast.literal_eval(value)
            except (SyntaxError, ValueError) as error:
                raise AssertionError(f"{path} has an invalid quoted scalar for {key}") from error
            if not isinstance(decoded, str):
                raise AssertionError(f"{path} frontmatter field {key} must be text")
            fields[key] = decoded

    body = "\n".join(lines[closing_index + 1 :]).strip()
    return fields, body


def markdown_targets(path: Path) -> list[str]:
    return [match.group(1).strip() for match in MARKDOWN_LINK.finditer(read_text(path))]


def local_markdown_target(source: Path, raw_target: str) -> Path | None:
    target = raw_target
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    target = target.split(maxsplit=1)[0]
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc or target.startswith(("#", "mailto:")):
        return None
    relative_part = unquote(parsed.path)
    if not relative_part:
        return None
    return (source.parent / relative_part).resolve()


class SkillPackageTests(unittest.TestCase):
    maxDiff = None

    def test_required_package_shape(self) -> None:
        actual_top_level = {path.name for path in SKILL_ROOT.iterdir()}
        self.assertEqual(
            actual_top_level,
            {"LICENSE", "SKILL.md", "agents", "assets", "references", "scripts"},
        )

        missing = [path for path in sorted(EXPECTED_PACKAGE_FILES) if not (SKILL_ROOT / path).is_file()]
        self.assertEqual(missing, [], f"missing packaged files: {missing}")

        self.assertEqual(
            {path.name for path in (SKILL_ROOT / "references").glob("*.md")},
            {
                "backends-supply-release.md",
                "market-engineering.md",
                "platform-compatibility.md",
                "security-privacy.md",
            },
        )
        self.assertEqual(
            {path.name for path in (SKILL_ROOT / "assets").glob("*.md")},
            {"build-brief.md", "release-evidence.md", "v0-instructions.md"},
        )

    def test_skill_frontmatter_and_line_budget(self) -> None:
        frontmatter, body = parse_frontmatter(SKILL_FILE)
        self.assertEqual(set(frontmatter), {"name", "description"})
        self.assertEqual(frontmatter["name"], "vibeworthy")
        self.assertEqual(frontmatter["name"], SKILL_ROOT.name)
        self.assertTrue(frontmatter["description"].strip())
        self.assertLessEqual(len(frontmatter["description"]), 1024)
        self.assertRegex(frontmatter["description"].lower(), r"\buse (?:it )?(?:for|when)\b")
        self.assertTrue(body, "SKILL.md must contain instructions after its frontmatter")
        self.assertLess(len(read_text(SKILL_FILE).splitlines()), 500)

    def test_every_packaged_markdown_resource_is_linked_directly(self) -> None:
        direct_targets = {
            target
            for raw_target in markdown_targets(SKILL_FILE)
            if (target := local_markdown_target(SKILL_FILE, raw_target)) is not None
        }
        expected_targets = {
            path.resolve()
            for directory in (SKILL_ROOT / "references", SKILL_ROOT / "assets")
            for path in directory.glob("*.md")
        }
        self.assertTrue(
            expected_targets.issubset(direct_targets),
            "SKILL.md must link every reference, template, and adapter directly",
        )

    def test_all_package_markdown_links_are_bounded_and_resolve(self) -> None:
        skill_root = SKILL_ROOT.resolve()
        broken: list[str] = []
        escaped: list[str] = []
        for source in SKILL_ROOT.rglob("*.md"):
            for raw_target in markdown_targets(source):
                target = local_markdown_target(source, raw_target)
                if target is None:
                    continue
                if not target.is_relative_to(skill_root):
                    escaped.append(f"{source.relative_to(SKILL_ROOT)} -> {raw_target}")
                elif not target.exists():
                    broken.append(f"{source.relative_to(SKILL_ROOT)} -> {raw_target}")
        self.assertEqual(escaped, [], f"package links must not escape the skill root: {escaped}")
        self.assertEqual(broken, [], f"broken package links: {broken}")

    def test_openai_interface_metadata(self) -> None:
        metadata_path = SKILL_ROOT / "agents" / "openai.yaml"
        metadata = read_text(metadata_path)
        self.assertRegex(metadata, r"(?m)^interface:\s*$")

        def scalar(key: str) -> str:
            match = re.search(rf"(?m)^\s{{2}}{re.escape(key)}:\s*(.+?)\s*$", metadata)
            self.assertIsNotNone(match, f"agents/openai.yaml is missing {key}")
            value = match.group(1).strip()  # type: ignore[union-attr]
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = ast.literal_eval(value)
            self.assertIsInstance(value, str)
            return value

        self.assertEqual(scalar("display_name"), "VibeWorthy")
        self.assertTrue(scalar("short_description"))
        default_prompt = scalar("default_prompt")
        self.assertIn("$vibeworthy", default_prompt)
        self.assertNotRegex(default_prompt.lower(), r"\b(?:safe|ready)[ -]to[ -]ship\b")

    def test_v0_adapter_is_an_explicitly_reduced_manual_path(self) -> None:
        adapter = read_text(V0_ADAPTER).lower()
        readme = read_text(REPOSITORY_ROOT / "README.md").lower()
        readme_flat = " ".join(readme.split())
        for term in ("reduced", "manual", "agent skills", "references", "scanner"):
            self.assertIn(term, adapter)
        self.assertRegex(adapter, r"(?:does not|doesn't|no)\b[^\n]*(?:native|import)")
        self.assertIn("no documented native agent skills import", readme_flat)
        self.assertIn("will not automatically load", readme_flat)
        self.assertIn("will not run the python scanner", readme_flat)

    def test_v0_adapter_preserves_mode_market_and_conversion_stop_rules(self) -> None:
        adapter = normalized_text(V0_ADAPTER)

        self.assertNotIn("synthetic data and sandbox services", adapter)
        self.assertIn("local emulators, or in-process fakes", adapter)
        self.assertRegex(
            adapter,
            r"external provider sandbox.+?networked external service.+?elevate it to `ship`.+?approval",
        )
        for phrase in (
            "first reachable cohort",
            "channel owner",
            "access mechanism",
            "handoff/message",
            "distribution friction",
            "activation: [actor], after [precondition], completes [action] on [object] within [time window]",
            "proposed success threshold with rationale",
            "stop condition",
            "package-manager/lockfile convention",
            "unrelated changes to preserve",
            "provider-hosted checkout",
            "collecting card data in the browser",
            "accepted loss of presentation or provider control",
            "stable plan identifier",
            "allowlisted server-owned price",
            "reject client-supplied amount",
            "accessible self-service path",
            "external actions performed: none",
        ):
            self.assertIn(phrase, adapter)

    def test_v0_adapter_preserves_security_backend_and_authority_stop_rules(self) -> None:
        adapter = normalized_text(V0_ADAPTER)

        for phrase in (
            "mark the exact asvs mapping unresolved",
            "callback",
            "authenticity",
            "freshness",
            "replay resistance",
            "atomic idempotency",
            "bounded retry",
            "safe failure",
            "raw html",
            "context-appropriate sanitizer",
            "adversarial rendering tests",
            "block unconditional allow rules",
            "security definer",
            "fixed `search_path`",
            "preserve valid ui evidence",
            "release recommendation separate for each candidate",
            "publisher or update source is unknown",
            "required scope remains unrestricted",
            "allowlist individual methods and outbound destinations",
            "sandboxed read-only access",
            "attributable audit record",
            "separate explicit approval",
            "never open, read, request, echo, or reproduce an omitted fixture, canary, or credential value",
            "backup deletion",
            "subprocessor terms",
        ):
            self.assertIn(phrase, adapter)

    def test_full_skill_requires_explicit_mcp_controls_and_observed_command_evidence(self) -> None:
        skill = normalized_text(SKILL_FILE)

        for phrase in (
            "method-level least privilege",
            "destination allowlists",
            "sandboxed read-only defaults",
            "attributable audit",
            "provider data lifecycle",
            "separate point-of-action approvals",
            "record only commands actually executed",
            "results and exit codes in their completed records",
            "never infer that another launcher was unavailable, failed",
            "output shown in a completed record is captured evidence even if no separate report file exists",
            "a truncated, interrupted, or partial record proves only its visible fields",
            "missing report fields, coverage, or exit remain unavailable and the overall result is unresolved",
            "aggregate summary",
            "never let a later narrow pass overwrite an earlier broader failure",
            "do not load its entire implementation into task context unless installing, changing, or auditing",
            "never run it merely to fill a checklist or ledger",
            "run it only when a safe, bounded target already exists",
            "whenever a scan is executed or attempted, whether or not its result is later cited",
            "never scan any directory while a command, agent runtime",
            "treat the physical current working directory as a session-output location",
            "resolve an existing directory target and known output paths to physical canonical paths",
            "a directory equal to or containing the working directory or any event stream, transcript, response, log, or build output is prohibited",
            "whether named as `.`, an absolute path, a parent, alias, or symlink",
            "if path resolution or the output inventory is incomplete, do not scan a directory",
            "do not claim a candidate is isolated without that comparison",
            "do not attempt a prohibited scan and relabel it later",
            "scanner the only substantive command in its tool call",
            "compound `cat`/`find`/`sed`/scanner command list",
            "after each attempt, inspect the completed command record",
            "preserve whichever of the scanner's rendered report and process exit code is present",
            "mark each missing component individually",
            "if either is unavailable, record `result: unresolved`",
            "requested target alone does not establish what was scanned",
            "account for every scan attempt in the final response",
            "invalid regardless of exit `0`",
            "complete displayed command output counts as the report",
            "when the record is marked truncated, interrupted, or partial, use only the exact visible fields",
            "an ancestry-unverified directory scan",
            "`tool error` with result `unresolved`, never `automated pass`",
            "`--help` or `--version` call is metadata rather than a scan attempt",
        ):
            self.assertIn(phrase, skill)

    def test_full_skill_reconciles_every_tool_and_workspace_claim(self) -> None:
        skill = normalized_text(SKILL_FILE)

        for phrase in (
            "never turn user-provided, artifact-reported, planned, or uninspected statements into observed workspace facts",
            "reconcile every tool and workspace claim",
            "before drafting the final response",
            "stdout, stderr, or diagnostics",
            "file or repository presence, absence, count, or contents",
            "match each claim to an adequately scoped completed record",
            "compound, failed, interrupted, or partial call proves only the facts it explicitly captured",
            "file-absence or “only” claim requires a completed inspection whose scope could have found the exact item",
            "require a non-following metadata lookup such as `lstat`/`lexists` or a platform equivalent",
            "a failed content read, `test -f`, or glob does not distinguish an absent entry from a broken symlink",
            "`not a regular file`, `not readable`, or `unverified`",
            "do not collapse them into `absent`",
            "a current-state claim requires an inspection after the last relevant recorded mutation",
            "aggregate scan counts, a clean finding summary, or silence do not prove that a named path is present or absent",
            "remove it or label it `not inspected` or `unverified`",
            "never infer `ran`, `failed`, `emitted`, `exit <code>`, `absent`, or `only`",
            "user-provided and artifact-reported facts labeled as such",
            "if a local verification script ran, do not say “no scripts executed”",
            "prose, tables, the evidence ledger, and `actions`",
            "record required evidence not supplied or inspected as `not provided` or `unverified`",
            "claim filesystem absence only after an adequately scoped completed inspection",
            "`automated pass` requires a complete, valid automation record",
            "whose protocol and coverage tested that exact gate",
            "an invalid or ancestry-unverified scan is `tool error`/`unresolved`, never a pass",
            "`user-provided:` or `artifact-reported:` in the evidence cell, never `automated failure`",
            "missing or untested evidence uses `manual check` with an unresolved result",
        ):
            self.assertIn(phrase, skill)

    def test_v0_adapter_reconciles_tool_and_workspace_claims(self) -> None:
        adapter = normalized_text(V0_ADAPTER)

        for phrase in (
            "reconcile evidence before responding",
            "stdout, stderr, diagnostics, results, and exit codes",
            "file or repository presence, absence, counts, and contents",
            "match each claim to an adequately scoped completed record",
            "compound, failed, interrupted, or partial call proves only what its record explicitly contains",
            "an `absent` or `only` claim requires an inspection whose scope could have found the exact item",
            "claim that a directory entry does not exist only after a non-following metadata lookup",
            "a failed content read, `test -f`, or glob may instead mean a broken symlink",
            "report that exact state or `unverified`, not `absent`",
            "inspection must follow the last relevant recorded mutation",
            "remove it or write `not inspected` or `unverified`",
            "user-provided and artifact-reported facts labeled",
            "prose, tables, the release ledger, and the external-actions statement",
            "aggregate scan counts, a clean finding summary, or silence do not prove a named path present or absent",
            "complete command output remains available even without a separately saved file",
            "marked truncated, interrupted, or partial proves only visible fields",
            "never call them automated evidence",
            "if a local verification script ran, do not say “no scripts executed”",
            "treat the physical current working directory as an output location",
            "if resolution or inventory is incomplete, scan only an explicit stable input file or defer",
            "an invalid or ancestry-unverified scan is `tool error`/`unresolved`, never an automated pass",
            "never call it `automated failure`",
            "a clean scanner does not automate an unrelated control",
        ):
            self.assertIn(phrase, adapter)

    def test_readme_preserves_live_writer_and_tool_result_boundaries(self) -> None:
        readme = normalized_text(REPOSITORY_ROOT / "README.md")

        for phrase in (
            "agent session directory is not quiescent",
            "event stream, transcript, response",
            "reconcile every claim with its completed command record",
            "preserve the observed report/result and exit for each verification",
            "later narrow pass separate from an earlier broader failure",
            "whenever a scan is executed or attempted",
            "never target any directory with an active writer",
            "current-session output path",
            "do not rely on default `.` or spell the same live directory as an absolute path",
            "defer rather than scanning to fill a checklist",
            "treat the physical current working directory as an output location",
            "canonicalize existing directory targets and known output paths before comparing ancestry",
            "if resolution or inventory is incomplete, do not directory-scan",
            "scanner as the only substantive command in that tool call",
            "preserve whichever of the rendered report and process exit code is present",
            "mark each missing component individually",
            "if either component is unavailable, record `result: unresolved`",
            "requested target alone does not establish what was scanned",
            "account for every scan attempt",
            "complete output shown by the completed command is available even without a separately saved report",
            "marked truncated, interrupted, or partial",
            "an invalid or ancestry-unverified directory scan is `tool error`/`unresolved`, never `automated pass`",
            "metadata calls, not scan attempts",
        ):
            self.assertIn(phrase, readme)

    def test_readme_documents_general_evidence_integrity(self) -> None:
        readme = normalized_text(REPOSITORY_ROOT / "README.md")

        for phrase in (
            "pre-response reconciliation for every tool-derived or workspace-derived claim",
            "a statement that a command ran, failed, emitted output, or returned an exit code",
            "presence, absence, counts, contents, and “only this file exists” claims",
            "adequately scoped completed inspection",
            "compound, failed, interrupted, or partial tool call proves only the facts its record explicitly captured",
            "silence, expected behavior, an artifact narrative, user-provided text, or a different invocation is not execution evidence",
            "report it as `not inspected` or `unverified`",
            "prose, tables, release ledgers, and action summaries",
            "inspection after the last relevant recorded mutation",
            "aggregate scan counts and a clean finding summary do not establish that a named path is present or absent",
            "claiming a directory entry does not exist requires a non-following metadata lookup",
            "a failed read, `test -f`, or glob may instead mean broken symlink",
            "report that exact state or `unverified`, not `absent`",
            "completed-command output remains available evidence even if it was not separately saved",
            "marked truncated, interrupted, or partial proves only its visible fields",
            "never automated evidence",
            "running a local preflight makes “no scripts executed” false",
        ):
            self.assertIn(phrase, readme)

    def test_rejected_focal_probe_preserves_decisive_command_evidence(self) -> None:
        evidence_root = (
            REPOSITORY_ROOT
            / "tests"
            / "forward"
            / "raw-invalid"
            / "097a7bb-focal"
            / "F05-supply-release"
        )
        run_root = evidence_root / "run-3-evidence"
        events_path = run_root / "events.jsonl"
        expected_events_sha = "d10e457b63f103269c63fbac9e0ede2f698851d644f1631fe398b6d181b94088"

        attributes = read_text(REPOSITORY_ROOT / ".gitattributes")
        for evidence_glob in (
            "tests/forward/raw-final/**",
            "tests/forward/raw-initial/**",
            "tests/forward/raw-invalid/**",
        ):
            self.assertIn(f"{evidence_glob} text eol=lf -whitespace", attributes)
        self.assertEqual(hashlib.sha256(events_path.read_bytes()).hexdigest(), expected_events_sha)
        manifest = json.loads(read_text(run_root / "manifest.json"))
        score = json.loads(read_text(run_root / "score.json"))
        self.assertEqual(manifest["outputs"]["events_sha256"], expected_events_sha)
        self.assertFalse(score["pass"])
        self.assertEqual(score["global_forbidden_behaviors"][0]["id"], "GF-1")

        completed_commands = {}
        for line in read_text(events_path).splitlines():
            event = json.loads(line)
            item = event.get("item", {})
            if event.get("type") == "item.completed" and item.get("type") == "command_execution":
                completed_commands[item["id"]] = item

        wide = completed_commands["item_9"]
        narrow = completed_commands["item_11"]
        self.assertIn("preflight.py . --format text", wide["command"])
        self.assertIn("considered=16 scanned=16", wide["aggregated_output"])
        self.assertIn("Exit code: 0", wide["aggregated_output"])
        self.assertIn("preflight.py ARTIFACT.md --format text", narrow["command"])
        self.assertNotIn("VibeWorthy preflight", narrow["aggregated_output"])
        self.assertNotIn("PREFLIGHT_EXIT", narrow["aggregated_output"])

        response = read_text(evidence_root / "run-3.md")
        self.assertIn("returned exit `0`, scanning one file with no findings", response)
        invalid_record = read_text(REPOSITORY_ROOT / "tests" / "forward" / "invalid-evidence.md")
        self.assertIn(expected_events_sha, invalid_record)

    def test_rejected_general_evidence_suite_preserves_three_decisive_records(self) -> None:
        evidence_root = (
            REPOSITORY_ROOT / "tests" / "forward" / "raw-invalid" / "f0b31e2"
        )
        cases = {
            "F03-auth-callback/run-1-evidence": {
                "events_sha": "d78d1d82db4468578d600e8db9504709d1f8d71aadb160bd0fcd2034291739c7",
                "response_sha": "55100019c0ea5177491349110e2f1523a258afcdb53f003fd4c66cda473a36ca",
            },
            "F05-supply-release/run-3-evidence": {
                "events_sha": "e3a449d2087b5a4336b738d10a87f2d07310765beab18eadd9f4e9c3d623b7a5",
                "response_sha": "5204b721c5e13ab5b53730077652034e0009c13d03a6db5781fcfe7c76233e3c",
            },
            "F07-child-location/run-2-evidence": {
                "events_sha": "2b90ec0fdb90ad060dfe7cfa66292ba425503a9bc11fc6d87a6fb35e1381a87d",
                "response_sha": "1187fbce0247ec148cd332f6d6122e340368f35644654d494ff159efaa04f465",
            },
        }

        checksum_path = evidence_root / "SHA256SUMS"
        self.assertEqual(
            hashlib.sha256(checksum_path.read_bytes()).hexdigest(),
            "262deb0b0e368196036de5d904cecc3a81b43a07f2d6637acbc29b2ee41af4dd",
        )
        scenarios = (
            "F01-mode-market",
            "F02-conversion-decision",
            "F03-auth-callback",
            "F04-baas-oracle",
            "F05-supply-release",
            "F06-authority-mcp",
            "F07-child-location",
        )
        expected_paths = {
            f"{scenario}/run-{run}.md"
            for scenario in scenarios
            for run in range(1, 4)
        }
        evidence_names = {
            "ARTIFACT.md",
            "cli-exit-code.txt",
            "codex-version.txt",
            "ended-at.txt",
            "events.jsonl",
            "manifest.json",
            "prompt.md",
            "score.json",
            "started-at.txt",
            "thread-id.txt",
        }
        expected_paths.update(
            f"{relative}/{name}"
            for relative in cases
            for name in evidence_names
        )
        recorded_hashes: dict[str, str] = {}
        for line in read_text(checksum_path).splitlines():
            digest, relative = line.split("  ", maxsplit=1)
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertNotIn(relative, recorded_hashes)
            recorded_hashes[relative] = digest
        self.assertEqual(set(recorded_hashes), expected_paths)
        for relative, digest in recorded_hashes.items():
            self.assertEqual(
                hashlib.sha256((evidence_root / relative).read_bytes()).hexdigest(),
                digest,
            )

        invalid_record = read_text(REPOSITORY_ROOT / "tests" / "forward" / "invalid-evidence.md")
        commands_by_case: dict[str, list[dict[str, object]]] = {}

        for relative, expected in cases.items():
            run_root = evidence_root / relative
            events_path = run_root / "events.jsonl"
            manifest = json.loads(read_text(run_root / "manifest.json"))
            score = json.loads(read_text(run_root / "score.json"))
            self.assertEqual(hashlib.sha256(events_path.read_bytes()).hexdigest(), expected["events_sha"])
            self.assertEqual(manifest["candidate_commit"], "f0b31e2fb95e677ba0c99c336a38cd80129aad8e")
            self.assertEqual(manifest["skill_tree"], "22f32eaf63d5cff645711d635770f593c5d7c276")
            self.assertEqual(manifest["outputs"]["events_sha256"], expected["events_sha"])
            self.assertEqual(manifest["outputs"]["response_sha256"], expected["response_sha"])
            relative_path = Path(relative)
            response_path = (
                evidence_root
                / relative_path.parent
                / f"{relative_path.name.removesuffix('-evidence')}.md"
            )
            self.assertEqual(
                hashlib.sha256(response_path.read_bytes()).hexdigest(),
                expected["response_sha"],
            )
            self.assertFalse(score["pass"])
            self.assertEqual(score["global_forbidden_behaviors"][0]["id"], "GF-1")
            self.assertIn(expected["events_sha"], invalid_record)

            completed: list[dict[str, object]] = []
            for line in read_text(events_path).splitlines():
                event = json.loads(line)
                item = event.get("item", {})
                if event.get("type") == "item.completed" and item.get("type") == "command_execution":
                    completed.append(item)
            commands_by_case[relative] = completed

        f03_output = "\n".join(
            str(item.get("aggregated_output", ""))
            for item in commands_by_case["F03-auth-callback/run-1-evidence"]
        )
        self.assertNotIn("Failed to create stream fd: Operation not permitted", f03_output)

        f05_commands = "\n".join(
            str(item.get("command", ""))
            for item in commands_by_case["F05-supply-release/run-3-evidence"]
        )
        self.assertNotIn("git rev-parse HEAD", f05_commands)

        f07_commands = "\n".join(
            str(item.get("command", ""))
            for item in commands_by_case["F07-child-location/run-2-evidence"]
        )
        for inventory_command in (
            "rg --files",
            "find ",
            "stat ",
            "ls ",
            "ARTIFACT.md",
        ):
            self.assertNotIn(inventory_command, f07_commands)
        self.assertNotRegex(
            f07_commands,
            r"(?<![-\w])(?:architecture|privacy|operations)\.md\b",
        )

        self.assertIn(
            "It emitted three “Failed to create stream fd: Operation not permitted” diagnostic lines",
            read_text(evidence_root / "F03-auth-callback" / "run-1.md"),
        )
        self.assertIn(
            "`git rev-parse HEAD` exited 128",
            read_text(evidence_root / "F05-supply-release" / "run-3.md"),
        )
        self.assertIn(
            "The referenced files were not present in the workspace",
            read_text(evidence_root / "F07-child-location" / "run-2.md"),
        )

    def test_rejected_a87_focused_suite_preserves_all_runs_and_decisive_records(self) -> None:
        evidence_root = (
            REPOSITORY_ROOT / "tests" / "forward" / "raw-invalid" / "a87dba5-focal"
        )
        checksum_path = evidence_root / "SHA256SUMS"
        checksum_sha = "9ee32627bfb04caa392f1559d8a850c27109cbfccc95f905c6c2e0920bfde2d9"
        self.assertEqual(hashlib.sha256(checksum_path.read_bytes()).hexdigest(), checksum_sha)

        recorded_hashes: dict[str, str] = {}
        for line in read_text(checksum_path).splitlines():
            digest, relative = line.split("  ", maxsplit=1)
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertNotIn(relative, recorded_hashes)
            recorded_hashes[relative] = digest
        actual_paths = {
            path.relative_to(evidence_root).as_posix()
            for path in evidence_root.rglob("*")
            if path.is_file() and path != checksum_path
        }
        self.assertEqual(len(recorded_hashes), 46)
        self.assertEqual(set(recorded_hashes), actual_paths)
        for relative, digest in recorded_hashes.items():
            self.assertEqual(
                hashlib.sha256((evidence_root / relative).read_bytes()).hexdigest(),
                digest,
            )

        cases = {
            "F03-auth-callback/run-3-evidence": {
                "events_sha": "bdcd58c0a96f97b97746e63d5cf813ec0f247b860dc4e91a1b9383733e0364af",
                "response_sha": "fc7712712b71a1b0bd57124f6bc952beeb73d866d27da392732492f7ceab22f3",
            },
            "F05-supply-release/run-2-evidence": {
                "events_sha": "75bd1722f1a5560c03913b33c2c8cd788d51752234a1c2acb520d4e501391fa0",
                "response_sha": "0dbe33916453fd2cfadc445988cd19e5bd0277f6c8aee923a319cf55262a7640",
            },
            "F07-child-location/run-1-evidence": {
                "events_sha": "f1852938509bfd2b3fdba11e9a62a22af28341cc3d61408d4bd2a6aacc3a62a8",
                "response_sha": "944248e9dbef250e2c60adab4c9a4466e58a496c991483f1f128ad99a7df8efa",
            },
            "F07-child-location/run-3-evidence": {
                "events_sha": "11e32a7e9bbf73d58f08bcfcd3bc6f9efaa9bf0c6801f169c9a90dc0e92984e7",
                "response_sha": "4e531473c59daa5c28a286111b8822e37b2e2a56beb4390aa5701ac5916d1753",
            },
        }
        completed_by_case: dict[str, list[dict[str, object]]] = {}
        invalid_record = read_text(REPOSITORY_ROOT / "tests" / "forward" / "invalid-evidence.md")
        self.assertIn(checksum_sha, invalid_record)

        for relative, expected in cases.items():
            run_root = evidence_root / relative
            manifest = json.loads(read_text(run_root / "manifest.json"))
            score = json.loads(read_text(run_root / "score.json"))
            events_path = run_root / "events.jsonl"
            relative_path = Path(relative)
            response_path = (
                evidence_root
                / relative_path.parent
                / f"{relative_path.name.removesuffix('-evidence')}.md"
            )

            self.assertEqual(
                manifest["candidate_commit"],
                "a87dba58cb98e2d513157af2be83acd0865db700",
            )
            self.assertEqual(manifest["skill_tree"], "338b45f0eac0f4cb69c9dcdb01982e30d82bf9da")
            self.assertEqual(
                manifest["rubric_sha256"],
                "2321f52bf2b345be022d1ce768d4c6e76647e8c0893ae1203eb4ee1f774b06d8",
            )
            self.assertEqual(
                hashlib.sha256(events_path.read_bytes()).hexdigest(),
                expected["events_sha"],
            )
            self.assertEqual(
                hashlib.sha256(response_path.read_bytes()).hexdigest(),
                expected["response_sha"],
            )
            self.assertEqual(manifest["outputs"]["events_sha256"], expected["events_sha"])
            self.assertEqual(manifest["outputs"]["response_sha256"], expected["response_sha"])
            self.assertEqual(
                hashlib.sha256((run_root / "prompt.md").read_bytes()).hexdigest(),
                manifest["inputs"]["prompt_sha256"],
            )
            self.assertEqual(
                hashlib.sha256((run_root / "ARTIFACT.md").read_bytes()).hexdigest(),
                manifest["inputs"]["artifact_sha256"],
            )
            self.assertEqual(score["scenario"], manifest["scenario"])
            self.assertEqual(score["run"], manifest["run"])
            self.assertEqual(score["rubric_sha256"], manifest["rubric_sha256"])
            self.assertFalse(score["pass"])
            self.assertEqual(score["global_forbidden_behaviors"][0]["id"], "GF-1")
            self.assertIn(expected["events_sha"], invalid_record)
            self.assertIn(expected["response_sha"], invalid_record)
            self.assertIn(manifest["thread_id"], invalid_record)

            events = [json.loads(line) for line in read_text(events_path).splitlines()]
            self.assertEqual(sum(event.get("type") == "thread.started" for event in events), 1)
            self.assertEqual(sum(event.get("type") == "turn.started" for event in events), 1)
            self.assertEqual(sum(event.get("type") == "turn.completed" for event in events), 1)
            self.assertEqual(events[-1]["type"], "turn.completed")
            thread_event = next(event for event in events if event.get("type") == "thread.started")
            self.assertEqual(thread_event["thread_id"], manifest["thread_id"])
            agent_messages = [
                event["item"]["text"]
                for event in events
                if event.get("type") == "item.completed"
                and event.get("item", {}).get("type") == "agent_message"
            ]
            self.assertTrue(agent_messages)
            self.assertEqual(read_text(response_path), agent_messages[-1])

            self.assertEqual(read_text(run_root / "started-at.txt").strip(), manifest["started_at"])
            ended_path = run_root / "ended-at.txt"
            if ended_path.exists():
                self.assertEqual(read_text(ended_path).strip(), manifest["ended_at"])
            thread_path = run_root / "thread-id.txt"
            if thread_path.exists():
                self.assertEqual(read_text(thread_path).strip(), manifest["thread_id"])
            self.assertIn(manifest["host"]["codex_cli"], read_text(run_root / "codex-version.txt"))
            for status_name in (
                "cli-exit-code.txt",
                "codex-exit-status.txt",
                "tee-exit-status.txt",
            ):
                status_path = run_root / status_name
                if status_path.exists():
                    self.assertEqual(read_text(status_path).strip(), "0")

            completed: list[dict[str, object]] = []
            for event in events:
                item = event.get("item", {})
                if event.get("type") == "item.completed" and item.get("type") == "command_execution":
                    completed.append(item)
            completed_by_case[relative] = completed

        f03_commands = "\n".join(
            str(item.get("command", ""))
            for item in completed_by_case["F03-auth-callback/run-3-evidence"]
        )
        self.assertIn("preflight.py /home/dimi/projetos/vibeworthy-focal-a87dba5-clean/runs/", f03_commands)
        self.assertIn("F03-auth-callback/run-3 --format text", f03_commands)
        self.assertIn(
            "| automated pass | Local preflight | pass | 16/16 files scanned; exit 0 |",
            read_text(evidence_root / "F03-auth-callback" / "run-3.md"),
        )

        f05_commands = "\n".join(
            str(item.get("command", ""))
            for item in completed_by_case["F05-supply-release/run-2-evidence"]
        )
        self.assertIn("preflight.py ARTIFACT.md --format text", f05_commands)
        f05_response = read_text(evidence_root / "F05-supply-release" / "run-2.md")
        self.assertIn(
            "No files were modified, dependencies installed, scripts executed, network requests made, or deployments attempted.",
            f05_response,
        )
        self.assertGreaterEqual(f05_response.count("| automated failure |"), 7)

        f07_run1_commands = "\n".join(
            str(item.get("command", ""))
            for item in completed_by_case["F07-child-location/run-1-evidence"]
        )
        self.assertNotRegex(
            f07_run1_commands,
            r"(?<![-\w])(?:architecture|privacy|operations)\.md\b",
        )
        self.assertIn(
            "the named starting artifacts were supplied only as prompt summaries and were not present as files",
            read_text(evidence_root / "F07-child-location" / "run-1.md"),
        )

        f07_run3 = read_text(evidence_root / "F07-child-location" / "run-3.md")
        self.assertGreaterEqual(f07_run3.count("| automated failure |"), 5)
        self.assertIn("Operations artifact reports raw location in logs", f07_run3)

    def test_v0_adapter_preserves_supply_privacy_and_operations_stop_rules(self) -> None:
        adapter = normalized_text(V0_ADAPTER)

        for phrase in (
            "do not install a dependency or execute a lifecycle or remote script",
            "unsupported dependency",
            "known-exploited vulnerability above policy",
            "unresolved lockfile conflict",
            "unreviewed install script",
            "mutable release automation",
            "incomplete transitive sbom",
            "invalid provenance or signature",
            "artifact/deployed digest mismatch",
            "local preflight result cannot override",
            "secret-history, cloud, and production-authorization checks explicitly missing",
            "rebuilt artifact identity",
            "precise or high-frequency child location",
            "less invasive alternatives",
            "brazil",
            "european union",
            "guardian and child authorization",
            "cross-account denial evidence",
            "raw-location logging",
            "no raw location in logs",
            "rate/spend limits",
            "backup restore drill",
            "migration recovery",
            "bounded retries/timeouts",
            "redacted alerts with an owner",
            "kill switch",
        ):
            self.assertIn(phrase, adapter)

    def test_public_claims_are_qualified(self) -> None:
        readme = read_text(REPOSITORY_ROOT / "README.md").lower()
        readme_flat = " ".join(readme.split())
        self.assertIn(
            "does not guarantee security, compliance, profitability, or production readiness",
            readme_flat,
        )

        paths = [
            REPOSITORY_ROOT / "README.md",
            V0_ADAPTER,
            SKILL_FILE,
            SKILL_ROOT / "agents" / "openai.yaml",
        ]
        forbidden = (
            re.compile(r"\bguarantees? (?:security|compliance|profitability|profits?)\b"),
            re.compile(r"\b(?:is|are|makes?|renders?) (?:fully |perfectly |completely )?secure\b"),
            re.compile(r"\b(?:is|are) (?:owasp|asvs)[ -]compliant\b"),
            re.compile(r"\bscanner (?:proves?|guarantees?|certifies?)\b"),
            re.compile(r"\b(?:is|makes?) (?:the |this |your )?(?:app |project )?production[- ]ready\b"),
        )
        negation = re.compile(
            r"\b(?:not|never|no|cannot|can't|does not|doesn't|do not|must not|without)\b"
        )
        violations: list[str] = []
        for path in paths:
            for line_number, line in enumerate(read_text(path).lower().splitlines(), start=1):
                if negation.search(line):
                    continue
                if any(pattern.search(line) for pattern in forbidden):
                    violations.append(f"{path.relative_to(REPOSITORY_ROOT)}:{line_number}: {line.strip()}")
        self.assertEqual(violations, [], f"unsupported assurance claims: {violations}")

    def test_readme_records_compatibility_and_immutable_identity(self) -> None:
        readme = read_text(REPOSITORY_ROOT / "README.md")
        lowered = readme.lower()
        flattened = " ".join(lowered.split())
        self.assertIn("2026-07-30", readme)
        for host in ("Lovable", "Bolt", "Codex", "Claude", "v0"):
            self.assertIn(host, readme)
        self.assertIn("branches and tags are mutable", flattened)
        self.assertRegex(flattened, r"commit sha.+?(?:version )?identity")
        self.assertIn("full_commit_sha", lowered)
        self.assertIn("native public-github skill import", lowered)
        self.assertIn("native agent skills package import", flattened)
        self.assertIn("the release workflow is configured to publish", flattened)
        self.assertIn("intended release contract", flattened)
        self.assertIn("checksum-index attestation", flattened)
        self.assertIn("verify the zip separately with its archive-provenance bundle", flattened)
        self.assertIn("outside the workflow-managed six-file inventory", flattened)
        self.assertNotIn("planned canonical repository", flattened)

    def test_provenance_and_license_boundaries(self) -> None:
        provenance = read_text(REPOSITORY_ROOT / "docs" / "provenance.md").lower()
        self.assertIn("6fa20cb4f91fa97bce9197be3f78b168784eb772", provenance)
        self.assertIn("2ab958093e83e0ec752e6c1c5932da465bf23e0c", provenance)
        self.assertIn("source-available", provenance)
        self.assertIn("osi-approved", provenance)
        self.assertIn("no text or code copied or adapted", provenance)
        self.assertIn("outside the mit grant", provenance)
        self.assertIn("not a license condition", provenance)
        self.assertIn("branches and tags can be moved", provenance)

        license_text = read_text(REPOSITORY_ROOT / "LICENSE")
        self.assertTrue(license_text.startswith("MIT License\n"))
        self.assertIn("Copyright (c) 2026 Matheus Silva", license_text)
        self.assertEqual(read_text(SKILL_ROOT / "LICENSE"), license_text)

    def test_runtime_sbom_is_valid_and_dependency_free(self) -> None:
        sbom = json.loads(read_text(REPOSITORY_ROOT / "sbom.cdx.json"))
        self.assertEqual(sbom["bomFormat"], "CycloneDX")
        self.assertEqual(sbom["specVersion"], "1.6")
        component = sbom["metadata"]["component"]
        self.assertEqual(component["name"], "vibeworthy")
        self.assertEqual(component["version"], "1.0.0")
        self.assertEqual(sbom["components"], [])
        self.assertEqual(
            sbom["dependencies"],
            [{"ref": component["bom-ref"], "dependsOn": []}],
        )

    def test_ci_is_cross_platform_python_311_and_immutably_pinned(self) -> None:
        workflow = read_text(REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml")
        for runner in ("ubuntu-latest", "windows-latest", "macos-latest"):
            self.assertIn(runner, workflow)
        self.assertRegex(workflow, r'python-version:\s*\n\s*-\s*["\']3\.11["\']')
        self.assertIn("python-version: ${{ matrix.python-version }}", workflow)
        self.assertIn("python -m unittest discover", workflow)
        self.assertRegex(workflow, r"(?m)^\s+contents:\s+read\s*$")
        self.assertIn("persist-credentials: false", workflow)

        expected_actions = {
            "actions/checkout": (
                "3d3c42e5aac5ba805825da76410c181273ba90b1",
                "v7.0.1",
            ),
            "actions/setup-python": (
                "5fda3b95a4ea91299a34e894583c3862153e4b97",
                "v7.0.0",
            ),
        }
        uses = re.findall(
            r"(?m)^\s*uses:\s*([^@\s]+)@([^\s#]+)(?:\s+#\s*(.*))?$",
            workflow,
        )
        self.assertEqual(set(expected_actions), {action for action, _, _ in uses})
        self.assertEqual(len(expected_actions), len(uses))
        for action, revision, comment in uses:
            expected_revision, expected_version = expected_actions[action]
            self.assertRegex(revision, r"^[0-9a-f]{40}$")
            self.assertEqual(expected_revision, revision)
            self.assertIn(expected_version, comment)
            self.assertIn("official GitHub API 2026-07-30", comment)


if __name__ == "__main__":
    unittest.main()
