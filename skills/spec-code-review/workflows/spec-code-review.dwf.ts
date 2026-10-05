/* zcode-workflow
description: >-
  Three-stage code review in any repository, with an optional fix loop,
  over a change, a pull request, a branch's recent changes, or the whole
  project. Stage 1 runs the repo's own detected checks as the mechanical
  gate (the skill's scripts/gate.sh). Stage 2 reviews the target through
  separate lenses — correctness, security, quality & tests (one general
  reviewer in fast mode) — each triaged by one editor, with independent
  confirmation of every kept finding. Stage 3 synthesizes a report with
  risk class, test gaps and residual risks. With fix_rounds > 0 an
  iterative loop follows: an author agent fixes the confirmed findings,
  every fix is independently verified, the gate re-runs, a fresh-eyes
  reviewer scans the fix diff, and the run ends with a risk-gated merge
  recommendation.
whenToUse: >-
  Use when the user asks to review a change — "review the diff",
  "review this change", "review the last commit" — a pull request —
  "review PR 12", "review this pull request" — a branch's recent
  changes — "review what's on this branch", "review the recent changes
  on this branch" — or the project's code as a whole — "review the
  project", "review the whole codebase" — or to review and fix any of
  them. Works in any git repository; the gate adapts by detecting the
  repo's own checks.
args:
  base:
    type: string
    description: >-
      Diff mode: the base ref the change is reviewed against (default
      HEAD — working-tree changes; HEAD~1 reviews the last commit; any
      branch, tag or sha). Branch mode: the base branch the current
      branch is diffed against (default: the remote's default branch).
      Ignored in pr and project mode.
  target:
    type: string
    description: >-
      diff (default) reviews the change against base; branch reviews the
      current branch's recent changes — the merge-base diff against the
      base branch, uncommitted work included; pr reviews a GitHub pull
      request (needs the gh CLI; the PR head is checked out automatically
      on a clean tree, refused on a dirty one); project reviews the
      repository's tracked source files as they stand — all of them: a
      big target is sharded into byte-balanced, directory-coherent
      reviewer parts per lens.
  pr:
    type: string
    description: >-
      Pr mode only: the pull request to review — a number, URL or
      owner/repo#N, resolved with the gh CLI.
  intent:
    type: string
    description: >-
      Optional, change modes only: what this change is supposed to do,
      in the author's words — the intent the reviewers judge against and
      the author's rebuttal channel for deliberate choices. In pr mode
      the PR description is used when this is absent.
  fix_from:
    type: string
    description: >-
      Fix-only continuation: the findings from a previous review — the
      report markdown itself (a file path to the saved report), or
      findings JSON (a file path or inline). Skips the review stages and
      runs the fix loop on the carried findings; fix_rounds defaults
      to 2 in this mode.
  paths:
    type: string
    description: >-
      Project mode only: comma- or space-separated repo-relative
      paths/directories to restrict the target to. Empty means every
      tracked source file.
  repo:
    type: string
    description: >-
      Sub-repo directory to review — for multi-repo workspaces whose
      root is not itself a git repository. Empty means the workspace
      root is the repo. Supported for target project; change/branch/pr
      targets refuse it — run those from inside the repository.
  mode:
    type: string
    description: >-
      fast = one general reviewer; full = three specialists; auto (default)
      picks fast for small targets and full otherwise.
  fix_rounds:
    type: number
    description: >-
      0 = review only (default). N = after the review, run up to N fix
      rounds: the author agent fixes confirmed findings in the working
      tree, each fix is independently verified, the gate re-runs, and a
      fresh-eyes reviewer scans the fix diff. Ends with a merge
      recommendation; fixes stay uncommitted. In fix_from mode N defaults
      to 2 when omitted.
  skill_dir:
    type: string
    description: >-
      Absolute skill dir override (defaults to the path baked at install
      time).
*/

// ---------------------------------------------------------------------------
// spec-code-review.dwf.ts — the zcode dialect (thin oracle-relay form,
// D-014): all shared review state — target resolution, the gate, sharding,
// finding IDs, findings parsing, report assembly, panel systems and ask
// text — lives in scripts/review_orchestrator.py, fetched through ONE
// world.run per phase (NFR-003). This file keeps only what is
// runtime-native: typed agent coordination, panel-brief injection, the
// live findings board, and the run's report bookkeeping.
// ---------------------------------------------------------------------------

interface Finding {
  where: string;
  what: string;
  evidence: string;
  severity: "low" | "medium" | "high";
  impact?: string;
  lens?: string;
}

interface LensReview {
  findings: Finding[];
}

interface DroppedFinding {
  where: string;
  what: string;
  reason: string;
}

interface TriageVerdict {
  kept: Finding[];
  dropped: DroppedFinding[];
}

interface Confirmation {
  status: "verified" | "unconfirmed";
  note: string;
}

interface ConfirmedFinding extends Finding {
  id: string;
  lens: string;
  confirmation: Confirmation;
}

interface Assessment {
  risk: "low" | "medium" | "high";
  testGaps: string[];
  residualRisks: string[];
  verdict: string;
}

interface FinalAssessment extends Assessment {
  recommendation: "merge" | "fix-first" | "human";
}

interface GateResult {
  name: string;
  exitCode: number;
  tail: string;
}

interface RepoMap {
  modules: { name: string; path: string; role: string }[];
  conventions: string[];
  riskAreas: string[];
}

interface PrMeta {
  number: number;
  title: string;
  author: string;
  state: string;
  url: string;
  baseRefName: string;
  baseRefOid: string;
  headRefName: string;
  headRefOid: string;
  body: string;
}

interface ReportedFinding {
  id: string;
  where: string;
  what: string;
  evidence: string;
  status: string;
  severity: "low" | "medium" | "high";
  lens: string;
  impact: string;
  fixStatus: string;
}

interface LensDef {
  label: string;
  name: string;
  system: string;
  focus: string;
}

interface FixOutcome {
  addressed: string[];
  skipped: { id: string; why: string }[];
  changedPaths: string[];
  notes: string[];
}

interface Verification {
  status: "fixed" | "unfixed" | "worse";
  note: string;
}

interface TrackedFinding {
  finding: ConfirmedFinding;
  fix: "pending" | "fixed" | "unfixed" | "worse";
  fixNote: string;
}

