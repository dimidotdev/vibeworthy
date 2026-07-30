from __future__ import annotations

import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
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
        self.assertRegex(
            self.workflow,
            r"(?m)^    environment: github-release\n    permissions:\n"
            r"      attestations: read\n      contents: write$",
        )
        build_block, promotion_block = self.workflow.split("\n  promote:\n", 1)
        self.assertNotIn("contents: write", build_block)
        self.assertEqual(1, promotion_block.count("contents: write"))
        self.assertNotIn("releases: write", self.workflow)
        self.assertNotIn("pull_request_target", self.workflow)

    def test_every_action_is_pinned_to_the_resolved_full_sha(self) -> None:
        expected = {
            "actions/checkout": (
                "3d3c42e5aac5ba805825da76410c181273ba90b1",
                "v7.0.1",
                1,
            ),
            "actions/attest-build-provenance": (
                "0f67c3f4856b2e3261c31976d6725780e5e4c373",
                "v4.1.1",
                2,
            ),
            "actions/upload-artifact": (
                "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
                "v7.0.1",
                1,
            ),
            "actions/download-artifact": (
                "3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c",
                "v8.0.1",
                1,
            ),
        }
        uses = re.findall(r"(?m)^\s+uses: ([^@\s]+)@([^\s]+)(?:\s+#\s*(.*))?$", self.workflow)
        self.assertEqual(set(expected), {action for action, _, _ in uses})
        self.assertEqual(sum(item[2] for item in expected.values()), len(uses))
        for action, revision, comment in uses:
            expected_revision, version, _ = expected[action]
            self.assertRegex(revision, r"^[0-9a-f]{40}$")
            self.assertEqual(expected_revision, revision)
            self.assertIn(version, comment)
            self.assertIn("official GitHub API 2026-07-30", comment)
        for action, (_, _, expected_count) in expected.items():
            self.assertEqual(expected_count, sum(found == action for found, _, _ in uses))

    def test_archive_is_built_twice_from_the_evaluated_skill_tree(self) -> None:
        self.assertEqual(2, self.workflow.count("git archive --format=zip -9"))
        self.assertEqual(2, self.workflow.count("--prefix=vibeworthy/"))
        self.assertEqual(2, self.workflow.count('--mtime="@$archive_epoch"'))
        self.assertIn('cmp --silent "$first_archive" "$second_archive"', self.workflow)
        self.assertIn('${candidate_commit}:skill/vibeworthy', self.workflow)
        self.assertIn('${release_commit}:skill/vibeworthy', self.workflow)
        self.assertIn('if [[ "$candidate_tree" != "$release_tree" ]]', self.workflow)
        self.assertIn("VibeWorthy-Candidate-Commit:", self.workflow)
        self.assertIn('if [[ "$candidate_commit" != "$release_commit" ]]', self.workflow)
        self.assertNotIn("git merge-base --is-ancestor", self.workflow)
        self.assertIn("archive inventory differs from the evaluated skill tree", self.workflow)

    def test_candidate_and_release_commit_must_be_identical(self) -> None:
        match = re.search(
            r'(?ms)^          if \[\[ "\$candidate_commit" != "\$release_commit" \]\]; then\n'
            r".*?^          fi$",
            self.workflow,
        )
        self.assertIsNotNone(match)
        bash = shutil.which("bash")
        self.assertIsNotNone(bash, "the release workflow requires bash")
        guard = textwrap.dedent(match.group(0))  # type: ignore[union-attr]

        def run_guard(candidate: str, release: str) -> subprocess.CompletedProcess[str]:
            script = (
                "set -euo pipefail\n"
                'candidate_commit="$1"\n'
                'release_commit="$2"\n'
                f"{guard}\n"
            )
            return subprocess.run(
                [bash, "-c", script, "identity-test", candidate, release],  # type: ignore[list-item]
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

        commit = "a" * 40
        self.assertEqual(0, run_guard(commit, commit).returncode)
        mismatch = run_guard(commit, "b" * 40)
        self.assertNotEqual(0, mismatch.returncode)
        self.assertIn("must exactly match", mismatch.stderr)

    def test_every_inline_python_uses_isolated_mode_and_cannot_shadow_stdlib(self) -> None:
        invocations = re.findall(r"(?m)^\s+(python3[^\n]*<<'PY')$", self.workflow)
        self.assertEqual(3, len(invocations))
        self.assertTrue(all(command == "python3 -I - <<'PY'" for command in invocations))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "shadow-import-executed"
            (root / "json.py").write_text(
                "from pathlib import Path\n"
                f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-I", "-"],
                cwd=root,
                input="import json\nprint(json.__file__)\n",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertFalse(marker.exists(), "isolated stdin Python imported a workspace json.py")
            self.assertNotIn(str(root), result.stdout)

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
        self.assertIn("subject-path: ${{ steps.describe.outputs.checksums_path }}", self.workflow)
        self.assertEqual(2, self.workflow.count("actions/attest-build-provenance@"))
        self.assertIn('"kind": "GitHub build provenance attestation"', self.workflow)
        self.assertNotIn("signature", self.workflow.lower())
        exact_paths = (
            "${{ steps.prepare.outputs.archive_path }}",
            "${{ steps.prepare.outputs.sbom_path }}",
            "${{ steps.describe.outputs.manifest_path }}",
            "${{ steps.describe.outputs.provenance_path }}",
            "${{ steps.describe.outputs.checksums_path }}",
            "${{ steps.stage_checksums_attestation.outputs.checksums_provenance_path }}",
        )
        upload_block = self.workflow.split("- name: Upload the exact release assets", 1)[1]
        for path in exact_paths:
            self.assertEqual(1, upload_block.count(path))
        self.assertIn("if-no-files-found: error", upload_block)
        self.assertIn("compression-level: 0", upload_block)
        self.assertIn(
            'checksums_provenance_name="vibeworthy-v${VERSION}.checksums.provenance.jsonl"',
            self.workflow,
        )
        self.assertRegex(
            self.workflow,
            r"(?s)checksum_paths = sorted\(\n\s+\(archive_path, bundle_path, manifest_path, sbom_path\),",
        )

    def test_only_tag_push_promotes_and_no_step_creates_or_moves_a_tag(self) -> None:
        forbidden = (
            "git tag",
            "git push",
            "create-release",
            "softprops/action-gh-release",
            "ncipollo/release-action",
        )
        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, self.workflow.lower())
        build_block, promotion_block = self.workflow.split("\n  promote:\n", 1)
        self.assertNotIn("gh release create", build_block)
        self.assertIn(
            "if: ${{ github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v') }}",
            promotion_block,
        )
        self.assertIn("environment: github-release", promotion_block)
        self.assertIn("artifact-ids: ${{ needs.release.outputs.artifact_id }}", promotion_block)
        self.assertEqual(2, promotion_block.count("gh attestation verify"))
        self.assertIn("--verify-tag", promotion_block)
        self.assertIn('gh release create "${release_args[@]}"', promotion_block)
        publish_block = promotion_block.split("- name: Publish the durable GitHub Release", 1)[1]
        for name in (
            "vibeworthy-v${VERSION}.zip",
            "vibeworthy-v${VERSION}.sbom.cdx.json",
            "vibeworthy-v${VERSION}.manifest.json",
            "vibeworthy-v${VERSION}.provenance.jsonl",
            "SHA256SUMS",
            "vibeworthy-v${VERSION}.checksums.provenance.jsonl",
        ):
            self.assertEqual(1, publish_block.count(f"$ASSET_DIR/{name}"))
        self.assertIn("Source code archives are repository snapshots", publish_block)

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
            "Release manifest",
            "Archive build provenance",
            "Checksum index",
            "Checksum-index provenance",
            "Published asset inventory",
            "Durable GitHub Release",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, evidence)
        self.assertIn("require R to equal C exactly", normalized_evidence)
        self.assertIn("R:skill/vibeworthy", evidence)
        self.assertIn("VibeWorthy-Candidate-Commit: <C>", evidence)
        self.assertIn("candidate that differs from the tag target", normalized_evidence)
        self.assertIn(
            "A GitHub build provenance attestation is provenance evidence",
            normalized_evidence,
        )
        self.assertIn(
            "| Evidence class | Gate/fact | Result | Evidence | Residual risk | Owner | Next action |",
            evidence,
        )
        self.assertIn("workflow_dispatch` run is only a build/attestation rehearsal", evidence)
        self.assertIn("exactly the ZIP, SBOM, release", normalized_evidence)
        self.assertIn("exact six workflow-managed files", normalized_evidence)
        self.assertIn("checking only a bundle digest is insufficient", normalized_evidence)
        self.assertIn("automatic source archives are host-created snapshots outside", normalized_evidence)
        self.assertIn("unknown` is an unresolved ownership blocker", evidence)


if __name__ == "__main__":
    unittest.main()
