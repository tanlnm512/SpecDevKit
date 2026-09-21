"""Tests for scripts/migrate.py — run via tests/run.sh (needs Python >= 3.10).

The migration contract (TC-002): given a version 1 active docset, the
preview lists exactly the lines apply inserts, no evidence is invented
(inserted lines are the template's own pending placeholders, and existing
evidence values survive byte-identical), and the second apply changes
nothing (the tree hash is stable). Refusals — done status, archived
location, missing files — exit nonzero and leave the tree byte-identical.

The migration target is the skill's own task template (the contract-v2
header shape), read live in these tests — the expected field-name sets
below pin that shape.
"""

import contextlib
import difflib
import hashlib
import importlib.util
import io
import shutil
import tempfile
import unittest

from pathlib import Path
SKILL = Path(__file__).resolve().parents[1]
FIXTURES = SKILL / "tests" / "fixtures"
TEMPLATE = SKILL / "templates" / "task.md"

_mspec = importlib.util.spec_from_file_location("migrate", SKILL / "scripts" / "migrate.py")
migrate = importlib.util.module_from_spec(_mspec)
_mspec.loader.exec_module(migrate)

_sspec = importlib.util.spec_from_file_location("specstate", SKILL / "scripts" / "specstate.py")
specstate = importlib.util.module_from_spec(_sspec)
_sspec.loader.exec_module(specstate)


