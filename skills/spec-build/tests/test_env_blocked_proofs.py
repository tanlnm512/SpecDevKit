"""ENV-BLOCKED proofs (spec-build D-047): a proof whose environment is
missing — a program that does not resolve, a Docker engine that does not
answer, a variable the command names but the shell lacks, or a run that
ends exit 126/127 with `command not found` — never ran, so it reads
ENV-BLOCKED naming what is missing: not a pass and not charged as a
failure, but red while it stands unruled. The owner's `- Proof: <proof
label> — <ruling>` line in the delivery block turns the row RULED and
lets dod gate 1 pass; a FAIL is never rulable this way. The tests pin
the evidence rules (each decided without guessing at the command's
merit — the shell's exit code, never a phrase in the output), the FAIL
pass-through, the ruling at both tiers (TC-### at full, the task id at
tiny), preflight's read of a settled ruling, land's refusal and its
`--allow-pending` escape, and the block draft.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SKILL = HERE.parent
_SCRIPTS = SKILL / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from test_mark import (  # noqa: E402
    entry_text,
    hand_fixture,
    make_wave,
    run_mark,
)
from test_execute_gates import write  # noqa: E402
from test_pending_proofs import GHOST, ghost_fixture  # noqa: E402

_spec = importlib.util.spec_from_file_location("audit", _SCRIPTS / "audit.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

AUDIT = _SCRIPTS / "audit.py"
GONE = "./no-such-proof.sh"          # a relative program that does not exist
TOKEN = "SPEC_KIT_PROOF_TOKEN"       # a variable the tests control


def env_fixture(tmp: Path, name: str, cmd: str) -> Path:
    """A hand docset whose T001 proof is `cmd` — T002 keeps its green
    one-liner, so a full proofs run always has one runnable command."""
    spec = hand_fixture(tmp, name)
    test = spec / "test.md"
    write(test, test.read_text(encoding="utf-8").replace(
        "`python3 -c 'print(\"HI\")'`", f"`{cmd}`"))
    return spec


TINY_SPEC = """# Spec: {name}

**Status**: executing
**Tier**: tiny
**Effort**: standard

## What
One task whose acceptance proof needs a program this machine lacks.

## Why
Pins the tiny-tier proof surface: the proofs are the § Tasks Accept
commands, keyed by task id.

## Requirements
- **FR-001**: The system shall do the thing.

## Tasks
- [ ] T001 Do the thing (FR-001) [P]
  Touches: `thing.py`
  Accept: `{cmd}`

Delivered: commit @ -
"""


def tiny_fixture(tmp: Path, name: str, cmd: str = GONE) -> Path:
    """A Tier: tiny one-file docset whose T001 Accept proof is `cmd` —
    spec.md is the whole docset and the status holder; laid out under
    specs/ so the CLI's repo root (spec.parent.parent) is `tmp`."""
    spec = tmp / "specs" / name
    spec.mkdir(parents=True)
    write(spec / "spec.md", TINY_SPEC.format(name=name, cmd=cmd))
    return spec


