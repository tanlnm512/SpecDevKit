#!/usr/bin/env python3
"""gate.sh's portable helpers — stdlib only, so the gate needs nothing
beyond bash, git and python3.

Usage:
  gate_helpers.py run SECONDS MARKER CMD...   run CMD with a hard timeout;
                                              on timeout kill its process
                                              group, touch MARKER, exit 124
  gate_helpers.py npm-scripts PACKAGE_JSON    print the gate-worthy scripts
  gate_helpers.py secrets REPO BASE           scan the change for token
                                              shapes; print path:line and
                                              pattern name, never the match
  gate_helpers.py dep-audit REPO              print the dependency-audit
                                              tools the repo's own config
                                              names (pip-audit, safety)
  gate_helpers.py manifests REPO BASE         list the added/removed lines
                                              of changed dependency
                                              manifests; silent when none
"""

import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

NPM_SCRIPTS = ("test", "lint", "typecheck", "audit")
NPM_STUB_TEST = "no test specified"

SECRET_PATTERNS = {
    "AWS access key id": r"AKIA[0-9A-Z]{16}",
    "GitHub token": r"gh[pousr]_[A-Za-z0-9]{36}",
    "GitHub fine-grained token": r"github_pat_[A-Za-z0-9_]{22,}",
    "GitLab token": r"glpat-[A-Za-z0-9_-]{20,}",
    "Stripe live secret key": r"sk_live_[A-Za-z0-9]{16,}",
    "Stripe live restricted key": r"rk_live_[A-Za-z0-9]{16,}",
    "Slack token": r"xox[baprs]-[A-Za-z0-9-]{10,}",
    "Google API key": r"AIza[0-9A-Za-z_-]{35}",
    "npm token": r"npm_[A-Za-z0-9]{36}",
    "Anthropic API key": r"sk-ant-[A-Za-z0-9_-]{32,}",
    "private key block": r"-----BEGIN (?:RSA |EC |OPENSSH |PGP |DSA )?PRIVATE KEY-----",
}
SECRET_RES = {name: re.compile(rx) for name, rx in SECRET_PATTERNS.items()}
ALLOW_MARKER = "spec-review:allow"
MAX_REPORTED_HITS = 5
HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
# Pinned so user config (noprefix, mnemonicPrefix, color, external diff) cannot reshape the headers.
GIT_DIFF = ["-c", "diff.noprefix=false", "-c", "diff.mnemonicPrefix=false", "diff",
            "--no-color", "--no-ext-diff", "--src-prefix=a/", "--dst-prefix=b/"]


DEP_AUDIT_CONFIGS = ("pyproject.toml", "setup.cfg", "tox.ini", "Makefile", "requirements*.txt",
                     ".pre-commit-config.yaml", ".gitlab-ci.yml", ".github/workflows/*.y*ml")
# safety is an ordinary English word, so it only counts as an invocation or a dependency spec.
DEP_AUDIT_TOOLS = {
    "pip-audit": re.compile(r"(?<![\w-])pip-audit(?![\w-])"),
    "safety": re.compile(r"(?<![\w-])safety\s+(?:check|scan)\b|^\s*[\"']?safety\s*(?:[=<>~!\[\"',]|$)",
                         re.M),
}
MANIFEST = re.compile(r"(^|/)(package\.json|pyproject\.toml|requirements[^/]*\.txt|go\.mod|Cargo\.toml)$")
MANIFEST_NOISE = re.compile(r"^\s*(?:[\[\]{}(),]*|\[[^\]]*\]|#.*|//.*)\s*$")
MAX_MANIFEST_LINES = 6


def cmd_run(seconds, marker, cmd):
    # A new session puts make/npm grandchildren in one killable group.
    proc = subprocess.Popen(cmd, start_new_session=True)
    try:
        return proc.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(proc.pid, sig)
                proc.wait(timeout=5)
                break
            except (ProcessLookupError, subprocess.TimeoutExpired):
                continue
        Path(marker).touch()
        print(f"gate: timed out after {seconds}s", file=sys.stderr)
        return 124


def cmd_npm_scripts(package_json):
    try:
        scripts = json.loads(Path(package_json).read_text(encoding="utf-8")).get("scripts") or {}
    except (OSError, ValueError, AttributeError):
        return 0
    for name in NPM_SCRIPTS:
        body = scripts.get(name)
        if not isinstance(body, str) or not body.strip():
            continue
        if name == "test" and NPM_STUB_TEST in body:
            continue
        print(name)
    return 0


