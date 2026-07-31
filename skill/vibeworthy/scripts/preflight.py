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
from fractions import Fraction
import hashlib
import json
import os
import posixpath
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
from collections import Counter, defaultdict, deque
from typing import Iterable, Sequence
from urllib.parse import quote, urlsplit


TOOL_NAME = "vibeworthy-preflight"
TOOL_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"
DEFAULT_MAX_FILE_BYTES = 1_048_576
DEFAULT_MAX_FILES = 20_000
DEFAULT_MAX_TOTAL_BYTES = 67_108_864
DEFAULT_MAX_FINDINGS = 50_000
MAX_PATH_REDACTION_VALUES = 2_048
MAX_PATH_REDACTION_PATTERN_CHARS = 131_072
MAX_PERCENT_DECODE_ROUNDS = 4
MAX_PATH_TRANSFORM_CHARS = 16_777_216
MAX_SHELL_CLASSIFICATION_TOKENS = 32_768
MAX_SHELL_CLASSIFICATION_CHARS = MAX_SHELL_CLASSIFICATION_TOKENS * 16
MAX_REMOTE_SHELL_SYMBOLS = 256
MAX_HEREDOC_SPECS = 64
MAX_FIREBASE_LITERAL_LIST_ITEMS = 4_096
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
            "Execution of remotely fetched content",
            "A command appears to execute remotely retrieved content, either through a pipeline or after writing it to a local file.",
            "Do not execute it. Verify identity, source, digest or signature, permissions, and necessity through a reviewable download-and-inspect workflow.",
            "dependency-execution",
        ),
        _rule(
            "VW-SHELL-PIPELINE-UNPARSED",
            BLOCKER,
            "Relevant shell flow not safely classified",
            "A shell-like fetch-to-execution flow exceeded a safety bound, used unresolved dynamic or conditional state, or was malformed, so it was not safely classified.",
            "Inspect the bounded shell flow without executing it, split or repair the commands for review, and rerun the scanner; an unclassified relevant fetch-to-execution flow cannot produce a clean result.",
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


class PathRedactionLimitExceeded(Exception):
    """Path redaction stopped before report locations could be proven safe."""


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
_POSTGRES_IDENTIFIER = (
    r'(?:U&"(?:""|[^"])+"(?:\s+UESCAPE\s+ +)?|"(?:""|[^"])+"|'
    r'[A-Za-z_\x80-\U0010ffff][A-Za-z0-9_$\x80-\U0010ffff]*)'
)
_POSTGRES_ALTER_TABLE_RE = re.compile(
    r"\bALTER\s+TABLE(?:\s+IF\s+EXISTS)?\s+(?:ONLY\s+)?"
    + _POSTGRES_IDENTIFIER
    + r"(?:\s*\.\s*" + _POSTGRES_IDENTIFIER + r")?"
    r"(?:\s*\*)?(?=\s)",
    re.IGNORECASE,
)
_POSTGRES_DISABLE_RLS_ACTION_RE = re.compile(
    r"DISABLE\s+ROW\s+LEVEL\s+SECURITY\b",
    re.IGNORECASE,
)
_POSTGRES_COPY_STDIN_RE = re.compile(
    r"(?:\A|;)\s*COPY\b[^;]*?\bFROM\s+STDIN\s*;",
    re.IGNORECASE,
)
_POSTGRES_DO_BODY_PREFIX_RE = re.compile(
    r"\s*DO(?:\s+LANGUAGE\s+" + _POSTGRES_IDENTIFIER + r")?"
    r"\s*(?:E|U&|N)?\s*\Z",
    re.IGNORECASE,
)
_POSTGRES_CREATE_ROUTINE_PREFIX_RE = re.compile(
    r"\s*CREATE(?:\s+OR\s+REPLACE)?\s+(?:FUNCTION|PROCEDURE)\b",
    re.IGNORECASE,
)
_POSTGRES_AS_TAIL_RE = re.compile(
    r"\bAS\s*(?:E|U&|N)?\s*\Z",
    re.IGNORECASE,
)
_POSTGRES_DYNAMIC_EXECUTE_TAIL_RE = re.compile(
    r"\bEXECUTE\s*(?:E|U&|N)?\s*\Z",
    re.IGNORECASE,
)
_MAX_POSTGRES_EXECUTABLE_NESTING = 16
_POSTGRES_DISABLED_RLS_SENTINEL = "\0"
_FIREBASE_RTD_PREFIX_RE = re.compile(
    r"(?:\.(?:read|write)|"
    r'"(?:\\.|[^"\\\r\n]){1,256}"|'
    r"'(?:\\.|[^'\\\r\n]){1,256}') *: *",
    re.IGNORECASE,
)
_FIREBASE_ALLOW_PREFIX_RE = re.compile(
    r"\ballow +(?:read|write|create|update|delete|get|list)"
    r"(?: *, *(?:read|write|create|update|delete|get|list))*"
    r" *: *if *",
    re.IGNORECASE,
)
_FIREBASE_UNCONDITIONAL_ALLOW_RE = re.compile(
    r"\ballow +(?:read|write|create|update|delete|get|list)"
    r"(?: *, *(?:read|write|create|update|delete|get|list))* *;",
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
_NON_EXECUTING_DATA_COMMANDS = frozenset(
    {
        "cat", "command", "cut", "echo", "grep", "head", "jq", "printf",
        "sort", "tail", "tee", "tr", "uniq", "wc",
    }
)
_JSON_LINE_BREAKS = frozenset("\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029")
_SHELL_LITERAL_OPERATOR_CODES = {
    "|": "\0p", ";": "\0s", "&": "\0a", "<": "\0l", ">": "\0g"
}
_SHELL_LITERAL_EXPANSION_CODES = {"$": "\0d", "%": "\0m", "!": "\0e"}
_SHELL_LITERAL_EXPANSION_VALUES = {
    encoded: operator for operator, encoded in _SHELL_LITERAL_EXPANSION_CODES.items()
}
_SHELL_LITERAL_OPERATOR_VALUES = {
    encoded: operator for operator, encoded in _SHELL_LITERAL_OPERATOR_CODES.items()
}
_SHELL_UNPARSED_SENTINEL = "\0vibeworthy-shell-unparsed\0"
_REMOTE_COMMAND_ALIAS_PREFIX = "\0alias:"
_REMOTE_FILE_AMBIGUOUS = "\0remote-file-unknown\0"


def _decode_shell_literal_operators(value: str) -> str:
    for encoded, operator in _SHELL_LITERAL_OPERATOR_VALUES.items():
        value = value.replace(encoded, operator)
    return value


def _decode_shell_payload(value: str) -> str:
    value = _decode_shell_literal_operators(value)
    for encoded, operator in _SHELL_LITERAL_EXPANSION_VALUES.items():
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


def _detected_sensitive_values(
    text: str, *, code_context: bool = False
) -> set[str]:
    """Collect every concrete value that causes a high-confidence secret finding."""

    values = _detected_assignment_values(text, code_context=code_context)
    for pattern in (
        _PRIVATE_KEY_RE,
        _CLOUD_KEY_RE,
        *_PROVIDER_TOKEN_RES,
        _CREDENTIAL_URL_RE,
        _FIREBASE_KEY_RE,
        _SUPABASE_PUBLIC_RE,
        _SUPABASE_SECRET_RE,
    ):
        values.update(match.group(0) for match in pattern.finditer(text))
    for match in _JWT_RE.finditer(text):
        if _jwt_role(match.group(0)) in {"anon", "service_role"}:
            values.add(match.group(0))
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


def _ascii_backslash_projection(value: str) -> str:
    """Match the projection used when text output is forced through ASCII."""

    return value.encode("ascii", "backslashreplace").decode("ascii")


def _json_string_projection(value: str) -> str:
    """Match JSON string escaping without the surrounding quotation marks."""

    return json.dumps(value, ensure_ascii=True)[1:-1]


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


def _percent_decode_path_once(current: str) -> tuple[str, bool, bool]:
    """Decode one strict UTF-8 percent layer without replacement characters."""

    hexdigits = frozenset("0123456789abcdefABCDEF")
    output: list[str] = []
    changed = False
    invalid_octet_sequence = False
    index = 0
    while index < len(current):
        if (
            current[index] != "%"
            or index + 2 >= len(current)
            or current[index + 1] not in hexdigits
            or current[index + 2] not in hexdigits
        ):
            output.append(current[index])
            index += 1
            continue
        first = int(current[index + 1 : index + 3], 16)
        if first < 0x80:
            width = 1
        elif 0xC2 <= first <= 0xDF:
            width = 2
        elif 0xE0 <= first <= 0xEF:
            width = 3
        elif 0xF0 <= first <= 0xF4:
            width = 4
        else:
            width = 0
        encoded_end = index + (3 * width)
        if not width or encoded_end > len(current):
            invalid_octet_sequence = True
            output.append(current[index])
            index += 1
            continue
        encoded_parts = [
            current[position + 1 : position + 3]
            for position in range(index, encoded_end, 3)
        ]
        if any(
            current[position] != "%"
            or len(part) != 2
            or any(character not in hexdigits for character in part)
            for position, part in zip(range(index, encoded_end, 3), encoded_parts)
        ):
            invalid_octet_sequence = True
            output.append(current[index])
            index += 1
            continue
        try:
            decoded = bytes(int(part, 16) for part in encoded_parts).decode("utf-8")
        except UnicodeDecodeError:
            invalid_octet_sequence = True
            output.append(current[index])
            index += 1
            continue
        if len(decoded) != 1:
            invalid_octet_sequence = True
            output.append(current[index])
            index += 1
            continue
        output.append(decoded)
        changed = True
        index = encoded_end
    return "".join(output), changed, invalid_octet_sequence


def _source_escape_decode_once(current: str) -> tuple[str, bool]:
    """Decode one bounded JSON/JavaScript-style string escape layer."""

    output: list[str] = []
    changed = False
    index = 0
    simple = {
        "a": "\a", "b": "\b", "f": "\f", "n": "\n", "r": "\r",
        "t": "\t", "v": "\v",
        "\\": "\\", "/": "/", '"': '"', "'": "'",
    }
    while index < len(current):
        if current[index] != "\\" or index + 1 >= len(current):
            output.append(current[index])
            index += 1
            continue
        escape = current[index + 1]
        replacement = simple.get(escape)
        if replacement is not None:
            output.append(replacement)
            changed = True
            index += 2
            continue
        if escape in "01234567":
            octal_match = re.match(r"[0-7]{1,3}", current[index + 1 :])
            if octal_match is not None:
                output.append(chr(int(octal_match.group(0), 8)))
                changed = True
                index += 1 + len(octal_match.group(0))
                continue
        if escape == "N" and current[index + 2 : index + 3] == "{":
            closing = current.find("}", index + 3, min(len(current), index + 260))
            if closing >= 0:
                try:
                    named_character = unicodedata.lookup(
                        current[index + 3 : closing]
                    )
                except KeyError:
                    pass
                else:
                    output.append(named_character)
                    changed = True
                    index = closing + 1
                    continue
        digits = ""
        width = 0
        consumed = 0
        if escape == "x":
            width = 2
            digits = current[index + 2 : index + 4]
            consumed = 4
        elif escape == "u" and current[index + 2 : index + 3] == "{":
            closing = current.find("}", index + 3, min(len(current), index + 10))
            if closing >= 0:
                digits = current[index + 3 : closing]
                width = len(digits)
                consumed = closing - index + 1
        elif escape == "u":
            unicode_cursor = index + 1
            while (
                unicode_cursor < len(current)
                and current[unicode_cursor] == "u"
            ):
                unicode_cursor += 1
            width = 4
            digits = current[unicode_cursor : unicode_cursor + 4]
            consumed = unicode_cursor + 4 - index
        elif escape == "U":
            width = 8
            digits = current[index + 2 : index + 10]
            consumed = 10
        if (
            not width
            or len(digits) != width
            or re.fullmatch(r"[0-9A-Fa-f]+", digits) is None
        ):
            output.append(current[index])
            index += 1
            continue
        codepoint = int(digits, 16)
        if (
            escape == "u"
            and width == 4
            and 0xD800 <= codepoint <= 0xDBFF
            and current[index + consumed : index + consumed + 2] == "\\u"
        ):
            low_cursor = index + consumed + 1
            while low_cursor < len(current) and current[low_cursor] == "u":
                low_cursor += 1
            low_digits = current[low_cursor : low_cursor + 4]
            if re.fullmatch(r"[0-9A-Fa-f]{4}", low_digits):
                low = int(low_digits, 16)
                if 0xDC00 <= low <= 0xDFFF:
                    codepoint = (
                        0x10000
                        + ((codepoint - 0xD800) << 10)
                        + (low - 0xDC00)
                    )
                    consumed = low_cursor + 4 - index
        if codepoint > 0x10FFFF or 0xD800 <= codepoint <= 0xDFFF:
            output.append(current[index])
            index += 1
            continue
        output.append(chr(codepoint))
        changed = True
        index += consumed
    return "".join(output), changed


def _percent_decoded_path_views(
    value: str,
    max_rounds: int = MAX_PERCENT_DECODE_ROUNDS,
) -> tuple[list[str], bool, bool]:
    """Return strict UTF-8 percent-decoded views and whether the bound was hit."""

    views: list[str] = []
    current = value
    unsafe_projection = False
    for _round in range(max_rounds):
        decoded, changed, invalid_octet_sequence = _percent_decode_path_once(current)
        unsafe_projection = unsafe_projection or invalid_octet_sequence
        if not changed:
            return views, unsafe_projection, False
        views.append(decoded)
        current = decoded
    _probe, can_decode_again, invalid_octet_sequence = _percent_decode_path_once(current)
    return views, unsafe_projection or invalid_octet_sequence, can_decode_again


def _path_projection_closure(value: str) -> tuple[set[str], bool, bool]:
    """Close an emitted path over bounded renderer and downstream decoders.

    ``display_path`` has already passed through the safe-display renderer. JSON,
    ASCII fallback, and URI rendering may add one more encoding layer apiece, so
    those known renderer layers receive explicit budget bonuses. The underlying
    source remains limited to DEC-017's four source-encoding layers. The state
    space is a small constant product, making total work linear in path length.
    """

    normalized = unicodedata.normalize("NFC", value)
    safe = _safe_display_component(value)
    base_seeds = {
        (value, 1),
        (normalized, 1),
        (safe, 2 if safe != value else 1),
    }
    seeds: set[tuple[str, int, int]] = set()
    for base, safe_source_layers in base_seeds:
        seeds.add((base, MAX_PERCENT_DECODE_ROUNDS, MAX_PERCENT_DECODE_ROUNDS + safe_source_layers))
        seeds.add(
            (
                _ascii_backslash_projection(base),
                MAX_PERCENT_DECODE_ROUNDS,
                MAX_PERCENT_DECODE_ROUNDS + safe_source_layers + 1,
            )
        )
        seeds.add(
            (
                _json_string_projection(base),
                MAX_PERCENT_DECODE_ROUNDS,
                MAX_PERCENT_DECODE_ROUNDS + safe_source_layers + 1,
            )
        )
        uri = quote(base, safe="/._-")
        seeds.add(
            (
                uri,
                MAX_PERCENT_DECODE_ROUNDS + 1,
                MAX_PERCENT_DECODE_ROUNDS + safe_source_layers,
            )
        )
        seeds.add(
            (
                _json_string_projection(uri),
                MAX_PERCENT_DECODE_ROUNDS + 1,
                MAX_PERCENT_DECODE_ROUNDS + safe_source_layers + 1,
            )
        )

    views: set[str] = set()
    pending: deque[tuple[str, int, int, int, int]] = deque(
        (seed, 0, 0, percent_limit, source_limit)
        for seed, percent_limit, source_limit in seeds
    )
    seen: set[tuple[str, int, int, int, int]] = set()
    invalid_utf8 = False
    exceeds_rounds = False
    while pending:
        current, percent_depth, source_depth, percent_limit, source_limit = (
            pending.popleft()
        )
        state = (current, percent_depth, source_depth, percent_limit, source_limit)
        if state in seen:
            continue
        seen.add(state)
        if len(seen) > 1_024:
            return views, invalid_utf8, True
        views.add(current)
        views.add(unicodedata.normalize("NFC", current))
        views.add(_safe_display_component(current))

        percent_value, percent_changed, percent_invalid = (
            _percent_decode_path_once(current)
        )
        invalid_utf8 = invalid_utf8 or percent_invalid
        if percent_changed:
            if percent_depth >= percent_limit:
                exceeds_rounds = True
            else:
                pending.append(
                    (
                        percent_value,
                        percent_depth + 1,
                        source_depth,
                        percent_limit,
                        source_limit,
                    )
                )

        source_value, source_changed = _source_escape_decode_once(current)
        if source_changed:
            if source_depth >= source_limit:
                exceeds_rounds = True
            else:
                pending.append(
                    (
                        source_value,
                        percent_depth,
                        source_depth + 1,
                        percent_limit,
                        source_limit,
                    )
                )
    return views, invalid_utf8, exceeds_rounds


def _redact_content_values_from_paths(
    candidates: Sequence[Candidate], values: Iterable[str]
) -> list[Candidate]:
    """Redact detected values from every path projection a renderer can expose."""

    patterns: set[str] = set()
    pattern_characters = 0

    def add_pattern(value: str) -> None:
        nonlocal pattern_characters
        if not value or value == "." or value in patterns:
            return
        pattern_characters += len(value)
        if (
            len(patterns) + 1 > MAX_PATH_REDACTION_VALUES * 16
            or pattern_characters > MAX_PATH_REDACTION_PATTERN_CHARS
        ):
            raise PathRedactionLimitExceeded
        patterns.add(value)

    self_sanitized_candidates: list[Candidate] = []
    for candidate in candidates:
        sensitive_projection = False
        projection_views, _invalid_utf8, exceeds_rounds = _path_projection_closure(
            candidate.display_path
        )
        if exceeds_rounds:
            raise PathRedactionLimitExceeded
        for view in projection_views:
            normalized = unicodedata.normalize("NFC", view)
            safe = _safe_display_component(view)
            if safe != normalized and "[REDACTED" in safe:
                sensitive_projection = True
                break
        self_sanitized_candidates.append(
            dataclasses.replace(candidate, display_path="[REDACTED-PATH]")
            if sensitive_projection
            else candidate
        )
    candidates = self_sanitized_candidates

    for raw_value in values:
        protected_views: set[str] = set()
        pending_views: deque[tuple[str, int, int]] = deque([(raw_value, 0, 0)])
        seen_states: set[tuple[str, int, int]] = set()
        while pending_views:
            value, percent_depth, source_depth = pending_views.popleft()
            state = (value, percent_depth, source_depth)
            if state in seen_states:
                continue
            seen_states.add(state)
            if len(seen_states) > (MAX_PERCENT_DECODE_ROUNDS + 1) ** 2:
                raise PathRedactionLimitExceeded
            protected_views.add(value)

            percent_value, percent_changed, _invalid_utf8 = (
                _percent_decode_path_once(value)
            )
            if percent_changed:
                if percent_depth >= MAX_PERCENT_DECODE_ROUNDS:
                    raise PathRedactionLimitExceeded
                pending_views.append(
                    (percent_value, percent_depth + 1, source_depth)
                )

            source_value, source_changed = _source_escape_decode_once(value)
            if source_changed:
                if source_depth >= MAX_PERCENT_DECODE_ROUNDS:
                    raise PathRedactionLimitExceeded
                pending_views.append(
                    (source_value, percent_depth, source_depth + 1)
                )

        for value in sorted(protected_views):
            normalized = unicodedata.normalize("NFC", value)
            safe = _safe_display_component(value)
            for base_pattern in (value, normalized, safe):
                for pattern in (
                    base_pattern,
                    _ascii_backslash_projection(base_pattern),
                    _json_string_projection(base_pattern),
                ):
                    add_pattern(pattern)
                    add_pattern(quote(pattern, safe="/._-"))

    if not patterns:
        return _disambiguate_display_paths(list(candidates))
    replacement_sensitive = any("\ufffd" in pattern for pattern in patterns)

    transitions: list[dict[str, int]] = [{}]
    failures = [0]
    longest = [0]
    for value in sorted(patterns):
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
    transformed_characters = 0
    for candidate in candidates:
        intervals: list[tuple[int, int]] = []

        def collect_matches(view: str, *, retain_spans: bool) -> bool:
            state = 0
            matched = False
            for index, character in enumerate(view):
                while state and character not in transitions[state]:
                    state = failures[state]
                state = transitions[state].get(character, 0)
                match_length = longest[state]
                if not match_length:
                    continue
                matched = True
                start = index + 1 - match_length
                if retain_spans:
                    intervals.append((start, index + 1))
            return matched

        collect_matches(candidate.display_path, retain_spans=True)
        transformed_views, invalid_utf8, exceeds_rounds = _path_projection_closure(
            candidate.display_path
        )
        transformed_views.discard(candidate.display_path)
        if exceeds_rounds or (invalid_utf8 and replacement_sensitive):
            raise PathRedactionLimitExceeded
        transformed_characters += sum(len(view) for view in transformed_views)
        if transformed_characters > MAX_PATH_TRANSFORM_CHARS:
            raise PathRedactionLimitExceeded
        if any(
            collect_matches(view, retain_spans=False)
            for view in sorted(transformed_views)
        ):
            redacted.append(
                dataclasses.replace(candidate, display_path="[REDACTED-PATH]")
            )
            continue
        if not intervals:
            redacted.append(candidate)
            continue
        intervals.sort()
        merged: list[tuple[int, int]] = []
        for start, end in intervals:
            if merged and start <= merged[-1][1]:
                previous_start, previous_end = merged[-1]
                merged[-1] = (previous_start, max(end, previous_end))
            else:
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
    if re.fullmatch(r"\{[a-z_][a-z0-9_.]*\}", lowered) is not None:
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


def _reject_nonstandard_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


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


def _compound_stdout_reaches_interpreter(command: str) -> bool:
    """Return whether a completed compound command is piped into a shell."""

    tokens, complete = _tokenize_shell_line(command)
    if not complete or len(tokens) > MAX_SHELL_CLASSIFICATION_TOKENS:
        return False
    for pipe_index in range(len(tokens) - 1, -1, -1):
        if tokens[pipe_index] not in {"|", "|&"}:
            continue
        previous = next(
            (tokens[index] for index in range(pipe_index - 1, -1, -1) if tokens[index]),
            "",
        )
        if previous not in {"}", ")", "fi", "done", "esac"}:
            continue
        downstream: list[str] = []
        for token in tokens[pipe_index + 1 :]:
            if token and all(character in "|;&" for character in token):
                break
            downstream.append(token)
        invocation = _command_invocation(downstream)
        if invocation.complete and invocation.executable in _COMMAND_INTERPRETERS:
            return True
    return False


def _heredoc_specs(command: str) -> list[tuple[str, bool, bool]] | None:
    """Return every heredoc body and whether that body can become code."""

    contexts = _contextual_shell_commands(command)
    if not contexts:
        return []
    if re.search(r"(?<!<)<<-?(?!<)", contexts[0]) is None:
        return []
    tokens, complete = _tokenize_shell_line(contexts[0])
    if not complete:
        return None if "<<" in contexts[0] else []
    if len(tokens) > MAX_SHELL_CLASSIFICATION_TOKENS:
        return None
    heredoc_count = sum(
        1
        for token in tokens
        if _SHELL_REDIRECTION_RE.fullmatch(token) is not None
        and (token.endswith("<<-") or (token.endswith("<<") and not token.endswith("<<<")))
    )
    if heredoc_count > MAX_HEREDOC_SPECS:
        return None

    def descriptor(redirection: str) -> str:
        match = re.match(r"(?:[0-9]+|\{[A-Za-z_][A-Za-z0-9_]*\})?", redirection)
        return match.group(0) if match is not None else ""

    def feeds_stdin(redirection: str) -> bool:
        file_descriptor = descriptor(redirection)
        suffix = redirection[len(file_descriptor) :]
        is_stdin = file_descriptor == "" or (
            file_descriptor.isdigit() and not file_descriptor.strip("0")
        )
        return is_stdin and suffix.startswith("<")

    def redirects_stdout(redirection: str) -> bool:
        file_descriptor = descriptor(redirection)
        suffix = redirection[len(file_descriptor) :]
        is_stdout = file_descriptor == "" or (
            file_descriptor.isdigit()
            and (file_descriptor.lstrip("0") or "0") == "1"
        )
        return is_stdout and suffix.startswith((">", "&>"))

    def invocation_may_execute_stdin(invocation: _CommandInvocation) -> bool:
        if not invocation.complete or invocation.executable_index is None:
            return True
        executable_word = invocation.tokens[invocation.executable_index]
        if (
            invocation.executable in _COMMAND_INTERPRETERS
            or _token_has_dynamic_execution_hint(executable_word)
        ):
            return True
        if invocation.executable in _NON_EXECUTING_DATA_COMMANDS:
            return False
        return invocation.executable is not None

    # Classify each token and simple-command segment once. The former
    # implementation rescanned every redirection for every heredoc in the same
    # segment, making a bounded 64-heredoc header quadratic and repeatable.
    redirections = [
        _SHELL_REDIRECTION_RE.fullmatch(token) is not None for token in tokens
    ]
    stdin_redirections = [
        is_redirection and feeds_stdin(token)
        for token, is_redirection in zip(tokens, redirections)
    ]
    stdout_redirections = [
        is_redirection and redirects_stdout(token)
        for token, is_redirection in zip(tokens, redirections)
    ]
    segments: list[
        tuple[int, int, _CommandInvocation, tuple[int, ...], bool]
    ] = []
    segment_for_token: list[int | None] = [None] * len(tokens)
    segment_start = 0
    for token_index in range(len(tokens) + 1):
        is_boundary = token_index == len(tokens) or (
            tokens[token_index]
            and all(character in "|;&" for character in tokens[token_index])
        )
        if not is_boundary:
            continue
        if segment_start < token_index:
            segment_index = len(segments)
            segment_stdin = tuple(
                index
                for index in range(segment_start, token_index)
                if stdin_redirections[index]
            )
            segments.append(
                (
                    segment_start,
                    token_index,
                    _command_invocation(tokens[segment_start:token_index]),
                    segment_stdin,
                    any(stdout_redirections[segment_start:token_index]),
                )
            )
            for index in range(segment_start, token_index):
                segment_for_token[index] = segment_index
        segment_start = token_index + 1

    specs: list[tuple[str, bool, bool]] = []
    docker_run_heredoc = re.match(r"^\s*RUN\b", command, re.IGNORECASE) is not None
    for index, token in enumerate(tokens[:-1]):
        is_heredoc = token.endswith("<<-") or (
            token.endswith("<<") and not token.endswith("<<<")
        )
        if not redirections[index] or not is_heredoc:
            continue
        delimiter = tokens[index + 1]
        segment_index = segment_for_token[index]
        if segment_index is None:
            return None
        start, end, invocation, segment_stdin, stdout_override = segments[
            segment_index
        ]
        effective_stdin = bool(segment_stdin and segment_stdin[-1] == index)
        downstream_executes = False
        if effective_stdin and invocation.executable == "cat":
            current_segment = segment_index
            flow_depends_on_body = not stdout_override
            while current_segment + 1 < len(segments):
                current_end = segments[current_segment][1]
                if current_end >= len(tokens) or tokens[current_end] not in {"|", "|&"}:
                    break
                current_segment += 1
                (
                    _downstream_start,
                    _downstream_end,
                    downstream,
                    downstream_stdin,
                    downstream_stdout,
                ) = segments[current_segment]
                if downstream_stdin:
                    flow_depends_on_body = False
                if flow_depends_on_body and invocation_may_execute_stdin(downstream):
                    downstream_executes = True
                    break
                if downstream_stdout:
                    flow_depends_on_body = False
        compound_downstream_executes = bool(
            effective_stdin
            and invocation.executable == "cat"
            and not stdout_override
            and _compound_stdout_reaches_interpreter(command)
        )
        executes = docker_run_heredoc or (
            effective_stdin and invocation_may_execute_stdin(invocation)
        ) or downstream_executes or compound_downstream_executes
        specs.append((delimiter, token.endswith("<<-"), executes))
    return specs


def _embedded_heredoc_bodies(
    command: str,
    specs: Sequence[tuple[str, bool, bool]],
) -> list[tuple[int, int, str, bool]] | None:
    """Extract already-contained heredoc bodies from a multiline logical command."""

    if not specs or "\n" not in command:
        return None
    lines = command.splitlines()
    header_index = next(
        (
            index
            for index, line in enumerate(lines)
            if re.search(r"(?<!<)<<-?(?!<)", line) is not None
        ),
        None,
    )
    if header_index is None:
        return None
    cursor = header_index + 1
    bodies: list[tuple[int, int, str, bool]] = []
    current_header = header_index
    for delimiter, strip_tabs, executes in specs:
        closing_index: int | None = None
        for index in range(cursor, len(lines)):
            comparison = lines[index].lstrip("\t") if strip_tabs else lines[index]
            if comparison == delimiter:
                closing_index = index
                break
        if closing_index is None:
            return None
        body_lines = [
            line.lstrip("\t") if strip_tabs else line
            for line in lines[cursor:closing_index]
        ]
        bodies.append(
            (current_header, cursor, "\n".join(body_lines), executes)
        )
        cursor = closing_index + 1
        next_header = next(
            (
                index
                for index in range(cursor, len(lines))
                if re.search(r"(?<!<)<<-?(?!<)", lines[index]) is not None
            ),
            None,
        )
        if next_header is not None:
            current_header = next_header
            cursor = next_header + 1
    return bodies


_FUNCTION_SIGNATURE_SOURCE = (
    r"(?:(?:function\s+(?P<keyword>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s*\(\s*\))?)|(?P<posix>[A-Za-z_][A-Za-z0-9_]*)\s*\(\s*\))"
)
_FUNCTION_HEADER_ONLY_RE = re.compile(
    rf"^\s*{_FUNCTION_SIGNATURE_SOURCE}\s*$"
)
_FUNCTION_DECLARATION_RE = re.compile(
    rf"^\s*{_FUNCTION_SIGNATURE_SOURCE}\s*"
    r"(?:(?P<opener>[{(])|(?P<control>if|until|while|for|select|case)\b)",
    re.DOTALL,
)
_FUNCTION_SIGNATURE_PREFIX_RE = re.compile(
    rf"^\s*{_FUNCTION_SIGNATURE_SOURCE}\s*",
    re.DOTALL,
)


@dataclasses.dataclass
class _ShellMultilineBalance:
    parentheses: int = 0
    braces: int = 0
    controls: int = 0
    quote_character: str | None = None
    escaped: bool = False
    backtick: bool = False
    relevant: bool = False
    awaiting_function_body: bool = False

    def feed(self, fragment: str) -> None:
        signature = _FUNCTION_SIGNATURE_PREFIX_RE.match(fragment)
        function_tail = fragment[signature.end() :] if signature is not None else fragment
        if signature is not None:
            self.relevant = True
            self.awaiting_function_body = not bool(function_tail.strip())
        elif self.awaiting_function_body and fragment.strip():
            self.awaiting_function_body = False
            self.relevant = True
        if (
            _has_remote_fetcher_hint(fragment)
            or fragment.strip() in {"(", "{"}
            or re.match(
                r"^\s*(?:(?:!|time(?:\s+-[^\s]+)*)\s+)+(?:\{|\()\s*$",
                fragment,
            )
            is not None
            or re.match(
                r"^\s*(?:case|for|if|select|until|while)\b",
                fragment,
            )
            is not None
            or re.match(
                r"^\s*(?:(?:function\s+)?[A-Za-z_][A-Za-z0-9_]*\s*\(\s*\))\s*\{?\s*$",
                fragment,
            )
            is not None
        ):
            self.relevant = True
        index = 0
        while index < len(fragment):
            character = fragment[index]
            if self.escaped:
                self.escaped = False
                index += 1
                continue
            if self.quote_character == "'":
                if character == "'":
                    self.quote_character = None
                index += 1
                continue
            if character == "\\":
                self.escaped = True
                index += 1
                continue
            if character == "`" and self.quote_character != "'":
                self.backtick = not self.backtick
                self.relevant = self.relevant or fragment.lstrip().startswith(
                    ("`", '"`')
                )
                index += 1
                continue
            if self.backtick:
                index += 1
                continue
            if self.quote_character == '"':
                if character == '"' and self.parentheses == 0:
                    self.quote_character = None
                elif character == "$" and fragment[index : index + 2] == "$(":
                    self.parentheses += 1
                    self.relevant = True
                    index += 2
                    continue
                elif character == ")" and self.parentheses:
                    self.parentheses -= 1
                index += 1
                continue
            if character in {'"', "'"}:
                self.quote_character = character
                index += 1
                continue
            if character in "<$>" and fragment[index : index + 2] in {"$(", "<(", ">("}:
                self.parentheses += 1
                self.relevant = True
                index += 2
                continue
            if character == "(":
                self.parentheses += 1
            elif character == ")" and self.parentheses:
                self.parentheses -= 1
            elif character == "{":
                self.braces += 1
            elif character == "}" and self.braces:
                self.braces -= 1
            index += 1

        tokens, _complete = _tokenize_shell_line(function_tail)
        command_position = True
        for token in tokens:
            normalized = token.strip("(){}")
            if token and all(character in "|;&" for character in token):
                command_position = True
                continue
            if normalized in {"then", "do", "else", "elif", "in"}:
                command_position = True
                continue
            if command_position and normalized in {
                "case", "for", "if", "select", "until", "while"
            }:
                self.controls += 1
            elif (
                command_position
                and normalized in {"done", "esac", "fi"}
                and self.controls
            ):
                self.controls -= 1
            command_position = False

    def needs_more(self) -> bool:
        return self.relevant and bool(
            self.parentheses
            or self.braces
            or self.controls
            or self.quote_character
            or self.backtick
            or self.awaiting_function_body
        )

    def reset(self) -> None:
        self.parentheses = 0
        self.braces = 0
        self.controls = 0
        self.quote_character = None
        self.escaped = False
        self.backtick = False
        self.relevant = False
        self.awaiting_function_body = False


def _logical_shell_commands(
    text: str,
    shell_payload: bool = False,
    structural_multiline: bool = True,
) -> Iterable[tuple[int, str, bool]]:
    """Yield executable logical lines, excluding data-only heredoc bodies."""

    parts: list[str] = []
    start_line = 1
    heredoc: tuple[str, bool, bool, int] | None = None
    pending_heredocs: deque[tuple[str, bool, bool]] = deque()
    heredoc_body: list[str] = []
    continuation_glue = " "
    folded_yaml_indent: int | None = None
    multiline_balance = _ShellMultilineBalance()
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if heredoc is not None:
            delimiter, strip_tabs, executes, body_start = heredoc
            comparison = raw_line.lstrip("\t") if strip_tabs else raw_line
            if comparison == delimiter:
                if executes and heredoc_body:
                    for nested_line, nested_command, _nested_payload in _logical_shell_commands(
                        "\n".join(heredoc_body),
                        True,
                        True,
                    ):
                        yield body_start + nested_line - 1, nested_command, True
                heredoc_body = []
                if pending_heredocs:
                    next_delimiter, next_strip_tabs, next_executes = pending_heredocs.popleft()
                    heredoc = (
                        next_delimiter,
                        next_strip_tabs,
                        next_executes,
                        line_number + 1,
                    )
                else:
                    heredoc = None
            else:
                heredoc_body.append(raw_line.lstrip("\t") if strip_tabs else raw_line)
            continue
        if folded_yaml_indent is not None:
            if not raw_line.strip():
                continue
            indentation = len(raw_line) - len(raw_line.lstrip(" "))
            if indentation > folded_yaml_indent:
                continue
            folded_yaml_indent = None
        if not parts:
            start_line = line_number
        trimmed = _shell_without_comment(raw_line).rstrip()
        trailing_backslashes = len(trimmed) - len(trimmed.rstrip("\\"))
        backslash_continuation = trailing_backslashes % 2 == 1
        if backslash_continuation:
            trimmed = trimmed[:-1]
        trailing_carets = len(trimmed) - len(trimmed.rstrip("^"))
        caret_continuation = trailing_carets % 2 == 1
        if caret_continuation:
            trimmed = trimmed[:-1]
        if parts and continuation_glue == "" and trimmed.strip():
            # The opposite shell dialect may treat the preceding continuation
            # marker literally, making this physical line independently active.
            yield line_number, trimmed, shell_payload
        parts.append((continuation_glue if parts else "") + trimmed)
        if structural_multiline:
            multiline_balance.feed(trimmed)
        yaml_header_match = re.match(
            r"^\s*(?:-\s*)?(?:run|script|command)\s*:\s*[|>][-+]?\s*$",
            trimmed,
            re.IGNORECASE,
        )
        yaml_block_header = yaml_header_match is not None
        continuation_tokens, continuation_complete = _tokenize_shell_line(trimmed)
        pipeline_continuation = bool(
            not yaml_block_header
            and continuation_complete
            and continuation_tokens
            and continuation_tokens[-1] in {"|", "|&", "||"}
        )
        structural_continuation = (
            structural_multiline and multiline_balance.needs_more()
        )
        if (
            backslash_continuation
            or caret_continuation
            or pipeline_continuation
            or structural_continuation
        ):
            continuation_glue = (
                ""
                if (backslash_continuation or caret_continuation)
                else "\n" if structural_continuation else " "
            )
            continue
        logical = "".join(parts)
        yield start_line, logical, shell_payload
        specifications = (
            _heredoc_specs(logical)
            if structural_multiline or shell_payload
            else []
        )
        if specifications is None:
            yield start_line, _SHELL_UNPARSED_SENTINEL, shell_payload
            return
        embedded_bodies = (
            _embedded_heredoc_bodies(logical, specifications)
            if specifications
            else None
        )
        if embedded_bodies is not None:
            for _header_offset, body_offset, body, executes in embedded_bodies:
                if not executes or not body:
                    continue
                for nested_line, nested_command, _nested_payload in _logical_shell_commands(
                    body,
                    True,
                    True,
                ):
                    yield (
                        start_line + body_offset + nested_line - 1,
                        nested_command,
                        True,
                    )
            # These delimiters and bodies were already consumed as part of the
            # structural logical command; do not treat following source lines
            # as their bodies a second time.
            specifications = []
        if specifications:
            delimiter, strip_tabs, executes = specifications[0]
            heredoc = (delimiter, strip_tabs, executes, line_number + 1)
            pending_heredocs.extend(specifications[1:])
        if yaml_block_header and ">" in trimmed.rsplit(":", 1)[-1]:
            folded_yaml_indent = len(raw_line) - len(raw_line.lstrip(" "))
        parts = []
        continuation_glue = " "
        multiline_balance.reset()
    if heredoc is not None:
        _delimiter, _strip_tabs, executes, body_start = heredoc
        if executes and heredoc_body:
            for nested_line, nested_command, _nested_payload in _logical_shell_commands(
                "\n".join(heredoc_body),
                True,
            ):
                yield body_start + nested_line - 1, nested_command, True
    elif parts:
        yield start_line, "".join(parts), shell_payload


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
            yield index + 1, lines[index], False
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


def _token_has_interpreter_hint(value: str) -> bool:
    decoded = _decode_shell_literal_operators(value).strip()
    if _normalized_executable_name(decoded) in _COMMAND_INTERPRETERS:
        return True
    compact = decoded.replace(" ", "").casefold()
    if compact in {
        "$shell", "${shell}", "$comspec", "${comspec}", "%shell%", "%comspec%"
    }:
        return True
    return (
        re.fullmatch(
            r"\$\{(?:shell|comspec)(?:[^A-Za-z0-9_{}][^{}]{0,255})?\}",
            compact,
        )
        is not None
        or re.fullmatch(r"%(?:shell|comspec)(?::[^%]{0,256})?%", compact)
        is not None
        or re.fullmatch(r"!(?:shell|comspec)!", compact) is not None
    )


def _token_has_dynamic_execution_hint(value: str) -> bool:
    """Return whether an executable word depends on active shell expansion."""

    decoded = _decode_shell_literal_operators(value).strip()
    if any(marker in decoded for marker in _SHELL_LITERAL_EXPANSION_CODES.values()):
        return False
    return (
        decoded.startswith(("$", "%", "!", "`"))
        or "$(" in decoded
        or re.fullmatch(r"%[^%]{1,256}%", decoded) is not None
        or re.fullmatch(r"![^!]{1,256}!", decoded) is not None
    )


def _invocation_redirects_stdout(tokens: Sequence[str]) -> bool:
    return any(_redirection_changes_stdout(token) for token in tokens)


def _shell_descriptor_routes(tokens: Sequence[str]) -> dict[int, str] | None:
    """Apply bounded output redirections with fd 1 initially representing a pipe."""

    routes: dict[int, str] = {0: "stdin", 1: "stdout", 2: "stderr"}

    def target_route(target: str) -> str | None:
        decoded = _decode_shell_literal_operators(target).strip().strip('"\'')
        aliases = {
            "/dev/stdin": 0,
            "/dev/stdout": 1,
            "/dev/stderr": 2,
        }
        if decoded in aliases:
            return routes.get(aliases[decoded], "file")
        descriptor_path = re.fullmatch(
            r"/(?:dev|proc/self)/fd/(?P<fd>[0-9]+)", decoded
        )
        if descriptor_path is not None:
            return routes.get(int(descriptor_path.group("fd")), "file")
        if "$" in decoded or "`" in decoded or not decoded:
            return None
        return "file"

    index = 0
    while index < len(tokens):
        token = _decode_shell_literal_operators(tokens[index])
        duplication = re.fullmatch(
            r"(?P<destination>[0-9]*)>&(?P<source>[0-9]+|-)", token
        )
        if duplication is not None:
            destination = int(duplication.group("destination") or "1")
            source = duplication.group("source")
            routes[destination] = (
                "closed" if source == "-" else routes.get(int(source), "file")
            )
            index += 1
            continue
        output = re.fullmatch(
            r"(?P<all>&)?(?P<destination>[0-9]*)(?:>>?|>\|)", token
        )
        if output is None:
            index += 1
            continue
        target_index = index + 1
        while target_index < len(tokens) and not tokens[target_index]:
            target_index += 1
        if target_index >= len(tokens):
            return None
        route = target_route(tokens[target_index])
        if route is None:
            return None
        if output.group("all"):
            routes[1] = route
            routes[2] = route
        else:
            destination = int(output.group("destination") or "1")
            routes[destination] = route
        index = target_index + 1
    return routes


def _stdout_reaches_pipeline(tokens: Sequence[str]) -> bool | None:
    routes = _shell_descriptor_routes(tokens)
    return None if routes is None else routes.get(1) == "stdout"


def _fetch_output_target_reaches_stdout(
    target: str,
    tokens: Sequence[str],
) -> bool:
    """Classify fetcher output aliases that feed fd 1 after redirections."""

    decoded = _decode_shell_literal_operators(target).strip()
    routes = _shell_descriptor_routes(tokens)
    if decoded == "-":
        return routes is None or routes.get(1) == "stdout"
    descriptor_aliases = {
        "/dev/stdin": 0,
        "/dev/stdout": 1,
        "/dev/stderr": 2,
    }
    descriptor = descriptor_aliases.get(decoded)
    descriptor_path = re.fullmatch(
        r"/(?:dev|proc/self)/fd/(?P<fd>[0-9]+)", decoded
    )
    if descriptor_path is not None:
        descriptor = int(descriptor_path.group("fd"))
    if descriptor is not None:
        return routes is None or routes.get(descriptor) == "stdout"
    if (
        "$" in decoded
        or "`" in decoded
        or decoded.startswith(("/dev/fd/", "/proc/self/fd/"))
    ):
        return True
    return False


def _fetch_arguments_output_stdout(
    executable: str | None,
    arguments: Sequence[str],
    tokens: Sequence[str],
) -> bool:
    """Return whether any bounded fetch transfer can still write to stdout."""

    decoded_arguments = [
        _decode_shell_literal_operators(argument) for argument in arguments
    ]
    if executable is None:
        if any(
            argument in {"-o", "--output", "--remote-name", "--remote-name-all"}
            or argument.startswith(("-o", "--output="))
            for argument in decoded_arguments
        ):
            executable = "curl"
        elif any(
            argument == "--output-document"
            or argument.startswith("--output-document=")
            for argument in decoded_arguments
        ):
            executable = "wget"
        else:
            return True

    if executable == "wget":
        index = 0
        saw_file_target = False
        while index < len(decoded_arguments):
            argument = decoded_arguments[index]
            if argument in {"-O", "--output-document"}:
                if index + 1 >= len(decoded_arguments):
                    return True
                target = decoded_arguments[index + 1]
                if _fetch_output_target_reaches_stdout(target, tokens):
                    return True
                saw_file_target = True
                index += 2
                continue
            if argument.startswith("--output-document="):
                if _fetch_output_target_reaches_stdout(
                    argument.split("=", 1)[1], tokens
                ):
                    return True
                saw_file_target = True
            elif re.match(r"^-O.+", argument):
                if _fetch_output_target_reaches_stdout(argument[2:], tokens):
                    return True
                saw_file_target = True
            index += 1
        return not saw_file_target

    # curl associates output selections with transfers. Preserve the source of
    # each selection so a later boolean negation can cancel only `-O`, without
    # accidentally discarding an explicit `-o file` target.
    output_queue: deque[tuple[bool, str]] = deque()
    remote_name_all = False
    transfers = 0
    curl_options_with_values = {
        "-A", "--user-agent", "-b", "--cookie", "-c", "--cookie-jar",
        "-d", "--data", "--data-ascii", "--data-binary", "--data-raw",
        "--data-urlencode", "-e", "--referer", "-F", "--form",
        "-H", "--header", "-m", "--max-time", "-u", "--user",
        "-x", "--proxy", "-X", "--request", "--connect-timeout",
        "--retry", "--retry-delay", "--resolve", "--cacert", "--cert",
        "--key", "-w", "--write-out",
    }

    def register_transfer() -> bool:
        nonlocal transfers
        transfers += 1
        reaches_stdout = (
            output_queue.popleft()[0] if output_queue else not remote_name_all
        )
        return reaches_stdout

    index = 0
    while index < len(decoded_arguments):
        argument = decoded_arguments[index]
        if argument == "--next":
            output_queue.clear()
            index += 1
            continue
        if argument == "--remote-name-all":
            remote_name_all = True
            index += 1
            continue
        if argument == "--no-remote-name-all":
            remote_name_all = False
            index += 1
            continue
        if argument in {"-O", "--remote-name"}:
            output_queue.append((False, "remote-name"))
            index += 1
            continue
        if argument == "--no-remote-name":
            output_queue = deque(
                selection
                for selection in output_queue
                if selection[1] != "remote-name"
            )
            index += 1
            continue
        if argument in {"--remote-header-name", "--no-remote-header-name"}:
            # `-J` only changes the filename selected by `-O`; it does not
            # redirect response bytes by itself.
            index += 1
            continue
        if argument in {"-o", "--output"}:
            if index + 1 >= len(decoded_arguments):
                return True
            output_queue.append(
                (
                    _fetch_output_target_reaches_stdout(
                        decoded_arguments[index + 1], tokens
                    ),
                    "output",
                )
            )
            index += 2
            continue
        if argument.startswith("--output="):
            output_queue.append(
                (
                    _fetch_output_target_reaches_stdout(
                        argument.split("=", 1)[1], tokens
                    ),
                    "output",
                )
            )
            index += 1
            continue
        if re.match(r"^-o.+", argument):
            output_queue.append(
                (
                    _fetch_output_target_reaches_stdout(argument[2:], tokens),
                    "output",
                )
            )
            index += 1
            continue
        if argument == "--url":
            if index + 1 >= len(decoded_arguments):
                return True
            if register_transfer():
                return True
            index += 2
            continue
        if argument.startswith("--url="):
            if register_transfer():
                return True
            index += 1
            continue
        if argument in curl_options_with_values:
            index += 2
            continue
        if not argument.startswith("-"):
            if register_transfer():
                return True
        index += 1
    return transfers == 0 and not output_queue


def _remote_fetch_command_outputs_stdout(tokens: Sequence[str]) -> bool:
    invocation = _command_invocation(tokens)
    if not invocation.complete or invocation.executable_index is None:
        return False
    if invocation.executable not in {"curl", "wget"}:
        if invocation.executable != "eval":
            return False
        arguments = invocation.tokens[invocation.executable_index + 1 :]
        if not arguments:
            return False
        nested_tokens, nested_complete = _tokenize_shell_line(arguments[0])
        if not nested_complete:
            return True
        return _remote_fetch_command_outputs_stdout(nested_tokens)
    stdout_reaches_pipeline = _stdout_reaches_pipeline(tokens)
    if stdout_reaches_pipeline is False:
        return False
    arguments = list(invocation.tokens[invocation.executable_index + 1 :])
    return _fetch_arguments_output_stdout(
        invocation.executable,
        arguments,
        tokens,
    )


def _pipeline_has_remote_shell(commands: Sequence[Sequence[str]]) -> bool:
    names = [_shell_command_name(command) for command in commands]
    fetchers = {"curl", "wget"}
    shells = _COMMAND_INTERPRETERS
    saw_fetcher = False
    for command, name in zip(commands, names):
        if name in fetchers:
            saw_fetcher = saw_fetcher or _remote_fetch_command_outputs_stdout(command)
        elif saw_fetcher and name in shells:
            return True
    return False


def _pipeline_has_ambiguous_remote_shell(commands: Sequence[Sequence[str]]) -> bool:
    """Fail closed when an unknown launcher precedes a fetcher token."""

    names = [_shell_command_name(command) for command in commands]
    shells = _COMMAND_INTERPRETERS
    non_launching_data_commands = _NON_EXECUTING_DATA_COMMANDS
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
            _token_has_interpreter_hint(token) for token in commands[index]
        ):
            saw_ambiguous_launcher = True

    for index, command in enumerate(commands):
        name = names[index]
        if name in {"curl", "wget"}:
            if not _remote_fetch_command_outputs_stdout(command):
                continue
            if ambiguous_launcher_after[index]:
                return True
            for later_command, later_name in zip(
                commands[index + 1 :],
                names[index + 1 :],
            ):
                later_invocation = _command_invocation(later_command)
                if (
                    later_invocation.complete
                    and later_invocation.executable_index is not None
                    and any(
                        marker
                        in later_invocation.tokens[later_invocation.executable_index]
                        for marker in _SHELL_LITERAL_EXPANSION_VALUES
                    )
                ):
                    continue
                if later_name in non_launching_data_commands:
                    continue
                if later_name not in shells:
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
            _token_has_interpreter_hint(candidate)
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


def _tokens_have_dynamic_source_pipeline(tokens: Sequence[str]) -> bool:
    pipeline: list[list[str]] = []
    command: list[str] = []

    def finish_pipeline() -> bool:
        nonlocal pipeline, command
        if command:
            pipeline.append(command)
        if len(pipeline) < 2:
            pipeline = []
            command = []
            return False
        for index, source in enumerate(pipeline[:-1]):
            source_invocation = _command_invocation(source)
            if (
                not source_invocation.complete
                or source_invocation.executable_index is None
            ):
                continue
            executable_word = source_invocation.tokens[
                source_invocation.executable_index
            ]
            if not _token_has_dynamic_execution_hint(executable_word):
                continue
            for sink in pipeline[index + 1 :]:
                sink_invocation = _command_invocation(sink)
                if sink_invocation.executable in _NON_EXECUTING_DATA_COMMANDS:
                    continue
                return True
        pipeline = []
        command = []
        return False

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
                        _decode_shell_payload(
                            " ".join(invocation_arguments[index + 1 :])
                        )
                    )
                    break
            continue

        if executable == "eval":
            if executable_index + 1 < len(invocation_arguments):
                payloads.append(
                    _decode_shell_payload(
                        " ".join(invocation_arguments[executable_index + 1 :])
                    )
                )
            continue

        if executable in interpreter_options:
            accepted = interpreter_options[executable]
            for index in range(executable_index + 1, len(invocation_arguments) - 1):
                if invocation_arguments[index].lower() in accepted:
                    payloads.append(
                        _decode_shell_payload(invocation_arguments[index + 1])
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
                        _decode_shell_payload(invocation_arguments[payload_index])
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

    if len(command) > MAX_SHELL_CLASSIFICATION_CHARS:
        return [], False
    tokens: list[str] = []
    current: list[str] = []
    quote_character: str | None = None
    ansi_c_quote = False
    escaped = False
    token_started = False
    index = 0

    def finish_token() -> None:
        nonlocal token_started
        if token_started:
            tokens.append("".join(current))
            current.clear()
            token_started = False

    def append_literal(character: str, *, protect_expansion: bool = False) -> None:
        nonlocal token_started
        token_started = True
        if protect_expansion and character in _SHELL_LITERAL_EXPANSION_CODES:
            current.append(_SHELL_LITERAL_EXPANSION_CODES[character])
        else:
            current.append(_SHELL_LITERAL_OPERATOR_CODES.get(character, character))

    while index < len(command):
        character = command[index]
        if escaped:
            append_literal(character, protect_expansion=True)
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
                    append_literal(simple_escapes[escape], protect_expansion=True)
                    index += 2
                    continue
                widths = {"x": 2, "u": 4, "U": 8}
                width = widths.get(escape)
                if width is not None:
                    digits = command[index + 2 : index + 2 + width]
                    if len(digits) == width and all(value in "0123456789abcdefABCDEF" for value in digits):
                        try:
                            append_literal(chr(int(digits, 16)), protect_expansion=True)
                        except ValueError:
                            pass
                        index += 2 + width
                        continue
                if escape in "01234567":
                    end = index + 2
                    while end < min(len(command), index + 5) and command[end] in "01234567":
                        end += 1
                    append_literal(
                        chr(int(command[index + 1 : end], 8)),
                        protect_expansion=True,
                    )
                    index = end
                    continue
                current.extend(("\\", escape))
                token_started = True
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
                    token_started = True
            else:
                append_literal(
                    character,
                    protect_expansion=quote_character == "'" or ansi_c_quote,
                )
            index += 1
            continue
        if character in {'"', "'"}:
            token_started = True
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
                token_started = True
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
        token_started = True
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
    if (
        _REMOTE_FETCHER_RE.search(command) is not None
        or _REMOTE_FETCHER_OBFUSCATED_RE.search(command) is not None
    ):
        return True
    if "\\\n" not in command and "^\n" not in command and "\\\r\n" not in command and "^\r\n" not in command:
        return False
    joined = re.sub(r"[\\^]\r?\n", "", command)
    return (
        _REMOTE_FETCHER_RE.search(joined) is not None
        or _REMOTE_FETCHER_OBFUSCATED_RE.search(joined) is not None
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


def _top_level_shell_statements(command: str) -> tuple[list[str], bool]:
    """Split command lists in source order without entering functions or subshells."""

    leading_function = _FUNCTION_DECLARATION_RE.match(command)
    if (
        leading_function is not None
        and leading_function.group("control") is not None
        and _function_declaration(command) is not None
    ):
        return [command.strip()], True

    statements: list[str] = []
    start = 0
    quote_character: str | None = None
    escaped = False
    brace_depth = 0
    parenthesis_depth = 0
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
        if character in {'"', "'"}:
            quote_character = (
                None
                if quote_character == character
                else character if quote_character is None else quote_character
            )
            index += 1
            continue
        if quote_character is not None:
            index += 1
            continue
        if character == "{":
            brace_depth += 1
        elif character == "}":
            brace_depth -= 1
            if brace_depth < 0:
                return statements, False
        elif character == "(":
            parenthesis_depth += 1
        elif character == ")":
            parenthesis_depth -= 1
            if parenthesis_depth < 0:
                return statements, False
        elif brace_depth == 0 and parenthesis_depth == 0:
            separator_width = 0
            if character == "\n" and _FUNCTION_HEADER_ONLY_RE.fullmatch(
                command[start:index]
            ) is not None:
                index += 1
                continue
            if character in {";", "\n"}:
                separator_width = 1
            elif character == "&" and (
                (index == 0 or command[index - 1] not in "|><")
                and command[index : index + 2] != "&>"
            ):
                separator_width = 2 if command[index : index + 2] == "&&" else 1
            elif command[index : index + 2] == "||":
                separator_width = 2
            if separator_width:
                statement = command[start:index].strip()
                if statement:
                    statements.append(statement)
                index += separator_width
                start = index
                continue
        index += 1
    statement = command[start:].strip()
    if statement:
        statements.append(statement)
    return statements, (
        quote_character is None
        and not escaped
        and brace_depth == 0
        and parenthesis_depth == 0
    )


def _has_top_level_uncertain_state_separator(command: str) -> bool:
    """Recognize async/short-circuit lists whose state effects are conditional."""

    quote_character: str | None = None
    escaped = False
    brace_depth = 0
    parenthesis_depth = 0
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
        if character in {'"', "'"}:
            quote_character = (
                None
                if quote_character == character
                else character if quote_character is None else quote_character
            )
            index += 1
            continue
        if quote_character is not None:
            index += 1
            continue
        if character == "{":
            brace_depth += 1
        elif character == "}" and brace_depth:
            brace_depth -= 1
        elif character == "(":
            parenthesis_depth += 1
        elif character == ")" and parenthesis_depth:
            parenthesis_depth -= 1
        elif brace_depth == 0 and parenthesis_depth == 0:
            if command[index : index + 2] in {"&&", "||"}:
                return True
            if character == "&" and (
                index == 0 or command[index - 1] not in {"|", ">", "<"}
            ):
                return True
        index += 1
    return False


def _redirection_changes_stdout(redirection: str) -> bool:
    if _SHELL_REDIRECTION_RE.fullmatch(redirection) is None:
        return False
    if redirection.startswith("&>"):
        return True
    descriptor_match = re.match(r"(?:[0-9]+|\{[A-Za-z_][A-Za-z0-9_]*\})?", redirection)
    descriptor = descriptor_match.group(0) if descriptor_match is not None else ""
    suffix = redirection[len(descriptor) :]
    if not suffix.startswith(">"):
        return False
    if not descriptor:
        return True
    return descriptor.isdigit() and (descriptor.lstrip("0") or "0") == "1"


def _function_declaration(statement: str) -> tuple[str, str, bool] | None:
    match = _FUNCTION_DECLARATION_RE.match(statement)
    if match is None:
        return None
    name = match.group("keyword") or match.group("posix")

    def stdout_redirected(suffix: str) -> bool:
        suffix_tokens, suffix_complete = _tokenize_shell_line(suffix)
        return suffix_complete and any(
            _redirection_changes_stdout(token) for token in suffix_tokens
        )

    opener = match.group("opener")
    if opener is None:
        control = match.group("control")
        closing_word = {
            "case": "esac",
            "for": "done",
            "if": "fi",
            "select": "done",
            "until": "done",
            "while": "done",
        }[control]
        quote_character: str | None = None
        escaped = False
        closing_end: int | None = None
        index = match.end()
        while index < len(statement):
            character = statement[index]
            if escaped:
                escaped = False
                index += 1
                continue
            if character == "\\" and quote_character != "'":
                escaped = True
                index += 1
                continue
            if character in {'"', "'"}:
                quote_character = (
                    None
                    if quote_character == character
                    else character if quote_character is None else quote_character
                )
                index += 1
                continue
            if quote_character is not None:
                index += 1
                continue
            if character.isalpha() or character == "_":
                end = index + 1
                while end < len(statement) and (
                    statement[end].isalnum() or statement[end] == "_"
                ):
                    end += 1
                if statement[index:end] == closing_word:
                    closing_end = end
                index = end
                continue
            index += 1
        if closing_end is None:
            return None
        suffix = statement[closing_end:]
        suffix_tokens, suffix_complete = _tokenize_shell_line(suffix)
        remaining, redirections_complete = _without_shell_redirections(suffix_tokens)
        if suffix.strip() and (
            not suffix_complete or not redirections_complete or remaining
        ):
            return None
        return (
            name,
            statement[match.start("control") : closing_end],
            stdout_redirected(suffix),
        )

    closing = "}" if opener == "{" else ")"
    depth = 1
    quote_character: str | None = None
    escaped = False
    for index in range(match.end(), len(statement)):
        character = statement[index]
        if quote_character is not None:
            if escaped:
                escaped = False
            elif character == "\\" and quote_character != "'":
                escaped = True
            elif character == quote_character:
                quote_character = None
            continue
        if character in {'"', "'"}:
            quote_character = character
        elif character == opener:
            depth += 1
        elif character == closing:
            depth -= 1
            if depth == 0:
                return (
                    name,
                    statement[match.end() : index],
                    stdout_redirected(statement[index + 1 :]),
                )
    return None


def _active_variable_name(value: str) -> str | None:
    match = re.fullmatch(
        r"\$(?:\{(?P<braced>[A-Za-z_][A-Za-z0-9_]*)\}|"
        r"(?P<plain>[A-Za-z_][A-Za-z0-9_]*))",
        value,
    )
    return (match.group("braced") or match.group("plain")) if match else None


def _remote_command_alias(name: str, value: str) -> str:
    return _REMOTE_COMMAND_ALIAS_PREFIX + name + "\0" + value


def _remote_command_alias_value(aliases: set[str], name: str) -> str | None:
    prefix = _REMOTE_COMMAND_ALIAS_PREFIX + name + "\0"
    return next(
        (entry[len(prefix) :] for entry in aliases if entry.startswith(prefix)),
        None,
    )


def _remove_remote_command_alias(aliases: set[str], name: str) -> None:
    prefix = _REMOTE_COMMAND_ALIAS_PREFIX + name + "\0"
    aliases.difference_update(
        {entry for entry in aliases if entry.startswith(prefix)}
    )


def _remote_command_alias_expansion(
    aliases: set[str],
    name: str,
) -> tuple[tuple[str, ...] | None, bool]:
    """Expand first-word Bash aliases with a strict symbol/token budget."""

    seen: set[str] = set()
    suffix: tuple[str, ...] = ()
    current = name
    while True:
        if current in seen or len(seen) >= MAX_REMOTE_SHELL_SYMBOLS:
            return None, True
        value = _remote_command_alias_value(aliases, current)
        if value is None:
            return None, bool(seen)
        seen.add(current)
        tokens, complete = _tokenize_shell_line(value)
        if (
            not complete
            or not tokens
            or len(tokens) + len(suffix) > MAX_SHELL_CLASSIFICATION_TOKENS
        ):
            return None, True
        invocation = _command_invocation(tokens)
        if not invocation.complete or invocation.executable_index is None:
            return None, True
        nested_name = _decode_shell_literal_operators(
            invocation.tokens[invocation.executable_index]
        )
        nested_value = _remote_command_alias_value(aliases, nested_name)
        if nested_value is None:
            return tuple(tokens) + suffix, False
        suffix = (
            tuple(invocation.tokens[invocation.executable_index + 1 :]) + suffix
        )
        current = nested_name


def _remote_command_alias_fetch_tokens(
    aliases: set[str],
    name: str,
    arguments: Sequence[str] = (),
) -> tuple[tuple[str, ...] | None, bool]:
    expansion, ambiguous = _remote_command_alias_expansion(aliases, name)
    if expansion is None:
        return None, ambiguous
    combined = tuple(expansion) + tuple(arguments)
    if len(combined) > MAX_SHELL_CLASSIFICATION_TOKENS:
        return None, True
    invocation = _command_invocation(combined)
    if not invocation.complete or invocation.executable_index is None:
        return None, True
    if invocation.executable not in {"curl", "wget"}:
        return None, False
    return combined, False


def _alias_builtin_tokens(tokens: Sequence[str]) -> tuple[str, tuple[str, ...]] | None:
    """Return exact alias/unalias builtins, including bounded wrappers."""

    index = 0
    if tokens and tokens[0] == "command":
        index = 1
        while index < len(tokens) and tokens[index].startswith("-"):
            if tokens[index] == "--":
                index += 1
                break
            if tokens[index] in {"-v", "-V"}:
                return None
            index += 1
    elif tokens and tokens[0] == "builtin":
        index = 1
        if index < len(tokens) and tokens[index] == "--":
            index += 1
    if index >= len(tokens) or tokens[index] not in {"alias", "unalias"}:
        return None
    return tokens[index], tuple(tokens[index + 1 :])


def _alias_value_is_remote_fetcher(value: str) -> bool:
    tokens, complete = _tokenize_shell_line(value)
    if not complete or len(tokens) > MAX_SHELL_CLASSIFICATION_TOKENS:
        return False
    invocation = _command_invocation(tokens)
    return invocation.complete and invocation.executable in {"curl", "wget"}


def _literal_remote_file_path(value: str) -> str | None:
    """Return a bounded, expansion-free shell path for exact flow tracking."""

    decoded = _decode_shell_payload(value).strip()
    if (
        not decoded
        or decoded == "-"
        or len(decoded) > 4_096
        or decoded.startswith("~")
        or any(character in decoded for character in "\0\r\n$`*?[")
        or re.fullmatch(r"%[^%]+%|![^!]+!", decoded) is not None
        or decoded in {"/dev/stdin", "/dev/stdout", "/dev/stderr"}
        or decoded.startswith(("/dev/fd/", "/proc/self/fd/"))
    ):
        return None
    normalized = posixpath.normpath(decoded)
    if normalized.startswith("//"):
        normalized = "/" + normalized.lstrip("/")
    return normalized


def _literal_remote_url_names(arguments: Sequence[str]) -> set[str]:
    """Derive only literal URL basenames; never consult the filesystem/network."""

    names: set[str] = set()
    for argument in arguments:
        decoded = _decode_shell_payload(argument)
        if decoded.startswith("-") or len(decoded) > 4_096:
            continue
        parsed = urlsplit(decoded)
        if parsed.scheme.casefold() not in {"ftp", "http", "https"} or not parsed.netloc:
            continue
        basename = posixpath.basename(parsed.path.rstrip("/"))
        literal = _literal_remote_file_path(basename)
        if literal is not None and literal not in {"", ".", "/"}:
            names.add(literal)
    return names


def _stdout_literal_redirection_target(
    tokens: Sequence[str],
) -> tuple[str | None, bool]:
    """Return the final literal file receiving stdout and whether it is dynamic."""

    target: str | None = None
    ambiguous = False
    index = 0
    while index < len(tokens):
        redirection = tokens[index]
        if (
            _SHELL_REDIRECTION_RE.fullmatch(redirection) is None
            or not _redirection_changes_stdout(redirection)
        ):
            index += 1
            continue
        if re.search(r">&(?:[0-9]+|-)$", redirection) is not None:
            target = None
            ambiguous = False
            index += 1
            continue
        target_index = index + 1
        while target_index < len(tokens) and not tokens[target_index]:
            target_index += 1
        if target_index >= len(tokens):
            return None, True
        target = _literal_remote_file_path(tokens[target_index])
        ambiguous = target is None
        index = target_index + 1
    return target, ambiguous


def _fetch_literal_output_paths(
    statement: str,
    aliases: set[str],
) -> tuple[set[str], bool]:
    """Summarize exact literal files written by one bounded fetch command."""

    tokens, complete = _tokenize_shell_line(statement)
    if not complete or len(tokens) > MAX_SHELL_CLASSIFICATION_TOKENS:
        return set(), False
    invocation = _command_invocation(tokens)
    if not invocation.complete or invocation.executable_index is None:
        return set(), False
    executable_word = _decode_shell_literal_operators(
        invocation.tokens[invocation.executable_index]
    )
    variable_name = _active_variable_name(executable_word)
    executable = invocation.executable
    outputs: set[str] = set()
    ambiguous = False

    def add_target(raw_target: str) -> None:
        nonlocal ambiguous
        if raw_target == "-":
            return
        literal_target = _literal_remote_file_path(raw_target)
        if literal_target is None:
            outputs.add(_REMOTE_FILE_AMBIGUOUS)
        else:
            outputs.add(literal_target)

    alias_fetch_tokens, alias_ambiguous = _remote_command_alias_fetch_tokens(
        aliases,
        executable_word,
        invocation.tokens[invocation.executable_index + 1 :],
    )
    if executable not in {"curl", "wget"} and alias_fetch_tokens is None:
        if alias_ambiguous:
            return {_REMOTE_FILE_AMBIGUOUS}, False
        substitutions, substitutions_complete = _command_substitution_payloads(
            statement
        )
        if not substitutions_complete:
            return set(), _has_remote_fetcher_hint(statement)
        if not any(
            kind == "command" and _has_remote_fetcher_hint(payload)
            for kind, payload in substitutions
        ):
            return set(), False
        redirect_target, redirect_ambiguous = (
            _stdout_literal_redirection_target(tokens)
        )
        if redirect_target is not None:
            outputs.add(redirect_target)
        elif redirect_ambiguous:
            outputs.add(_REMOTE_FILE_AMBIGUOUS)
        return outputs, False

    fetch_tokens = (
        tuple(tokens) if executable in {"curl", "wget"} else alias_fetch_tokens
    )
    if fetch_tokens is None:
        return {_REMOTE_FILE_AMBIGUOUS}, False
    fetch_invocation = _command_invocation(fetch_tokens)
    if (
        not fetch_invocation.complete
        or fetch_invocation.executable_index is None
        or fetch_invocation.executable not in {"curl", "wget"}
    ):
        return set(), True
    executable = fetch_invocation.executable
    arguments = list(
        fetch_invocation.tokens[fetch_invocation.executable_index + 1 :]
    )
    saw_wget_output_selection = False

    index = 0
    while index < len(arguments):
        argument = _decode_shell_literal_operators(arguments[index])
        separated_target = (
            executable == "curl" and argument in {"-o", "--output"}
            or executable == "wget" and argument in {"-O", "--output-document"}
        )
        if separated_target:
            if index + 1 >= len(arguments):
                ambiguous = True
                break
            saw_wget_output_selection = (
                saw_wget_output_selection or executable == "wget"
            )
            add_target(arguments[index + 1])
            index += 2
            continue
        if argument.startswith("--output=") or argument.startswith(
            "--output-document="
        ):
            saw_wget_output_selection = (
                saw_wget_output_selection
                or executable == "wget"
                and argument.startswith("--output-document=")
            )
            add_target(argument.split("=", 1)[1])
        elif (
            executable == "curl"
            and re.fullmatch(r"-o.+", argument) is not None
        ):
            add_target(argument[2:])
        elif (
            executable == "wget"
            and re.fullmatch(r"-O.+", argument) is not None
        ):
            saw_wget_output_selection = True
            add_target(argument[2:])
        elif executable == "wget":
            combined_output = re.fullmatch(r"-[^-]*O(?P<target>.*)", argument)
            if combined_output is not None:
                saw_wget_output_selection = True
                target = combined_output.group("target")
                if target:
                    add_target(target)
                elif index + 1 < len(arguments):
                    add_target(arguments[index + 1])
                    index += 1
                else:
                    ambiguous = True
        elif executable == "curl":
            combined_output = re.fullmatch(r"-[^-]*o(?P<target>.*)", argument)
            if combined_output is not None:
                target = combined_output.group("target")
                if target:
                    add_target(target)
                elif index + 1 < len(arguments):
                    add_target(arguments[index + 1])
                    index += 1
                else:
                    ambiguous = True
        index += 1

    native_names = _literal_remote_url_names(arguments)
    if executable == "wget" and not saw_wget_output_selection:
        outputs.update(native_names or {_REMOTE_FILE_AMBIGUOUS})
    if _fetch_arguments_output_stdout(executable, arguments, tokens):
        redirect_target, _redirect_ambiguous = (
            _stdout_literal_redirection_target(tokens)
        )
        if redirect_target is not None:
            outputs.add(redirect_target)
        elif _redirect_ambiguous:
            outputs.add(_REMOTE_FILE_AMBIGUOUS)
        # This tracker deliberately models literal paths only. Dynamic fd/file
        # destinations remain the responsibility of the descriptor and
        # pipeline classifiers and cannot be correlated to a later exact path.
    elif executable == "curl" and not outputs:
        # Native-name selections (`-O`, `--remote-name`, or remote-name-all)
        # derive a path from remote metadata. Keep a bounded unknown state and
        # emit only if that state later reaches an execution-like consumer.
        if any(
            _decode_shell_literal_operators(argument) == "--remote-header-name"
            for argument in arguments
        ):
            outputs.add(_REMOTE_FILE_AMBIGUOUS)
        else:
            outputs.update(native_names or {_REMOTE_FILE_AMBIGUOUS})
    return outputs, ambiguous


def _remote_file_argument_status(
    arguments: Sequence[str],
    remote_files: set[str],
) -> tuple[bool, bool]:
    """Match exact paths and retain uncertainty for an unknown tracked path."""

    exact_files = remote_files - {_REMOTE_FILE_AMBIGUOUS}
    has_unknown = _REMOTE_FILE_AMBIGUOUS in remote_files
    ambiguous = False
    for argument in arguments:
        decoded = _decode_shell_payload(argument)
        if decoded.startswith("-") and decoded != "-":
            continue
        literal = _literal_remote_file_path(decoded)
        if literal in exact_files:
            return True, ambiguous
        if literal is None and has_unknown:
            ambiguous = True
    return False, ambiguous


def _remote_file_stdin_status(
    tokens: Sequence[str],
    remote_files: set[str],
) -> tuple[bool, bool]:
    exact_files = remote_files - {_REMOTE_FILE_AMBIGUOUS}
    has_unknown = _REMOTE_FILE_AMBIGUOUS in remote_files
    index = 0
    while index < len(tokens):
        redirection = _decode_shell_literal_operators(tokens[index])
        input_match = re.fullmatch(r"(?:0*)<(?![<&])", redirection)
        if input_match is None:
            index += 1
            continue
        target_index = index + 1
        while target_index < len(tokens) and not tokens[target_index]:
            target_index += 1
        if target_index >= len(tokens):
            return False, True
        target = _literal_remote_file_path(tokens[target_index])
        if target in exact_files:
            return True, False
        if target is None and (has_unknown or exact_files):
            return False, True
        if has_unknown:
            return False, True
        index = target_index + 1
    return False, False


def _remote_file_cat_pipeline_status(
    tokens: Sequence[str],
    remote_files: set[str],
) -> tuple[bool, bool]:
    """Classify tracked file bytes read by cat and piped into an interpreter."""

    commands: list[list[str]] = []
    command: list[str] = []
    for token in tokens:
        if token in {"|", "|&"}:
            commands.append(command)
            command = []
        elif token and all(character in "|;&" for character in token):
            if command:
                commands.append(command)
            command = []
        else:
            command.append(token)
    if command:
        commands.append(command)

    for index, candidate in enumerate(commands[:-1]):
        invocation = _command_invocation(candidate)
        if (
            not invocation.complete
            or invocation.executable != "cat"
            or invocation.executable_index is None
        ):
            continue
        matched, ambiguous = _remote_file_argument_status(
            invocation.tokens[invocation.executable_index + 1 :],
            remote_files,
        )
        if not matched and not ambiguous:
            continue
        for downstream in commands[index + 1 :]:
            downstream_invocation = _command_invocation(downstream)
            if not downstream_invocation.complete:
                return False, True
            if downstream_invocation.executable in _COMMAND_INTERPRETERS:
                return (True, False) if matched else (False, True)
            if downstream_invocation.executable not in _NON_EXECUTING_DATA_COMMANDS:
                return False, True
    return False, False


def _remote_file_eval_substitution_status(
    statement: str,
    invocation: _CommandInvocation,
    remote_files: set[str],
) -> tuple[bool, bool]:
    if invocation.executable != "eval":
        return False, False
    substitutions, complete = _command_substitution_payloads(statement)
    if not complete:
        return False, True
    for kind, payload in substitutions:
        if kind != "command":
            continue
        payload_tokens, payload_complete = _tokenize_shell_line(payload)
        if not payload_complete:
            return False, True
        payload_invocation = _command_invocation(payload_tokens)
        if (
            not payload_invocation.complete
            or payload_invocation.executable != "cat"
            or payload_invocation.executable_index is None
        ):
            continue
        matched, ambiguous = _remote_file_argument_status(
            payload_invocation.tokens[payload_invocation.executable_index + 1 :],
            remote_files,
        )
        if matched:
            return True, False
        if ambiguous:
            return False, True
    return False, False


def _pipeline_literal_remote_outputs(
    statement: str,
    aliases: set[str],
    functions: dict[str, str],
) -> tuple[set[str], bool]:
    """Track fetched stdout through bounded data filters into literal tee files."""

    if "|" not in statement or "tee" not in statement:
        return set(), False
    tokens, complete = _tokenize_shell_line(statement)
    if not complete or len(tokens) > MAX_SHELL_CLASSIFICATION_TOKENS:
        return set(), True
    pipelines: list[list[list[str]]] = []
    pipeline: list[list[str]] = []
    command: list[str] = []
    for token in tokens:
        if token in {"|", "|&"}:
            pipeline.append(command)
            command = []
        elif token and all(character in "|;&" for character in token):
            if command:
                pipeline.append(command)
            if pipeline:
                pipelines.append(pipeline)
            pipeline = []
            command = []
        else:
            command.append(token)
    if command:
        pipeline.append(command)
    if pipeline:
        pipelines.append(pipeline)

    outputs: set[str] = set()
    ambiguous = False
    for commands in pipelines:
        remote_flow = False
        for simple_command in commands:
            invocation = _command_invocation(simple_command)
            if not invocation.complete or invocation.executable_index is None:
                ambiguous = ambiguous or remote_flow
                remote_flow = False
                continue
            executable_word = _decode_shell_literal_operators(
                invocation.tokens[invocation.executable_index]
            )
            alias_tokens, alias_ambiguous = _remote_command_alias_fetch_tokens(
                aliases,
                executable_word,
                invocation.tokens[invocation.executable_index + 1 :],
            )
            ambiguous = ambiguous or alias_ambiguous
            if invocation.executable in {"curl", "wget"}:
                remote_flow = _remote_fetch_command_outputs_stdout(simple_command)
                continue
            if alias_tokens is not None:
                alias_invocation = _command_invocation(alias_tokens)
                remote_flow = _fetch_arguments_output_stdout(
                    alias_invocation.executable,
                    alias_invocation.tokens[alias_invocation.executable_index + 1 :],
                    simple_command,
                )
                continue
            if executable_word in functions:
                function_status = _function_outputs_remote_content(
                    functions[executable_word],
                    aliases,
                    functions,
                    frozenset({executable_word}),
                )
                ambiguous = ambiguous or function_status is None
                remote_flow = function_status is True
                continue
            if not remote_flow:
                continue
            if invocation.executable == "tee":
                for argument in invocation.tokens[invocation.executable_index + 1 :]:
                    decoded = _decode_shell_payload(argument)
                    if decoded.startswith("-"):
                        continue
                    target = _literal_remote_file_path(decoded)
                    if target is None:
                        outputs.add(_REMOTE_FILE_AMBIGUOUS)
                    else:
                        outputs.add(target)
                continue
            if invocation.executable not in _NON_EXECUTING_DATA_COMMANDS:
                ambiguous = True
                remote_flow = False
    return outputs, ambiguous


def _literal_remote_file_execution_status(
    statement: str,
    remote_files: set[str],
) -> tuple[bool, bool]:
    """Detect execution of an exact previously fetched path."""

    if not remote_files:
        return False, False
    tokens, complete = _tokenize_shell_line(statement)
    if not complete or len(tokens) > MAX_SHELL_CLASSIFICATION_TOKENS:
        return False, True
    pipeline_detected, pipeline_ambiguous = _remote_file_cat_pipeline_status(
        tokens,
        remote_files,
    )
    if pipeline_detected or pipeline_ambiguous:
        return pipeline_detected, pipeline_ambiguous
    invocation = _command_invocation(tokens)
    if not invocation.complete or invocation.executable_index is None:
        return False, True
    eval_detected, eval_ambiguous = _remote_file_eval_substitution_status(
        statement,
        invocation,
        remote_files,
    )
    if eval_detected or eval_ambiguous:
        return eval_detected, eval_ambiguous
    executable_word = _decode_shell_payload(
        invocation.tokens[invocation.executable_index]
    )
    literal_executable = _literal_remote_file_path(executable_word)
    if literal_executable in remote_files:
        return True, False
    arguments = invocation.tokens[invocation.executable_index + 1 :]
    if invocation.executable in {"cp", "install", "ln", "mv"}:
        transformed, transform_ambiguous = _remote_file_argument_status(
            arguments,
            remote_files,
        )
        if transformed or transform_ambiguous:
            return False, True
    if invocation.executable not in _COMMAND_INTERPRETERS:
        direct_ambiguous = (
            _REMOTE_FILE_AMBIGUOUS in remote_files
            and (
                _token_has_dynamic_execution_hint(executable_word)
                or "/" in executable_word
            )
        )
        return False, direct_ambiguous
    stdin_detected, stdin_ambiguous = _remote_file_stdin_status(
        tokens,
        remote_files,
    )
    if stdin_detected or stdin_ambiguous:
        return stdin_detected, stdin_ambiguous
    ambiguous = False
    has_unknown = _REMOTE_FILE_AMBIGUOUS in remote_files
    for argument in arguments:
        decoded_argument = _decode_shell_payload(argument)
        literal_argument = _literal_remote_file_path(decoded_argument)
        if literal_argument in remote_files:
            return True, False
        ambiguous = ambiguous or _token_has_dynamic_execution_hint(argument)
        if (
            has_unknown
            and not decoded_argument.startswith("-")
            and literal_argument is not None
        ):
            ambiguous = True
    return False, ambiguous


def _literal_remote_file_flow_status(
    command: str,
    remote_files: set[str],
    aliases: set[str],
    functions: dict[str, str],
    depth: int = 0,
) -> tuple[bool, bool]:
    """Track exact fetch-to-file-to-execution flow in lexical order."""

    if depth > 64:
        return False, True
    if len(command) > MAX_SHELL_CLASSIFICATION_CHARS:
        return False, True
    if (
        not remote_files
        and ">" not in command
        and not _has_remote_fetcher_hint(command)
        and re.search(
            r"(?:^|\s)(?:-[oO](?:\s|[^\s])|--output(?:-document)?(?:=|\s))",
            command,
        )
        is None
        and not any(
            re.match(rf"^\s*{re.escape(name)}(?:\s|$)", command) is not None
            for name in functions
        )
        and not any(
            command.lstrip().startswith(name + " ")
            for name in (
                entry[len(_REMOTE_COMMAND_ALIAS_PREFIX) :].split("\0", 1)[0]
                for entry in aliases
                if entry.startswith(_REMOTE_COMMAND_ALIAS_PREFIX)
            )
        )
    ):
        return False, False
    statements, complete = _top_level_shell_statements(command)
    if not complete:
        control_fetch = (
            re.match(
                r"^\s*(?:case|for|if|select|until|while)\b",
                command,
            )
            is not None
            and _has_remote_fetcher_hint(command)
        )
        return False, bool(remote_files) or control_fetch
    local_files = set(remote_files)
    local_functions = dict(functions)
    state_changed = False
    ambiguous = False
    detected = False
    for statement in statements:
        stripped = statement.strip()
        if (
            stripped.startswith("{") and stripped.endswith("}")
            or stripped.startswith("(") and stripped.endswith(")")
        ):
            nested_detected, nested_ambiguous = _literal_remote_file_flow_status(
                stripped[1:-1],
                local_files,
                aliases,
                local_functions,
                depth + 1,
            )
            detected = detected or nested_detected
            ambiguous = ambiguous or nested_ambiguous
            state_changed = state_changed or local_files != remote_files
            continue
        declaration = _function_declaration(statement)
        if declaration is not None:
            function_name, body, stdout_redirected = declaration
            local_functions[function_name] = "" if stdout_redirected else body
            continue
        if re.match(r"^(?:case|for|if|select|until|while)\b", stripped):
            if _has_remote_fetcher_hint(stripped) or local_files:
                ambiguous = True
            continue
        statement_tokens, statement_complete = _tokenize_shell_line(statement)
        if not statement_complete:
            ambiguous = ambiguous or bool(local_files)
            continue
        statement_invocation = _command_invocation(statement_tokens)
        if (
            statement_invocation.complete
            and statement_invocation.executable_index is not None
        ):
            invoked_name = _decode_shell_literal_operators(
                statement_invocation.tokens[statement_invocation.executable_index]
            )
            if invoked_name in local_functions:
                before_function = set(local_files)
                function_detected, function_ambiguous = (
                    _literal_remote_file_flow_status(
                        local_functions[invoked_name],
                        local_files,
                        aliases,
                        local_functions,
                        depth + 1,
                    )
                )
                detected = detected or function_detected
                ambiguous = ambiguous or function_ambiguous
                state_changed = state_changed or local_files != before_function
        execution_detected, execution_ambiguous = (
            _literal_remote_file_execution_status(statement, local_files)
        )
        detected = detected or execution_detected
        ambiguous = ambiguous or execution_ambiguous
        output_paths, output_ambiguous = _fetch_literal_output_paths(
            statement,
            aliases,
        )
        ambiguous = ambiguous or output_ambiguous
        if output_paths:
            local_files.update(output_paths)
            state_changed = True
        pipeline_paths, pipeline_ambiguous = _pipeline_literal_remote_outputs(
            statement,
            aliases,
            local_functions,
        )
        ambiguous = ambiguous or pipeline_ambiguous
        if pipeline_paths:
            local_files.update(pipeline_paths)
            state_changed = True
        if len(local_files) > MAX_REMOTE_SHELL_SYMBOLS:
            remote_files.clear()
            return False, True
    if state_changed and _has_top_level_uncertain_state_separator(command):
        return False, True
    remote_files.clear()
    remote_files.update(local_files)
    return detected, ambiguous


def _function_scoped_declaration(
    statement: str,
) -> tuple[set[str], bool] | None:
    """Return declared names and whether they are local to the current function."""

    tokens, complete = _tokenize_shell_line(statement)
    if not complete or not tokens or tokens[0] not in {"local", "declare", "typeset"}:
        return None
    command = tokens.pop(0)
    force_global = False
    while tokens and tokens[0].startswith("-") and tokens[0] != "-":
        option = tokens.pop(0)
        force_global = force_global or command in {"declare", "typeset"} and "g" in option[1:]
    names: set[str] = set()
    for token in tokens:
        match = re.match(r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)", token)
        if match is None:
            return set(), not force_global
        names.add(match.group("name"))
    return names, not force_global


def _function_literal_heredoc_output_status(body: str) -> bool | None:
    """Classify literal script bytes emitted by a function-local `cat` heredoc."""

    specs = _heredoc_specs(body)
    if specs is None:
        return None
    embedded = _embedded_heredoc_bodies(body, specs)
    if embedded is None:
        return False
    lines = body.splitlines()
    unresolved = False
    for header_index, _body_index, literal_body, _executes in embedded:
        header_tokens, header_complete = _tokenize_shell_line(lines[header_index])
        if not header_complete:
            unresolved = True
            continue
        invocation = _command_invocation(header_tokens)
        if invocation.executable != "cat":
            continue
        stdin_heredocs = [
            token
            for token in header_tokens
            if _SHELL_REDIRECTION_RE.fullmatch(token) is not None
            and (token.endswith("<<") or token.endswith("<<-"))
            and (
                not re.match(r"[0-9]+", token)
                or not re.match(r"[0-9]+", token).group(0).strip("0")
            )
        ]
        if not stdin_heredocs:
            continue
        stdout_route = _stdout_reaches_pipeline(header_tokens)
        if stdout_route is False:
            continue
        if stdout_route is None:
            unresolved = True
        for _line, logical, shell_payload in _logical_shell_commands(
            literal_body,
            True,
            True,
        ):
            detected, unparsed = _remote_pipeline_status(
                logical,
                shell_payload=shell_payload,
            )
            if detected:
                return True
            unresolved = unresolved or unparsed
    return None if unresolved else False


def _function_outputs_remote_content(
    body: str,
    aliases: set[str],
    functions: dict[str, str],
    visited: frozenset[str] = frozenset(),
) -> bool | None:
    if len(body) > DEFAULT_MAX_FILE_BYTES:
        return None
    literal_heredoc_status = _function_literal_heredoc_output_status(body)
    if literal_heredoc_status is True:
        return True
    statements, complete = _top_level_shell_statements(body)
    if not complete:
        return None
    local_aliases = set(aliases)
    local_functions = dict(functions)
    local_names: set[str] = set()
    unresolved = literal_heredoc_status is None
    for statement in statements:
        descriptor_duplication = _remote_descriptor_duplication(statement)
        opened_descriptor, _closed_descriptor, descriptor_ambiguous = (
            _remote_descriptor_update(statement)
        )
        if (
            descriptor_duplication is not None
            or opened_descriptor is not None
            or descriptor_ambiguous
        ):
            unresolved = True
        scoped_declaration = _function_scoped_declaration(statement)
        if scoped_declaration is not None and scoped_declaration[1]:
            declared_names = scoped_declaration[0]
            local_names.update(declared_names)
            for declared_name in declared_names:
                local_aliases.discard(declared_name)
            _update_remote_shell_statement(
                statement,
                local_aliases,
                local_functions,
            )
            continue
        if _update_remote_shell_statement(statement, local_aliases, local_functions):
            continue
        tokens, tokens_complete = _tokenize_shell_line(statement)
        if not tokens_complete or len(tokens) > MAX_SHELL_CLASSIFICATION_TOKENS:
            unresolved = True
            continue
        pipelines: list[list[list[str]]] = []
        pipeline: list[list[str]] = []
        command: list[str] = []

        def finish_pipeline() -> None:
            nonlocal pipeline, command
            if command:
                pipeline.append(command)
            if pipeline:
                pipelines.append(pipeline)
            pipeline = []
            command = []

        for token in tokens:
            if token in {"|", "|&"}:
                pipeline.append(command)
                command = []
            elif token and all(character in "|;&" for character in token):
                finish_pipeline()
            else:
                command.append(token)
        finish_pipeline()

        for pipeline_commands in pipelines:
            remote_flow = False
            for command in pipeline_commands:
                invocation = _command_invocation(command)
                if not invocation.complete or invocation.executable_index is None:
                    unresolved = True
                    remote_flow = False
                    continue
                executable_word = invocation.tokens[invocation.executable_index]
                variable_name = _active_variable_name(executable_word)
                function_name = _decode_shell_literal_operators(executable_word)
                alias_fetch_tokens, alias_ambiguous = (
                    _remote_command_alias_fetch_tokens(
                        local_aliases,
                        function_name,
                        invocation.tokens[invocation.executable_index + 1 :],
                    )
                )
                unresolved = unresolved or alias_ambiguous
                if invocation.executable in {"curl", "wget"}:
                    remote_flow = _remote_fetch_command_outputs_stdout(command)
                elif alias_fetch_tokens is not None:
                    alias_invocation = _command_invocation(alias_fetch_tokens)
                    arguments = alias_invocation.tokens[
                        alias_invocation.executable_index + 1 :
                    ]
                    stdout_route = _stdout_reaches_pipeline(command)
                    remote_flow = (
                        stdout_route is not False
                        and _fetch_arguments_output_stdout(
                            alias_invocation.executable,
                            arguments,
                            command,
                        )
                    )
                    unresolved = unresolved or stdout_route is None
                elif variable_name is not None and variable_name in local_aliases:
                    arguments = invocation.tokens[invocation.executable_index + 1 :]
                    stdout_route = _stdout_reaches_pipeline(command)
                    remote_flow = (
                        stdout_route is not False
                        and _fetch_arguments_output_stdout(None, arguments, command)
                    )
                    unresolved = unresolved or stdout_route is None
                elif function_name in local_functions:
                    if function_name in visited or len(visited) >= 16:
                        unresolved = True
                        remote_flow = False
                        continue
                    nested = _function_outputs_remote_content(
                        local_functions[function_name],
                        local_aliases,
                        local_functions,
                        visited | {function_name},
                    )
                    stdout_route = _stdout_reaches_pipeline(command)
                    remote_flow = nested is True and stdout_route is not False
                    unresolved = unresolved or nested is None or stdout_route is None
                elif remote_flow:
                    stdout_route = _stdout_reaches_pipeline(command)
                    if stdout_route is False:
                        remote_flow = False
                    elif stdout_route is None:
                        unresolved = True
                        remote_flow = False
            if remote_flow:
                return True
    return None if unresolved else False


def _update_remote_shell_statement(
    statement: str,
    aliases: set[str],
    functions: dict[str, str],
) -> bool:
    """Update exact, case-sensitive summaries; return whether it was a declaration."""

    declaration = _function_declaration(statement)
    if declaration is not None:
        name, body, stdout_redirected = declaration
        functions[name] = "" if stdout_redirected else body
        return True

    unset_tokens, unset_complete = _tokenize_shell_line(statement)
    alias_builtin = (
        _alias_builtin_tokens(unset_tokens) if unset_complete else None
    )
    if alias_builtin is not None and alias_builtin[0] == "alias":
        declarations: list[tuple[str, str]] = []
        for token in alias_builtin[1]:
            match = re.fullmatch(
                r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>.*)",
                token,
                re.DOTALL,
            )
            if match is None:
                return False
            declarations.append((match.group("name"), match.group("value")))
        if not declarations:
            return False
        for name, value in declarations:
            _remove_remote_command_alias(aliases, name)
            aliases.add(_remote_command_alias(name, value))
        return True
    if alias_builtin is not None and alias_builtin[0] == "unalias":
        names = [token for token in alias_builtin[1] if token != "--"]
        if names == ["-a"]:
            aliases.difference_update(
                {
                    alias
                    for alias in aliases
                    if alias.startswith(_REMOTE_COMMAND_ALIAS_PREFIX)
                }
            )
            return True
        if not names or any(
            re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None
            for name in names
        ):
            return False
        for name in names:
            _remove_remote_command_alias(aliases, name)
        return True
    if unset_complete and unset_tokens and unset_tokens[0] == "unset":
        unset_variables = True
        unset_functions = False
        names: list[str] = []
        options = True
        for token in unset_tokens[1:]:
            if options and token == "--":
                options = False
                continue
            if options and token.startswith("-") and token != "-":
                flags = token[1:]
                if not flags or any(flag not in "fv" for flag in flags):
                    return False
                unset_functions = unset_functions or "f" in flags
                if "f" in flags and "v" not in flags:
                    unset_variables = False
                if "v" in flags:
                    unset_variables = True
                continue
            options = False
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token) is None:
                return False
            names.append(token)
        if not names:
            return False
        for name in names:
            if unset_variables:
                aliases.discard(name)
            if unset_functions:
                functions.pop(name, None)
        return True

    tokens, complete = _tokenize_shell_line(statement)
    if not complete or len(tokens) > MAX_SHELL_CLASSIFICATION_TOKENS:
        return False
    while tokens and tokens[0] in {
        "(", "{", "!", "do", "elif", "else", "if", "then", "until", "while",
    }:
        tokens.pop(0)
    if tokens and tokens[0] in {"declare", "export", "local", "readonly", "typeset"}:
        tokens.pop(0)
        while tokens and tokens[0].startswith("-"):
            tokens.pop(0)
    assignments: list[tuple[str, str]] = []
    for token in tokens:
        match = re.fullmatch(
            r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>.*)",
            token,
            re.DOTALL,
        )
        if match is None:
            return False
        assignments.append((match.group("name"), match.group("value")))
    if not assignments:
        return False
    for name, value in assignments:
        if _normalized_executable_name(value) in {"curl", "wget"}:
            aliases.add(name)
        else:
            aliases.discard(name)
    return True


