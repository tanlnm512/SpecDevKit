#!/usr/bin/env python3
"""Workflow runtime execution tests (rubric W4).

EXECUTES skills/spec-to-prod/workflows/spec-run.js (Claude dialect) in
a Node harness that provides the workflow runtime's documented
primitive set — agent(), pipeline(), phase(), log() — with scripted
agent responses and a graph-probe agent that runs the REAL graph.py
oracle against a fixture spec. This is execution validation, not the
static parity the workflow-copies tests do: a logic error in the
loop's stop conditions or wave assembly fails here.

Serves: kit grading rubric W4 (mechanical); the level-up plan Phase 1.
Skipped loudly where node is unavailable — a skip is reported, never
credited.
"""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOW = ROOT / "skills" / "spec-to-prod" / "workflows" / "spec-run.js"
SKILL_DIR = ROOT / "skills" / "spec-to-prod"
FIXTURE = SKILL_DIR / "examples" / "mini-spec" / "specs" / "mini-spec"

HARNESS_JS = r"""
"use strict";
const fs = require("fs");
const { execSync } = require("child_process");

const workflowPath = process.argv[2];
const fixtureRoot = process.argv[3];
const skillDir = process.argv[4];
const args = JSON.parse(process.argv[5] || "{}");

// Mirror install-workflow.sh's bake: the master ships a placeholder so
// one edit ships without a workflow edit.
const src = fs
  .readFileSync(workflowPath, "utf8")
  .replace("export const meta", "const meta")
  .replace(/"__SKILL_DIR__"/g, JSON.stringify(skillDir));

const calls = [];
const logs = [];
const phases = [];
let lastFindings = [];

async function agent(prompt, opts) {
  const label = opts && opts.label ? opts.label : "unlabeled";
  calls.push({ label: label, prompt: prompt });
  if (label === "graph-probe") {
    const line = prompt
      .split("\n")
      .map((l) => l.trim())
      .find((l) => l.startsWith("python3 "));
    if (!line) throw new Error("probe ask carries no command: " + prompt);
    // The runtime's agent contract: stdout verbatim, empty on failure —
    // a failed command is data for the loop, not a harness crash.
    let stdout = "";
    try {
      stdout = execSync(line, { cwd: fixtureRoot, encoding: "utf8" });
    } catch (e) {
      stdout = (e && e.stdout) || "";
    }
    return { stdout: stdout };
  }
  // Scripted role agent: always blocked, so the loop's no-change stop
  // and bounded re-brief round are exercised without writing artifacts.
  return { status: "blocked", digest: "harness-stub: scripted blocked" };
}

async function pipeline(items, fn) {
  return Promise.all(items.map(fn));
}

function phase(name) {
  phases.push(name);
}

function log() {
  logs.push(Array.from(arguments).join(" "));
}

// The real runtime takes the file completion value; new Function
// needs the arrow to return it explicitly.
const body = "return (async () => {\n" + src + "\n;return result;\n})();";
const fn = new Function("args", "agent", "pipeline", "phase", "log", body);

(async () => {
  const result = await fn(args, agent, pipeline, phase, log);
  process.stdout.write(JSON.stringify({ result: result, calls: calls, logs: logs, phases: phases }));
})().catch((e) => {
  console.error(e && e.stack ? e.stack : String(e));
  process.exit(1);
});
"""


