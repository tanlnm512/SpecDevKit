"""Tests for scripts/archive.sh — run via `python3 skills/spec-to-prod/tests/test_archive.py`.

Covers TC-003: pre-move gates (strict kebab-case, symlink refusal, canonical
containment) must refuse without mutating anything. Covers TC-004: a
finalization failure after the move (INDEX repoint or final validation) must
restore the source byte-identically, report exact recovery paths, and exit
nonzero. The journal survives only when rollback itself fails.
"""

import os
import shutil
import subprocess
import tempfile
import unittest

from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
ARCHIVE = SKILL / "scripts" / "archive.sh"

SPEC_MD = """# Spec: rollback-spec

**Status**: done
"""

INDEX_MD = "- [Spec: rollback-spec](rollback-spec/spec.md)\n"


# Shared fixtures and helpers for the archive contract tests.
class ArchiveContractBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.specs = self.tmp / "specs"
        self.spec = self.specs / "rollback-spec"
        self.spec.mkdir(parents=True)
        self.spec_md = self.spec / "spec.md"
        self.spec_md.write_text(SPEC_MD, encoding="utf-8")
        (self.specs / "INDEX.md").write_text(INDEX_MD, encoding="utf-8")
        self.before = self.spec_md.read_bytes()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _shim_dir(self, name, body):
        d = self.tmp / "_shims"
        d.mkdir(exist_ok=True)
        tool = d / name
        tool.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        tool.chmod(0o755)
        return d

    def _run(self, prepend=None, extra_env=None, name="rollback-spec"):
        env = dict(os.environ)
        if prepend:
            env["PATH"] = str(prepend) + os.pathsep + env["PATH"]
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            ["bash", str(ARCHIVE), name, str(self.tmp)],
            capture_output=True, text=True, env=env)

    def _dest_entries(self):
        return sorted((self.specs / "archive").glob("*-rollback-spec"))

    def _journal_entries(self):
        return sorted((self.specs / "archive").glob("*.journal"))


class ArchiveFinalizationTests(ArchiveContractBase):
    def test_success_moves_repoints_and_clears_journal(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(self.spec_md.exists())
        dests = self._dest_entries()
        self.assertEqual(len(dests), 1)
        self.assertEqual((dests[0] / "spec.md").read_bytes(), self.before)
        index = (self.specs / "INDEX.md").read_text(encoding="utf-8")
        self.assertNotIn("(rollback-spec/spec.md)", index)
        self.assertRegex(index, r"\(archive/\d{4}-\d{2}-\d{2}-rollback-spec/spec\.md\)")
        self.assertEqual(self._journal_entries(), [])

    def test_without_index_moves_and_clears_journal(self):
        (self.specs / "INDEX.md").unlink()
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self._dest_entries()), 1)
        self.assertEqual(self._journal_entries(), [])

    def test_move_failure_preserves_source_and_cleans_journal(self):
        shim = self._shim_dir("mv", "exit 9\n")
        proc = self._run(prepend=shim)
        self.assertNotEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.spec_md.read_bytes(), self.before)
        self.assertEqual(self._dest_entries(), [])
        self.assertEqual(self._journal_entries(), [])

    def test_index_failure_restores_source_byte_identical(self):
        shim = self._shim_dir("python3", 'echo "shim: repoint failed" >&2\nexit 1\n')
        proc = self._run(prepend=shim)
        self.assertNotEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.spec_md.read_bytes(), self.before)
        self.assertIn(str(self.spec), proc.stderr)
        self.assertIn("restored", proc.stderr)
        self.assertEqual(self._dest_entries(), [])
        self.assertEqual(self._journal_entries(), [])

    def test_final_validation_failure_restores_source_byte_identical(self):
        # Fails only the post-move check, which is the sole grep run against
        # a path under specs/archive/.
        shim = self._shim_dir(
            "grep", 'case "$*" in *archive/*) exit 1 ;; esac\nexec /usr/bin/grep "$@"\n')
        proc = self._run(prepend=shim)
        self.assertNotEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("final validation", proc.stderr)
        self.assertEqual(self.spec_md.read_bytes(), self.before)
        self.assertEqual(self._dest_entries(), [])
        self.assertEqual(self._journal_entries(), [])

    def test_rollback_failure_keeps_journal_with_recovery_paths(self):
        shim = self._shim_dir("python3", "exit 1\n")
        (shim / "mv").write_text(
            "#!/bin/sh\n"
            'c="$(cat "$MV_COUNT" 2>/dev/null || echo 0)"\n'
            "c=$((c+1))\n"
            'echo "$c" > "$MV_COUNT"\n'
            '[ "$c" -eq 2 ] && exit 9\n'
            'exec /bin/mv "$@"\n',
            encoding="utf-8")
        (shim / "mv").chmod(0o755)
        proc = self._run(prepend=shim, extra_env={"MV_COUNT": str(shim / "count")})
        self.assertNotEqual(proc.returncode, 0, proc.stderr)
        dests = self._dest_entries()
        self.assertEqual(len(dests), 1)
        self.assertFalse(self.spec_md.exists())
        journals = self._journal_entries()
        self.assertEqual(len(journals), 1)
        self.assertEqual(journals[0].read_text(encoding="utf-8").splitlines(),
                         [str(dests[0]), str(self.spec)])
        self.assertIn(str(dests[0]), proc.stderr)
        self.assertIn(str(self.spec), proc.stderr)
        self.assertIn("recovery", proc.stderr)


class ArchiveGateTests(ArchiveContractBase):
    # TC-003: pre-move gates refuse an invalid identity before any mutation.
    BAD_NAMES = ("Rollback-Spec", "rollback_spec", "rollback--spec",
                 "-rollback", "rollback.spec", "rollback-spec/../other")

    def test_rejects_non_kebab_case_names_without_mutation(self):
        for bad in self.BAD_NAMES:
            with self.subTest(name=bad):
                proc = self._run(name=bad)
                self.assertNotEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("kebab-case", proc.stderr)
                self.assertEqual(self.spec_md.read_bytes(), self.before)
                self.assertEqual(self._dest_entries(), [])
                self.assertEqual(self._journal_entries(), [])

    def test_rejects_symlinked_spec_without_mutation(self):
        # Both an external target and a sibling alias of the real spec dir
        # are refused; the targets themselves stay untouched.
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "spec.md").write_text(SPEC_MD, encoding="utf-8")
        for link_name, target in (("linked-spec", outside),
                                  ("alias-spec", self.spec)):
            os.symlink(target, self.specs / link_name)
        for link_name in ("linked-spec", "alias-spec"):
            with self.subTest(name=link_name):
                proc = self._run(name=link_name)
                self.assertNotEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("symlink", proc.stderr)
                self.assertEqual(self._dest_entries(), [])
                self.assertEqual(self._journal_entries(), [])
        self.assertEqual((outside / "spec.md").read_bytes(), self.before)
        self.assertEqual(self.spec_md.read_bytes(), self.before)


if __name__ == "__main__":
    unittest.main()
