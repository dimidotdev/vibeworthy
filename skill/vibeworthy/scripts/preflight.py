#!/usr/bin/env python3
"""Local, read-only preflight checks for a VibeWorthy worktree.

The scanner deliberately reports rule, location, and remediation without retaining
or rendering matched values.  It does not execute project code, contact a network,
scan Git history, inspect submodule contents, or claim that a clean run is a release
approval.
"""

from __future__ import annotations

import argparse
import base64
import dataclasses
import datetime as dt
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from typing import Iterable, Sequence
from urllib.parse import quote


TOOL_NAME = "vibeworthy-preflight"
TOOL_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"
DEFAULT_MAX_FILE_BYTES = 1_048_576
DEFAULT_MAX_FILES = 20_000
MAX_SUPPRESSION_METADATA_CHARS = 4_096

BLOCKER = "blocker"
WARNING = "warning"
REQUIRED_MANUAL_CHECK = "required-manual-check"


@dataclasses.dataclass(frozen=True)
class Rule:
    rule_id: str
    severity: str
    title: str
    message: str
    remediation: str
    category: str


def _rule(
    rule_id: str,
    severity: str,
    title: str,
    message: str,
    remediation: str,
    category: str,
) -> Rule:
    return Rule(rule_id, severity, title, message, remediation, category)


RULES: dict[str, Rule] = {
    rule.rule_id: rule
    for rule in (
        _rule(
            "VW-SECRET-PRIVATE-KEY",
            BLOCKER,
            "Private key material",
            "Private key material is present in the current worktree.",
            "Revoke or rotate it first, audit use, remediate Git history, and move the replacement to a managed secret store with least privilege, an owner, inventory, and expiry.",
            "suspected-secret",
        ),
        _rule(
            "VW-SECRET-CLOUD-ACCESS-KEY",
            BLOCKER,
            "Cloud access credential",
            "A high-confidence cloud access credential pattern is present in the current worktree.",
            "Revoke or rotate it first, audit use, remediate Git history, and provision a least-privileged short-lived identity through a managed secret store.",
            "suspected-secret",
        ),
        _rule(
            "VW-SECRET-PROVIDER-TOKEN",
            BLOCKER,
            "Provider credential",
            "A high-confidence provider credential pattern is present in the current worktree.",
            "Revoke or rotate it first, audit use, remediate Git history, and provision the replacement outside source and client bundles.",
            "suspected-secret",
        ),
        _rule(
            "VW-SECRET-GENERIC-ASSIGNMENT",
            BLOCKER,
            "Credential-like assignment",
            "A non-placeholder credential-like value is assigned in source or configuration.",
            "Treat it as exposed until disproven: revoke or rotate, audit use and history, then use a managed secret store with least privilege, owner, inventory, and expiry.",
            "suspected-secret",
        ),
        _rule(
            "VW-SECRET-CREDENTIAL-URL",
            BLOCKER,
            "Credential in URL",
            "A URL appears to contain embedded credentials.",
            "Revoke or rotate the credential, remove it from source and history, and supply authentication through a managed secret mechanism.",
            "suspected-secret",
        ),
        _rule(
            "VW-ENV-TRACKED",
            BLOCKER,
            "Tracked sensitive environment file",
            "A sensitive environment file is tracked by Git.",
            "Remove the file from tracking without printing it, rotate any exposed values, audit and remediate history, and retain only a placeholder template.",
            "environment",
        ),
        _rule(
            "VW-ENV-UNIGNORED",
            BLOCKER,
            "Unignored sensitive environment file",
            "A sensitive environment file is untracked but not ignored.",
            "Add a narrowly scoped ignore rule, keep a placeholder template, and rotate any value that may already have been shared or staged.",
            "environment",
        ),
        _rule(
            "VW-CLIENT-PRIVILEGED-CREDENTIAL",
            BLOCKER,
            "Privileged credential in public client configuration",
            "A public-client variable appears to contain a privileged credential.",
            "Remove it from the client, rotate it, and enforce the privileged operation at a reviewed server or IAM boundary with independent denial tests.",
            "client-secret",
        ),
        _rule(
            "VW-FIREBASE-PUBLIC-API-KEY",
            WARNING,
            "Firebase-style client API key",
            "A Firebase-style client API key is present; its external API and application restrictions are unverified.",
            "Do not treat the identifier as authorization. Manually verify cloud restrictions, deny-by-default Rules, App Check where appropriate, and anonymous/user-A/user-B/admin denial evidence.",
            REQUIRED_MANUAL_CHECK,
        ),
        _rule(
            "VW-FIREBASE-SERVICE-ACCOUNT",
            BLOCKER,
            "Firebase service-account credential",
            "A Firebase service-account credential pattern is present in the current worktree.",
            "Revoke or rotate the credential, audit use and history, and replace it with a least-privileged server-side workload identity where supported.",
            "privileged-backend-credential",
        ),
        _rule(
            "VW-SUPABASE-PUBLIC-KEY",
            WARNING,
            "Supabase public client key",
            "A Supabase publishable or legacy anonymous key is present; RLS and external project controls are unverified.",
            "Manually verify RLS, USING and WITH CHECK behavior, and anonymous/user-A/user-B/admin denial across applicable tables, storage, realtime, views, and functions.",
            REQUIRED_MANUAL_CHECK,
        ),
        _rule(
            "VW-SUPABASE-PRIVILEGED-KEY",
            BLOCKER,
            "Supabase privileged key",
            "A Supabase secret or service-role credential pattern is present in the current worktree.",
            "Revoke or rotate it, remove it from public clients and history, and test authorization at the privileged server or IAM boundary.",
            "privileged-backend-credential",
        ),
        _rule(
            "VW-SUPABASE-RLS-DISABLED",
            BLOCKER,
            "Supabase row-level security disabled",
            "A SQL migration explicitly disables PostgreSQL row-level security on a table.",
            "Keep RLS enabled and deny by default; review bypass roles and prove anonymous/user-A/user-B/admin USING and WITH CHECK behavior in isolated staging.",
            "authorization",
        ),
        _rule(
            "VW-FIREBASE-PERMISSIVE-RULE",
            BLOCKER,
            "Unconditional Firebase access rule",
            "A Firebase Security Rule appears to allow an operation unconditionally.",
            "Replace it with deny-by-default authorization and prove anonymous/user-A/user-B/admin behavior in an isolated emulator or staging project.",
            "authorization",
        ),
        _rule(
            "VW-LOCKFILE-CONFLICT",
            BLOCKER,
            "Conflicting lockfiles",
            "More than one JavaScript package-manager lockfile applies in the same project directory.",
            "Defer installation, confirm package-manager identity and necessity, then preserve one reviewed immutable lockfile.",
            "dependency-integrity",
        ),
        _rule(
            "VW-LOCKFILE-MISSING",
            WARNING,
            "Dependency manifest without lockfile",
            "A JavaScript dependency manifest has dependencies but no applicable lockfile in scope.",
            "Confirm package identity and necessity, then generate and review one immutable lockfile without running untrusted install hooks.",
            "dependency-integrity",
        ),
        _rule(
            "VW-INSTALL-SCRIPT",
            WARNING,
            "Package install lifecycle script",
            "A package install lifecycle script can execute code during dependency installation.",
            "Defer installation until the package, source, permissions, necessity, and script behavior have been independently reviewed.",
            "dependency-execution",
        ),
        _rule(
            "VW-REMOTE-INSTALL-SCRIPT",
            BLOCKER,
            "Remote script execution",
            "A command appears to pipe remotely retrieved content into a command interpreter.",
            "Do not execute it. Verify identity, source, digest or signature, permissions, and necessity through a reviewable download-and-inspect workflow.",
            "dependency-execution",
        ),
        _rule(
            "VW-SHELL-PIPELINE-UNPARSED",
            BLOCKER,
            "Relevant shell pipeline not safely tokenized",
            "A shell-like line containing a fetch command and pipeline punctuation exceeded the tokenizer budget or was malformed, so it was not classified.",
            "Inspect the bounded line without executing it, split or repair the command for review, and rerun the scanner; an unparsed relevant pipeline cannot produce a clean result.",
            "dependency-execution",
        ),
        _rule(
            "VW-AUTOMATION-UNPINNED",
            BLOCKER,
            "Unpinned third-party automation",
            "A third-party workflow action or container is not pinned to an immutable commit or digest.",
            "Pin actions to a reviewed full commit SHA and containers to a verified digest; record provenance and update ownership.",
            "supply-chain",
        ),
        _rule(
            "VW-MANIFEST-INVALID",
            BLOCKER,
            "Invalid dependency manifest",
            "A dependency manifest could not be parsed as a JSON object.",
            "Repair and review the manifest before dependency installation or release checks.",
            "dependency-integrity",
        ),
        _rule(
            "VW-SUPPRESSION-INVALID",
            BLOCKER,
            "Invalid warning suppression",
            "A warning suppression is missing valid, distinct-approver, or future-dated metadata.",
            "Keep the warning active or provide nonempty reason, owner, distinct approved-by, compensating-control, and a future ISO expiry date on the same line; verify approver independence outside the scanner.",
            "scanner-policy",
        ),
        _rule(
            "VW-SUPPRESSION-BLOCKER",
            BLOCKER,
            "Blocker suppression attempt",
            "An inline marker attempts to suppress a blocker, which is not permitted.",
            "Resolve the blocker and retain evidence; blocker and tool-error results cannot be suppressed or waived by this scanner.",
            "scanner-policy",
        ),
    )
}


