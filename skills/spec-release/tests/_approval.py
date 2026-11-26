"""A real approval for test fixtures: the owner's signing key, the
repo's approver list, and `freeze.py --approve` run the way the owner
runs it. No fixture writes an approval record by hand.

Without ssh-keygen nothing can sign: a test that reaches for this
module skips with the reason."""

import atexit
import functools
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
PRINCIPAL = "kit-owner"
SKIP_REASON = "ssh-keygen is not installed — nothing can sign an approval"


@functools.cache
def signing_key() -> Path:
    """A passphrase-less ed25519 key, generated once per test run."""
    keygen = shutil.which("ssh-keygen")
    if keygen is None:
        raise unittest.SkipTest(SKIP_REASON)
    key = Path(tempfile.mkdtemp(prefix="kit-approval-key-")) / "id_ed25519"
    subprocess.run(
        [keygen, "-q", "-t", "ed25519", "-N", "", "-C", "kit-test",
         "-f", str(key)],
        check=True, capture_output=True, timeout=60)
    atexit.register(shutil.rmtree, key.parent, ignore_errors=True)
    return key


def approvers(repo: Path) -> Path:
    """The repo's approver list, naming the fixture key."""
    key = signing_key()
    public = key.with_name(key.name + ".pub").read_text(
        encoding="utf-8").strip()
    path = repo / "specs" / ".approvers"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{PRINCIPAL} {public}\n", encoding="utf-8")
    return path


def approve(spec_dir: Path, repo: Path | None = None,
            review: str | None = None, force: bool = False,
            scripts: Path = SCRIPTS) -> None:
    """Approve spec_dir with the owner's key through the skill's own
    freeze.py; repo defaults to the spec dir's grandparent."""
    key = signing_key()
    repo = repo if repo is not None else spec_dir.parent.parent
    approvers(repo)
    argv = [sys.executable, str(scripts / "freeze.py"), str(spec_dir),
            "--approve", "--key", str(key), "--repo", str(repo)]
    if review:
        argv += ["--review", review]
    if force:
        argv += ["--force"]
    run = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, (
        f"freeze.py --approve refused the fixture: {run.stdout}{run.stderr}")