def _apply_function_alias_effects(
    statement: str,
    aliases: set[str],
    functions: dict[str, str],
    visited: frozenset[str] = frozenset(),
) -> bool | None:
    """Apply straight-line global alias effects from a simple function call."""

    tokens, complete = _tokenize_shell_line(statement)
    if (
        not complete
        or len(tokens) > MAX_SHELL_CLASSIFICATION_TOKENS
        or any(token and all(character in "|;&" for character in token) for token in tokens)
    ):
        return False
    invocation = _command_invocation(tokens)
    if not invocation.complete or invocation.executable_index is None:
        return None
    function_name = _decode_shell_literal_operators(
        invocation.tokens[invocation.executable_index]
    )
    if function_name not in functions:
        return False
    if function_name in visited or len(visited) >= 16:
        return None
    body_statements, body_complete = _top_level_shell_statements(functions[function_name])
    if not body_complete:
        return None
    outer_aliases = set(aliases)
    local_aliases = set(aliases)
    local_functions = dict(functions)
    local_names: set[str] = set()
    for body_statement in body_statements:
        stripped = body_statement.strip()
        descriptor_duplication = _remote_descriptor_duplication(stripped)
        opened_descriptor, _closed_descriptor, descriptor_ambiguous = (
            _remote_descriptor_update(stripped)
        )
        if (
            descriptor_duplication is not None
            or opened_descriptor is not None
            or descriptor_ambiguous
        ):
            return None
        if re.match(r"^(?:case|for|if|select|until|while)\b", stripped):
            return None
        scoped_declaration = _function_scoped_declaration(stripped)
        if scoped_declaration is not None and scoped_declaration[1]:
            declared_names = scoped_declaration[0]
            local_names.update(declared_names)
            for declared_name in declared_names:
                local_aliases.discard(declared_name)
            _update_remote_shell_statement(
                stripped,
                local_aliases,
                local_functions,
            )
            continue
        if _update_remote_shell_statement(stripped, local_aliases, local_functions):
            continue
        nested = _apply_function_alias_effects(
            stripped,
            local_aliases,
            local_functions,
            visited | {function_name},
        )
        if nested is None:
            return None
    committed_aliases = set(outer_aliases)
    for name in outer_aliases | local_aliases:
        if name in local_names:
            continue
        if name in local_aliases:
            committed_aliases.add(name)
        else:
            committed_aliases.discard(name)
    aliases.clear()
    aliases.update(committed_aliases)
    return True


