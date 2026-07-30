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
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shlex
import shutil
import stat
import subprocess
import sys
import threading
import time
import unicodedata
from collections import Counter, defaultdict
from typing import Iterable, Sequence
from urllib.parse import quote


TOOL_NAME = "vibeworthy-preflight"
TOOL_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"
DEFAULT_MAX_FILE_BYTES = 1_048_576
DEFAULT_MAX_FILES = 20_000
DEFAULT_MAX_TOTAL_BYTES = 67_108_864
DEFAULT_MAX_FINDINGS = 50_000
MAX_PATH_REDACTION_VALUES = 2_048
MAX_PATH_REDACTION_PATTERN_CHARS = 131_072
MAX_SHELL_CLASSIFICATION_TOKENS = 32_768
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
    scope_path: str = ""


@dataclasses.dataclass(frozen=True)
class RootGuard:
    requested: Path
    resolved: Path
    identity: tuple[int, int, int]
    root_is_file: bool


@dataclasses.dataclass
class Scope:
    mode: str = "not-started"
    target: str = "."
    includes: list[str] = dataclasses.field(default_factory=list)
    excludes: list[str] = dataclasses.field(default_factory=list)
    atomic_snapshot: bool = False
    release_evidence_requires_quiescent_isolated_checkout: bool = True
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


class CandidateLimitExceeded(Exception):
    """Candidate enumeration stopped before retaining an unbounded path list."""


