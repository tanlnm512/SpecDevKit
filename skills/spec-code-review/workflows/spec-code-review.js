export const meta = {
  name: "spec-code-review",
  description:
    "Three-stage code review in any repository, with an optional fix " +
    "loop, over a change, a pull request, a branch's recent changes, or " +
    "the whole project. Stage 1 runs the repo's own detected checks as " +
    "the mechanical gate (the skill's scripts/gate.sh). Stage 2 reviews " +
    "the target through separate lenses — correctness, security, quality " +
    "& tests (one general reviewer in fast mode) — triaged by one " +
    "editor, with independent confirmation of every kept finding. Stage " +
    "3 synthesizes a report with risk class, test gaps and residual " +
    "risks. With fix_rounds > 0 an iterative loop follows: an author " +
    "agent fixes the confirmed findings, every fix is independently " +
    "verified, the gate re-runs, a fresh-eyes reviewer scans the fix " +
    "diff, and the run ends with a merge / fix-first / human " +
    "recommendation. Use when the user asks to review a change — a pull " +
    "request, a branch's recent changes, or the whole project — or to " +
    "review and fix any of them, in any git repository.",
}

// ---------------------------------------------------------------------------
// spec-code-review.js — the Claude Code dialect (thin oracle-relay form,
// D-014): all shared review state — target resolution, the gate, sharding,
// finding IDs, findings parsing, report assembly, panel systems and ask
// text — lives in scripts/review_orchestrator.py, fetched through ONE probe
// agent per phase (NFR-003). This file keeps only what is runtime-native:
// agent coordination, schemas, and the run's report bookkeeping.
//
// This script has NO filesystem/shell access of its own (runtime rule) —
// the probe agents below are the only seam that runs the oracle (and so
// gate.sh and git), and every reviewer/triage/confirm/fix agent works the
// repo with its own tools.
//
// Dialect divergences from the zcode master, each forced by the one-shot
// agent model — behavior is otherwise identical:
// - system prompts ride at the head of each one-shot ask;
// - cross-lens dedup runs as one explicit merge pass (per-lens triage
//   plus a cross-lens pass before confirmation);
// - the fixer is one-shot per round, so every round's ask embeds the full
//   finding detail;
// - the report returns as the run result's `markdown` field.
// ---------------------------------------------------------------------------

const TARGETS = ["diff", "branch", "pr", "project"];
const TARGET = typeof args !== "undefined" && args && typeof args.target === "string" && args.target.trim() ? args.target.trim().toLowerCase() : "diff";
const PROJECT = TARGET === "project";
const PR = TARGET === "pr";
const BRANCH_MODE = TARGET === "branch";
const PR_ARG = typeof args !== "undefined" && args && typeof args.pr === "string" && args.pr.trim() ? args.pr.trim() : "";
const INTENT_ARG = typeof args !== "undefined" && args && typeof args.intent === "string" && args.intent.trim() ? args.intent.trim() : "";
const HAS_BASE = typeof args !== "undefined" && args && typeof args.base === "string" && args.base.trim() ? true : false;
const BASE_ARG = HAS_BASE ? String(args.base).trim() : "";
// BASE starts at the diff default and is resolved by the oracle's scope:
// the merge-base in branch/pr modes, args.base (default HEAD) in diff
// mode — every ask and the gate then work unchanged.
let BASE = HAS_BASE ? BASE_ARG : "HEAD";
let intentText = INTENT_ARG;
let scopeDirty = false;
let scoutMap = null;
const PATHS_ARG = typeof args !== "undefined" && args && typeof args.paths === "string" && args.paths.trim() ? args.paths.trim() : "";
const REPO_ARG = typeof args !== "undefined" && args && typeof args.repo === "string" && args.repo.trim() ? args.repo.trim() : "";
const MODE_ARG = typeof args !== "undefined" && args && typeof args.mode === "string" && args.mode.trim() ? args.mode.trim().toLowerCase() : "auto";
const FIX_FROM_ARG = typeof args !== "undefined" && args && typeof args.fix_from === "string" && args.fix_from.trim() ? args.fix_from.trim() : "";
const FIX_FROM = FIX_FROM_ARG !== "";
let FIX_ROUNDS = typeof args !== "undefined" && args && typeof args.fix_rounds === "number" && Number.isInteger(args.fix_rounds) && args.fix_rounds >= 0 ? args.fix_rounds : 0;
// A fix_from run is always a fix run: an explicit fix_rounds: 0 is
// indistinguishable from omission, so it gets the default bounded loop.
if (FIX_FROM && FIX_ROUNDS === 0) FIX_ROUNDS = 2;
const SKILL_DIR_BAKED = "__SKILL_DIR__";
const skillDir = typeof args !== "undefined" && args && typeof args.skill_dir === "string" && args.skill_dir ? args.skill_dir : SKILL_DIR_BAKED;
const SEV_RANK = { high: 0, medium: 1, low: 2 };

// --- schemas: every agent result is validated, never trusted raw -----------

const PROBE_SCHEMA = {
  type: "object",
  properties: { stdout: { type: "string" } },
  required: ["stdout"],
  additionalProperties: false,
};

const FINDING_ITEM = {
  type: "object",
  properties: {
    where: { type: "string" },
    what: { type: "string" },
    evidence: { type: "string" },
    severity: { type: "string", enum: ["low", "medium", "high"] },
    impact: { type: "string" },
  },
  required: ["where", "what", "evidence", "severity"],
  additionalProperties: false,
};

const LENS_SCHEMA = {
  type: "object",
  properties: { findings: { type: "array", items: FINDING_ITEM } },
  required: ["findings"],
  additionalProperties: false,
};

const SCOUT_SCHEMA = {
  type: "object",
  properties: {
    modules: {
      type: "array",
      items: {
        type: "object",
        properties: { name: { type: "string" }, path: { type: "string" }, role: { type: "string" } },
        required: ["name", "path", "role"],
        additionalProperties: false,
      },
    },
    conventions: { type: "array", items: { type: "string" } },
    riskAreas: { type: "array", items: { type: "string" } },
  },
  required: ["modules", "conventions", "riskAreas"],
  additionalProperties: false,
};

const DROPPED_ITEM = {
  type: "object",
  properties: { where: { type: "string" }, what: { type: "string" }, reason: { type: "string" } },
  required: ["where", "what", "reason"],
  additionalProperties: false,
};

const TRIAGE_SCHEMA = {
  type: "object",
  properties: { kept: { type: "array", items: FINDING_ITEM }, dropped: { type: "array", items: DROPPED_ITEM } },
  required: ["kept", "dropped"],
  additionalProperties: false,
};

const TAGGED_FINDING_ITEM = {
  type: "object",
  properties: {
    where: { type: "string" },
    what: { type: "string" },
    evidence: { type: "string" },
    severity: { type: "string", enum: ["low", "medium", "high"] },
    lens: { type: "string" },
    impact: { type: "string" },
  },
  required: ["where", "what", "evidence", "severity", "lens"],
  additionalProperties: false,
};