def _dynamic_remote_pipeline_status(
    command: str,
    aliases: set[str],
    functions: dict[str, str],
) -> tuple[bool, bool]:
    """Classify known fetch aliases/functions feeding literal or dynamic shells."""

    if "|" not in command or (not aliases and not functions):
        return False, False
    tokens, complete = _tokenize_shell_line(command)
    if not complete or len(tokens) > MAX_SHELL_CLASSIFICATION_TOKENS:
        return False, True
    pipelines: list[list[list[str]]] = []
    pipeline: list[list[str]] = []
    simple_command: list[str] = []

    def finish_pipeline() -> None:
        nonlocal pipeline, simple_command
        if simple_command:
            pipeline.append(simple_command)
        if pipeline:
            pipelines.append(pipeline)
        pipeline = []
        simple_command = []

    for token in tokens:
        if token in {"|", "|&"}:
            pipeline.append(simple_command)
            simple_command = []
        elif token and all(character in "|;&" for character in token):
            finish_pipeline()
        else:
            simple_command.append(token)
    finish_pipeline()

    for commands in pipelines:
        names = [_shell_command_name(item) for item in commands]
        for index, item in enumerate(commands):
            invocation = _command_invocation(item)
            executable_word = (
                invocation.tokens[invocation.executable_index]
                if invocation.complete and invocation.executable_index is not None
                else ""
            )
            variable_name = _active_variable_name(executable_word)
            function_name = _decode_shell_literal_operators(executable_word)
            alias_fetch_tokens, alias_ambiguous = (
                _remote_command_alias_fetch_tokens(
                    aliases,
                    function_name,
                    invocation.tokens[invocation.executable_index + 1 :]
                    if invocation.complete and invocation.executable_index is not None
                    else (),
                )
            )
            function_status = (
                _function_outputs_remote_content(
                    functions[function_name],
                    aliases,
                    functions,
                    frozenset({function_name}),
                )
                if function_name in functions
                else False
            )
            is_remote_source = (
                invocation.executable in {"curl", "wget"}
                or function_status is True
                or alias_fetch_tokens is not None
                or (
                    variable_name is not None and variable_name in aliases
                )
            )
            ambiguous_source = alias_ambiguous or function_status is None or (
                not is_remote_source
                and invocation.executable not in _NON_EXECUTING_DATA_COMMANDS
                and any(
                    (_active_variable_name(token) in aliases)
                    for token in invocation.tokens
                )
            )
            if not is_remote_source and not ambiguous_source:
                continue
            for later_item, later_name in zip(commands[index + 1 :], names[index + 1 :]):
                if is_remote_source and later_name in _COMMAND_INTERPRETERS:
                    return True, False
                if later_name in _NON_EXECUTING_DATA_COMMANDS:
                    continue
                return False, True
    return False, False


