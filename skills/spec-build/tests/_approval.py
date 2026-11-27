"""A real approval for test fixtures: the owner's signing key, the
machine's approver list, and `freeze.py --approve` run the way the owner
runs it — on a terminal, typing the confirmation. No fixture writes an
approval record by hand.

Importing this module points HOME at a throwaway directory for the rest
of the process: freeze.py reads the approver list and the default
signing key under it, so no test reads or writes the real ones.

Without ssh-keygen nothing can sign: a test that reaches for this
module skips with the reason."""

import atexit
import errno
import functools
import os
import pty
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
PRINCIPAL = "kit-owner"
SKIP_REASON = "ssh-keygen is not installed — nothing can sign an approval"
TIMEOUT = 120
PROMPT = re.compile(r"^Type exactly: (.+?)\s*$", re.M)
PASSPHRASE_PROMPT = "Enter passphrase"

HOME = Path(tempfile.mkdtemp(prefix="kit-approval-home-"))
atexit.register(shutil.rmtree, HOME, ignore_errors=True)
os.environ["HOME"] = str(HOME)


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


def _public(key: Path) -> str:
    return key.with_name(key.name + ".pub").read_text(
        encoding="utf-8").strip()


@functools.cache
def machine_list() -> Path:
    """The machine approver list, naming the fixture key."""
    path = HOME / ".config" / "spec-dev-kit" / "approvers"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{PRINCIPAL} {_public(signing_key())}\n",
                    encoding="utf-8")
    return path


def run_freeze(argv: list[str], answer: str | None = None,
               env: dict | None = None,
               passphrase: str | None = None) -> tuple[int, str]:
    """freeze.py on a terminal: (exit code, what the terminal showed).
    The phrase the prompt names is typed back, or `answer` is written
    in its place when given; `passphrase` answers ssh-keygen's prompt."""
    pid, master = pty.fork()
    if pid == 0:
        try:
            os.execve(sys.executable, [sys.executable, *argv],
                      dict(os.environ, **(env or {})))
        finally:
            os._exit(127)
    shown, answered, deadline = [], set(), time.monotonic() + TIMEOUT
    try:
        while True:
            left = deadline - time.monotonic()
            if left <= 0 or not select.select([master], [], [], left)[0]:
                raise AssertionError(
                    f"freeze.py did not finish in {TIMEOUT}s: "
                    f"{''.join(shown)[-2000:]}")
            try:
                chunk = os.read(master, 4096)
            except OSError as exc:
                if exc.errno == errno.EIO:
                    break
                raise
            if not chunk:
                break
            shown.append(chunk.decode("utf-8", errors="replace"))
            text = "".join(shown)
            prompt = PROMPT.search(text) if "phrase" not in answered else None
            if prompt:
                answered.add("phrase")
                os.write(master, (prompt.group(1) + "\n" if answer is None
                                  else answer).encode("utf-8"))
            if (passphrase and "passphrase" not in answered
                    and PASSPHRASE_PROMPT in text):
                answered.add("passphrase")
                os.write(master, (passphrase + "\n").encode("utf-8"))
    except BaseException:
        os.kill(pid, signal.SIGKILL)
        raise
    finally:
        _, status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(status), "".join(shown)


def publish(repo: Path, branch: str = "main") -> Path:
    """Give repo a bare origin whose default branch carries its HEAD —
    the remote CI and the delivered-record grandfather read."""
    def git(*args):
        subprocess.run(["git", "-C", str(repo), *args], check=True,
                       capture_output=True, text=True, timeout=120)

    bare = repo.parent / f"{repo.name}-origin.git"
    if not bare.exists():
        git("init", "-q", "--bare", str(bare))
        git("remote", "add", "origin", str(bare))
    git("push", "-q", "origin", f"HEAD:refs/heads/{branch}")
    git("symbolic-ref", "refs/remotes/origin/HEAD",
        f"refs/remotes/origin/{branch}")
    return bare


def approve(spec_dir: Path, repo: Path | None = None,
            review: str | None = None, force: bool = False,
            scripts: Path = SCRIPTS) -> None:
    """Approve spec_dir with the owner's key through the skill's own
    freeze.py; repo defaults to the spec dir's grandparent."""
    key = signing_key()
    machine_list()
    repo = repo if repo is not None else spec_dir.parent.parent
    argv = [str(scripts / "freeze.py"), str(spec_dir),
            "--approve", "--key", str(key), "--repo", str(repo)]
    if review:
        argv += ["--review", review]
    if force:
        argv += ["--force"]
    code, shown = run_freeze(argv)
    assert code == 0, f"freeze.py --approve refused the fixture: {shown}"
