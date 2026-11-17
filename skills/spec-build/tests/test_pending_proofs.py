"""Proofs that name tests nobody wrote are PENDING, never a pass (spec-build
D-042), plus the delivery-pass friction fixes that rode with it: scope reads
globs the docs spell, Docs impact tolerates a trailing parenthetical, `block`
drafts the delivery block, `preflight` names missing prerequisites.

A runner told to select a test that does not exist exits 0 when the command
tolerates an empty selection or runs quiet, so a proof of a not-yet-written
test used to read PASS. The tests below pin the detector on the selector
dialects (Maven `-Dtest=`, Gradle `--tests`, pytest node ids), the land
refusal and its explicit `--allow-pending` escape, and the proofs/dod exit.
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

_spec = importlib.util.spec_from_file_location("audit", _SCRIPTS / "audit.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

AUDIT = _SCRIPTS / "audit.py"
GHOST = ("mvn -q test -Dtest='GhostTest#shouts' "
         "-Dsurefire.failIfNoSpecifiedTests=false")


def make_repo(tmp: Path) -> Path:
    root = tmp / "repo"
    (root / "src" / "test" / "java").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    write(root / "src" / "test" / "java" / "RealTest.java",
          "class RealTest {\n  @Test void shouts() {}\n  @Test void whispers() {}\n}\n")
    write(root / "tests" / "test_real.py",
          "class TestShout:\n    def test_loud(self):\n        pass\n")
    return root


class MissingNamedTestsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="pending-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.repo = make_repo(self._tmp)

    def missing(self, cmd: str) -> list[str]:
        audit._SOURCE_INDEX.clear()
        return audit.missing_named_tests(cmd, self.repo)

    def test_an_existing_class_and_method_is_not_missing(self):
        self.assertEqual(self.missing("mvn test -Dtest=RealTest#shouts"), [])
        self.assertEqual(self.missing("mvn test -Dtest='RealTest#shouts+whispers'"), [])
        self.assertEqual(self.missing("mvn test -Dtest=RealTest"), [])

    def test_a_missing_class_or_method_is_named(self):
        self.assertEqual(self.missing("mvn test -Dtest=GhostTest"), ["GhostTest"])
        self.assertEqual(self.missing("mvn test -Dtest=RealTest#sings"),
                         ["RealTest#sings"])
        self.assertEqual(
            self.missing("mvn test -Dtest='RealTest#shouts,GhostTest#x'"),
            ["GhostTest#x"])

    def test_wildcards_need_one_matching_source(self):
        self.assertEqual(self.missing("mvn test -Dtest='Real*Test'"), [])
        self.assertEqual(self.missing("mvn test -Dtest='Ghost*Test'"),
                         ["Ghost*Test"])
        self.assertEqual(self.missing("mvn test -Dtest='!GhostTest'"), [])

    def test_gradle_and_pytest_selectors(self):
        self.assertEqual(self.missing("gradle test --tests pkg.RealTest.shouts"), [])
        self.assertEqual(self.missing("gradle test --tests pkg.GhostTest.shouts"),
                         ["GhostTest#shouts"])
        self.assertEqual(self.missing("pytest tests/test_real.py::TestShout::test_loud"), [])
        self.assertEqual(self.missing("pytest tests/test_real.py::TestShout::test_quiet"),
                         ["tests/test_real.py::TestShout::test_quiet"])
        self.assertEqual(self.missing("pytest tests/gone.py::test_x"),
                         ["tests/gone.py::test_x"])

    def test_a_command_with_no_selector_is_not_judged(self):
        self.assertEqual(self.missing("python3 -c 'print(1)'"), [])
        self.assertEqual(self.missing("mvn -q test"), [])

    def test_build_output_directories_do_not_count_as_sources(self):
        (self.repo / "target").mkdir()
        write(self.repo / "target" / "GhostTest.java", "class GhostTest {}\n")
        self.assertEqual(self.missing("mvn test -Dtest=GhostTest"), ["GhostTest"])


def ghost_fixture(tmp: Path, name: str) -> Path:
    spec = hand_fixture(tmp, name)
    test = spec / "test.md"
    write(test, test.read_text(encoding="utf-8").replace(
        "`python3 -c 'print(\"HI\")'`", f"`{GHOST}`"))
    return spec


class PendingProofsCliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="pending-cli-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.tel = self._tmp / "tel"

    def audit_cli(self, spec: Path, *args: str):
        env = dict(os.environ, KIT_TELEMETRY_DIR=str(self.tel),
                   KIT_TELEMETRY="on")
        return subprocess.run(
            [sys.executable, str(AUDIT), args[0], str(spec), *args[1:]],
            capture_output=True, text=True, timeout=300, env=env)

    def test_a_proof_naming_a_missing_test_reads_pending_and_fails_the_run(self):
        spec = ghost_fixture(self._tmp, "ghost")
        r = self.audit_cli(spec, "proofs", "--run")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("PENDING", r.stdout)
        self.assertIn("GhostTest#shouts", r.stdout)
        self.assertNotRegex(r.stdout, r"(?m)^\s+PASS\s+TC-001")

    def test_land_refuses_when_no_proof_ran(self):
        spec = ghost_fixture(self._tmp, "refuse")
        make_wave(spec, "T001")
        run_mark(spec, "claim", "--wave", str(spec / "spawns" / "wave-4"),
                 tel=self.tel)
        r = run_mark(spec, "land", "T001",
                     "--digest", "digest: task T001 · status implemented",
                     tel=self.tel)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("none of T001's proofs ran", r.stderr)
        self.assertIn("--allow-pending", r.stderr)
        self.assertIn("(in-progress)", entry_text(spec, "T001"))

    def test_allow_pending_lands_loudly_and_dod_stays_red(self):
        spec = ghost_fixture(self._tmp, "allow")
        make_wave(spec, "T001")
        run_mark(spec, "claim", "--wave", str(spec / "spawns" / "wave-4"),
                 tel=self.tel)
        r = run_mark(spec, "land", "T001", "--allow-pending",
                     "--digest", "digest: task T001 · status implemented",
                     tel=self.tel)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("lands unproven", r.stderr)
        self.assertIn("(implemented)", entry_text(spec, "T001").splitlines()[0])
        dod = self.audit_cli(spec, "dod")
        self.assertRegex(dod.stdout, r"(?m)^\s+1 PROOF auto\s+FAIL\s")
        self.assertIn("pending", dod.stdout)


class ScopeGlobTests(unittest.TestCase):
    def test_a_glob_the_docs_spell_names_every_file_it_matches(self):
        docs = "Touches: `pipeline/src/test/java/p/HoldWindow*.java` and a * bullet"
        self.assertTrue(audit._mentioned("pipeline/src/test/java/p/HoldWindowTest.java", docs))
        self.assertTrue(audit._mentioned("pipeline/src/test/java/p/HoldWindowSupport.java", docs))
        self.assertFalse(audit._mentioned("pipeline/src/test/java/p/Other.java", docs))

    def test_a_bare_star_or_emphasis_matches_nothing(self):
        self.assertFalse(audit._mentioned("src/Anything.java", "* item **bold** text"))

    def test_exact_paths_and_bare_names_still_match(self):
        self.assertTrue(audit._mentioned("src/A.java", "edit src/A.java"))
        self.assertTrue(audit._mentioned("src/deep/A.java", "edit A.java"))


class DocsImpactParseTests(unittest.TestCase):
    def test_a_trailing_parenthetical_is_prose_not_path(self):
        self.assertEqual(
            audit.docs_impact_files(
                "`CLAUDE.md` (Contract, State machine), docs/a.md, b.json (schema)"),
            ["CLAUDE.md", "docs/a.md", "b.json"])

    def test_plain_lists_are_unchanged(self):
        self.assertEqual(audit.docs_impact_files("README.md, CHANGELOG.md"),
                         ["README.md", "CHANGELOG.md"])


class BlockAndPreflightTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="block-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def preflight(self, spec: Path):
        return subprocess.run([sys.executable, str(AUDIT), "preflight", str(spec)],
                              capture_output=True, text=True, timeout=120)

    def test_preflight_lists_pending_proofs(self):
        r = self.preflight(ghost_fixture(self._tmp, "pre"))
        self.assertIn("PENDING", r.stdout)
        self.assertIn("GhostTest#shouts", r.stdout)

    def test_preflight_is_no_go_for_a_script_that_does_not_exist(self):
        spec = hand_fixture(self._tmp, "nogo")
        test = spec / "test.md"
        write(test, test.read_text(encoding="utf-8").replace(
            "`python3 -c 'print(\"HI\")'`", "`./no-such-script.sh`"))
        r = self.preflight(spec)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("NO-GO", r.stdout)
        self.assertIn("no-such-script.sh", r.stdout)

    def test_block_prints_placeholders_without_writing(self):
        spec = hand_fixture(self._tmp, "blk")
        before = (spec / "task.md").read_text(encoding="utf-8")
        r = subprocess.run([sys.executable, str(AUDIT), "block", str(spec)],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((spec / "task.md").read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
