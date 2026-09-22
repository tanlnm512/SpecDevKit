"""Tests for the dynamic-workflow dialect surface (ADR-019).

Three layers, one file: the generator (determinism, --check), the two
committed dialect artifacts (per-runtime structural invariants — the
tokens each workflow runtime requires or forbids), and the installer
(per-harness targeting, skill_dir baking, foreign refusal, drift
detection, absent-home skip, no-write --dry-run/--check, FR-009) under
a fake HOME, plus the sync.sh wiring.
The install tests never touch the live HOME: the repo is copied to a
temp dir and HOME pointed at a fresh one, exactly like test_sync.py.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / "skills" / "spec-to-prod" / "workflows"
DWF_TS = WORKFLOWS / "spec-run.dwf.ts"
WF_JS = WORKFLOWS / "spec-run.js"
LEDGER = ".spec-dev-kit-deployed"

HUMAN_GATES = ["clarify", "research-gate", "before-audit", "approve",
               "closing-audit", "tick-commit"]
AGENT_NODES = ["survey", "research", "plan", "tech", "qa", "tasks",
               "execute"]
STOP_TOKENS = ["max-waves", "no doc-state change", "AWAITING HUMAN",
               "complete", "held"]
PAYLOAD_RE = r"^ {3}payload: (\S+) \(role: (\S+), node: (\S+)\)$"


def run_py(*argv, **kw):
    return subprocess.run(
        ["python3", str(REPO_ROOT / "tools" / "workflow-defs.py"), *argv],
        capture_output=True, text=True, timeout=120, **kw)


class GeneratorTests(unittest.TestCase):
    def test_regeneration_is_deterministic_and_check_passes(self):
        before_ts = DWF_TS.read_text()
        before_js = WF_JS.read_text()
        r1 = run_py("--out", str(WORKFLOWS))
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.assertEqual(before_ts, DWF_TS.read_text())
        self.assertEqual(before_js, WF_JS.read_text())
        r2 = run_py("--check")
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        self.assertIn("OK", r2.stdout)

    def test_check_flags_a_hand_edited_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            run_py("--out", str(out))
            victim = out / "spec-run.js"
            victim.write_text(victim.read_text() + "\n// hand edit\n")
            r = run_py("--out", str(out), "--check")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("DRIFT", r.stdout)

    def test_check_flags_a_missing_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            r = run_py("--out", str(td), "--check")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("MISSING", r.stdout)

    def test_masters_carry_the_skill_dir_placeholder(self):
        for path in (DWF_TS, WF_JS):
            self.assertIn("__SKILL_DIR__", path.read_text(), path.name)


# Both dialects carry the placeholder inside a double-quoted JS-family
# string literal; --bake must encode for that grammar, so every character
# raw substitution would eat (&, |, backslash) or that would terminate the
# literal (quote, newline, control chars) survives verbatim.
BAKED_LITERAL_RE = r'const SKILL_DIR_BAKED = ("(?:[^"\\]|\\.)*");'
ADVERSARIAL_DIR = '/sk"ill & d\'ir \\ back|pipe $dollar (paren) tab\tend'


class BakeTests(unittest.TestCase):
    def baked(self, master, skill_dir):
        r = run_py("--bake", str(master), "--skill-dir", skill_dir)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_bake_encodes_the_path_as_a_string_literal(self):
        for master in (DWF_TS, WF_JS):
            baked = self.baked(master, ADVERSARIAL_DIR)
            self.assertNotIn("__SKILL_DIR__", baked, master.name)
            m = re.search(BAKED_LITERAL_RE, baked)
            self.assertIsNotNone(
                m, f"no SKILL_DIR_BAKED literal in {master.name}")
            self.assertEqual(json.loads(m.group(1)), ADVERSARIAL_DIR)

    def test_bake_touches_only_the_placeholder(self):
        master = DWF_TS
        baked = self.baked(master, ADVERSARIAL_DIR)
        m = re.search(BAKED_LITERAL_RE, baked)
        self.assertEqual(
            baked.replace(m.group(1)[1:-1], "__SKILL_DIR__"),
            master.read_text())

    def test_bake_keeps_each_literal_on_one_line(self):
        weird = "/nl\nline\ttab\x01ctl"
        for master in (DWF_TS, WF_JS):
            baked = self.baked(master, weird)
            m = re.search(BAKED_LITERAL_RE, baked)
            self.assertEqual(json.loads(m.group(1)), weird)
            self.assertEqual(len(baked.splitlines()),
                             len(master.read_text().splitlines()))

    def test_bake_without_skill_dir_is_a_usage_error(self):
        r = run_py("--bake", str(DWF_TS))
        self.assertEqual(r.returncode, 2)


class ZcodeDialectTests(unittest.TestCase):
    """The zcode facade compiles a plain function body: no import/export/
    declare token anywhere (comments included), a /* zcode-workflow */
    metadata block with the documented fields only, literal phase names,
    and world.run with a literal command."""

    def setUp(self):
        self.ts = DWF_TS.read_text()

    def test_no_facade_forbidden_tokens(self):
        for token in ("import", "export", "declare"):
            self.assertIsNone(
                re.search(rf"\b{token}\b", self.ts),
                f"forbidden token {token!r} in spec-run.dwf.ts")

    def test_metadata_block_uses_documented_fields_only(self):
        m = re.search(r"/\* zcode-workflow\n(.*?)\n\*/", self.ts, re.S)
        self.assertIsNotNone(m, "no /* zcode-workflow */ metadata block")
        block = m.group(1)
        for field in ("description:", "whenToUse:", "args:"):
            self.assertIn(field, block)
        # only the documented fields — the filename carries the name
        for line in block.splitlines():
            self.assertFalse(
                re.match(r"^[a-zA-Z]+:", line) and
                not line.startswith(("description", "whenToUse", "args",
                                     " ", "-", "#")),
                f"undocumented metadata field: {line}")

    def test_phase_names_are_compile_time_literals(self):
        phases = re.findall(r'phase\("([^"]+)"\)', self.ts)
        self.assertEqual(phases, [
            "Read doc state and check the human gates",
            "Run the ready wave",
            "Closing pre-check — reviewer + read-only audits",
            "Recompute and summarize",
        ])
        self.assertFalse(re.search(r"phase\((?!\"|\))", re.sub(
            r"phase\(\"[^\"]*\"\)", "", self.ts)), "non-literal phase call")

    def test_world_run_literal_command_and_typed_asks(self):
        self.assertIn('world.run("python3", [', self.ts)
        self.assertIn(".ask<WaveDigest>(", self.ts)
        self.assertIn("await artifact.markdown(", self.ts)

    def test_summary_reuses_the_last_post_wave_state(self):
        # every stop path leaves st fresh from its most recent fetch —
        # the summary needs no extra graph.py run (D-020 parity with the
        # claude dialect)
        self.assertIn("const finalSt = st;", self.ts)
        self.assertNotIn("const finalSt = await graphState();", self.ts)


class ClaudeDialectTests(unittest.TestCase):
    """Claude Code dynamic workflows: `export const meta` as the first
    statement, no module loading, no direct fs/shell in the script (the
    graph-probe agent is the seam), deterministic primitives only."""

    def setUp(self):
        self.js = WF_JS.read_text()

    def test_meta_is_the_first_statement(self):
        first = next(l for l in self.js.splitlines() if l.strip())
        self.assertTrue(first.startswith("export const meta"),
                        f"first statement is: {first!r}")
        self.assertIn('name: "spec-run"', self.js)

    def test_no_import_and_no_nondeterministic_primitives(self):
        self.assertIsNone(re.search(r"\bimport\b", self.js))
        self.assertNotIn("Date.now", self.js)
        self.assertNotIn("Math.random", self.js)

    def test_documented_primitives_and_schema_validation(self):
        for token in ("pipeline(", "agent(", "phase(", "log(",
                      "schema:", "additionalProperties: false"):
            self.assertIn(token, self.js)

    def test_shell_needs_route_through_the_probe_agent(self):
        # the only places shell-ish text may appear are inside the probe
        # agent's prompt strings — never as script-level calls
        self.assertNotIn('world.run', self.js)
        self.assertNotIn("subprocess", self.js)
        self.assertIn("graph-probe", self.js)

    def test_single_probe_per_wave(self):
        # one agent fetches state + emit outputs together (marker-split),
        # and the summary reuses the last post-wave state — no extra probe
        self.assertIn("__SPLIT__", self.js)
        self.assertEqual(self.js.count('"graph-probe"'), 1)
        self.assertIn("--state-json", self.js)
        self.assertIn("--emit-spawns", self.js)
        self.assertIn("fetchCycle", self.js)
        self.assertIn("const finalSt = st;", self.js)


class ParityTests(unittest.TestCase):
    """Both dialects mirror the same loop contract: the six human gates,
    the agent-node set, the graph.py invocations, and the stop
    conditions — the mechanical guarantee that the two runtimes behave
    identically (FR-003)."""

    def test_both_name_every_human_gate(self):
        for path in (DWF_TS, WF_JS):
            for gate in HUMAN_GATES:
                self.assertIn(gate, path.read_text(), f"{gate} in {path.name}")

    def test_both_cover_the_agent_nodes_and_oracle_flags(self):
        for path in (DWF_TS, WF_JS):
            text = path.read_text()
            for node in AGENT_NODES:
                self.assertIn(f'"{node}"', text, f"{node} in {path.name}")
            self.assertIn("--state-json", text)
            self.assertIn("--emit-spawns", text)
            self.assertIn("graph.py", text)

    def test_both_stop_on_the_same_conditions(self):
        for path in (DWF_TS, WF_JS):
            text = path.read_text()
            for token in STOP_TOKENS:
                self.assertIn(token, text, f"{token} in {path.name}")

    def test_payload_line_regexes_are_identical(self):
        ts = DWF_TS.read_text()
        js = WF_JS.read_text()
        self.assertEqual(ts.count(PAYLOAD_RE), 1)
        self.assertEqual(js.count(PAYLOAD_RE), 1)

    def test_both_have_a_bounded_rebrief_round(self):
        for path in (DWF_TS, WF_JS):
            text = path.read_text()
            self.assertIn("re-brief round 1", text, path.name)
            self.assertIn("rebriefText", text, path.name)
            # the once-only guard: a payload already retried is never
            # retried again in the same run
            self.assertIn("retriedPaths.indexOf", text, path.name)
            # the failure evidence rides verbatim in the retry ask
            self.assertIn("address that failure evidence directly", text, path.name)

    def test_both_carry_the_launch_weight_preflight(self):
        # D-022: the dialects' metadata points the invoker at graph.py
        # --launch-check — only a weight "wave" span justifies a launch
        for path in (DWF_TS, WF_JS):
            text = path.read_text()
            self.assertIn("--launch-check", text, path.name)
            self.assertIn('wave', text, path.name)

    def test_both_precheck_the_closing_stop(self):
        # D-023: at the closing-audit stop both dialects spawn the
        # implementation-diff reviewer and run the read-only audit modes
        # before returning — the ack session opens with results
        for path in (DWF_TS, WF_JS):
            text = path.read_text()
            self.assertIn("reviewer-diff", text, path.name)
            self.assertIn("closing precheck", text, path.name)
            self.assertIn("--dry-run", text, path.name)
            self.assertIn("implementation-diff", text, path.name)


class InstallerBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wfinstall-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"
        shutil.copytree(
            REPO_ROOT, self.repo,
            ignore=shutil.ignore_patterns(".git", ".DS_Store", "__pycache__"))
        self.home = self.tmp / "home"
        self.home.mkdir()

    def stub_skill(self, harness):
        """A minimal installed skill copy — just enough for the
        installer's scripts/graph.py validation."""
        d = self.home / f".{harness}" / "skills" / "spec-to-prod" / "scripts"
        d.mkdir(parents=True)
        (d / "graph.py").write_text("# stub\n")

    def run_install(self, *argv):
        return subprocess.run(
            ["bash", str(self.repo / "tools" / "install-workflow.sh"), *argv],
            env=dict(os.environ, HOME=str(self.home)),
            capture_output=True, text=True, timeout=120)

    def home_snapshot(self):
        """relpath -> sha256 for every file under the temp HOME."""
        return {
            str(p.relative_to(self.home)):
                hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(self.home.rglob("*")) if p.is_file()
        }


