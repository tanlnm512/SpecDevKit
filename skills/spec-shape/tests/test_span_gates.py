"""Tests for the spec-shape intake gate — T014 of spec-to-prod-split.

FR-003/FR-008/NFR-003, TC-007..TC-009: `--span shape` (D-003) refuses a
docset whose intent.md is present, filled and red — the refusal families
are exactly check.py --intent-only's on authored artifacts: a stale
baseline (Baseline != HEAD, TC-009), a missing or hashless baseline
header, and an open NEEDS CLARIFICATION marker (TC-008). Placeholders and
empty files are the scout's unwritten territory (D-002): the node reads
READY there, so intake never refuses them. An absent intent.md reads
SKIPPED per FR-008 — pre-split dirs pass the gate untouched, and the
full-span bare report keeps the pre-split vocabulary (the marker list;
the monolith's engine retired with its tree, T023). A valid intent admits the
authoring waves; a drained shape span stops at the named approve handoff
and never emits an execute payload. Every refusal records an
intake_refusal telemetry event under the skill's own derived name in the
temp KIT_TELEMETRY_DIR store, and writes zero payload files.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
GRAPH = SCRIPTS / "graph.py"
SCAFFOLD = SCRIPTS / "scaffold.sh"
ROOT = SKILL.parent.parent
# the mini-spec fixture moved to this skill's examples/ with the split
# (T022); the monolith's copy went with its tree (T023)
MINI_SPEC = SKILL / "examples" / "mini-spec" / "specs" / "mini-spec"
MINI_SPEC_REPO = SKILL / "examples" / "mini-spec" / "repo"
MASTER_CHECK = SCRIPTS / "check.py"

SPEC_TEXT = (MINI_SPEC / "spec.md").read_text(encoding="utf-8")

GOOD_INTENT = (
    "# Intent: demo\n"
    "\n"
    "**Baseline**: intent v1 @ {sha}\n"
    "\n"
    "## Problem\n"
    "Users cannot multiply integers.\n"
    "\n"
    "## Grilled questions\n"
    "- who is the audience — answered: calculator users.\n"
)


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def scaffold_spec(tmp: Path, name: str = "demo") -> Path:
    """Full-tier scaffold with a filled spec.md and nothing else authored:
    survey/plan/tech/qa/tasks stay unfilled templates, research.md ships
    the skip marker (D-025), so the frontier is exactly the intent gate's
    to decide."""
    r = subprocess.run(["bash", str(SCAFFOLD), "--tier", "full", name,
                        str(tmp)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    d = tmp / "specs" / name
    write(d / "spec.md", SPEC_TEXT)
    return d


def copy_mini_spec(tmp: Path, name: str = "mini-spec") -> Path:
    """The committed mini-spec docset plus the repo it cites, under a tmp
    root — never the read-only original."""
    (tmp / "specs").mkdir(parents=True, exist_ok=True)
    dst = tmp / "specs" / name
    shutil.copytree(MINI_SPEC, dst)
    shutil.copytree(MINI_SPEC_REPO, tmp / "repo")
    return dst


def doc_hashes(spec_dir: Path) -> dict:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(spec_dir.glob("*.md"))}


def dir_checksum(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def git_commit(root: Path, message: str) -> str:
    (root / "note.txt").write_text(message, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=kit",
                    "-c", "user.email=kit@example.com", "commit", "-qm",
                    message], check=True, capture_output=True)
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
        check=True, capture_output=True, text=True).stdout.strip()


class TelemetryStoreTestCase(unittest.TestCase):
    """Every invocation runs against a temp telemetry store — the suite
    stays hermetic and intake_refusal rows are assertable in
    spec-shape.jsonl (FR-007's derived skill name)."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="spangate-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.store = self._tmp / "telemetry"
        self.store.mkdir()

    def run_cli(self, *args):
        env = dict(os.environ, KIT_TELEMETRY_DIR=str(self.store),
                   KIT_TELEMETRY="on")
        return subprocess.run(
            [sys.executable, str(GRAPH), *[str(a) for a in args]],
            capture_output=True, text=True, timeout=300, env=env)

    def telemetry_rows(self, event=None):
        p = self.store / f"{SKILL.name}.jsonl"
        if not p.exists():
            return []
        rows = [json.loads(ln) for ln in p.read_text().splitlines()]
        return [r for r in rows if event is None or r["event"] == event]


class ShapeIntakeRefusalTests(TelemetryStoreTestCase):
    """TC-008/TC-009: every present-and-red intent family refuses span
    entry — exit 4, the message naming the blocking gate and the intent
    node's BLOCKED reason, zero payload files, zero authoring docs
    written, one intake_refusal telemetry event per refused invocation.
    The checker families a filled artifact can fail: stale baseline,
    absent baseline header, hashless baseline header, open clarify
    marker. Placeholder residue and empty files read READY (the scout
    rewrites them — intake is a gate on validated artifacts, never on
    unwritten ones), and absence reads SKIPPED (FR-008)."""

    def refused(self, spec_dir: Path):
        """Both executor modes refuse identically; the docset is byte-
        unchanged and no spawns tree appears."""
        before = doc_hashes(spec_dir)
        for argv in (("--emit-spawns",), ("--run",)):
            r = self.run_cli(spec_dir, "--span", "shape", *argv)
            self.assertEqual(r.returncode, 4, (argv, r.stdout, r.stderr))
            self.assertIn("span entry refused", r.stdout)
            self.assertIn("blocking gate intent", r.stdout)
            self.assertIn("--intent-only", r.stdout,
                          "the BLOCKED reason names the failing check")
        self.assertFalse((spec_dir / "spawns").exists(),
                         "a refused span writes no payload")
        self.assertEqual(before, doc_hashes(spec_dir),
                         "a refused span writes no authoring doc")
        rows = self.telemetry_rows("intake_refusal")
        self.assertEqual(len(rows), 2, "one event per refused invocation")
        for row in rows:
            self.assertEqual(row["skill"], SKILL.name)
            self.assertEqual(row["payload"]["span"], "shape")
            self.assertEqual(row["payload"]["gates"], ["intent"])

    def test_stale_baseline_refuses(self):
        # TC-009: the artifact passed the checker once, but HEAD moved on
        root = self._tmp / "stale"
        root.mkdir(parents=True)
        subprocess.run(["git", "-C", str(root), "init", "-q"],
                       capture_output=True)
        d = scaffold_spec(root)
        base = git_commit(root, "first")
        write(d / "intent.md", GOOD_INTENT.format(sha=base))
        head = git_commit(root, "second")
        self.assertNotEqual(base, head)
        self.refused(d)

    def test_absent_baseline_header_refuses(self):
        # The artifact is named in the dir but the scout's baseline record
        # is absent — nothing anchors its validation to a repo snapshot
        d = scaffold_spec(self._tmp / "nobaseline")
        write(d / "intent.md",
              GOOD_INTENT.format(sha="x").replace(
                  "**Baseline**: intent v1 @ x\n\n", ""))
        self.refused(d)

    def test_hashless_baseline_header_refuses(self):
        d = scaffold_spec(self._tmp / "nohash")
        write(d / "intent.md",
              GOOD_INTENT.format(sha="x").replace(
                  "intent v1 @ x", "intent v1 latest"))
        self.refused(d)

    def test_open_clarify_marker_refuses(self):
        # The grilling vocabulary: an open marker means a question on the
        # frontier was never answered
        d = scaffold_spec(self._tmp / "marker")
        write(d / "intent.md", GOOD_INTENT.format(sha="3fa9c21")
              + "\n- [NEEDS CLARIFICATION: who funds the work?]\n")
        self.refused(d)

    def test_placeholder_residue_is_ready_never_refused(self):
        # D-002's boundary: placeholder-shaped lines mean the scout has
        # not rewritten the artifact yet — that is work to spawn, not a
        # validation to reject (check.py would fail it; intake never asks)
        d = scaffold_spec(self._tmp / "residue")
        write(d / "intent.md", GOOD_INTENT.format(sha="3fa9c21")
              + "\nAudience: <target users> everywhere.\n")
        r = self.run_cli(d, "--emit-spawns", "--span", "shape")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("span entry refused", r.stdout)
        self.assertEqual(
            sorted(p.name for p in (d / "spawns" / "wave-1").glob("*.md")),
            ["surveyor.md"])
        self.assertEqual(self.telemetry_rows("intake_refusal"), [])

    def test_empty_intent_file_is_ready_never_refused(self):
        d = scaffold_spec(self._tmp / "empty")
        write(d / "intent.md", "")
        r = self.run_cli(d, "--emit-spawns", "--span", "shape")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("span entry refused", r.stdout)
        self.assertEqual(self.telemetry_rows("intake_refusal"), [])


class ShapeValidIntentRunTests(TelemetryStoreTestCase):
    """TC-007: a green intent admits the authoring waves — the payloads
    are the authoring wave's (the surveyor; never an implementer); and a
    docset at the approve boundary drains the shape span at its named
    handoff without ever emitting an execute payload."""

    def test_valid_intent_admits_the_authoring_wave(self):
        # non-git tmp: the baseline's staleness probe reads SKIPPED (a
        # note, never fatal), so the filled artifact checks green
        d = scaffold_spec(self._tmp / "valid")
        write(d / "intent.md", GOOD_INTENT.format(sha="3fa9c21"))
        for f in ("survey.md", "plan.md", "tech-spec.md", "test.md",
                  "task.md"):
            self.assertTrue((d / f).exists(), f)
        r = self.run_cli(d, "--emit-spawns", "--span", "shape")
        self.assertNotEqual(r.returncode, 4, r.stdout)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("span entry refused", r.stdout)
        payloads = sorted(p.name for p in (d / "spawns").rglob("*.md"))
        self.assertEqual(payloads, ["surveyor.md"],
                         "the authoring wave's own payload set")
        self.assertEqual(self.telemetry_rows("intake_refusal"), [])

    def test_drained_span_stops_at_approve_and_never_executes(self):
        # the committed mini-spec sits exactly at the approve boundary:
        # draft Status, verify green, approve the whole frontier
        d = copy_mini_spec(self._tmp / "drain")
        before = doc_hashes(d)
        r = self.run_cli(d, "--run", "--span", "shape")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("span drained — approve handoff", r.stdout)
        self.assertIn("--span execute", r.stdout)
        self.assertNotIn("AWAITING HUMAN", r.stdout)
        self.assertNotIn("== wave", r.stdout)
        self.assertNotIn("implementer", r.stdout)
        self.assertFalse((d / "spawns").exists(),
                         "a drained span writes no execute payload")
        self.assertEqual(before, doc_hashes(d))
        pauses = self.telemetry_rows("gate_pause")
        self.assertTrue(pauses
                        and pauses[-1]["payload"]["node"] == "approve")


class LegacyDirCompatTests(TelemetryStoreTestCase):
    """FR-008: a pre-split docset (no intent.md) is untouched by the new
    gate — the shape span admits it (intent SKIPPED citing FR-008), the
    bare full-span report keeps the pre-split vocabulary (the marker
    list below; the byte-for-byte monolith comparison retired with the
    monolith's tree, T023 — this skill's engine is the master now), and
    the committed fixture itself is only ever read: the proof anchor
    (the master check.py PASS on it) holds with the tree checksummed
    before and after."""

    @classmethod
    def setUpClass(cls):
        cls.before = dir_checksum(MINI_SPEC)
        cls.repo_before = dir_checksum(MINI_SPEC_REPO)
        cls.anchor = subprocess.run(
            [sys.executable, str(MASTER_CHECK), str(MINI_SPEC)],
            capture_output=True, text=True, timeout=300)

    @classmethod
    def tearDownClass(cls):
        assert dir_checksum(MINI_SPEC) == cls.before, \
            "the read-only fixture was mutated"
        assert dir_checksum(MINI_SPEC_REPO) == cls.repo_before, \
            "the read-only fixture repo was mutated"

    def test_proof_anchor_master_check_passes_in_place(self):
        self.assertEqual(self.anchor.returncode, 0, self.anchor.stdout)
        self.assertIn("PASS", self.anchor.stdout)

    def test_shape_span_admits_the_pre_split_dir(self):
        d = copy_mini_spec(self._tmp / "legacy")
        r = self.run_cli(d, "--emit-spawns", "--span", "shape")
        self.assertNotEqual(r.returncode, 4, r.stdout)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("span entry refused", r.stdout)
        self.assertIn("no shape-span agent payloads", r.stdout)
        self.assertFalse((d / "spawns").exists())
        self.assertEqual(self.telemetry_rows("intake_refusal"), [])
        state = json.loads(self.run_cli(d, "--state-json").stdout)
        self.assertEqual(state["nodes"]["intent"]["state"], "SKIPPED")
        self.assertIn("FR-008", state["nodes"]["intent"]["reason"])

    def test_bare_full_span_report_matches_the_pre_split_vocabulary(self):
        d = copy_mini_spec(self._tmp / "vocab")
        successor = self.run_cli(d)
        self.assertEqual(successor.returncode, 0, successor.stderr)
        for marker in ("workflow graph:", "Status: draft", "frontier",
                       "approve", "survey", "verify", "execute",
                       "tick-commit", "archive",
                       "git: SKIPPED (not a git repo)"):
            self.assertIn(marker, successor.stdout, marker)


if __name__ == "__main__":
    unittest.main(verbosity=2)