def line_hits(text):
    if ALLOW_MARKER in text:
        return []
    return [name for name, rx in SECRET_RES.items() if rx.search(text)]


def git_diff(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *GIT_DIFF, *args],
                       capture_output=True, text=True, errors="replace")
    return r.stdout if r.returncode == 0 else ""


def diff_changes(diff_text):
    """Yield (path, sign, new_line_no, text) per +/- line; @@ counts keep header-shaped content as content."""
    path, after_minus_header = "?", False
    old_left = new_left = new_no = 0
    # split("\n"), not splitlines(): a \r or \f inside a line must not desync the counts.
    for line in diff_text.split("\n"):
        if old_left > 0 or new_left > 0:
            sign = line[:1]
            if sign == "+":
                yield path, "+", new_no, line[1:]
                new_no += 1
                new_left -= 1
            elif sign == "-":
                yield path, "-", None, line[1:]
                old_left -= 1
            elif sign != "\\":
                new_no += 1
                old_left -= 1
                new_left -= 1
            continue
        m = HUNK.match(line)
        if m:
            old_left, new_no, new_left = int(m[1] or 1), int(m[2]), int(m[3] or 1)
        elif after_minus_header and line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else "?"
        after_minus_header = line.startswith("--- ")


def added_lines(repo, base):
    for path, sign, line_no, text in diff_changes(git_diff(repo, "-U0", base)):
        if sign == "+":
            yield path, line_no, text


def untracked_lines(repo):
    listed = subprocess.run(["git", "-C", repo, "ls-files", "--others", "--exclude-standard", "-z"],
                            capture_output=True, text=True).stdout
    for rel in filter(None, listed.split("\0")):
        try:
            data = (Path(repo) / rel).read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8192]:
            continue
        for n, text in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
            yield rel, n, text


def cmd_secrets(repo, base):
    hits = []
    for source in (added_lines(repo, base), untracked_lines(repo)):
        for path, n, text in source:
            hits += [f"{path}:{n} — {name}" for name in line_hits(text)]
    if not hits:
        print("no secret-shaped tokens in the change")
        return 0
    for h in hits[:MAX_REPORTED_HITS]:
        print(h)
    if len(hits) > MAX_REPORTED_HITS:
        print(f"... and {len(hits) - MAX_REPORTED_HITS} more")
    return 1


def cmd_dep_audit(repo):
    root = Path(repo)
    texts = []
    for pattern in DEP_AUDIT_CONFIGS:
        for f in sorted(root.glob(pattern)):
            try:
                texts.append(f.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
    blob = "\n".join(texts)
    for tool, rx in DEP_AUDIT_TOOLS.items():
        if rx.search(blob):
            print(tool)
    return 0


def manifest_changes(repo, base):
    changes = [(path, sign, text.strip()) for path, sign, _, text in diff_changes(git_diff(repo, "-U0", base))
               if MANIFEST.search(path)]
    for path, _, text in untracked_lines(repo):
        if MANIFEST.search(path):
            changes.append((path, "+", text.strip()))
    return [(p, sign, t) for p, sign, t in changes if t and not MANIFEST_NOISE.match(t)]


def cmd_manifests(repo, base):
    changes = manifest_changes(repo, base)
    if not changes:
        return 0
    print(f"{len({p for p, _, _ in changes})} manifest(s) changed")
    for path, sign, text in changes[:MAX_MANIFEST_LINES]:
        print(f"{path}: {sign} {text}")
    if len(changes) > MAX_MANIFEST_LINES:
        print(f"... and {len(changes) - MAX_MANIFEST_LINES} more line(s)")
    return 0


def main(argv):
    if len(argv) >= 4 and argv[0] == "run":
        return cmd_run(float(argv[1]), argv[2], argv[3:])
    if len(argv) == 2 and argv[0] == "npm-scripts":
        return cmd_npm_scripts(argv[1])
    if len(argv) == 3 and argv[0] == "secrets":
        return cmd_secrets(argv[1], argv[2])
    if len(argv) == 2 and argv[0] == "dep-audit":
        return cmd_dep_audit(argv[1])
    if len(argv) == 3 and argv[0] == "manifests":
        return cmd_manifests(argv[1], argv[2])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