def _ordered_dynamic_remote_status(
    command: str,
    aliases: set[str],
    functions: dict[str, str],
    depth: int = 0,
) -> tuple[bool, bool]:
    """Apply declarations and uses in lexical order within one logical command."""

    if depth > 64:
        return False, True

    declaration_prefix = (
        _FUNCTION_DECLARATION_RE.match(command) is not None
        or re.search(
            r"^\s*(?:(?:declare|export|local|readonly|typeset)(?:\s+-[^\s]+)*\s+)?"
            r"[A-Za-z_][A-Za-z0-9_]*=",
            command,
        )
        is not None
        or re.search(
            r"(?:^|[\s;({])[A-Za-z_][A-Za-z0-9_]*=",
            command,
        )
        is not None
        or re.match(
            r"^\s*(?:(?:command|builtin)(?:\s+--)?\s+)?"
            r"(?:alias|unalias|unset)(?:\s|$)",
            command,
        )
        is not None
    )
    if not aliases and not functions:
        if not declaration_prefix:
            return False, False
    statements, complete = _top_level_shell_statements(command)
    if not complete:
        return False, True
    if _has_top_level_uncertain_state_separator(command):
        probe_aliases = set(aliases)
        probe_functions = dict(functions)
        for statement in statements:
            before_aliases = set(probe_aliases)
            before_functions = dict(probe_functions)
            if _update_remote_shell_statement(
                statement,
                probe_aliases,
                probe_functions,
            ):
                return False, True
            effect_status = _apply_function_alias_effects(
                statement,
                probe_aliases,
                probe_functions,
            )
            if effect_status is None or (
                effect_status
                and (
                    probe_aliases != before_aliases
                    or probe_functions != before_functions
                )
            ):
                return False, True
    saw_unparsed = False
    for statement in statements:
        stripped_statement = statement.strip()
        if stripped_statement.startswith("{") and stripped_statement.endswith("}"):
            detected, unparsed = _ordered_dynamic_remote_status(
                stripped_statement[1:-1],
                aliases,
                functions,
                depth + 1,
            )
            if detected:
                return True, False
            saw_unparsed = saw_unparsed or unparsed
            continue
        if stripped_statement.startswith("(") and stripped_statement.endswith(")"):
            detected, unparsed = _ordered_dynamic_remote_status(
                stripped_statement[1:-1],
                set(aliases),
                dict(functions),
                depth + 1,
            )
            if detected:
                return True, False
            saw_unparsed = saw_unparsed or unparsed
            continue
        if _update_remote_shell_statement(statement, aliases, functions):
            if len(aliases) + len(functions) > MAX_REMOTE_SHELL_SYMBOLS:
                aliases.clear()
                functions.clear()
                return False, True
            continue
        effect_status = _apply_function_alias_effects(
            statement,
            aliases,
            functions,
        )
        if effect_status is None:
            return False, True
        if effect_status:
            continue
        detected, unparsed = _dynamic_remote_pipeline_status(
            statement,
            aliases,
            functions,
        )
        if detected:
            return True, False
        saw_unparsed = saw_unparsed or unparsed
    return False, saw_unparsed