const TARGETS = ["diff", "branch", "pr", "project"];
const TARGET = typeof args.target === "string" && args.target.trim() ? args.target.trim().toLowerCase() : "diff";
const PROJECT = TARGET === "project";
const PR = TARGET === "pr";
const BRANCH_MODE = TARGET === "branch";
const PR_ARG = typeof args.pr === "string" && args.pr.trim() ? args.pr.trim() : "";
const INTENT_ARG = typeof args.intent === "string" && args.intent.trim() ? args.intent.trim() : "";
const HAS_BASE = typeof args.base === "string" && args.base.trim() ? true : false;
const BASE_ARG = HAS_BASE ? String(args.base).trim() : "";
// BASE is resolved by the oracle's scope: the merge-base in branch/pr
// modes, args.base (default HEAD) in diff mode.
let BASE = HAS_BASE ? BASE_ARG : "HEAD";
const PATHS_ARG = typeof args.paths === "string" && args.paths.trim() ? args.paths.trim() : "";
const REPO_ARG = typeof args.repo === "string" && args.repo.trim() ? args.repo.trim().replace(/\/+$/, "") : "";
let REPO_ABS = "";
const MODE = typeof args.mode === "string" && args.mode.trim() ? args.mode.trim().toLowerCase() : "auto";
const FIX_FROM_ARG = typeof args.fix_from === "string" && args.fix_from.trim() ? args.fix_from.trim() : "";
const FIX_FROM = FIX_FROM_ARG !== "";
let FIX_ROUNDS =
  typeof args.fix_rounds === "number" && Number.isInteger(args.fix_rounds) && args.fix_rounds >= 0
    ? args.fix_rounds
    : 0;
// A fix_from run is always a fix run: an explicit fix_rounds: 0 is
// indistinguishable from omission, so it gets the default bounded loop
// rather than a review-only no-op.
if (FIX_FROM && FIX_ROUNDS === 0) FIX_ROUNDS = 2;
const SKILL_DIR_BAKED = "__SKILL_DIR__";
const skillDir = typeof args.skill_dir === "string" && args.skill_dir ? args.skill_dir : SKILL_DIR_BAKED;
const SEV_RANK: Record<string, number> = { high: 0, medium: 1, low: 2 };

let idSeqs: Record<string, number> = {};
function nextId(prefix: string): string {
  idSeqs[prefix] = (idSeqs[prefix] !== undefined ? idSeqs[prefix] : 0) + 1;
  return prefix + "-" + idSeqs[prefix];
}

// Declared once at the top level; report(item, "findings") feeds it.
artifact.board("findings", {
  title: "Findings",
  key: "id",
  status: "stage",
  columns: ["verified", "unconfirmed", "fixed", "unfixed", "worse", "gate"],
  cardTitle: "what",
  detail: [
    { field: "severity", label: "Severity" },
    { field: "lens", label: "Lens" },
  ],
});

// The shared review-state oracle (D-014), one world.run per fetch: its
// JSON contract is status ok/error, errors carry a stage the run maps
// to its exact stop-the-panel text.
async function oracle(label: string, subargs: string[]): Promise<any | null> {
  const r = await world.run("python3", [skillDir + "/scripts/review_orchestrator.py", ...subargs], { timeoutMs: 1800000 });
  if (r.exitCode !== 0 || !r.stdout.trim()) {
    log(label + ": oracle returned no result");
    return null;
  }
  try {
    return JSON.parse(r.stdout);
  } catch (e) {
    log(label + ": oracle stdout is not JSON: " + String(e));
    return null;
  }
}

// gate rows cross the oracle boundary as exit_code (its JSON contract);
// the orchestration below keeps its historic internal exitCode shape
function gateRows(oracleRows: any[]): GateResult[] {
  return oracleRows.map((g) => ({
    name: g.name,
    exitCode: typeof g.exit_code === "number" ? g.exit_code : 0,
    tail: g.tail,
  }));
}

// one world.run renders a whole wave of asks (NFR-003)
async function askWave(label: string, items: { kind: string; ctx: any }[]): Promise<string[] | null> {
  const d = await oracle(label, ["ask", "--kind", "batch", "--ctx", JSON.stringify({ batch: items })]);
  return d && d.status === "ok" && Array.isArray(d.asks) ? d.asks : null;
}

// Briefs sit outside the workspace, so files.read cannot reach them —
// cat through world.run is the same seam the oracle uses. A missing
// brief degrades to the inline system, never an error.
async function readBrief(file: string): Promise<string> {
  const r = await world.run("cat", [skillDir + "/agents/" + file]);
  return r.exitCode === 0 ? r.stdout.trim() : "";
}

async function withBrief(system: string, files: string[]): Promise<string> {
  const bodies = (await Promise.all(files.map(readBrief))).filter(Boolean);
  return bodies.length
    ? system + "\n\nFull checklist(s) from the panel briefs:\n\n" + bodies.join("\n\n---\n\n")
    : system;
}

// Which panel briefs each persona carries. The general reviewer covers
// all three lenses, so it reads all three lens briefs.
const BRIEF_FILES: Record<string, string[]> = {
  correctness: ["code-review-correctness.md"],
  security: ["code-review-security.md"],
  quality: ["code-review-quality.md"],
  general: [
    "code-review-correctness.md",
    "code-review-security.md",
    "code-review-quality.md",
  ],
};

let intentText = INTENT_ARG;
let scopeDirty = false;
let scoutMap: RepoMap | null = null;

// ---------------------------------------------------------------------------
// The run ------------------------------------------------------------------

let targetFiles: string[] = [];
let targetParts: string[][] = [];
let partLabels: string[] = [];
let targetCandidates = 0;
let gateTracked: TrackedFinding[] = [];
let changed: string[] = [];
let addedLines = 0;
let prMeta: PrMeta | null = null;
let branchBaseRef = "";
let branchName = "";
let commitCount = 0;
let gate: GateResult[] = [];
let GATE_LINE = "";
let modeUsed = "fix-only";
let tracked: TrackedFinding[] = [];
let allConfirmed: ConfirmedFinding[] = [];
let allDropped: DroppedFinding[] = [];
let summary: { id: string; where: string; what: string; severity: "low" | "medium" | "high"; lens: string; status: string }[] = [];
let partCoverageGaps: string[] = [];
let askCtxBase: any = {};
let fastDefault = false;
let suggestSplit = false;