const CROSS_TRIAGE_SCHEMA = {
  type: "object",
  properties: { kept: { type: "array", items: TAGGED_FINDING_ITEM }, dropped: { type: "array", items: DROPPED_ITEM } },
  required: ["kept", "dropped"],
  additionalProperties: false,
};

const CONFIRM_SCHEMA = {
  type: "object",
  properties: { status: { type: "string", enum: ["verified", "unconfirmed"] }, note: { type: "string" } },
  required: ["status", "note"],
  additionalProperties: false,
};

const ASSESSMENT_FIELDS = {
  risk: { type: "string", enum: ["low", "medium", "high"] },
  testGaps: { type: "array", items: { type: "string" } },
  residualRisks: { type: "array", items: { type: "string" } },
  verdict: { type: "string" },
};

const ASSESS_SCHEMA = {
  type: "object",
  properties: ASSESSMENT_FIELDS,
  required: ["risk", "testGaps", "residualRisks", "verdict"],
  additionalProperties: false,
};

const LOOP_ASSESS_SCHEMA = {
  type: "object",
  properties: Object.assign({}, ASSESSMENT_FIELDS, {
    recommendation: { type: "string", enum: ["merge", "fix-first", "human"] },
  }),
  required: ["risk", "testGaps", "residualRisks", "verdict", "recommendation"],
  additionalProperties: false,
};

const FIX_SCHEMA = {
  type: "object",
  properties: {
    addressed: { type: "array", items: { type: "string" } },
    skipped: {
      type: "array",
      items: {
        type: "object",
        properties: { id: { type: "string" }, why: { type: "string" } },
        required: ["id", "why"],
        additionalProperties: false,
      },
    },
    changedPaths: { type: "array", items: { type: "string" } },
    notes: { type: "array", items: { type: "string" } },
  },
  required: ["addressed", "skipped", "changedPaths", "notes"],
  additionalProperties: false,
};

const VERIFY_SCHEMA = {
  type: "object",
  properties: { status: { type: "string", enum: ["fixed", "unfixed", "worse"] }, note: { type: "string" } },
  required: ["status", "note"],
  additionalProperties: false,
};

// --- helpers ----------------------------------------------------------------

// one-shot agents have no system slot — the panel role rides at the head
function withSystem(systemText, task) {
  return systemText + "\n\n" + task;
}