def _remote_pipeline_status(
    command: str,
    depth: int = 0,
    shell_payload: bool = False,
) -> tuple[bool, bool]:
    """Return (detected, unparsed) for a bounded shell-like command string."""

    if command == _SHELL_UNPARSED_SENTINEL:
        return False, True
    contexts = _contextual_shell_commands(command)
    normalized_input = command.strip()
    if contexts != [normalized_input]:
        for context in contexts:
            detected, unparsed = _remote_pipeline_status(context, depth, shell_payload)
            if detected or unparsed:
                return detected, unparsed
        return False, False
    command = normalized_input
    if not _has_remote_execution_syntax(command):
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
    if not _has_remote_fetcher_hint(command):
        return False, _tokens_have_dynamic_source_pipeline(tokens)
    if tokens and tokens[-1] in {"|", "|&", "||"}:
        return False, True
    invocation = _command_invocation(tokens)
    if invocation.complete and invocation.executable_index is not None:
        executable_word = invocation.tokens[invocation.executable_index]
        if (
            invocation.executable not in _COMMAND_INTERPRETERS
            and _token_has_interpreter_hint(executable_word)
        ):
            arguments = invocation.tokens[invocation.executable_index + 1 :]
            for index, argument in enumerate(arguments[:-1]):
                if argument.casefold() not in {"-c", "/c"}:
                    continue
                payload = _decode_shell_literal_operators(arguments[index + 1])
                payload_detected, payload_unparsed = _remote_pipeline_status(
                    payload,
                    depth + 1,
                    True,
                )
                if payload_detected or payload_unparsed:
                    return False, True
                break
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
    executable_substitution = False
    for simple_command in simple_commands:
        simple_invocation = _command_invocation(simple_command)
        if (
            simple_invocation.complete
            and simple_invocation.executable_index is not None
        ):
            executable_word = simple_invocation.tokens[
                simple_invocation.executable_index
            ]
            if "$(" in executable_word or "`" in executable_word:
                executable_substitution = True
                break
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
            shell_payload
            or executable_substitution
            or (outer_has_shell and "<<<" in command)
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
        detected, unparsed = _ordered_dynamic_remote_status(payload, set(), {})
        if detected or unparsed:
            return detected, unparsed
    for _kind, payload in substitutions:
        detected, unparsed = _remote_pipeline_status(payload, depth + 1, False)
        if detected or unparsed:
            return detected, unparsed
    return False, False


@dataclasses.dataclass
class _PendingShellFunction:
    start_line: int
    parts: list[str]
    character_count: int
    brace_depth: int
    awaiting_brace: bool
    quote_character: str | None = None
    escaped: bool = False
    invalid: bool = False
    overflow: bool = False

    def append(self, fragment: str) -> bool:
        self.character_count += len(fragment) + 1
        if self.character_count > DEFAULT_MAX_FILE_BYTES:
            self.overflow = True
        if not self.overflow:
            self.parts.append(fragment)
        index = 0
        if self.awaiting_brace:
            while index < len(fragment) and fragment[index].isspace():
                index += 1
            if index >= len(fragment):
                return False
            if fragment[index] != "{":
                self.invalid = True
                return False
            self.awaiting_brace = False
            self.brace_depth = 1
            index += 1
        while index < len(fragment):
            character = fragment[index]
            if self.escaped:
                self.escaped = False
            elif self.quote_character is not None:
                if character == "\\" and self.quote_character != "'":
                    self.escaped = True
                elif character == self.quote_character:
                    self.quote_character = None
            elif character in {'"', "'"}:
                self.quote_character = character
            elif character == "\\":
                self.escaped = True
            elif character == "{":
                self.brace_depth += 1
            elif character == "}":
                self.brace_depth -= 1
                if self.brace_depth < 0:
                    self.invalid = True
                    return False
                if self.brace_depth == 0:
                    return True
            index += 1
        return False


def _start_pending_shell_function(
    command: str,
    start_line: int,
) -> tuple[_PendingShellFunction | None, bool]:
    if _function_declaration(command) is not None:
        return (
            _PendingShellFunction(
                start_line,
                [command],
                len(command),
                0,
                False,
            ),
            True,
        )
    declaration = _FUNCTION_DECLARATION_RE.match(command)
    if declaration is not None and declaration.group("opener") == "{":
        pending = _PendingShellFunction(
            start_line,
            [command],
            len(command),
            1,
            False,
        )
        completed = pending.append(command[declaration.end() :])
        # append() stores only the suffix when not told otherwise; retain one
        # canonical copy of the complete source for the eventual parser.
        pending.parts = [command]
        pending.character_count = len(command)
        return pending, completed
    if _FUNCTION_HEADER_ONLY_RE.fullmatch(command) is not None:
        return (
            _PendingShellFunction(
                start_line,
                [command],
                len(command),
                0,
                True,
            ),
            False,
        )
    return None, False


def _canonical_remote_descriptor(value: str) -> str:
    if value.startswith("{") and value.endswith("}"):
        return "v:" + value[1:-1]
    return str(int(value))


def _remote_descriptor_duplication(
    command: str,
) -> tuple[str, str | None, bool, bool] | None:
    """Return (destination, source, move, ambiguous) for exec fd duplication."""

    prefix = (
        r"\s*(?:[A-Za-z_][A-Za-z0-9_]*=[^\s;]+\s+)*"
        r"(?:command(?:\s+--)?\s+)?exec\s+"
    )
    match = re.fullmatch(
        prefix
        + r"(?P<destination>[0-9]{0,4}|\{[A-Za-z_][A-Za-z0-9_]*\})"
        + r">&(?P<source>-|[0-9]{1,4}|\$[A-Za-z_][A-Za-z0-9_]*|"
        + r"\$\{[A-Za-z_][A-Za-z0-9_]*\})(?P<move>-)?\s*",
        command,
    )
    if match is None:
        if re.match(prefix, command) and re.search(r">&\s*[$`]", command):
            return "1", None, False, True
        return None
    destination = _canonical_remote_descriptor(match.group("destination") or "1")
    source = match.group("source")
    if source == "-":
        return destination, None, False, False
    if source.isdigit():
        canonical_source = _canonical_remote_descriptor(source)
    else:
        variable = source[2:-1] if source.startswith("${") else source[1:]
        canonical_source = "v:" + variable
    return destination, canonical_source, bool(match.group("move")), False


def _remote_descriptor_update(command: str) -> tuple[str | None, str | None, bool]:
    """Return (opened, closed, ambiguous) for bounded exec descriptor wiring."""

    command_tokens, command_complete = _tokenize_shell_line(command)
    if command_complete:
        command_invocation = _command_invocation(command_tokens)
        if command_invocation.executable == "eval" and any(
            re.search(
                r"\bexec\b[^;\n]{0,512}>\s*>\(",
                _decode_shell_payload(argument),
            )
            for argument in command_invocation.tokens[
                (command_invocation.executable_index or 0) + 1 :
            ]
        ):
            return None, None, True

    exec_prefix = r"(?:command(?:\s+--)?\s+)?exec"
    descriptor_pattern = r"(?:[0-9]{1,4}|\{[A-Za-z_][A-Za-z0-9_]*\})"
    assignment_prefix = r"(?:[A-Za-z_][A-Za-z0-9_]*=[^\s;]+\s+)*"
    rewire_match = re.match(
        rf"\s*{assignment_prefix}{exec_prefix}\s+(?P<fd>{descriptor_pattern})?"
        rf"(?:&>>?|>>?|>&)",
        command,
    )
    if rewire_match is None:
        return None, None, False
    descriptor = _canonical_remote_descriptor(rewire_match.group("fd") or "1")
    open_match = re.fullmatch(
        rf"\s*{assignment_prefix}{exec_prefix}\s+"
        rf"(?P<fd>{descriptor_pattern})?(?:&>>?|>>?)\s*>\((?P<payload>.*)\)"
        rf"(?P<suffix>\s+.*)?\s*",
        command,
        re.DOTALL,
    )
    if open_match is None:
        return None, descriptor, ">(" in command
    suffix = open_match.group("suffix") or ""
    suffix_is_simple_redirection = re.fullmatch(
        r"(?:\s+(?:[0-9]{0,4}|&)?(?:>>?|<<?|<>|>&|<&)\s*[^\s;|&()]+)*\s*",
        suffix,
    ) is not None
    payload_tokens, complete = _tokenize_shell_line(open_match.group("payload"))
    if not complete or len(payload_tokens) > MAX_SHELL_CLASSIFICATION_TOKENS:
        return None, descriptor, True
    saw_unknown = False
    for simple_command in _simple_shell_commands(payload_tokens):
        invocation = _command_invocation(simple_command)
        if not invocation.complete or invocation.executable_index is None:
            saw_unknown = True
            continue
        executable_word = invocation.tokens[invocation.executable_index]
        if invocation.executable in _COMMAND_INTERPRETERS:
            return descriptor, descriptor, not suffix_is_simple_redirection
        if invocation.executable in _NON_EXECUTING_DATA_COMMANDS:
            continue
        if _token_has_dynamic_execution_hint(executable_word):
            saw_unknown = True
        else:
            saw_unknown = True
    return None, descriptor, saw_unknown or not suffix_is_simple_redirection


def _remote_descriptor_followup_operations(
    command: str,
) -> tuple[list[tuple[str, str | None, bool]], bool]:
    """Parse ordered redirections following a process-substitution descriptor."""

    exec_prefix = r"(?:command(?:\s+--)?\s+)?exec"
    descriptor_pattern = r"(?:[0-9]{1,4}|\{[A-Za-z_][A-Za-z0-9_]*\})"
    assignment_prefix = r"(?:[A-Za-z_][A-Za-z0-9_]*=[^\s;]+\s+)*"
    match = re.fullmatch(
        rf"\s*{assignment_prefix}{exec_prefix}\s+"
        rf"(?P<fd>{descriptor_pattern})?(?:&>>?|>>?)\s*>\((?P<payload>.*)\)"
        rf"(?P<suffix>\s+.*)?\s*",
        command,
        re.DOTALL,
    )
    if match is None or not (match.group("suffix") or "").strip():
        return [], False
    tokens, complete = _tokenize_shell_line(match.group("suffix"))
    if not complete or len(tokens) > MAX_SHELL_CLASSIFICATION_TOKENS:
        return [], True

    operations: list[tuple[str, str | None, bool]] = []
    index = 0
    while index < len(tokens):
        token = _decode_shell_literal_operators(tokens[index])
        if not token:
            index += 1
            continue
        duplication = re.fullmatch(
            r"(?P<destination>[0-9]{0,4}|\{[A-Za-z_][A-Za-z0-9_]*\})"
            r">&(?P<source>-|[0-9]{1,4}|\$[A-Za-z_][A-Za-z0-9_]*|"
            r"\$\{[A-Za-z_][A-Za-z0-9_]*\})(?P<move>-)?",
            token,
        )
        if duplication is not None:
            destination = _canonical_remote_descriptor(
                duplication.group("destination") or "1"
            )
            source_word = duplication.group("source")
            if source_word == "-":
                source = None
            elif source_word.isdigit():
                source = _canonical_remote_descriptor(source_word)
            else:
                variable = (
                    source_word[2:-1]
                    if source_word.startswith("${")
                    else source_word[1:]
                )
                source = "v:" + variable
            operations.append(
                (destination, source, bool(duplication.group("move")))
            )
            index += 1
            continue
        output = re.fullmatch(
            r"(?P<all>&)?(?P<destination>[0-9]{0,4}|"
            r"\{[A-Za-z_][A-Za-z0-9_]*\})?(?:>>?|>\|)",
            token,
        )
        if output is not None:
            target_index = index + 1
            while target_index < len(tokens) and not tokens[target_index]:
                target_index += 1
            if target_index >= len(tokens):
                return operations, True
            target = _decode_shell_literal_operators(tokens[target_index])
            if target.startswith(">(") or target == ">":
                return operations, True
            if output.group("all"):
                operations.extend((("1", None, False), ("2", None, False)))
            else:
                operations.append(
                    (
                        _canonical_remote_descriptor(
                            output.group("destination") or "1"
                        ),
                        None,
                        False,
                    )
                )
            index = target_index + 1
            continue
        if _SHELL_REDIRECTION_RE.fullmatch(token) is not None:
            index += 2
            continue
        return operations, True
    return operations, False


def _descriptor_variable_invalidations(command: str) -> set[str]:
    """Return named descriptor variables overwritten by a pure state command."""

    statements, complete = _top_level_shell_statements(command)
    if not complete or not statements:
        return set()
    names: set[str] = set()
    for statement in statements:
        tokens, tokens_complete = _tokenize_shell_line(statement)
        if not tokens_complete or not tokens:
            return set()
        if tokens[0] == "unset":
            for token in tokens[1:]:
                if token == "--" or token.startswith("-"):
                    continue
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token) is None:
                    return set()
                names.add(token)
            continue
        if tokens[0] in {"declare", "export", "local", "readonly", "typeset"}:
            tokens.pop(0)
            while tokens and tokens[0].startswith("-"):
                tokens.pop(0)
        if not tokens:
            return set()
        for token in tokens:
            assignment = re.fullmatch(
                r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)=.*",
                token,
                re.DOTALL,
            )
            if assignment is None:
                return set()
            names.add(assignment.group("name"))
    return names