// The triage editor exists in both flows: cross-lens dedup and the final
// assessment on a fresh review; fix-review triage and the closing
// assessment on a fix_from continuation. Its system rides the oracle's
// single-source definition plus the panel protocol brief.
const SYSTEMS: any = await oracle("systems-probe", ["systems"]);
if (!SYSTEMS || SYSTEMS.status !== "ok") {
  return {
    conclusion: "The panel systems could not be loaded from the oracle — rerun the workflow.",
    findings: [],
    verified: [],
    notCovered: ["the whole review — the systems fetch failed"],
  };
}
const triage = agent("Triage editor", {
  system: await withBrief(SYSTEMS.triage, ["_panel-protocol.md"]),
});

if (REPO_ARG) {
  const resolved = await world.run("git", ["-C", REPO_ARG, "rev-parse", "--show-toplevel"]);
  REPO_ABS = resolved.exitCode === 0 ? resolved.stdout.trim() : "";
  if (!REPO_ABS) {
    return {
      conclusion: "The repo arg \"" + REPO_ARG + "\" did not resolve to a git repository — pass the sub-repo's " +
        "directory relative to the working directory, or an absolute path.",
      findings: [],
      verified: [],
      notCovered: ["the review target — the repo arg did not resolve to a repository"],
    };
  }
  if (!PROJECT) {
    return {
      conclusion: "The repo arg is supported for target project today — for a change, branch or PR review, run " +
        "the workflow from inside that repository (its own workspace), where the diff and the working tree " +
        "the panel reads are the repo's own.",
      findings: [],
      verified: [],
      notCovered: ["the review target — repo with target " + TARGET + " is not supported yet"],
    };
  }
  log("review repo: " + REPO_ABS);
}