class FindingLimitExceeded(Exception):
    """Finding enumeration stopped before a partial report could be trusted."""


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
    re.compile(r"(?<![A-Za-z0-9_])github_pat_[A-Za-z0-9_]{22,255}(?![A-Za-z0-9_])"),
    re.compile(r"(?<![A-Za-z0-9_-])glpat-[A-Za-z0-9_-]{20,255}(?![A-Za-z0-9_-])"),
    re.compile(r"(?<![A-Za-z0-9_-])sk-proj-[A-Za-z0-9_-]{20,255}(?![A-Za-z0-9_-])"),
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
_FIREBASE_LITERAL = (
    r"(?:null|[+-]?[0-9]{1,32}(?:\.[0-9]{1,32})?|"
    r'"(?:\\.|[^"\\\r\n]){0,256}"|'
    r"'(?:\\.|[^'\\\r\n]){0,256}')"
)
_FIREBASE_TRUE_EXPRESSION = (
    r"(?:true(?: *== *true)?|false *== *false|"
    + _FIREBASE_LITERAL
    + r" *== *"
    + _FIREBASE_LITERAL
    + r"|"
    r"(?:! *! *){1,16}true|! *(?:! *! *){0,15}false)"
)
_FIREBASE_LITERAL_EQUALITY_RE = re.compile(
    r"(?<![A-Za-z0-9_.])(?P<left>"
    + _FIREBASE_LITERAL
    + r") *== *(?P<right>"
    + _FIREBASE_LITERAL
    + r")(?![A-Za-z0-9_.])",
    re.IGNORECASE,
)
_FIREBASE_TRUE_OPERAND_RE = re.compile(
    r"(?<![A-Za-z0-9_.!])(?P<expression>"
    + _FIREBASE_TRUE_EXPRESSION
    + r")(?![A-Za-z0-9_.])",
    re.IGNORECASE,
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
_WORKFLOW_IMAGE_RE = re.compile(
    r"(?:^\s*-?\s*|[{,]\s*)[\"']?(?:container|image)[\"']?\s*:\s*[\"']?(?P<reference>[^\s,}#\"']+)",
    re.IGNORECASE,
)
_SUPPRESSION_HINT_RE = re.compile(r"vibeworthy\s*:\s*(?:ignore|suppress)\b", re.IGNORECASE)
_SUPPRESSION_RE = re.compile(
    r"vibeworthy\s*:\s*(?:ignore|suppress)\s+(?:\[)?(?P<rule>[A-Za-z0-9._-]+)(?:\])?(?P<meta>.*)$",
    re.IGNORECASE,
)
_REMOTE_FETCHER_RE = re.compile(r"\b(?:curl|wget)(?:\.exe)?\b", re.IGNORECASE)
_REMOTE_FETCHER_OBFUSCATED_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"c[\\\"'$]*u[\\\"'$]*r[\\\"'$]*l|"
    r"w[\\\"'$]*g[\\\"'$]*e[\\\"'$]*t"
    r")(?:\.exe)?(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
_SHELL_ENCODED_PIPE_RE = re.compile(
    r"\\(?:x7c|174|u007c|U0000007c)",
    re.IGNORECASE,
)
_SHELL_REDIRECTION_RE = re.compile(
    r"(?:[0-9]+|\{[A-Za-z_][A-Za-z0-9_]*\})?"
    r"(?:<<<|<<-?|<>|>>|>\||>|<|&>>|&>|<&|>&)"
    r"(?:[0-9]+|-)?"
)
_COMMAND_INTERPRETERS = frozenset(
    {
        ".", "source", "ash", "bash", "cmd", "csh", "dash", "ksh", "mksh", "sh",
        "zsh", "python", "python2", "python3", "node", "perl", "ruby", "php",
        "powershell", "pwsh",
    }
)
_JSON_LINE_BREAKS = frozenset("\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029")
_SHELL_LITERAL_OPERATOR_CODES = {
    "|": "\0p", ";": "\0s", "&": "\0a", "<": "\0l", ">": "\0g"
}
_SHELL_LITERAL_OPERATOR_VALUES = {
    encoded: operator for operator, encoded in _SHELL_LITERAL_OPERATOR_CODES.items()
}


def _decode_shell_literal_operators(value: str) -> str:
    for encoded, operator in _SHELL_LITERAL_OPERATOR_VALUES.items():
        value = value.replace(encoded, operator)
    return value


def _contains_path(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _path_originates_within(root: Path, path: Path) -> bool:
    """Compare lexical ancestors by object identity without losing redirect origin."""

    for candidate in (path, *path.parents):
        try:
            if candidate.samefile(root):
                return True
        except (OSError, ValueError):
            continue
    return False


def _path_identity(value: os.stat_result) -> tuple[int, int, int]:
    """Return stable object identity without mutable directory metadata."""

    return (value.st_dev, value.st_ino, stat.S_IFMT(value.st_mode))


def _file_snapshot(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _is_path_redirect(value: os.stat_result) -> bool:
    """Recognize POSIX symlinks and Windows name-surrogate reparse points."""

    if stat.S_ISLNK(value.st_mode):
        return True
    if hasattr(value, "st_reparse_tag"):
        return bool(getattr(value, "st_reparse_tag", 0) & 0x20000000)
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse_attribute and getattr(value, "st_file_attributes", 0) & reparse_attribute)


def _resolve_strict(path: Path) -> Path:
    """Resolve a path through a narrow boundary that race tests can control."""

    return path.resolve(strict=True)


def _root_guard_current(guard: RootGuard) -> bool:
    """Verify established root names still reference the original object."""

    for path in dict.fromkeys((guard.requested, guard.resolved)):
        try:
            current = os.lstat(path)
        except (OSError, ValueError):
            return False
        if _is_path_redirect(current) or _path_identity(current) != guard.identity:
            return False
    return True


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


def _normalized_assignment_line(line: str) -> str:
    """Bridge block comments and quoted subscripts without evaluating source."""

    if "/*" not in line and "[" not in line:
        return line
    output: list[str] = []
    index = 0
    quote_character: str | None = None
    escaped = False
    while index < len(line):
        character = line[index]
        if quote_character is not None:
            output.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote_character:
                quote_character = None
            index += 1
            continue
        if character in {'"', "'"}:
            quote_character = character
            output.append(character)
            index += 1
            continue
        if line.startswith("/*", index):
            output.append(" ")
            index += 2
            while index < len(line) and not line.startswith("*/", index):
                index += 1
            index = min(len(line), index + 2)
            output.append(" ")
            continue
        if character == "[":
            cursor = index + 1
            while cursor < len(line) and line[cursor].isspace():
                cursor += 1
            if cursor < len(line) and line[cursor] in {'"', "'"}:
                bracket_quote = line[cursor]
                key_start = cursor + 1
                cursor = key_start
                while cursor < len(line) and line[cursor] != bracket_quote:
                    if line[cursor] == "\\":
                        break
                    cursor += 1
                if cursor < len(line) and line[cursor] == bracket_quote:
                    key = line[key_start:cursor]
                    cursor += 1
                    while cursor < len(line) and line[cursor].isspace():
                        cursor += 1
                    if (
                        cursor < len(line)
                        and line[cursor] == "]"
                        and key
                        and all(
                            item in _ASSIGNMENT_NAME_CHARS and item not in {'"', "'"}
                            for item in key
                        )
                    ):
                        output.extend((".", key))
                        index = cursor + 1
                        continue
        output.append(character)
        index += 1
    return "".join(output)


def _typed_assignment_separator(line: str, start: int) -> int | None:
    """Find a nearby typed-assignment equals with a fixed linear-work budget."""

    limit = min(len(line), start + 512)
    index = start
    while index < limit and line[index].isspace():
        index += 1
    type_start = index
    quote_character: str | None = None
    escaped = False
    nesting: list[str] = []
    pairs = {")": "(", "]": "[", "}": "{", ">": "<"}
    while index < limit:
        character = line[index]
        if quote_character is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote_character:
                quote_character = None
            index += 1
            continue
        if character in {'"', "'"}:
            quote_character = character
            index += 1
            continue
        if character in "([{<":
            nesting.append(character)
            index += 1
            continue
        if character in pairs:
            if nesting and nesting[-1] == pairs[character]:
                nesting.pop()
                index += 1
                continue
            if character == ">":
                return None
        if not nesting and character in {",", ";"}:
            return None
        if not nesting and character == "=":
            if (
                (index + 1 < len(line) and line[index + 1] in {"=", ">"})
                or (index > type_start and line[index - 1] in {"=", "!", "<", ">"})
            ):
                return None
            type_text = line[type_start:index].strip()
            if type_text and any(item.isalpha() or item in {"_", "$"} for item in type_text):
                return index
            return None
        if not nesting and character in {"@", "/", "%", "!", "~", "`"}:
            return None
        index += 1
    return None


def _assignment_value(line: str, separator: int) -> tuple[str, int, bool]:
    value_index = separator + 1
    while value_index < len(line) and line[value_index].isspace():
        value_index += 1
    quote_character = ""
    if value_index < len(line) and line[value_index] in {'"', "'"}:
        quote_character = line[value_index]
        value_index += 1
    value_start = value_index
    if quote_character:
        escaped = False
        while value_index < len(line):
            character = line[value_index]
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote_character:
                return line[value_start:value_index], value_index + 1, True
            value_index += 1
        return line[value_start:value_index], value_index, False
    while value_index < len(line) and line[value_index] in _ASSIGNMENT_VALUE_CHARS:
        value_index += 1
    value = line[value_start:value_index]
    quote_closed = not quote_character or (
        value_index < len(line) and line[value_index] == quote_character
    )
    next_index = value_index + (1 if quote_character and quote_closed else 0)
    return value, next_index, quote_closed


def _generic_assignments_core(
    line: str, *, code_context: bool = False
) -> Iterable[tuple[str, str]]:
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
        separators = [index]
        if character == ":":
            typed_separator = _typed_assignment_separator(line, index + 1)
            if typed_separator is not None:
                separators.append(typed_separator)
        next_index = index + 1
        for separator in separators:
            value, value_end, quote_closed = _assignment_value(line, separator)
            next_index = max(next_index, value_end)
            literal_start = separator + 1
            while literal_start < len(line) and line[literal_start].isspace():
                literal_start += 1
            quoted = literal_start < len(line) and line[literal_start] in {'"', "'"}
            following = value_end
            while following < len(line) and line[following].isspace():
                following += 1
            looks_like_call = not quoted and following < len(line) and line[following] == "("
            direct_colon = character == ":" and separator == index
            bare_identifier = re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", value) is not None
            declaration_prefix = line[max(0, (name_start or 0) - 512) : name_start or 0].lower()
            looks_like_type = (
                code_context
                and
                not quoted
                and value.replace("_", "").isalnum()
                and not any(character.isdigit() for character in value)
                and re.search(r"\b(?:interface|type|function|class|declare)\b", declaration_prefix) is not None
            )
            if (
                _is_secret_assignment_name(name)
                and 12 <= len(value) <= 4_096
                and quote_closed
                and not looks_like_call
                and not looks_like_type
                and not (code_context and not quoted and direct_colon and bare_identifier)
                and not (code_context and not quoted and bare_identifier)
            ):
                yield name, value

        index = next_index
        name_start = None
        name_end = None
        whitespace_after_name = False


def _generic_assignments(
    line: str, *, code_context: bool = False
) -> Iterable[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    normalized = _normalized_assignment_line(line)
    for candidate_line in (line,) if normalized == line else (line, normalized):
        for name, value in _generic_assignments_core(
            candidate_line, code_context=code_context
        ):
            key = (_normalized_assignment_name(name), value)
            if key not in seen:
                seen.add(key)
                yield name, value


def _backtick_assignments(text: str) -> Iterable[tuple[int, str]]:
    """Yield non-interpolated credential literals, including bounded multiline ones."""

    index = 0
    line_number = 1
    while index < len(text):
        opening = text.find("`", index)
        if opening < 0:
            return
        line_number += text.count("\n", index, opening)
        left_boundary = max(text.rfind("\n", max(0, opening - 768), opening), text.rfind(";", max(0, opening - 768), opening))
        prefix = text[left_boundary + 1 : opening]
        separator = prefix.rfind("=")
        if separator < 0:
            separator = prefix.rfind(":")
        name_match = re.search(
            r"([A-Za-z_$][A-Za-z0-9_$.'\"-]{0,255})\s*(?::[^=]{0,512})?=\s*$",
            prefix,
        )
        if name_match is None and separator >= 0:
            name_match = re.search(
                r"([A-Za-z_$][A-Za-z0-9_$.'\"-]{0,255})\s*[:=]\s*$",
                prefix,
            )
        cursor = opening + 1
        escaped = False
        while cursor < len(text):
            character = text[cursor]
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == "`":
                break
            cursor += 1
        if cursor >= len(text):
            return
        value = text[opening + 1 : cursor]
        if (
            name_match is not None
            and _is_secret_assignment_name(name_match.group(1))
            and "${" not in value
            and 12 <= len(value) <= 4_096
            and not _placeholder(value)
        ):
            yield line_number, value
        line_number += text.count("\n", opening, cursor)
        index = cursor + 1


def _detected_assignment_values(
    text: str, *, code_context: bool = False
) -> set[str]:
    values: set[str] = set()
    for line in text.splitlines():
        for match in _PUBLIC_CLIENT_CREDENTIAL_RE.finditer(line):
            value = match.group("value")
            if not _placeholder(value):
                values.add(value)
        for match in _SERVICE_ROLE_ASSIGNMENT_RE.finditer(line):
            value = match.group("value")
            if not _placeholder(value):
                values.add(value)
        for _name, value in _generic_assignments(line, code_context=code_context):
            if not _placeholder(value):
                values.add(value)
    values.update(value for _line, value in _backtick_assignments(text))
    return values


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
    value = unicodedata.normalize("NFC", value)
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


def _filesystem_scope_path(path: Path, fallback: str) -> str:
    """Recover security-relevant path context when no Git root is available."""

    parts = path.parts
    lowered = tuple(part.lower() for part in parts)
    for index in range(len(parts) - 1):
        if lowered[index : index + 2] == (".github", "workflows"):
            return Path(*parts[index:]).as_posix()
    return fallback


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


def _redact_content_values_from_paths(
    candidates: Sequence[Candidate], values: Iterable[str]
) -> list[Candidate]:
    """Redact all detected assignment values from report paths in linear time."""

    transitions: list[dict[str, int]] = [{}]
    failures = [0]
    longest = [0]
    for raw_value in values:
        value = _safe_display_component(raw_value)
        if not value or value == ".":
            continue
        state = 0
        for character in value:
            next_state = transitions[state].get(character)
            if next_state is None:
                next_state = len(transitions)
                transitions[state][character] = next_state
                transitions.append({})
                failures.append(0)
                longest.append(0)
            state = next_state
        longest[state] = max(longest[state], len(value))

    pending: queue.SimpleQueue[int] = queue.SimpleQueue()
    for state in transitions[0].values():
        pending.put(state)
    while not pending.empty():
        state = pending.get()
        longest[state] = max(longest[state], longest[failures[state]])
        for character, child in transitions[state].items():
            fallback = failures[state]
            while fallback and character not in transitions[fallback]:
                fallback = failures[fallback]
            failures[child] = transitions[fallback].get(character, 0)
            pending.put(child)

    redacted: list[Candidate] = []
    for candidate in candidates:
        intervals: list[tuple[int, int]] = []
        state = 0
        for index, character in enumerate(candidate.display_path):
            while state and character not in transitions[state]:
                state = failures[state]
            state = transitions[state].get(character, 0)
            match_length = longest[state]
            if match_length:
                intervals.append((index + 1 - match_length, index + 1))
        if not intervals:
            redacted.append(candidate)
            continue
        merged: list[tuple[int, int]] = []
        for start, end in intervals:
            # Matches arrive in non-decreasing end order, not start order. A
            # longer match can therefore begin before several earlier spans.
            # Collapse every overlap while retaining the leftmost boundary;
            # each span is pushed and popped at most once.
            while merged and start <= merged[-1][1]:
                previous_start, previous_end = merged.pop()
                start = min(start, previous_start)
                end = max(end, previous_end)
            merged.append((start, end))
        parts: list[str] = []
        cursor = 0
        for start, end in merged:
            parts.extend((candidate.display_path[cursor:start], "[REDACTED]"))
            cursor = end
        parts.append(candidate.display_path[cursor:])
        redacted.append(dataclasses.replace(candidate, display_path="".join(parts)))
    return _disambiguate_display_paths(redacted)


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


def _git_environment() -> dict[str, str]:
    """Keep the caller's normal config locations but remove Git behavior overrides."""

    environment = os.environ.copy()
    for name in tuple(environment):
        if name.upper().startswith("GIT_"):
            environment.pop(name, None)
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def _controlled_source_root(cwd: Path) -> Path:
    """Find the outermost visible repository boundary without invoking Git."""

    current = cwd if cwd.is_dir() else cwd.parent
    controlled_root = current
    for candidate in (current, *current.parents):
        try:
            os.lstat(candidate / ".git")
        except (FileNotFoundError, NotADirectoryError):
            continue
        except OSError:
            # An unreadable marker is still a controlled boundary. Keep
            # walking so a nested marker cannot narrow an outer worktree.
            controlled_root = candidate
            continue
        controlled_root = candidate
    return controlled_root


def _resolve_git_executable(cwd: Path) -> str:
    """Resolve Git without trusting relative or worktree-controlled PATH entries."""

    try:
        resolved_cwd = cwd.resolve(strict=True)
    except OSError as exc:
        raise GitUnavailable from exc
    controlled_root = _controlled_source_root(resolved_cwd)
    path_value = os.environ.get("PATH", "")
    for entry in path_value.split(os.pathsep):
        if not entry:
            continue
        entry_path = Path(entry)
        if not entry_path.is_absolute():
            continue
        try:
            lexical_entry = Path(os.path.abspath(os.fspath(entry_path)))
        except (OSError, ValueError):
            continue
        if _path_originates_within(controlled_root, lexical_entry):
            continue
        candidate = shutil.which("git", path=os.fspath(entry_path))
        if candidate is None:
            continue
        candidate_path = Path(candidate)
        if not candidate_path.is_absolute():
            continue
        try:
            lexical_candidate = Path(os.path.abspath(os.fspath(candidate_path)))
            resolved_candidate = candidate_path.resolve(strict=True)
            candidate_stat = resolved_candidate.stat()
        except (OSError, ValueError):
            continue
        if not stat.S_ISREG(candidate_stat.st_mode):
            continue
        if _path_originates_within(controlled_root, lexical_candidate):
            continue
        candidate_parent = resolved_candidate.parent
        if _contains_path(controlled_root, resolved_candidate) or _contains_path(
            candidate_parent, controlled_root
        ):
            continue
        return os.fspath(resolved_candidate)
    raise GitUnavailable


def _git_command(executable: str, arguments: Sequence[str]) -> list[str]:
    return [
        executable,
        "-c",
        "core.quotepath=false",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.untrackedCache=false",
        *arguments,
    ]


def _run_git(cwd: Path, arguments: Sequence[str]) -> tuple[int, bytes]:
    executable = _resolve_git_executable(cwd)
    try:
        completed = subprocess.run(
            _git_command(executable, arguments),
            cwd=os.fspath(cwd),
            env=_git_environment(),
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


def _run_git_paths(cwd: Path, arguments: Sequence[str], max_paths: int) -> tuple[int, list[bytes]]:
    """Read NUL-delimited Git paths with bounded buffering and an early count limit."""

    executable = _resolve_git_executable(cwd)
    try:
        process = subprocess.Popen(
            _git_command(executable, arguments),
            cwd=os.fspath(cwd),
            env=_git_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError as exc:
        raise GitUnavailable from exc
    except OSError as exc:
        raise RuntimeError("git-failed") from exc

    chunks: queue.Queue[bytes | None] = queue.Queue(maxsize=4)
    stop_reader = threading.Event()
    reader_failed = threading.Event()

    def publish(item: bytes | None) -> bool:
        while not stop_reader.is_set():
            try:
                chunks.put(item, timeout=0.05)
                return True
            except queue.Full:
                continue
        return False

    def read_stdout() -> None:
        try:
            if process.stdout is None:
                reader_failed.set()
                return
            while not stop_reader.is_set():
                chunk = process.stdout.read(65_536)
                if not chunk:
                    break
                if not publish(chunk):
                    return
        except OSError:
            reader_failed.set()
        finally:
            publish(None)

    reader = threading.Thread(target=read_stdout, name="vibeworthy-git-reader", daemon=True)
    reader.start()
    deadline = time.monotonic() + 30
    entries: list[bytes] = []
    pending = b""
    exceeded = False
    timed_out = False
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            try:
                chunk = chunks.get(timeout=remaining)
            except queue.Empty:
                timed_out = True
                break
            if chunk is None:
                break
            parts = (pending + chunk).split(b"\0")
            pending = parts.pop()
            for encoded_path in parts:
                if not encoded_path:
                    continue
                if len(entries) >= max_paths:
                    exceeded = True
                    break
                entries.append(encoded_path)
            if exceeded:
                break
    finally:
        if exceeded or timed_out:
            stop_reader.set()
            process.kill()
        try:
            process.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            timed_out = True
            stop_reader.set()
            process.kill()
            process.wait()
        stop_reader.set()
        if process.stdout is not None:
            process.stdout.close()
        reader.join(timeout=1)

    if exceeded:
        raise CandidateLimitExceeded
    if timed_out or reader_failed.is_set() or reader.is_alive() or pending:
        raise RuntimeError("git-failed")
    return process.returncode, entries


def _git_candidates(
    target: Path,
    target_is_file: bool,
    max_files: int,
    report: Report,
) -> list[Candidate] | None:
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
    target_resolved = target
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
            return_code, encoded_paths = _run_git_paths(
                git_root,
                command,
                max_files - len(by_raw_path),
            )
        except CandidateLimitExceeded:
            report.tool_errors.append(
                ToolIssue(
                    "tool.file-limit",
                    "The candidate-file limit was exceeded; enumeration stopped before a partial clean result was produced.",
                )
            )
            return []
        except (GitUnavailable, RuntimeError):
            report.tool_errors.append(ToolIssue("tool.git-enumeration", "Git worktree enumeration failed."))
            return []
        if return_code != 0:
            report.tool_errors.append(ToolIssue("tool.git-enumeration", "Git worktree enumeration failed."))
            return []
        for encoded_path in encoded_paths:
            raw_relative = os.fsdecode(encoded_path)
            candidate_path = git_root / raw_relative
            display = _relative_display(candidate_path, target_resolved, target_is_file)
            by_raw_path[raw_relative] = Candidate(
                candidate_path,
                display,
                tracked,
                os.fsencode(raw_relative),
                raw_relative,
            )

    report.scope = Scope(
        mode="git-worktree",
        includes=["tracked", "untracked-non-ignored"],
        excludes=["git-history", "submodules", "ignored", "symlinks", "binary", "generated-or-vendor", "oversized"],
    )
    return _disambiguate_display_paths(list(by_raw_path.values()))


def _filesystem_candidates(
    target: Path,
    target_is_file: bool,
    max_files: int,
    report: Report,
) -> list[Candidate]:
    report.scope = Scope(
        mode="filesystem",
        includes=["regular-files"],
        excludes=["git-history", "submodules", "symlinks", "binary", "generated-or-vendor", "oversized"],
    )
    if target_is_file:
        if max_files < 1:
            report.tool_errors.append(
                ToolIssue(
                    "tool.file-limit",
                    "The candidate-file limit was exceeded; enumeration stopped before a partial clean result was produced.",
                )
            )
            return []
        display = _safe_display_component(target.name)
        return [
            Candidate(
                target,
                display,
                None,
                os.fsencode(target.name),
                _filesystem_scope_path(target, display),
            )
        ]

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
            else:
                try:
                    directory_stat = os.lstat(directory_path)
                except OSError as error:
                    errors.append(error)
                    continue
                if _is_path_redirect(directory_stat):
                    report.skipped["symlink"] += 1
                else:
                    retained_directories.append(directory_name)
        directory_names[:] = retained_directories
        for file_name in sorted(file_names):
            path = current_path / file_name
            raw_relative = os.fspath(path.relative_to(target))
            display = _relative_display(path, target, False)
            if len(candidates) >= max_files:
                report.tool_errors.append(
                    ToolIssue(
                        "tool.file-limit",
                        "The candidate-file limit was exceeded; enumeration stopped before a partial clean result was produced.",
                    )
                )
                return []
            candidates.append(
                Candidate(
                    path,
                    display,
                    None,
                    os.fsencode(raw_relative),
                    _filesystem_scope_path(path, display),
                )
            )
    if errors:
        report.tool_errors.append(ToolIssue("tool.walk", "One or more directories could not be enumerated safely."))
    return _disambiguate_display_paths(candidates)


def _enumerate_candidates(
    target: Path,
    max_files: int,
    report: Report,
) -> tuple[list[Candidate], RootGuard | None]:
    try:
        target_stat = os.lstat(target)
    except (OSError, ValueError):
        report.tool_errors.append(ToolIssue("tool.target", "The requested target could not be accessed safely."))
        return [], None
    if _is_path_redirect(target_stat):
        report.tool_errors.append(
            ToolIssue("tool.target-symlink", "A symlink or filesystem redirect cannot be used as the scan root.")
        )
        return [], None
    target_is_file = stat.S_ISREG(target_stat.st_mode)
    if not target_is_file and not stat.S_ISDIR(target_stat.st_mode):
        report.tool_errors.append(ToolIssue("tool.target-type", "The scan root must be a regular file or directory."))
        return [], None
    identity = _path_identity(target_stat)
    try:
        resolved = _resolve_strict(target)
        requested_after = os.lstat(target)
        resolved_stat = os.lstat(resolved)
    except (OSError, ValueError):
        report.tool_errors.append(ToolIssue("tool.target", "The requested target could not be resolved safely."))
        return [], None
    if (
        _is_path_redirect(requested_after)
        or _is_path_redirect(resolved_stat)
        or _path_identity(requested_after) != identity
        or _path_identity(resolved_stat) != identity
    ):
        report.tool_errors.append(
            ToolIssue("tool.target-race", "The requested scan root changed while its identity was being established.")
        )
        return [], None

    guard = RootGuard(target, resolved, identity, target_is_file)

    candidates = _git_candidates(resolved, target_is_file, max_files, report)
    if candidates is None:
        candidates = _filesystem_candidates(resolved, target_is_file, max_files, report)
    if not _root_guard_current(guard):
        report.tool_errors.append(
            ToolIssue("tool.target-race", "The requested scan root changed while candidates were being enumerated.")
        )
        return [], None
    return candidates, guard


def _has_symlink_component(path: Path, allowed_root: Path) -> bool:
    """Reject a candidate whose path below the root traverses a filesystem redirect."""

    try:
        relative = path.relative_to(allowed_root)
    except ValueError:
        return True
    current = allowed_root
    for component in relative.parts[:-1]:
        current = current / component
        try:
            if _is_path_redirect(os.lstat(current)):
                return True
        except OSError:
            return True
    return False


def _open_readonly(path: Path) -> int:
    """Open a candidate without following its final symlink where supported."""

    flags = os.O_RDONLY
    flags |= getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    return os.open(path, flags)


def _descriptor_stat(descriptor: int) -> os.stat_result:
    """Read descriptor metadata through a narrow, independently testable boundary."""

    return os.fstat(descriptor)


def _read_candidate(
    candidate: Candidate,
    root_guard: RootGuard,
    max_bytes: int,
    report: Report,
    *,
    count_scan: bool = True,
) -> str | None:
    if not _root_guard_current(root_guard):
        report.tool_errors.append(
            ToolIssue("tool.target-race", "The requested scan root changed while files were being read.")
        )
        return None
    scan_root = root_guard.resolved
    root_is_file = root_guard.root_is_file
    skip_reason = _skip_path_reason(candidate.scope_path or candidate.display_path)
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
    if _is_path_redirect(file_stat):
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

    try:
        descriptor = _open_readonly(candidate.path)
        try:
            opened_stat = _descriptor_stat(descriptor)
            if not stat.S_ISREG(opened_stat.st_mode):
                report.skipped["special-file"] += 1
                return None
            if _file_snapshot(file_stat) != _file_snapshot(opened_stat):
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
            final_opened_stat = _descriptor_stat(descriptor)
        finally:
            os.close(descriptor)
    except OSError:
        report.tool_errors.append(ToolIssue("tool.file-read", "A candidate file could not be read safely.", candidate.display_path))
        return None
    try:
        final_path_stat = os.lstat(candidate.path)
        final_resolved = candidate.path.resolve(strict=True)
    except OSError:
        report.tool_errors.append(
            ToolIssue(
                "tool.file-race",
                "A candidate changed while it was being read; no content was scanned.",
                candidate.display_path,
            )
        )
        return None
    if (
        _file_snapshot(opened_stat) != _file_snapshot(final_opened_stat)
        or _file_snapshot(final_opened_stat) != _file_snapshot(final_path_stat)
        or final_resolved != resolved
        or _has_symlink_component(candidate.path, allowed_root)
    ):
        report.tool_errors.append(
            ToolIssue(
                "tool.file-race",
                "A candidate changed while it was being read; no content was scanned.",
                candidate.display_path,
            )
        )
        return None
    if not _root_guard_current(root_guard):
        report.tool_errors.append(
            ToolIssue("tool.target-race", "The requested scan root changed while files were being read.")
        )
        return None
    if len(content) > max_bytes:
        report.skipped["oversized"] += 1
        return None
    if b"\0" in content:
        if candidate.path.name == "package.json":
            report.tool_errors.append(
                ToolIssue(
                    "tool.manifest-binary",
                    "A package manifest contains NUL bytes and cannot be parsed safely.",
                    candidate.display_path,
                )
            )
            return None
        report.skipped["binary"] += 1
        return None
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        report.skipped["binary"] += 1
        return None
    if count_scan:
        report.files_scanned += 1
    return text


def _placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    if not lowered:
        return True
    if lowered.startswith(("${", "{{", "<", "process.env")):
        return True
    if re.match(
        r"^(?:https?://)?(?:[^/@\s]+@)?(?:localhost|(?:[^./\s]+\.)*example\.(?:com|org|net)|(?:[^./\s]+\.)*(?:invalid|test))(?:[/:?#]|$)",
        lowered,
    ):
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


def _json_location_tokens(text: str) -> Iterable[tuple[str, str, int]]:
    """Yield decoded strings, structural punctuation, and atoms with line numbers."""

    index = 0
    line_number = 1
    punctuation = set("{}[]:,")
    while index < len(text):
        character = text[index]
        if character.isspace():
            if character in _JSON_LINE_BREAKS:
                line_number += 1
                if character == "\r" and index + 1 < len(text) and text[index + 1] == "\n":
                    index += 1
            index += 1
            continue
        if character == '"':
            start = index
            start_line = line_number
            index += 1
            escaped = False
            while index < len(text):
                current = text[index]
                if current in _JSON_LINE_BREAKS:
                    line_number += 1
                    if current == "\r" and index + 1 < len(text) and text[index + 1] == "\n":
                        index += 1
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    index += 1
                    break
                index += 1
            try:
                decoded = json.loads(text[start:index])
            except (json.JSONDecodeError, TypeError):
                decoded = ""
            yield "string", decoded if isinstance(decoded, str) else "", start_line
            continue
        if character in punctuation:
            yield character, character, line_number
            index += 1
            continue
        start = index
        while index < len(text) and not text[index].isspace() and text[index] not in punctuation:
            index += 1
        yield "atom", text[start:index], line_number


def _line_numbers_for_json_object_keys(
    text: str,
    object_key: str,
    keys: set[str],
) -> dict[str, int]:
    """Locate effective keys in the effective top-level JSON object value."""

    containers: list[str] = []
    previous: tuple[str, str, int] | None = None
    waiting_for_object_value = False
    active_depth: int | None = None
    result: dict[str, int] = {}
    for kind, value, line_number in _json_location_tokens(text):
        if kind == ":":
            if previous is not None and previous[0] == "string":
                key, key_line = previous[1], previous[2]
                if containers == ["object"] and key == object_key:
                    waiting_for_object_value = True
                if (
                    active_depth is not None
                    and len(containers) == active_depth
                    and containers[-1:] == ["object"]
                    and key in keys
                ):
                    result[key] = key_line
            previous = (kind, value, line_number)
            continue

        activates_object = waiting_for_object_value and kind == "{"
        if waiting_for_object_value:
            result = {}
            active_depth = None
            waiting_for_object_value = False

        if kind == "{":
            containers.append("object")
            if activates_object:
                active_depth = len(containers)
        elif kind == "[":
            containers.append("array")
        elif kind in {"}", "]"}:
            if active_depth is not None and len(containers) == active_depth:
                active_depth = None
            if containers:
                containers.pop()
        previous = (kind, value, line_number)
    return result


def _is_firebase_rules_path(display_path: str) -> bool:
    lower = display_path.lower()
    name = Path(lower).name
    return (
        name in {"firestore.rules", "storage.rules", "database.rules.json", "firebase.rules"}
        or bool(re.fullmatch(r"database(?:\.[a-z0-9_-]+)*\.rules\.json", name))
        or lower.endswith(".rules")
    )


def _is_workflow_path(display_path: str) -> bool:
    lower = display_path.lower()
    return lower.startswith(".github/workflows/") and lower.endswith((".yml", ".yaml"))


def _is_code_assignment_path(path: Path) -> bool:
    return path.suffix.lower() in {
        ".c", ".cc", ".cpp", ".cs", ".go", ".java", ".js", ".jsx", ".kt",
        ".mjs", ".cjs", ".php", ".py", ".rb", ".rs", ".swift", ".ts", ".tsx",
    }


def _action_is_pinned(reference: str) -> bool:
    if reference.startswith("./"):
        return True
    if reference.startswith("docker://"):
        return "@sha256:" in reference.lower() and bool(re.search(r"@sha256:[0-9a-f]{64}$", reference, re.IGNORECASE))
    if "@" not in reference:
        return False
    revision = reference.rsplit("@", 1)[1]
    return bool(re.fullmatch(r"[0-9a-fA-F]{40}", revision))


def _container_is_pinned(reference: str) -> bool:
    return bool(re.search(r"@sha256:[0-9a-f]{64}$", reference, re.IGNORECASE))


def _shell_without_comment(line: str) -> str:
    quote_character: str | None = None
    escaped = False
    token_started = False
    for index, character in enumerate(line):
        if escaped:
            escaped = False
            token_started = True
            continue
        if character == "\\" and quote_character != "'":
            escaped = True
            token_started = True
            continue
        if character in {'"', "'"}:
            quote_character = None if quote_character == character else (
                character if quote_character is None else quote_character
            )
            token_started = True
            continue
        if quote_character is None and character == "#" and not token_started:
            return line[:index].rstrip()
        if quote_character is None and (character.isspace() or character in "|;&()"):
            token_started = False
        else:
            token_started = True
    return line.rstrip()


def _contextual_shell_commands(command: str) -> list[str]:
    stripped = command.strip()
    yaml_match = re.match(r"^(?:-\s*)?run\s*:\s*(.*)$", stripped, re.IGNORECASE | re.DOTALL)
    if yaml_match:
        payload = yaml_match.group(1).strip()
        if payload in {"|", "|-", "|+", ">", ">-", ">+"}:
            return []
        if len(payload) >= 2 and payload[0] == payload[-1] and payload[0] in {'"', "'"}:
            quote_character = payload[0]
            payload = payload[1:-1]
            if quote_character == '"':
                payload = _decode_yaml_double_quoted_scalar(payload)
        return [payload]
    docker_match = re.match(r"^RUN\s+(.*)$", stripped, re.IGNORECASE | re.DOTALL)
    if docker_match:
        payload = docker_match.group(1).strip()
        if payload.startswith("["):
            try:
                arguments = json.loads(payload)
            except json.JSONDecodeError:
                return [payload]
            if isinstance(arguments, list) and all(isinstance(item, str) for item in arguments):
                return [" ".join(shlex.quote(item) for item in arguments)]
        return [payload]
    if stripped and stripped[0] in "@+-" and not stripped.startswith("--"):
        stripped = stripped.lstrip("@+- ")
    return [stripped]


def _decode_yaml_double_quoted_scalar(value: str) -> str:
    """Decode bounded YAML double-quoted escapes that can alter shell syntax."""

    escapes = {
        "0": "\0", "a": "\a", "b": "\b", "t": "\t", "n": "\n",
        "v": "\v", "f": "\f", "r": "\r", "e": "\x1b", " ": " ",
        '"': '"', "/": "/", "\\": "\\", "N": "\x85", "_": "\xa0",
        "L": "\u2028", "P": "\u2029",
    }
    output: list[str] = []
    index = 0
    while index < len(value):
        character = value[index]
        if character != "\\" or index + 1 >= len(value):
            output.append(character)
            index += 1
            continue
        escape = value[index + 1]
        widths = {"x": 2, "u": 4, "U": 8}
        if escape in widths:
            width = widths[escape]
            digits = value[index + 2 : index + 2 + width]
            if len(digits) == width and re.fullmatch(r"[0-9A-Fa-f]+", digits):
                try:
                    output.append(chr(int(digits, 16)))
                except ValueError:
                    output.extend(("\\", escape, digits))
                index += 2 + width
                continue
        replacement = escapes.get(escape)
        if replacement is not None:
            output.append(replacement)
            index += 2
            continue
        output.extend(("\\", escape))
        index += 2
    return "".join(output)


def _heredoc_spec(command: str) -> tuple[str, bool, bool] | None:
    contexts = _contextual_shell_commands(command)
    if not contexts:
        return None
    tokens, complete = _tokenize_shell_line(contexts[0])
    if not complete:
        return None
    for index, token in enumerate(tokens[:-1]):
        is_heredoc = token.endswith("<<-") or (
            token.endswith("<<") and not token.endswith("<<<")
        )
        if _SHELL_REDIRECTION_RE.fullmatch(token) is None or not is_heredoc:
            continue
        delimiter = tokens[index + 1]
        if not delimiter:
            return None
        preceding_commands = _simple_shell_commands(tokens[:index])
        invocation = _command_invocation(preceding_commands[-1] if preceding_commands else ())
        interpreters = _COMMAND_INTERPRETERS
        downstream_names = [
            _shell_command_name(command)
            for command in _simple_shell_commands(tokens[index + 2 :])
        ]
        descriptor = token[: -3 if token.endswith("<<-") else -2]
        feeds_standard_input = descriptor in {"", "0"}
        docker_run_heredoc = re.match(r"^\s*RUN\b", command, re.IGNORECASE) is not None
        executes = docker_run_heredoc or (
            feeds_standard_input and invocation.executable in interpreters
        ) or (
            feeds_standard_input
            and invocation.executable == "cat"
            and any(name in interpreters for name in downstream_names)
        )
        return delimiter, token.endswith("<<-"), executes
    return None


def _logical_shell_commands(
    text: str,
    shell_payload: bool = False,
) -> Iterable[tuple[int, str, bool]]:
    """Yield executable logical lines, excluding data-only heredoc bodies."""

    parts: list[str] = []
    start_line = 1
    heredoc: tuple[str, bool, bool, int] | None = None
    heredoc_body: list[str] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if heredoc is not None:
            delimiter, strip_tabs, executes, body_start = heredoc
            comparison = raw_line.lstrip("\t") if strip_tabs else raw_line
            if comparison == delimiter:
                if executes and heredoc_body:
                    for nested_line, nested_command, _nested_payload in _logical_shell_commands(
                        "\n".join(heredoc_body),
                        True,
                    ):
                        yield body_start + nested_line - 1, nested_command, True
                heredoc = None
                heredoc_body = []
            else:
                heredoc_body.append(raw_line.lstrip("\t") if strip_tabs else raw_line)
            continue
        if not parts:
            start_line = line_number
        trimmed = _shell_without_comment(raw_line).rstrip()
        trailing_backslashes = len(trimmed) - len(trimmed.rstrip("\\"))
        backslash_continuation = trailing_backslashes % 2 == 1
        if backslash_continuation:
            trimmed = trimmed[:-1].rstrip()
        trailing_carets = len(trimmed) - len(trimmed.rstrip("^"))
        caret_continuation = trailing_carets % 2 == 1
        if caret_continuation:
            trimmed = trimmed[:-1].rstrip()
        parts.append(trimmed)
        pipeline_continuation = trimmed.endswith(("|", "|&", "||"))
        if backslash_continuation or caret_continuation or pipeline_continuation:
            continue
        logical = " ".join(parts)
        yield start_line, logical, shell_payload
        specification = _heredoc_spec(logical)
        if specification is not None:
            delimiter, strip_tabs, executes = specification
            heredoc = (delimiter, strip_tabs, executes, line_number + 1)
        parts = []
    if heredoc is not None:
        _delimiter, _strip_tabs, executes, body_start = heredoc
        if executes and heredoc_body:
            for nested_line, nested_command, _nested_payload in _logical_shell_commands(
                "\n".join(heredoc_body),
                True,
            ):
                yield body_start + nested_line - 1, nested_command, True
    elif parts:
        yield start_line, " ".join(parts), shell_payload


def _yaml_folded_shell_commands(text: str) -> Iterable[tuple[int, str, bool]]:
    """Yield common folded YAML command scalars as their executed shell text."""

    lines = text.splitlines()
    header = re.compile(r"^(?P<indent> *)(?:run|script|command)\s*:\s*>[-+]?\s*(?:#.*)?$", re.IGNORECASE)
    index = 0
    while index < len(lines):
        match = header.match(lines[index])
        if match is None:
            index += 1
            continue
        base_indent = len(match.group("indent"))
        cursor = index + 1
        body: list[tuple[int, str, int] | None] = []
        while cursor < len(lines):
            raw_line = lines[cursor]
            if not raw_line.strip():
                body.append(None)
                cursor += 1
                continue
            indentation = len(raw_line) - len(raw_line.lstrip(" "))
            if indentation <= base_indent:
                break
            body.append((cursor + 1, raw_line, indentation))
            cursor += 1
        first_content = next((item for item in body if item is not None), None)
        if first_content is not None:
            content_indent = first_content[2]
            executed_lines: list[str] = []
            source_lines: list[int] = []
            folded_parts: list[str] = []
            folded_start = first_content[0]

            def flush_folded() -> None:
                nonlocal folded_parts
                if folded_parts:
                    executed_lines.append(" ".join(folded_parts))
                    source_lines.append(folded_start)
                    folded_parts = []

            for item in body:
                if item is None:
                    flush_folded()
                    continue
                source_line, raw_line, indentation = item
                if indentation > content_indent:
                    flush_folded()
                    executed_lines.append(raw_line[content_indent:].rstrip())
                    source_lines.append(source_line)
                    continue
                if not folded_parts:
                    folded_start = source_line
                folded_parts.append(raw_line[content_indent:].strip())
            flush_folded()
            for local_line, command, _shell_payload in _logical_shell_commands(
                "\n".join(executed_lines),
                True,
            ):
                source_index = min(max(local_line - 1, 0), len(source_lines) - 1)
                yield source_lines[source_index], command, True
        index = max(index + 1, cursor)


@dataclasses.dataclass(frozen=True)
class _CommandInvocation:
    tokens: tuple[str, ...]
    executable: str | None
    executable_index: int | None
    complete: bool = True


def _without_shell_redirections(tokens: Sequence[str]) -> tuple[tuple[str, ...], bool]:
    """Remove syntactic redirections and their non-command targets."""

    result: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if _SHELL_REDIRECTION_RE.fullmatch(token) is None:
            result.append(token)
            index += 1
            continue
        inline_descriptor_target = re.search(r"(?:<|>)&(?:[0-9]+|-)$", token) is not None
        index += 1
        if inline_descriptor_target:
            continue
        if index >= len(tokens) or (
            tokens[index] and all(character in "|;&" for character in tokens[index])
        ):
            return tuple(result), False
        index += 1
    return tuple(result), True


def _command_invocation(tokens: Sequence[str], depth: int = 0) -> _CommandInvocation:
    if depth > 4:
        return _CommandInvocation(tuple(tokens), None, None, False)
    current_tokens, redirections_complete = _without_shell_redirections(tokens)
    if not redirections_complete:
        return _CommandInvocation(current_tokens, None, None, False)

    index = 0
    assignment = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*", re.DOTALL)
    control_prefixes = {
        "(",
        "{",
        "!",
        "coproc",
        "do",
        "elif",
        "else",
        "if",
        "then",
        "until",
        "while",
    }
    sudo_options_with_value = {
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
    }
    env_options_with_value = {"-u", "--unset", "-C", "--chdir", "-a", "--argv0"}
    timeout_options_with_value = {"-k", "--kill-after", "-s", "--signal"}
    time_options_with_value = {"-f", "--format", "-o", "--output"}
    time_options_without_value = {
        "-a",
        "--append",
        "-p",
        "--portability",
        "-q",
        "--quiet",
        "-v",
        "--verbose",
    }

    while index < len(current_tokens):
        while index < len(current_tokens):
            token = current_tokens[index]
            if token in control_prefixes or token.endswith(")"):
                index += 1
                continue
            if assignment.fullmatch(token):
                index += 1
                continue
            break
        if index >= len(current_tokens):
            return _CommandInvocation(current_tokens, None, None)

        if current_tokens[index] == "case":
            saw_in = False
            branch_index: int | None = None
            for cursor in range(index + 1, len(current_tokens)):
                if current_tokens[cursor] == "in":
                    saw_in = True
                    continue
                if saw_in and current_tokens[cursor].endswith(")"):
                    branch_index = cursor + 1
                    break
            if branch_index is None:
                return _CommandInvocation(current_tokens, None, None, False)
            index = branch_index
            continue

        function_index = index
        function_token = current_tokens[function_index]
        body_index: int | None = None
        if function_token == "function":
            name_index = function_index + 1
            if name_index >= len(current_tokens):
                return _CommandInvocation(current_tokens, None, None, False)
            name_token = current_tokens[name_index]
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\(\)\{?", name_token):
                body_index = name_index + 1
                if name_token.endswith("{"):
                    index = body_index
                    continue
            elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name_token):
                body_index = name_index + 1
                if body_index < len(current_tokens) and current_tokens[body_index] == "()":
                    body_index += 1
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\(\)\{?", function_token):
            body_index = function_index + 1
            if function_token.endswith("{"):
                index = body_index
                continue
        elif (
            re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", function_token)
            and function_index + 1 < len(current_tokens)
            and current_tokens[function_index + 1] == "()"
        ):
            body_index = function_index + 2
        if body_index is not None:
            if (
                body_index >= len(current_tokens)
                or current_tokens[body_index] not in {"{", "("}
            ):
                return _CommandInvocation(current_tokens, None, None, False)
            index = body_index + 1
            continue

        wrapper_index = index
        name = _normalized_executable_name(current_tokens[index])
        if name == "busybox":
            applet_index = index + 1
            if applet_index < len(current_tokens) and not current_tokens[applet_index].startswith("-"):
                return _command_invocation(
                    current_tokens[applet_index:],
                    depth + 1,
                )
            return _CommandInvocation(current_tokens, name, wrapper_index)
        if name not in {
            "builtin",
            "chrt",
            "command",
            "doas",
            "env",
            "exec",
            "ionice",
            "nice",
            "nohup",
            "setsid",
            "stdbuf",
            "sudo",
            "taskset",
            "time",
            "timeout",
            "xargs",
        }:
            return _CommandInvocation(current_tokens, name, index)
        index += 1

        if name == "builtin":
            while index < len(current_tokens) and current_tokens[index] in {"-a", "--"}:
                index += 1
            if (
                index >= len(current_tokens)
                or _normalized_executable_name(current_tokens[index])
                not in {"command", "eval", "exec"}
            ):
                return _CommandInvocation(current_tokens, "builtin", wrapper_index)
            continue

        if name == "command":
            while index < len(current_tokens) and current_tokens[index].startswith("-"):
                argument = current_tokens[index]
                if argument == "--":
                    index += 1
                    break
                if argument in {"-v", "-V"}:
                    return _CommandInvocation(current_tokens, "command", wrapper_index)
                index += 1
            continue

        if name == "env":
            while index < len(current_tokens):
                argument = current_tokens[index]
                if assignment.fullmatch(argument) is not None:
                    index += 1
                    continue
                split_string: str | None = None
                tail_index = index + 1
                if argument in {"-S", "--split-string"}:
                    if tail_index >= len(current_tokens):
                        return _CommandInvocation(current_tokens, None, None, False)
                    split_string = current_tokens[tail_index]
                    tail_index += 1
                elif argument.startswith("--split-string="):
                    split_string = argument.split("=", 1)[1]
                elif argument.startswith("-S") and argument != "-S":
                    split_string = argument[2:]
                if split_string is not None:
                    embedded_tokens, complete = _tokenize_shell_line(
                        _decode_shell_literal_operators(split_string)
                    )
                    if not complete or not embedded_tokens:
                        return _CommandInvocation(current_tokens, None, None, False)
                    return _command_invocation(
                        (*embedded_tokens, *current_tokens[tail_index:]),
                        depth + 1,
                    )
                if argument == "--":
                    index += 1
                    break
                if not argument.startswith("-"):
                    break
                option = argument.split("=", 1)[0]
                index += 1
                if (
                    option in env_options_with_value
                    and "=" not in argument
                    and index < len(current_tokens)
                ):
                    index += 1
            continue

        if name == "exec":
            while index < len(current_tokens) and current_tokens[index].startswith("-"):
                argument = current_tokens[index]
                if argument == "--":
                    index += 1
                    break
                index += 1
                if argument == "-a" and index < len(current_tokens):
                    index += 1
            continue

        if name == "sudo":
            while index < len(current_tokens):
                argument = current_tokens[index]
                if assignment.fullmatch(argument) is not None:
                    index += 1
                    continue
                if argument == "--":
                    index += 1
                    break
                if not argument.startswith("-"):
                    break
                option = argument.split("=", 1)[0]
                index += 1
                if (
                    option in sudo_options_with_value
                    and "=" not in argument
                    and index < len(current_tokens)
                ):
                    index += 1
            continue

        if name == "nohup":
            if index < len(current_tokens) and current_tokens[index] == "--":
                index += 1
            elif index < len(current_tokens) and current_tokens[index].startswith("-"):
                return _CommandInvocation(current_tokens, "nohup", wrapper_index)
            continue

        if name == "chrt":
            pid_mode = False
            options_with_value = {
                "-D", "--sched-deadline", "-P", "--sched-period",
                "-T", "--sched-runtime",
            }
            options_without_value = {
                "-a", "--all-tasks", "-b", "--batch", "-d", "--deadline",
                "-f", "--fifo", "-i", "--idle", "-m", "--max",
                "-o", "--other", "-R", "--reset-on-fork", "-r", "--rr",
                "-v", "--verbose",
            }
            while index < len(current_tokens) and current_tokens[index].startswith("-"):
                argument = current_tokens[index]
                if argument == "--":
                    index += 1
                    break
                option = argument.split("=", 1)[0]
                if option in {"-p", "--pid"}:
                    pid_mode = True
                    index += 1
                    continue
                if option not in options_with_value and option not in options_without_value:
                    return _CommandInvocation(current_tokens, None, None, False)
                index += 1
                if option in options_with_value and "=" not in argument:
                    if index >= len(current_tokens):
                        return _CommandInvocation(current_tokens, None, None, False)
                    index += 1
            if pid_mode:
                return _CommandInvocation(current_tokens, "chrt", wrapper_index)
            if index + 1 >= len(current_tokens):
                return _CommandInvocation(current_tokens, None, None, False)
            index += 1  # scheduling priority
            continue

        if name == "doas":
            shell_mode = False
            while index < len(current_tokens) and current_tokens[index].startswith("-"):
                argument = current_tokens[index]
                if argument == "--":
                    index += 1
                    break
                if argument in {"-L", "-n"}:
                    index += 1
                    continue
                if argument == "-s":
                    shell_mode = True
                    index += 1
                    continue
                if argument in {"-C", "-u"}:
                    if index + 1 >= len(current_tokens):
                        return _CommandInvocation(current_tokens, None, None, False)
                    index += 2
                    continue
                return _CommandInvocation(current_tokens, None, None, False)
            if shell_mode:
                return _CommandInvocation(current_tokens, "doas", wrapper_index)
            if index >= len(current_tokens):
                return _CommandInvocation(current_tokens, None, None, False)
            continue

        if name == "ionice":
            process_mode = False
            options_with_value = {"-c", "--class", "-n", "--classdata"}
            while index < len(current_tokens) and current_tokens[index].startswith("-"):
                argument = current_tokens[index]
                if argument == "--":
                    index += 1
                    break
                option = argument.split("=", 1)[0]
                if option in {"-p", "--pid", "-P", "--pgid", "-u", "--uid"}:
                    process_mode = True
                    index += 1
                    if "=" not in argument and index < len(current_tokens):
                        index += 1
                    continue
                if option in {"-t", "--ignore"}:
                    index += 1
                    continue
                if option not in options_with_value:
                    return _CommandInvocation(current_tokens, None, None, False)
                index += 1
                if "=" not in argument:
                    if index >= len(current_tokens):
                        return _CommandInvocation(current_tokens, None, None, False)
                    index += 1
            if process_mode:
                return _CommandInvocation(current_tokens, "ionice", wrapper_index)
            if index >= len(current_tokens):
                return _CommandInvocation(current_tokens, None, None, False)
            continue

        if name == "nice":
            while index < len(current_tokens) and current_tokens[index].startswith("-"):
                argument = current_tokens[index]
                if argument == "--":
                    index += 1
                    break
                if re.fullmatch(r"-\d+", argument):
                    index += 1
                    continue
                option = argument.split("=", 1)[0]
                if option not in {"-n", "--adjustment"}:
                    return _CommandInvocation(current_tokens, None, None, False)
                index += 1
                if "=" not in argument:
                    if index >= len(current_tokens):
                        return _CommandInvocation(current_tokens, None, None, False)
                    index += 1
            if index >= len(current_tokens):
                return _CommandInvocation(current_tokens, None, None, False)
            continue

        if name == "setsid":
            while index < len(current_tokens) and current_tokens[index].startswith("-"):
                argument = current_tokens[index]
                if argument == "--":
                    index += 1
                    break
                if argument not in {"-c", "--ctty", "-f", "--fork", "-w", "--wait"}:
                    return _CommandInvocation(current_tokens, None, None, False)
                index += 1
            if index >= len(current_tokens):
                return _CommandInvocation(current_tokens, None, None, False)
            continue

        if name == "stdbuf":
            while index < len(current_tokens) and current_tokens[index].startswith("-"):
                argument = current_tokens[index]
                if argument == "--":
                    index += 1
                    break
                option = argument.split("=", 1)[0]
                if option in {"--input", "--output", "--error"}:
                    index += 1
                    if "=" not in argument:
                        if index >= len(current_tokens):
                            return _CommandInvocation(current_tokens, None, None, False)
                        index += 1
                    continue
                if re.fullmatch(r"-[ioe].+", argument):
                    index += 1
                    continue
                if argument in {"-i", "-o", "-e"}:
                    if index + 1 >= len(current_tokens):
                        return _CommandInvocation(current_tokens, None, None, False)
                    index += 2
                    continue
                return _CommandInvocation(current_tokens, None, None, False)
            if index >= len(current_tokens):
                return _CommandInvocation(current_tokens, None, None, False)
            continue

        if name == "taskset":
            pid_mode = False
            while index < len(current_tokens) and current_tokens[index].startswith("-"):
                argument = current_tokens[index]
                if argument == "--":
                    index += 1
                    break
                if argument.startswith("--"):
                    if argument not in {"--all-tasks", "--cpu-list", "--pid"}:
                        return _CommandInvocation(current_tokens, None, None, False)
                    pid_mode = pid_mode or argument == "--pid"
                else:
                    flags = argument[1:]
                    if not flags or any(flag not in "acp" for flag in flags):
                        return _CommandInvocation(current_tokens, None, None, False)
                    pid_mode = pid_mode or "p" in flags
                index += 1
            if pid_mode:
                return _CommandInvocation(current_tokens, "taskset", wrapper_index)
            if index + 1 >= len(current_tokens):
                return _CommandInvocation(current_tokens, None, None, False)
            index += 1  # CPU mask or list
            continue

        if name == "time":
            while index < len(current_tokens) and current_tokens[index].startswith("-"):
                argument = current_tokens[index]
                if argument == "--":
                    index += 1
                    break
                option = argument.split("=", 1)[0]
                if option not in time_options_with_value and option not in time_options_without_value:
                    return _CommandInvocation(current_tokens, None, None, False)
                index += 1
                if (
                    option in time_options_with_value
                    and "=" not in argument
                    and index < len(current_tokens)
                ):
                    index += 1
            if index >= len(current_tokens):
                return _CommandInvocation(current_tokens, None, None, False)
            continue

        if name == "timeout":
            while index < len(current_tokens) and current_tokens[index].startswith("-"):
                argument = current_tokens[index]
                if argument == "--":
                    index += 1
                    break
                option = argument.split("=", 1)[0]
                index += 1
                if (
                    option in timeout_options_with_value
                    and "=" not in argument
                    and index < len(current_tokens)
                ):
                    index += 1
            if index >= len(current_tokens):
                return _CommandInvocation(current_tokens, "timeout", wrapper_index)
            index += 1  # duration
            continue

        if name == "xargs":
            options_with_value = {
                "-a", "--arg-file", "-d", "--delimiter", "-E", "--eof",
                "-I", "--replace", "-L", "--max-lines", "-n", "--max-args",
                "-P", "--max-procs", "-s", "--max-chars",
            }
            options_without_value = {
                "-0", "--null", "-o", "--open-tty", "-p", "--interactive",
                "-r", "--no-run-if-empty", "-t", "--verbose", "-x", "--exit",
            }
            while index < len(current_tokens) and current_tokens[index].startswith("-"):
                argument = current_tokens[index]
                if argument == "--":
                    index += 1
                    break
                option = argument.split("=", 1)[0]
                if option not in options_with_value and option not in options_without_value:
                    return _CommandInvocation(current_tokens, None, None, False)
                index += 1
                if option in options_with_value and "=" not in argument:
                    if index >= len(current_tokens):
                        return _CommandInvocation(current_tokens, None, None, False)
                    index += 1
            if index >= len(current_tokens):
                return _CommandInvocation(current_tokens, "xargs", wrapper_index)
            continue

    return _CommandInvocation(current_tokens, None, None)


def _shell_command_name(tokens: Sequence[str]) -> str | None:
    invocation = _command_invocation(tokens)
    if not invocation.complete:
        return None
    if invocation.executable == "eval" and invocation.executable_index is not None:
        payload = _decode_shell_literal_operators(
            " ".join(invocation.tokens[invocation.executable_index + 1 :])
        )
        payload_tokens, complete = _tokenize_shell_line(payload)
        if not complete or not payload_tokens:
            return None
        nested = _command_invocation(payload_tokens, 1)
        return nested.executable if nested.complete else None
    return invocation.executable


def _normalized_executable_name(value: str) -> str:
    stripped = value.strip("(){}[]").lstrip("@+-")
    path_name = stripped.replace("\\", "/").rsplit("/", 1)[-1].lower()
    path_name = path_name[:-4] if path_name.endswith(".exe") else path_name
    shell_name = stripped.replace("\\", "").lower()
    shell_name = shell_name[:-4] if shell_name.endswith(".exe") else shell_name
    security_relevant_names = {
        ".", "source", "ash", "bash", "builtin", "busybox", "chrt", "cmd", "command",
        "csh", "curl", "dash", "doas", "env", "eval", "exec", "ionice", "ksh", "mksh", "nice",
        "node", "nohup", "perl", "php", "powershell", "pwsh", "python", "python2",
        "python3", "ruby", "setsid", "sh", "stdbuf", "sudo", "taskset", "time",
        "timeout", "wget", "xargs", "zsh",
    }
    return shell_name if shell_name in security_relevant_names else path_name


def _pipeline_has_remote_shell(commands: Sequence[Sequence[str]]) -> bool:
    names = [_shell_command_name(command) for command in commands]
    fetchers = {"curl", "wget"}
    shells = _COMMAND_INTERPRETERS
    saw_fetcher = False
    for name in names:
        if name in fetchers:
            saw_fetcher = True
        elif saw_fetcher and name in shells:
            return True
    return False


def _pipeline_has_ambiguous_remote_shell(commands: Sequence[Sequence[str]]) -> bool:
    """Fail closed when an unknown launcher precedes a fetcher token."""

    names = [_shell_command_name(command) for command in commands]
    shells = _COMMAND_INTERPRETERS
    non_launching_data_commands = {
        "cat", "command", "echo", "grep", "head", "printf", "tail", "tee", "wc"
    }
    shell_after = [False] * len(commands)
    ambiguous_launcher_after = [False] * len(commands)
    saw_shell = False
    saw_ambiguous_launcher = False
    for index in range(len(commands) - 1, -1, -1):
        shell_after[index] = saw_shell
        ambiguous_launcher_after[index] = saw_ambiguous_launcher
        name = names[index]
        saw_shell = saw_shell or name in shells
        if name not in shells and name not in non_launching_data_commands and any(
            _normalized_executable_name(token) in shells for token in commands[index]
        ):
            saw_ambiguous_launcher = True

    for index, command in enumerate(commands):
        name = names[index]
        if name in {"curl", "wget"}:
            if ambiguous_launcher_after[index]:
                return True
            continue
        if name in non_launching_data_commands:
            continue
        if not any(
            _normalized_executable_name(token) in {"curl", "wget"}
            for token in command
        ):
            continue
        if shell_after[index]:
            return True
    return False


def _compound_group_before_pipe(
    tokens: Sequence[str], pipe_index: int, max_steps: int
) -> tuple[tuple[str, ...] | None, int, bool]:
    """Return a syntactic compound command whose aggregate output reaches a pipe."""

    if pipe_index <= 0:
        return None, 0, True
    steps = 0
    closing_index = pipe_index - 1
    while closing_index >= 0:
        redirection_index: int | None = None
        redirection = tokens[closing_index]
        if _SHELL_REDIRECTION_RE.fullmatch(redirection) is not None:
            redirection_index = closing_index
        elif (
            closing_index > 0
            and _SHELL_REDIRECTION_RE.fullmatch(tokens[closing_index - 1]) is not None
        ):
            redirection_index = closing_index - 1
            redirection = tokens[redirection_index]
        if redirection_index is None:
            break
        steps += closing_index - redirection_index + 1
        if steps > max_steps:
            return None, steps, False
        descriptor_match = re.match(r"(?:([0-9]+|\{[A-Za-z_][A-Za-z0-9_]*\}))?", redirection)
        descriptor = descriptor_match.group(1) if descriptor_match is not None else None
        operator = redirection[len(descriptor or "") :]
        if operator.startswith((">", "&>")) and descriptor in {None, "1"}:
            return None, steps, False
        closing_index = redirection_index - 1
    if closing_index < 0:
        return None, steps, True
    closing = tokens[closing_index]
    if closing == "}" or closing.endswith(")"):
        opening = "{" if closing == "}" else "("
        depth = 1 if closing == "}" else len(closing) - len(closing.rstrip(")"))
        start: int | None = None
        for index in range(closing_index - 1, -1, -1):
            steps += 1
            if steps > max_steps:
                return None, steps, False
            candidate = tokens[index]
            if opening == "{" and candidate == "}":
                depth += 1
            elif opening == "{" and candidate == "{":
                depth -= 1
            elif opening == "(":
                depth += len(candidate) - len(candidate.rstrip(")"))
                depth -= len(candidate) - len(candidate.lstrip("("))
            if depth == 0:
                start = index
                break
    elif closing in {"fi", "done", "esac"}:
        opening_words = {
            "fi": {"if"},
            "done": {"for", "select", "until", "while"},
            "esac": {"case"},
        }[closing]
        depth = 1
        start = None
        for index in range(closing_index - 1, -1, -1):
            steps += 1
            if steps > max_steps:
                return None, steps, False
            if tokens[index] == closing:
                depth += 1
            elif tokens[index] in opening_words:
                depth -= 1
                if depth == 0:
                    start = index
                    break
    else:
        return None, 0, True
    if start is None:
        return None, steps, True
    if start and not (
        tokens[start - 1] == "!"
        or (
            tokens[start - 1]
            and all(character in "|;&" for character in tokens[start - 1])
        )
    ):
        return None, steps, True
    return tuple(tokens[start : closing_index + 1]), steps, True


def _tokens_have_compound_remote_pipeline(tokens: Sequence[str]) -> tuple[bool, bool]:
    """Classify fetchers inside compound commands piped into interpreters."""

    fetchers = {"curl", "wget"}
    non_launching_data_commands = {
        "cat", "command", "echo", "grep", "head", "printf", "tail", "tee", "wc"
    }
    remaining_work = max(4_096, len(tokens) * 4)
    for pipe_index, token in enumerate(tokens):
        if token not in {"|", "|&"}:
            continue
        downstream: list[str] = []
        cursor = pipe_index + 1
        while cursor < len(tokens):
            candidate = tokens[cursor]
            if candidate and all(character in "|;&" for character in candidate):
                break
            downstream.append(candidate)
            cursor += 1
        downstream_name = _shell_command_name(downstream)
        if downstream_name in non_launching_data_commands:
            continue
        downstream_has_interpreter = any(
            _normalized_executable_name(candidate) in _COMMAND_INTERPRETERS
            for candidate in downstream
        )
        if downstream_name not in _COMMAND_INTERPRETERS and not downstream_has_interpreter:
            continue
        group, consumed, complete = _compound_group_before_pipe(
            tokens, pipe_index, remaining_work
        )
        remaining_work = max(0, remaining_work - consumed)
        if not complete:
            return False, True
        if group is None:
            continue
        group_commands = _simple_shell_commands(group)
        names = [_shell_command_name(command) for command in group_commands]
        if any(name in fetchers for name in names):
            if downstream_name in _COMMAND_INTERPRETERS:
                return True, False
            return False, True
        for command, name in zip(group_commands, names):
            if name in non_launching_data_commands:
                continue
            if any(_normalized_executable_name(part) in fetchers for part in command):
                return False, True
    return False, False


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


def _tokens_have_ambiguous_remote_pipeline(tokens: Sequence[str]) -> bool:
    pipeline: list[list[str]] = []
    command: list[str] = []

    def finish_pipeline() -> bool:
        nonlocal pipeline, command
        if command:
            pipeline.append(command)
        found = len(pipeline) > 1 and _pipeline_has_ambiguous_remote_shell(pipeline)
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


def _simple_shell_commands(tokens: Sequence[str]) -> list[list[str]]:
    commands: list[list[str]] = []
    command: list[str] = []
    for token in tokens:
        if token and all(character in "|;&" for character in token):
            if command:
                commands.append(command)
            command = []
        else:
            command.append(token)
    if command:
        commands.append(command)
    return commands


def _shell_command_payloads(tokens: Sequence[str]) -> tuple[list[str], bool]:
    shells = {"ash", "bash", "csh", "dash", "ksh", "mksh", "sh", "zsh"}
    interpreter_options = {
        "python": {"-c"}, "python2": {"-c"}, "python3": {"-c"},
        "node": {"-e", "--eval"}, "perl": {"-e"}, "ruby": {"-e"},
        "php": {"-r"}, "powershell": {"-c", "-command"},
        "pwsh": {"-c", "-command"},
    }
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
        invocation = _command_invocation(command)
        if not invocation.complete:
            return payloads, False
        executable = invocation.executable
        executable_index = invocation.executable_index
        invocation_arguments = invocation.tokens
        if executable_index is None:
            continue

        if executable == "cmd":
            for index in range(executable_index + 1, len(invocation_arguments) - 1):
                if invocation_arguments[index].lower() in {"/c", "/k"}:
                    payloads.append(
                        _decode_shell_literal_operators(
                            " ".join(invocation_arguments[index + 1 :])
                        )
                    )
                    break
            continue

        if executable == "eval":
            if executable_index + 1 < len(invocation_arguments):
                payloads.append(
                    _decode_shell_literal_operators(
                        " ".join(invocation_arguments[executable_index + 1 :])
                    )
                )
            continue

        if executable in interpreter_options:
            accepted = interpreter_options[executable]
            for index in range(executable_index + 1, len(invocation_arguments) - 1):
                if invocation_arguments[index].lower() in accepted:
                    payloads.append(
                        _decode_shell_literal_operators(invocation_arguments[index + 1])
                    )
                    break
            continue

        if executable not in shells:
            continue
        index = executable_index + 1
        while index < len(invocation_arguments):
            option = invocation_arguments[index]
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
                if (
                    payload_index < len(invocation_arguments)
                    and invocation_arguments[payload_index] == "--"
                ):
                    payload_index += 1
                if payload_index < len(invocation_arguments):
                    payloads.append(
                        _decode_shell_literal_operators(invocation_arguments[payload_index])
                    )
                break
            option_name = option.split("=", 1)[0]
            if option_name in shell_options_with_value and "=" not in option:
                index += 2
                continue
            index += 1
    return payloads, True


def _command_substitution_payloads(
    command: str,
) -> tuple[list[tuple[str, str]], bool]:
    """Extract typed command/process substitutions without evaluating them."""

    payloads: list[tuple[str, str]] = []
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
                        if is_command_substitution:
                            kind = "command"
                        elif character == "<":
                            kind = "process-input"
                        else:
                            kind = "process-output"
                        payloads.append((kind, command[start:cursor]))
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
                    payloads.append(("command", command[index + 1 : cursor]))
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
    ansi_c_quote = False
    escaped = False
    index = 0

    def finish_token() -> None:
        if current:
            tokens.append("".join(current))
            current.clear()

    def append_literal(character: str) -> None:
        current.append(_SHELL_LITERAL_OPERATOR_CODES.get(character, character))

    while index < len(command):
        character = command[index]
        if escaped:
            append_literal(character)
            escaped = False
            index += 1
            continue
        if quote_character is not None:
            if character == quote_character:
                quote_character = None
                ansi_c_quote = False
            elif ansi_c_quote and character == "\\" and index + 1 < len(command):
                escape = command[index + 1]
                simple_escapes = {
                    "a": "\a", "b": "\b", "e": "\x1b", "f": "\f", "n": "\n",
                    "r": "\r", "t": "\t", "v": "\v", "\\": "\\", "'": "'", '"': '"',
                }
                if escape in simple_escapes:
                    append_literal(simple_escapes[escape])
                    index += 2
                    continue
                widths = {"x": 2, "u": 4, "U": 8}
                width = widths.get(escape)
                if width is not None:
                    digits = command[index + 2 : index + 2 + width]
                    if len(digits) == width and all(value in "0123456789abcdefABCDEF" for value in digits):
                        try:
                            append_literal(chr(int(digits, 16)))
                        except ValueError:
                            pass
                        index += 2 + width
                        continue
                if escape in "01234567":
                    end = index + 2
                    while end < min(len(command), index + 5) and command[end] in "01234567":
                        end += 1
                    append_literal(chr(int(command[index + 1 : end], 8)))
                    index = end
                    continue
                current.extend(("\\", escape))
                index += 2
                continue
            elif character == "\\" and quote_character == '"':
                if (
                    index + 1 < len(command)
                    and command[index + 1] in '$`"\\\n'
                ):
                    escaped = True
                else:
                    current.append(character)
            else:
                append_literal(character)
            index += 1
            continue
        if character in {'"', "'"}:
            is_dollar_quote = bool(current and current[-1] == "$")
            if is_dollar_quote:
                current.pop()
            ansi_c_quote = is_dollar_quote and character == "'"
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
            descriptor_prefix = ""
            current_value = "".join(current)
            if re.fullmatch(r"(?:[0-9]+|\{[A-Za-z_][A-Za-z0-9_]*\})", current_value):
                descriptor_prefix = current_value
                current.clear()
            else:
                finish_token()
            end = index + 1
            if character == "&":
                end += 1
                if end < len(command) and command[end] == ">":
                    end += 1
            else:
                while end < len(command) and command[end] == character:
                    end += 1
                if character == "<" and end < len(command) and command[end] == ">":
                    end += 1
                elif character == ">" and end < len(command) and command[end] == "|":
                    end += 1
                if (
                    character == "<"
                    and end - index == 2
                    and end < len(command)
                    and command[end] == "-"
                ):
                    end += 1
                elif end < len(command) and command[end] == "&":
                    end += 1
                    while end < len(command) and (command[end].isdigit() or command[end] == "-"):
                        end += 1
            tokens.append(descriptor_prefix + command[index:end])
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


def _has_remote_execution_syntax(command: str) -> bool:
    return (
        "|" in command
        or any(marker in command for marker in ("$(", "<(", ">(", "`"))
        or _SHELL_ENCODED_PIPE_RE.search(command) is not None
    )


def _has_remote_fetcher_hint(command: str) -> bool:
    return (
        _REMOTE_FETCHER_RE.search(command) is not None
        or _REMOTE_FETCHER_OBFUSCATED_RE.search(command) is not None
    )


def _generated_shell_output_status(
    tokens: Sequence[str],
    depth: int,
) -> tuple[bool, bool]:
    invocation = _command_invocation(tokens)
    if (
        not invocation.complete
        or invocation.executable not in {"echo", "printf"}
        or invocation.executable_index is None
    ):
        return False, False
    arguments = [
        _decode_shell_literal_operators(argument)
        for argument in invocation.tokens[invocation.executable_index + 1 :]
    ]
    for generated_payload in (*arguments, " ".join(arguments)):
        detected, unparsed = _remote_pipeline_status(
            generated_payload,
            depth + 1,
            True,
        )
        if detected or unparsed:
            return detected, unparsed
    return False, False


def _remote_pipeline_status(
    command: str,
    depth: int = 0,
    shell_payload: bool = False,
) -> tuple[bool, bool]:
    """Return (detected, unparsed) for a bounded shell-like command string."""

    contexts = _contextual_shell_commands(command)
    normalized_input = command.strip()
    if contexts != [normalized_input]:
        for context in contexts:
            detected, unparsed = _remote_pipeline_status(context, depth, shell_payload)
            if detected or unparsed:
                return detected, unparsed
        return False, False
    command = normalized_input
    if not _has_remote_execution_syntax(command) or not _has_remote_fetcher_hint(command):
        return False, False
    if re.search(r"\^[\^|&<>]", command):
        # Caret escaping changes meaning between POSIX shells and cmd.exe. The
        # path-agnostic scanner cannot safely choose one grammar.
        return False, True
    if depth > 4:
        return False, True
    tokens, complete = _tokenize_shell_line(command)
    if not complete:
        return False, True
    if len(tokens) > MAX_SHELL_CLASSIFICATION_TOKENS:
        return False, True
    if tokens and tokens[-1] in {"|", "|&", "||"}:
        return False, True
    compound_detected, compound_unparsed = _tokens_have_compound_remote_pipeline(tokens)
    if compound_detected or compound_unparsed:
        return compound_detected, compound_unparsed
    if _tokens_have_remote_pipeline(tokens):
        return True, False
    if _tokens_have_ambiguous_remote_pipeline(tokens):
        return False, True

    simple_commands = _simple_shell_commands(tokens)
    simple_names = [_shell_command_name(item) for item in simple_commands]
    interpreter_names = _COMMAND_INTERPRETERS
    interpreter_after = [False] * len(simple_names)
    saw_interpreter = False
    for index in range(len(simple_names) - 1, -1, -1):
        interpreter_after[index] = saw_interpreter
        saw_interpreter = saw_interpreter or simple_names[index] in interpreter_names
    for command_index, simple_command in enumerate(simple_commands):
        invocation = _command_invocation(simple_command)
        if (
            not invocation.complete
            or invocation.executable not in {"echo", "printf"}
            or invocation.executable_index is None
            or not interpreter_after[command_index]
        ):
            continue
        detected, unparsed = _generated_shell_output_status(simple_command, depth)
        if detected or unparsed:
            return detected, unparsed

    for simple_command, simple_name in zip(simple_commands, simple_names):
        if simple_name not in interpreter_names:
            continue
        for token_index, token in enumerate(simple_command[:-1]):
            if _SHELL_REDIRECTION_RE.fullmatch(token) is None or not token.endswith("<<<"):
                continue
            detected, unparsed = _remote_pipeline_status(
                _decode_shell_literal_operators(simple_command[token_index + 1]),
                depth + 1,
                True,
            )
            if detected or unparsed:
                return detected, unparsed

    nested_payloads, payloads_complete = _shell_command_payloads(tokens)
    if not payloads_complete:
        return False, True
    substitutions, substitutions_complete = _command_substitution_payloads(command)
    if not substitutions_complete:
        return False, True

    outer_names = [_shell_command_name(item) for item in simple_commands]
    outer_has_fetcher = any(name in {"curl", "wget"} for name in outer_names)
    outer_has_shell = any(
        name in interpreter_names
        for name in outer_names
    )
    for kind, payload in substitutions:
        payload_tokens, substitution_complete = _tokenize_shell_line(payload)
        if not substitution_complete:
            return False, True
        payload_name = _shell_command_name(payload_tokens) if payload_tokens else None
        if outer_has_fetcher and kind == "process-output" and payload_name in interpreter_names:
            return True, False
        if outer_has_shell and kind == "process-input" and payload_name in {"curl", "wget"}:
            return True, False
        substitution_becomes_code = kind == "command" and (
            shell_payload or (outer_has_shell and "<<<" in command)
        )
        if substitution_becomes_code:
            if payload_name in {"curl", "wget"}:
                return True, False
            detected, unparsed = _generated_shell_output_status(payload_tokens, depth)
            if detected or unparsed:
                return detected, unparsed

    for payload in nested_payloads:
        detected, unparsed = _remote_pipeline_status(payload, depth + 1, True)
        if detected or unparsed:
            return detected, unparsed
    for _kind, payload in substitutions:
        detected, unparsed = _remote_pipeline_status(payload, depth + 1, False)
        if detected or unparsed:
            return detected, unparsed
    return False, False


def _remote_pipe_line_numbers(text: str) -> tuple[list[int], list[int]]:
    if not _has_remote_execution_syntax(text) or not _has_remote_fetcher_hint(text):
        return [], []
    findings: list[int] = []
    unparsed: list[int] = []
    for command_source in (
        _logical_shell_commands(text),
        _yaml_folded_shell_commands(text),
    ):
        for start_line, logical_command, shell_payload in command_source:
            detected, could_not_parse = _remote_pipeline_status(
                logical_command,
                shell_payload=shell_payload,
            )
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


def _firebase_quoted_positions(text: str) -> bytearray:
    """Mark quoted contents while leaving an opening JSON key quote structural."""

    quoted = bytearray(len(text))
    quote_character: str | None = None
    escaped = False
    for index, character in enumerate(text):
        if quote_character is not None:
            quoted[index] = 1
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote_character:
                quote_character = None
            continue
        if character in {'"', "'"}:
            quote_character = character
    return quoted


def _firebase_or_true_offsets(text: str) -> Iterable[int]:
    """Find true literal operands adjacent to OR in one bounded regex pass."""

    for match in _FIREBASE_TRUE_OPERAND_RE.finditer(text):
        expression = match.group("expression")
        if not _firebase_literal_equality_is_true(expression):
            continue
        before_expression = match.start()
        while before_expression and text[before_expression - 1].isspace():
            before_expression -= 1
        after_expression = match.end()
        while after_expression < len(text) and text[after_expression].isspace():
            after_expression += 1
        if (
            text[max(0, before_expression - 2) : before_expression] in {"==", "!="}
            or text[after_expression : after_expression + 2] in {"==", "!="}
        ):
            continue
        left = match.start()
        while left and (text[left - 1].isspace() or text[left - 1] == "("):
            left -= 1
        right = match.end()
        while right < len(text) and (text[right].isspace() or text[right] == ")"):
            right += 1
        if text[max(0, left - 2) : left] == "||" or text[right : right + 2] == "||":
            yield match.start()


def _firebase_literal_equality_is_true(expression: str) -> bool:
    match = _FIREBASE_LITERAL_EQUALITY_RE.search(expression)
    if match is None:
        return True
    left = match.group("left")
    right = match.group("right")
    if left.lower() == "null" or right.lower() == "null":
        return left.lower() == right.lower() == "null"
    if left[:1] in {'"', "'"} or right[:1] in {'"', "'"}:
        if left == right:
            return True
        if "\\" not in left and "\\" not in right:
            return left[1:-1] == right[1:-1]
        return False
    try:
        return Decimal(left) == Decimal(right)
    except InvalidOperation:
        return False


def _firebase_rtd_key_at(
    text: str,
    index: int,
    quoted_positions: Sequence[int],
) -> bool:
    """Recognize a structural RTDB .read/.write key, not text inside a value."""

    if index >= len(text) or (index < len(quoted_positions) and quoted_positions[index]):
        return False
    cursor = index
    quote = ""
    if text[cursor] in {'"', "'"}:
        quote = text[cursor]
        cursor += 1
    key = next(
        (candidate for candidate in (".read", ".write") if text.startswith(candidate, cursor)),
        None,
    )
    if key is None:
        return False
    cursor += len(key)
    if quote:
        if cursor >= len(text) or text[cursor] != quote:
            return False
        cursor += 1
    elif cursor < len(text) and (text[cursor].isalnum() or text[cursor] in "_."):
        return False
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor < len(text) and text[cursor] == ":"


def _firebase_contextual_or_true_offsets(
    text: str,
    quoted_positions: Sequence[int],
) -> Iterable[tuple[int, bool]]:
    """Classify OR-true offsets with one forward context pass."""

    offsets = iter(_firebase_or_true_offsets(text))
    next_offset = next(offsets, None)
    if next_offset is None:
        return
    lowered = text.lower()
    statement_has_allow = False
    statement_has_if = False
    rtd_has_key = False
    rtd_has_colon = False
    for index, character in enumerate(lowered):
        is_quoted = index < len(quoted_positions) and bool(quoted_positions[index])
        if character == ";" and not is_quoted:
            statement_has_allow = False
            statement_has_if = False
            rtd_has_key = False
            rtd_has_colon = False
        elif character == "," and not is_quoted:
            rtd_has_key = False
            rtd_has_colon = False
        if lowered.startswith("allow ", index):
            statement_has_allow = True
        if character == ":":
            condition = index + 1
            while condition < len(lowered) and lowered[condition].isspace():
                condition += 1
            if lowered.startswith("if", condition) and (
                condition + 2 >= len(lowered)
                or not (
                    lowered[condition + 2].isalnum()
                    or lowered[condition + 2] == "_"
                )
            ):
                statement_has_if = True
        if _firebase_rtd_key_at(lowered, index, quoted_positions):
            rtd_has_key = True
            rtd_has_colon = True
        while next_offset is not None and index == next_offset:
            is_allow = statement_has_allow and statement_has_if
            is_rtd = rtd_has_key and rtd_has_colon
            if is_allow or is_rtd:
                yield next_offset, is_rtd
            next_offset = next(offsets, None)
        if next_offset is None:
            return


def _sql_code_view(text: str) -> str:
    """Blank SQL comments and literal bodies while preserving offsets and lines."""

    output = list(text)
    index = 0
    block_depth = 0
    while index < len(text):
        if block_depth:
            if text.startswith("/*", index):
                output[index] = output[index + 1] = " "
                block_depth += 1
                index += 2
            elif text.startswith("*/", index):
                output[index] = output[index + 1] = " "
                block_depth -= 1
                index += 2
            else:
                if text[index] not in "\r\n":
                    output[index] = " "
                index += 1
            continue
        if text.startswith("--", index):
            while index < len(text) and text[index] not in "\r\n":
                output[index] = " "
                index += 1
            continue
        if text.startswith("/*", index):
            output[index] = output[index + 1] = " "
            block_depth = 1
            index += 2
            continue
        character = text[index]
        if character == "'":
            output[index] = " "
            index += 1
            while index < len(text):
                if text[index] not in "\r\n":
                    output[index] = " "
                if text[index] == "'":
                    if index + 1 < len(text) and text[index + 1] == "'":
                        output[index + 1] = " "
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            continue
        if character == '"':
            index += 1
            while index < len(text):
                if text[index] == '"':
                    if index + 1 < len(text) and text[index + 1] == '"':
                        output[index] = output[index + 1] = "x"
                        index += 2
                        continue
                    index += 1
                    break
                if text[index] not in "\r\n":
                    output[index] = "x"
                index += 1
            continue
        if character == "$":
            delimiter_end = index + 1
            while delimiter_end < len(text) and (
                text[delimiter_end].isalnum() or text[delimiter_end] == "_"
            ):
                delimiter_end += 1
            if delimiter_end < len(text) and text[delimiter_end] == "$" and (
                delimiter_end == index + 1
                or text[index + 1].isalpha()
                or text[index + 1] == "_"
            ):
                delimiter = text[index : delimiter_end + 1]
                close = text.find(delimiter, delimiter_end + 1)
                literal_end = len(text) if close < 0 else close + len(delimiter)
                for position in range(index, literal_end):
                    if text[position] not in "\r\n":
                        output[position] = " "
                index = literal_end
                continue
        index += 1
    return "".join(output)


def _scan_text(
    candidate: Candidate,
    text: str,
    findings: list[Finding],
    max_findings: int = DEFAULT_MAX_FINDINGS,
) -> dict[str, object] | None:
    lines = text.splitlines()
    seen: set[tuple[str, int]] = set()

    def add(rule_id: str, line_number: int) -> None:
        key = (rule_id, line_number)
        if key not in seen:
            if len(findings) >= max_findings:
                raise FindingLimitExceeded
            findings.append(
                Finding(
                    rule_id,
                    candidate.display_path,
                    max(1, line_number),
                    source_id=candidate.source_id,
                )
            )
            seen.add(key)

    firebase_rule_file = _is_firebase_rules_path(candidate.display_path)
    workflow_file = _is_workflow_path(candidate.scope_path or candidate.display_path)
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

        for _name, value in _generic_assignments(
            line, code_context=_is_code_assignment_path(candidate.path)
        ):
            if not _placeholder(value) and not _is_known_specialized_value(value):
                add("VW-SECRET-GENERIC-ASSIGNMENT", line_number)

        if workflow_file:
            for action_match in _ACTION_USES_RE.finditer(line):
                if not _action_is_pinned(action_match.group("reference")):
                    add("VW-AUTOMATION-UNPINNED", line_number)
            for image_match in _WORKFLOW_IMAGE_RE.finditer(line):
                if not _container_is_pinned(image_match.group("reference")):
                    add("VW-AUTOMATION-UNPINNED", line_number)

        if re.search(r"[\"']type[\"']\s*:\s*[\"']service_account[\"']", line):
            service_account_type_line = line_number
        if re.search(r"[\"']private_key[\"']\s*:", line) and not re.search(
            r"(?i)(?:placeholder|example|replace|dummy|fake|\$\{|\{\{)", line
        ):
            service_account_private_line = line_number

    if service_account_type_line is not None and service_account_private_line is not None:
        add("VW-FIREBASE-SERVICE-ACCOUNT", service_account_private_line)

    for line_number, value in _backtick_assignments(text):
        if not _is_known_specialized_value(value):
            add("VW-SECRET-GENERIC-ASSIGNMENT", line_number)

    remote_lines, unparsed_shell_lines = _remote_pipe_line_numbers(text)
    for line_number in remote_lines:
        add("VW-REMOTE-INSTALL-SCRIPT", line_number)
    for line_number in unparsed_shell_lines:
        add("VW-SHELL-PIPELINE-UNPARSED", line_number)

    if firebase_rule_file:
        normalized_rules, normalized_line_numbers = _normalized_firebase_rules(text)
        quoted_positions = _firebase_quoted_positions(normalized_rules)
        for pattern in (_FIREBASE_RTD_RULE_RE, _FIREBASE_ALLOW_RE):
            for match in pattern.finditer(normalized_rules):
                if match.start() < len(quoted_positions) and quoted_positions[match.start()]:
                    continue
                if pattern is _FIREBASE_RTD_RULE_RE and normalized_rules[match.start()] in {'"', "'"}:
                    opening_quote = normalized_rules[match.start()]
                    key_start = match.start() + 1
                    key = next(
                        (
                            candidate_key
                            for candidate_key in (".read", ".write")
                            if normalized_rules.startswith(candidate_key, key_start)
                        ),
                        None,
                    )
                    if (
                        key is None
                        or key_start + len(key) >= len(normalized_rules)
                        or normalized_rules[key_start + len(key)] != opening_quote
                    ):
                        continue
                if not _firebase_literal_equality_is_true(match.group(0)):
                    continue
                line_number = (
                    normalized_line_numbers[match.start()]
                    if match.start() < len(normalized_line_numbers)
                    else 1
                )
                add("VW-FIREBASE-PERMISSIVE-RULE", line_number)
        for start, is_rtd_condition in _firebase_contextual_or_true_offsets(
            normalized_rules,
            quoted_positions,
        ):
            if quoted_positions[start] and not is_rtd_condition:
                continue
            line_number = normalized_line_numbers[start] if start < len(normalized_line_numbers) else 1
            add("VW-FIREBASE-PERMISSIVE-RULE", line_number)

    if candidate.path.suffix.lower() == ".sql":
        sql_code = _sql_code_view(text)
        previous_match_start = 0
        sql_line_number = 1
        for match in _SUPABASE_RLS_DISABLED_RE.finditer(sql_code):
            sql_line_number += sql_code.count("\n", previous_match_start, match.start())
            previous_match_start = match.start()
            add("VW-SUPABASE-RLS-DISABLED", sql_line_number)

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
        lifecycle_hooks = {
            "preinstall",
            "install",
            "postinstall",
            "prepublish",
            "preprepare",
            "prepare",
            "postprepare",
        }
        script_names = {
            name
            for name, script in scripts.items()
            if isinstance(name, str) and isinstance(script, str)
        }
        script_line_numbers = _line_numbers_for_json_object_keys(
            text,
            "scripts",
            script_names,
        )
        for name, script in scripts.items():
            if isinstance(name, str) and isinstance(script, str):
                script_line = script_line_numbers.get(name, 1)
                if name in lifecycle_hooks:
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
            {
                part.lower()
                for part in Path(candidate.scope_path or candidate.display_path).parts[:-1]
            }
            & _SKIP_DIR_NAMES
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
        normalized = unicodedata.normalize("NFKD", value)
        return "".join(
            character
            for character in normalized.casefold().strip()
            if unicodedata.category(character)[:1] in {"L", "N"}
        )

    def normalized_required_value(value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value)
        return "".join(
            character
            for character in normalized
            if unicodedata.category(character) != "Cf"
        ).strip()

    if any(
        not normalized_required_value(metadata[key])
        or not any(
            unicodedata.category(character)[:1] in {"L", "N"}
            for character in normalized_required_value(metadata[key])
        )
        for key in required
    ):
        return False, None
    owner = normalized_identity(metadata["owner"])
    approver = normalized_identity(metadata["approved-by"])
    if not owner or not approver or owner == approver:
        return False, None
    try:
        expiry = dt.date.fromisoformat(normalized_required_value(metadata["expires"]))
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


def _hide_incomplete_issue_paths(report: Report) -> None:
    report.tool_errors = [
        issue
        if issue.path == "."
        else dataclasses.replace(issue, path="__vibeworthy_unavailable_path__")
        for issue in report.tool_errors
    ]


def scan_path(path: str | os.PathLike[str], max_file_bytes: int = DEFAULT_MAX_FILE_BYTES, max_files: int = DEFAULT_MAX_FILES) -> Report:
    report = Report()
    if max_files <= 0:
        report.tool_errors.append(
            ToolIssue(
                "tool.file-limit",
                "The candidate-file limit must be positive.",
            )
        )
        return report
    try:
        target = Path(path)
    except (TypeError, ValueError):
        report.tool_errors.append(ToolIssue("tool.target", "The requested target is invalid."))
        return report
    candidates, root_guard = _enumerate_candidates(target, max_files, report)
    if report.tool_errors or root_guard is None:
        return report
    scan_root = root_guard.resolved
    root_is_file = root_guard.root_is_file
    report.files_considered = len(candidates)
    if len(candidates) > max_files:
        report.tool_errors.append(ToolIssue("tool.file-limit", "The candidate-file limit was exceeded; no partial clean result was produced."))
        return report

    content_hashes: dict[bytes, bytes] = {}
    path_values: dict[str, str] = {}
    path_value_characters = 0
    aggregate_bytes = 0
    readable_source_ids: set[bytes] = set()
    for candidate in candidates:
        text = _read_candidate(
            candidate,
            root_guard,
            max_file_bytes,
            report,
            count_scan=False,
        )
        if text is None:
            if report.tool_errors:
                break
            continue
        encoded = text.encode("utf-8")
        aggregate_bytes += len(encoded)
        if aggregate_bytes > DEFAULT_MAX_TOTAL_BYTES:
            report.tool_errors.append(
                ToolIssue(
                    "tool.byte-limit",
                    "The aggregate input-byte limit was exceeded; no partial clean result was produced.",
                )
            )
            _hide_incomplete_issue_paths(report)
            return report
        readable_source_ids.add(candidate.source_id)
        content_hashes[candidate.source_id] = hashlib.sha256(encoded).digest()
        detected_values = _detected_assignment_values(
            text, code_context=_is_code_assignment_path(candidate.path)
        )
        for raw_value in detected_values:
            display_value = _safe_display_component(raw_value)
            if not display_value or display_value == "." or display_value in path_values:
                continue
            path_values[display_value] = raw_value
            path_value_characters += len(display_value)
        if (
            len(path_values) > MAX_PATH_REDACTION_VALUES
            or path_value_characters > MAX_PATH_REDACTION_PATTERN_CHARS
        ):
            report.tool_errors.append(
                ToolIssue(
                    "tool.path-redaction-limit",
                    "Path redaction exceeded its bounded value budget; no report locations were emitted.",
                )
            )
            _hide_incomplete_issue_paths(report)
            return report
    if report.tool_errors:
        _hide_incomplete_issue_paths(report)
        return report

    candidates = _redact_content_values_from_paths(candidates, path_values.values())
    for candidate in candidates:
        rule_id: str | None = None
        if _is_sensitive_env(candidate.path.name):
            if candidate.tracked is True:
                rule_id = "VW-ENV-TRACKED"
            elif candidate.tracked is False:
                rule_id = "VW-ENV-UNIGNORED"
        if rule_id is None:
            continue
        if len(report.findings) >= DEFAULT_MAX_FINDINGS:
            report.findings.clear()
            report.tool_errors.append(
                ToolIssue(
                    "tool.finding-limit",
                    "The finding limit was exceeded; no partial result was produced.",
                )
            )
            return report
        report.findings.append(
            Finding(
                rule_id,
                candidate.display_path,
                1,
                source_id=candidate.source_id,
            )
        )
    manifests: list[dict[str, object]] = []
    for candidate in candidates:
        if candidate.source_id not in readable_source_ids:
            continue
        text = _read_candidate(candidate, root_guard, max_file_bytes, report)
        if text is None:
            if not report.tool_errors:
                report.tool_errors.append(
                    ToolIssue(
                        "tool.file-race",
                        "A candidate became unavailable between scanner passes; no partial result was produced.",
                        candidate.display_path,
                    )
                )
            break
        encoded = text.encode("utf-8")
        if hashlib.sha256(encoded).digest() != content_hashes[candidate.source_id]:
            report.tool_errors.append(
                ToolIssue(
                    "tool.file-race",
                    "A candidate changed between scanner passes; no partial result was produced.",
                    candidate.display_path,
                )
            )
            break
        current_findings: list[Finding] = []
        try:
            manifest = _scan_text(
                candidate,
                text,
                current_findings,
                DEFAULT_MAX_FINDINGS - len(report.findings),
            )
        except FindingLimitExceeded:
            report.tool_errors.append(
                ToolIssue(
                    "tool.finding-limit",
                    "The finding limit was exceeded; no partial result was produced.",
                )
            )
            break
        _apply_suppressions(current_findings, {candidate.source_id: text})
        if len(report.findings) + len(current_findings) > DEFAULT_MAX_FINDINGS:
            report.tool_errors.append(
                ToolIssue(
                    "tool.finding-limit",
                    "The finding limit was exceeded; no partial result was produced.",
                )
            )
            break
        report.findings.extend(current_findings)
        if manifest is not None:
            manifests.append(manifest)

    if report.tool_errors:
        report.findings.clear()
        _hide_incomplete_issue_paths(report)
        return report
    if not _root_guard_current(root_guard):
        report.findings.clear()
        report.tool_errors.append(
            ToolIssue("tool.target-race", "The requested scan root changed before scanning completed.")
        )
        return report
    _add_dependency_findings(candidates, manifests, scan_root, root_is_file, report.findings)
    if len(report.findings) > DEFAULT_MAX_FINDINGS:
        report.findings.clear()
        report.tool_errors.append(
            ToolIssue(
                "tool.finding-limit",
                "The finding limit was exceeded; no partial result was produced.",
            )
        )
        return report
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
        "Consistency: non-atomic worktree view; run against a quiescent isolated checkout. Concurrent local writers can invalidate evidence.",
        "Safety: network not used; project files not modified; matched values are never reported.",
    ]
    if report.findings:
        lines.append("Findings:")
        for finding in report.findings:
            state = "[SUPPRESSED]" if finding.suppressed else ""
            lines.append(
                f"- [{finding.rule.severity.upper()}]{state} {finding.rule_id} {finding.path}:{finding.line} - {finding.rule.message}"
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
            lines.append(f"- [TOOL-ERROR] {issue.code} {issue.path} - {issue.message}")
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
    rendered = "\n".join(lines) + "\n"
    return rendered.encode("ascii", "backslashreplace").decode("ascii")


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