def _remote_source_redirects_to_descriptor(
    command: str,
    descriptors: set[str],
    aliases: set[str],
    functions: dict[str, str],
) -> tuple[bool, bool]:
    if not descriptors:
        return False, False
    tokens, complete = _tokenize_shell_line(command)
    if not complete or len(tokens) > MAX_SHELL_CLASSIFICATION_TOKENS:
        return False, True

    def target_status(target: str) -> bool | None:
        decoded = _decode_shell_literal_operators(target).strip().strip('"\'')
        if decoded.isdigit():
            return str(int(decoded)) in descriptors
        if decoded == "/dev/stdout":
            return "1" in descriptors
        if decoded == "/dev/stderr":
            return "2" in descriptors
        if decoded == "/dev/stdin":
            return "0" in descriptors
        path_variable_match = re.fullmatch(
            r"/(?:dev|proc/self)/fd/\$(?:\{(?P<braced>[A-Za-z_][A-Za-z0-9_]*)\}|"
            r"(?P<plain>[A-Za-z_][A-Za-z0-9_]*))",
            decoded,
        )
        if path_variable_match is not None:
            name = (
                path_variable_match.group("braced")
                or path_variable_match.group("plain")
            )
            return True if "v:" + name in descriptors else None
        variable_match = re.fullmatch(
            r"\$(?:\{(?P<braced>[A-Za-z_][A-Za-z0-9_]*)\}|"
            r"(?P<plain>[A-Za-z_][A-Za-z0-9_]*))",
            decoded,
        )
        if variable_match is not None:
            name = variable_match.group("braced") or variable_match.group("plain")
            if "v:" + name in descriptors:
                return True
            return None
        if decoded.startswith(("$", "`")) or "$" in decoded:
            return None
        path_match = re.fullmatch(
            r"/(?:dev|proc/self)/(?:fd/)?(?P<fd>[0-9]+)", decoded
        )
        if path_match is not None:
            return str(int(path_match.group("fd"))) in descriptors
        return False

    def fetch_output_descriptor_status(
        executable: str | None,
        arguments: Sequence[str],
    ) -> tuple[bool, bool]:
        ambiguous = False
        decoded_arguments = [
            _decode_shell_literal_operators(argument) for argument in arguments
        ]
        index = 0
        while index < len(decoded_arguments):
            argument = decoded_arguments[index]
            target: str | None = None
            if argument in {"-o", "--output", "-O", "--output-document"}:
                if index + 1 >= len(decoded_arguments):
                    ambiguous = True
                    break
                target = decoded_arguments[index + 1]
                index += 1
            elif argument.startswith(("--output=", "--output-document=")):
                target = argument.split("=", 1)[1]
            elif (
                executable in {None, "curl"}
                and argument.startswith("-o")
                and len(argument) > 2
            ):
                target = argument[2:]
            elif (
                executable in {None, "wget"}
                and argument.startswith("-O")
                and len(argument) > 2
            ):
                target = argument[2:]
            if target is not None:
                status = target_status(target)
                if status is True:
                    return True, ambiguous
                ambiguous = ambiguous or status is None
            index += 1
        return False, ambiguous

    def stdout_redirect_status(simple_command: Sequence[str]) -> tuple[bool, bool]:
        ambiguous = False
        index = 0
        while index < len(simple_command):
            token = _decode_shell_literal_operators(simple_command[index])
            duplication = re.fullmatch(
                r"(?:(?P<source>[0-9]+))?>&(?P<target>.*)", token
            )
            if duplication is not None:
                source = duplication.group("source")
                if source is None or (source.lstrip("0") or "0") == "1":
                    target = duplication.group("target")
                    if not target and index + 1 < len(simple_command):
                        index += 1
                        target = simple_command[index]
                    status = target_status(target)
                    if status is True:
                        return True, ambiguous
                    ambiguous = ambiguous or status is None
            output_path = re.fullmatch(
                r"(?:(?P<source>[0-9]+))?>(?P<target>/(?:dev|proc/self)/.*)",
                token,
            )
            if output_path is not None:
                source = output_path.group("source")
                if source is None or (source.lstrip("0") or "0") == "1":
                    status = target_status(output_path.group("target"))
                    if status is True:
                        return True, ambiguous
                    ambiguous = ambiguous or status is None
            index += 1
        return False, ambiguous

    def redirects_stdin(simple_command: Sequence[str]) -> bool:
        for token in simple_command:
            if _SHELL_REDIRECTION_RE.fullmatch(token) is None:
                continue
            descriptor_match = re.match(
                r"(?:[0-9]+|\{[A-Za-z_][A-Za-z0-9_]*\})?", token
            )
            descriptor = descriptor_match.group(0) if descriptor_match else ""
            suffix = token[len(descriptor) :]
            if suffix.startswith("<") and (
                not descriptor
                or (
                    descriptor.isdigit()
                    and (descriptor.lstrip("0") or "0") == "0"
                )
            ):
                return True
        return False

    def tee_target_status(simple_command: Sequence[str], start: int) -> tuple[bool, bool]:
        ambiguous_target = False
        for argument in simple_command[start:]:
            decoded = _decode_shell_literal_operators(argument)
            if decoded.startswith("-"):
                continue
            status = target_status(decoded)
            if status is True:
                return True, ambiguous_target
            ambiguous_target = ambiguous_target or status is None
        return False, ambiguous_target

    pipelines: list[list[list[str]]] = []
    pipeline: list[list[str]] = []
    simple_command: list[str] = []

    def finish_pipeline() -> None:
        nonlocal pipeline, simple_command
        if simple_command:
            pipeline.append(simple_command)
        if pipeline:
            pipelines.append(pipeline)
        pipeline = []
        simple_command = []

    for token in tokens:
        if token in {"|", "|&"}:
            pipeline.append(simple_command)
            simple_command = []
        elif token and all(character in "|;&" for character in token):
            finish_pipeline()
        else:
            simple_command.append(token)
    finish_pipeline()

    ambiguous = False
    for pipeline_commands in pipelines:
        remote_flow = False
        for simple_command in pipeline_commands:
            invocation = _command_invocation(simple_command)
            if not invocation.complete or invocation.executable_index is None:
                ambiguous = ambiguous or remote_flow
                remote_flow = False
                continue
            executable_word = invocation.tokens[invocation.executable_index]
            variable_name = _active_variable_name(executable_word)
            function_name = _decode_shell_literal_operators(executable_word)
            alias_fetch_tokens, alias_ambiguous = (
                _remote_command_alias_fetch_tokens(
                    aliases,
                    function_name,
                    invocation.tokens[invocation.executable_index + 1 :],
                )
            )
            function_status = (
                _function_outputs_remote_content(
                    functions[function_name],
                    aliases,
                    functions,
                    frozenset({function_name}),
                )
                if function_name in functions
                else False
            )
            ambiguous = ambiguous or alias_ambiguous or function_status is None

            if remote_flow:
                if redirects_stdin(simple_command):
                    remote_flow = False
                else:
                    redirected, redirect_ambiguous = stdout_redirect_status(
                        simple_command
                    )
                    if redirected:
                        return True, ambiguous
                    ambiguous = ambiguous or redirect_ambiguous
                    if invocation.executable == "tee":
                        tee_detected, tee_ambiguous = tee_target_status(
                            simple_command,
                            invocation.executable_index + 1,
                        )
                        if tee_detected:
                            return True, ambiguous
                        ambiguous = ambiguous or tee_ambiguous
                    stdout_route = _stdout_reaches_pipeline(simple_command)
                    if stdout_route is False:
                        remote_flow = False
                    elif stdout_route is None:
                        ambiguous = True
                        remote_flow = False
                    elif invocation.executable in _COMMAND_INTERPRETERS:
                        return True, ambiguous
                    elif invocation.executable in _NON_EXECUTING_DATA_COMMANDS:
                        remote_flow = True
                    else:
                        ambiguous = True
                        remote_flow = False

            output_to_descriptor = False
            output_ambiguous = False
            if invocation.executable in {"curl", "wget"}:
                arguments = invocation.tokens[invocation.executable_index + 1 :]
                output_to_descriptor, output_ambiguous = (
                    fetch_output_descriptor_status(invocation.executable, arguments)
                )
                remote_stdout = _fetch_arguments_output_stdout(
                    invocation.executable,
                    arguments,
                    simple_command,
                )
            elif alias_fetch_tokens is not None:
                alias_invocation = _command_invocation(alias_fetch_tokens)
                arguments = alias_invocation.tokens[
                    alias_invocation.executable_index + 1 :
                ]
                output_to_descriptor, output_ambiguous = (
                    fetch_output_descriptor_status(
                        alias_invocation.executable,
                        arguments,
                    )
                )
                remote_stdout = _fetch_arguments_output_stdout(
                    alias_invocation.executable,
                    arguments,
                    simple_command,
                )
            elif variable_name is not None and variable_name in aliases:
                arguments = invocation.tokens[invocation.executable_index + 1 :]
                output_to_descriptor, output_ambiguous = (
                    fetch_output_descriptor_status(None, arguments)
                )
                remote_stdout = _fetch_arguments_output_stdout(
                    None,
                    arguments,
                    simple_command,
                )
            else:
                remote_stdout = function_status is True
            if output_to_descriptor:
                return True, ambiguous
            ambiguous = ambiguous or output_ambiguous
            if not remote_stdout:
                continue
            redirected, redirect_ambiguous = stdout_redirect_status(simple_command)
            if redirected:
                return True, ambiguous
            ambiguous = ambiguous or redirect_ambiguous
            stdout_route = _stdout_reaches_pipeline(simple_command)
            if "1" in descriptors and stdout_route is not False:
                return True, ambiguous
            ambiguous = ambiguous or stdout_route is None
            remote_flow = stdout_route is not False
    return False, ambiguous


def _remote_fetching_heredoc_output_lines(text: str) -> list[int]:
    """Fail closed when an executing heredoc writes fetched bytes to a file."""

    lines = text.splitlines()
    unparsed: list[int] = []
    index = 0
    while index < len(lines):
        header = lines[index]
        specifications = _heredoc_specs(header)
        if not specifications:
            index += 1
            continue
        header_tokens, header_complete = _tokenize_shell_line(header)
        if not header_complete:
            index += 1
            continue
        output_target, output_ambiguous = _stdout_literal_redirection_target(
            header_tokens
        )
        cursor = index + 1
        relevant = False
        complete = True
        for delimiter, strip_tabs, executes in specifications:
            body: list[str] = []
            while cursor < len(lines):
                comparison = (
                    lines[cursor].lstrip("\t") if strip_tabs else lines[cursor]
                )
                if comparison == delimiter:
                    cursor += 1
                    break
                body.append(comparison)
                cursor += 1
            else:
                complete = False
                break
            if executes and _has_remote_fetcher_hint("\n".join(body)):
                relevant = True
        if (
            complete
            and relevant
            and (output_target is not None or output_ambiguous)
        ):
            unparsed.append(index + 1)
        index = max(index + 1, cursor)
    return unparsed


def _remote_pipe_line_numbers(
    text: str,
    *,
    structural_multiline: bool = True,
) -> tuple[list[int], list[int]]:
    if not _has_remote_fetcher_hint(text):
        return [], []
    findings: list[int] = []
    unparsed: list[int] = (
        _remote_fetching_heredoc_output_lines(text)
        if structural_multiline
        else []
    )
    for command_source in (
        _logical_shell_commands(text, structural_multiline=structural_multiline),
        _yaml_folded_shell_commands(text),
    ):
        remote_aliases: set[str] = set()
        remote_functions: dict[str, str] = {}
        remote_descriptors: set[str] = set()
        remote_files: set[str] = set()
        pending_function: _PendingShellFunction | None = None
        previous_shell_payload: bool | None = None
        for start_line, logical_command, shell_payload in command_source:
            if not structural_multiline:
                remote_aliases.clear()
                remote_functions.clear()
                remote_descriptors.clear()
                remote_files.clear()
                pending_function = None
            if (
                previous_shell_payload is not None
                and shell_payload != previous_shell_payload
            ):
                remote_aliases.clear()
                remote_functions.clear()
                remote_descriptors.clear()
                remote_files.clear()
                pending_function = None
            previous_shell_payload = shell_payload
            stripped = logical_command.lstrip()
            contextual_wrapper = bool(
                re.match(r"^(?:-\s*)?run\s*:", stripped, re.IGNORECASE)
                or re.match(
                r"^RUN\b", stripped, re.IGNORECASE
                )
            )
            if contextual_wrapper:
                remote_aliases.clear()
                remote_functions.clear()
                remote_descriptors.clear()
                remote_files.clear()
                pending_function = None
            contexts = (
                _contextual_shell_commands(logical_command)
                if contextual_wrapper
                else [logical_command]
            )
            if contextual_wrapper and not contexts:
                continue
            for contextual_command in contexts:
                if pending_function is None and (
                    structural_multiline or shell_payload or contextual_wrapper
                ):
                    file_detected, file_unparsed = (
                        _literal_remote_file_flow_status(
                            contextual_command,
                            remote_files,
                            remote_aliases,
                            remote_functions,
                        )
                    )
                else:
                    file_detected = False
                    file_unparsed = False
                if (
                    not remote_aliases
                    and not remote_functions
                    and not remote_descriptors
                    and not remote_files
                    and pending_function is None
                    and not _has_remote_fetcher_hint(contextual_command)
                ):
                    relevance_tokens, relevance_complete = _tokenize_shell_line(
                        contextual_command
                    )
                    dynamic_source = (
                        relevance_complete
                        and _tokens_have_dynamic_source_pipeline(relevance_tokens)
                    ) or re.search(
                        r"\$(?:\{)?[A-Za-z_][A-Za-z0-9_]*(?:[^|\n]{0,512})\|",
                        contextual_command,
                    ) is not None
                    alias_state_declaration = (
                        relevance_complete
                        and _alias_builtin_tokens(relevance_tokens) is not None
                    )
                    descriptor_source = re.search(
                        r"\bexec\b[^;\n]{0,512}>\s*>\(",
                        _decode_shell_payload(contextual_command),
                    ) is not None
                    function_header = structural_multiline and (
                        _FUNCTION_HEADER_ONLY_RE.fullmatch(contextual_command)
                        is not None
                        or _FUNCTION_DECLARATION_RE.match(contextual_command)
                        is not None
                    )
                    if (
                        not dynamic_source
                        and not descriptor_source
                        and not function_header
                        and not alias_state_declaration
                        and contextual_command != _SHELL_UNPARSED_SENTINEL
                    ):
                        continue
                for invalidated_name in _descriptor_variable_invalidations(
                    contextual_command
                ):
                    remote_descriptors.discard("v:" + invalidated_name)
                descriptor_duplication = _remote_descriptor_duplication(
                    contextual_command
                )
                opened_descriptor, closed_descriptor, descriptor_ambiguous = (
                    _remote_descriptor_update(contextual_command)
                )
                if descriptor_duplication is not None:
                    destination, source, move, duplication_ambiguous = (
                        descriptor_duplication
                    )
                    source_active = source is not None and source in remote_descriptors
                    remote_descriptors.discard(destination)
                    if source_active:
                        remote_descriptors.add(destination)
                        if move and source != destination:
                            remote_descriptors.discard(source)
                    opened_descriptor = destination if source_active else None
                    closed_descriptor = None
                    descriptor_ambiguous = (
                        descriptor_ambiguous or duplication_ambiguous
                    )
                else:
                    if closed_descriptor is not None:
                        remote_descriptors.discard(closed_descriptor)
                    if opened_descriptor is not None:
                        remote_descriptors.add(opened_descriptor)
                    followup_operations, followup_ambiguous = (
                        _remote_descriptor_followup_operations(contextual_command)
                    )
                    for destination, source, move in followup_operations:
                        source_active = (
                            source is not None and source in remote_descriptors
                        )
                        remote_descriptors.discard(destination)
                        if source_active:
                            remote_descriptors.add(destination)
                        if move and source is not None and source != destination:
                            remote_descriptors.discard(source)
                    if followup_operations:
                        active_destinations = [
                            destination
                            for destination, _source, _move in followup_operations
                            if destination in remote_descriptors
                        ]
                        opened_descriptor = (
                            active_destinations[-1]
                            if active_destinations
                            else None
                        )
                    descriptor_ambiguous = (
                        descriptor_ambiguous or followup_ambiguous
                    )
                descriptor_budget_exceeded = (
                    len(remote_aliases)
                    + len(remote_functions)
                    + len(remote_descriptors)
                    + len(remote_files)
                    > MAX_REMOTE_SHELL_SYMBOLS
                )
                if descriptor_budget_exceeded:
                    remote_aliases.clear()
                    remote_functions.clear()
                    remote_descriptors.clear()
                    remote_files.clear()
                pipeline_detected, pipeline_unparsed = _remote_pipeline_status(
                    contextual_command,
                    shell_payload=shell_payload,
                )
                detected = file_detected or pipeline_detected
                if (
                    opened_descriptor is not None
                    and not detected
                    and not descriptor_ambiguous
                ):
                    pipeline_unparsed = False
                descriptor_unparsed = False
                if not detected and opened_descriptor is None:
                    descriptor_detected, descriptor_unparsed = (
                        _remote_source_redirects_to_descriptor(
                            contextual_command,
                            remote_descriptors,
                            remote_aliases,
                            remote_functions,
                        )
                    )
                    detected = descriptor_detected
                base_unparsed = (
                    pipeline_unparsed
                    or file_unparsed
                    or descriptor_unparsed
                    or descriptor_ambiguous
                    or descriptor_budget_exceeded
                )
                could_not_parse = base_unparsed
                if contextual_wrapper:
                    contextual_aliases: set[str] = set()
                    contextual_functions: dict[str, str] = {}
                    if not detected and opened_descriptor is None:
                        dynamic_detected, dynamic_unparsed = (
                            _ordered_dynamic_remote_status(
                                contextual_command,
                                contextual_aliases,
                                contextual_functions,
                            )
                        )
                        detected = dynamic_detected
                        could_not_parse = (
                            False if detected else base_unparsed or dynamic_unparsed
                        )
                elif not detected and opened_descriptor is None:
                    dynamic_handled = False
                    dynamic_unparsed = False
                    if pending_function is not None:
                        completed = pending_function.append(contextual_command)
                        if pending_function.overflow:
                            dynamic_unparsed = True
                            unparsed.append(pending_function.start_line)
                            pending_function = None
                        elif pending_function.invalid:
                            pending_function = None
                        elif completed:
                            dynamic_command = "\n".join(pending_function.parts)
                            pending_function = None
                            detected, dynamic_unparsed = (
                                _ordered_dynamic_remote_status(
                                    dynamic_command,
                                    remote_aliases,
                                    remote_functions,
                                )
                            )
                            dynamic_handled = True
                        else:
                            continue
                    if (
                        pending_function is None
                        and not dynamic_handled
                    ):
                        new_pending, completed = _start_pending_shell_function(
                            contextual_command,
                            start_line,
                        )
                        if new_pending is not None and not completed:
                            pending_function = new_pending
                            continue
                        dynamic_command = contextual_command
                        if new_pending is not None:
                            if new_pending.invalid or new_pending.overflow:
                                dynamic_unparsed = True
                            else:
                                dynamic_command = "\n".join(new_pending.parts)
                        if not dynamic_unparsed:
                            detected, dynamic_unparsed = _ordered_dynamic_remote_status(
                                dynamic_command,
                                remote_aliases,
                                remote_functions,
                            )
                    could_not_parse = (
                        False if detected else base_unparsed or dynamic_unparsed
                    )
                if detected:
                    findings.append(start_line)
                elif could_not_parse:
                    unparsed.append(start_line)
        if pending_function is not None:
            pending_source = "\n".join(pending_function.parts)
            if not pending_function.awaiting_brace and _has_remote_fetcher_hint(
                pending_source
            ):
                unparsed.append(pending_function.start_line)
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


def _firebase_string_literal_value(literal: str) -> str | None:
    if len(literal) < 2 or literal[0] not in {'"', "'"} or literal[-1] != literal[0]:
        return None
    body = literal[1:-1]
    output: list[str] = []
    index = 0
    simple_escapes = {
        "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t",
        "\\": "\\", "/": "/", '"': '"', "'": "'",
    }
    while index < len(body):
        if body[index] != "\\":
            output.append(body[index])
            index += 1
            continue
        if index + 1 >= len(body):
            return None
        escape = body[index + 1]
        if escape != "u":
            replacement = simple_escapes.get(escape)
            if replacement is None:
                return None
            output.append(replacement)
            index += 2
            continue
        digits = body[index + 2 : index + 6]
        if len(digits) != 4 or re.fullmatch(r"[0-9A-Fa-f]{4}", digits) is None:
            return None
        codepoint = int(digits, 16)
        index += 6
        if 0xD800 <= codepoint <= 0xDBFF and body[index : index + 2] == "\\u":
            low_digits = body[index + 2 : index + 6]
            if len(low_digits) == 4 and re.fullmatch(r"[0-9A-Fa-f]{4}", low_digits):
                low = int(low_digits, 16)
                if 0xDC00 <= low <= 0xDFFF:
                    codepoint = 0x10000 + ((codepoint - 0xD800) << 10) + (low - 0xDC00)
                    index += 6
        if 0xD800 <= codepoint <= 0xDFFF:
            return None
        output.append(chr(codepoint))
    return "".join(output)


def _canonical_firebase_number(literal: str) -> tuple[int, str, str] | None:
    if re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", literal) is None:
        return None
    sign = -1 if literal.startswith("-") else 1
    unsigned = literal.lstrip("+-")
    integer, separator, fraction = unsigned.partition(".")
    integer = integer.lstrip("0") or "0"
    fraction = fraction.rstrip("0") if separator else ""
    if integer == "0" and not fraction:
        sign = 0
    return sign, integer, fraction


def _compare_firebase_numbers(
    left: tuple[int, str, str] | Fraction,
    right: tuple[int, str, str] | Fraction,
) -> int | None:
    if isinstance(left, Fraction) or isinstance(right, Fraction):
        left_fraction = _firebase_number_fraction(left)
        right_fraction = _firebase_number_fraction(right)
        if left_fraction is None or right_fraction is None:
            return None
        return -1 if left_fraction < right_fraction else 1 if left_fraction > right_fraction else 0
    if left[0] != right[0]:
        return -1 if left[0] < right[0] else 1
    if left[0] == 0:
        return 0

    def compare_magnitude() -> int:
        if len(left[1]) != len(right[1]):
            return -1 if len(left[1]) < len(right[1]) else 1
        if left[1] != right[1]:
            return -1 if left[1] < right[1] else 1
        width = max(len(left[2]), len(right[2]))
        for index in range(width):
            left_digit = left[2][index] if index < len(left[2]) else "0"
            right_digit = right[2][index] if index < len(right[2]) else "0"
            if left_digit != right_digit:
                return -1 if left_digit < right_digit else 1
        return 0

    comparison = compare_magnitude()
    return comparison if left[0] > 0 else -comparison