if (FIX_FROM) {
  phase("Load the findings from the previous review");
  const isInline = /^\s*[\[{]/.test(FIX_FROM_ARG);
  const loaded = await oracle("fix-from-probe", ["findings-parse", isInline ? "--text" : "--file", FIX_FROM_ARG]);
  if (!loaded) {
    return {
      conclusion: "fix_from: could not read \"" + FIX_FROM_ARG + "\" — pass the review report markdown, a findings JSON file path, or inline JSON.",
      findings: [],
      verified: [],
      notCovered: ["the fix loop — fix_from payload unusable"],
    };
  }
  if (loaded.status === "error") {
    return {
      conclusion: "fix_from: " + loaded.error + " — pass the review report markdown of a previous review, or its findings JSON.",
      findings: [],
      verified: [],
      notCovered: ["the fix loop — fix_from payload unusable"],
    };
  }
  tracked = loaded.tracked;
  allConfirmed = tracked.map((t) => t.finding);
  summary = tracked.map((t) => ({
    id: t.finding.id,
    where: t.finding.where,
    what: t.finding.what,
    severity: t.finding.severity,
    lens: t.finding.lens,
    status: t.finding.confirmation.status,
  }));
  const g = await oracle("gate-probe", ["gate", ...(REPO_ABS ? ["--repo", REPO_ABS] : []), "--base", BASE]);
  gate = g && g.status === "ok" ? gateRows(g.rows) : [{ name: "gate.sh (spec-code-review)", exitCode: 1, tail: "gate.sh produced no JSON report" }];
  GATE_LINE = g && g.status === "ok" ? g.note : "The repo's own checks could not be read";
  const preFixFailed = gate.filter((x) => x.exitCode !== 0);
  for (const x of preFixFailed) {
    const gid = nextId("gate");
    tracked.push({
      finding: {
        id: gid,
        where: x.name,
        what: "Repo check failed before the fixes: " + x.name,
        evidence: x.tail || "(no output)",
        severity: "high",
        lens: "gate",
        impact: "",
        confirmation: { status: "verified", note: "exit code nonzero before fix round 1" },
      },
      fix: "unfixed",
      fixNote: "pre-fix: check failing",
    });
    report({ id: gid, where: x.name, what: "Repo check failed before the fixes: " + x.name, severity: "high", lens: "gate", stage: "gate" }, "findings");
  }
  log("fix loop: " + tracked.length + " finding(s) carried from the previous review — pre-fix gate: " +
    (gate.length - preFixFailed.length) + "/" + gate.length + " checks passing" +
    (preFixFailed.length > 0 ? " — RED, the fixer must clear " + preFixFailed.length + " check(s)" : ""));
} else {
phase("Scope the change and run the repo's checks");

if (TARGETS.indexOf(TARGET) === -1) {
  return {
    conclusion: "Unknown target \"" + TARGET + "\" — valid targets: diff (a change against a base ref), " +
      "branch (the current branch's changes against its base), pr (a GitHub pull request), " +
      "project (the whole codebase).",
    findings: [],
    verified: [],
    notCovered: ["the review target — unknown target value \"" + TARGET + "\""],
  };
}
if (PR && !PR_ARG) {
  return {
    conclusion: "target pr needs a pr arg — the pull request number, URL or owner/repo#N.",
    findings: [],
    verified: [],
    notCovered: ["the review target — pr target without a pr arg"],
  };
}

// ONE oracle fetch resolves the whole scope + gate (NFR-003).
const scopeArgs = ["scope", "--target", TARGET, "--base", BASE_ARG || "HEAD",
  ...(PR_ARG ? ["--pr", PR_ARG] : []),
  ...(REPO_ABS ? ["--repo", REPO_ABS] : []),
  ...(PATHS_ARG ? ["--paths", PATHS_ARG] : []),
  "--include-gate"];
const sc = await oracle("scope-probe", scopeArgs);
if (!sc) {
  return {
    conclusion: "The scope probe returned no result — the review cannot see the change. Rerun the workflow.",
    findings: [],
    verified: [],
    notCovered: ["the change scope — the git scope probe failed"],
  };
}
if (sc.status === "error") {
  const stage = sc.stage || "";
  const fail = (conclusion: string, notCovered: string) => ({
    conclusion, findings: [], verified: [], notCovered: [notCovered],
  });
  if (stage === "pr-view") return fail(
    "gh pr view failed for \"" + PR_ARG + "\" — is the gh CLI installed and authenticated, and is that a valid pull request in this repo's remote?",
    "the pull request — gh pr view returned nothing usable");
  if (stage === "pr-state") return fail(
    "The review cannot see the git state (rev-parse/status probe returned nothing) — rerun the workflow.",
    "the pull request — git state probe failed");
  if (stage === "pr-dirty") return fail(
    sc.head_matches
      ? "PR #" + (sc.pr_number || "") + " is checked out but the working tree is dirty — the PR diff would fold uncommitted local work into code attributed to the PR. Commit or stash, then rerun."
      : "PR #" + (sc.pr_number || "") + " is not checked out and the working tree is dirty — the panel reads the working tree, so checking out would hide uncommitted work. Commit or stash, then rerun; on a clean tree the review checks the PR out itself.",
    "the pull request — refused to review a PR target over a dirty working tree");
  if (stage === "pr-checkout") return fail(
    "Could not check out the PR (gh pr checkout failed, or HEAD does not match the PR head afterward) — check the PR out manually and rerun.",
    "the pull request — automatic checkout failed");
  if (stage === "pr-merge-base") return fail(
    "No common ancestor between HEAD and the PR's base commit — cannot compute the PR diff.",
    "the pull request — merge-base with the base commit failed");
  if (stage === "branch-no-base") return fail(
    "Could not detect a base branch for the branch review — pass base explicitly (e.g. base: \"main\").",
    "the branch review — no base branch resolved");
  if (stage === "branch-merge-base") return fail(
    "No common ancestor between HEAD and " + (sc.base || "") + " — cannot compute the branch diff.",
    "the branch review — merge-base with " + (sc.base || "") + " failed");
  if (stage === "ls-files") return fail(
    "The target probe returned no result — the review cannot see the project's files. Rerun the workflow.",
    "the project file listing — the target probe failed");
  // diff with an unresolvable base behaves as an empty diff, exactly as
  // the inline implementation did
  return fail("git diff " + (sc.base || BASE) + " has no changes — nothing to review.",
    "the change scope — the review target resolved to an empty diff");
}

if (PR) {
  prMeta = sc.pr;
  if (!intentText && prMeta.body) intentText = prMeta.body;
  BASE = sc.merge_base;
  if (sc.previous_head) log("checked out PR #" + prMeta.number + " (previous HEAD " + sc.previous_head.slice(0, 12) + ") — switch back when done reviewing");
  log("review target: PR #" + prMeta.number + " " + prMeta.title + " (" + prMeta.state + ", by " + prMeta.author + ", base " + prMeta.baseRefName + ") — diff vs merge-base " + BASE.slice(0, 12));
} else if (BRANCH_MODE) {
  branchName = sc.branch_name || "";
  branchBaseRef = sc.base;
  BASE = sc.merge_base;
  commitCount = sc.commit_count;
  log("review target: branch " + branchName + " vs " + branchBaseRef + " — merge-base " + BASE.slice(0, 12) + ", " + commitCount + " commit(s)");
}

if (PROJECT) {
  targetFiles = sc.files;
  targetCandidates = sc.candidates;
  targetParts = sc.parts;
  partLabels = sc.part_labels;
  log("review target: project" + (REPO_ABS ? " (repo: " + REPO_ABS + ")" : "") + " — all " + targetCandidates +
    " tracked source files" + (PATHS_ARG ? " (paths filter: " + PATHS_ARG + ")" : "") +
    ", read as " + targetParts.length + " reviewer part(s) per lens");
  if (targetFiles.length === 0) {
    return {
      conclusion: "No tracked source files matched the project target" +
        (PATHS_ARG ? " (paths filter: " + PATHS_ARG + ")" : "") + " — nothing to review.",
      findings: [],
      verified: ["project target: no tracked source files matched"],
      notCovered: [],
    };
  }
} else {
  changed = sc.files;
  addedLines = sc.added;
  scopeDirty = !sc.clean;
  log("change under review: " +
    (PR ? "PR #" + (prMeta as PrMeta).number + " (diff vs merge-base " + BASE.slice(0, 12) + ")"
      : BRANCH_MODE ? "branch " + branchName + " (diff vs merge-base " + BASE.slice(0, 12) + ")"
      : "git diff " + BASE) +
    " — " + changed.length + " files, ~" + addedLines + " added lines" +
    (sc.clean ? " (clean tree)" : " (uncommitted work present)") +
    (sc.suggest_split ? " — large change: the report will recommend splitting" : ""));
  if (changed.length === 0) {
    const nothing = PR
      ? "PR #" + (prMeta as PrMeta).number + " has no changes against " + (prMeta as PrMeta).baseRefName + " — nothing to review."
      : BRANCH_MODE
        ? "Branch " + branchName + " has no changes against " + branchBaseRef + " — nothing to review."
        : "git diff " + BASE + " has no changes — nothing to review.";
    return {
      conclusion: nothing,
      findings: [],
      verified: ["change scope: the review target resolved to an empty diff"],
      notCovered: [],
    };
  }
}
fastDefault = sc.fast_mode_default;
suggestSplit = sc.suggest_split;

gate = gateRows(sc.gate.rows);
GATE_LINE = sc.gate.note;
const gateFailed = gate.filter((x) => x.exitCode !== 0);
log("repo checks: " + (gate.length - gateFailed.length) + "/" + gate.length + " detected and run" +
  (gateFailed.length > 0 ? " — " + gateFailed.length + " FAILING" : ""));

if (gateFailed.length > 0) {
  for (const x of gateFailed) {
    const gid = nextId("gate");
    gateTracked.push({
      finding: {
        id: gid,
        where: x.name,
        what: "Repo check failed before the review: " + x.name,
        evidence: x.tail || "(no output)",
        severity: "high",
        lens: "gate",
        impact: "",
        confirmation: { status: "verified", note: "exit code nonzero before the review started" },
      },
      fix: "pending",
      fixNote: "not yet attempted",
    });
    report({ id: gid, where: x.name, what: "Repo check failed before the review: " + x.name, severity: "high", lens: "gate", stage: "gate" }, "findings");
  }
  if (!PROJECT) {
    const gateMd = [
      "# Code review — checks failed, review stopped", "",
      PR ? "PR #" + (prMeta as PrMeta).number + " (" + changed.length + " files) failed the repo's own checks, so the "
        : BRANCH_MODE ? "Branch " + branchName + " (" + changed.length + " files) failed the repo's own checks, so the "
        : "The change (`git diff " + BASE + "` — " + changed.length + " files) failed the repo's own checks, so the ",
      "specialist reviewers were not spent on it. Fix these first, then rerun the review.", "",
      "## Failed checks", "",
      ...gate.map((x) => "- " + (x.exitCode === 0 ? "pass" : "**FAIL**") + " — " + x.name +
        (x.exitCode === 0 ? "" : "\n\n  ```\n  " + x.tail + "\n  ```")),
    ].join("\n");
    return {
      conclusion:
        (PR ? "PR #" + (prMeta as PrMeta).number : BRANCH_MODE ? "Branch " + branchName : "The change") +
        " failed " + gateFailed.length + " of " + gate.length +
        " detected repo checks (" + gateFailed.map((x) => x.name).join("; ") + "). Specialist review was skipped — " +
        "these are mechanical fixes; rerun the review after they pass.",
      findings: gateFailed.map((x) => ({
        id: nextId("gate"), where: x.name, what: "Repo check failed: " + x.name,
        evidence: x.tail || "(no output)", status: "verified", severity: "high" as const,
        lens: "gate", impact: "", fixStatus: "pending",
      })),
      verified: ["the mechanical gate ran the repo's own detected checks — " + gateFailed.length + " failed"],
      notCovered: ["specialist review of the diff — skipped because the mechanical gate failed"],
      markdown: gateMd,
    };
  }
  log("project audit continues past the red gate — " + gateFailed.length + " failing check(s) recorded as gate findings");
}

// ---------------------------------------------------------------------------
phase("Preflight the codebase and modules the target touches");

const scout = agent("Preflight scout", {
  system: await withBrief(SYSTEMS.scout, ["code-review-scout.md"]),
});
const scoutAsks = await askWave("scout-ask-probe", [
  { kind: "scout", ctx: { base: BASE, project: PROJECT, files: PROJECT ? targetFiles : changed, repo_abs: REPO_ABS || null } },
]);
try {
  scoutMap = scoutAsks ? await scout.ask<RepoMap>(scoutAsks[0]) : null;
} catch {
  scoutMap = null;
}
if (scoutMap && (!Array.isArray(scoutMap.modules) || !Array.isArray(scoutMap.conventions) || !Array.isArray(scoutMap.riskAreas))) {
  scoutMap = null;
}
log(scoutMap
  ? "preflight scout: " + scoutMap.modules.length + " module(s), " + scoutMap.conventions.length +
    " convention(s), " + scoutMap.riskAreas.length + " risk area(s)"
  : "preflight scout returned no map — the reviewers start from the raw target");

// ---------------------------------------------------------------------------
phase("Review the change through separate lenses and confirm every finding");

modeUsed = MODE === "fast" || MODE === "full" ? MODE : (fastDefault ? "fast" : "full");
const panel: LensDef[] = modeUsed === "fast" ? [SYSTEMS.general] : SYSTEMS.lenses;
log("review mode: " + modeUsed + (modeUsed === "fast" ? " (small diff, one general reviewer)" : " (three specialists)"));

askCtxBase = { base: BASE, intent: intentText, scout_map: scoutMap, repo_abs: REPO_ABS || null, project: PROJECT };
// ONE ask wave for the whole panel (per part in project mode)
const reviewItems: { kind: string; ctx: any; label: string; lens: LensDef }[] = [];
for (const lensDef of panel) {
  if (PROJECT) {
    targetParts.forEach((partFiles, pi) => {
      reviewItems.push({
        kind: "review-project",
        ctx: { ...askCtxBase, lens: lensDef, files: partFiles, candidates: targetCandidates, part: pi + 1, parts: targetParts.length, gate_line: GATE_LINE },
        label: lensDef.name + " · part " + (pi + 1) + "/" + targetParts.length + " · " + (partLabels[pi] || "part"),
        lens: lensDef,
      });
    });
  } else {
    reviewItems.push({
      kind: "review",
      ctx: { ...askCtxBase, lens: lensDef, files_n: changed.length, lines: addedLines, over_cap: false, gate_line: GATE_LINE },
      label: lensDef.name,
      lens: lensDef,
    });
  }
}
const reviewAsks = await askWave("review-asks-probe", reviewItems);

const perLens = await Promise.all(
  panel.map(async (lensDef, li) => {
    const system = await withBrief(lensDef.system, BRIEF_FILES[lensDef.label] ?? []);
    let rawFindings: Finding[] = [];
    if (PROJECT) {
      const myItems = reviewItems.filter((it) => it.lens === lensDef);
      const asks = reviewAsks ? myItems.map((it, i) => reviewAsks[reviewItems.indexOf(it)]) : [];
      const partReviews = await Promise.all(
        myItems.map((it, i) => agent(it.label, { system }).ask<LensReview>(asks[i])),
      );
      const failedParts = partReviews.filter((r) => !r || !Array.isArray(r.findings)).length;
      rawFindings = partReviews.flatMap((r) => (r && Array.isArray(r.findings) ? r.findings : []));
      if (failedParts > 0) {
        partCoverageGaps.push(
          "the " + lensDef.label + " lens: " + failedParts + " of " + targetParts.length +
          " reviewer part(s) returned no result — their files were not reviewed",
        );
      }
      log(lensDef.name + ": " + (targetParts.length - failedParts) + "/" + targetParts.length +
        " part(s) read — " + rawFindings.length + " finding(s)");
    } else {
      const ask = reviewAsks ? reviewAsks[reviewItems.findIndex((it) => it.lens === lensDef)] : "";
      const review = ask ? await agent(lensDef.name, { system }).ask<LensReview>(ask) : { findings: [] as Finding[] };
      rawFindings = review.findings;
      log(lensDef.name + ": " + rawFindings.length + " finding(s)");
    }
    if (rawFindings.length === 0) {
      return { lens: lensDef.label, confirmed: [] as ConfirmedFinding[], dropped: [] as DroppedFinding[], raw: [] as Finding[] };
    }
    return { lens: lensDef.label, confirmed: [] as ConfirmedFinding[], dropped: [] as DroppedFinding[], raw: rawFindings };
  }),
);

// ONE triage ask wave for every lens that found something, then ONE
// confirm ask wave per lens's kept findings (batched by lens to match
// the typed per-lens agent fan-out)
for (const r of perLens) {
  if (!(r.raw && r.raw.length > 0)) continue;
  const lensDef = panel.find((l) => l.label === r.lens)!;
  const tAsks = await askWave("triage-asks-probe", [
    { kind: PROJECT ? "triage-project" : "triage", ctx: { ...askCtxBase, lens_label: r.lens, findings: r.raw } },
  ]);
  const triaged = tAsks ? await triage.ask<TriageVerdict>(tAsks[0]) : { kept: r.raw, dropped: [] as DroppedFinding[] };
  const cAsks = triaged.kept.length ? await askWave("confirm-asks-probe",
    triaged.kept.map((f) => ({ kind: PROJECT ? "confirm-project" : "confirm", ctx: { ...askCtxBase, finding: f } }))) : [];
  const confirmations = await Promise.all(
    triaged.kept.map((f, i) =>
      agent("Confirm " + r.lens + " finding " + (i + 1)).ask<Confirmation>(cAsks ? cAsks[i] : ""),
    ),
  );
  r.confirmed = triaged.kept.map((f, i) => ({ ...f, id: r.lens + "-" + (i + 1), lens: r.lens, confirmation: confirmations[i] }));
  r.dropped = triaged.dropped;
  for (const c of r.confirmed) {
    report({
      id: c.id, where: c.where, what: c.what, severity: c.severity, lens: c.lens,
      status: c.confirmation.status, stage: c.confirmation.status,
    }, "findings");
  }
  r.raw = [];
}

allConfirmed = perLens.flatMap((r) => r.confirmed);
allDropped = perLens.flatMap((r) => r.dropped);
allConfirmed.sort((a, b) =>
  (SEV_RANK[a.severity] !== undefined ? SEV_RANK[a.severity] : 3) -
  (SEV_RANK[b.severity] !== undefined ? SEV_RANK[b.severity] : 3));
summary = gateTracked.map((t) => ({
  id: t.finding.id, where: t.finding.where, what: t.finding.what,
  severity: t.finding.severity, lens: t.finding.lens, status: t.finding.confirmation.status,
})).concat(allConfirmed.map((c) => ({
  id: c.id, where: c.where, what: c.what, severity: c.severity, lens: c.lens, status: c.confirmation.status,
})));

tracked = gateTracked.concat(allConfirmed.map((f) => ({ finding: f, fix: "pending" as const, fixNote: "not yet attempted" })));
}

let roundsUsed = 0;
let finalGate = gate;
let gateGreen = gate.every((x) => x.exitCode === 0);
const fixerNotes: string[] = [];
const allChangedPaths: string[] = [];

if (FIX_ROUNDS > 0 && tracked.length > 0) {
  phase("Fix the confirmed findings and verify every fix");
  const fixer = agent("Author and fixer", {
    system: await withBrief(SYSTEMS.fixer, ["code-review-fixer.md", "_panel-protocol.md"]),
  });
  let gateFeedback = "";

  for (let round = 1; round <= FIX_ROUNDS; round++) {
    const unresolved = tracked.filter((t) => t.fix !== "fixed");
    if (unresolved.length === 0) break;
    const fAsks = await askWave("fixer-ask-probe", [{
      kind: "fixer",
      ctx: { base: BASE, project: PROJECT, intent: intentText, repo_abs: REPO_ABS || null, round, unresolved, gate_feedback: gateFeedback || null },
    }]);
    const outcome = await fixer.ask<FixOutcome>(fAsks ? fAsks[0] : "");
    roundsUsed = round;
    for (const n of outcome.notes) fixerNotes.push("round " + round + ": " + n);
    for (const p of outcome.changedPaths) if (allChangedPaths.indexOf(p) === -1) allChangedPaths.push(p);
    log("fix round " + round + ": " + outcome.addressed.length + " addressed · " + outcome.skipped.length +
      " skipped · " + outcome.changedPaths.length + " path(s) changed");

    const g = await oracle("gate-probe", ["gate", ...(REPO_ABS ? ["--repo", REPO_ABS] : []), ...(PROJECT ? ["--tree"] : ["--base", BASE])]);
    const roundGate = g && g.status === "ok" ? gateRows(g.rows) : [{ name: "gate.sh (spec-code-review)", exitCode: 1, tail: "gate.sh produced no JSON report" }];
    finalGate = roundGate;
    const gateBad = roundGate.filter((x) => x.exitCode !== 0);
    gateGreen = gateBad.length === 0;
    gateFeedback = gateBad.map((x) => x.name + ":\n" + x.tail).join("\n\n");
    log("checks after round " + round + ": " + (roundGate.length - gateBad.length) + "/" + roundGate.length + " passed");

    for (let i = tracked.length - 1; i >= 0; i--) {
      if (tracked[i].finding.lens === "gate") tracked.splice(i, 1);
    }
    for (const x of gateBad) {
      const gid = nextId("gate");
      tracked.push({
        finding: {
          id: gid, where: x.name, what: "Repo check failed after the fixes: " + x.name,
          evidence: x.tail || "(no output)", severity: "high", lens: "gate",
          confirmation: { status: "verified", note: "exit code nonzero after fix round " + round },
        },
        fix: "unfixed", fixNote: "round " + round + ": check failing",
      });
      report({ id: gid, where: x.name, what: "Repo check failed after the fixes: " + x.name, severity: "high", lens: "gate", stage: "gate", fix: "unfixed", round }, "findings");
    }

    const verifiable = unresolved.filter((t) => t.finding.lens !== "gate");
    const vAsks = verifiable.length ? await askWave("verify-asks-probe",
      verifiable.map((t) => ({ kind: "verify", ctx: { base: BASE, project: PROJECT, repo_abs: REPO_ABS || null, tracked: t, notes: outcome.notes.join(" | ") } }))) : [];
    const verifications = await Promise.all(
      verifiable.map((t, i) => agent("Verify round " + round + " fix " + (i + 1)).ask<Verification>(vAsks ? vAsks[i] : "")),
    );
    for (let i = 0; i < verifiable.length; i++) {
      const v = verifications[i];
      const t = verifiable[i];
      t.fix = v.status;
      t.fixNote = "round " + round + ": " + v.note;
      report({ id: t.finding.id, where: t.finding.where, what: t.finding.what, severity: t.finding.severity, lens: t.finding.lens, fix: v.status, note: v.note, round, stage: v.status }, "findings");
    }

    if (outcome.changedPaths.length > 0) {
      const frAsks = await askWave("fix-review-ask-probe", [{ kind: "fix-review", ctx: { base: BASE, repo_abs: REPO_ABS || null, paths: outcome.changedPaths, gate_green: gateGreen } }]);
      const fixReview = await agent("Fix reviewer round " + round, { system: SYSTEMS.fix_review }).ask<LensReview>(frAsks ? frAsks[0] : "");
      if (fixReview.findings.length > 0) {
        const ftAsks = await askWave("fix-review-triage-ask-probe", [{ kind: "triage", ctx: { base: BASE, intent: intentText, lens_label: "fix-review", findings: fixReview.findings } }]);
        const triagedFix = await triage.ask<TriageVerdict>(ftAsks ? ftAsks[0] : "");
        const fcAsks = await askWave("fix-review-confirm-asks-probe",
          triagedFix.kept.map((f) => ({ kind: "confirm", ctx: { base: BASE, finding: f } })));
        const fixConfs = await Promise.all(
          triagedFix.kept.map((f, i) => agent("Confirm fix-review finding " + round + "-" + (i + 1)).ask<Confirmation>(fcAsks ? fcAsks[i] : "")),
        );
        for (let i = 0; i < triagedFix.kept.length; i++) {
          const c: ConfirmedFinding = { ...triagedFix.kept[i], id: nextId("fix-review"), lens: "fix-review", confirmation: fixConfs[i] };
          tracked.push({ finding: c, fix: "pending", fixNote: "new from fix review, round " + round });
          report({ id: c.id, where: c.where, what: c.what, severity: c.severity, lens: "fix-review", status: c.confirmation.status, stage: c.confirmation.status, round }, "findings");
        }
      }
    }

    if (tracked.every((t) => t.fix === "fixed")) break;
  }
}

// ---------------------------------------------------------------------------
phase("Synthesize the final review report");

let finalAdded = addedLines;
let finalChangedN = changed.length;
if (PROJECT) {
  finalChangedN = targetFiles.length;
  finalAdded = 0;
} else if (roundsUsed > 0) {
  const again = await oracle("rescope-probe", ["scope", "--target", "diff", "--base", BASE, ...(REPO_ABS ? ["--repo", REPO_ABS] : [])]);
  if (again && again.status === "ok") {
    finalAdded = again.added;
    finalChangedN = again.files.length;
  }
}

const readerTracked = tracked.filter((t) => t.finding.lens !== "gate");
const nVerified = readerTracked.filter((t) => t.finding.confirmation.status === "verified").length;
const nUnconfirmed = readerTracked.length - nVerified;
const nHigh = tracked.filter((t) => t.finding.severity === "high").length;
const nFixed = tracked.filter((t) => t.fix === "fixed").length;

let assessmentOut: Assessment;
let recommendation: "merge" | "fix-first" | "human" | "none";
if (roundsUsed > 0) {
  const lfAsks = await askWave("loop-final-ask-probe", [{
    kind: "loop-final",
    ctx: { base: BASE, project: PROJECT, scout_map: scoutMap, tracked, rounds_used: roundsUsed, gate_green: gateGreen, changed_paths: allChangedPaths },
  }]);
  const fa = await triage.ask<FinalAssessment>(lfAsks ? lfAsks[0] : "");
  assessmentOut = fa;
  recommendation = fa.recommendation;
} else {
  const fAsks = await askWave("final-ask-probe", [{
    kind: PROJECT ? "final-project" : "final",
    ctx: { ...askCtxBase, summary, gate_line: GATE_LINE, files: targetFiles },
  }]);
  assessmentOut = await triage.ask<Assessment>(fAsks ? fAsks[0] : "");
  recommendation = "none";
}
const assessment = assessmentOut;

// The report body renders in the oracle (D-014); the run keeps only the
// title/mode lines (PR metadata lives here) and the result envelope.
const title = FIX_FROM
  ? "# Code review — fix loop (" + tracked.length + " finding(s) carried from the previous review)"
  : PROJECT
    ? "# Code review — project (" + finalChangedN + " files)"
    : PR
      ? "# Code review — PR #" + (prMeta as PrMeta).number + ": " + (prMeta as PrMeta).title.replace(/[\\`*_[\]()!<>]/g, (ch) => "\\" + ch) +
        " (" + finalChangedN + " files, ~" + finalAdded + " added lines)"
      : BRANCH_MODE
        ? "# Code review — branch " + branchName + " vs " + branchBaseRef +
          " (" + finalChangedN + " files, ~" + finalAdded + " added lines)"
        : "# Code review — " + BASE + " (" + finalChangedN + " files, ~" + finalAdded + " added lines)";
const modeLine = FIX_FROM
  ? "Mode: fix-only — the review stages were skipped; findings carried from the previous review's report. fix_rounds: " + FIX_ROUNDS + "."
  : "Mode: " + modeUsed + (modeUsed === "fast" ? " — one general reviewer" : " — correctness, security, quality") +
    " · every kept non-gate finding confirmed by an independent reader." +
    (PROJECT ? " Target: the project's code as it stands — \"merge\" reads as ready-as-is." : "") +
    (PR ? " Target: pull request #" + (prMeta as PrMeta).number + " by " + (prMeta as PrMeta).author + " → " + (prMeta as PrMeta).baseRefName +
      ((prMeta as PrMeta).url ? " — " + (prMeta as PrMeta).url : "") + " — \"merge\" reads as the PR is ready." : "") +
    (BRANCH_MODE ? " Target: the branch's changes vs " + branchBaseRef + " at the merge-base — \"merge\" reads as the branch is ready to merge." +
      (scopeDirty ? " Uncommitted work present in the working tree is included in the reviewed diff." : "") : "") +
    ((!FIX_FROM && !PROJECT && suggestSplit) ? " Large change: ~" + finalAdded + " added lines across " + finalChangedN +
      " files — consider splitting into smaller, independently reviewable chunks; reviewers read whole targets, and coverage thins as size grows." : "") +
    (roundsUsed > 0 ? " Fix loop: " + roundsUsed + " round(s) — " + nFixed + "/" + tracked.length + " findings fixed, checks " +
      (gateGreen ? "green" : "RED") + ". Fixes sit uncommitted in the working tree." : "");

const rep = await oracle("report-probe", ["report", "--kind", roundsUsed > 0 ? "fix" : "review", "--data", JSON.stringify({
  title,
  mode_line: modeLine,
  verdict_line: "## Verdict — " + assessment.risk + " risk" + (roundsUsed > 0 ? " · recommendation: **" + recommendation + "**" : ""),
  tracked,
  gate_rows: finalGate,
  gate_green: gateGreen,
  assessment,
  dropped: allDropped,
  fixer_notes: fixerNotes,
  rounds_used: roundsUsed,
  checked: [
    ...(PROJECT ? ["- Project review target: all " + targetCandidates + " tracked source files of " +
      (REPO_ABS ? "the sub-repo at " + REPO_ABS : "the repository") + ", covered by " + targetParts.length +
      " reviewer part(s) per lens (contiguous, directory-coherent, byte-balanced runs of the path-sorted file list); lockfiles, generated and vendored files are excluded by type" +
      (PATHS_ARG ? "; paths filter: " + PATHS_ARG : "") + "."] : []),
    ...(finalGate.length > 0
      ? gateGreen
        ? ["- The repo's own detected checks all ran and passed: " + finalGate.map((x) => x.name).join("; ") + "."]
        : ["- The repo's own detected checks: " + finalGate.filter((x) => x.exitCode === 0).length + " of " + finalGate.length +
            " passed — failing: " + finalGate.filter((x) => x.exitCode !== 0).map((x) => x.name).join("; ") + " (see FAIL rows above)."]
      : ["- The gate detected no checks in this repo — the review ran without a mechanical floor."]),
    ...(!FIX_FROM && scoutMap
      ? ["- Preflight scout mapped the ground before the reviewers started: " + scoutMap.modules.length + " module(s), " +
          scoutMap.conventions.length + " convention(s), " + scoutMap.riskAreas.length + " risk area(s)."]
      : []),
    "- Each non-gate finding was re-checked by an independent reader that did not write it (" + nVerified + " verified, " + nUnconfirmed + " unconfirmed).",
  ],
  fix_checked: roundsUsed > 0 ? [
    "- After each fix round the gate re-ran" + (gateGreen ? " and finished green" : " — still failing") +
    ", every attempted fix was verified by an independent reader, and a fresh-eyes reviewer scanned the fix diff.",
    "- The fixes are uncommitted in the working tree — inspect with `git diff` and commit when satisfied.",
  ] : [],
})]);
const reportedFindings: ReportedFinding[] = rep && rep.status === "ok" ? rep.reported_findings : [];

return {
  conclusion:
    roundsUsed > 0
      ? assessment.verdict + " — recommendation: " + recommendation + ". " + nFixed + "/" + tracked.length + " findings fixed over " + roundsUsed + " round(s); checks " + (gateGreen ? "green" : "RED") + ". The fixes sit uncommitted in the working tree."
      : assessment.verdict + " — " + tracked.length + " confirmed finding(s), " + nHigh + " high, " + nUnconfirmed + " unconfirmed; overall risk " + assessment.risk + "." +
        (allDropped.length ? " (" + allDropped.length + " dropped at triage as duplicates or out of scope.)" : ""),
  findings: reportedFindings,
  verified: [
    ...(FIX_FROM ? ["fix loop continuation — findings carried from the previous review's report; review stages skipped"] : []),
    ...(PROJECT ? ["review target: " + (REPO_ABS ? "the sub-repo at " + REPO_ABS + " — its" : "the project's") +
      " tracked source files — all " + targetCandidates + " matched, read as " + targetParts.length + " reviewer part(s) per lens"] : []),
    ...(!FIX_FROM && PR ? ["review target: PR #" + (prMeta as PrMeta).number + " (" + (prMeta as PrMeta).state + ") — the merge-base diff against " + (prMeta as PrMeta).baseRefName] : []),
    ...(!FIX_FROM && BRANCH_MODE ? ["review target: branch " + branchName + " vs " + branchBaseRef + " — the merge-base diff (" + commitCount + " commit(s))"] : []),
    ...(finalGate.length > 0
      ? gateGreen
        ? ["the mechanical gate ran the repo's own detected checks (all passed): " + finalGate.map((x) => x.name).join("; ")]
        : ["the mechanical gate ran the repo's own detected checks — " + finalGate.filter((x) => x.exitCode !== 0).length + " of " + finalGate.length + " FAILED: " + finalGate.filter((x) => x.exitCode !== 0).map((x) => x.name).join("; ")]
      : []),
    ...(!FIX_FROM && scoutMap ? ["preflight scout mapped the codebase and modules before the panel started (" + scoutMap.modules.length + " module(s))"] : []),
    "every reported non-gate finding was re-checked by an independent reader that did not write it",
    ...(roundsUsed > 0
      ? [
          "every attempted fix was verified by an independent reader, and a fresh-eyes reviewer scanned the fix diff",
          "the gate re-ran after the final fix round — " + (gateGreen ? "all green" : "still failing"),
        ]
      : []),
  ],
  notCovered: [
    ...(FIX_FROM ? ["the review stages were skipped (fix_from) — coverage inherits the previous report's notCovered; anything it missed stays missed"] : []),
    ...(!FIX_FROM && !scoutMap ? ["preflight scout returned no map — the review ran without the codebase and module context step"] : []),
    ...partCoverageGaps,
    ...(finalGate.length === 0 ? ["no repo checks were detected by the gate — this review ran without a mechanical floor; ask the repo for its documented check command"] : []),
    ...assessment.testGaps.map((t) => "test gap: " + t),
    ...assessment.residualRisks.map((r) => "residual: " + r),
    "runtime behavior beyond the repo's test suites was not exercised — this was a static review",
    ...(roundsUsed > 0 ? ["the fixes are uncommitted — the commit decision and message remain yours"] : []),
  ],
};