@dataclasses.dataclass
class Finding:
    rule_id: str
    path: str
    line: int
    suppressed: bool = False
    suppression: dict[str, object] | None = None
    source_id: bytes = dataclasses.field(default=b"", repr=False)

    @property
    def rule(self) -> Rule:
        return RULES[self.rule_id]

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "rule_id": self.rule_id,
            "severity": self.rule.severity,
            "path": self.path,
            "line": self.line,
            "message": self.rule.message,
            "remediation": self.rule.remediation,
            "evidence_category": self.rule.category,
            "suppressed": self.suppressed,
        }
        if self.suppression is not None:
            result["suppression"] = self.suppression
        return result


@dataclasses.dataclass(frozen=True)
class ToolIssue:
    code: str
    message: str
    path: str = "."

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "path": self.path}


@dataclasses.dataclass(frozen=True)
class Candidate:
    path: Path
    display_path: str
    tracked: bool | None
    source_id: bytes = b""


@dataclasses.dataclass
class Scope:
    mode: str = "not-started"
    target: str = "."
    includes: list[str] = dataclasses.field(default_factory=list)
    excludes: list[str] = dataclasses.field(default_factory=list)
    git_history_scanned: bool = False
    submodules_scanned: bool = False
    network_used: bool = False
    files_modified: bool = False

    def as_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class Report:
    scope: Scope = dataclasses.field(default_factory=Scope)
    findings: list[Finding] = dataclasses.field(default_factory=list)
    tool_errors: list[ToolIssue] = dataclasses.field(default_factory=list)
    files_considered: int = 0
    files_scanned: int = 0
    skipped: Counter[str] = dataclasses.field(default_factory=Counter)

    @property
    def exit_code(self) -> int:
        if self.tool_errors:
            return 2
        if any(f.rule.severity == BLOCKER for f in self.findings):
            return 1
        return 0

    def summary(self) -> dict[str, object]:
        blockers = sum(f.rule.severity == BLOCKER for f in self.findings)
        warnings = sum(f.rule.severity == WARNING for f in self.findings)
        suppressed = sum(f.suppressed for f in self.findings)
        manual = sum(f.rule.category == REQUIRED_MANUAL_CHECK for f in self.findings)
        return {
            "files_considered": self.files_considered,
            "files_scanned": self.files_scanned,
            "files_skipped": sum(self.skipped.values()),
            "skipped_by_reason": dict(sorted(self.skipped.items())),
            "findings_total": len(self.findings),
            "blockers": blockers,
            "warnings": warnings,
            "active_warnings": warnings - suppressed,
            "suppressed_warnings": suppressed,
            "required_manual_checks": manual,
            "tool_errors": len(self.tool_errors),
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
            "scope": self.scope.as_dict(),
            "findings": [finding.as_dict() for finding in self.findings],
            "tool_errors": [issue.as_dict() for issue in self.tool_errors],
            "summary": self.summary(),
            "exit_code": self.exit_code,
            "release_assertion": "none",
        }


class UsageFailure(Exception):
    """An argument error that must not echo untrusted argument content."""


class GitUnavailable(Exception):
    """Git is optional; filesystem scope remains available when it is absent."""


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # noqa: ARG002 - intentionally redacted
        raise UsageFailure


_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".cache",
        ".next",
        ".nuxt",
        ".output",
        ".parcel-cache",
        ".pytest_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "bower_components",
        "build",
        "coverage",
        "dist",
        "generated",
        "node_modules",
        "out",
        "target",
        "vendor",
        "venv",
    }
)

_BINARY_SUFFIXES = frozenset(
    {
        ".7z",
        ".a",
        ".avi",
        ".bin",
        ".bmp",
        ".class",
        ".dll",
        ".dylib",
        ".eot",
        ".exe",
        ".gif",
        ".gz",
        ".ico",
        ".jar",
        ".jpeg",
        ".jpg",
        ".lockb",
        ".mov",
        ".mp3",
        ".mp4",
        ".o",
        ".otf",
        ".pdf",
        ".png",
        ".pyc",
        ".so",
        ".tar",
        ".tgz",
        ".ttf",
        ".wav",
        ".webm",
        ".webp",
        ".woff",
        ".woff2",
        ".xz",
        ".zip",
    }
)

_LOCKFILES = frozenset(
    {"package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb"}
)

_PRIVATE_KEY_RE = re.compile(r"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----")
_CLOUD_KEY_RE = re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])")
_PROVIDER_TOKEN_RES = (
    re.compile(r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{36,255}(?![A-Za-z0-9])"),
    re.compile(r"(?<![A-Za-z0-9])sk_live_[A-Za-z0-9]{20,255}(?![A-Za-z0-9])"),
    re.compile(r"(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9-]{20,255}(?![A-Za-z0-9])"),
)
_FIREBASE_KEY_RE = re.compile(r"(?<![A-Za-z0-9_-])AIza[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])")
_SUPABASE_PUBLIC_RE = re.compile(r"(?<![A-Za-z0-9_-])sb_publishable_[A-Za-z0-9_-]{20,255}(?![A-Za-z0-9_-])")
_SUPABASE_SECRET_RE = re.compile(r"(?<![A-Za-z0-9_-])sb_secret_[A-Za-z0-9_-]{20,255}(?![A-Za-z0-9_-])")
_JWT_RE = re.compile(r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{5,2048}\.[A-Za-z0-9_-]{5,4096}\.[A-Za-z0-9_-]{5,2048}(?![A-Za-z0-9_-])")
_CREDENTIAL_URL_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]{1,20}://[^\s/:@]{1,128}:[^\s/@]{8,512}@")
_PUBLIC_CLIENT_CREDENTIAL_RE = re.compile(
    r"(?i)(?P<name>\b(?:VITE|NEXT_PUBLIC|PUBLIC|REACT_APP)_[A-Z0-9_]{0,128}(?:SERVICE_ROLE|SECRET|PRIVATE_KEY|ADMIN_KEY|DATABASE_PASSWORD))"
    r"\s*[:=]\s*(?P<quote>[\"']?)(?P<value>[^\s\"'`,;#]{12,4096})(?P=quote)"
)
_SERVICE_ROLE_ASSIGNMENT_RE = re.compile(
    r"(?i)(?P<name>\b[A-Z0-9_]{0,128}SUPABASE[A-Z0-9_]{0,128}SERVICE_ROLE[A-Z0-9_]{0,128})"
    r"\s*[:=]\s*(?P<quote>[\"']?)(?P<value>[^\s\"'`,;#]{12,4096})(?P=quote)"
)
_ASSIGNMENT_NAME_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.\"'-"
)
_ASSIGNMENT_VALUE_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_./+=:@%$!~-"
)
_GENERIC_SECRET_NAME_HINTS = (
    "api_key",
    "api-key",
    "apikey",
    "secret",
    "token",
    "password",
    "passwd",
    "private_key",
    "private-key",
    "access_key",
    "access-key",
)
_PUBLIC_CLIENT_PREFIXES = ("vite_", "next_public_", "public_", "react_app_")
_PUBLIC_CLIENT_SUFFIXES = (
    "service_role",
    "secret",
    "private_key",
    "admin_key",
    "database_password",
)
_SUPABASE_RLS_DISABLED_RE = re.compile(
    r"\bALTER\s+TABLE(?:\s+IF\s+EXISTS)?\s+(?:ONLY\s+)?"
    r"(?:\"[^\"\r\n]+\"|[A-Za-z_][A-Za-z0-9_$]*)"
    r"(?:\s*\.\s*(?:\"[^\"\r\n]+\"|[A-Za-z_][A-Za-z0-9_$]*))?"
    r"\s+DISABLE\s+ROW\s+LEVEL\s+SECURITY\b",
    re.IGNORECASE,
)
_FIREBASE_TRUE_EXPRESSION = (
    r"(?:true(?: *== *true)?|false *== *false|1 *== *1|"
    r"(?:! *! *){1,16}true|! *(?:! *! *){0,15}false)"
)
_FIREBASE_OPEN_PARENS = r"(?:\( *)*"
_FIREBASE_CLOSE_PARENS = r"(?: *\))*"
_FIREBASE_RTD_RULE_RE = re.compile(
    r"[\"']?\.(?:read|write)[\"']? *: *(?:"
    + _FIREBASE_OPEN_PARENS
    + _FIREBASE_TRUE_EXPRESSION
    + _FIREBASE_CLOSE_PARENS
    + r"|(?P<quote>[\"']) *"
    + _FIREBASE_OPEN_PARENS
    + _FIREBASE_TRUE_EXPRESSION
    + _FIREBASE_CLOSE_PARENS
    + r" *(?P=quote))",
    re.IGNORECASE,
)
_FIREBASE_ALLOW_RE = re.compile(
    r"\ballow +(?:read|write|create|update|delete|get|list)"
    r"(?: *, *(?:read|write|create|update|delete|get|list))*"
    r" *: *if *"
    + _FIREBASE_OPEN_PARENS
    + _FIREBASE_TRUE_EXPRESSION
    + _FIREBASE_CLOSE_PARENS
    + r" *;",
    re.IGNORECASE,
)
_ACTION_USES_RE = re.compile(
    r"(?:^\s*-?\s*|[{,]\s*)[\"']?uses[\"']?\s*:\s*[\"']?(?P<reference>[^\s,}#\"']+)",
    re.IGNORECASE,
)
_SUPPRESSION_HINT_RE = re.compile(r"vibeworthy\s*:\s*(?:ignore|suppress)\b", re.IGNORECASE)
_SUPPRESSION_RE = re.compile(
    r"vibeworthy\s*:\s*(?:ignore|suppress)\s+(?:\[)?(?P<rule>[A-Za-z0-9._-]+)(?:\])?(?P<meta>.*)$",
    re.IGNORECASE,
)