@unittest.skipUnless(shutil.which("node"), "node is not on PATH")
class SpecRunRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="wf-runtime-")
        cls.root = Path(cls.tmp.name)
        cls.harness = cls.root / "harness.js"
        cls.harness.write_text(HARNESS_JS, encoding="utf-8")
        cls.fixture_tmps = []

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()
        for t in cls.fixture_tmps:
            t.cleanup()

    def run_workflow(self, spec_root, spec_name):
        r = subprocess.run(
            ["node", str(self.harness), str(WORKFLOW), str(spec_root),
             str(SKILL_DIR), json.dumps({"spec": spec_name})],
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(
            r.returncode, 0,
            f"workflow execution crashed:\n{r.stdout}\n{r.stderr}",
        )
        return json.loads(r.stdout)

    def make_fixture(self, name):
        # graph.py resolves specs/<name> against the working root. Each
        # fixture gets its OWN root: two mini-spec copies in one specs/
        # tree carry duplicate IDs and fail check.py's repo-level checks.
        holder = tempfile.TemporaryDirectory(prefix=f"wf-{name}-")
        self.fixture_tmps.append(holder)
        root = Path(holder.name)
        (root / "specs").mkdir()
        dest = root / "specs" / name
        shutil.copytree(FIXTURE, dest)
        return root, dest

    def test_human_gate_stops_the_loop_without_spawning(self):
        """The W2-critical property, executed: a READY human gate halts
        the workflow before any role agent spawns."""
        root, _ = self.make_fixture("gate-spec")
        out = self.run_workflow(root, "gate-spec")
        labels = [c["label"] for c in out["calls"]]
        self.assertIn("graph-probe", labels)
        self.assertEqual(
            [l for l in labels if l != "graph-probe"], [],
            f"a human-gated frontier must spawn zero role agents; got {labels}",
        )
        self.assertEqual(out["result"]["stop"]["kind"], "gate")
        self.assertEqual(out["result"]["stop"]["gate"], "approve")
        self.assertTrue(
            any("AWAITING HUMAN: approve" in l for l in out["logs"]),
            f"gate stop not announced in logs: {out['logs']}",
        )

    def test_ready_wave_spawns_then_rebriefs_once_then_stops(self):
        """A READY agent node spawns its role agent; a wave that
        changes no doc state gets exactly ONE re-brief round, then the
        loop stops no-change (never spinning to the wave cap)."""
        root, dest = self.make_fixture("wave-spec")
        (dest / "survey.md").unlink()  # survey node -> READY
        out = self.run_workflow(root, "wave-spec")
        labels = [c["label"] for c in out["calls"]]
        self.assertIn("surveyor", labels, f"ready survey node never spawned: {labels}")
        self.assertIn("surveyor-rebrief", labels, f"bounded re-brief round never ran: {labels}")
        rebriefs = [l for l in labels if l.endswith("-rebrief")]
        self.assertEqual(len(rebriefs), 1, f"re-brief must be exactly one round: {labels}")
        self.assertEqual(out["result"]["stop"]["kind"], "no-change")
        self.assertLessEqual(out["result"]["waves_run"], 2)

    def test_bogus_spec_reports_error_not_a_hang(self):
        """A missing spec must terminate (error/held/no-change), never
        spin to the wave cap."""
        root, _ = self.make_fixture("err-spec")
        out = self.run_workflow(root, "no-such-spec")
        result = out["result"]
        # The error path returns {error}, not {stop}; both terminate.
        self.assertTrue(
            "error" in result or result.get("stop", {}).get("kind") in ("held", "no-change"),
            f"bogus spec did not terminate cleanly: {result}",
        )
        self.assertLessEqual(result.get("waves_run", 0), 2)




REVIEW_HARNESS_JS = r"""
"use strict";
const fs = require("fs");
const { execSync } = require("child_process");

const workflowPath = process.argv[2];
const fixtureRoot = process.argv[3];
const skillDir = process.argv[4];
const args = JSON.parse(process.argv[5] || "{}");

const src = fs
  .readFileSync(workflowPath, "utf8")
  .replace("export const meta", "const meta")
  .replace(/"__SKILL_DIR__"/g, JSON.stringify(skillDir));

const calls = [];
const logs = [];
const phases = [];
let lastFindings = [];

async function agent(prompt, opts) {
  const label = opts && opts.label ? opts.label : "unlabeled";
  calls.push({ label: label, prompt: prompt });
  if (prompt.indexOf("Run this exact shell command") !== -1) {
    const line = prompt.split("\n").map((l) => l.trim())
      .find((l) => l.startsWith("python3 ") || l.startsWith("git ") || l.startsWith("bash "));
    if (!line) throw new Error("probe ask carries no command: " + prompt.slice(0, 120));
    let stdout = "";
    try { stdout = execSync(line, { cwd: fixtureRoot, encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] }); }
    catch (e) { stdout = (e && e.stdout) || ""; }
    return { stdout: stdout };
  }
  // Scripted panel agents, by label shape
  if (label === "preflight-scout") {
    return { modules: [{ name: "app", path: "app.py", role: "the module" }],
             conventions: ["plain functions"], riskAreas: ["none"] };
  }
  if (label.indexOf("-review") !== -1) {
    lastFindings = [{ where: "app.py:2", what: "off-by-one leaves the last item unprocessed",
                      evidence: "for (i = 0; i < n; i++) but n is length+1", severity: "medium",
                      impact: "the final record is dropped on every run" }];
    return { findings: lastFindings };
  }
  if (label.indexOf("-triage") !== -1 || label === "cross-lens-merge") {
    // a schema-valid triage always returns arrays; this one keeps what
    // the scripted reviewer found
    return { kept: lastFindings, dropped: [] };
  }
  if (label.indexOf("confirm-") === 0) {
    return { status: "verified", note: "code alone reproduces it" };
  }
  if (label === "final-assessment") {
    return { risk: "medium", testGaps: ["no test covers the loop bound"],
             residualRisks: ["runtime not exercised"], verdict: "One real defect; fix before merge." };
  }
  if (label.indexOf("fixer-round-") === 0) {
    return { addressed: [], skipped: [], changedPaths: [], notes: [] };
  }
  if (label.indexOf("verify-round-") === 0) {
    return { status: "unfixed", note: "not fixed in this scripted run" };
  }
  throw new Error("unscripted agent label: " + label);
}

async function pipeline(items, fn) { return Promise.all(items.map(fn)); }
function phase(name) { phases.push(name); }
function log() { logs.push(Array.from(arguments).join(" ")); }

const body = "return (async () => {\n" + src + "\n;return result;\n})();";
const fn = new Function("args", "agent", "pipeline", "phase", "log", body);
(async () => {
  const result = await fn(args, agent, pipeline, phase, log);
  process.stdout.write(JSON.stringify({ result: result, calls: calls, logs: logs, phases: phases }));
})().catch((e) => { console.error(e && e.stack ? e.stack : String(e)); process.exit(1); });
"""


@unittest.skipUnless(shutil.which("node"), "node is not on PATH")
class SpecCodeReviewRuntimeTests(unittest.TestCase):
    """Executes the thin Claude dialect (D-014) against a real git
    fixture with scripted panel agents and the REAL oracle underneath —
    proving the probe-relay rewrite orchestrates identically (T006)."""

    REVIEW_WORKFLOW = ROOT / "skills" / "spec-code-review" / "workflows" / "spec-code-review.js"
    REVIEW_SKILL = ROOT / "skills" / "spec-code-review"

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="scr-runtime-")
        cls.root = Path(cls.tmp.name)
        cls.harness = cls.root / "harness.js"
        cls.harness.write_text(REVIEW_HARNESS_JS, encoding="utf-8")
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        cls.run_git("init", "-q", "-b", "main")
        cls.run_git("config", "user.email", "t@example.com")
        cls.run_git("config", "user.name", "T")
        (cls.repo / "app.py").write_text("items = [1, 2, 3]\n", encoding="utf-8")
        cls.run_git("add", "-A")
        cls.run_git("commit", "-qm", "base")
        (cls.repo / "app.py").write_text(
            "items = [1, 2, 3]\nfor i in range(len(items) + 1):\n    print(items[i])\n",
            encoding="utf-8",
        )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def run_git(cls, *git_args):
        subprocess.run(["git", "-C", str(cls.repo), *git_args], check=True,
                       capture_output=True, text=True)

    def run_review(self, args):
        r = subprocess.run(
            ["node", str(self.harness), str(self.REVIEW_WORKFLOW), str(self.repo),
             str(self.REVIEW_SKILL), json.dumps(args)],
            capture_output=True, text=True, timeout=180,
        )
        self.assertEqual(r.returncode, 0, f"review execution crashed:\n{r.stdout}\n{r.stderr}")
        return json.loads(r.stdout)

    def test_fast_diff_review_runs_end_to_end_through_the_oracle(self):
        out = self.run_review({"target": "diff", "base": "HEAD", "mode": "fast", "fix_rounds": 0})
        res = out["result"]
        labels = [c["label"] for c in out["calls"]]
        self.assertIn("scope-probe", labels)
        self.assertIn("systems-probe", labels)
        self.assertIn("general-review", labels)
        self.assertIn("general-triage", labels)
        self.assertIn("confirm-general", labels)
        self.assertIn("final-assessment", labels)
        self.assertIn("report-probe", labels)
        self.assertEqual(res["findings"][0]["where"], "app.py:2")
        self.assertEqual(res["findings"][0]["severity"], "medium")
        self.assertIn("1 confirmed finding", res["conclusion"])
        self.assertIn("### [general-1 · MEDIUM · verified · general]", res["markdown"])
        self.assertIn("## Mechanical gate", res["markdown"])
        self.assertTrue(any("static review" in nc for nc in res["notCovered"]))

    def test_one_probe_per_phase_shape_holds(self):
        out = self.run_review({"target": "diff", "base": "HEAD", "mode": "fast", "fix_rounds": 0})
        labels = [c["label"] for c in out["calls"] if c["label"].endswith("-probe")]
        # exactly one scope, one systems, one ask wave per phase, one report
        for probe in ("scope-probe", "systems-probe", "scout-ask-probe",
                      "review-asks-probe", "triage-asks-probe", "confirm-asks-probe",
                      "final-ask-probe", "report-probe"):
            self.assertEqual(labels.count(probe), 1, f"{probe} ran {labels.count(probe)}x: {labels}")

    def test_red_gate_stops_a_change_review_before_the_panel(self):
        (self.repo / "Makefile").write_text("test:\n\texit 1\n", encoding="utf-8")
        (self.repo / "t.py").write_text("x = 1\n", encoding="utf-8")
        self.run_git("add", "-A")
        self.run_git("commit", "-qm", "red gate")
        (self.repo / "t.py").write_text("x = 2\n", encoding="utf-8")
        try:
            out = self.run_review({"target": "diff", "base": "HEAD", "mode": "fast", "fix_rounds": 0})
            res = out["result"]
            labels = [c["label"] for c in out["calls"]]
            self.assertNotIn("general-review", labels,
                             "the panel must not spawn on a red change-review gate")
            self.assertIn("failed", res["conclusion"])
            self.assertIn("## Failed checks", res["markdown"])
        finally:
            self.run_git("checkout", "-q", "--", ".")
            (self.repo / "Makefile").unlink()
            (self.repo / "t.py").unlink()
            self.run_git("add", "-A")
            self.run_git("commit", "-qm", "restore green")


if __name__ == "__main__":
    unittest.main()