class EnvBlockEvidenceTests(unittest.TestCase):
    """The evidence rules on env_block_reason / run_env_block: an outcome
    only when the environment demonstrably lacks something."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="envblock-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.repo = self._tmp / "repo"
        self.repo.mkdir()
        os.environ.pop(TOKEN, None)
        self.addCleanup(os.environ.pop, TOKEN, None)

    def tearDown(self):
        audit._DOCKER_UP = None

    def test_a_program_that_does_not_resolve_blocks(self):
        self.assertEqual(audit.env_block_reason("spec-kit-gone-tool --x", self.repo),
                         "program `spec-kit-gone-tool`")
        self.assertEqual(audit.env_block_reason(GONE, self.repo),
                         f"program `{GONE}`")

    def test_a_resolvable_program_blocks_on_nothing(self):
        self.assertIsNone(audit.env_block_reason("python3 -c 'print(1)'", self.repo))

    def test_an_unset_named_variable_blocks(self):
        cmd = f'python3 -c \'print("${TOKEN}")\''
        self.assertEqual(audit.env_block_reason(cmd, self.repo), f"env var {TOKEN}")

    def test_a_set_variable_blocks_on_nothing(self):
        os.environ[TOKEN] = "s3cret"
        cmd = f'python3 -c \'print("${TOKEN}")\''
        self.assertIsNone(audit.env_block_reason(cmd, self.repo))

    def test_a_variable_with_a_fallback_expansion_blocks_on_nothing(self):
        cmd = f'python3 -c \'print("${{{TOKEN}:-fallback}}")\''
        self.assertIsNone(audit.env_block_reason(cmd, self.repo))

    def test_a_docker_lean_names_the_engine_when_none_answers(self):
        # python3 resolves everywhere, so the lean check is what decides
        audit._DOCKER_UP = False
        self.assertEqual(
            audit.env_block_reason("python3 -c 'docker compose up -d'", self.repo),
            "docker engine")
        self.assertEqual(
            audit.env_block_reason("python3 -c 'testcontainers.up()'", self.repo),
            "docker engine")

    def test_an_answering_engine_blocks_on_nothing(self):
        audit._DOCKER_UP = True
        self.assertIsNone(
            audit.env_block_reason("python3 -c 'docker compose up -d'", self.repo))

    def test_run_evidence_126_and_127_block(self):
        self.assertEqual(
            audit.run_env_block(127, "bash: gone: command not found"),
            "program (exit 127: command not found)")
        self.assertEqual(audit.run_env_block(126, ""), "program (exit 126: not executable)")
        self.assertEqual(
            audit.run_env_block(127, "sh: 1: gone: not found"),
            "program (exit 127: not found)")

    def test_a_red_exit_with_the_phrase_in_its_output_blocks_on_nothing(self):
        # the shell's exit code is the evidence, never the output's
        # wording: a wrapper that continues past a missing sub-command
        # exits nonzero with `command not found` in its output — the
        # change under proof ran and failed, it is not an environment
        # gap (a FAIL is never rulable)
        self.assertIsNone(
            audit.run_env_block(1, "scripts/run.sh: line 3: "
                                  "make-check: command not found"))
        self.assertIsNone(audit.run_env_block(2, "x: command not found"))

    def test_an_ordinary_red_exit_is_run_evidence_for_nothing(self):
        self.assertIsNone(audit.run_env_block(3, "AssertionError: nope"))
        self.assertIsNone(audit.run_env_block(0, "ok"))


class ProofRunTests(unittest.TestCase):
    """`proofs --run` prints the outcome with what is missing and exits 1
    while it stands unruled; an ordinary red exit stays FAIL."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="envblock-cli-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"

    def audit_cli(self, spec: Path, *args: str, path: str | None = None):
        env = dict(os.environ, KIT_TELEMETRY_DIR=str(self.tel),
                   KIT_TELEMETRY="on")
        if path:
            env["PATH"] = f"{path}:{os.environ['PATH']}"
        return subprocess.run(
            [sys.executable, str(AUDIT), args[0], str(spec), *args[1:]],
            capture_output=True, text=True, timeout=300, env=env)

    def test_a_missing_program_reads_env_blocked_naming_it(self):
        spec = env_fixture(self._tmp, "gone", GONE)
        r = self.audit_cli(spec, "proofs", "--run")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("ENV-BLOCKED", r.stdout)
        self.assertIn(f"missing: program `{GONE}`", r.stdout)
        self.assertNotRegex(r.stdout, r"(?m)^\s+PASS\s+TC-001")
        self.assertIn("not a pass and not charged as a failure", r.stdout)

    def test_a_docker_engine_that_does_not_answer_reads_env_blocked(self):
        bin_dir = self._tmp / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "docker"
        write(fake, "#!/bin/sh\n"
              "echo 'Cannot connect to the Docker daemon' >&2\nexit 1\n")
        fake.chmod(0o755)
        spec = env_fixture(self._tmp, "docker", "docker run --rm alpine true")
        r = self.audit_cli(spec, "proofs", "--run", path=str(bin_dir))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("ENV-BLOCKED", r.stdout)
        self.assertIn("missing: docker engine", r.stdout)

    def test_a_program_the_shell_never_started_reads_env_blocked(self):
        # the first word resolves; the inner program does not — the run's
        # own exit-127 evidence decides, whatever the shell prints
        spec = env_fixture(self._tmp, "inner", "sh -c 'spec-kit-gone-inner --run'")
        r = self.audit_cli(spec, "proofs", "--run")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("ENV-BLOCKED", r.stdout)
        self.assertIn("missing: program (exit", r.stdout)
        self.assertNotRegex(r.stdout, r"(?m)^\s+FAIL\s+TC-001")

    def test_an_ordinary_red_exit_stays_fail(self):
        spec = env_fixture(self._tmp, "red", "python3 -c 'import sys; sys.exit(3)'")
        r = self.audit_cli(spec, "proofs", "--run")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"(?m)^\s+FAIL\s+TC-001")
        self.assertNotIn("ENV-BLOCKED", r.stdout)

    def test_a_wrappers_red_exit_with_the_phrase_stays_fail(self):
        # a wrapper that continues past a missing sub-command and exits
        # nonzero: the proof ran and failed — its exit code is the
        # verdict, the phrase in its output is nothing
        wrapper = 'sh -c \'echo "wrapper: command not found" >&2; exit 1\''
        spec = env_fixture(self._tmp, "wrap", wrapper)
        r = self.audit_cli(spec, "proofs", "--run")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"(?m)^\s+FAIL\s+TC-001")
        self.assertNotIn("ENV-BLOCKED", r.stdout)