def _contains_path(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _normalized_assignment_name(value: str) -> str:
    return value.strip().strip("\"'").lower()


def _is_secret_assignment_name(value: str) -> bool:
    """Classify an assignment name in bounded linear time."""

    normalized = _normalized_assignment_name(value)
    if any(hint in normalized for hint in _GENERIC_SECRET_NAME_HINTS):
        return True
    if normalized.startswith(_PUBLIC_CLIENT_PREFIXES) and normalized.endswith(
        _PUBLIC_CLIENT_SUFFIXES
    ):
        return True
    supabase_index = normalized.find("supabase")
    return supabase_index >= 0 and normalized.find("service_role", supabase_index + 8) >= 0


def _generic_assignments(line: str) -> Iterable[tuple[str, str]]:
    """Yield credential-like assignments without backtracking over untrusted text."""

    name_start: int | None = None
    name_end: int | None = None
    whitespace_after_name = False
    index = 0
    while index < len(line):
        character = line[index]
        if character in _ASSIGNMENT_NAME_CHARS:
            if name_start is None or whitespace_after_name:
                name_start = index
            name_end = index + 1
            whitespace_after_name = False
            index += 1
            continue
        if character.isspace():
            if name_start is not None:
                whitespace_after_name = True
            index += 1
            continue
        if character not in {":", "="}:
            name_start = None
            name_end = None
            whitespace_after_name = False
            index += 1
            continue

        name = line[name_start:name_end] if name_start is not None and name_end is not None else ""
        value_index = index + 1
        while value_index < len(line) and line[value_index].isspace():
            value_index += 1
        quote_character = ""
        if value_index < len(line) and line[value_index] in {'"', "'"}:
            quote_character = line[value_index]
            value_index += 1
        value_start = value_index
        while value_index < len(line) and line[value_index] in _ASSIGNMENT_VALUE_CHARS:
            value_index += 1
        value = line[value_start:value_index]
        quote_closed = not quote_character or (
            value_index < len(line) and line[value_index] == quote_character
        )
        if (
            _is_secret_assignment_name(name)
            and 12 <= len(value) <= 4_096
            and quote_closed
        ):
            yield name, value

        index = value_index + (1 if quote_character and quote_closed else 0)
        name_start = None
        name_end = None
        whitespace_after_name = False


def _secret_assignment_separator(value: str) -> int | None:
    """Locate the first secret-like path assignment without regex backtracking."""

    name_start: int | None = None
    name_end: int | None = None
    whitespace_after_name = False
    for index, character in enumerate(value):
        if character in _ASSIGNMENT_NAME_CHARS:
            if name_start is None or whitespace_after_name:
                name_start = index
            name_end = index + 1
            whitespace_after_name = False
        elif character.isspace():
            if name_start is not None:
                whitespace_after_name = True
        elif character in {":", "="}:
            name = (
                value[name_start:name_end]
                if name_start is not None and name_end is not None
                else ""
            )
            if _is_secret_assignment_name(name):
                return index
            name_start = None
            name_end = None
            whitespace_after_name = False
        else:
            name_start = None
            name_end = None
            whitespace_after_name = False
    return None


def _safe_display_component(value: str) -> str:
    output: list[str] = []
    for character in value:
        code = ord(character)
        category = unicodedata.category(character)
        if character == "\\":
            output.append("\\u005c")
        elif code < 32 or code == 127 or category in {"Cc", "Cf", "Cs", "Zl", "Zp"}:
            output.append(f"\\u{code:04x}" if code <= 0xFFFF else f"\\U{code:08x}")
        else:
            output.append(character)
    safe = "".join(output)
    for pattern in (
        _PRIVATE_KEY_RE,
        _CLOUD_KEY_RE,
        _FIREBASE_KEY_RE,
        _SUPABASE_PUBLIC_RE,
        _SUPABASE_SECRET_RE,
        _JWT_RE,
        *_PROVIDER_TOKEN_RES,
    ):
        safe = pattern.sub("[REDACTED]", safe)
    safe = _CREDENTIAL_URL_RE.sub("[REDACTED-CREDENTIAL-URL]", safe)
    assignment_separator = _secret_assignment_separator(safe)
    if assignment_separator is not None:
        safe = safe[: assignment_separator + 1] + "[REDACTED]"
    return safe or "."


def _relative_display(path: Path, root: Path, root_is_file: bool) -> str:
    if root_is_file:
        raw = path.name
    else:
        try:
            raw = path.relative_to(root).as_posix()
        except ValueError:
            raw = "."
    return _safe_display_component(raw)


def _disambiguate_display_paths(candidates: Sequence[Candidate]) -> list[Candidate]:
    """Give sanitization collisions distinct, opaque report locations."""

    groups: dict[str, list[Candidate]] = defaultdict(list)
    for candidate in candidates:
        groups[candidate.display_path].append(candidate)
    used = set(groups)
    result: list[Candidate] = []
    for display_path, group in sorted(groups.items()):
        if len(group) == 1:
            result.append(group[0])
            continue
        parent, separator, name = display_path.rpartition("/")
        prefix = f"{parent}{separator}" if separator else ""
        for index, candidate in enumerate(sorted(group, key=lambda item: item.source_id), start=1):
            marker = f"__vibeworthy_redacted_path_{index}_of_{len(group)}__"
            disambiguated = f"{prefix}{marker}/{name}"
            while disambiguated in used:
                marker += "_"
                disambiguated = f"{prefix}{marker}/{name}"
            used.add(disambiguated)
            result.append(dataclasses.replace(candidate, display_path=disambiguated))
    return sorted(result, key=lambda candidate: candidate.display_path)


def _is_env_template(name: str) -> bool:
    lower = name.lower()
    template_parts = (".example", ".sample", ".template", ".dist", ".defaults")
    return lower.startswith(".env") and any(part in lower for part in template_parts)


def _is_sensitive_env(name: str) -> bool:
    lower = name.lower()
    return (lower == ".env" or lower.startswith(".env.")) and not _is_env_template(lower)


def _skip_path_reason(display_path: str) -> str | None:
    path = Path(display_path)
    lowered_parts = {part.lower() for part in path.parts[:-1]}
    if lowered_parts & _SKIP_DIR_NAMES:
        return "generated-or-vendor"
    lower_name = path.name.lower()
    if lower_name.endswith((".min.js", ".min.css", ".map")) or ".generated." in lower_name:
        return "generated-or-vendor"
    if path.suffix.lower() in _BINARY_SUFFIXES:
        return "binary"
    return None


def _run_git(cwd: Path, arguments: Sequence[str]) -> tuple[int, bytes]:
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        completed = subprocess.run(
            [
                "git",
                "-c",
                "core.quotepath=false",
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.untrackedCache=false",
                *arguments,
            ],
            cwd=os.fspath(cwd),
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=30,
        )
    except FileNotFoundError as exc:
        raise GitUnavailable from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("git-failed") from exc
    return completed.returncode, completed.stdout


def _git_candidates(target: Path, target_is_file: bool, report: Report) -> list[Candidate] | None:
    probe = target.parent if target_is_file else target
    try:
        return_code, root_output = _run_git(probe, ["rev-parse", "--show-toplevel"])
    except GitUnavailable:
        return None
    except RuntimeError:
        report.tool_errors.append(ToolIssue("tool.git-unavailable", "Git could not be invoked safely."))
        return []
    if return_code != 0:
        return None

    try:
        git_root = Path(os.fsdecode(root_output.rstrip(b"\r\n"))).resolve(strict=True)
    except (OSError, ValueError):
        report.tool_errors.append(ToolIssue("tool.git-root", "The Git worktree root could not be resolved safely."))
        return []
    target_resolved = target.resolve(strict=True)
    if not _contains_path(git_root, target_resolved):
        report.tool_errors.append(ToolIssue("tool.scope", "The requested target is outside the resolved Git worktree."))
        return []

    relative_target = target_resolved.relative_to(git_root)
    raw_pathspec = "" if not relative_target.parts else relative_target.as_posix()
    pathspec = f":(top,literal){raw_pathspec}"
    commands = (
        (True, ["ls-files", "-z", "--cached", "--", pathspec]),
        (False, ["ls-files", "-z", "--others", "--exclude-standard", "--", pathspec]),
    )
    by_raw_path: dict[str, Candidate] = {}
    for tracked, command in commands:
        try:
            return_code, output = _run_git(git_root, command)
        except RuntimeError:
            report.tool_errors.append(ToolIssue("tool.git-enumeration", "Git worktree enumeration failed."))
            return []
        if return_code != 0:
            report.tool_errors.append(ToolIssue("tool.git-enumeration", "Git worktree enumeration failed."))
            return []
        for encoded_path in output.split(b"\0"):
            if not encoded_path:
                continue
            raw_relative = os.fsdecode(encoded_path)
            candidate_path = git_root / raw_relative
            display = _relative_display(candidate_path, target_resolved, target_is_file)
            by_raw_path[raw_relative] = Candidate(candidate_path, display, tracked, os.fsencode(raw_relative))

    report.scope = Scope(
        mode="git-worktree",
        includes=["tracked", "untracked-non-ignored"],
        excludes=["git-history", "submodules", "ignored", "symlinks", "binary", "generated-or-vendor", "oversized"],
    )
    return _disambiguate_display_paths(list(by_raw_path.values()))


def _filesystem_candidates(target: Path, target_is_file: bool, report: Report) -> list[Candidate]:
    report.scope = Scope(
        mode="filesystem",
        includes=["regular-files"],
        excludes=["git-history", "submodules", "symlinks", "binary", "generated-or-vendor", "oversized"],
    )
    if target_is_file:
        return [Candidate(target, _safe_display_component(target.name), None, os.fsencode(target.name))]

    candidates: list[Candidate] = []
    errors: list[OSError] = []

    def remember_error(error: OSError) -> None:
        errors.append(error)

    for current, directory_names, file_names in os.walk(target, topdown=True, followlinks=False, onerror=remember_error):
        current_path = Path(current)
        retained_directories: list[str] = []
        for directory_name in sorted(directory_names):
            directory_path = current_path / directory_name
            display = _relative_display(directory_path, target, False)
            if directory_name.lower() in _SKIP_DIR_NAMES:
                report.skipped["generated-or-vendor"] += 1
            elif directory_path.is_symlink():
                report.skipped["symlink"] += 1
            else:
                retained_directories.append(directory_name)
        directory_names[:] = retained_directories
        for file_name in sorted(file_names):
            path = current_path / file_name
            raw_relative = os.fspath(path.relative_to(target))
            candidates.append(Candidate(path, _relative_display(path, target, False), None, os.fsencode(raw_relative)))
    if errors:
        report.tool_errors.append(ToolIssue("tool.walk", "One or more directories could not be enumerated safely."))
    return _disambiguate_display_paths(candidates)


def _enumerate_candidates(target: Path, report: Report) -> tuple[list[Candidate], Path, bool]:
    try:
        target_stat = os.lstat(target)
    except (OSError, ValueError):
        report.tool_errors.append(ToolIssue("tool.target", "The requested target could not be accessed safely."))
        return [], target, False
    if stat.S_ISLNK(target_stat.st_mode):
        report.tool_errors.append(ToolIssue("tool.target-symlink", "A symlink cannot be used as the scan root."))
        return [], target, False
    target_is_file = stat.S_ISREG(target_stat.st_mode)
    if not target_is_file and not stat.S_ISDIR(target_stat.st_mode):
        report.tool_errors.append(ToolIssue("tool.target-type", "The scan root must be a regular file or directory."))
        return [], target, False
    try:
        resolved = target.resolve(strict=True)
    except OSError:
        report.tool_errors.append(ToolIssue("tool.target", "The requested target could not be resolved safely."))
        return [], target, target_is_file

    candidates = _git_candidates(resolved, target_is_file, report)
    if candidates is None:
        candidates = _filesystem_candidates(resolved, target_is_file, report)
    return candidates, resolved, target_is_file


def _has_symlink_component(path: Path, allowed_root: Path) -> bool:
    """Reject a candidate whose path below the root traverses a symlink."""

    try:
        relative = path.relative_to(allowed_root)
    except ValueError:
        return True
    current = allowed_root
    for component in relative.parts[:-1]:
        current = current / component
        try:
            if stat.S_ISLNK(os.lstat(current).st_mode):
                return True
        except OSError:
            return True
    return False


def _read_candidate(candidate: Candidate, scan_root: Path, root_is_file: bool, max_bytes: int, report: Report) -> str | None:
    skip_reason = _skip_path_reason(candidate.display_path)
    if skip_reason:
        report.skipped[skip_reason] += 1
        return None
    try:
        file_stat = os.lstat(candidate.path)
    except FileNotFoundError:
        report.skipped["missing-from-worktree"] += 1
        return None
    except OSError:
        report.tool_errors.append(ToolIssue("tool.file-metadata", "A candidate file could not be inspected safely.", candidate.display_path))
        return None
    if stat.S_ISLNK(file_stat.st_mode):
        report.skipped["symlink"] += 1
        return None
    if stat.S_ISDIR(file_stat.st_mode):
        report.skipped["submodule-or-directory"] += 1
        return None
    if not stat.S_ISREG(file_stat.st_mode):
        report.skipped["special-file"] += 1
        return None
    if file_stat.st_size > max_bytes:
        report.skipped["oversized"] += 1
        return None
    allowed_root = scan_root.parent if root_is_file else scan_root
    if _has_symlink_component(candidate.path, allowed_root):
        report.skipped["symlink"] += 1
        return None
    try:
        resolved = candidate.path.resolve(strict=True)
    except OSError:
        report.tool_errors.append(ToolIssue("tool.file-resolution", "A candidate file could not be resolved safely.", candidate.display_path))
        return None
    if not _contains_path(allowed_root, resolved) or (root_is_file and resolved != scan_root):
        report.skipped["outside-scope"] += 1
        return None

    flags = os.O_RDONLY
    flags |= getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate.path, flags)
        try:
            opened_stat = os.fstat(descriptor)
            if not stat.S_ISREG(opened_stat.st_mode):
                report.skipped["special-file"] += 1
                return None
            if not os.path.samestat(file_stat, opened_stat):
                report.tool_errors.append(
                    ToolIssue(
                        "tool.file-race",
                        "A candidate changed identity while it was being opened; no content was scanned.",
                        candidate.display_path,
                    )
                )
                return None
            chunks: list[bytes] = []
            remaining = max_bytes + 1
            while remaining:
                chunk = os.read(descriptor, min(65_536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            content = b"".join(chunks)
        finally:
            os.close(descriptor)
    except OSError:
        report.tool_errors.append(ToolIssue("tool.file-read", "A candidate file could not be read safely.", candidate.display_path))
        return None
    if len(content) > max_bytes:
        report.skipped["oversized"] += 1
        return None
    if b"\0" in content:
        report.skipped["binary"] += 1
        return None
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        report.skipped["binary"] += 1
        return None
    report.files_scanned += 1
    return text


def _placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    if not lowered:
        return True
    if lowered.startswith(("${", "{{", "<", "process.env")):
        return True
    tokens = [token for token in re.split(r"[^a-z0-9]+", lowered) if token]
    if not tokens:
        return True
    placeholder_tokens = {
        "changeme",
        "dummy",
        "example",
        "fake",
        "placeholder",
        "replace",
        "sample",
        "test",
        "your",
    }
    placeholder_suffixes = {
        "api",
        "credential",
        "here",
        "key",
        "me",
        "password",
        "secret",
        "token",
        "value",
    }
    return tokens[0] in placeholder_tokens and all(
        token in placeholder_suffixes for token in tokens[1:]
    )


def _jwt_role(value: str) -> str | None:
    try:
        payload = value.split(".", 2)[1]
        padding = "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode((payload + padding).encode("ascii"))
        if len(decoded) > 16_384:
            return None
        data = json.loads(decoded.decode("utf-8"))
        role = data.get("role") if isinstance(data, dict) else None
        return role if isinstance(role, str) else None
    except (ValueError, UnicodeError, json.JSONDecodeError):
        return None


def _is_known_specialized_value(value: str) -> bool:
    if (
        _FIREBASE_KEY_RE.fullmatch(value)
        or _SUPABASE_PUBLIC_RE.fullmatch(value)
        or _SUPABASE_SECRET_RE.fullmatch(value)
        or _CLOUD_KEY_RE.fullmatch(value)
        or any(pattern.fullmatch(value) for pattern in _PROVIDER_TOKEN_RES)
    ):
        return True
    if _JWT_RE.fullmatch(value) and _jwt_role(value) in {"anon", "service_role"}:
        return True
    return False


def _line_for_json_key(lines: Sequence[str], key: str) -> int:
    pattern = re.compile(rf"^\s*[\"']{re.escape(key)}[\"']\s*:")
    for index, line in enumerate(lines, start=1):
        if pattern.search(line):
            return index
    return 1


def _is_firebase_rules_path(display_path: str) -> bool:
    lower = display_path.lower()
    name = Path(lower).name
    return name in {"firestore.rules", "storage.rules", "database.rules.json", "firebase.rules"} or lower.endswith(".rules")


def _is_workflow_path(display_path: str) -> bool:
    lower = display_path.lower()
    return lower.startswith(".github/workflows/") and lower.endswith((".yml", ".yaml"))


def _action_is_pinned(reference: str) -> bool:
    if reference.startswith("./"):
        return True
    if reference.startswith("docker://"):
        return "@sha256:" in reference.lower() and bool(re.search(r"@sha256:[0-9a-f]{64}$", reference, re.IGNORECASE))
    if "@" not in reference:
        return False
    revision = reference.rsplit("@", 1)[1]
    return bool(re.fullmatch(r"[0-9a-fA-F]{40}", revision))


def _logical_shell_commands(text: str) -> Iterable[tuple[int, str]]:
    """Yield shell-like logical lines without merging independent physical lines."""

    parts: list[str] = []
    start_line = 1
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not parts:
            start_line = line_number
        trimmed = line.rstrip()
        trailing_backslashes = len(trimmed) - len(trimmed.rstrip("\\"))
        backslash_continuation = trailing_backslashes % 2 == 1
        if backslash_continuation:
            trimmed = trimmed[:-1].rstrip()
        parts.append(trimmed)
        pipeline_continuation = trimmed.endswith(("|", "|&", "||"))
        if backslash_continuation or pipeline_continuation:
            continue
        yield start_line, " ".join(parts)
        parts = []
    if parts:
        yield start_line, " ".join(parts)


def _command_invocation(tokens: Sequence[str]) -> tuple[str | None, int | None]:
    index = 0
    assignment = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*", re.DOTALL)
    while index < len(tokens) and assignment.fullmatch(tokens[index]):
        index += 1
    wrappers = {"command", "env", "exec", "sudo"}
    options_with_value = {
        "env": {"-u", "--unset", "-C", "--chdir"},
        "sudo": {
            "-C",
            "--chdir",
            "-g",
            "--group",
            "-h",
            "--host",
            "-p",
            "--prompt",
            "-R",
            "--chroot",
            "-r",
            "--role",
            "-T",
            "--command-timeout",
            "-t",
            "--type",
            "-u",
            "--user",
            "-U",
            "--other-user",
        },
    }
    while index < len(tokens):
        name = _normalized_executable_name(tokens[index])
        if name not in wrappers:
            return name, index
        index += 1
        while index < len(tokens):
            token = tokens[index]
            if assignment.fullmatch(token) is not None:
                index += 1
                continue
            if token == "--":
                index += 1
                break
            if not token.startswith("-"):
                break
            option = token.split("=", 1)[0]
            index += 1
            if option in options_with_value.get(name, set()) and "=" not in token and index < len(tokens):
                index += 1
    return None, None


def _shell_command_name(tokens: Sequence[str]) -> str | None:
    return _command_invocation(tokens)[0]


def _normalized_executable_name(value: str) -> str:
    name = value.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return name[:-4] if name.endswith(".exe") else name


def _pipeline_has_remote_shell(commands: Sequence[Sequence[str]]) -> bool:
    names = [_shell_command_name(command) for command in commands]
    fetchers = {"curl", "wget"}
    shells = {"bash", "csh", "dash", "ksh", "sh", "zsh"}
    return any(
        name in fetchers and any(later in shells for later in names[index + 1 :])
        for index, name in enumerate(names)
    )


def _tokens_have_remote_pipeline(tokens: Sequence[str]) -> bool:
    pipeline: list[list[str]] = []
    command: list[str] = []

    def finish_pipeline() -> bool:
        nonlocal pipeline, command
        if command:
            pipeline.append(command)
        found = len(pipeline) > 1 and _pipeline_has_remote_shell(pipeline)
        pipeline = []
        command = []
        return found

    for token in tokens:
        if token in {"|", "|&"}:
            pipeline.append(command)
            command = []
        elif token and all(character in "|;&" for character in token):
            if finish_pipeline():
                return True
        else:
            command.append(token)
    return finish_pipeline()


def _shell_command_payloads(tokens: Sequence[str]) -> list[str]:
    shells = {"bash", "csh", "dash", "ksh", "sh", "zsh"}
    payloads: list[str] = []
    simple_commands: list[list[str]] = []
    simple_command: list[str] = []
    for token in tokens:
        if token and all(character in "|;&" for character in token):
            if simple_command:
                simple_commands.append(simple_command)
            simple_command = []
        else:
            simple_command.append(token)
    if simple_command:
        simple_commands.append(simple_command)

    shell_options_with_value = {"-O", "-o", "--init-file", "--rcfile"}
    for command in simple_commands:
        executable, executable_index = _command_invocation(command)
        if executable_index is None:
            continue

        if executable == "cmd":
            for index in range(executable_index + 1, len(command) - 1):
                if command[index].lower() in {"/c", "/k"}:
                    payloads.append(" ".join(command[index + 1 :]))
                    break
            continue

        if executable not in shells:
            continue
        index = executable_index + 1
        while index < len(command):
            option = command[index]
            if option == "--":
                break
            if not option.startswith("-") or option == "-":
                break
            is_command_option = option == "-c" or (
                option.startswith("-")
                and not option.startswith("--")
                and "c" in option[1:]
            )
            if is_command_option:
                payload_index = index + 1
                if payload_index < len(command) and command[payload_index] == "--":
                    payload_index += 1
                if payload_index < len(command):
                    payloads.append(command[payload_index])
                break
            option_name = option.split("=", 1)[0]
            if option_name in shell_options_with_value and "=" not in option:
                index += 2
                continue
            index += 1
    return payloads


def _command_substitution_payloads(command: str) -> tuple[list[str], bool]:
    """Extract executable command/process substitutions without evaluating them."""

    payloads: list[str] = []
    quote_character: str | None = None
    escaped = False
    index = 0
    while index < len(command):
        character = command[index]
        if escaped:
            escaped = False
            index += 1
            continue
        if character == "\\" and quote_character != "'":
            escaped = True
            index += 1
            continue
        if character == "'":
            quote_character = None if quote_character == "'" else ("'" if quote_character is None else quote_character)
            index += 1
            continue
        if character == '"':
            quote_character = None if quote_character == '"' else ('"' if quote_character is None else quote_character)
            index += 1
            continue
        is_command_substitution = character == "$" and quote_character != "'"
        is_process_substitution = character in {"<", ">"} and quote_character is None
        if (
            (is_command_substitution or is_process_substitution)
            and index + 1 < len(command)
            and command[index + 1] == "("
        ):
            start = index + 2
            cursor = start
            depth = 1
            inner_quote: str | None = None
            inner_escaped = False
            while cursor < len(command):
                current = command[cursor]
                if inner_escaped:
                    inner_escaped = False
                elif current == "\\" and inner_quote != "'":
                    inner_escaped = True
                elif current == "'":
                    inner_quote = None if inner_quote == "'" else ("'" if inner_quote is None else inner_quote)
                elif current == '"':
                    inner_quote = None if inner_quote == '"' else ('"' if inner_quote is None else inner_quote)
                elif inner_quote is None and current == "(":
                    depth += 1
                elif inner_quote is None and current == ")":
                    depth -= 1
                    if depth == 0:
                        payloads.append(command[start:cursor])
                        index = cursor + 1
                        break
                cursor += 1
            else:
                return payloads, False
            continue
        if quote_character != "'" and character == "`":
            cursor = index + 1
            inner_escaped = False
            while cursor < len(command):
                current = command[cursor]
                if inner_escaped:
                    inner_escaped = False
                elif current == "\\":
                    inner_escaped = True
                elif current == "`":
                    payloads.append(command[index + 1 : cursor])
                    index = cursor + 1
                    break
                cursor += 1
            else:
                return payloads, False
            continue
        index += 1
    return payloads, True


def _tokenize_shell_line(command: str) -> tuple[list[str], bool]:
    """Tokenize only the shell syntax needed for pipeline classification in linear time."""

    tokens: list[str] = []
    current: list[str] = []
    quote_character: str | None = None
    escaped = False
    index = 0

    def finish_token() -> None:
        if current:
            tokens.append("".join(current))
            current.clear()

    while index < len(command):
        character = command[index]
        if escaped:
            current.append(character)
            escaped = False
            index += 1
            continue
        if quote_character is not None:
            if character == quote_character:
                quote_character = None
            elif character == "\\" and quote_character == '"':
                if (
                    index + 1 < len(command)
                    and command[index + 1] in '$`"\\\n'
                ):
                    escaped = True
                else:
                    current.append(character)
            else:
                current.append(character)
            index += 1
            continue
        if character in {'"', "'"}:
            quote_character = character
            index += 1
            continue
        if character == "\\":
            if index + 1 < len(command) and command[index + 1] in " \t\r\n\"'`$|;&<>\\":
                escaped = True
            else:
                current.append(character)
            index += 1
            continue
        if character.isspace():
            finish_token()
            index += 1
            continue
        if character == "#" and not current:
            break
        if character in "<>" or (
            character == "&" and index + 1 < len(command) and command[index + 1] == ">"
        ):
            finish_token()
            end = index + 1
            if character == "&":
                end += 1
            else:
                while end < len(command) and command[end] == character:
                    end += 1
                if end < len(command) and command[end] == "&":
                    end += 1
            while end < len(command) and (command[end].isdigit() or command[end] == "-"):
                end += 1
            tokens.append(command[index:end])
            index = end
            continue
        if character in "|;&":
            finish_token()
            end = index + 1
            while end < len(command) and command[end] in "|;&":
                end += 1
            tokens.append(command[index:end])
            index = end
            continue
        current.append(character)
        index += 1
    finish_token()
    return tokens, quote_character is None and not escaped


def _remote_pipeline_status(command: str, depth: int = 0) -> tuple[bool, bool]:
    """Return (detected, unparsed) for a bounded shell-like command string."""

    if "|" not in command or re.search(
        r"\b(?:curl|wget)(?:\.exe)?\b", command, re.IGNORECASE
    ) is None:
        return False, False
    if depth > 4:
        return False, True
    tokens, complete = _tokenize_shell_line(command)
    if not complete:
        return False, True
    if _tokens_have_remote_pipeline(tokens):
        return True, False

    nested_payloads = _shell_command_payloads(tokens)
    substitution_payloads, substitutions_complete = _command_substitution_payloads(command)
    if not substitutions_complete:
        return False, True
    for payload in (*nested_payloads, *substitution_payloads):
        detected, unparsed = _remote_pipeline_status(payload, depth + 1)
        if detected or unparsed:
            return detected, unparsed
    return False, False


def _remote_pipe_line_numbers(text: str) -> tuple[list[int], list[int]]:
    findings: list[int] = []
    unparsed: list[int] = []
    for start_line, logical_command in _logical_shell_commands(text):
        detected, could_not_parse = _remote_pipeline_status(logical_command)
        if detected:
            findings.append(start_line)
        elif could_not_parse:
            unparsed.append(start_line)
    return sorted(set(findings)), sorted(set(unparsed))


def _normalized_firebase_rules(text: str) -> tuple[str, list[int]]:
    """Remove comments and collapse whitespace linearly while retaining locations."""

    output: list[str] = []
    line_numbers: list[int] = []
    line_number = 1
    quote_character: str | None = None
    escaped = False
    index = 0

    def append_space(source_line: int) -> None:
        if output and output[-1] != " ":
            output.append(" ")
            line_numbers.append(source_line)

    while index < len(text):
        character = text[index]
        if quote_character is not None:
            if not escaped and character.isspace():
                append_space(line_number)
                while index < len(text) and text[index].isspace():
                    if text[index] == "\n":
                        line_number += 1
                    index += 1
                continue
            output.append(character)
            line_numbers.append(line_number)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote_character:
                quote_character = None
            if character == "\n":
                line_number += 1
            index += 1
            continue
        if character in {'"', "'"}:
            quote_character = character
            output.append(character)
            line_numbers.append(line_number)
            index += 1
            continue
        if text.startswith("//", index):
            append_space(line_number)
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue
        if text.startswith("/*", index):
            append_space(line_number)
            index += 2
            while index < len(text) and not text.startswith("*/", index):
                if text[index] == "\n":
                    line_number += 1
                index += 1
            index = min(len(text), index + 2)
            continue
        if character.isspace():
            append_space(line_number)
            while index < len(text) and text[index].isspace():
                if text[index] == "\n":
                    line_number += 1
                index += 1
            continue
        output.append(character)
        line_numbers.append(line_number)
        index += 1
    return "".join(output), line_numbers


def _scan_text(candidate: Candidate, text: str, findings: list[Finding]) -> dict[str, object] | None:
    lines = text.splitlines()
    seen: set[tuple[str, int]] = set()

    def add(rule_id: str, line_number: int) -> None:
        key = (rule_id, line_number)
        if key not in seen:
            findings.append(
                Finding(
                    rule_id,
                    candidate.display_path,
                    max(1, line_number),
                    source_id=candidate.source_id,
                )
            )
            seen.add(key)

    if _is_sensitive_env(candidate.path.name):
        if candidate.tracked is True:
            add("VW-ENV-TRACKED", 1)
        elif candidate.tracked is False:
            add("VW-ENV-UNIGNORED", 1)

    firebase_rule_file = _is_firebase_rules_path(candidate.display_path)
    workflow_file = _is_workflow_path(candidate.display_path)
    service_account_type_line: int | None = None
    service_account_private_line: int | None = None

    for line_number, line in enumerate(lines, start=1):
        if _PRIVATE_KEY_RE.search(line):
            add("VW-SECRET-PRIVATE-KEY", line_number)
        if _CLOUD_KEY_RE.search(line):
            add("VW-SECRET-CLOUD-ACCESS-KEY", line_number)
        if any(pattern.search(line) for pattern in _PROVIDER_TOKEN_RES):
            add("VW-SECRET-PROVIDER-TOKEN", line_number)
        if _CREDENTIAL_URL_RE.search(line):
            add("VW-SECRET-CREDENTIAL-URL", line_number)
        if _FIREBASE_KEY_RE.search(line):
            add("VW-FIREBASE-PUBLIC-API-KEY", line_number)
        if _SUPABASE_PUBLIC_RE.search(line):
            add("VW-SUPABASE-PUBLIC-KEY", line_number)
        if _SUPABASE_SECRET_RE.search(line):
            add("VW-SUPABASE-PRIVILEGED-KEY", line_number)
        for jwt_match in _JWT_RE.finditer(line):
            role = _jwt_role(jwt_match.group(0))
            if role == "service_role":
                add("VW-SUPABASE-PRIVILEGED-KEY", line_number)
            elif role == "anon":
                add("VW-SUPABASE-PUBLIC-KEY", line_number)

        public_client_match = _PUBLIC_CLIENT_CREDENTIAL_RE.search(line)
        if public_client_match and not _placeholder(public_client_match.group("value")):
            add("VW-CLIENT-PRIVILEGED-CREDENTIAL", line_number)
        service_role_match = _SERVICE_ROLE_ASSIGNMENT_RE.search(line)
        if service_role_match and not _placeholder(service_role_match.group("value")):
            add("VW-SUPABASE-PRIVILEGED-KEY", line_number)

        for _name, value in _generic_assignments(line):
            if not _placeholder(value) and not _is_known_specialized_value(value):
                add("VW-SECRET-GENERIC-ASSIGNMENT", line_number)

        if workflow_file:
            for action_match in _ACTION_USES_RE.finditer(line):
                if not _action_is_pinned(action_match.group("reference")):
                    add("VW-AUTOMATION-UNPINNED", line_number)

        if re.search(r"[\"']type[\"']\s*:\s*[\"']service_account[\"']", line):
            service_account_type_line = line_number
        if re.search(r"[\"']private_key[\"']\s*:", line) and not re.search(
            r"(?i)(?:placeholder|example|replace|dummy|fake|\$\{|\{\{)", line
        ):
            service_account_private_line = line_number

    if service_account_type_line is not None and service_account_private_line is not None:
        add("VW-FIREBASE-SERVICE-ACCOUNT", service_account_private_line)

    remote_lines, unparsed_shell_lines = _remote_pipe_line_numbers(text)
    for line_number in remote_lines:
        add("VW-REMOTE-INSTALL-SCRIPT", line_number)
    for line_number in unparsed_shell_lines:
        add("VW-SHELL-PIPELINE-UNPARSED", line_number)

    if firebase_rule_file:
        normalized_rules, normalized_line_numbers = _normalized_firebase_rules(text)
        for pattern in (_FIREBASE_RTD_RULE_RE, _FIREBASE_ALLOW_RE):
            for match in pattern.finditer(normalized_rules):
                line_number = (
                    normalized_line_numbers[match.start()]
                    if match.start() < len(normalized_line_numbers)
                    else 1
                )
                add("VW-FIREBASE-PERMISSIVE-RULE", line_number)

    if candidate.path.suffix.lower() == ".sql":
        for match in _SUPABASE_RLS_DISABLED_RE.finditer(text):
            add("VW-SUPABASE-RLS-DISABLED", text.count("\n", 0, match.start()) + 1)

    if candidate.path.name != "package.json":
        return None
    try:
        manifest = json.loads(text)
    except json.JSONDecodeError:
        add("VW-MANIFEST-INVALID", 1)
        return {
            "valid": False,
            "path": candidate.display_path,
            "source_id": candidate.source_id,
            "directory": candidate.path.parent,
        }
    if not isinstance(manifest, dict):
        add("VW-MANIFEST-INVALID", 1)
        return {
            "valid": False,
            "path": candidate.display_path,
            "source_id": candidate.source_id,
            "directory": candidate.path.parent,
        }
    scripts = manifest.get("scripts")
    if isinstance(scripts, dict):
        for name in ("preinstall", "install", "postinstall", "prepare"):
            script = scripts.get(name)
            if isinstance(script, str):
                script_line = _line_for_json_key(lines, name)
                add("VW-INSTALL-SCRIPT", script_line)
                remote_lines, unparsed_shell_lines = _remote_pipe_line_numbers(script)
                if remote_lines:
                    add("VW-REMOTE-INSTALL-SCRIPT", script_line)
                if unparsed_shell_lines:
                    add("VW-SHELL-PIPELINE-UNPARSED", script_line)
    dependency_sections = ("dependencies", "devDependencies", "optionalDependencies")
    has_dependencies = any(isinstance(manifest.get(section), dict) and bool(manifest[section]) for section in dependency_sections)
    return {
        "valid": True,
        "path": candidate.display_path,
        "source_id": candidate.source_id,
        "directory": candidate.path.parent,
        "has_dependencies": has_dependencies,
    }


def _nearest_lockfiles(directory: Path, scan_root: Path, lockfiles_by_directory: dict[Path, list[Candidate]]) -> list[Candidate]:
    current = directory
    while True:
        if current in lockfiles_by_directory:
            return lockfiles_by_directory[current]
        if current == scan_root or current.parent == current or not _contains_path(scan_root, current.parent):
            return []
        current = current.parent


def _add_dependency_findings(
    candidates: Sequence[Candidate],
    manifests: Sequence[dict[str, object]],
    scan_root: Path,
    root_is_file: bool,
    findings: list[Finding],
) -> None:
    if root_is_file:
        return
    lockfiles_by_directory: dict[Path, list[Candidate]] = {}
    for candidate in candidates:
        if candidate.path.name in _LOCKFILES and not (
            {part.lower() for part in Path(candidate.display_path).parts[:-1]} & _SKIP_DIR_NAMES
        ):
            lockfiles_by_directory.setdefault(candidate.path.parent, []).append(candidate)
    for lockfiles in lockfiles_by_directory.values():
        distinct_names = {candidate.path.name for candidate in lockfiles}
        if len(distinct_names) > 1:
            first = sorted(lockfiles, key=lambda item: item.display_path)[0]
            findings.append(
                Finding(
                    "VW-LOCKFILE-CONFLICT",
                    first.display_path,
                    1,
                    source_id=first.source_id,
                )
            )
    for manifest in manifests:
        if not manifest.get("valid") or not manifest.get("has_dependencies"):
            continue
        directory = manifest.get("directory")
        if isinstance(directory, Path) and not _nearest_lockfiles(directory, scan_root, lockfiles_by_directory):
            source_id = manifest.get("source_id")
            findings.append(
                Finding(
                    "VW-LOCKFILE-MISSING",
                    str(manifest["path"]),
                    1,
                    source_id=source_id if isinstance(source_id, bytes) else b"",
                )
            )


def _parse_suppression(line: str) -> tuple[str, dict[str, str]] | None:
    match = _SUPPRESSION_RE.search(line)
    if not match:
        return None
    rule_id = match.group("rule").upper()
    metadata_text = match.group("meta").strip()
    metadata_text = re.sub(r"(?:\*/|-->)\s*$", "", metadata_text).strip()
    if len(metadata_text) > MAX_SUPPRESSION_METADATA_CHARS:
        return rule_id, {}
    try:
        tokens = shlex.split(metadata_text, posix=True)
    except ValueError:
        return rule_id, {}
    metadata: dict[str, str] = {}
    for token in tokens:
        if "=" not in token:
            return rule_id, {}
        key, value = token.split("=", 1)
        key = key.strip().lower().replace("_", "-")
        if not key or key in metadata:
            return rule_id, {}
        metadata[key] = value.strip()
    return rule_id, metadata


def _valid_suppression_metadata(metadata: dict[str, str], today: dt.date) -> tuple[bool, str | None]:
    required = {"reason", "owner", "approved-by", "compensating-control", "expires"}
    if not required.issubset(metadata) or any(not metadata[key].strip() for key in required):
        return False, None
    if any(len(metadata[key]) > 512 or any(ord(character) < 32 for character in metadata[key]) for key in required):
        return False, None
    def normalized_identity(value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value)
        return "".join(
            character
            for character in normalized.casefold().strip()
            if unicodedata.category(character) != "Cf" and not character.isspace()
        )

    if normalized_identity(metadata["owner"]) == normalized_identity(metadata["approved-by"]):
        return False, None
    try:
        expiry = dt.date.fromisoformat(metadata["expires"].strip())
    except ValueError:
        return False, None
    if expiry <= today:
        return False, None
    return True, expiry.isoformat()


def _apply_suppressions(findings: list[Finding], sources: dict[bytes, str], today: dt.date | None = None) -> None:
    today = today or dt.date.today()
    additions: list[Finding] = []
    findings_by_location: dict[tuple[bytes, int], list[Finding]] = defaultdict(list)
    for finding in findings:
        findings_by_location[(finding.source_id, finding.line)].append(finding)
    for source_id, source in sorted(sources.items()):
        for line_number, line in enumerate(source.splitlines(), start=1):
            if not _SUPPRESSION_HINT_RE.search(line):
                continue
            same_line = findings_by_location.get((source_id, line_number), [])
            if not same_line:
                continue
            path = same_line[0].path
            parsed = _parse_suppression(line)
            if parsed is None:
                additions.append(
                    Finding("VW-SUPPRESSION-INVALID", path, line_number, source_id=source_id)
                )
                continue
            target_rule, metadata = parsed
            targets = [finding for finding in same_line if finding.rule_id == target_rule]
            if not targets:
                additions.append(
                    Finding("VW-SUPPRESSION-INVALID", path, line_number, source_id=source_id)
                )
                continue
            if any(target.rule.severity == BLOCKER for target in targets):
                additions.append(
                    Finding("VW-SUPPRESSION-BLOCKER", path, line_number, source_id=source_id)
                )
                continue
            valid, expiry = _valid_suppression_metadata(metadata, today)
            if not valid:
                additions.append(
                    Finding("VW-SUPPRESSION-INVALID", path, line_number, source_id=source_id)
                )
                continue
            for target in targets:
                target.suppressed = True
                target.suppression = {
                    "status": "metadata-valid",
                    "metadata_complete": True,
                    "approver_identifier_distinct": True,
                    "approver_independence_verified": False,
                    "expires": expiry,
                    "values_redacted": True,
                }
    findings.extend(additions)


def scan_path(path: str | os.PathLike[str], max_file_bytes: int = DEFAULT_MAX_FILE_BYTES, max_files: int = DEFAULT_MAX_FILES) -> Report:
    report = Report()
    try:
        target = Path(path)
    except (TypeError, ValueError):
        report.tool_errors.append(ToolIssue("tool.target", "The requested target is invalid."))
        return report
    candidates, scan_root, root_is_file = _enumerate_candidates(target, report)
    if report.tool_errors:
        return report
    report.files_considered = len(candidates)
    if len(candidates) > max_files:
        report.tool_errors.append(ToolIssue("tool.file-limit", "The candidate-file limit was exceeded; no partial clean result was produced."))
        return report

    sources: dict[bytes, str] = {}
    manifests: list[dict[str, object]] = []
    for candidate in candidates:
        text = _read_candidate(candidate, scan_root, root_is_file, max_file_bytes, report)
        if text is None:
            continue
        sources[candidate.source_id] = text
        manifest = _scan_text(candidate, text, report.findings)
        if manifest is not None:
            manifests.append(manifest)

    _add_dependency_findings(candidates, manifests, scan_root, root_is_file, report.findings)
    _apply_suppressions(report.findings, sources)
    unique: dict[tuple[str, bytes, int], Finding] = {}
    for finding in report.findings:
        key = (finding.rule_id, finding.source_id, finding.line)
        existing = unique.get(key)
        if existing is None or (finding.suppressed and not existing.suppressed):
            unique[key] = finding
    report.findings = sorted(unique.values(), key=lambda finding: (finding.path, finding.line, finding.rule_id))
    report.tool_errors.sort(key=lambda issue: (issue.path, issue.code))
    return report


def render_text(report: Report) -> str:
    summary = report.summary()
    lines = [
        "VibeWorthy preflight",
        f"Scope: {report.scope.mode}; includes: {', '.join(report.scope.includes) or 'none'}.",
        "Coverage: current target only; Git history and submodule contents were not scanned.",
        "Safety: network not used; project files not modified; matched values are never reported.",
    ]
    if report.findings:
        lines.append("Findings:")
        for finding in report.findings:
            state = "[SUPPRESSED]" if finding.suppressed else ""
            lines.append(
                f"- [{finding.rule.severity.upper()}]{state} {finding.rule_id} {finding.path}:{finding.line} — {finding.rule.message}"
            )
            lines.append(f"  Remediation: {finding.rule.remediation}")
            if finding.suppressed:
                lines.append(
                    "  Suppression: complete metadata and distinct approver identifier present; "
                    "independence not verified; values redacted; release evidence unchanged."
                )
    else:
        lines.append("Findings: none.")
    if report.tool_errors:
        lines.append("Tool errors:")
        for issue in report.tool_errors:
            lines.append(f"- [TOOL-ERROR] {issue.code} {issue.path} — {issue.message}")
    skipped = ", ".join(f"{key}={value}" for key, value in sorted(report.skipped.items())) or "none"
    lines.extend(
        [
            (
                "Summary: "
                f"considered={summary['files_considered']} scanned={summary['files_scanned']} "
                f"skipped={summary['files_skipped']} blockers={summary['blockers']} "
                f"warnings={summary['warnings']} suppressed={summary['suppressed_warnings']} "
                f"manual-checks={summary['required_manual_checks']} tool-errors={summary['tool_errors']}."
            ),
            f"Skipped by reason: {skipped}.",
            f"Exit code: {report.exit_code}.",
            "Release assertion: none. Exit 0 only means no scanner blocker; it is not GO or proof of security/readiness.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_json(report: Report) -> str:
    return json.dumps(report.as_dict(), indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _sarif_rule(rule: Rule) -> dict[str, object]:
    return {
        "id": rule.rule_id,
        "name": rule.title.replace(" ", ""),
        "shortDescription": {"text": rule.title},
        "fullDescription": {"text": rule.message},
        "defaultConfiguration": {"level": "error" if rule.severity == BLOCKER else "warning"},
        "properties": {"severity": rule.severity, "category": rule.category, "remediation": rule.remediation},
    }


def render_sarif(report: Report) -> str:
    used_rules = sorted({finding.rule_id for finding in report.findings})
    results: list[dict[str, object]] = []
    for finding in report.findings:
        result: dict[str, object] = {
            "ruleId": finding.rule_id,
            "level": "error" if finding.rule.severity == BLOCKER else "warning",
            "message": {"text": finding.rule.message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": quote(finding.path, safe="/._-")},
                        "region": {"startLine": finding.line},
                    }
                }
            ],
            "properties": {
                "severity": finding.rule.severity,
                "evidenceCategory": finding.rule.category,
                "remediation": finding.rule.remediation,
                "suppressed": finding.suppressed,
            },
        }
        if finding.suppressed:
            result["suppressions"] = [
                {
                    "kind": "inSource",
                    "status": "underReview",
                    "justification": "Complete warning metadata with distinct owner and approver identifiers is present; approver independence requires external verification, values are redacted, and release evidence is unchanged.",
                }
            ]
        results.append(result)
    notifications = [
        {
            "descriptor": {"id": issue.code},
            "level": "error",
            "message": {"text": issue.message},
            "properties": {"path": issue.path, "suppressible": False},
        }
        for issue in report.tool_errors
    ]
    document = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": TOOL_NAME,
                        "version": TOOL_VERSION,
                        "semanticVersion": TOOL_VERSION,
                        "rules": [_sarif_rule(RULES[rule_id]) for rule_id in used_rules],
                    }
                },
                "invocations": [
                    {
                        "executionSuccessful": not report.tool_errors,
                        "exitCode": report.exit_code,
                        "toolExecutionNotifications": notifications,
                        "properties": {
                            "scope": report.scope.as_dict(),
                            "summary": report.summary(),
                            "releaseAssertion": "none",
                        },
                    }
                ],
                "results": results,
            }
        ],
    }
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _detect_requested_format(arguments: Sequence[str]) -> str:
    for index, argument in enumerate(arguments):
        if argument.startswith("--format="):
            candidate = argument.split("=", 1)[1]
            return candidate if candidate in {"text", "json", "sarif"} else "text"
        if argument == "--format" and index + 1 < len(arguments):
            candidate = arguments[index + 1]
            return candidate if candidate in {"text", "json", "sarif"} else "text"
    return "text"


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError
    return parsed


