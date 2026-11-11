"""One dir walks idea -> gen -> execute through each skill's own engine
copy; every seam must hand off with the right next step."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SHAPE = REPO / "skills" / "spec-author"
MINI = SHAPE / "examples" / "mini-spec"

INTENT = (
    "# Intent: mini-spec\n\n**Baseline**: intent v1 @ 3fa9c21\n\n"
    "## Problem\nUsers cannot multiply integers.\n\n"
    "## Audience\n- Calculator users chaining add calls.\n\n"
    "## Constraints\n- Stdlib only.\n\n"
    "## Questions\n- who is the audience — answered: calculator users.\n\n"
    "## FR seeds\n- **FR-001**: The system shall multiply two integers.\n")


def run_graph(skill, spec_dir, *args):
    graph = REPO / "skills" / skill / "scripts" / "graph.py"
    env = dict(os.environ, KIT_TELEMETRY="off")
    return subprocess.run([sys.executable, str(graph), str(spec_dir), *args],
                          capture_output=True, text=True, timeout=300,
                          env=env)


class ChainTests(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp(prefix="chain-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        shutil.copytree(MINI / "repo", tmp / "repo")
        self.spec = tmp / "specs" / "mini-spec"
        shutil.copytree(MINI / "specs" / "mini-spec", self.spec)

    def test_intake_to_shape_to_execute_handoffs(self):
        spec_md = (self.spec / "spec.md").read_text(encoding="utf-8")
        (self.spec / "spec.md").unlink()
        (self.spec / "intent.md").write_text(INTENT, encoding="utf-8")

        shape = run_graph("spec-author", self.spec, "--run", "--span", "shape")
        self.assertEqual(shape.returncode, 0, shape.stdout + shape.stderr)
        self.assertIn("draft it from intent.md", shape.stdout)

        (self.spec / "spec.md").write_text(spec_md, encoding="utf-8")
        shape = run_graph("spec-author", self.spec, "--run", "--span", "shape")
        self.assertEqual(shape.returncode, 0, shape.stdout + shape.stderr)
        self.assertIn("/spec-execute", shape.stdout)

        refused = run_graph("spec-execute", self.spec, "--run", "--span",
                            "execute")
        self.assertEqual(refused.returncode, 4, refused.stdout)

        approved = re.sub(r"\*\*Status\*\*: draft", "**Status**: approved",
                          spec_md, count=1)
        (self.spec / "spec.md").write_text(approved, encoding="utf-8")
        # a Status word alone is not an approval — the freeze is its record
        flipped = run_graph("spec-execute", self.spec, "--run", "--span",
                            "execute")
        self.assertEqual(flipped.returncode, 4, flipped.stdout)

        emitted = run_graph("spec-author", self.spec, "--emit-spawns",
                            "--span", "shape")
        self.assertNotIn("reviewer-contract.md", emitted.stdout,
                         "an unfrozen approved Status is not the approve gate")
        (self.spec / "spec.md").write_text(spec_md, encoding="utf-8")
        emitted = run_graph("spec-author", self.spec, "--emit-spawns",
                            "--span", "shape")
        payload = next(self.spec.glob("spawns/*/reviewer-contract.md"))
        fingerprint = re.search(r"Docset fingerprint: (\w+)",
                                payload.read_text(encoding="utf-8")).group(1)
        (self.spec / "approvals").mkdir()
        (self.spec / "approvals" / "review.md").write_text(
            f"# Contract review\n\nDocset fingerprint: {fingerprint}\n\n"
            "digest: BLOCK 0 · WARN 0 · NIT 0 · worst none\n",
            encoding="utf-8")
        frozen = subprocess.run(
            [sys.executable, str(SHAPE / "scripts" / "freeze.py"),
             str(self.spec), "--record"], capture_output=True, text=True)
        self.assertEqual(frozen.returncode, 0, frozen.stderr)
        (self.spec / "spec.md").write_text(approved, encoding="utf-8")
        admitted = run_graph("spec-execute", self.spec, "--run", "--span",
                             "execute")
        self.assertNotEqual(admitted.returncode, 4, admitted.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
