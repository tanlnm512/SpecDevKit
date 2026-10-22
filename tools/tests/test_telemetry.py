"""Tests for the kit's local telemetry (skills/*/scripts/telemetry.py).

Three contracts:
1. Parity — the module is byte-identical across every skill that
   ships it (the kit's self-contained-packaging duplication, pinned
   so the copies cannot diverge).
2. Behavior — record/summary/off-switch, via KIT_TELEMETRY_DIR into a
   temp store.
3. Constitution — recording is fire-and-forget: a read-only store dir
   or a bad payload never raises into the host script.
"""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS = sorted(p.name for p in (REPO_ROOT / "skills").iterdir()
                if (p / "scripts" / "telemetry.py").exists())


def load(skill):
    spec = importlib.util.spec_from_file_location(
        f"telemetry_{skill}", REPO_ROOT / "skills" / skill / "scripts"
        / "telemetry.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ParityTests(unittest.TestCase):
    def test_all_five_skills_ship_the_module(self):
        self.assertEqual(SKILLS, ["spec-brainstorming", "spec-code-review",
                                  "spec-execute", "spec-intent",
                                  "spec-shape"])

    def test_modules_are_byte_identical(self):
        shas = {(REPO_ROOT / "skills" / s / "scripts" / "telemetry.py")
                .read_bytes() for s in SKILLS}
        self.assertEqual(len(shas), 1)


class BehaviorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Path(self.tmp.name)
        self.env = dict(os.environ, KIT_TELEMETRY_DIR=str(self.store))
        self.old = {k: os.environ.get(k) for k in
                    ("KIT_TELEMETRY_DIR", "KIT_TELEMETRY")}
        os.environ.update(self.env)
        self.addCleanup(self._restore)

    def _restore(self):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_record_appends_jsonl_and_summary_aggregates(self):
        t = load("spec-shape")
        t.record("spec-shape", "wave", wave=1, payloads=3)
        t.record("spec-shape", "wave", wave=2, payloads=5)
        t.record("spec-shape", "gate_pause", node="approve")
        p = self.store / "spec-shape.jsonl"
        rows = [json.loads(l) for l in p.read_text().splitlines()]
        self.assertEqual([r["event"] for r in rows],
                         ["wave", "wave", "gate_pause"])
        self.assertEqual(rows[0]["payload"], {"wave": 1, "payloads": 3})
        self.assertEqual(rows[0]["schema"], 1)
        s = t.summary("spec-shape")
        self.assertIn("**wave**: 2", s)
        self.assertIn("**gate_pause**: 1", s)
        self.assertIn("payloads: mean 4.0", s)
        self.assertIn("p90 5.0", s)

    def test_off_switch_writes_nothing(self):
        t = load("spec-shape")
        os.environ["KIT_TELEMETRY"] = "off"
        try:
            t.record("spec-shape", "wave", wave=1)
        finally:
            os.environ.pop("KIT_TELEMETRY", None)
        self.assertFalse((self.store / "spec-shape.jsonl").exists())

    def test_record_swallows_errors(self):
        t = load("spec-shape")
        # store dir occupied by a regular file -> mkdir fails -> swallowed
        blocker = self.store / "blocker"
        blocker.parent.mkdir(parents=True, exist_ok=True)
        os.environ["KIT_TELEMETRY_DIR"] = str(blocker)
        try:
            t.record("spec-shape", "wave", wave=1)  # must not raise
        finally:
            os.environ["KIT_TELEMETRY_DIR"] = str(self.store)

    def test_summary_on_missing_store_is_honest(self):
        t = load("spec-code-review")
        self.assertIn("no telemetry recorded",
                      t.summary("spec-code-review"))

    def test_cli_record_and_summary(self):
        import subprocess, sys
        mod = REPO_ROOT / "skills" / "spec-shape" / "scripts" \
            / "telemetry.py"
        r = subprocess.run(
            [sys.executable, str(mod), "record", "spec-shape",
             "check_run", '{"fails": 0, "warns": 1}'],
            env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        r2 = subprocess.run(
            [sys.executable, str(mod), "summary", "spec-shape"],
            env=self.env, capture_output=True, text=True)
        self.assertIn("**check_run**: 1", r2.stdout)
        self.assertIn("warns: mean 1.0", r2.stdout)


if __name__ == "__main__":
    unittest.main()