def _parser() -> SafeArgumentParser:
    parser = SafeArgumentParser(
        prog="preflight.py",
        description="Read-only local VibeWorthy preflight. A clean scan is not a release approval.",
    )
    parser.add_argument("path", nargs="?", default=".", help="file or directory to scan (default: current directory)")
    parser.add_argument("--format", choices=("text", "json", "sarif"), default="text", help="report format")
    parser.add_argument("--max-file-bytes", type=_positive_integer, default=DEFAULT_MAX_FILE_BYTES, help="skip larger files")
    parser.add_argument("--max-files", type=_positive_integer, default=DEFAULT_MAX_FILES, help="fail closed above this candidate count")
    parser.add_argument("--version", action="version", version=f"{TOOL_NAME} {TOOL_VERSION}")
    return parser


def _render(report: Report, output_format: str) -> str:
    if output_format == "json":
        return render_json(report)
    if output_format == "sarif":
        return render_sarif(report)
    return render_text(report)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    output_format = _detect_requested_format(arguments)
    try:
        options = _parser().parse_args(arguments)
    except UsageFailure:
        report = Report()
        report.tool_errors.append(ToolIssue("usage.invalid-arguments", "Invalid command-line arguments."))
        sys.stdout.write(_render(report, output_format))
        return 2
    try:
        report = scan_path(options.path, options.max_file_bytes, options.max_files)
    except KeyboardInterrupt:
        report = Report()
        report.tool_errors.append(ToolIssue("tool.interrupted", "The scan was interrupted before a complete result was produced."))
    except Exception:  # A safe closed failure must never render source or exception text.
        report = Report()
        report.tool_errors.append(ToolIssue("tool.internal", "The scan failed before a complete result was produced."))
    sys.stdout.write(_render(report, options.format))
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