class RulingTests(unittest.TestCase):
    """The D-037 shape: the owner's `- Proof: TC-### — <ruling>` line
    turns the row RULED and lets dod gate 1 pass; without it both stay
    red. A FAIL never reads from the ruling."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="envblock-ruling-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"

    def audit_cli(self, spec: Path, *args: str):
        env = dict(os.environ, KIT_TELEMETRY_DIR=str(self.tel),
                   KIT_TELEMETRY="on")
        return subprocess.run(
            [sys.executable, str(AUDIT), args[0], str(spec), *args[1:]],
            capture_output=True, text=True, timeout=300, env=env)

    def with_block(self, spec: Path, *lines: str) -> Path:
        task = spec / "task.md"
        write(task, task.read_text(encoding="utf-8")
              + "\n**Delivered**: commit @ -\n" + "\n".join(lines) + "\n")
        return spec

    def test_dod_gate1_stays_red_while_unruled(self):
        spec = env_fixture(self._tmp, "open", GONE)
        dod = self.audit_cli(spec, "dod")
        self.assertRegex(dod.stdout, r"(?m)^\s+1 PROOF auto\s+FAIL\s")
        self.assertIn("environment-blocked", dod.stdout)
        self.assertIn("ENV-BLOCKED", dod.stdout)

    def test_a_ruling_turns_the_row_ruled_and_gate1_passes(self):
        spec = self.with_block(
            env_fixture(self._tmp, "ruled", GONE),
            "- Proof: TC-001 — this session lacks the program; re-run in "
            "CI where it exists (D-047)")
        r = self.audit_cli(spec, "proofs", "--run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"(?m)^\s+RULED\s+TC-001")
        self.assertIn("ruled in the delivery block", r.stdout)
        self.assertNotIn("ENV-BLOCKED  TC-001", r.stdout)
        dod = self.audit_cli(spec, "dod")
        self.assertRegex(dod.stdout, r"(?m)^\s+1 PROOF auto\s+PASS\s")
        self.assertIn("ruled in the delivery block", dod.stdout)

    def test_a_ruling_never_turns_a_fail_into_ruled(self):
        spec = self.with_block(
            env_fixture(self._tmp, "redruled", "python3 -c 'import sys; sys.exit(3)'"),
            "- Proof: TC-001 — owner rules to proceed anyway")
        r = self.audit_cli(spec, "proofs", "--run")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"(?m)^\s+FAIL\s+TC-001")
        self.assertNotIn("RULED", r.stdout)

    def test_a_ruling_never_turns_a_wrappers_fail_into_ruled(self):
        wrapper = 'sh -c \'echo "wrapper: command not found" >&2; exit 1\''
        spec = self.with_block(env_fixture(self._tmp, "wrapruled", wrapper),
                               "- Proof: TC-001 — owner rules to proceed anyway")
        r = self.audit_cli(spec, "proofs", "--run")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"(?m)^\s+FAIL\s+TC-001")
        self.assertNotIn("RULED", r.stdout)
        self.assertNotIn("ENV-BLOCKED", r.stdout)


class TinyRulingTests(unittest.TestCase):
    """At Tier: tiny the proofs are the § Tasks Accept commands, keyed by
    task id — the ruling line carries the same id (`- Proof: T001 —`),
    the block drafts it, and proofs/dod read it back RULED."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="envblock-tiny-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"

    def audit_cli(self, spec: Path, *args: str):
        env = dict(os.environ, KIT_TELEMETRY_DIR=str(self.tel),
                   KIT_TELEMETRY="on")
        return subprocess.run(
            [sys.executable, str(AUDIT), args[0], str(spec), *args[1:]],
            capture_output=True, text=True, timeout=300, env=env)

    def with_block(self, spec: Path, *lines: str) -> Path:
        holder = spec / "spec.md"
        write(holder, holder.read_text(encoding="utf-8")
              + "\n" + "\n".join(lines) + "\n")
        return spec

    def test_an_unruled_tiny_proof_reads_env_blocked_under_its_task_id(self):
        spec = tiny_fixture(self._tmp, "tiny-open")
        r = self.audit_cli(spec, "proofs", "--run")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("ENV-BLOCKED  T001", r.stdout)
        self.assertIn(f"missing: program `{GONE}`", r.stdout)
        # the guidance names the id shape this tier keys its proofs under
        self.assertIn("- Proof: T### — <ruling>", r.stdout)
        self.assertNotIn("TC-###", r.stdout)

    def test_a_task_id_ruling_turns_the_row_ruled_and_gate1_passes(self):
        spec = self.with_block(tiny_fixture(self._tmp, "tiny-ruled"),
                               "- Proof: T001 — this session lacks the "
                               "program; re-run in CI where it exists (D-047)")
        r = self.audit_cli(spec, "proofs", "--run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("RULED    T001", r.stdout)
        self.assertIn("ruled in the delivery block", r.stdout)
        self.assertNotIn("ENV-BLOCKED", r.stdout)
        dod = self.audit_cli(spec, "dod")
        self.assertRegex(dod.stdout, r"(?m)^\s+1 PROOF auto\s+PASS\s")
        self.assertIn("ruled in the delivery block", dod.stdout)

    def test_the_block_drafts_the_task_id_and_the_draft_reads_ruled(self):
        spec = tiny_fixture(self._tmp, "tiny-blk")
        subprocess.run(["git", "-C", str(spec.parent.parent), "init", "-q"],
                       check=True, capture_output=True)
        r = self.audit_cli(spec, "block")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("- Proof: T001 — <ruling>", r.stdout)
        # paste the drafted line under the Delivered field — the same
        # move the delivery record makes — and the row reads RULED
        self.with_block(spec, "- Proof: T001 — environment cannot be "
                              "supplied this session (D-047)")
        r = self.audit_cli(spec, "proofs", "--run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("RULED    T001", r.stdout)


class LandGateTests(unittest.TestCase):
    """land treats an environment-blocked proof like a pending one: no
    proof ran, so it refuses unless --allow-pending, saying what is
    missing."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="envblock-land-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"

    def test_land_refuses_and_names_the_missing_environment(self):
        spec = env_fixture(self._tmp, "refuse", GONE)
        make_wave(spec, "T001")
        run_mark(spec, "claim", "--wave", str(spec / "spawns" / "wave-4"),
                 tel=self.tel)
        r = run_mark(spec, "land", "T001",
                     "--digest", "digest: task T001 · status implemented",
                     tel=self.tel)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("none of T001's proofs ran", r.stderr)
        self.assertIn("ENV-BLOCKED", r.stderr)
        self.assertIn(f"missing: program `{GONE}`", r.stderr)
        self.assertIn("--allow-pending", r.stderr)
        self.assertIn("(in-progress)", entry_text(spec, "T001"))

    def test_allow_pending_lands_loudly(self):
        spec = env_fixture(self._tmp, "allow", GONE)
        make_wave(spec, "T001")
        run_mark(spec, "claim", "--wave", str(spec / "spawns" / "wave-4"),
                 tel=self.tel)
        r = run_mark(spec, "land", "T001", "--allow-pending",
                     "--digest", "digest: task T001 · status implemented",
                     tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("lands unproven", r.stderr)
        self.assertIn("env-blocked", r.stderr)
        self.assertIn("(implemented)", entry_text(spec, "T001").splitlines()[0])


class BlockDraftTests(unittest.TestCase):
    """`block` drafts one `- Proof: TC-### — <ruling>` line per unruled
    environment-blocked proof — never for a PENDING one."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="envblock-blk-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def block(self, spec: Path):
        # block drafts from a repository's change surface: init one
        # around the fixture (no commit — untracked surface is enough)
        subprocess.run(["git", "-C", str(spec.parent.parent), "init", "-q"],
                       check=True, capture_output=True)
        return subprocess.run([sys.executable, str(AUDIT), "block", str(spec)],
                              capture_output=True, text=True, timeout=120)

    def test_block_drafts_a_proof_line_per_env_blocked_proof(self):
        r = self.block(env_fixture(self._tmp, "blk", GONE))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("- Proof: TC-001 — <ruling>", r.stdout)

    def test_block_does_not_draft_a_pending_proof(self):
        r = self.block(ghost_fixture(self._tmp, "pend"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("- Proof:", r.stdout)


class PreflightTests(unittest.TestCase):
    """preflight names which proofs would be ENV-BLOCKED and the ruling
    as the way to proceed when the environment cannot be supplied."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="envblock-pre-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def preflight(self, spec: Path):
        return subprocess.run([sys.executable, str(AUDIT), "preflight",
                               str(spec)],
                              capture_output=True, text=True, timeout=120)

    def test_preflight_names_the_env_blocked_proof_and_the_ruling(self):
        r = self.preflight(env_fixture(self._tmp, "pre", GONE))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("NO-GO", r.stdout)
        self.assertIn(f"TC-001 would be ENV-BLOCKED — missing: program `{GONE}`",
                      r.stdout)
        self.assertIn("- Proof: TC-### — <ruling>", r.stdout)

    def test_a_recorded_ruling_reads_ruled_and_stops_being_a_no_go(self):
        # the owner's ruling settled the stop — preflight reports it
        # RULED instead of a permanent NO-GO (the delivery block is the
        # way to proceed when the environment cannot be supplied)
        spec = env_fixture(self._tmp, "ruled-pre", GONE)
        task = spec / "task.md"
        write(task, task.read_text(encoding="utf-8")
              + "\n**Delivered**: commit @ -\n"
                "- Proof: TC-001 — CI owns this program; the gap is "
                "accepted (D-047)\n")
        r = self.preflight(spec)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("RULED  TC-001 would be ENV-BLOCKED", r.stdout)
        self.assertIn("ruled in the delivery block", r.stdout)
        self.assertIn("preflight: GO", r.stdout)
        self.assertNotIn("NO-GO", r.stdout)

    def test_a_recorded_ruling_reads_ruled_at_tiny_too(self):
        spec = tiny_fixture(self._tmp, "tiny-ruled-pre")
        holder = spec / "spec.md"
        write(holder, holder.read_text(encoding="utf-8")
              + "\n- Proof: T001 — CI owns this program; the gap is "
                "accepted (D-047)\n")
        r = self.preflight(spec)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("RULED  T001 would be ENV-BLOCKED", r.stdout)
        self.assertIn("preflight: GO", r.stdout)

    def test_preflight_stays_go_without_env_problems(self):
        r = self.preflight(hand_fixture(self._tmp, "go"))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("GO", r.stdout)
        self.assertNotIn("ENV-BLOCKED", r.stdout)


if __name__ == "__main__":
    unittest.main()