def run_migrate(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = migrate.main(list(argv))
    return rc, buf.getvalue()


def preview_lines(out: str) -> list[str]:
    return [line[4:] for line in out.splitlines() if line.startswith("  + ")]


def template_field_lines() -> dict[str, str]:
    _, fields = migrate.header_fields(TEMPLATE.read_text(encoding="utf-8"))
    return dict(fields)


def field_names(lines: list[str]) -> list[str]:
    return [migrate.FIELD_LINE.match(l).group(1) for l in lines]


def tree_digest(root: Path) -> str:
    """sha256 over every file under root — the byte-identical guarantee
    covers the whole spec dir, stray temp files included."""
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def assert_no_evidence_invented(testcase, lines):
    for line in lines:
        testcase.assertFalse(specstate.BEFORE_AUDIT_PASSED.search(line), line)
        testcase.assertFalse(specstate.CLOSING_AUDIT_APPROVED.search(line), line)
        testcase.assertFalse(specstate.DELIVERED_COMMIT.search(line), line)


class MigrateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.spec = self.tmp / "legacy-v1"
        shutil.copytree(FIXTURES / "legacy-v1", self.spec)
        self.tpl = str(TEMPLATE)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _task(self) -> str:
        return (self.spec / "task.md").read_text(encoding="utf-8")

    def test_template_declares_contract_v2_header_shape(self):
        # the migration target must be the contract's shape: the lifecycle
        # declaration plus the three header evidence records
        names = set(template_field_lines())
        self.assertEqual(
            names, {"Spec", "Lifecycle", "Before-audit", "Closing-audit", "Delivered"})
        self.assertEqual(template_field_lines()["Lifecycle"], "**Lifecycle**: v2")

    def test_dry_run_previews_exactly_and_writes_nothing(self):
        before = tree_digest(self.spec)
        rc, out = run_migrate(str(self.spec), "--template", self.tpl, "--dry-run")
        self.assertEqual(rc, 0, out)
        inserted = preview_lines(out)
        self.assertEqual(field_names(inserted), ["Lifecycle", "Closing-audit", "Delivered"])
        by_name = template_field_lines()
        for line in inserted:
            self.assertEqual(line, by_name[migrate.FIELD_LINE.match(line).group(1)])
        self.assertIn("nothing written", out)
        self.assertEqual(tree_digest(self.spec), before)

    def test_preview_matches_apply_diff(self):
        rc, preview = run_migrate(str(self.spec), "--template", self.tpl, "--dry-run")
        self.assertEqual(rc, 0, preview)
        before = self._task()
        rc, out = run_migrate(str(self.spec), "--template", self.tpl)
        self.assertEqual(rc, 0, out)
        added = [l[1:] for l in difflib.unified_diff(
            before.splitlines(), self._task().splitlines(), lineterm="")
            if l.startswith("+") and not l.startswith("+++")]
        self.assertEqual(preview_lines(preview), added)

    def test_apply_inserts_template_lines_without_inventing_evidence(self):
        rc, out = run_migrate(str(self.spec), "--template", self.tpl)
        self.assertEqual(rc, 0, out)
        inserted = preview_lines(out)
        by_name = template_field_lines()
        for line in inserted:
            self.assertIn(line, set(by_name.values()))
        assert_no_evidence_invented(self, inserted)
        after = self._task()
        # the fixture's own v1 evidence survives byte-identical, unclaimed
        self.assertIn("**Before-audit**: passed @ abc1234", after)
        self.assertEqual(len(specstate.BEFORE_AUDIT_PASSED.findall(after)), 1)
        # insertions land in the preamble, ahead of the first section
        self.assertLess(after.index("**Lifecycle**: v2"), after.index("## Burndown"))

    def test_second_apply_is_a_noop(self):
        rc, first = run_migrate(str(self.spec), "--template", self.tpl)
        self.assertEqual(rc, 0, first)
        stable = tree_digest(self.spec)
        rc, second = run_migrate(str(self.spec), "--template", self.tpl)
        self.assertEqual(rc, 0, second)
        self.assertIn("already migrated", second)
        self.assertEqual(tree_digest(self.spec), stable)
        self.assertEqual(self._task().count("**Lifecycle**: v2"), 1)

    def test_pre003_docset_gets_every_missing_field(self):
        spec = self.tmp / "legacy-pre003"
        shutil.copytree(FIXTURES / "legacy-pre003", spec)
        rc, out = run_migrate(str(spec), "--template", self.tpl)
        self.assertEqual(rc, 0, out)
        self.assertEqual(field_names(preview_lines(out)),
                         ["Lifecycle", "Before-audit", "Closing-audit", "Delivered"])
        assert_no_evidence_invented(self, preview_lines(out))
        rc, out = run_migrate(str(spec), "--template", self.tpl)
        self.assertEqual(rc, 0, out)
        self.assertIn("already migrated", out)

    def test_default_template_roundtrip_is_idempotent(self):
        rc, first = run_migrate(str(self.spec))
        self.assertEqual(rc, 0, first)
        self.assertIn("**Lifecycle**: v2", self._task())
        stable = tree_digest(self.spec)
        rc, second = run_migrate(str(self.spec))
        self.assertEqual(rc, 0, second)
        self.assertIn("already migrated", second)
        self.assertEqual(tree_digest(self.spec), stable)

    def test_done_status_refused_and_tree_untouched(self):
        spec_md = self.spec / "spec.md"
        spec_md.write_text(
            spec_md.read_text(encoding="utf-8").replace(
                "**Status**: active", "**Status**: done", 1),
            encoding="utf-8")
        baseline = tree_digest(self.spec)
        rc, err_cap = run_migrate(str(self.spec), "--template", self.tpl, "--dry-run")
        self.assertEqual(rc, 1)
        self.assertIn("Status is done", err_cap)
        rc, _ = run_migrate(str(self.spec), "--template", self.tpl)
        self.assertEqual(rc, 1)
        self.assertEqual(tree_digest(self.spec), baseline)
        spec_md.write_text(
            spec_md.read_text(encoding="utf-8").replace(
                "**Status**: done", "**Status**: implemented", 1),
            encoding="utf-8")
        rc, err_cap = run_migrate(str(self.spec), "--template", self.tpl)
        self.assertEqual(rc, 1)
        self.assertIn("only draft or active", err_cap)
        spec_md.write_text(
            spec_md.read_text(encoding="utf-8").replace(
                "**Status**: implemented", "no status line", 1),
            encoding="utf-8")
        baseline = tree_digest(self.spec)
        rc, err_cap = run_migrate(str(self.spec), "--template", self.tpl)
        self.assertEqual(rc, 1)
        self.assertIn("no recognizable **Status**", err_cap)
        self.assertEqual(tree_digest(self.spec), baseline)

    def test_archive_location_refused(self):
        archived = self.tmp / "specs" / "archive" / "legacy-v1"
        archived.parent.mkdir(parents=True)
        shutil.copytree(self.spec, archived)
        baseline = tree_digest(archived)
        rc, err_cap = run_migrate(str(archived), "--template", self.tpl, "--dry-run")
        self.assertEqual(rc, 1)
        self.assertIn("specs/archive", err_cap)
        self.assertEqual(tree_digest(archived), baseline)

    def test_missing_files_refused(self):
        (self.spec / "task.md").unlink()
        baseline = tree_digest(self.spec)
        rc, err_cap = run_migrate(str(self.spec), "--template", self.tpl)
        self.assertEqual(rc, 1)
        self.assertIn("no task.md", err_cap)
        rc, err_cap = run_migrate(str(self.tmp / "nowhere"), "--template", self.tpl)
        self.assertEqual(rc, 1)
        self.assertIn("not a directory", err_cap)
        self.assertEqual(tree_digest(self.spec), baseline)

    def test_missing_template_refused(self):
        rc, err_cap = run_migrate(str(self.spec), "--template",
                                  str(self.tmp / "no-such-template.md"))
        self.assertEqual(rc, 1)
        self.assertIn("template not found", err_cap)

    def test_usage_errors(self):
        rc, _ = run_migrate()
        self.assertEqual(rc, 2)
        rc, _ = run_migrate(str(self.spec), "extra")
        self.assertEqual(rc, 2)
        rc, _ = run_migrate(str(self.spec), "--template")
        self.assertEqual(rc, 2)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = migrate.main(["-h"])
        self.assertEqual(rc, 0)
        self.assertIn("idempotent", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
