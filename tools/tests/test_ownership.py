"""Tests for tools/ownership.py — the read-only ownership planner the
installers consume. The decision matrix is exercised purely (classify),
then tree and single-file planning and the CLI against temp roots; no
test writes outside its TemporaryDirectory.
"""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "ownership", REPO_ROOT / "tools" / "ownership.py")
ownership = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ownership)

A = "a" * 64
B = "b" * 64


def deploy(src: Path, dest: Path) -> None:
    """Simulate a complete prior deploy: copy the tree and write the
    ledger from the deployed bytes themselves."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.mkdir(parents=True)
    for name in ownership.inventory(src):
        to = dest / name
        to.parent.mkdir(parents=True, exist_ok=True)
        to.write_bytes((src / name).read_bytes())
    lines = sorted(f"{ownership.sha256_file(dest / n)} {n}"
                   for n in ownership.inventory(dest))
    (dest / ownership.LEDGER_NAME).write_text("\n".join(lines) + "\n")


def make_src(tmp: Path) -> Path:
    src = tmp / "src"
    (src / "scripts").mkdir(parents=True)
    (src / "SKILL.md").write_text("skill\n")
    (src / "scripts" / "tick.py").write_text("print(1)\n")
    return src


def kinds(decisions):
    return sorted(d.kind for d in decisions)


def by_name(decisions):
    return {d.name: d.kind for d in decisions}


class ClassifyTests(unittest.TestCase):
    def check(self, src_sha, dest_sha, ledger, want):
        got = ownership.classify("x.md", src_sha, dest_sha, ledger)
        self.assertEqual(got.kind, want)
        self.assertEqual(got.name, "x.md")

    def test_absent_destination_is_create(self):
        self.check(A, None, {}, ownership.CREATE)
        self.check(A, None, {"x.md": A}, ownership.CREATE)

    def test_identical_ledgered_is_unchanged(self):
        self.check(A, A, {"x.md": A}, ownership.UNCHANGED)

    def test_differing_ledgered_is_update(self):
        self.check(B, A, {"x.md": A}, ownership.UPDATE)

    def test_path_match_hash_mismatch_is_refuse(self):
        # ownership needs the path AND the current bytes to match the
        # ledger line — anything else proves nothing
        self.check(B, A, {"x.md": B}, ownership.REFUSE)  # differs, ledger stale
        self.check(A, A, {"x.md": B}, ownership.REFUSE)  # identical, ledger stale

    def test_unledgered_destination_is_refuse_even_when_identical(self):
        # never silently adopt a look-alike
        self.check(A, A, {}, ownership.REFUSE)
        self.check(B, A, {}, ownership.REFUSE)

    def test_unshipped_ledgered_is_delete(self):
        self.check(None, A, {"x.md": A}, ownership.DELETE)

    def test_unshipped_unledgered_is_refuse(self):
        self.check(None, A, {}, ownership.REFUSE)


class LedgerTests(unittest.TestCase):
    def test_missing_ledger_reads_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                ownership.read_ledger(Path(tmp) / "none"), {})

    def test_names_may_contain_spaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "L"
            p.write_text(f"{A} a/b c.md\n{B} top.md\n\n")
            self.assertEqual(
                ownership.read_ledger(p), {"a/b c.md": A, "top.md": B})

    def test_malformed_line_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "L"
            p.write_text("not-a-ledger-line\n")
            with self.assertRaises(ValueError):
                ownership.read_ledger(p)

    def test_short_sha_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "L"
            p.write_text("abc x.md\n")
            with self.assertRaises(ValueError):
                ownership.read_ledger(p)

    def test_duplicate_name_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "L"
            p.write_text(f"{A} x.md\n{B} x.md\n")
            with self.assertRaises(ValueError):
                ownership.read_ledger(p)


class InventoryTests(unittest.TestCase):
    def test_ledger_cache_and_pycache_are_invisible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "m.py").write_text("")
            (root / "sub").mkdir()
            for f in ("keep.md", ".DS_Store",
                      ownership.LEDGER_NAME,
                      ownership.LEDGER_NAME + ".tmp"):
                (root / f).write_text("")
            (root / "sub" / "nested.md").write_text("")
            self.assertEqual(
                ownership.inventory(root), ["keep.md", "sub/nested.md"])

    def test_symlinks_are_skipped_not_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "real.md").write_text("")
            (root / "link.md").symlink_to("real.md")
            (root / "dir").mkdir()
            (root / "dirlink").symlink_to("dir")
            self.assertEqual(ownership.inventory(root), ["real.md"])

    def test_missing_root_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                ownership.inventory(Path(tmp) / "absent"), [])


class PlanTreeTests(unittest.TestCase):
    def test_fresh_destination_is_all_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = make_src(tmp)
            got = ownership.plan_tree(src, tmp / "dest")
            self.assertEqual(kinds(got), [ownership.CREATE] * 2)
            self.assertEqual(
                by_name(got), {"SKILL.md": ownership.CREATE,
                               "scripts/tick.py": ownership.CREATE})

    def test_deployed_tree_is_all_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = make_src(tmp)
            dest = tmp / "root" / "sk"
            deploy(src, dest)
            self.assertEqual(
                kinds(ownership.plan_tree(src, dest)),
                [ownership.UNCHANGED] * 2)

    def test_master_change_is_update_for_that_file_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = make_src(tmp)
            dest = tmp / "root" / "sk"
            deploy(src, dest)
            (src / "SKILL.md").write_text("skill v2\n")
            self.assertEqual(by_name(ownership.plan_tree(src, dest)), {
                "SKILL.md": ownership.UPDATE,
                "scripts/tick.py": ownership.UNCHANGED})

    def test_foreign_extra_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = make_src(tmp)
            dest = tmp / "root" / "sk"
            deploy(src, dest)
            (dest / "zzz-foreign.md").write_text("# not ours\n")
            self.assertEqual(by_name(ownership.plan_tree(src, dest)), {
                "SKILL.md": ownership.UNCHANGED,
                "scripts/tick.py": ownership.UNCHANGED,
                "zzz-foreign.md": ownership.REFUSE})

    def test_hand_edit_after_deploy_is_refuse_not_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = make_src(tmp)
            dest = tmp / "root" / "sk"
            deploy(src, dest)
            (dest / "SKILL.md").write_text("hand-edited\n")
            self.assertEqual(by_name(ownership.plan_tree(src, dest)), {
                "SKILL.md": ownership.REFUSE,
                "scripts/tick.py": ownership.UNCHANGED})

    def test_identical_tree_without_ledger_is_refused_not_adopted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = make_src(tmp)
            dest = tmp / "root" / "sk"
            deploy(src, dest)
            (dest / ownership.LEDGER_NAME).unlink()
            self.assertEqual(
                kinds(ownership.plan_tree(src, dest)),
                [ownership.REFUSE] * 2)

    def test_unshipped_ledgered_file_is_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = make_src(tmp)
            dest = tmp / "root" / "sk"
            deploy(src, dest)
            (src / "scripts" / "tick.py").unlink()
            self.assertEqual(by_name(ownership.plan_tree(src, dest)), {
                "SKILL.md": ownership.UNCHANGED,
                "scripts/tick.py": ownership.DELETE})

    def test_unshipped_file_without_its_ledger_line_is_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = make_src(tmp)
            dest = tmp / "root" / "sk"
            deploy(src, dest)
            (src / "scripts" / "tick.py").unlink()
            ledger = dest / ownership.LEDGER_NAME
            kept = [l for l in ledger.read_text().splitlines()
                    if not l.endswith(" scripts/tick.py")]
            ledger.write_text("\n".join(kept) + "\n")
            self.assertEqual(by_name(ownership.plan_tree(src, dest)), {
                "SKILL.md": ownership.UNCHANGED,
                "scripts/tick.py": ownership.REFUSE})

    def test_directory_squatting_a_planned_path_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = make_src(tmp)
            dest = tmp / "root" / "sk"
            deploy(src, dest)
            (dest / "SKILL.md").unlink()
            (dest / "SKILL.md").mkdir()
            got = by_name(ownership.plan_tree(src, dest))
            self.assertEqual(got["SKILL.md"], ownership.REFUSE)

    def test_corrupt_ledger_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = make_src(tmp)
            dest = tmp / "root" / "sk"
            deploy(src, dest)
            with open(dest / ownership.LEDGER_NAME, "a") as fh:
                fh.write("garbage\n")
            with self.assertRaises(ValueError):
                ownership.plan_tree(src, dest)

    def test_missing_source_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                ownership.plan_tree(Path(tmp) / "absent", Path(tmp) / "dest")

    def test_ledger_location_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = make_src(tmp)
            dest = tmp / "root" / "sk"
            deploy(src, dest)
            lines = sorted(f"{ownership.sha256_file(dest / n)} {n}"
                           for n in ownership.inventory(dest))
            (tmp / "elsewhere-ledger").write_text("\n".join(lines) + "\n")
            self.assertEqual(
                kinds(ownership.plan_tree(
                    src, dest, tmp / "elsewhere-ledger")),
                [ownership.UNCHANGED] * 2)


class PlanFileTests(unittest.TestCase):
    def test_command_root_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / "spec.md"
            src.write_text("v1\n")
            root = tmp / "commands"
            root.mkdir()
            dest = root / "spec.md"
            ledger = root / ownership.LEDGER_NAME

            d = ownership.plan_file(src, dest, name="spec")
            self.assertEqual(d.kind, ownership.CREATE)

            dest.write_text("v1\n")
            ledger.write_text(f"{ownership.sha256_file(dest)} spec\n")
            self.assertEqual(
                ownership.plan_file(src, dest, name="spec").kind,
                ownership.UNCHANGED)

            src.write_text("v2\n")
            self.assertEqual(
                ownership.plan_file(src, dest, name="spec").kind,
                ownership.UPDATE)

            dest.write_text("hand-edited\n")
            self.assertEqual(
                ownership.plan_file(src, dest, name="spec").kind,
                ownership.REFUSE)

    def test_default_name_is_destination_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / "spec.md"
            src.write_text("v1\n")
            root = tmp / "commands"
            root.mkdir()
            (root / "spec.md").write_text("v1\n")
            (root / ownership.LEDGER_NAME).write_text(
                f"{ownership.sha256_file(root / 'spec.md')} spec.md\n")
            self.assertEqual(
                ownership.plan_file(src, root / "spec.md").kind,
                ownership.UNCHANGED)

    def test_missing_source_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            with self.assertRaises(ValueError):
                ownership.plan_file(tmp / "absent.md", tmp / "dest.md")


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "ownership.py"), *args],
            capture_output=True, text=True, timeout=60)

    def test_plan_tree_prints_one_decision_per_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = make_src(tmp)
            r = self.run_cli("plan-tree", "--src", str(src),
                             "--dest", str(tmp / "dest"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(
                r.stdout, "create SKILL.md\ncreate scripts/tick.py\n")

    def test_refusal_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = make_src(tmp)
            dest = tmp / "dest"
            (dest / "sub").mkdir(parents=True)
            (dest / "sub" / "foreign.md").write_text("# not ours\n")
            r = self.run_cli("plan-tree", "--src", str(src),
                             "--dest", str(dest))
            self.assertEqual(r.returncode, 1)
            self.assertIn("refuse sub/foreign.md", r.stdout)

    def test_validation_error_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.run_cli("plan-tree", "--src",
                             str(Path(tmp) / "absent"),
                             "--dest", str(Path(tmp) / "dest"))
            self.assertEqual(r.returncode, 2)
            self.assertIn("ERROR", r.stderr)

    def test_plan_file_with_ledger_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / "spec.md"
            src.write_text("v1\n")
            root = tmp / "commands"
            root.mkdir()
            r = self.run_cli("plan-file", "--src", str(src),
                             "--dest", str(root / "spec.md"),
                             "--name", "spec")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout, "create spec\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
