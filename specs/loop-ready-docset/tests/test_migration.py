"""TC-017/TC-018/TC-019 — the grammar migration (FR-011, NFR-004): a
docset written in the pre-change grammar warns exactly once — the marker
lands beside its docs — and the same elements fail by name from the next
cycle; done and archived docsets are exempt from the ramp entirely;
migrate.py upgrade converts the grammar in place idempotently and never
re-opens a recorded freeze.

Run: python3 specs/loop-ready-docset/tests/test_migration.py
MigrationTests.<method>
"""

import contextlib
import datetime
import importlib.util
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
_SCRIPTS = str(REPO / "skills" / "spec-design" / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import check  # noqa: E402 - repo-relative scripts dir prepended above
import freeze  # noqa: E402 - parity-identical to spec-build's copy

_migrate_spec = importlib.util.spec_from_file_location(
    "migrate", REPO / "skills" / "spec-build" / "scripts" / "migrate.py")
migrate = importlib.util.module_from_spec(_migrate_spec)
_migrate_spec.loader.exec_module(migrate)

FIXTURE = REPO / "skills" / "spec-design" / "examples" / "mini-spec"
MARKER = ".grammar-v1-warned"
HINT = "run `migrate.py <spec-dir> upgrade`"
SKIP_LINE = "not applicable — no open questions at Stage 0"
ELEMENTS = (
    "research.md present",
    "the unfolded approval record",
    "notes/delivery.md present",
    "a two-column burndown header",
    "full-tier tech-spec.md without the `## Questions & options` section",
)


def scratch_docset(tmp: Path, name: str = "legacy") -> Path:
    """The mini-spec docset plus the repo it cites, degraded to the
    pre-change grammar: an open research.md instead of the folded
    section, the review sidecar without a freeze, a delivery note with
    no delivery block, and a burndown header without the Verified
    column."""
    (tmp / "specs").mkdir(parents=True, exist_ok=True)
    spec = tmp / "specs" / name
    shutil.copytree(FIXTURE / "specs" / "mini-spec", spec)
    shutil.copytree(FIXTURE / "repo", tmp / "repo", dirs_exist_ok=True)

    def rewrite(path: Path, old: str, new: str) -> None:
        text = path.read_text(encoding="utf-8")
        assert old in text, old
        path.write_text(text.replace(old, new), encoding="utf-8")

    rewrite(spec / "task.md",
            "| Phase | Total | Done | Verified |\n"
            "|-------|-------|------|----------|",
            "| Phase | Total | Done |\n|---|---|---|")
    rewrite(spec / "research.md", SKIP_LINE,
            "- Q1 — where does the multiply sign live?")
    (spec / "approvals").mkdir()
    (spec / "approvals" / "review.md").write_text(
        "# Contract review\n\nDocset fingerprint: 0badf00d\n\n"
        "digest: BLOCK 0 · WARN 0 · NIT 0 · worst none\n", encoding="utf-8")
    (spec / "notes").mkdir()
    (spec / "notes" / "delivery.md").write_text(
        "# Delivery\n\nDocs impact: none recorded yet\n", encoding="utf-8")
    return spec


def run_check(spec: Path) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = check.main([str(spec)])
    return code, buf.getvalue()


def run_upgrade(spec: Path, *args: str) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = migrate.main([str(spec), "upgrade", *args])
    return code, buf.getvalue()


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


def frozen_legacy_docset(tmp: Path, name: str = "legacy") -> Path:
    """scratch_docset plus a recorded old-grammar freeze: the `## Frozen
    contract` manifest over the docset's current frozen files (Approved-at
    dash — the scratch repo has no git) beside the review sidecar."""
    spec = scratch_docset(tmp, name)
    entries = "\n".join(
        f"- `{f}`: {kind} sha256:{digest} length:{length}"
        for f, (kind, digest, length) in freeze.manifest_values(spec).items())
    (spec / "approvals" / "approval.md").write_text(
        "# Approval freeze\n\n"
        "**Approved-at**: `-`\n"
        "**Algorithm**: sha256 over UTF-8 bytes\n\n"
        "## Frozen contract\n"
        f"{entries}\n", encoding="utf-8")
    return spec


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="t018-migrate-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def test_warn_once_then_fail_next_cycle(self):
        # TC-017: cycle 1 warns exactly once, naming the upgrade command
        # and every detected element, and writes the marker beside the
        # docs; cycle 2 fails the same elements by name, each with the
        # migrate hint
        spec = scratch_docset(self._tmp)
        code, out = run_check(spec)
        self.assertEqual(code, 0, out)
        self.assertIn("migration: pre-change grammar", out)
        self.assertIn(HINT, out)
        for element in ELEMENTS:
            self.assertIn(element, out)
        self.assertNotIn("FAIL  migration:", out)
        marker = spec / MARKER
        body = marker.read_text(encoding="utf-8")
        self.assertIn(datetime.date.today().isoformat(), body)
        for element in ELEMENTS:
            self.assertIn(element, body)

        code, out = run_check(spec)
        self.assertEqual(code, 1, out)
        self.assertEqual(out.count("FAIL  migration:"), len(ELEMENTS), out)
        for element in ELEMENTS:
            self.assertIn(f"FAIL  migration: {element}", out)
        self.assertIn(HINT, out)

    def test_done_and_archived_docsets_are_exempt(self):
        # a done plan is a record and archived history is never migrated:
        # neither warns, fails, nor grows a marker, whatever it carries
        done = scratch_docset(self._tmp, "settled")
        done_text = done / "spec.md"
        done_text.write_text(done_text.read_text(encoding="utf-8").replace(
            "**Status**: draft", "**Status**: done"), encoding="utf-8")
        for _ in range(2):
            _, out = run_check(done)
            self.assertNotIn("FAIL  migration:", out)
            self.assertNotIn("WARN  migration:", out)
            self.assertFalse((done / MARKER).exists())

        archived = scratch_docset(self._tmp, "archived")
        (archived.parent / "archive").mkdir()
        archived.rename(archived.parent / "archive" / "2026-01-02-archived")
        for _ in range(2):
            _, out = run_check(archived)
            self.assertNotIn("FAIL  migration:", out)
            self.assertNotIn("WARN  migration:", out)
            self.assertFalse((archived / MARKER).exists())

    def test_upgrade_idempotent(self):
        # TC-018: dry-run plans the folds and writes nothing; the first
        # apply converts the grammar in place and check.py reads it
        # green; a second apply changes nothing
        spec = frozen_legacy_docset(self._tmp)
        (spec / MARKER).write_text("stale ramp state\n", encoding="utf-8")
        before = snapshot(spec)
        code, out = run_upgrade(spec)
        self.assertEqual(code, 0, out)
        for step in ("burndown", "research", "approval", "delivery", MARKER):
            self.assertIn(step, out)
        self.assertEqual(snapshot(spec), before)

        code, out = run_upgrade(spec, "--apply")
        self.assertEqual(code, 0, out)
        self.assertFalse((spec / "research.md").exists(), out)
        self.assertFalse((spec / "approvals" / "review.md").exists(), out)
        self.assertFalse((spec / MARKER).exists(), out)
        tech = (spec / "tech-spec.md").read_text(encoding="utf-8")
        self.assertIn("## Questions & options", tech)
        self.assertIn("Q1 — where does the multiply sign live?", tech)
        approval = (spec / "approvals" / "approval.md").read_text(
            encoding="utf-8")
        self.assertIn("## Contract review", approval)
        self.assertIn("## Freeze", approval)
        self.assertNotIn("Frozen contract", approval)
        task = (spec / "task.md").read_text(encoding="utf-8")
        self.assertIn("| Phase | Total | Done | Verified |", task)
        self.assertIn("- Docs impact: none recorded yet", task)

        code, out = run_check(spec)
        self.assertEqual(code, 0, out)

        converted = snapshot(spec)
        code, out = run_upgrade(spec, "--apply")
        self.assertEqual(code, 0, out)
        self.assertIn("already upgraded", out)
        self.assertEqual(snapshot(spec), converted)

    def test_upgrade_preserves_recorded_freeze(self):
        # TC-019: the upgrade converts the grammar around a recorded
        # freeze — tech-spec.md changes are appends beyond the recorded
        # prefix, the manifest's entry lines and Approved-at transplant
        # byte-identically, and the freeze still verifies afterwards
        spec = frozen_legacy_docset(self._tmp, "frozen")
        approval_before = (spec / "approvals" / "approval.md").read_text(
            encoding="utf-8")
        entries_before = freeze.ENTRY.findall(approval_before)
        tech_before = (spec / "tech-spec.md").read_bytes()

        code, out = run_upgrade(spec, "--apply")
        self.assertEqual(code, 0, out)

        approval_after = (spec / "approvals" / "approval.md").read_text(
            encoding="utf-8")
        self.assertEqual(freeze.ENTRY.findall(approval_after), entries_before)
        self.assertIn("**Approved-at**: `-`", approval_after)
        tech_after = (spec / "tech-spec.md").read_bytes()
        self.assertNotEqual(tech_after, tech_before)
        self.assertTrue(tech_after.startswith(tech_before))
        self.assertEqual(freeze.verify(spec, spec.parent.parent), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