def _firebase_number_fraction(
    value: tuple[int, str, str] | Fraction,
) -> Fraction | None:
    """Convert a bounded numeric constant for arithmetic without giant integers."""

    if isinstance(value, Fraction):
        return value
    sign, integer, fraction = value
    digits = integer + fraction
    if len(digits) > 512:
        return None
    numerator = int(digits or "0") * sign
    denominator = 10 ** len(fraction)
    return Fraction(numerator, denominator)


def _bounded_firebase_fraction(value: Fraction) -> Fraction | None:
    if value.numerator.bit_length() > 4096 or value.denominator.bit_length() > 4096:
        return None
    return value


def _firebase_unary_value(
    operator: str,
    value: tuple[str, object] | None,
) -> tuple[str, object] | None:
    if operator == "!":
        boolean = _firebase_boolean_value(value)
        return None if boolean is None else ("boolean", not boolean)
    if value is None or value[0] != "number":
        return None
    number = _firebase_number_fraction(value[1])
    if number is None:
        return None
    return "number", number if operator == "u+" else -number


def _firebase_arithmetic_value(
    operator: str,
    left: tuple[str, object] | None,
    right: tuple[str, object] | None,
) -> tuple[str, object] | None:
    if left is None or right is None or left[0] != "number" or right[0] != "number":
        return None
    left_number = _firebase_number_fraction(left[1])
    right_number = _firebase_number_fraction(right[1])
    if left_number is None or right_number is None:
        return None
    if operator == "+":
        result = left_number + right_number
    elif operator == "-":
        result = left_number - right_number
    elif operator == "*":
        result = left_number * right_number
    elif operator == "/":
        if right_number == 0:
            return None
        result = left_number / right_number
    elif operator == "%":
        if right_number == 0 or left_number.denominator != 1 or right_number.denominator != 1:
            return None
        left_integer = left_number.numerator
        right_integer = right_number.numerator
        quotient = abs(left_integer) // abs(right_integer)
        if (left_integer < 0) != (right_integer < 0):
            quotient = -quotient
        result = Fraction(left_integer - (quotient * right_integer), 1)
    else:
        return None
    bounded = _bounded_firebase_fraction(result)
    return None if bounded is None else ("number", bounded)


def _firebase_constant_literal(expression: str) -> tuple[str, object] | None:
    literal = expression.strip()
    folded = literal.casefold()
    if folded in {"true", "false"}:
        return "boolean", folded == "true"
    if folded == "null":
        return "null", None
    if literal[:1] in {'"', "'"}:
        value = _firebase_string_literal_value(literal)
        return None if value is None else ("string", value)
    number = _canonical_firebase_number(literal)
    return None if number is None else ("number", number)


def _firebase_comparison_value(
    operator: str,
    left: tuple[str, object] | None,
    right: tuple[str, object] | None,
) -> tuple[str, object] | None:
    """Evaluate a comparison only when both operands are known constants."""

    if left is None or right is None:
        return None
    if left[0] == "list" or right[0] == "list":
        return None
    if operator in {"==", "!=", "===", "!=="}:
        if left[0] == right[0] == "number":
            comparison = _compare_firebase_numbers(left[1], right[1])
            if comparison is None:
                return None
            equal = comparison == 0
        else:
            equal = left == right
        if operator in {"!=", "!=="}:
            equal = not equal
        return "boolean", equal
    if left[0] != right[0] or left[0] not in {"number", "string"}:
        return None
    if left[0] == "number":
        ordered = _compare_firebase_numbers(left[1], right[1])
        if ordered is None:
            return None
    else:
        ordered = -1 if left[1] < right[1] else 1 if left[1] > right[1] else 0
    return "boolean", {
        "<": ordered < 0,
        "<=": ordered <= 0,
        ">": ordered > 0,
        ">=": ordered >= 0,
    }[operator]


def _firebase_membership_value(
    left: tuple[str, object] | None,
    right: tuple[str, object] | None,
) -> tuple[str, object] | None:
    """Evaluate scalar membership only for a fully constant bounded list."""

    if (
        left is None
        or right is None
        or left[0] not in {"boolean", "null", "number", "string"}
        or right[0] != "list"
    ):
        return None
    elements = right[1]
    if not isinstance(elements, tuple):
        return None
    for element in elements:
        if not isinstance(element, tuple) or len(element) != 2:
            return None
        equal = _firebase_comparison_value("==", left, element)
        if equal is None:
            return None
        if _firebase_boolean_value(equal) is True:
            return "boolean", True
    return "boolean", False


def _firebase_boolean_value(value: tuple[str, object] | None) -> bool | None:
    if value is None or value[0] != "boolean":
        return None
    return bool(value[1])


def _firebase_boolean_binary_value(
    operator: str,
    left: tuple[str, object] | None,
    right: tuple[str, object] | None,
) -> tuple[str, object] | None:
    left_boolean = _firebase_boolean_value(left)
    right_boolean = _firebase_boolean_value(right)
    if operator == "&&":
        if left_boolean is False or right_boolean is False:
            return "boolean", False
        if left_boolean is True and right_boolean is True:
            return "boolean", True
        return None
    if operator == "||":
        if left_boolean is True or right_boolean is True:
            return "boolean", True
        if left_boolean is False and right_boolean is False:
            return "boolean", False
        return None
    if operator in {"+", "-", "*", "/", "%"}:
        return _firebase_arithmetic_value(operator, left, right)
    if operator == "in":
        return _firebase_membership_value(left, right)
    return _firebase_comparison_value(operator, left, right)


def _firebase_condition_value(condition: str) -> bool | None:
    """Evaluate a bounded constant projection with Firebase operator precedence.

    Unknown repository expressions stay unknown, while boolean identities can still
    prove a complete condition true or false. Parsing is iterative so deeply nested
    generated rules cannot consume the Python call stack.
    """

    precedence = {
        "?:": 0,
        "||": 1,
        "&&": 2,
        "==": 3,
        "!=": 3,
        "===": 3,
        "!==": 3,
        "<": 4,
        "<=": 4,
        ">": 4,
        ">=": 4,
        "in": 4,
        "+": 5,
        "-": 5,
        "*": 6,
        "/": 6,
        "%": 6,
        "!": 7,
        "u+": 7,
        "u-": 7,
    }
    binary_operators = (
        "!==", "===", "&&", "||", "<=", ">=", "==", "!=",
        "<", ">", "+", "-", "*", "/", "%",
    )
    values: list[tuple[str, object] | None] = []
    operators: list[str] = []
    index = 0
    expecting_operand = True
    work = 0
    work_limit = max(256, (len(condition) * 16) + 64)

    def spend(amount: int = 1) -> bool:
        nonlocal work
        work += amount
        return work <= work_limit

    def binary_operator_at(position: int) -> str | None:
        for candidate in binary_operators:
            if condition.startswith(candidate, position):
                return candidate
        if condition[position : position + 2].casefold() == "in":
            before = condition[position - 1 : position]
            after = condition[position + 2 : position + 3]
            identifier_characters = {"_", "$"}
            if not (
                (before and (before.isalnum() or before in identifier_characters))
                or (after and (after.isalnum() or after in identifier_characters))
            ):
                return "in"
        return None

    def scan_quoted(position: int) -> tuple[int, bool]:
        quote_character = condition[position]
        cursor = position + 1
        escaped = False
        while cursor < len(condition):
            if not spend():
                return cursor, False
            character = condition[cursor]
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote_character:
                return cursor + 1, True
            cursor += 1
        return cursor, False

    def scan_comment(position: int) -> tuple[int, bool]:
        if condition.startswith("//", position):
            cursor = position + 2
            while cursor < len(condition) and condition[cursor] not in "\r\n":
                if not spend():
                    return cursor, False
                cursor += 1
            return cursor, True
        if not condition.startswith("/*", position):
            return position, False
        cursor = position + 2
        while cursor < len(condition) and not condition.startswith("*/", cursor):
            if not spend():
                return cursor, False
            cursor += 1
        if cursor >= len(condition):
            return cursor, False
        return cursor + 2, True

    def scan_unknown(position: int) -> tuple[int, bool]:
        """Consume one unsupported primary without exposing its internal operators."""

        cursor = position
        closers: list[str] = []
        pairs = {"(": ")", "[": "]", "{": "}"}
        while cursor < len(condition):
            if not spend():
                return cursor, False
            character = condition[cursor]
            if character in {'"', "'"}:
                cursor, complete = scan_quoted(cursor)
                if not complete:
                    return cursor, False
                continue
            if condition.startswith(("//", "/*"), cursor):
                cursor, complete = scan_comment(cursor)
                if not complete:
                    return cursor, False
                continue
            if character in pairs:
                closers.append(pairs[character])
                cursor += 1
                continue
            if character in {")", "]", "}"}:
                if closers:
                    if character != closers[-1]:
                        return cursor, False
                    closers.pop()
                    cursor += 1
                    continue
                if character == ")":
                    break
                return cursor, False
            if not closers and (
                binary_operator_at(cursor) is not None
                or character in {"?", ":"}
            ):
                break
            cursor += 1
        return cursor, not closers

    def scan_constant_list(
        position: int,
    ) -> tuple[int, tuple[str, object] | None, bool]:
        """Parse a flat list of scalar constants, otherwise consume it opaquely."""

        cursor = position + 1
        elements: list[tuple[str, object]] = []
        expecting_element = True
        while cursor < len(condition):
            if not spend():
                return cursor, None, False
            if condition[cursor].isspace():
                cursor += 1
                continue
            if condition.startswith(("//", "/*"), cursor):
                cursor, complete = scan_comment(cursor)
                if not complete:
                    return cursor, None, False
                continue
            if condition[cursor] == "]":
                if expecting_element and elements:
                    opaque_end, complete = scan_unknown(position)
                    return opaque_end, None, complete
                return cursor + 1, ("list", tuple(elements)), True
            if not expecting_element:
                if condition[cursor] != ",":
                    opaque_end, complete = scan_unknown(position)
                    return opaque_end, None, complete
                cursor += 1
                expecting_element = True
                continue
            if len(elements) >= MAX_FIREBASE_LITERAL_LIST_ITEMS:
                opaque_end, complete = scan_unknown(position)
                return opaque_end, None, complete

            literal_start = cursor
            literal_end = cursor
            literal_complete = True
            if condition[cursor] in {'"', "'"}:
                literal_end, literal_complete = scan_quoted(cursor)
            elif condition[cursor].isalpha() or condition[cursor] == "_":
                literal_end += 1
                while literal_end < len(condition) and (
                    condition[literal_end].isalnum()
                    or condition[literal_end] in {"_", "$"}
                ):
                    if not spend():
                        return literal_end, None, False
                    literal_end += 1
            else:
                if condition[cursor] in {"+", "-"}:
                    literal_end += 1
                digit_start = literal_end
                while literal_end < len(condition) and condition[literal_end].isdigit():
                    if not spend():
                        return literal_end, None, False
                    literal_end += 1
                if digit_start == literal_end:
                    opaque_end, complete = scan_unknown(position)
                    return opaque_end, None, complete
                if (
                    literal_end + 1 < len(condition)
                    and condition[literal_end] == "."
                    and condition[literal_end + 1].isdigit()
                ):
                    literal_end += 1
                    while literal_end < len(condition) and condition[literal_end].isdigit():
                        if not spend():
                            return literal_end, None, False
                        literal_end += 1

            literal = (
                _firebase_constant_literal(condition[literal_start:literal_end])
                if literal_complete
                else None
            )
            if literal is None or literal[0] == "list":
                opaque_end, complete = scan_unknown(position)
                return opaque_end, None, complete
            elements.append(literal)
            cursor = literal_end
            expecting_element = False
        return cursor, None, False

    def reduce_top() -> bool:
        if not operators or operators[-1] == "(" or not spend():
            return False
        operator = operators.pop()
        if operator in {"!", "u+", "u-"}:
            if not values:
                return False
            values.append(_firebase_unary_value(operator, values.pop()))
            return True
        if operator == "?:":
            if len(values) < 3:
                return False
            false_value = values.pop()
            true_value = values.pop()
            condition_value = _firebase_boolean_value(values.pop())
            if condition_value is True:
                values.append(true_value)
            elif condition_value is False:
                values.append(false_value)
            else:
                values.append(true_value if true_value == false_value else None)
            return True
        if len(values) < 2:
            return False
        right = values.pop()
        left = values.pop()
        values.append(_firebase_boolean_binary_value(operator, left, right))
        return True

    while index < len(condition):
        if not spend():
            return None
        if condition[index].isspace():
            index += 1
            continue
        if condition.startswith(("//", "/*"), index):
            index, complete = scan_comment(index)
            if not complete:
                return None
            continue

        character = condition[index]
        if expecting_operand:
            if character == "(":
                operators.append("(")
                index += 1
                continue
            if character == "!" and not condition.startswith("!=", index):
                operators.append("!")
                index += 1
                continue
            if character in {"+", "-"}:
                operators.append("u" + character)
                index += 1
                continue
            if character in {")", "]", "}"} or binary_operator_at(index) is not None:
                return None

            literal_end = index
            literal_value: tuple[str, object] | None = None
            literal_complete = True
            if character in {'"', "'"}:
                literal_end, literal_complete = scan_quoted(index)
                if literal_complete:
                    literal_value = _firebase_constant_literal(condition[index:literal_end])
            elif character == "[":
                literal_end, literal_value, literal_complete = scan_constant_list(index)
            elif character.isalpha() or character == "_":
                literal_end = index + 1
                while literal_end < len(condition) and (
                    condition[literal_end].isalnum() or condition[literal_end] in {"_", "$"}
                ):
                    if not spend():
                        return None
                    literal_end += 1
                literal_value = _firebase_constant_literal(condition[index:literal_end])
                if literal_value is None:
                    literal_end, literal_complete = scan_unknown(index)
            elif character.isdigit():
                literal_end = index
                while literal_end < len(condition) and condition[literal_end].isdigit():
                    if not spend():
                        return None
                    literal_end += 1
                if (
                    literal_end + 1 < len(condition)
                    and condition[literal_end] == "."
                    and condition[literal_end + 1].isdigit()
                ):
                    literal_end += 1
                    while literal_end < len(condition) and condition[literal_end].isdigit():
                        if not spend():
                            return None
                        literal_end += 1
                literal_value = _firebase_constant_literal(condition[index:literal_end])
            else:
                literal_end, literal_complete = scan_unknown(index)

            if not literal_complete or literal_end <= index:
                return None
            values.append(literal_value)
            index = literal_end
            expecting_operand = False
            continue

        if character == ")":
            while operators and operators[-1] != "(":
                if not reduce_top():
                    return None
            if not operators or operators[-1] != "(":
                return None
            operators.pop()
            index += 1
            continue

        if character == "?":
            while (
                operators
                and operators[-1] not in {"(", "?", "?:"}
            ):
                if not reduce_top():
                    return None
            operators.append("?")
            index += 1
            expecting_operand = True
            continue

        if character == ":":
            while operators and operators[-1] != "?":
                if operators[-1] == "(" or not reduce_top():
                    return None
            if not operators or operators[-1] != "?":
                return None
            operators.pop()
            operators.append("?:")
            index += 1
            expecting_operand = True
            continue

        operator = binary_operator_at(index)
        if operator is not None:
            while (
                operators
                and operators[-1] not in {"(", "?"}
                and precedence[operators[-1]] >= precedence[operator]
            ):
                if not reduce_top():
                    return None
            operators.append(operator)
            index += len(operator)
            expecting_operand = True
            continue

        # A method/index suffix or an unsupported valid operator turns only the
        # current primary into unknown; outer &&/|| can still prove the result.
        suffix_end, complete = scan_unknown(index)
        if not complete or suffix_end <= index or not values:
            return None
        values[-1] = None
        index = suffix_end

    if expecting_operand:
        return None
    while operators:
        if operators[-1] == "(" or not reduce_top():
            return None
    if len(values) != 1:
        return None
    return _firebase_boolean_value(values[0])


def _firebase_direct_true_offsets(
    text: str,
    quoted_positions: Sequence[int],
) -> Iterable[int]:
    """Find directly permissive Firestore/RTDB conditions with linear cursors."""

    for match in _FIREBASE_UNCONDITIONAL_ALLOW_RE.finditer(text):
        if not (
            match.start() < len(quoted_positions)
            and quoted_positions[match.start()]
        ):
            yield match.start()

    cursor = 0
    while cursor < len(text):
        match = _FIREBASE_ALLOW_PREFIX_RE.search(text, cursor)
        if match is None:
            break
        if match.start() < len(quoted_positions) and quoted_positions[match.start()]:
            cursor = match.end()
            continue
        condition_end = text.find(";", match.end())
        if condition_end < 0:
            break
        while condition_end < len(text) and quoted_positions[condition_end]:
            condition_end = text.find(";", condition_end + 1)
            if condition_end < 0:
                break
        if condition_end < 0:
            break
        condition = text[match.end() : condition_end]
        if _firebase_condition_value(condition) is True:
            yield match.start()
        cursor = condition_end + 1

    cursor = 0
    while cursor < len(text):
        match = _FIREBASE_RTD_PREFIX_RE.search(text, cursor)
        if match is None:
            break
        if not _firebase_rtd_key_at(text, match.start(), quoted_positions):
            cursor = match.end()
            continue
        value_start = match.end()
        if value_start >= len(text):
            break
        if text[value_start] in {'"', "'"}:
            quote_character = text[value_start]
            value_end = value_start + 1
            escaped = False
            while value_end < len(text):
                character = text[value_end]
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == quote_character:
                    break
                value_end += 1
            if value_end >= len(text):
                break
            literal = text[value_start : value_end + 1]
            decoded_condition = _firebase_string_literal_value(literal)
            condition = (
                decoded_condition
                if decoded_condition is not None
                else text[value_start + 1 : value_end]
            )
            cursor = value_end + 1
        else:
            value_end = value_start
            while value_end < len(text) and text[value_end] not in ",}":
                value_end += 1
            condition = text[value_start:value_end]
            cursor = max(value_end + 1, match.end())
        if _firebase_condition_value(condition) is True:
            yield match.start()


def _firebase_rtd_key_at(
    text: str,
    index: int,
    quoted_positions: Sequence[int],
) -> bool:
    """Recognize a structural RTDB .read/.write key, not text inside a value."""

    if index >= len(text) or (index < len(quoted_positions) and quoted_positions[index]):
        return False
    cursor = index
    if text[cursor] in {'"', "'"}:
        quote = text[cursor]
        cursor += 1
        escaped = False
        while cursor < len(text):
            character = text[cursor]
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                break
            cursor += 1
        if cursor >= len(text):
            return False
        key = _firebase_string_literal_value(text[index : cursor + 1])
        cursor += 1
    else:
        key = next(
            (
                candidate
                for candidate in (".read", ".write")
                if text.startswith(candidate, cursor)
            ),
            None,
        )
        if key is not None:
            cursor += len(key)
        if cursor < len(text) and (text[cursor].isalnum() or text[cursor] in "_."):
            return False
    if key is None or key.casefold() not in {".read", ".write"}:
        return False
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor < len(text) and text[cursor] == ":"


