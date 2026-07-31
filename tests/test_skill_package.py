"""Small contract tests for the distributed VibeWorthy Agent Skill."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from urllib.parse import unquote, urlparse


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPOSITORY_ROOT / "skill" / "vibeworthy"
SKILL_FILE = SKILL_ROOT / "SKILL.md"

EXPECTED_PACKAGE_FILES = {
    Path("LICENSE"),
    Path("SKILL.md"),
    Path("agents/openai.yaml"),
    Path("assets/security-checkpoint.md"),
    Path("assets/v0-instructions.md"),
    Path("references/backends-supply-release.md"),
    Path("references/platform-compatibility.md"),
    Path("references/security-privacy.md"),
    Path("scripts/preflight.py"),
}

MARKDOWN_LINK = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalized(path: Path) -> str:
    return " ".join(read_text(path).lower().split())


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    lines = read_text(path).splitlines()
    if not lines or lines[0] != "---":
        raise AssertionError("SKILL.md must start with YAML frontmatter")
    try:
        closing = lines.index("---", 1)
    except ValueError as error:
        raise AssertionError("SKILL.md frontmatter is not closed") from error

    fields: dict[str, str] = {}
    for line in lines[1:closing]:
        if not line.strip():
            continue
        if line[:1].isspace() or ":" not in line:
            raise AssertionError(f"unsupported frontmatter line: {line!r}")
        key, value = line.split(":", 1)
        if key in fields:
            raise AssertionError(f"duplicate frontmatter key: {key}")
        fields[key] = value.strip()
    return fields, "\n".join(lines[closing + 1 :]).strip()


def local_target(source: Path, raw_target: str) -> Path | None:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc or target.startswith(("#", "mailto:")):
        return None
    path = unquote(parsed.path)
    return (source.parent / path).resolve() if path else None


class SkillPackageTests(unittest.TestCase):
    maxDiff = None

    def test_package_shape_is_small_and_explicit(self) -> None:
        actual = {
            path.relative_to(SKILL_ROOT)
            for path in SKILL_ROOT.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }
        self.assertEqual(actual, EXPECTED_PACKAGE_FILES)

    def test_frontmatter_and_core_budget(self) -> None:
        frontmatter, body = parse_frontmatter(SKILL_FILE)
        self.assertEqual(set(frontmatter), {"name", "description"})
        self.assertEqual(frontmatter["name"], "vibeworthy")
        description = frontmatter["description"].lower()
        self.assertIn("security-first", description)
        self.assertIn("use when", description)
        self.assertTrue(body)
        self.assertLessEqual(len(read_text(SKILL_FILE).splitlines()), 200)

    def test_every_packaged_resource_is_linked_directly(self) -> None:
        direct = {
            target
            for match in MARKDOWN_LINK.finditer(read_text(SKILL_FILE))
            if (target := local_target(SKILL_FILE, match.group(1))) is not None
        }
        expected = {
            path.resolve()
            for directory in (SKILL_ROOT / "references", SKILL_ROOT / "assets")
            for path in directory.glob("*.md")
        }
        self.assertTrue(expected.issubset(direct))

    def test_all_local_markdown_links_stay_in_package_and_resolve(self) -> None:
        root = SKILL_ROOT.resolve()
        for source in SKILL_ROOT.rglob("*.md"):
            for match in MARKDOWN_LINK.finditer(read_text(source)):
                target = local_target(source, match.group(1))
                if target is None:
                    continue
                self.assertTrue(target.is_relative_to(root), f"{source}: link escapes package")
                self.assertTrue(target.exists(), f"{source}: broken link {match.group(1)}")

    def test_openai_metadata_matches_the_skill(self) -> None:
        metadata = read_text(SKILL_ROOT / "agents" / "openai.yaml")
        self.assertIn('display_name: "VibeWorthy"', metadata)
        short = re.search(r'(?m)^  short_description: "([^"]+)"$', metadata)
        self.assertIsNotNone(short)
        self.assertGreaterEqual(len(short.group(1)), 25)
        self.assertLessEqual(len(short.group(1)), 64)
        self.assertIn("$vibeworthy", metadata)

    def test_core_enforces_security_without_validation_theater(self) -> None:
        skill = normalized(SKILL_FILE)
        plain = skill.replace(chr(96), "")
        for phrase in (
            "quick",
            "guarded",
            "critical",
            "keep .env and environment variants out of git",
            "user a attempting to access user b's object",
            "deny by default",
            "do not run recursive review loops",
            "at most once per stable revision",
            "run preflight again only when scanner-relevant files changed",
            "do not load its implementation into model context",
            "plain language",
        ):
            self.assertIn(phrase, plain)
        for obsolete in ("mandatory release ledger", "seven-column"):
            self.assertNotIn(obsolete, skill)

    def test_lifecycle_reference_covers_first_prompt_through_operations(self) -> None:
        lifecycle = normalized(SKILL_ROOT / "references" / "security-privacy.md")
        for phrase in (
            "first prompt and project setup",
            "authentication and sessions",
            "authorization",
            "input, output, and files",
            "apis and abuse",
            "testing",
            "deployment and maintenance",
            "ai agents, mcp, and connected tools",
            "incident response for exposed secrets",
        ):
            self.assertIn(phrase, lifecycle)

    def test_backend_reference_covers_common_vibe_coding_risks(self) -> None:
        backend = normalized(SKILL_ROOT / "references" / "backends-supply-release.md")
        for phrase in (
            "firebase",
            "supabase",
            "service-account",
            "service_role",
            "user a on user b",
            "payments and webhooks",
            "dependencies and automation",
            "migrations and destructive changes",
            "efficient release checkpoint",
        ):
            self.assertIn(phrase, backend)

    def test_compact_adapter_preserves_critical_controls(self) -> None:
        adapter_path = SKILL_ROOT / "assets" / "v0-instructions.md"
        adapter = normalized(adapter_path).replace(chr(96), "")
        self.assertLessEqual(len(read_text(adapter_path).splitlines()), 80)
        for phrase in (
            "keep .env* out of git",
            "user a against user b's data",
            "never expose admin/service-account material",
            "never expose service_role",
            "do not repeat equivalent scans",
            "meaningful unknowns",
        ):
            self.assertIn(phrase, adapter)

    def test_readme_is_honest_about_scope_and_env_incidents(self) -> None:
        readme = normalized(REPOSITORY_ROOT / "README.md").replace(chr(96), "")
        for phrase in (
            "without turning every change into a heavyweight audit",
            "tracked or unignored sensitive .env file",
            "revoke or rotate the exposed values first",
            "does not inspect git history",
            "cannot prove cloud configuration",
        ):
            self.assertIn(phrase, readme)

    def test_sbom_declares_no_runtime_dependencies(self) -> None:
        sbom = json.loads(read_text(REPOSITORY_ROOT / "sbom.cdx.json"))
        self.assertEqual(sbom["bomFormat"], "CycloneDX")
        self.assertEqual(sbom["metadata"]["component"]["name"], "vibeworthy")
        self.assertEqual(sbom["components"], [])
        self.assertEqual(len(sbom["dependencies"]), 1)
        self.assertEqual(sbom["dependencies"][0]["dependsOn"], [])

    def test_ci_uses_cross_platform_python_and_pinned_actions(self) -> None:
        workflow = read_text(REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml")
        for runner in ("ubuntu-latest", "windows-latest", "macos-latest"):
            self.assertIn(runner, workflow)
        self.assertIn('"3.11"', workflow)
        for reference in re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", workflow):
            self.assertRegex(reference, r"@[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
