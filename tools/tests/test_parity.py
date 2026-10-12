"""Kit parity pin — the FR-005 shared core stays one engine, byte-identical
in every graph.py-shipping skill (master skills/spec-shape/scripts/ plus its
replicas), backing NFR-001 (no dialect/engine fork) and NFR-003 (a kit-level
suite behind each skill's own). Kill criterion: any released divergence — a
mutated, missing, or extra closure copy — fails this suite.
"""
import hashlib
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PARITY = REPO_ROOT / "tools" / "parity.py"

_spec = importlib.util.spec_from_file_location("parity_tool", PARITY)
parity = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parity)

GRAPH_SKILLS = sorted(
    p.parent.parent.name
    for p in (REPO_ROOT / "skills").glob("*/scripts/graph.py"))
CLOSURE = parity.closure()


class DiscoveryTests(unittest.TestCase):
    def test_graph_shipping_skills_pinned_exactly(self):
        # the trio alone since the monolith's retirement (T023) —
        # discovery is keyed on graph.py shipping, never a hand list
        self.assertEqual(
            GRAPH_SKILLS,
            ["spec-execute", "spec-intent", "spec-shape"])

class ParityTests(unittest.TestCase):
    def test_closure_files_byte_identical_across_master_and_replicas(self):
        for name in CLOSURE:
            with self.subTest(closure_file=name):
                shas = {
                    hashlib.sha256(
                        (REPO_ROOT / "skills" / skill / "scripts" / name)
                        .read_bytes()).hexdigest()
                    for skill in GRAPH_SKILLS}
                self.assertEqual(len(shas), 1, f"{name} diverged")


class DivergenceFixtureTests(unittest.TestCase):
    def test_mutated_replica_byte_fails_check_and_real_tree_is_green(self):
        tmp = Path(tempfile.mkdtemp(prefix="parity-test-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        repo = tmp / "repo"
        shutil.copytree(REPO_ROOT, repo, ignore=shutil.ignore_patterns(
            ".git", ".DS_Store", "__pycache__"))
        victim = repo / "skills" / "spec-intent" / "scripts" / "graph.py"
        mutated = bytearray(victim.read_bytes())
        mutated[-1] ^= 1
        victim.write_bytes(bytes(mutated))
        r = subprocess.run(
            [sys.executable, str(repo / "tools" / "parity.py"), "--check"],
            capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("DRIFT", r.stdout)
        self.assertIn("skills/spec-intent/scripts/graph.py", r.stdout)
        real = subprocess.run(
            [sys.executable, str(PARITY), "--check"],
            capture_output=True, text=True, timeout=300)
        self.assertEqual(real.returncode, 0, real.stdout + real.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
