#!/usr/bin/env python3
"""Reject likely credentials in files eligible for publication.

Checks the Git index, working-tree copies, and non-ignored untracked files.
Diagnostics intentionally name only the file and rule, never a matching value.
"""

import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROHIBITED_NAMES = {".npmrc", ".pypirc", "credentials.json", "secrets.json", "id_rsa", "id_ed25519"}
PROHIBITED_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
SIGNATURES = {
    "private-key block": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "provider credential": re.compile(
        rb"(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
        rb"sk-(?:live-)?[A-Za-z0-9_-]{20,}|A[SK]IA[0-9A-Z]{16}|"
        rb"AIza[0-9A-Za-z_-]{20,}|xox[baprs]-[A-Za-z0-9-]{20,})"
    ),
    "credential assignment": re.compile(
        rb"(?im)^[ \t]*(?:(?:export|const|let|var)[ \t]+)?[\"']?"
        rb"(?:[A-Z][A-Z0-9_]*_)?"
        rb"(?:API_KEY|ACCESS_TOKEN|AUTH_TOKEN|SECRET_KEY|CLIENT_SECRET|PASSWORD)"
        rb"[\"']?[ \t]*[:=][ \t]*[\"']?[^\s#\"']{8,}"
    ),
    "credential-bearing URL": re.compile(rb"https?://[^/@\s]+:[^/@\s]+@"),
}


def git_paths(*flags):
    result = subprocess.run(
        ["git", "ls-files", "-z", *flags],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    return {Path(os.fsdecode(raw)) for raw in result.stdout.split(b"\0") if raw}


def staged_bytes(relative):
    result = subprocess.run(
        ["git", "show", f":{relative.as_posix()}"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def scan():
    issues = []
    tracked = git_paths("--cached")
    paths = sorted(tracked | git_paths("--others", "--exclude-standard"))
    for relative in paths:
        name = relative.name.lower()
        if name == ".env" or name.startswith(".env.") or name in PROHIBITED_NAMES or any(
            name.endswith(suffix) for suffix in PROHIBITED_SUFFIXES
        ):
            issues.append(f"{relative}: prohibited credential/configuration filename")
            continue
        path = ROOT / relative
        if path.is_symlink():
            issues.append(f"{relative}: symlink requires manual review")
            continue
        copies = []
        if relative in tracked:
            copies.append(("Git index", staged_bytes(relative)))
        if path.is_file():
            copies.append(("working tree", path.read_bytes()))
        for location, data in copies:
            if b"\0" in data:
                continue
            for label, pattern in SIGNATURES.items():
                if pattern.search(data):
                    issues.append(f"{relative}: possible {label} in {location}")
    return issues, len(paths)


def main():
    issues, count = scan()
    if issues:
        print("\n".join(issues), file=sys.stderr)
        return 1
    print(f"Repository safety scan passed: {count} publishable files checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