// single-quote a shell word for the probe command lines (refs, paths and
// JSON payloads carry user-controlled characters; never a raw interpolation)
function shq(s) {
  return "'" + String(s).replace(/'/g, "'\\''") + "'";
}

// PR-author-controlled fields render inside the trusted report artifact:
// escape the markdown-active characters so a crafted PR cannot plant
// links, images or emphasis in the report the reader merges from.
function mdSafe(s) {
  return s.replace(/[\\`*_[\]()!<>]/g, function (ch) { return "\\" + ch; });
}

const idSeqs = {};
function nextId(prefix) {
  idSeqs[prefix] = (idSeqs[prefix] !== undefined ? idSeqs[prefix] : 0) + 1;
  return prefix + "-" + idSeqs[prefix];
}

// gate rows cross the oracle boundary as exit_code (its JSON contract);
// the orchestration below keeps its historic internal exitCode shape
function gateRows(oracleRows) {
  return oracleRows.map(function (g) {
    return { name: g.name, exitCode: typeof g.exit_code === "number" ? g.exit_code : 0, tail: g.tail };
  });
}

// ONE probe agent per oracle fetch: runs the shared review-state oracle
// (D-014) and returns its parsed JSON — the script's only seam to the
// shell beyond it, exactly like spec-run.js's graph probe.
async function oracle(label, subargs) {
  const cmd = "python3 " + shq(skillDir + "/scripts/review_orchestrator.py") + " " +
    subargs.map(function (a) { return shq(a); }).join(" ");
  const r = await agent(
    "Run this exact shell command from the workspace root and return ONLY its " +
    "combined stdout verbatim in the stdout field (empty string if none). " +
    "Some commands run for minutes — wait for completion, never truncate:\n  " + cmd,
    { label: label, schema: PROBE_SCHEMA }
  );
  if (!r || typeof r.stdout !== "string" || !r.stdout.trim()) {
    log(label + ": oracle probe returned no result");
    return null;
  }
  try {
    return JSON.parse(r.stdout);
  } catch (e) {
    log(label + ": oracle stdout is not JSON: " + String(e));
    return null;
  }
}

// one probe renders a whole wave of asks (NFR-003): items are
// {kind, ctx} pairs against the oracle's proven ask renderers
async function askWave(label, items) {
  const d = await oracle(label, ["ask", "--kind", "batch", "--ctx", JSON.stringify({ batch: items })]);
  return d && d.status === "ok" && Array.isArray(d.asks) ? d.asks : null;
}

// mechanical fallback when the assessment agent returns nothing — computed
// from tracked state only, never fabricated prose
function fallbackAssessment(tracked, gateGreen, roundsUsed) {
  const openHigh = tracked.some(function (t) { return t.finding.severity === "high" && t.fix !== "fixed"; });
  const anyOpen = tracked.some(function (t) { return t.fix !== "fixed"; });
  const risk = !gateGreen || openHigh ? "high" : anyOpen ? "medium" : "low";
  const verdict =
    "The assessment agent returned no result — mechanical fallback. Open findings: " +
    tracked.filter(function (t) { return t.fix !== "fixed"; }).length + " of " + tracked.length +
    (roundsUsed > 0 ? " after " + roundsUsed + " fix round(s)" : "") +
    "; checks " + (gateGreen ? "green" : "RED") + ".";
  return { risk: risk, testGaps: [], residualRisks: ["the final assessment agent returned no result"], verdict: verdict };
}

// --- the run ----------------------------------------------------------------

async function main() {
  let targetFiles = [];
  let targetParts = [];
  let partLabels = [];
  let targetCandidates = 0;
  let gateTracked = [];
  let changed = [];
  let addedLines = 0;
  let prMeta = null;
  let branchBaseRef = "";
  let branchName = "";
  let commitCount = 0;
  let gate = [];
  let GATE_LINE = "";
  let modeUsed = "fix-only";
  let tracked = [];
  let allConfirmed = [];
  let allDropped = [];
  let summary = [];
  let perLens = [];
  let lensFailures = [];
  let REPO_ABS = null;
  let fastDefault = false;
  let suggestSplit = false;

  function failReturn(conclusion, notCovered, mdTitle, mdBody) {
    return { conclusion: conclusion, findings: [], verified: [], notCovered: notCovered, title: mdTitle, markdown: mdBody };
  }

  // The panel's systems, fetched once per run (one probe, NFR-003) —
  // every phase (review, triage, fix loop, final) reads this cache.
  systemsCache = await oracle("systems-probe", ["systems"]);
  if (!systemsCache || systemsCache.status !== "ok") {
    return failReturn(
      "The panel systems could not be loaded from the oracle — rerun the workflow.",
      ["the whole review — the systems fetch failed"],
      "Code review — systems unavailable",
      "# Code review — systems unavailable\n\nThe oracle's systems fetch returned nothing; nothing was reviewed.\n",
    );
  }

  // Resolve the repo arg to the repo's absolute toplevel before anything
  // else — an arg that resolves to nothing fails loudly: a silent fallback
  // to the cwd would review the wrong tree, or nothing.
  if (REPO_ARG) {
    const resolved = await oracle("repo-probe", ["scope", "--target", "diff", "--base", "HEAD", "--repo", REPO_ARG]);
    if (!resolved || resolved.status !== "ok") {
      return failReturn(
        "The repo arg \"" + REPO_ARG + "\" did not resolve to a git repository — pass the sub-repo's " +
        "directory relative to the working directory, or an absolute path.",
        ["the review target — the repo arg did not resolve to a repository"],
        "Code review — target unknown",
        "# Code review — target unknown\n\nThe repo arg \"" + REPO_ARG + "\" did not resolve to a git " +
        "repository — nothing was reviewed.\n",
      );
    }
    REPO_ABS = resolved.repo_abs;
    if (!PROJECT) {
      return failReturn(
        "The repo arg is supported for target project today — for a change, branch or PR review, run " +
        "the workflow from inside that repository (its own workspace), where the diff and the working " +
        "tree the panel reads are the repo's own.",
        ["the review target — repo with target " + TARGET + " is not supported yet"],
        "Code review — target unsupported",
        "# Code review — target unsupported\n\nThe repo arg is supported for target project today; " +
        "run change/branch/pr reviews from inside the repository.\n",
      );
    }
    log("review repo: " + REPO_ABS);
  }

  if (FIX_FROM) {
    phase("Load the findings from the previous review");
    const isInline = /^\s*[\[{]/.test(FIX_FROM_ARG);
    const loaded = await oracle(
      "fix-from-probe",
      ["findings-parse", isInline ? "--text" : "--file", FIX_FROM_ARG]
    );
    if (!loaded || loaded.status !== "error") {
      // status ok means tracked findings; anything else is a hard stop
    }
    if (!loaded) {
      return failReturn(
        "fix_from: could not read \"" + FIX_FROM_ARG + "\" — pass the review report markdown, a findings JSON file path (workspace-relative or absolute), or inline JSON.",
        ["the fix loop — fix_from payload unusable"],
        "Code review — fix_from unusable",
        "# Code review — fix_from unusable\n\nfix_from: the oracle probe returned nothing.\n",
      );
    }
    if (loaded.status === "error") {
      const msg = "fix_from: " + loaded.error + " — pass the review report markdown of a previous review, or its findings JSON.";
      return failReturn(msg, ["the fix loop — fix_from payload unusable"], "Code review — fix_from unusable", "# Code review — fix_from unusable\n\n" + msg + "\n");
    }
    tracked = loaded.tracked;
    allConfirmed = tracked.map(function (t) { return t.finding; });
    summary = tracked.map(function (t) {
      return { id: t.finding.id, where: t.finding.where, what: t.finding.what, severity: t.finding.severity, lens: t.finding.lens, status: t.finding.confirmation.status };
    });
    const g = await oracle("gate-probe", ["gate", REPO_ABS ? "--repo" : "--noop", REPO_ABS || "", "--base", BASE].filter(function (x) { return x !== "--noop" && x !== ""; }));
    gate = g && g.status === "ok" ? gateRows(g.rows) : [{ name: "gate.sh (spec-code-review)", exitCode: 1, tail: "gate.sh produced no JSON report" }];
    GATE_LINE = g && g.status === "ok" ? g.note : "The repo's own checks could not be read";
    const preBad = gate.filter(function (x) { return x.exitCode !== 0; });
    for (const x of preBad) {
      tracked.push({
        finding: {
          id: nextId("gate"), where: x.name, what: "Repo check failed before the fixes: " + x.name,
          evidence: x.tail || "(no output)", severity: "high", lens: "gate", impact: "",
          confirmation: { status: "verified", note: "exit code nonzero before fix round 1" },
        },
        fix: "unfixed", fixNote: "pre-fix: check failing",
      });
      log("gate finding (pre-fix): " + x.name + " failing");
    }
    log("fix loop: " + tracked.length + " finding(s) carried from the previous review — pre-fix gate: " + (gate.length - preBad.length) + "/" + gate.length + " checks passed");
  } else {
    phase("Scope the change and run the repo's checks");

    if (TARGETS.indexOf(TARGET) === -1) {
      return failReturn(
        "Unknown target \"" + TARGET + "\" — valid targets: diff (a change against a base ref), " +
        "branch (the current branch's changes against its base), pr (a GitHub pull request), " +
        "project (the whole codebase).",
        ["the review target — unknown target value \"" + TARGET + "\""],
        "Code review — target unknown",
        "# Code review — target unknown\n\nUnknown target \"" + TARGET + "\" — nothing was reviewed.\n",
      );
    }
    if (PR && !PR_ARG) {
      return failReturn(
        "target pr needs a pr arg — the pull request number, URL or owner/repo#N.",
        ["the review target — pr target without a pr arg"],
        "Code review — target unknown",
        "# Code review — target unknown\n\ntarget pr needs a pr arg — nothing was reviewed.\n",
      );
    }

    // ONE oracle fetch resolves the whole scope + gate (NFR-003).
    const scopeArgs = ["scope", "--target", TARGET, "--base", BASE_ARG || "HEAD"];
    if (PR_ARG) scopeArgs.push("--pr", PR_ARG);
    if (REPO_ABS) scopeArgs.push("--repo", REPO_ABS);
    if (PATHS_ARG) scopeArgs.push("--paths", PATHS_ARG);
    scopeArgs.push("--include-gate");
    const sc = await oracle("scope-probe", scopeArgs);

    if (!sc) {
      return failReturn(
        "The scope probe returned no result — the review cannot see the change. Rerun the workflow.",
        ["the change scope — the git scope probe failed"],
        "Code review — scope unknown",
        "# Code review — scope unknown\n\nThe scope probe returned nothing; nothing was reviewed.\n",
      );
    }
    if (sc.status === "error") {
      const stage = sc.stage || "";
      if (stage === "pr-view") {
        return failReturn(
          "gh pr view failed for \"" + PR_ARG + "\" — is the gh CLI installed and authenticated, " +
          "and is that a valid pull request in this repo's remote?",
          ["the pull request — gh pr view returned nothing usable"],
          "Code review — PR unknown",
          "# Code review — PR unknown\n\ngh pr view returned nothing usable; nothing was reviewed.\n",
        );
      }
      if (stage === "pr-state") {
        return failReturn(
          "The review cannot see the git state (rev-parse/status probe returned nothing) — rerun the workflow.",
          ["the pull request — git state probe failed"],
          "Code review — state unknown",
          "# Code review — state unknown\n\nThe git state probe returned nothing; nothing was reviewed.\n",
        );
      }
      if (stage === "pr-dirty") {
        return failReturn(
          sc.head_matches
            ? "PR #" + (sc.pr_number || "") + " is checked out but the working tree is dirty — the PR diff would fold " +
              "uncommitted local work into code attributed to the PR. Commit or stash, then rerun."
            : "PR #" + (sc.pr_number || "") + " is not checked out and the working tree is dirty — the panel " +
              "reads the working tree, so checking out would hide uncommitted work. Commit or stash, then rerun; " +
              "on a clean tree the review checks the PR out itself.",
          ["the pull request — refused to review a PR target over a dirty working tree"],
          "Code review — PR not reviewed",
          "# Code review — PR not reviewed\n\nThe working tree is dirty; the PR review was refused before anything was reviewed.\n",
        );
      }
      if (stage === "pr-checkout") {
        return failReturn(
          "Could not check out the PR (gh pr checkout failed, or HEAD does not match the PR head " +
          "afterward) — check the PR out manually and rerun.",
          ["the pull request — automatic checkout failed"],
          "Code review — PR checkout failed",
          "# Code review — PR checkout failed\n\nAutomatic checkout failed; nothing was reviewed.\n",
        );
      }
      if (stage === "pr-merge-base") {
        return failReturn(
          "No common ancestor between HEAD and the PR's base commit — cannot compute the PR diff.",
          ["the pull request — merge-base with the base commit failed"],
          "Code review — PR diff unknown",
          "# Code review — PR diff unknown\n\nNo common ancestor with the PR's base commit; nothing was reviewed.\n",
        );
      }
      if (stage === "branch-no-base") {
        return failReturn(
          "Could not detect a base branch for the branch review — pass base explicitly (e.g. base: \"main\").",
          ["the branch review — no base branch resolved"],
          "Code review — base unknown",
          "# Code review — base unknown\n\nNo base branch resolved; nothing was reviewed.\n",
        );
      }
      if (stage === "branch-merge-base") {
        return failReturn(
          "No common ancestor between HEAD and " + (sc.base || "") + " — cannot compute the branch diff.",
          ["the branch review — merge-base with " + (sc.base || "") + " failed"],
          "Code review — branch diff unknown",
          "# Code review — branch diff unknown\n\nNo common ancestor; nothing was reviewed.\n",
        );
      }
      if (stage === "ls-files") {
        return failReturn(
          "The target probe returned no result — the review cannot see the project's files. Rerun the workflow.",
          ["the project file listing — the target probe failed"],
          "Code review — target unknown",
          "# Code review — target unknown\n\nThe project file probe returned nothing; nothing was reviewed.\n",
        );
      }
      // diff with an unresolvable base behaves as an empty diff, exactly
      // as the inline implementation did (numstat produced nothing)
      return failReturn(
        "git diff " + (sc.base || BASE) + " has no changes — nothing to review.",
        [],
        "Code review — nothing to review",
        "# Code review — nothing to review\n\ngit diff " + (sc.base || BASE) + " has no changes.\n",
      );
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
      log(
        "review target: project" + (REPO_ABS ? " (repo: " + REPO_ABS + ")" : "") + " — all " + targetCandidates +
        " tracked source files" + (PATHS_ARG ? " (paths filter: " + PATHS_ARG + ")" : "") +
        ", read as " + targetParts.length + " reviewer part(s) per lens"
      );
      if (targetFiles.length === 0) {
        return {
          conclusion: "No tracked source files matched the project target" +
            (PATHS_ARG ? " (paths filter: " + PATHS_ARG + ")" : "") + " — nothing to review.",
          findings: [], verified: ["project target: no tracked source files matched"], notCovered: [],
          title: "Code review — nothing to review",
          markdown: "# Code review — nothing to review\n\nNo tracked source files matched the target filter.\n",
        };
      }
    } else {
      changed = sc.files;
      addedLines = sc.added;
      scopeDirty = !sc.clean;
      log(
        "change under review: " +
        (PR ? "PR #" + prMeta.number + " (diff vs merge-base " + BASE.slice(0, 12) + ")"
          : BRANCH_MODE ? "branch " + branchName + " (diff vs merge-base " + BASE.slice(0, 12) + ")"
          : "git diff " + BASE) +
        " — " + changed.length + " files, ~" + addedLines + " added lines" +
        (sc.clean ? " (clean tree)" : " (uncommitted work present)") +
        (sc.suggest_split ? " — large change: the report will recommend splitting" : "")
      );
      if (changed.length === 0) {
        const nothing = PR
          ? "PR #" + prMeta.number + " has no changes against " + prMeta.baseRefName + " — nothing to review."
          : BRANCH_MODE
            ? "Branch " + branchName + " has no changes against " + branchBaseRef + " — nothing to review."
            : "git diff " + BASE + " has no changes — nothing to review.";
        return {
          conclusion: nothing, findings: [],
          verified: ["change scope: the review target resolved to an empty diff"], notCovered: [],
          title: "Code review — nothing to review",
          markdown: "# Code review — nothing to review\n\n" + nothing + "\n",
        };
      }
    }
    fastDefault = sc.fast_mode_default;
    suggestSplit = sc.suggest_split;

    gate = gateRows(sc.gate.rows);
    GATE_LINE = sc.gate.note;
    const gateFailed = gate.filter(function (g) { return g.exitCode !== 0; });
    log("repo checks: " + (gate.length - gateFailed.length) + "/" + gate.length + " detected and run" +
      (gateFailed.length > 0 ? " — " + gateFailed.length + " FAILING" : ""));

    if (gateFailed.length > 0) {
      for (const g of gateFailed) {
        gateTracked.push({
          finding: {
            id: nextId("gate"), where: g.name, what: "Repo check failed before the review: " + g.name,
            evidence: g.tail || "(no output)", severity: "high", lens: "gate", impact: "",
            confirmation: { status: "verified", note: "exit code nonzero before the review started" },
          },
          fix: "pending", fixNote: "not yet attempted",
        });
      }
      if (!PROJECT) {
        const gateFindings = gateFailed.map(function (g) {
          return {
            id: nextId("gate"), where: g.name, what: "Repo check failed: " + g.name,
            evidence: g.tail || "(no output)", status: "verified", severity: "high", lens: "gate",
            impact: "", fixStatus: "pending",
          };
        });
        const gateMd = [
          "# Code review — checks failed, review stopped", "",
          PR ? "PR #" + prMeta.number + " (" + changed.length + " files) failed the repo's own checks, so the "
            : BRANCH_MODE ? "Branch " + branchName + " (" + changed.length + " files) failed the repo's own checks, so the "
            : "The change (`git diff " + BASE + "` — " + changed.length + " files) failed the repo's own checks, so the ",
          "specialist reviewers were not spent on it. Fix these first, then rerun the review.", "",
          "## Failed checks", "",
        ].concat(gate.map(function (g) {
          return "- " + (g.exitCode === 0 ? "pass" : "**FAIL**") + " — " + g.name +
            (g.exitCode === 0 ? "" : "\n\n  ```\n  " + g.tail + "\n  ```");
        })).join("\n");
        return {
          conclusion:
            (PR ? "PR #" + prMeta.number : BRANCH_MODE ? "Branch " + branchName : "The change") +
            " failed " + gateFailed.length + " of " + gate.length +
            " detected repo checks (" + gateFailed.map(function (g) { return g.name; }).join("; ") + "). Specialist review was skipped — " +
            "these are mechanical fixes; rerun the review after they pass.",
          findings: gateFindings,
          verified: ["the mechanical gate ran the repo's own detected checks — " + gateFailed.length + " failed"],
          notCovered: ["specialist review of the diff — skipped because the mechanical gate failed"],
          title: "Code review — checks failed",
          markdown: gateMd,
        };
      }
      log("project audit continues past the red gate — " + gateFailed.length + " failing check(s) recorded as gate findings");
    }

    phase("Preflight the codebase and modules the target touches");

    const scoutAskText = await askWave("scout-ask-probe", [
      { kind: "scout", ctx: { base: BASE, project: PROJECT, files: PROJECT ? targetFiles : changed, repo_abs: REPO_ABS } },
    ]);
    const scoutResult = scoutAskText
      ? await agent(withSystem(systemsCache.scout, scoutAskText[0]), { label: "preflight-scout", schema: SCOUT_SCHEMA })
      : null;
    scoutMap = scoutResult && Array.isArray(scoutResult.modules) ? scoutResult : null;
    log(scoutMap
      ? "preflight scout: " + scoutMap.modules.length + " module(s), " + scoutMap.conventions.length +
        " convention(s), " + scoutMap.riskAreas.length + " risk area(s)"
      : "preflight scout returned no map — the reviewers start from the raw target");

    phase("Review the change through separate lenses and confirm every finding");

    modeUsed = MODE_ARG === "fast" || MODE_ARG === "full" ? MODE_ARG : (fastDefault ? "fast" : "full");
    const panel = modeUsed === "fast" ? [systemsCache.general] : systemsCache.lenses;
    log("review mode: " + modeUsed + (modeUsed === "fast" ? " (small diff, one general reviewer)" : " (three specialists)"));

    const askCtxBase = { base: BASE, intent: intentText, scout_map: scoutMap, repo_abs: REPO_ABS, project: PROJECT };
    // ONE ask wave for the whole panel (per part in project mode)
    const reviewItems = [];
    for (const lensDef of panel) {
      if (PROJECT) {
        targetParts.forEach(function (partFiles, pi) {
          reviewItems.push({
            kind: "review-project",
            ctx: Object.assign({}, askCtxBase, {
              lens: lensDef, files: partFiles, candidates: targetCandidates,
              part: pi + 1, parts: targetParts.length, gate_line: GATE_LINE,
            }),
            label: lensDef.label + "-review-" + (pi + 1) + "-" + (partLabels[pi] || "part"),
          });
        });
      } else {
        reviewItems.push({
          kind: "review",
          ctx: Object.assign({}, askCtxBase, {
            lens: lensDef, files_n: changed.length, lines: addedLines, over_cap: false, gate_line: GATE_LINE,
          }),
          label: lensDef.label + "-review",
        });
      }
    }
    const reviewAsks = await askWave("review-asks-probe", reviewItems);

    async function runLens(lensDef, lensAsks) {
      let rawFindings = [];
      let failedParts = 0;
      if (PROJECT) {
        const partReviews = await pipeline(lensAsks, function (item) {
          return agent(withSystem(lensDef.system, item.ask), { label: item.label, schema: LENS_SCHEMA });
        });
        for (const r of partReviews) {
          if (r && Array.isArray(r.findings)) rawFindings = rawFindings.concat(r.findings);
          else failedParts++;
        }
        log(lensDef.name + ": " + (lensAsks.length - failedParts) + "/" + lensAsks.length +
          " part(s) read — " + rawFindings.length + " finding(s)");
      } else {
        const review = lensAsks[0]
          ? await agent(withSystem(lensDef.system, lensAsks[0].ask), { label: lensDef.label + "-review", schema: LENS_SCHEMA })
          : null;
        if (!review) return { lens: lensDef.label, failed: true, kept: [], dropped: [] };
        rawFindings = review.findings;
        log(lensDef.name + ": " + rawFindings.length + " finding(s)");
      }
      if (rawFindings.length === 0) {
        return { lens: lensDef.label, partFailures: failedParts, kept: [], dropped: [] };
      }
      return { lens: lensDef.label, partFailures: failedParts, raw: rawFindings };
    }

    const perLens = [];
    if (reviewAsks) {
      let idx = 0;
      for (const lensDef of panel) {
        const take = PROJECT ? targetParts.length : 1;
        const items = reviewAsks.slice(idx, idx + take).map(function (ask, i) {
          return { ask: ask, label: reviewItems[idx + i].label };
        });
        idx += take;
        perLens.push(await runLens(lensDef, items));
      }
    } else {
      log("review asks could not be rendered — the panel cannot start");
      return failReturn(
        "The ask wave returned no result — the review cannot brief its reviewers. Rerun the workflow.",
        ["the whole review — the ask rendering probe failed"],
        "Code review — asks unavailable",
        "# Code review — asks unavailable\n\nThe oracle's ask wave returned nothing; nothing was reviewed.\n",
      );
    }

    // ONE triage ask wave for every lens that found something
    const triageItems = [];
    for (const r of perLens) {
      if (r.raw && r.raw.length > 0) {
        triageItems.push({ kind: PROJECT ? "triage-project" : "triage", ctx: Object.assign({}, askCtxBase, { lens_label: r.lens, findings: r.raw }) });
      }
    }
    const triageAsks = triageItems.length ? await askWave("triage-asks-probe", triageItems) : [];
    let ti = 0;
    for (const r of perLens) {
      if (!(r.raw && r.raw.length > 0)) continue;
      const ask = triageAsks[ti++];
      const triaged = ask
        ? await agent(withSystem(systemsCache.triage, ask), { label: r.lens + "-triage", schema: TRIAGE_SCHEMA })
        : null;
      if (!triaged) {
        log(r.lens + ": triage returned no result — raw findings pass through");
        r.kept = r.raw.map(function (f) { return { finding: f, lens: r.lens }; });
        r.dropped = [];
        r.triageFailed = true;
      } else {
        r.kept = triaged.kept.map(function (f) { return { finding: f, lens: r.lens }; });
        r.dropped = triaged.dropped;
      }
      delete r.raw;
    }

    const lensFailures = perLens.filter(function (r) { return r.failed; });
    for (const f of lensFailures) log("lens failed: " + f.lens + " reviewer returned no result");

    let keptAll = perLens.reduce(function (a, r) { return a.concat(r.kept || []); }, []);
    allDropped = perLens.reduce(function (a, r) { return a.concat(r.dropped || []); }, []);

    if (keptAll.length > 1) {
      const crossAsk = await askWave("cross-ask-probe", [{ kind: "cross-lens", ctx: Object.assign({}, askCtxBase, { kept: keptAll }) }]);
      const cross = crossAsk
        ? await agent(withSystem(systemsCache.triage, crossAsk[0]), { label: "cross-lens-merge", schema: CROSS_TRIAGE_SCHEMA })
        : null;
      if (cross) {
        keptAll = cross.kept.map(function (f) { return { finding: f, lens: f.lens }; });
        allDropped = allDropped.concat(cross.dropped);
      } else {
        log("cross-lens merge returned no result — per-lens kept findings all proceed to confirmation");
      }
    }

    // ONE confirm ask wave for every kept finding
    const confirmItems = keptAll.map(function (kf) {
      return { kind: PROJECT ? "confirm-project" : "confirm", ctx: Object.assign({}, askCtxBase, { finding: kf.finding }) };
    });
    const confirmAsks = confirmItems.length ? await askWave("confirm-asks-probe", confirmItems) : [];
    const confirmations = await pipeline(
      keptAll.map(function (kf, i) { return { kf: kf, ask: confirmAsks[i] }; }),
      function (item) {
        return item.ask
          ? agent(item.ask, { label: "confirm-" + item.kf.lens, schema: CONFIRM_SCHEMA })
          : Promise.resolve(null);
      }
    );
    allConfirmed = [];
    for (let i = 0; i < keptAll.length; i++) {
      const c = confirmations[i];
      const confirmation = c ? c : { status: "unconfirmed", note: "no confirmation result — the confirmer returned nothing; treat as unverified" };
      if (!c) log("confirm " + keptAll[i].finding.where + ": no result");
      allConfirmed.push({
        id: nextId(keptAll[i].lens), where: keptAll[i].finding.where, what: keptAll[i].finding.what,
        evidence: keptAll[i].finding.evidence, severity: keptAll[i].finding.severity, lens: keptAll[i].lens,
        impact: typeof keptAll[i].finding.impact === "string" ? keptAll[i].finding.impact : "",
        confirmation: confirmation,
      });
    }
    allConfirmed.sort(function (a, b) {
      return (SEV_RANK[a.severity] !== undefined ? SEV_RANK[a.severity] : 3) - (SEV_RANK[b.severity] !== undefined ? SEV_RANK[b.severity] : 3);
    });
    summary = gateTracked.map(function (t) {
      return { id: t.finding.id, where: t.finding.where, what: t.finding.what, severity: t.finding.severity, lens: t.finding.lens, status: t.finding.confirmation.status };
    }).concat(allConfirmed.map(function (c) {
      return { id: c.id, where: c.where, what: c.what, severity: c.severity, lens: c.lens, status: c.confirmation.status };
    }));

    tracked = gateTracked.concat(allConfirmed.map(function (f) {
      return { finding: f, fix: "pending", fixNote: "not yet attempted" };
    }));
  }

  let roundsUsed = 0;
  let finalGate = gate;
  let gateGreen = gate.every(function (g) { return g.exitCode === 0; });
  const fixerNotes = [];
  const allChangedPaths = [];
  let fixerAborted = false;

  if (FIX_ROUNDS > 0 && tracked.length > 0) {
    phase("Fix the confirmed findings and verify every fix");
    let gateFeedback = "";

    for (let round = 1; round <= FIX_ROUNDS; round++) {
      const unresolved = tracked.filter(function (t) { return t.fix !== "fixed"; });
      if (unresolved.length === 0) break;
      const fixerAsks = await askWave("fixer-ask-probe", [{
        kind: "fixer",
        ctx: { base: BASE, project: PROJECT, intent: intentText, repo_abs: REPO_ABS, round: round, unresolved: unresolved, gate_feedback: gateFeedback || null },
      }]);
      const outcome = fixerAsks
        ? await agent(withSystem(systemsCache.fixer, fixerAsks[0]), { label: "fixer-round-" + round, schema: FIX_SCHEMA })
        : null;
      if (!outcome) {
        log("fix round " + round + ": the fixer returned no result — loop aborted");
        fixerAborted = true;
        break;
      }
      roundsUsed = round;
      for (const n of outcome.notes) fixerNotes.push("round " + round + ": " + n);
      for (const p of outcome.changedPaths) if (allChangedPaths.indexOf(p) === -1) allChangedPaths.push(p);
      log("fix round " + round + ": " + outcome.addressed.length + " addressed · " + outcome.skipped.length + " skipped · " + outcome.changedPaths.length + " path(s) changed");

      const g = await oracle("gate-probe", ["gate", REPO_ABS ? "--repo" : "--noop", REPO_ABS || "", PROJECT ? "--tree" : "--base", PROJECT ? "" : BASE].filter(function (x) { return x !== "--noop" && x !== ""; }));
      const roundGate = g && g.status === "ok" ? gateRows(g.rows) : [{ name: "gate.sh (spec-code-review)", exitCode: 1, tail: "gate.sh produced no JSON report" }];
      finalGate = roundGate;
      const gateBad = roundGate.filter(function (g2) { return g2.exitCode !== 0; });
      gateGreen = gateBad.length === 0;
      gateFeedback = gateBad.map(function (g2) { return g2.name + ":\n" + g2.tail; }).join("\n\n");
      log("checks after round " + round + ": " + (roundGate.length - gateBad.length) + "/" + roundGate.length + " passed");

      for (let i = tracked.length - 1; i >= 0; i--) {
        if (tracked[i].finding.lens === "gate") tracked.splice(i, 1);
      }
      for (const g2 of gateBad) {
        tracked.push({
          finding: {
            id: nextId("gate"), where: g2.name, what: "Repo check failed after the fixes: " + g2.name,
            evidence: g2.tail || "(no output)", severity: "high", lens: "gate",
            confirmation: { status: "verified", note: "exit code nonzero after fix round " + round },
          },
          fix: "unfixed", fixNote: "round " + round + ": check failing",
        });
        log("gate finding (round " + round + "): " + g2.name + " failing");
      }

      const verifiable = unresolved.filter(function (t) { return t.finding.lens !== "gate"; });
      const verifyAsks = verifiable.length ? await askWave("verify-asks-probe", verifiable.map(function (t) {
        return { kind: "verify", ctx: { base: BASE, project: PROJECT, repo_abs: REPO_ABS, tracked: t, notes: outcome.notes.join(" | ") } };
      })) : [];
      const verifications = await pipeline(
        verifiable.map(function (t, i) { return { t: t, ask: verifyAsks[i] }; }),
        function (item) {
          return item.ask ? agent(item.ask, { label: "verify-round-" + round, schema: VERIFY_SCHEMA }) : Promise.resolve(null);
        }
      );
      for (let i = 0; i < verifiable.length; i++) {
        const v = verifications[i];
        const t = verifiable[i];
        if (!v) {
          t.fixNote = "round " + round + ": verifier returned no result (treated as not fixed)";
          log("verify round " + round + " (" + t.finding.where + "): no result");
          continue;
        }
        t.fix = v.status;
        t.fixNote = "round " + round + ": " + v.note;
        log("verify round " + round + " (" + t.finding.where + "): " + v.status);
      }

      if (outcome.changedPaths.length > 0) {
        const frAsks = await askWave("fix-review-ask-probe", [{ kind: "fix-review", ctx: { base: BASE, repo_abs: REPO_ABS, paths: outcome.changedPaths, gate_green: gateGreen } }]);
        const fixReview = frAsks
          ? await agent(withSystem(systemsCache.fix_review, frAsks[0]), { label: "fix-review-round-" + round, schema: LENS_SCHEMA })
          : null;
        if (fixReview && fixReview.findings.length > 0) {
          const ftAsks = await askWave("fix-review-triage-ask-probe", [{ kind: "triage", ctx: { base: BASE, intent: intentText, lens_label: "fix-review", findings: fixReview.findings } }]);
          const triagedFix = ftAsks
            ? await agent(withSystem(systemsCache.triage, ftAsks[0]), { label: "fix-review-triage-" + round, schema: TRIAGE_SCHEMA })
            : null;
          const fixKept = triagedFix ? triagedFix.kept : fixReview.findings;
          const fcAsks = await askWave("fix-review-confirm-asks-probe", fixKept.map(function (f) {
            return { kind: "confirm", ctx: { base: BASE, finding: f } };
          }));
          const fixConfs = await pipeline(
            fixKept.map(function (f, i) { return { f: f, ask: fcAsks ? fcAsks[i] : null }; }),
            function (item) {
              return item.ask ? agent(item.ask, { label: "confirm-fix-review-" + round, schema: CONFIRM_SCHEMA }) : Promise.resolve(null);
            }
          );
          for (let i = 0; i < fixKept.length; i++) {
            const fc = fixConfs[i];
            tracked.push({
              finding: {
                id: nextId("fix-review"), where: fixKept[i].where, what: fixKept[i].what,
                evidence: fixKept[i].evidence, severity: fixKept[i].severity, lens: "fix-review",
                impact: typeof fixKept[i].impact === "string" ? fixKept[i].impact : "",
                confirmation: fc ? fc : { status: "unconfirmed", note: "no confirmation result — the confirmer returned nothing" },
              },
              fix: "pending", fixNote: "new from fix review, round " + round,
            });
          }
        } else if (!fixReview) {
          log("fix review round " + round + ": reviewer returned no result");
        }
      }

      if (tracked.every(function (t) { return t.fix === "fixed"; })) break;
    }
  }

  phase("Synthesize the final review report");

  let finalAdded = addedLines;
  let finalChangedN = changed.length;
  if (PROJECT) {
    finalChangedN = targetFiles.length;
    finalAdded = 0;
  } else if (roundsUsed > 0) {
    const again = await oracle("rescope-probe", ["scope", "--target", "diff", "--base", BASE].concat(REPO_ABS ? ["--repo", REPO_ABS] : []));
    if (again && again.status === "ok") {
      finalAdded = again.added;
      finalChangedN = again.files.length;
    }
  }

  const readerTracked = tracked.filter(function (t) { return t.finding.lens !== "gate"; });
  const nVerified = readerTracked.filter(function (t) { return t.finding.confirmation.status === "verified"; }).length;
  const nUnconfirmed = readerTracked.length - nVerified;
  const nHigh = tracked.filter(function (t) { return t.finding.severity === "high"; }).length;
  const nFixed = tracked.filter(function (t) { return t.fix === "fixed"; }).length;

  let assessment;
  let recommendation;
  let assessmentFailed = false;
  if (roundsUsed > 0) {
    const lfAsks = await askWave("loop-final-ask-probe", [{
      kind: "loop-final",
      ctx: { base: BASE, project: PROJECT, scout_map: scoutMap, tracked: tracked, rounds_used: roundsUsed, gate_green: gateGreen, changed_paths: allChangedPaths },
    }]);
    const fa = lfAsks
      ? await agent(withSystem(systemsCache.triage, lfAsks[0]), { label: "final-assessment", schema: LOOP_ASSESS_SCHEMA })
      : null;
    if (fa) {
      assessment = fa;
      recommendation = fa.recommendation;
    } else {
      assessment = fallbackAssessment(tracked, gateGreen, roundsUsed);
      recommendation = "human";
      assessmentFailed = true;
    }
  } else {
    const fAsks = await askWave("final-ask-probe", [{
      kind: PROJECT ? "final-project" : "final",
      ctx: { base: BASE, intent: intentText, scout_map: scoutMap, repo_abs: REPO_ABS, summary: summary, gate_line: GATE_LINE, files: targetFiles },
    }]);
    const fa = fAsks
      ? await agent(withSystem(systemsCache.triage, fAsks[0]), { label: "final-assessment", schema: ASSESS_SCHEMA })
      : null;
    assessment = fa ? fa : fallbackAssessment(tracked, gateGreen, 0);
    recommendation = "none";
    if (!fa) assessmentFailed = true;
  }

  const title = FIX_FROM
    ? "# Code review — fix loop (" + tracked.length + " finding(s) carried from the previous review)"
    : PROJECT
      ? "# Code review — project (" + finalChangedN + " files)"
      : PR
        ? "# Code review — PR #" + prMeta.number + ": " + mdSafe(prMeta.title) + " (" + finalChangedN + " files, ~" + finalAdded + " added lines)"
        : BRANCH_MODE
          ? "# Code review — branch " + branchName + " vs " + branchBaseRef + " (" + finalChangedN + " files, ~" + finalAdded + " added lines)"
          : "# Code review — " + BASE + " (" + finalChangedN + " files, ~" + finalAdded + " added lines)";
  const modeLine = FIX_FROM
    ? "Mode: fix-only — the review stages were skipped; findings carried from the previous review's report. fix_rounds: " + FIX_ROUNDS + "."
    : "Mode: " + modeUsed + (modeUsed === "fast" ? " — one general reviewer" : " — correctness, security, quality") +
      " · every kept non-gate finding confirmed by an independent reader." +
      (PROJECT ? " Target: the project's code as it stands — \"merge\" reads as ready-as-is." : "") +
      (PR ? " Target: pull request #" + prMeta.number + " by " + mdSafe(prMeta.author) + " → " + mdSafe(prMeta.baseRefName) + (prMeta.url ? " — " + mdSafe(prMeta.url) : "") + " — \"merge\" reads as the PR is ready." : "") +
      (BRANCH_MODE ? " Target: the branch's changes vs " + branchBaseRef + " at the merge-base — \"merge\" reads as the branch is ready to merge." + (scopeDirty ? " Uncommitted work present in the working tree is included in the reviewed diff." : "") : "") +
      ((!FIX_FROM && !PROJECT && suggestSplit) ? " Large change: ~" + finalAdded + " added lines across " + finalChangedN + " files — consider splitting into smaller, independently reviewable chunks; reviewers read whole targets, and coverage thins as size grows." : "") +
      (roundsUsed > 0 ? " Fix loop: " + roundsUsed + " round(s) — " + nFixed + "/" + tracked.length + " findings fixed, checks " + (gateGreen ? "green" : "RED") + ". Fixes sit uncommitted in the working tree." : "");

  // The report body renders in the oracle (D-014): findings markdown,
  // gate rows, dropped-at-triage, gaps, residuals, checked lines.
  const reportPayload = {
    title: title,
    mode_line: modeLine,
    verdict_line: "## Verdict — " + assessment.risk + " risk" + (roundsUsed > 0 ? " · recommendation: **" + recommendation + "**" : ""),
    tracked: tracked,
    gate_rows: finalGate,
    gate_green: gateGreen,
    assessment: assessment,
    dropped: allDropped,
    fixer_notes: fixerNotes,
    rounds_used: roundsUsed,
    checked: [
      PROJECT
        ? "- Project review target: all " + targetCandidates + " tracked source files of " + (REPO_ABS ? "the sub-repo at " + REPO_ABS : "the repository") + ", covered by " + targetParts.length + " reviewer part(s) per lens (contiguous, directory-coherent, byte-balanced runs of the path-sorted file list); lockfiles, generated and vendored files are excluded by type" + (PATHS_ARG ? "; paths filter: " + PATHS_ARG : "") + "."
        : "",
      finalGate.length > 0
        ? gateGreen
          ? "- The repo's own detected checks all ran and passed: " + finalGate.map(function (g) { return g.name; }).join("; ") + "."
          : "- The repo's own detected checks: " + finalGate.filter(function (g) { return g.exitCode === 0; }).length + " of " + finalGate.length + " passed — failing: " + finalGate.filter(function (g) { return g.exitCode !== 0; }).map(function (g) { return g.name; }).join("; ") + " (see FAIL rows above)."
        : "- The gate detected no checks in this repo — the review ran without a mechanical floor.",
      !FIX_FROM && scoutMap
        ? "- Preflight scout mapped the ground before the reviewers started: " + scoutMap.modules.length + " module(s), " + scoutMap.conventions.length + " convention(s), " + scoutMap.riskAreas.length + " risk area(s)."
        : "",
      "- Each non-gate finding was re-checked by an independent reader that did not write it (" + nVerified + " verified, " + nUnconfirmed + " unconfirmed).",
    ].filter(Boolean),
    fix_checked: roundsUsed > 0
      ? [
          "- After each fix round the gate re-ran" + (gateGreen ? " and finished green" : " — still failing") + ", every attempted fix was verified by an independent reader, and a fresh-eyes reviewer scanned the fix diff.",
          "- The fixes are uncommitted in the working tree — inspect with `git diff` and commit when satisfied.",
        ]
      : [],
  };
  const rep = await oracle("report-probe", ["report", "--kind", roundsUsed > 0 ? "fix" : "review", "--data", JSON.stringify(reportPayload)]);
  const reportMd = rep && rep.status === "ok"
    ? rep.markdown
    : "# Code review — report unavailable\n\nThe oracle's report rendering failed; findings remain in the run result.\n";
  const reportedFindings = rep && rep.status === "ok" ? rep.reported_findings : [];

  const notCovered = [];
  if (FIX_FROM) notCovered.push("the review stages were skipped (fix_from) — coverage inherits the previous report's notCovered; anything it missed stays missed");
  if (!FIX_FROM && !scoutMap) notCovered.push("preflight scout returned no map — the review ran without the codebase and module context step");
  for (const f of lensFailures || []) notCovered.push("the " + f.lens + " lens was not covered — its reviewer returned no result");
  for (const r of perLens || []) {
    if (r.partFailures) notCovered.push("the " + r.lens + " lens: " + r.partFailures + " of " + targetParts.length + " reviewer part(s) returned no result — their files were not reviewed");
    if (r.triageFailed) notCovered.push("the " + r.lens + " lens ran without triage — its raw findings passed straight to confirmation");
  }
  if (finalGate.length === 0) notCovered.push("no repo checks were detected by the gate — this review ran without a mechanical floor; ask the repo for its documented check command");
  if (assessmentFailed) notCovered.push("residual: the final assessment agent returned no result — a mechanical fallback assessment was used");
  if (fixerAborted) notCovered.push("residual: the fixer returned no result in an active round — the loop aborted with findings unresolved");
  for (const t of assessment.testGaps) notCovered.push("test gap: " + t);
  for (const r of assessment.residualRisks) notCovered.push("residual: " + r);
  notCovered.push("runtime behavior beyond the repo's test suites was not exercised — this was a static review");
  if (roundsUsed > 0) notCovered.push("the fixes are uncommitted — the commit decision and message remain yours");

  return {
    conclusion:
      roundsUsed > 0
        ? assessment.verdict + " — recommendation: " + recommendation + ". " + nFixed + "/" + tracked.length + " findings fixed over " + roundsUsed + " round(s); checks " + (gateGreen ? "green" : "RED") + ". The fixes sit uncommitted in the working tree."
        : assessment.verdict + " — " + tracked.length + " confirmed finding(s), " + nHigh + " high, " + nUnconfirmed + " unconfirmed; overall risk " + assessment.risk + "." + (allDropped.length ? " (" + allDropped.length + " dropped at triage as duplicates or out of scope.)" : ""),
    findings: reportedFindings,
    verified: [].concat(
      FIX_FROM ? ["fix loop continuation — findings carried from the previous review's report; review stages skipped"] : [],
      PROJECT ? ["review target: " + (REPO_ABS ? "the sub-repo at " + REPO_ABS + " — its" : "the project's") + " tracked source files — all " + targetCandidates + " matched, read as " + targetParts.length + " reviewer part(s) per lens"] : [],
      !FIX_FROM && PR ? ["review target: PR #" + prMeta.number + " (" + prMeta.state + ") — the merge-base diff against " + prMeta.baseRefName] : [],
      !FIX_FROM && BRANCH_MODE ? ["review target: branch " + branchName + " vs " + branchBaseRef + " — the merge-base diff (" + commitCount + " commit(s))"] : [],
      finalGate.length > 0
        ? gateGreen
          ? ["the mechanical gate ran the repo's own detected checks (all passed): " + finalGate.map(function (g) { return g.name; }).join("; ")]
          : ["the mechanical gate ran the repo's own detected checks — " + finalGate.filter(function (g) { return g.exitCode !== 0; }).length + " of " + finalGate.length + " FAILED: " + finalGate.filter(function (g) { return g.exitCode !== 0; }).map(function (g) { return g.name; }).join("; ")]
        : [],
      !FIX_FROM && scoutMap ? ["preflight scout mapped the codebase and modules before the panel started (" + scoutMap.modules.length + " module(s))"] : [],
      ["every reported non-gate finding was re-checked by an independent reader that did not write it"],
      roundsUsed > 0
        ? ["every attempted fix was verified by an independent reader, and a fresh-eyes reviewer scanned the fix diff", "the gate re-ran after the final fix round — " + (gateGreen ? "all green" : "still failing")]
        : []
    ),
    notCovered: notCovered,
    title: roundsUsed > 0 ? "Code review and fix report" : "Code review report",
    markdown: reportMd,
  };
}

// Module-level systems cache, filled once at the top of main(): the
// review wave, the fix loop and the final assessment all read it.
let systemsCache = null;

const result = await main();
result;