def _sql_code_view(text: str) -> str:
    """Project executable PostgreSQL code while preserving source offsets.

    Ordinary literal bodies remain blank. Anonymous blocks and routine bodies are
    recursively projected, as are literal SQL payloads passed to PL/pgSQL
    ``EXECUTE``. Recursion has a small hard ceiling; beyond it the payload is left
    visible (fail closed) rather than risking interpreter-stack or quadratic work.
    """

    def blank_range(output: list[str], source: str, start: int, end: int) -> None:
        for position in range(start, end):
            if source[position] not in "\r\n":
                output[position] = " "

    def dollar_delimiter_end(source: str, start: int) -> int | None:
        if start >= len(source) or source[start] != "$":
            return None
        cursor = start + 1
        if cursor < len(source) and source[cursor] == "$":
            return cursor + 1
        if cursor >= len(source) or not (
            source[cursor] == "_"
            or source[cursor].isascii() and source[cursor].isalpha()
            or ord(source[cursor]) >= 0x80
        ):
            return None
        cursor += 1
        while cursor < len(source) and (
            source[cursor] == "_"
            or source[cursor].isascii() and source[cursor].isalnum()
            or ord(source[cursor]) >= 0x80
        ):
            cursor += 1
        return cursor + 1 if cursor < len(source) and source[cursor] == "$" else None

    def single_literal_end(
        source: str,
        start: int,
        *,
        escape_string: bool,
    ) -> tuple[int, bool]:
        cursor = start + 1
        while cursor < len(source):
            if escape_string and source[cursor] == "\\" and cursor + 1 < len(source):
                cursor += 2
                continue
            if source[cursor] != "'":
                cursor += 1
                continue
            if cursor + 1 < len(source) and source[cursor + 1] == "'":
                cursor += 2
                continue
            return cursor + 1, True
        return len(source), False

    def skip_sql_trivia(source: str, start: int) -> int:
        """Skip whitespace and comments once, with nested block comments."""

        cursor = start
        while cursor < len(source):
            if source[cursor].isspace():
                cursor += 1
                continue
            if source.startswith("--", cursor):
                cursor += 2
                while cursor < len(source) and source[cursor] not in "\r\n":
                    cursor += 1
                continue
            if not source.startswith("/*", cursor):
                break
            block_depth = 1
            cursor += 2
            while cursor < len(source) and block_depth:
                if source.startswith("/*", cursor):
                    block_depth += 1
                    cursor += 2
                elif source.startswith("*/", cursor):
                    block_depth -= 1
                    cursor += 2
                else:
                    cursor += 1
            if block_depth:
                return len(source)
        return cursor

    def string_token_start(source: str, quote_start: int) -> int:
        """Include a valid E, N, or U& prefix already consumed by the lexer."""

        if (
            quote_start >= 2
            and source[quote_start - 2 : quote_start].casefold() == "u&"
            and (
                quote_start == 2
                or not (
                    source[quote_start - 3].isalnum()
                    or source[quote_start - 3] in {"_", "$"}
                )
            )
        ):
            return quote_start - 2
        if (
            quote_start >= 1
            and source[quote_start - 1] in {"e", "E", "n", "N"}
            and (
                quote_start == 1
                or not (
                    source[quote_start - 2].isalnum()
                    or source[quote_start - 2] in {"_", "$"}
                )
            )
        ):
            return quote_start - 1
        return quote_start

    def unicode_scalar(value: int) -> str | None:
        if value == 0 or value > 0x10FFFF or 0xD800 <= value <= 0xDFFF:
            return None
        return chr(value)

    def decoded_single_literal(
        source: str,
        quote_start: int,
        end: int,
        *,
        literal_kind: str,
        unicode_escape: str = "\\",
    ) -> str | None:
        """Decode one closed PostgreSQL string constant without evaluating SQL."""

        output: list[str] = []
        body_end = end - 1
        cursor = quote_start + 1
        while cursor < body_end:
            character = source[cursor]
            if character == "'" and cursor + 1 < body_end and source[cursor + 1] == "'":
                output.append("'")
                cursor += 2
                continue

            if literal_kind == "unicode" and character == unicode_escape:
                if cursor + 1 >= body_end:
                    return None
                if source[cursor + 1] == unicode_escape:
                    output.append(unicode_escape)
                    cursor += 2
                    continue
                plus_form = source[cursor + 1] == "+"
                digit_start = cursor + 2 if plus_form else cursor + 1
                digit_count = 6 if plus_form else 4
                digits = source[digit_start : digit_start + digit_count]
                if (
                    len(digits) != digit_count
                    or re.fullmatch(r"[0-9A-Fa-f]+", digits) is None
                ):
                    return None
                value = int(digits, 16)
                cursor = digit_start + digit_count
                if 0xD800 <= value <= 0xDBFF and not plus_form:
                    low_prefix = source[cursor : cursor + 1]
                    low_digits = source[cursor + 1 : cursor + 5]
                    if (
                        low_prefix == unicode_escape
                        and re.fullmatch(r"[0-9A-Fa-f]{4}", low_digits)
                        and 0xDC00 <= int(low_digits, 16) <= 0xDFFF
                    ):
                        low = int(low_digits, 16)
                        value = 0x10000 + ((value - 0xD800) << 10) + low - 0xDC00
                        cursor += 5
                decoded = unicode_scalar(value)
                if decoded is None:
                    return None
                output.append(decoded)
                continue

            if literal_kind == "escape" and character == "\\":
                if cursor + 1 >= body_end:
                    return None
                escaped = source[cursor + 1]
                simple = {
                    "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t",
                }
                if escaped in simple:
                    output.append(simple[escaped])
                    cursor += 2
                    continue
                if escaped in "01234567":
                    match = re.match(r"[0-7]{1,3}", source[cursor + 1 : body_end])
                    if match is None:
                        return None
                    value = int(match.group(0), 8)
                    if value == 0:
                        return None
                    output.append(chr(value))
                    cursor += 1 + len(match.group(0))
                    continue
                if escaped in {"x", "X"}:
                    match = re.match(r"[0-9A-Fa-f]{1,2}", source[cursor + 2 : body_end])
                    if match is None:
                        return None
                    value = int(match.group(0), 16)
                    if value == 0:
                        return None
                    output.append(chr(value))
                    cursor += 2 + len(match.group(0))
                    continue
                if escaped in {"u", "U"}:
                    digit_count = 4 if escaped == "u" else 8
                    digits = source[cursor + 2 : cursor + 2 + digit_count]
                    if (
                        len(digits) != digit_count
                        or re.fullmatch(r"[0-9A-Fa-f]+", digits) is None
                    ):
                        return None
                    value = int(digits, 16)
                    cursor += 2 + digit_count
                    if 0xD800 <= value <= 0xDBFF and escaped == "u":
                        low_digits = source[cursor + 2 : cursor + 6]
                        if (
                            source[cursor : cursor + 2] == "\\u"
                            and re.fullmatch(r"[0-9A-Fa-f]{4}", low_digits)
                            and 0xDC00 <= int(low_digits, 16) <= 0xDFFF
                        ):
                            low = int(low_digits, 16)
                            value = 0x10000 + ((value - 0xD800) << 10) + low - 0xDC00
                            cursor += 6
                    decoded = unicode_scalar(value)
                    if decoded is None:
                        return None
                    output.append(decoded)
                    continue
                if escaped in "\r\n":
                    if escaped == "\r" and cursor + 2 < body_end and source[cursor + 2] == "\n":
                        cursor += 3
                    else:
                        cursor += 2
                    continue
                output.append(escaped)
                cursor += 2
                continue

            output.append(character)
            cursor += 1
        return "".join(output)

    def constant_string_at(source: str, start: int) -> tuple[int, str] | None:
        """Parse one exact PostgreSQL string token, including UESCAPE."""

        if start >= len(source):
            return None
        if source[start] == "$":
            delimiter_end = dollar_delimiter_end(source, start)
            if delimiter_end is None:
                return None
            delimiter = source[start:delimiter_end]
            close = source.find(delimiter, delimiter_end)
            if close < 0:
                return None
            return close + len(delimiter), source[delimiter_end:close]

        literal_kind = "regular"
        quote_start = start
        if source[start : start + 2].casefold() == "u&" and source[start + 2 : start + 3] == "'":
            literal_kind = "unicode"
            quote_start = start + 2
        elif source[start : start + 1] in {"e", "E"} and source[start + 1 : start + 2] == "'":
            literal_kind = "escape"
            quote_start = start + 1
        elif source[start : start + 1] in {"n", "N"} and source[start + 1 : start + 2] == "'":
            quote_start = start + 1
        elif source[start] != "'":
            return None

        literal_end, closed = single_literal_end(
            source,
            quote_start,
            escape_string=literal_kind == "escape",
        )
        if not closed:
            return None

        unicode_escape = "\\"
        token_end = literal_end
        if literal_kind == "unicode":
            clause_start = skip_sql_trivia(source, literal_end)
            clause_end = clause_start + len("UESCAPE")
            if (
                source[clause_start:clause_end].casefold() == "uescape"
                and (
                    clause_end == len(source)
                    or not (
                        source[clause_end].isalnum()
                        or source[clause_end] in {"_", "$"}
                    )
                )
            ):
                escape_literal_start = skip_sql_trivia(source, clause_end)
                if source[escape_literal_start : escape_literal_start + 1] != "'":
                    return None
                escape_end, escape_closed = single_literal_end(
                    source,
                    escape_literal_start,
                    escape_string=False,
                )
                if not escape_closed:
                    return None
                escape_value = decoded_single_literal(
                    source,
                    escape_literal_start,
                    escape_end,
                    literal_kind="regular",
                )
                if (
                    escape_value is None
                    or len(escape_value) != 1
                    or escape_value in {"+", "'", '"'}
                    or escape_value.isspace()
                    or escape_value in "0123456789abcdefABCDEF"
                ):
                    return None
                unicode_escape = escape_value
                token_end = escape_end

        value = decoded_single_literal(
            source,
            quote_start,
            literal_end,
            literal_kind=literal_kind,
            unicode_escape=unicode_escape,
        )
        return None if value is None else (token_end, value)

    def single_quoted_string_start(source: str, position: int) -> bool:
        if source[position : position + 1] == "'":
            return True
        if (
            source[position : position + 1] in {"e", "E", "n", "N"}
            and source[position + 1 : position + 2] == "'"
        ):
            return True
        return (
            source[position : position + 2].casefold() == "u&"
            and source[position + 2 : position + 3] == "'"
        )

    def adjacent_constant_string_at(
        source: str,
        start: int,
    ) -> tuple[int, str] | None:
        """Fold PostgreSQL's newline-separated single-quoted constants."""

        token = constant_string_at(source, start)
        if token is None:
            return None
        end, value = token
        parts = [value] if value else []
        while True:
            adjacent_start = skip_sql_trivia(source, end)
            separator = source[end:adjacent_start]
            if not any(character in "\r\n" for character in separator):
                break
            if not single_quoted_string_start(source, adjacent_start):
                break
            adjacent = constant_string_at(source, adjacent_start)
            if adjacent is None:
                return None
            end, adjacent_value = adjacent
            if adjacent_value:
                parts.append(adjacent_value)
        return end, "".join(parts)

    def constant_execute_expression(
        source: str,
        start: int,
    ) -> tuple[int, str] | None:
        """Fold a linear grammar of literal-only PL/pgSQL expressions.

        Accepted operations are PostgreSQL string constants, newline-separated
        adjacent string tokens, ``||``, parentheses, and exact identity casts to
        ``text``/``pg_catalog.text`` in postfix or SQL-standard form. Group depth
        uses a stack rather than recursion and total work is bounded by the
        scanner's candidate-byte budget. Identifiers, function calls, quoted or
        search-path-dependent type names, and every non-text cast remain opaque.
        """

        def keyword_at(position: int, keyword: str) -> bool:
            end = position + len(keyword)
            return source[position:end].casefold() == keyword.casefold() and (
                end >= len(source)
                or not (source[end].isalnum() or source[end] in {"_", "$"})
            )

        def identity_text_type_end(position: int) -> int | None:
            first_start = skip_sql_trivia(source, position)
            if keyword_at(first_start, "text"):
                return first_start + len("text")
            if not keyword_at(first_start, "pg_catalog"):
                return None
            dot = skip_sql_trivia(source, first_start + len("pg_catalog"))
            if source[dot : dot + 1] != ".":
                return None
            text_start = skip_sql_trivia(source, dot + 1)
            if not keyword_at(text_start, "text"):
                return None
            return text_start + len("text")

        def identity_casts_end(position: int) -> int | None:
            end = position
            while True:
                operator_start = skip_sql_trivia(source, end)
                if not source.startswith("::", operator_start):
                    return end
                type_start = skip_sql_trivia(source, operator_start + 2)
                type_end = identity_text_type_end(type_start)
                if type_end is None:
                    return None
                end = type_end

        position = start
        groups: list[str] = []
        expecting_operand = True
        parts: list[str] = []
        while True:
            cursor = skip_sql_trivia(source, position)
            if expecting_operand:
                while True:
                    if source[cursor : cursor + 1] == "(":
                        groups.append("group")
                        cursor = skip_sql_trivia(source, cursor + 1)
                        continue
                    if keyword_at(cursor, "cast"):
                        opening = skip_sql_trivia(source, cursor + len("cast"))
                        if source[opening : opening + 1] != "(":
                            return None
                        groups.append("cast")
                        cursor = skip_sql_trivia(source, opening + 1)
                        continue
                    break
                operand = adjacent_constant_string_at(source, cursor)
                if operand is None:
                    return None
                position, value = operand
                if value:
                    parts.append(value)
                cast_end = identity_casts_end(position)
                if cast_end is None:
                    return None
                position = cast_end
                expecting_operand = False
                continue

            cursor = skip_sql_trivia(source, position)
            closed_group = False
            while groups:
                if groups[-1] == "group" and source[cursor : cursor + 1] == ")":
                    groups.pop()
                    position = cursor + 1
                    cast_end = identity_casts_end(position)
                    if cast_end is None:
                        return None
                    position = cast_end
                    cursor = skip_sql_trivia(source, position)
                    closed_group = True
                    continue
                if groups[-1] == "cast" and keyword_at(cursor, "as"):
                    type_start = skip_sql_trivia(source, cursor + len("as"))
                    type_end = identity_text_type_end(type_start)
                    if type_end is None:
                        return None
                    closing = skip_sql_trivia(source, type_end)
                    if source[closing : closing + 1] != ")":
                        return None
                    groups.pop()
                    position = closing + 1
                    cast_end = identity_casts_end(position)
                    if cast_end is None:
                        return None
                    position = cast_end
                    cursor = skip_sql_trivia(source, position)
                    closed_group = True
                    continue
                break
            if closed_group:
                continue
            if source.startswith("||", cursor):
                position = cursor + 2
                expecting_operand = True
                continue
            break

        if expecting_operand or groups:
            return None
        tail = skip_sql_trivia(source, position)
        if tail >= len(source) or source[tail] == ";":
            return position, "".join(parts)
        tail_match = re.match(r"(?:INTO|USING)\b", source[tail:], re.IGNORECASE)
        return (position, "".join(parts)) if tail_match is not None else None

    def same_width_payload(
        source: str,
        start: int,
        end: int,
        payload: str,
    ) -> str | None:
        """Place a decoded value into its source span without moving line offsets."""

        result = [character if character in "\r\n" else " " for character in source[start:end]]
        line_slots: list[list[int]] = []
        current_slots: list[int] = []
        for slot, character in enumerate(result):
            if character in "\r\n":
                if current_slots:
                    line_slots.append(current_slots)
                    current_slots = []
            else:
                current_slots.append(slot)
        if current_slots:
            line_slots.append(current_slots)

        # Pack whole non-whitespace tokens onto source lines. A raw expression
        # newline must not split a decoded keyword (for example ``TA\nBLE``),
        # while unused slots remain spaces and preserve every original offset.
        pieces = [
            match.group(0).rstrip() + (" " if match.group(0)[-1].isspace() else "")
            for match in re.finditer(r"\S+\s*", payload)
        ]
        line_index = 0
        line_offset = 0
        for piece in pieces:
            while line_index < len(line_slots):
                slots = line_slots[line_index]
                if len(piece) <= len(slots) - line_offset:
                    for character, slot in zip(piece, slots[line_offset:]):
                        result[slot] = character
                    line_offset += len(piece)
                    break
                line_index += 1
                line_offset = 0
            else:
                return None
        return "".join(result)

    def project(source: str, *, mode: str, depth: int) -> list[str]:
        output = list(source)
        index = 0
        statement_prefix: list[str] = []
        statement_prefix_overflow = False
        code_tail: deque[str] = deque(maxlen=512)

        def remember(character: str) -> None:
            nonlocal statement_prefix_overflow
            code_tail.append(character)
            if len(statement_prefix) < 512:
                statement_prefix.append(character)
            else:
                statement_prefix_overflow = True

        def remember_space() -> None:
            if not code_tail or not code_tail[-1].isspace():
                remember(" ")

        def reset_statement() -> None:
            nonlocal statement_prefix_overflow
            statement_prefix.clear()
            statement_prefix_overflow = False
            code_tail.clear()

        def statement_opens_executable_body() -> bool:
            prefix = "".join(statement_prefix)
            if _POSTGRES_DO_BODY_PREFIX_RE.fullmatch(prefix):
                return True
            if statement_prefix_overflow and re.match(
                r"\s*DO\b", prefix, re.IGNORECASE
            ):
                return True
            return (
                _POSTGRES_CREATE_ROUTINE_PREFIX_RE.match(prefix) is not None
                and _POSTGRES_AS_TAIL_RE.search("".join(code_tail)) is not None
            )

        def dynamic_execute_precedes() -> bool:
            return (
                mode == "plpgsql"
                and _POSTGRES_DYNAMIC_EXECUTE_TAIL_RE.search("".join(code_tail))
                is not None
            )

        def overlay_projected_payload(
            payload: str,
            destination_start: int,
            *,
            payload_mode: str,
        ) -> None:
            if depth >= _MAX_POSTGRES_EXECUTABLE_NESTING:
                projected = list(payload)
            else:
                projected = project(payload, mode=payload_mode, depth=depth + 1)
            output[destination_start : destination_start + len(projected)] = projected

        def payload_disables_rls(payload: str, *, payload_mode: str) -> bool:
            projected = (
                list(payload)
                if depth >= _MAX_POSTGRES_EXECUTABLE_NESTING
                else project(payload, mode=payload_mode, depth=depth + 1)
            )
            return next(
                _postgres_disabled_rls_offsets("".join(projected)),
                None,
            ) is not None

        def overlay_decoded_payload(
            payload: str,
            destination_start: int,
            destination_end: int,
            *,
            payload_mode: str,
        ) -> None:
            projection = same_width_payload(
                source,
                destination_start,
                destination_end,
                payload,
            )
            blank_range(output, source, destination_start, destination_end)
            if projection is not None:
                overlay_projected_payload(
                    projection,
                    destination_start,
                    payload_mode=payload_mode,
                )
            elif payload_disables_rls(payload, payload_mode=payload_mode):
                # The decoded statement is known to disable RLS but cannot be
                # represented at the original line widths. Preserve its source
                # offset with an internal one-character finding sentinel.
                output[destination_start] = _POSTGRES_DISABLED_RLS_SENTINEL

        def project_constant_expression(start: int) -> int | None:
            expression = constant_execute_expression(source, start)
            if expression is None:
                return None
            expression_end, payload = expression
            overlay_decoded_payload(
                payload,
                start,
                expression_end,
                payload_mode="sql",
            )
            return expression_end

        while index < len(source):
            if source.startswith("--", index):
                start = index
                while index < len(source) and source[index] not in "\r\n":
                    index += 1
                blank_range(output, source, start, index)
                remember_space()
                continue
            if source.startswith("/*", index):
                start = index
                block_depth = 1
                index += 2
                while index < len(source) and block_depth:
                    if source.startswith("/*", index):
                        block_depth += 1
                        index += 2
                    elif source.startswith("*/", index):
                        block_depth -= 1
                        index += 2
                    else:
                        index += 1
                blank_range(output, source, start, index)
                remember_space()
                continue

            character = source[index]
            if character == "(" and dynamic_execute_precedes():
                expression_end = project_constant_expression(index)
                if expression_end is not None:
                    index = expression_end
                    remember_space()
                    continue
            if (
                character in {"c", "C"}
                and source[index : index + len("cast")].casefold() == "cast"
                and (
                    index + len("cast") >= len(source)
                    or not (
                        source[index + len("cast")].isalnum()
                        or source[index + len("cast")] in {"_", "$"}
                    )
                )
                and dynamic_execute_precedes()
            ):
                expression_end = project_constant_expression(index)
                if expression_end is not None:
                    index = expression_end
                    remember_space()
                    continue

            if character == "'":
                token_start = string_token_start(source, index)
                escape_string = (
                    index > 0
                    and source[index - 1] in {"e", "E"}
                    and (
                        index < 2
                        or not (
                            source[index - 2].isalnum()
                            or source[index - 2] in {"_", "$"}
                        )
                    )
                )
                literal_end, closed = single_literal_end(
                    source,
                    index,
                    escape_string=escape_string,
                )
                executable_body = statement_opens_executable_body()
                dynamic_payload = dynamic_execute_precedes()

                if dynamic_payload:
                    expression_end = project_constant_expression(token_start)
                    if expression_end is not None:
                        index = expression_end
                        remember_space()
                        continue

                executable_token = (
                    adjacent_constant_string_at(source, token_start)
                    if executable_body
                    else None
                )
                if executable_token is not None:
                    token_end, payload = executable_token
                    overlay_decoded_payload(
                        payload,
                        token_start,
                        token_end,
                        payload_mode="plpgsql",
                    )
                    index = token_end
                    remember_space()
                    continue

                blank_range(output, source, index, literal_end)
                index = literal_end
                remember_space()
                continue

            if character == '"':
                start = index
                index += 1
                while index < len(source):
                    if source[index] == '"':
                        if index + 1 < len(source) and source[index + 1] == '"':
                            output[index] = output[index + 1] = "x"
                            index += 2
                            continue
                        index += 1
                        break
                    if source[index] not in "\r\n":
                        output[index] = "x"
                    index += 1
                for projected_character in output[start:index]:
                    remember(projected_character)
                continue

            if character == "$":
                delimiter_end = dollar_delimiter_end(source, index)
                if delimiter_end is not None:
                    delimiter = source[index:delimiter_end]
                    close = source.find(delimiter, delimiter_end)
                    body_end = len(source) if close < 0 else close
                    literal_end = len(source) if close < 0 else close + len(delimiter)
                    executable_body = statement_opens_executable_body()
                    dynamic_payload = dynamic_execute_precedes()

                    if dynamic_payload:
                        expression_end = project_constant_expression(index)
                        if expression_end is not None:
                            index = expression_end
                            remember_space()
                            continue

                    blank_range(output, source, index, literal_end)
                    if executable_body and close >= 0:
                        payload = source[delimiter_end:body_end]
                        overlay_projected_payload(
                            payload,
                            delimiter_end,
                            payload_mode="plpgsql",
                        )
                    index = literal_end
                    remember_space()
                    continue

            remember(character)
            index += 1
            if character == ";":
                reset_statement()

        return output

    output = project(text, mode="sql", depth=0)
    code_view = "".join(output)
    copy_cursor = 0
    copy_terminator = re.compile(r"(?m)^\\\.\r?$")
    while True:
        copy_match = _POSTGRES_COPY_STDIN_RE.search(code_view, copy_cursor)
        if copy_match is None:
            break
        data_start = text.find("\n", copy_match.end())
        if data_start < 0:
            break
        data_start += 1
        terminator = copy_terminator.search(text, data_start)
        data_end = len(text) if terminator is None else terminator.end()
        for position in range(data_start, data_end):
            if text[position] not in "\r\n":
                output[position] = " "
        if terminator is None:
            break
        copy_cursor = data_end
    return "".join(output)


def _postgres_disabled_rls_offsets(sql_code: str) -> Iterable[int]:
    """Yield ALTER TABLE statements whose top-level action disables RLS."""

    statement_start = 0
    while statement_start < len(sql_code):
        statement_end = sql_code.find(";", statement_start)
        if statement_end < 0:
            statement_end = len(sql_code)
        sentinel = sql_code.find(
            _POSTGRES_DISABLED_RLS_SENTINEL,
            statement_start,
            statement_end,
        )
        if sentinel >= 0:
            yield sentinel
            statement_start = statement_end + 1
            continue
        alter_match = _POSTGRES_ALTER_TABLE_RE.search(
            sql_code,
            statement_start,
            statement_end,
        )
        if alter_match is None:
            statement_start = statement_end + 1
            continue
        action_start = alter_match.end()
        depth = 0
        index = action_start
        while index < statement_end:
            if index == action_start:
                while index < statement_end and sql_code[index].isspace():
                    index += 1
                action_start = index
                if _POSTGRES_DISABLE_RLS_ACTION_RE.match(sql_code, index):
                    yield alter_match.start()
                    break
            character = sql_code[index]
            if character == "(":
                depth += 1
            elif character == ")" and depth:
                depth -= 1
            elif character == "," and depth == 0:
                action_start = index + 1
            index += 1
        statement_start = statement_end + 1


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

    firebase_rule_file = _is_firebase_rules_path(candidate.path.name)
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

    first_line = text.split("\n", 1)[0][:512]
    shell_shebang = re.match(
        r"^#!\s*(?:(?:/usr/bin/env)(?:\s+-S)?\s+|(?:/[^/\s]+)*/)"
        r"(?:ba|da|a|k|mk|z)?sh(?:\s|$)",
        first_line,
        re.IGNORECASE,
    ) is not None
    remote_lines, unparsed_shell_lines = _remote_pipe_line_numbers(
        text,
        structural_multiline=(
            shell_shebang or not _is_code_assignment_path(candidate.path)
        ),
    )
    for line_number in remote_lines:
        add("VW-REMOTE-INSTALL-SCRIPT", line_number)
    for line_number in unparsed_shell_lines:
        add("VW-SHELL-PIPELINE-UNPARSED", line_number)

    if firebase_rule_file:
        normalized_rules, normalized_line_numbers = _normalized_firebase_rules(text)
        quoted_positions = _firebase_quoted_positions(normalized_rules)
        for start in _firebase_direct_true_offsets(normalized_rules, quoted_positions):
            line_number = (
                normalized_line_numbers[start]
                if start < len(normalized_line_numbers)
                else 1
            )
            add("VW-FIREBASE-PERMISSIVE-RULE", line_number)

    if candidate.path.suffix.lower() == ".sql":
        sql_code = unicodedata.normalize("NFC", _sql_code_view(text))
        previous_match_start = 0
        sql_line_number = 1
        for match_start in _postgres_disabled_rls_offsets(sql_code):
            sql_line_number += sql_code.count("\n", previous_match_start, match_start)
            previous_match_start = match_start
            add("VW-SUPABASE-RLS-DISABLED", sql_line_number)

    if candidate.path.name != "package.json":
        return None
    try:
        manifest = json.loads(text, parse_constant=_reject_nonstandard_json_constant)
    except (json.JSONDecodeError, ValueError):
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
    path_values: set[str] = set()
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
        detected_values = _detected_sensitive_values(
            text, code_context=_is_code_assignment_path(candidate.path)
        )
        for raw_value in detected_values:
            display_value = _safe_display_component(raw_value)
            if not display_value or display_value == "." or raw_value in path_values:
                continue
            path_values.add(raw_value)
            path_value_characters += len(raw_value) + len(display_value)
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

    try:
        candidates = _redact_content_values_from_paths(candidates, path_values)
    except PathRedactionLimitExceeded:
        report.findings.clear()
        report.tool_errors.append(
            ToolIssue(
                "tool.path-redaction-limit",
                "Path redaction exceeded its bounded transform budget; no report locations were emitted.",
            )
        )
        _hide_incomplete_issue_paths(report)
        return report
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
