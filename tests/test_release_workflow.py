from __future__ import annotations

import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
import zipfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "release.yml"
FORWARD_README = REPOSITORY_ROOT / "tests" / "forward" / "README.md"
RELEASE_EVIDENCE = (
    REPOSITORY_ROOT / "skill" / "vibeworthy" / "assets" / "release-evidence.md"
)


class ReleaseWorkflowTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_release_triggers_and_permissions_are_minimal(self) -> None:
        self.assertRegex(
            self.workflow,
            r'(?m)^on:\n  push:\n    tags:\n      - "v\*"\n  workflow_dispatch:',
        )
        self.assertIn("permissions: {}", self.workflow)
        self.assertRegex(
            self.workflow,
            r"(?m)^    permissions:\n      contents: read\n      id-token: write\n"
            r"      attestations: write$",
        )
        self.assertNotIn("contents: write", self.workflow)
        self.assertNotIn("releases: write", self.workflow)
        self.assertNotIn("pull_request_target", self.workflow)

    def test_every_action_is_pinned_to_the_resolved_full_sha(self) -> None:
        expected = {
            "actions/checkout": (
                "3d3c42e5aac5ba805825da76410c181273ba90b1",
                "v7.0.1",
            ),
            "actions/attest-build-provenance": (
                "0f67c3f4856b2e3261c31976d6725780e5e4c373",
                "v4.1.1",
            ),
            "actions/upload-artifact": (
                "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
                "v7.0.1",
            ),
        }
        uses = re.findall(r"(?m)^\s+uses: ([^@\s]+)@([^\s]+)(?:\s+#\s*(.*))?$", self.workflow)
        self.assertEqual(set(expected), {action for action, _, _ in uses})
        self.assertEqual(len(expected), len(uses))
        for action, revision, comment in uses:
            expected_revision, version = expected[action]
            self.assertRegex(revision, r"^[0-9a-f]{40}$")
            self.assertEqual(expected_revision, revision)
            self.assertIn(version, comment)
            self.assertIn("official GitHub API 2026-07-30", comment)

    def test_archive_is_built_twice_from_the_evaluated_skill_tree(self) -> None:
        self.assertEqual(2, self.workflow.count("git archive --format=zip -9"))
        self.assertEqual(2, self.workflow.count("--prefix=vibeworthy/"))
        self.assertEqual(2, self.workflow.count('--mtime="@$archive_epoch"'))
        self.assertIn('cmp --silent "$first_archive" "$second_archive"', self.workflow)
        self.assertIn('${candidate_commit}:skill/vibeworthy', self.workflow)
        self.assertIn('${release_commit}:skill/vibeworthy', self.workflow)
        self.assertIn('if [[ "$candidate_tree" != "$release_tree" ]]', self.workflow)
        self.assertIn("VibeWorthy-Candidate-Commit:", self.workflow)
        self.assertIn("git merge-base --is-ancestor", self.workflow)
        self.assertIn("archive inventory differs from the evaluated skill tree", self.workflow)

    def test_version_validation_follows_semver_2_0_0(self) -> None:
        match = re.search(
            r"(?m)^          semver_pattern='([^'\n]+)'$",
            self.workflow,
        )
        self.assertIsNotNone(match)
        pattern = re.compile(match.group(1))

        accepted = (
            "0.0.0",
            "1.0.0",
            "1.0.0-0",
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-0.3.7",
            "1.0.0-x.7.z.92",
            "1.0.0-alpha-beta",
            "1.0.0+001",
            "1.0.0-alpha+001",
            "1.0.0-rc.1+build.001",
        )
        rejected = (
            "01.0.0",
            "1.01.0",
            "1.0.01",
            "1.0.0-01",
            "1.0.0-alpha.01",
            "1.0.0-",
            "1.0.0-alpha..1",
            "1.0.0+",
            "1.0.0+build..1",
            "v1.0.0",
        )
        for version in accepted:
            with self.subTest(version=version, expected="accepted"):
                self.assertIsNotNone(pattern.fullmatch(version))
        for version in rejected:
            with self.subTest(version=version, expected="rejected"):
                self.assertIsNone(pattern.fullmatch(version))

        self.assertIn(
            'if [[ ! "$tag_name" =~ ^v${semver_pattern}$ ]]',
            self.workflow,
        )
        self.assertIn(
            'if [[ ! "$version" =~ ^${semver_pattern}$ ]]',
            self.workflow,
        )

    def test_archive_command_is_reproducible_and_skill_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            repository = temporary_root / "repository"
            source = REPOSITORY_ROOT / "skill" / "vibeworthy"
            shutil.copytree(
                source,
                repository,
                ignore=shutil.ignore_patterns(
                    "__pycache__",
                    "*.py[cod]",
                    ".DS_Store",
                    ".idea",
                    ".vscode",
                ),
            )
            source_inventory = sorted(
                path.relative_to(repository).as_posix()
                for path in repository.rglob("*")
                if path.is_file()
            )

            def git(*arguments: str) -> str:
                return subprocess.run(
                    ["git", *arguments],
                    cwd=repository,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                ).stdout.strip()

            git("init", "--quiet")
            git("-c", "core.autocrlf=false", "add", "--force", "--", ".")
            tree = git("write-tree")
            expected = git("ls-tree", "-r", "--name-only", tree).splitlines()
            self.assertEqual(source_inventory, expected)

            first = temporary_root / "first.zip"
            second = temporary_root / "second.zip"
            for path in (first, second):
                git(
                    "archive",
                    "--format=zip",
                    "-9",
                    "--prefix=vibeworthy/",
                    "--mtime=@1704067200",
                    f"--output={path}",
                    tree,
                )
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).digest(),
                hashlib.sha256(second.read_bytes()).digest(),
            )
            with zipfile.ZipFile(first) as archive:
                names = archive.namelist()
            self.assertTrue(all(name.startswith("vibeworthy/") for name in names))
            archived_files = [name for name in names if not name.endswith("/")]
            self.assertEqual([f"vibeworthy/{name}" for name in expected], archived_files)

    def test_release_assets_have_sbom_manifest_checksums_and_attestation(self) -> None:
        self.assertIn("sbom.cdx.json", self.workflow)
        self.assertIn("SHA256SUMS", self.workflow)
        self.assertIn(".manifest.json", self.workflow)
        self.assertIn(".provenance.jsonl", self.workflow)
        self.assertIn("subject-path: ${{ steps.prepare.outputs.archive_path }}", self.workflow)
        self.assertIn('"kind": "GitHub build provenance attestation"', self.workflow)
        self.assertNotIn("signature", self.workflow.lower())
        exact_paths = (
            "${{ steps.prepare.outputs.archive_path }}",
            "${{ steps.prepare.outputs.sbom_path }}",
            "${{ steps.describe.outputs.manifest_path }}",
            "${{ steps.describe.outputs.provenance_path }}",
            "${{ steps.describe.outputs.checksums_path }}",
        )
        upload_block = self.workflow.split("- name: Upload the exact release assets", 1)[1]
        for path in exact_paths:
            self.assertEqual(1, upload_block.count(path))
        self.assertIn("if-no-files-found: error", upload_block)
        self.assertIn("compression-level: 0", upload_block)

    def test_workflow_does_not_publish_or_create_a_tag(self) -> None:
        forbidden = (
            "gh release",
            "git tag",
            "git push",
            "create-release",
            "softprops/action-gh-release",
            "ncipollo/release-action",
        )
        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, self.workflow.lower())

    def test_forward_protocol_records_exact_model_and_thread_id(self) -> None:
        documentation = FORWARD_README.read_text(encoding="utf-8")
        self.assertIn("--json", documentation)
        self.assertIn("--model gpt-5.6-sol", documentation)
        self.assertIn("model_reasoning_effort=\"low\"", documentation)
        self.assertIn("events.jsonl", documentation)
        self.assertIn('event.get("type") == "thread.started"', documentation)
        self.assertIn('event["thread_id"]', documentation)
        self.assertIn("thread-id.txt", documentation)

    def test_release_evidence_separates_all_release_identities(self) -> None:
        evidence = RELEASE_EVIDENCE.read_text(encoding="utf-8")
        normalized_evidence = " ".join(evidence.split())
        for phrase in (
            "Evaluated candidate commit (C)",
            "Evaluated `skill/vibeworthy` tree (T)",
            "Release/tag commit (R)",
            "Skill archive (A)",
            "Skill archive SHA-256 (D)",
            "Companion SBOM",
            "Build provenance attestation",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, evidence)
        self.assertIn("C is an ancestor of R", evidence)
        self.assertIn("C:skill/vibeworthy", evidence)
        self.assertIn("R:skill/vibeworthy", evidence)
        self.assertIn("VibeWorthy-Candidate-Commit: <C>", evidence)
        self.assertIn(
            "A GitHub build provenance attestation is provenance evidence",
            normalized_evidence,
        )


if __name__ == "__main__":
    unittest.main()
