#!/usr/bin/env python3
"""Block a commit that carries a live credential.

WHY THIS FILE EXISTS
    The pre-commit config had `bandit` (a linter for insecure code) and
    `safety` (a dependency CVE checker, which was not even installed). Neither
    looks for a key in a diff. Meanwhile this repository has, in its own
    record: a TypeSafe key committed into history, `security/api_keys.json`
    found untracked-but-not-ignored in the July 2026 audit, and an API key
    shipped inside a .vsix. The gap was never insecure code. It was keys.

WHAT IT MATCHES
    Only shapes that are unambiguous when they appear in full: vendor-prefixed
    tokens (nvapi-, sk-ant-, ghp_, AKIA...), private-key PEM headers, and an
    assignment of a long opaque string to something named like a secret.
    A generic "40 hex characters" rule was deliberately left out: it fires on
    git SHAs, checksums and PDB hashes, and a scanner that cries wolf gets
    disabled within a week, which is worse than no scanner.

HOW TO ALLOW A DELIBERATE FIXTURE
    Put `pragma: allowlist secret` on the line. Obvious dummies are also
    skipped automatically: anything containing EXAMPLE, XXXX, abcdef...,
    <your-key-here>, or a run of the same character.

Usage:  scan_credentials.py FILE [FILE ...]     (pre-commit passes the staged files)
Exit 1 with a report when something is found, 0 when clean.

-- MOLEVERA / BIOQL
"""
from __future__ import annotations

import re
import sys
from typing import List, Tuple

ALLOW_PRAGMA = "pragma: allowlist secret"

# (name, compiled pattern). Each one is a shape that does not occur by accident.
PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("NVIDIA NGC key", re.compile(r"nvapi-[A-Za-z0-9_\-]{20,}")),
    ("Anthropic key", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("OpenAI key", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("Google API key", re.compile(r"\bAIza[A-Za-z0-9_\-]{35}\b")),
    ("IBM Quantum token", re.compile(r"\bibmq?_[A-Za-z0-9]{40,}\b")),
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY")),
    # An assignment whose NAME says secret and whose VALUE is long and opaque.
    (
        "secret assignment",
        re.compile(
            r"""(?ix)
        \b(?:api[_-]?key|secret|token|passwd|password|access[_-]?key)\b
        \s*[:=]\s*
        ['"]([A-Za-z0-9_\-/+]{24,})['"]
        """
        ),
    ),
]

# Shapes that are obviously placeholders rather than credentials.
_DUMMY = re.compile(
    r"(?ix)"
    r"example|sample|dummy|placeholder|redacted|your[_-]?key|changeme|"
    r"<[^>]+>|\bfake\b|\btest\b|xxxx|abcdefghij|0123456789|"
    r"\$\{?[A-Z_]+\}?"  # $VAR / ${VAR} -- an env reference, not a key
)


def _is_dummy(line: str, match_text: str) -> bool:
    if _DUMMY.search(match_text):
        return True
    if _DUMMY.search(line):
        return True
    # A run of one repeated character is nobody's real key.
    stripped = re.sub(r"[^A-Za-z0-9]", "", match_text)
    return bool(stripped) and len(set(stripped)) <= 3


def scan_text(text: str, path: str = "<text>") -> List[dict]:
    findings = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if ALLOW_PRAGMA in line:
            continue
        for name, pattern in PATTERNS:
            m = pattern.search(line)
            if not m:
                continue
            found = m.group(0)
            if _is_dummy(line, found):
                continue
            # Show enough to identify it, never the whole credential.
            shown = found[:12] + "..." if len(found) > 14 else found
            findings.append({"file": path, "line": lineno, "kind": name, "excerpt": shown})
            break
    return findings


def scan_file(path: str) -> List[dict]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return scan_text(fh.read(), path)
    except (IsADirectoryError, FileNotFoundError, PermissionError):
        return []


def main(argv: List[str]) -> int:
    findings = []
    for path in argv:
        findings.extend(scan_file(path))
    if not findings:
        return 0
    print("A credential must not enter the history. Found:\n", file=sys.stderr)
    for f in findings:
        print(
            "  %s:%d  %s  (%s)" % (f["file"], f["line"], f["excerpt"], f["kind"]), file=sys.stderr
        )
    print(
        "\nMove it to the environment (~/.bioql_secrets) and read it with "
        "os.environ.\nIf this really is a fixture, put '%s' on the line." % ALLOW_PRAGMA,
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

# MOLEVERA / BIOQL