class InstallTests(InstallerBase):
    def test_all_installs_each_dialect_to_its_own_root(self):
        self.stub_skill("zcode")
        self.stub_skill("claude")
        r = self.run_install("all")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        ts = self.home / ".zcode" / "workflows" / "spec-run.dwf.ts"
        js = self.home / ".claude" / "workflows" / "spec-run.js"
        self.assertTrue(ts.is_file() and js.is_file())
        for path, harness in ((ts, "zcode"), (js, "claude")):
            text = path.read_text()
            self.assertNotIn("__SKILL_DIR__", text, f"{path.name} unbaked")
            baked = self.home / f".{harness}" / "skills" / "spec-to-prod"
            self.assertIn(str(baked), text,
                          f"{path.name} did not bake its own root's skill dir")
        # idempotent: a second install stays clean
        r2 = self.run_install("all")
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)

    def test_adversarial_home_bakes_a_verbatim_literal(self):
        # the whole install root — HOME included — may carry characters a
        # raw substitution would eat; the baked literal must parse back to
        # the exact resolved skill dir and --check must agree
        self.home = self.tmp / 'we&ird "q" $doll\'ar |pipe\\ back'
        self.home.mkdir()
        self.stub_skill("zcode")
        r = self.run_install("zcode")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        dest = self.home / ".zcode" / "workflows" / "spec-run.dwf.ts"
        skill = self.home / ".zcode" / "skills" / "spec-to-prod"
        m = re.search(BAKED_LITERAL_RE, dest.read_text())
        self.assertIsNotNone(m, "no SKILL_DIR_BAKED literal in the install")
        self.assertEqual(json.loads(m.group(1)), str(skill))
        r2 = self.run_install("zcode", "--check")
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)

    def test_absent_harness_home_skips_loudly(self):
        self.stub_skill("claude")  # zcode home deliberately absent
        r = self.run_install("zcode")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("skip", r.stdout)
        self.assertFalse((self.home / ".zcode").exists(),
                         "user-mode home must never be fabricated")

    def test_foreign_destination_refused(self):
        self.stub_skill("claude")
        dest = self.home / ".claude" / "workflows" / "spec-run.js"
        dest.parent.mkdir(parents=True)
        dest.write_text("// a hand-written workflow, not ours\n")
        r = self.run_install("claude")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        self.assertIn("hand-written", dest.read_text())  # never clobbered

    def test_check_flags_drift(self):
        self.stub_skill("zcode")
        self.assertEqual(self.run_install("zcode").returncode, 0)
        victim = self.home / ".zcode" / "workflows" / "spec-run.dwf.ts"
        victim.write_text(victim.read_text() + "\n// hand edit\n")
        r = self.run_install("zcode", "--check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("DRIFT", r.stdout)
        # a never-installed copy is a MISSING, also a failure
        self.stub_skill("claude")
        r2 = self.run_install("claude", "--check")
        self.assertNotEqual(r2.returncode, 0)
        self.assertIn("MISSING", r2.stdout)

    def test_dry_run_and_check_write_nothing(self):
        # FR-009: both modes report without touching a byte — --dry-run
        # on a fresh HOME fabricates no workflow root, and --check on a
        # drifted copy reports DRIFT and repairs nothing
        self.stub_skill("zcode")
        r = self.run_install("zcode", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("would install", r.stdout)
        self.assertFalse((self.home / ".zcode" / "workflows").exists())
        self.assertEqual(self.run_install("zcode").returncode, 0)
        before = self.home_snapshot()
        ok = self.run_install("zcode", "--check")
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertIn("OK", ok.stdout)
        self.assertEqual(self.home_snapshot(), before)
        victim = self.home / ".zcode" / "workflows" / "spec-run.dwf.ts"
        drifted = victim.read_text() + "\n// hand edit\n"
        victim.write_text(drifted)
        after_edit = self.home_snapshot()
        bad = self.run_install("zcode", "--check")
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("DRIFT", bad.stdout)
        self.assertEqual(victim.read_text(), drifted)
        self.assertEqual(self.home_snapshot(), after_edit)

    def test_master_update_reinstalls_over_ledgered_copy(self):
        # the repo's provenance rule (sync.sh's): a deployed copy that
        # still matches its ledger entry is ours-stale, replaced when
        # the master moves; a copy drifted from BOTH the expected bake
        # and the ledger is foreign (covered by the refusal test above)
        self.stub_skill("zcode")
        self.assertEqual(self.run_install("zcode").returncode, 0)
        dest = self.home / ".zcode" / "workflows" / "spec-run.dwf.ts"
        before = dest.read_text()
        master = (self.repo / "skills" / "spec-to-prod" / "workflows"
                  / "spec-run.dwf.ts")
        master.write_text(master.read_text() + "\n// master moved on\n")
        r = self.run_install("zcode")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotEqual(before, dest.read_text())  # updated
        self.assertIn("master moved on", dest.read_text())

    def test_project_mode_installs_into_repo_roots(self):
        proj = self.tmp / "proj"
        (proj / ".zcode" / "skills" / "spec-to-prod" / "scripts").mkdir(
            parents=True)
        (proj / ".zcode" / "skills" / "spec-to-prod" / "scripts" /
         "graph.py").write_text("# stub\n")
        r = subprocess.run(
            ["bash", str(self.repo / "tools" / "install-workflow.sh"),
             "zcode", "--project", "--repo", str(proj)],
            env=dict(os.environ, HOME=str(self.home)),
            capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        dest = proj / ".zcode" / "workflows" / "spec-run.dwf.ts"
        self.assertTrue(dest.is_file())
        self.assertNotIn("__SKILL_DIR__", dest.read_text())

    def test_no_skill_copy_to_bake_fails_loudly(self):
        (self.home / ".zcode").mkdir()  # home exists, skill does not
        r = self.run_install("zcode")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ERROR", r.stderr + r.stdout)

    def test_sync_installs_and_verifies_workflows(self):
        r1 = subprocess.run(
            ["bash", str(self.repo / "tools" / "sync.sh")],
            env=dict(os.environ, HOME=str(self.home)),
            capture_output=True, text=True, timeout=300)
        self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
        ts = self.home / ".zcode" / "workflows" / "spec-run.dwf.ts"
        js = self.home / ".claude" / "workflows" / "spec-run.js"
        self.assertTrue(ts.is_file() and js.is_file())
        self.assertNotIn("__SKILL_DIR__", ts.read_text())
        self.assertNotIn("__SKILL_DIR__", js.read_text())
        self.assertIn("graph.py", ts.read_text())
        r2 = subprocess.run(
            ["bash", str(self.repo / "tools" / "sync.sh")],
            env=dict(os.environ, HOME=str(self.home)),
            capture_output=True, text=True, timeout=300)
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        self.assertIn(str(ts), r2.stdout)  # verify pass covered the file


if __name__ == "__main__":
    unittest.main(verbosity=2)
