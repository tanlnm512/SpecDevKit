"""The delivery pass's instruments run against the real CLIs: the tiny
tier's one-file contract, failed-proof evidence, the mutation surface,
and the archive gate."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
AUDIT = SCRIPTS / "audit.py"
ARCHIVE = SCRIPTS / "archive.sh"
TINY = SKILL / "examples" / "spec-tiny-delivered"
ENV = {**os.environ, "KIT_TELEMETRY": "off"}

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import audit  # noqa: E402

CALC = '''import sys


def multiply(a, b):
    return a * b


if __name__ == "__main__":
    try:
        a, b = int(sys.argv[2]), int(sys.argv[3])
    except ValueError:
        sys.stderr.write("error: integers only\\n")
        sys.exit(2)
    sys.stdout.write(f"{multiply(a, b)}\\n")
'''


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), "-c", "user.name=kit",
                    "-c", "user.email=kit@example.com", *args],
                   check=True, capture_output=True)


def run(*argv, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run([*map(str, argv)], cwd=str(cwd), env=ENV,
                          capture_output=True, text=True)


class DeliveryPassTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="delivery-pass-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        git(self.root, "init", "-q")
        (self.root / "README").write_text("seed\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base")

    def tiny_spec(self, name: str = "tiny-delivered-demo") -> Path:
        spec = self.root / "specs" / name
        shutil.copytree(TINY, spec)
        return spec

    def test_dod_proves_counts_and_scopes_a_tiny_spec(self):
        spec = self.tiny_spec()
        (self.root / "calc.py").write_text(CALC, encoding="utf-8")
        (self.root / "test_calc.py").write_text(
            "import calc\n\n\ndef test_product():\n"
            "    assert calc.multiply(6, 7) == 42\n", encoding="utf-8")
        (self.root / "requirements.txt").write_text("left-pad==1.0\n", encoding="utf-8")
        r = run(sys.executable, AUDIT, "dod", spec, cwd=self.root)
        self.assertIn("REGRESSION    NONE    no repo checks detected", r.stdout)
        self.assertIn("DOCS IMPACT   FAIL    no `Docs impact:` line", r.stdout)
        self.assertIn("deps: requirements.txt: + left-pad==1.0", r.stdout)
        self.assertEqual(r.returncode, 1, r.stdout)

        (self.root / "requirements.txt").unlink()
        (self.root / "Makefile").write_text(
            "test:\n\t@python3 -c 'import calc; assert calc.multiply(6, 7) == 42'\n",
            encoding="utf-8")
        git(self.root, "add", "Makefile")
        git(self.root, "commit", "-qm", "the repo's own check")
        (spec / "notes").mkdir()
        (spec / "notes" / "delivery.md").write_text(
            "Docs impact: none — no user-facing docs describe the calculator\n",
            encoding="utf-8")
        r = run(sys.executable, AUDIT, "dod", spec, cwd=self.root)
        self.assertIn("PROOF auto    PASS    2/2 proofs green", r.stdout)
        self.assertIn("REGRESSION    PASS    1 repo check(s) green: make test", r.stdout)
        self.assertIn("COMPLETENESS  PASS    2/2 ticked", r.stdout)
        self.assertIn("SCOPE         PASS    0 unmentioned", r.stdout)
        self.assertIn("ROLLBACK      N/A     Tier: tiny", r.stdout)
        self.assertIn("deps: no dependency manifest changed", r.stdout)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_hygiene_suspect_is_ruled_in_the_delivery_block_not_silenced(self):
        spec = self.tiny_spec()
        (self.root / "calc.py").write_text(CALC.replace("sys.stdout.write(", "print(")
                                           .replace('}\\n")', '}")'), encoding="utf-8")
        args = ("--base", "HEAD", "--repo", self.root)
        r = run(sys.executable, AUDIT, "clean", spec, *args, cwd=self.root)
        self.assertIn("SUSPECT  calc.py:", r.stdout)
        r = run(sys.executable, AUDIT, "dod", spec, *args, "--dry-run", cwd=self.root)
        self.assertRegex(r.stdout, r"HYGIENE\s+FAIL\s+1 suspect")

        holder = spec / "spec.md"
        holder.write_text(holder.read_text(encoding="utf-8")
                          + "- Hygiene: calc.py [debug print] — the CLI's own product output\n",
                          encoding="utf-8")
        r = run(sys.executable, AUDIT, "clean", spec, *args, cwd=self.root)
        self.assertIn("RULED    calc.py:", r.stdout)
        self.assertNotIn("SUSPECT", r.stdout)
        r = run(sys.executable, AUDIT, "dod", spec, *args, "--dry-run", cwd=self.root)
        self.assertRegex(r.stdout, r"HYGIENE\s+PASS\s+0 suspect\(s\) in added lines \(1 ruled")

        holder.write_text(holder.read_text(encoding="utf-8").replace("calc.py [", "other.py ["),
                          encoding="utf-8")
        r = run(sys.executable, AUDIT, "dod", spec, *args, "--dry-run", cwd=self.root)
        self.assertRegex(r.stdout, r"HYGIENE\s+FAIL")

    def test_delivery_note_gates_rollback_rows_and_the_bugfix_red_run(self):
        spec = self.root / "specs" / "demo"
        (spec / "notes").mkdir(parents=True)
        (spec / "spec.md").write_text("# Spec: demo\n\n**Type**: bugfix\n", encoding="utf-8")
        (spec / "test.md").write_text("## TC-001 restore\n", encoding="utf-8")
        (spec / "tech-spec.md").write_text(
            "## Quality, threats, and rollback\n"
            "| Requirement | Design consequence | Rollback or verification |\n"
            "|---|---|---|\n"
            "| NFR-001 | backup first | restore drill, TC-001 |\n"
            "| NFR-002 | flag | flip the flag off |\n"
            "| NFR-003 | none | — |\n\n## Code guide\n| A | B |\n|---|---|\n| x | y |\n",
            encoding="utf-8")
        (spec / "plan.md").write_text(
            "## Delivery\n### Rollout\n- **Exposure**: 10% of tenants\n"
            "- **Migration order**: <what runs before>\n", encoding="utf-8")
        note = spec / "notes" / "delivery.md"
        note.write_text("Docs impact: none — internal\n", encoding="utf-8")
        gates = {n: (st, dt) for n, st, dt in audit.delivery_gates(spec, self.root, [], True)}
        self.assertEqual(gates["ROLLBACK"][0], "FAIL")
        self.assertIn("for: NFR-002, Exposure", gates["ROLLBACK"][1])
        self.assertEqual(gates["WORK TYPE"][0], "FAIL")

        note.write_text("Docs impact: none — internal\n"
                        "Rollback: NFR-002 — flag flip proven in staging by hand\n"
                        "Rollback: Exposure — tenant cohort is the user's call\n", encoding="utf-8")
        (spec / "notes" / "T001.md").write_text(
            "## Regression test (red before fix)\n`pytest -k crash` exit 1\n", encoding="utf-8")
        gates = {n: st for n, st, _ in audit.delivery_gates(spec, self.root, [], True)}
        self.assertEqual(gates, {"DOCS IMPACT": "PASS", "ROLLBACK": "PASS", "WORK TYPE": "PASS"})

    def test_verified_column_cannot_run_ahead_of_the_delivered_record(self):
        spec = self.root / "specs" / "demo"
        spec.mkdir(parents=True)
        (spec / "spec.md").write_text("# Spec: demo\n\n**Type**: feature\n",
                                      encoding="utf-8")
        burndown = ("## Burndown\n"
                    "| Phase | Total | Done | Verified |\n"
                    "|-------|-------|------|----------|\n"
                    "| 1     | 1     | 1    | pass     |\n"
                    "| 2     | 1     | 1    |          |\n"
                    "| **Σ** | 2     | 2    |          |\n")
        (spec / "task.md").write_text(f"# Tasks: demo\n\n{burndown}", encoding="utf-8")
        r = run(sys.executable, AUDIT, "dod", spec, cwd=self.root)
        self.assertIn("VERIFIED      FAIL    `pass` on 1 with no `Delivered:` record",
                      r.stdout)

        (spec / "task.md").write_text(
            f"# Tasks: demo\n\nDelivered: commit @ abc1234\n\n{burndown}",
            encoding="utf-8")
        r = run(sys.executable, AUDIT, "dod", spec, cwd=self.root)
        self.assertIn("VERIFIED      FAIL    delivered but Verified not `pass` on 2",
                      r.stdout)

        all_green = burndown.replace("| 2     | 1     | 1    |          |",
                                     "| 2     | 1     | 1    | pass     |")
        (spec / "task.md").write_text(
            f"# Tasks: demo\n\nDelivered: commit @ abc1234\n\n{all_green}",
            encoding="utf-8")
        r = run(sys.executable, AUDIT, "dod", spec, cwd=self.root)
        self.assertIn("VERIFIED      PASS    2 phase row(s) `pass` with the "
                      "`Delivered:` record", r.stdout)

    def test_a_failed_proof_prints_its_exit_and_stderr(self):
        spec = self.root / "specs" / "demo"
        spec.mkdir(parents=True)
        (spec / "test.md").write_text(
            "## TC-001 fails loudly\n- **Pass condition**: "
            "`python3 -c \"import sys; sys.stderr.write('boom-evidence'); "
            "sys.exit(3)\"` exits 0\n", encoding="utf-8")
        r = run(sys.executable, AUDIT, "proofs", spec, "--run", cwd=self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("(exit 3, expected 0)", r.stdout)
        self.assertIn("boom-evidence", r.stdout)

    def test_mutation_spares_lines_the_diff_did_not_change(self):
        spec = self.root / "specs" / "demo"
        spec.mkdir(parents=True)
        (spec / "test.md").write_text(
            "## TC-001 suite\n- **Pass condition**: `true` exits 0\n",
            encoding="utf-8")
        mod = self.root / "mod.py"
        mod.write_text("def old(a):\n    return a + 1\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "old")
        mod.write_text(mod.read_text() + "\n\ndef new(a):\n    return a * 2\n",
                       encoding="utf-8")
        r = run(sys.executable, AUDIT, "mutate", spec, "--repo", self.root,
                cwd=self.root)
        self.assertIn("mod.py:6", r.stdout)
        self.assertNotIn("mod.py:2", r.stdout)

    def test_each_mutant_flips_its_own_site(self):
        mutants, _ = audit.python_mutants("x = a < 1 or a > 9\n", "m.py")
        compares = [src for _, desc, src in mutants if "→" in desc
                    and desc.split("→")[0] in ("Lt", "Gt")]
        self.assertEqual(len(set(compares)), 2, compares)

    def test_archive_requires_the_delivery_record_and_marks_index_done(self):
        spec = self.tiny_spec("tiny-demo")
        index = self.root / "specs" / "INDEX.md"
        index.write_text("# Specs index\n- [tiny-demo](tiny-demo/spec.md) "
                         "— done · feature · tiny\n", encoding="utf-8")
        spec_md = spec / "spec.md"
        delivered = spec_md.read_text(encoding="utf-8")
        spec_md.write_text(delivered.replace("Delivered: commit @ -", ""),
                           encoding="utf-8")
        r = run("bash", ARCHIVE, "tiny-demo", self.root, cwd=self.root)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Delivered", r.stderr)
        self.assertTrue(spec.is_dir())

        spec_md.write_text(delivered, encoding="utf-8")
        r = run("bash", ARCHIVE, "tiny-demo", self.root, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        line = index.read_text(encoding="utf-8").splitlines()[1]
        self.assertRegex(line, r"\(archive/[\d-]+-tiny-demo/spec\.md\) — done ")
        retro_md = next((self.root / "specs" / "archive").glob("*-tiny-demo/retro.md"))
        self.assertIn("| T002 | ticked | 0 |", retro_md.read_text(encoding="utf-8"))
        r = run(sys.executable, AUDIT, "archived", "--repo", self.root,
                cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_retro_records_rounds_deviations_and_parked_and_rolls_decisions_up(self):
        spec = self.root / "specs" / "demo"
        (spec / "notes").mkdir(parents=True)
        (spec / "approvals").mkdir()
        (spec / "spec.md").write_text("# Spec: demo\n", encoding="utf-8")
        approved = "## Decisions\n### D-001: Pure function\n- why\n"
        (spec / "tech-spec.md").write_text(
            approved + "### D-002: Cache dropped mid-build\n", encoding="utf-8")
        (spec / "approvals" / "approval.md").write_text(
            f"- `tech-spec.md`: prefix sha256:{'0' * 64} length:{len(approved.encode())}\n",
            encoding="utf-8")
        (spec / "task.md").write_text(
            "## Phase 1: Multiply\n- [x] T001 Multiply (FR-001) (fixed 2/5)\n"
            "- [x] T002 Tests (FR-001)\n"
            "Delivered: commit @ abc1234\n"
            "- Docs impact: README.md\n"
            "- Rollback: NFR-001 — revert the module commit\n", encoding="utf-8")
        (spec / "notes" / "delivery.md").write_text(
            "Docs impact: superseded note\n", encoding="utf-8")
        (self.root / "specs" / "BACKLOG.md").write_text(
            "# Backlog\n\n- demo — jitter untested (source: auditor WARN 2)\n"
            "- other — not ours (source: deviation)\n", encoding="utf-8")
        for _ in range(2):
            r = run(sys.executable, SCRIPTS / "retro.py", spec, "demo", self.root, cwd=self.root)
            self.assertEqual(r.returncode, 0, r.stderr)
        retro = (spec / "retro.md").read_text(encoding="utf-8")
        self.assertIn("| T001 | ticked | 2 |", retro)
        self.assertIn("Fix rounds: 2 across 2 task(s).", retro)
        self.assertIn("- D-001: Pure function\n- D-002: Cache dropped mid-build (deviation", retro)
        self.assertIn("Docs impact: README.md", retro)
        self.assertIn("Rollback: NFR-001 — revert the module commit", retro)
        self.assertNotIn("superseded note", retro)
        self.assertIn("- demo — jitter untested", retro)
        self.assertNotIn("not ours", retro)
        rolled = (self.root / "specs" / "context" / "decisions.md").read_text(encoding="utf-8")
        self.assertEqual([l for l in rolled.splitlines() if l.startswith("- ")],
                         ["- demo D-001: Pure function", "- demo D-002: Cache dropped mid-build"])

        (spec / "retro.md").unlink()
        (spec / "task.md").write_text(
            "## Phase 1: Multiply\n- [x] T001 Multiply (FR-001) (fixed 2/5)\n"
            "- [x] T002 Tests (FR-001)\n"
            "Delivered: commit @ abc1234\n", encoding="utf-8")
        r = run(sys.executable, SCRIPTS / "retro.py", spec, "demo", self.root, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        retro = (spec / "retro.md").read_text(encoding="utf-8")
        self.assertIn("Docs impact: superseded note", retro)


    def test_retro_written_before_delivery_is_refreshed_and_counts_each_round_once(self):
        spec = self.root / "specs" / "demo"
        (spec / "notes").mkdir(parents=True)
        (spec / "spec.md").write_text("# Spec: demo\n", encoding="utf-8")
        (spec / "notes" / "T001.md").write_text(
            "## Fix round 1\n\n## Fix round 1 \u2014 attempt\n\n## Fix round 1 \u2014 closed\n",
            encoding="utf-8")
        (spec / "task.md").write_text(
            "## Phase 1: Multiply\n- [ ] T001 Multiply (FR-001) (implemented) (fixed 1/5)\n",
            encoding="utf-8")
        r = run(sys.executable, SCRIPTS / "retro.py", spec, "demo", self.root, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        retro = (spec / "retro.md").read_text(encoding="utf-8")
        self.assertIn("| T001 | open | 1 |", retro)
        self.assertIn("Delivered: commit @ -", retro)

        (spec / "task.md").write_text(
            "## Phase 1: Multiply\n- [x] T001 Multiply (FR-001) (fixed 1/5)\n"
            "Delivered: commit @ abc1234\n", encoding="utf-8")
        (self.root / "specs" / "BACKLOG.md").write_text(
            "- demo \u2014 jitter untested (source: auditor WARN 2)\n", encoding="utf-8")
        r = run(sys.executable, SCRIPTS / "retro.py", spec, "demo", self.root, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        retro = (spec / "retro.md").read_text(encoding="utf-8")
        self.assertIn("| T001 | ticked | 1 |", retro)
        self.assertIn("- demo \u2014 jitter untested", retro)
        self.assertIn("Delivered: commit @ abc1234", retro)

        before = retro
        r = run(sys.executable, SCRIPTS / "retro.py", spec, "demo", self.root, cwd=self.root)
        self.assertIn("reused", r.stdout)
        self.assertEqual((spec / "retro.md").read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
