"""Dependency-free contract tests for the distributed VibeWorthy skill."""

from __future__ import annotations

import ast
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
            {"SKILL.md", "agents", "assets", "references", "scripts"},
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
        self.assertIn("$vibeworthy", scalar("default_prompt"))

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

    def test_public_claims_are_qualified(self) -> None:
        readme = read_text(REPOSITORY_ROOT / "README.md").lower()
        readme_flat = " ".join(readme.split())
        self.assertIn(
            "does not guarantee security, compliance, profitability, or production readiness",
            readme_flat,
        )

        paths = [REPOSITORY_ROOT / "README.md", V0_ADAPTER, SKILL_FILE]
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

        action_revisions = re.findall(r"(?m)^\s*uses:\s*[^@\s]+@([^\s#]+)", workflow)
        self.assertGreaterEqual(len(action_revisions), 2)
        self.assertTrue(
            all(re.fullmatch(r"[0-9a-f]{40}", revision) for revision in action_revisions),
            f"all GitHub Actions must use immutable full SHAs: {action_revisions}",
        )


if __name__ == "__main__":
    unittest.main()
