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
    "recommendation. Use when the user asks to review a change, a pull " +
    "request, a branch's recent changes, or the whole project — or to " +
    "review and fix any of them, in any git repository.",
}

// ---------------------------------------------------------------------------
// spec-code-review.js — the Claude Code dialect of the three-stage review.
// __SKILL_DIR__ below is a placeholder; tools/install-workflow.sh bakes the
// active skill dir into the installed copy (a runtime skill_dir arg wins).
// This script has NO filesystem/shell access of its own (runtime rule) —
// the probe agents below are the only seam that runs gate.sh and git, and
// every reviewer/triage/confirm/fix agent works the repo with its own tools.
//
// Dialect divergences from the zcode master (spec-code-review.dwf.ts), each
// forced by the one-shot agent model — behavior is otherwise identical:
//   - system prompts ride at the head of each one-shot ask;
//   - cross-lens dedup cannot ride a shared triage conversation, so triage
//     runs per lens (within-lens bar) plus one explicit cross-lens merge
//     pass before confirmation;
//   - the fixer is one-shot per round, so every round's ask embeds the full
//     finding detail instead of relying on conversation context;
//   - the final report returns as the `markdown` field (no artifact
//     primitive) and live finding events degrade to log() lines.
// ---------------------------------------------------------------------------

const TARGETS = ["diff", "branch", "pr", "project"];
const TARGET =
  typeof args !== "undefined" && args && typeof args.target === "string" && args.target.trim()
    ? args.target.trim().toLowerCase()
    : "diff";
const PROJECT = TARGET === "project";
const PR = TARGET === "pr";
const BRANCH_MODE = TARGET === "branch";
const PR_ARG =
  typeof args !== "undefined" && args && typeof args.pr === "string" && args.pr.trim()
    ? args.pr.trim()
    : "";
const HAS_BASE =
  typeof args !== "undefined" && args && typeof args.base === "string" && args.base.trim()
    ? true
    : false;
const BASE_ARG = HAS_BASE ? args.base.trim() : "";
// BASE starts at the diff default and is resolved in the scope phase:
// args.base in diff mode (default HEAD), the merge-base with the base
// branch in branch mode, the merge-base with the PR's base commit in
// pr mode — every diff-mode ask and the gate then work unchanged.
let BASE = HAS_BASE ? BASE_ARG : "HEAD";
const PATHS_ARG =
  typeof args !== "undefined" && args && typeof args.paths === "string" && args.paths.trim()
    ? args.paths.trim()
    : "";
const MODE =
  typeof args !== "undefined" && args && typeof args.mode === "string" && args.mode.trim()
    ? args.mode.trim().toLowerCase()
    : "auto";
const FIX_ROUNDS =
  typeof args !== "undefined" && args && typeof args.fix_rounds === "number" &&
  Number.isInteger(args.fix_rounds) && args.fix_rounds >= 0
    ? args.fix_rounds
    : 0;
const SKILL_DIR_BAKED = "__SKILL_DIR__";
const skillDir =
  typeof args !== "undefined" && args && typeof args.skill_dir === "string" && args.skill_dir
    ? args.skill_dir
    : SKILL_DIR_BAKED;
const FAST_MAX_LINES = 400;
const FAST_MAX_FILES = 5;
// Whole-project reviews read files, not diffs: the target list is the
// tracked source files, largest first, capped so a reviewer's turn can
// actually cover it. paths narrows the list on big repos.
const PROJECT_MAX_FILES = 30;
const SEV_RANK = { high: 0, medium: 1, low: 2 };

// Source-file targeting for project mode — same lists as the zcode
// master: an extension whitelist plus well-known build files, minus
// lockfiles, generated code and the common vendored/build directories.
const CODE_EXTENSIONS = [
  "bash", "c", "cc", "clj", "cljs", "cmake", "cpp", "cs", "css", "cxx", "dart",
  "d", "edn", "el", "elm", "erl", "ex", "exs", "fish", "go", "gradle", "groovy",
  "graphql", "h", "hh", "hpp", "hs", "html", "hrl", "java", "js", "json", "jsx",
  "kt", "kts", "less", "lua", "m", "ml", "mli", "mm", "nim", "php", "pl", "pm",
  "proto", "ps1", "py", "pyi", "r", "rb", "rs", "sass", "scala", "scss", "sh",
  "sql", "svelte", "swift", "tf", "toml", "ts", "tsx", "vue", "yaml", "yml",
  "zig", "zsh",
];
const CODE_BASENAMES = [
  "Makefile", "Dockerfile", "CMakeLists.txt", "Rakefile", "Gemfile",
  "Justfile", "Podfile", "Vagrantfile", "Brewfile",
];
const EXCLUDED_BASENAMES = [
  "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock",
  "poetry.lock", "Pipfile.lock", "uv.lock", "go.sum", "composer.lock",
  "Gemfile.lock",
];
const EXCLUDED_SEGMENTS = [
  "vendor/", "third_party/", "external/", "node_modules/", "dist/",
  "__snapshots__/", ".venv/", "venv/",
];

function isExcludedSource(path) {
  const base = path.slice(path.lastIndexOf("/") + 1);
  if (EXCLUDED_BASENAMES.indexOf(base) !== -1) return true;
  if (base.endsWith(".d.ts")) return true;
  if (base.endsWith(".min.js") || base.endsWith(".min.css")) return true;
  if (base.endsWith(".pb.go") || /_pb2\.py$/.test(base)) return true;
  for (const seg of EXCLUDED_SEGMENTS) {
    if (path.indexOf(seg) !== -1) return true;
  }
  return false;
}

function isSourceFile(path) {
  const base = path.slice(path.lastIndexOf("/") + 1);
  if (CODE_BASENAMES.indexOf(base) !== -1) return true;
  const dot = base.lastIndexOf(".");
  if (dot <= 0) return false; // no extension, or a dotfile — not source
  return CODE_EXTENSIONS.indexOf(base.slice(dot + 1).toLowerCase()) !== -1;
}

function matchesPathFilter(path, terms) {
  if (terms.length === 0) return true;
  for (const t of terms) {
    if (path === t || path.slice(0, t.length + 1) === t + "/") return true;
  }
  return false;
}

const HONESTY =
  " If your instructions are impossible to satisfy, escalate and say so plainly rather than working around it.";

const LENSES = [
  {
    label: "correctness",
    name: "Correctness reviewer",
    system:
      "You are the correctness reviewer on a code review panel. You read whole diffs, follow call sites, " +
      "and report only defects a reasonable author would fix: logic errors, broken edge cases, wrong or missing " +
      "error handling, concurrency hazards, contract violations between caller and callee. Never style, never " +
      "speculation, never pre-existing issues the change does not touch." + HONESTY,
    focus:
      "logic errors, broken edge cases, wrong or missing error handling, concurrency hazards, broken contracts between caller and callee.",
  },
  {
    label: "security",
    name: "Security reviewer",
    system:
      "You are the security reviewer on a code review panel. You read whole diffs and trace untrusted data from " +
      "where it enters to where it is used. You report only real, demonstrable vulnerabilities and exposure " +
      "changes a reasonable author would fix — not checklist theater, not speculation." + HONESTY,
    focus:
      "untrusted input paths, injection, secrets and token handling, unsafe deserialization, permission changes, destructive operations.",
  },
  {
    label: "quality",
    name: "Quality and tests reviewer",
    system:
      "You are the quality-and-tests reviewer on a code review panel. You read whole diffs and judge what the next " +
      "reader pays for. You report complexity that obscures, over-engineering, misleading names, comments and docs " +
      "that drift from the code, and test problems — changed behavior with no test covering it, tests that cannot " +
      "fail. Never pure style or formatting; the repo's checks own those." + HONESTY,
    focus:
      "complexity the next reader pays for, over-engineering, misleading names, comments and docs that drift from the code, and tests — behavior this change alters with no test covering it, tests that cannot fail.",
  },
];

const GENERAL = {
  label: "general",
  name: "General reviewer",
  system:
    "You are the sole reviewer on a small change. You combine three lenses — correctness (logic, edge cases, " +
    "error handling), security (untrusted input, secrets, permissions), and quality (complexity, tests that fail " +
    "to cover changed behavior) — and report only defects a reasonable author would fix. Never style, never " +
    "speculation, never pre-existing issues the change does not touch." + HONESTY,
  focus:
    "correctness (logic, edge cases, error handling), security (untrusted input, secrets, permissions), and quality (complexity, tests that fail to cover changed behavior).",
};

const TRIAGE_SYSTEM =
  "You are the triage editor of a code review panel. Reviewers hand you their raw findings lens by lens; you " +
  "dedupe across lenses, enforce the flagging bar (real, introduced by the change, actionable), and drop style " +
  "nits, speculation and pre-existing issues with a one-line reason. You are stingy but never suppress a real " +
  "defect to keep the count down.";

const FIXER_SYSTEM =
  "You are the author and fixer of this change. You receive confirmed review findings and fix them in the " +
  "working tree. Minimal, surgical fixes in the repo's own style — no refactors beyond what a finding requires. " +
  "Never commit. Never weaken, skip, or delete a test to make a finding go away; if a fix legitimately changes " +
  "behavior, pin the corrected behavior in the test. If a finding is wrong or cannot be fixed, say so in skipped " +
  "with why rather than pretending." + HONESTY;

const FIX_REVIEW_SYSTEM =
  "You are the fresh-eyes reviewer for an author's fixes. The author cannot see their own gaps; you can. You " +
  "read only the cumulative diff of the paths the author changed, and you report NEW defects those fixes " +
  "introduce — never the original findings, which separate verifiers own." + HONESTY;

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

const DROPPED_ITEM = {
  type: "object",
  properties: {
    where: { type: "string" },
    what: { type: "string" },
    reason: { type: "string" },
  },
  required: ["where", "what", "reason"],
  additionalProperties: false,
};

const TRIAGE_SCHEMA = {
  type: "object",
  properties: {
    kept: { type: "array", items: FINDING_ITEM },
    dropped: { type: "array", items: DROPPED_ITEM },
  },
  required: ["kept", "dropped"],
  additionalProperties: false,
};

// the cross-lens merge pass must carry each finding's lens back out
const TAGGED_FINDING_ITEM = {
  type: "object",
  properties: {
    where: { type: "string" },
    what: { type: "string" },
    evidence: { type: "string" },
    severity: { type: "string", enum: ["low", "medium", "high"] },
    lens: { type: "string" },
  },
  required: ["where", "what", "evidence", "severity", "lens"],
  additionalProperties: false,
};

const CROSS_TRIAGE_SCHEMA = {
  type: "object",
  properties: {
    kept: { type: "array", items: TAGGED_FINDING_ITEM },
    dropped: { type: "array", items: DROPPED_ITEM },
  },
  required: ["kept", "dropped"],
  additionalProperties: false,
};

const CONFIRM_SCHEMA = {
  type: "object",
  properties: {
    status: { type: "string", enum: ["verified", "unconfirmed"] },
    note: { type: "string" },
  },
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
        properties: { what: { type: "string" }, why: { type: "string" } },
        required: ["what", "why"],
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
  properties: {
    status: { type: "string", enum: ["fixed", "unfixed", "worse"] },
    note: { type: "string" },
  },
  required: ["status", "note"],
  additionalProperties: false,
};

// --- helpers ----------------------------------------------------------------

function outTail(s, n) {
  const t = s.trim();
  return t ? t.split("\n").slice(-n).join("\n") : "";
}

// one-shot agents have no system slot — the panel role rides at the head
function withSystem(systemText, task) {
  return systemText + "\n\n" + task;
}

// single-quote a shell word for the probe command lines (refs and paths
// carry user-controlled characters; never a raw interpolation)
function shq(s) {
  return "'" + String(s).replace(/'/g, "'\\''") + "'";
}

// ONE probe agent per shell need: runs the exact command and returns its
// combined stdout verbatim through a schema — the script's only seam to
// the shell (same pattern as spec-run.js's graph probe).
async function probe(label, command) {
  const r = await agent(
    "Run this exact shell command from the workspace root and return ONLY its " +
    "combined stdout verbatim in the stdout field (empty string if none). " +
    "Some commands run for minutes — wait for completion, never truncate:\n  " +
    command,
    { label: label, schema: PROBE_SCHEMA }
  );
  if (!r || typeof r.stdout !== "string") {
    log(label + ": probe returned no result");
    return null;
  }
  return r.stdout;
}

// The mechanical gate: the skill's gate.sh detects and runs the repo's
// OWN checks and reports a JSON array on stdout. Run once before the
// review and again after every fix round. Project mode passes --tree so
// the shell-syntax family scans every tracked script, not the diff.
async function runGate() {
  const gateArgs = PROJECT ? ["--tree"] : ["--base", BASE];
  const out = await probe(
    "gate-probe",
    "bash " + shq(skillDir + "/scripts/gate.sh") + " " +
    gateArgs.map(function (a) { return shq(a); }).join(" ")
  );
  if (out !== null) {
    try {
      const parsed = JSON.parse(out);
      if (Array.isArray(parsed)) {
        return parsed.map(function (g) {
          return {
            name: g.name,
            exitCode: typeof g.exit_code === "number" ? g.exit_code : 0,
            tail: g.tail,
          };
        });
      }
    } catch (e) {
      log("gate.sh stdout is not a JSON report: " + String(e));
    }
  }
  return [
    {
      name: "gate.sh (spec-code-review)",
      exitCode: 1,
      tail: outTail(out || "", 12) || "gate.sh produced no JSON report",
    },
  ];
}

function gateNote(gate) {
  if (gate.length === 0) {
    return "No repo checks were detected by the gate — this review has no mechanical floor; " +
      "the report must say so under notCovered";
  }
  return "The repo's own checks the gate detected (" + gate.map(function (g) { return g.name; }).join("; ") + ") all passed";
}

// Project-mode targeting: tracked files from git, sizes from wc, filtered
// to source, largest first, capped. Two probes — ls-files first guards
// the xargs/wc pipeline against an empty repo (xargs on empty input can
// still invoke wc, which would then wait on stdin).
async function selectProjectFiles() {
  const listed = await probe("target-probe", "git ls-files");
  if (listed === null) return null;
  const all = listed.split("\n").map(function (s) { return s.trim(); }).filter(Boolean);
  if (all.length === 0) return { files: [], candidates: 0 };
  const sizes = {};
  const wc = await probe(
    "target-size-probe",
    "git ls-files -z | xargs -0 wc -c"
  );
  if (wc !== null) {
    for (const line of wc.split("\n")) {
      const m = /^\s*(\d+)\s+(.+)$/.exec(line);
      if (m && m[2] !== "total") sizes[m[2]] = parseInt(m[1], 10);
    }
  }
  const terms = PATHS_ARG.split(/[\s,]+/).filter(Boolean);
  const candidates = all.filter(function (p) {
    return isSourceFile(p) && !isExcludedSource(p) && matchesPathFilter(p, terms);
  });
  const sorted = candidates.sort(function (a, b) {
    const d = (sizes[b] !== undefined ? sizes[b] : 0) - (sizes[a] !== undefined ? sizes[a] : 0);
    return d !== 0 ? d : (a < b ? -1 : a > b ? 1 : 0);
  });
  return { files: sorted.slice(0, PROJECT_MAX_FILES), candidates: candidates.length };
}

// change scope through ONE probe: porcelain status + numstat (numstat is
// compact enough that no diff-size cap can overflow it — reviewers page
// the real diff themselves with their own tools)
const SCOPE_SPLIT = "__SCOPE__";

async function gitScope() {
  const out = await probe(
    "scope-probe",
    "git status --porcelain && echo " + SCOPE_SPLIT + " && git diff --numstat " + shq(BASE)
  );
  if (out === null) return null;
  const parts = out.split(SCOPE_SPLIT);
  const porcelain = (parts[0] || "").trim();
  const numstat = parts.length > 1 ? parts[1] : "";
  const files = [];
  let added = 0;
  for (const line of numstat.split("\n")) {
    const cols = line.split("\t");
    if (cols.length < 3 || !cols[2].trim()) continue;
    files.push(cols.slice(2).join("\t").trim());
    const n = parseInt(cols[0], 10);
    if (!isNaN(n)) added += n;
  }
  return { clean: porcelain === "", files: files, added: added };
}

// --- pr and branch target resolution (probe dialect) -------------------------
// Both collapse to a diff review against a resolved base — the merge-base
// with the base branch — so the panel machinery, the gate and the fix loop
// run unchanged underneath. The panel and any fix loop work in the working
// tree, so pr mode requires the PR head to be checked out: on a clean tree
// the workflow checks it out itself (announced, with the previous HEAD in
// the log); on a dirty tree it refuses rather than hide uncommitted work.

function prMetaFromJson(raw) {
  let j;
  try {
    j = JSON.parse(raw);
  } catch (e) {
    return null;
  }
  if (!j || typeof j.headRefOid !== "string" || !j.headRefOid) return null;
  return {
    number: typeof j.number === "number" ? j.number : 0,
    title: typeof j.title === "string" ? j.title.replace(/\s+/g, " ").trim() : "",
    author: j.author && typeof j.author.login === "string" ? j.author.login : "unknown",
    state: typeof j.state === "string" ? j.state : "UNKNOWN",
    url: typeof j.url === "string" ? j.url : "",
    baseRefName: typeof j.baseRefName === "string" ? j.baseRefName : "",
    baseRefOid: typeof j.baseRefOid === "string" ? j.baseRefOid : "",
    headRefName: typeof j.headRefName === "string" ? j.headRefName : "",
    headRefOid: j.headRefOid,
  };
}

// pr metadata + head/dirty state + checkout + merge-base, each through one
// probe (the script's only seam to the shell). The base-branch probe folds
// base detection and the current branch name into one output separated by
// SCOPE_SPLIT: parts[0] is the resolved base ref (possibly empty), parts[1]
// the current branch name.
async function probePrMeta() {
  const out = await probe(
    "pr-meta-probe",
    "gh pr view " + shq(PR_ARG) + " --json number,title,author,baseRefName,baseRefOid,headRefName,headRefOid,state,url"
  );
  return out !== null ? prMetaFromJson(out) : null;
}

async function probeHeadState() {
  const out = await probe(
    "pr-head-probe",
    "git rev-parse HEAD && echo " + SCOPE_SPLIT + " && git status --porcelain"
  );
  if (out === null) return null;
  const parts = out.split(SCOPE_SPLIT);
  return {
    head: (parts[0] || "").trim(),
    dirty: (parts.length > 1 ? parts[1] : "").trim() !== "",
  };
}

async function probeCheckoutPr() {
  const out = await probe(
    "pr-checkout-probe",
    "gh pr checkout " + shq(PR_ARG) + " && git rev-parse HEAD"
  );
  return out !== null ? out.trim() : "";
}

async function probeMergeBase(ref) {
  const out = await probe("merge-base-probe", "git merge-base HEAD " + shq(ref));
  return out !== null ? out.trim() : "";
}

// merge-base + commit count in one probe: parts[0] the merge-base sha,
// parts[1] the commit count on the branch side.
async function probeMergeBaseWithCount(ref) {
  const out = await probe(
    "merge-base-probe",
    "mb=$(git merge-base HEAD " + shq(ref) + ') && printf "%s" "$mb" && echo ' + SCOPE_SPLIT +
    ' && git rev-list --count "$mb..HEAD"'
  );
  if (out === null) return null;
  const parts = out.split(SCOPE_SPLIT);
  const sha = (parts[0] || "").trim();
  if (!sha) return null;
  const count = parseInt((parts.length > 1 ? parts[1] : "").trim(), 10);
  return { sha: sha, count: isNaN(count) ? 0 : count };
}

// base-branch detection, one probe: explicit base first (remote form, then
// local), else the remote's default branch (origin/HEAD dereferenced to the
// branch it points at), else main/master — local or remote — first
// resolvable wins. An empty first part means nothing resolved.
async function probeBaseBranchAndName() {
  const candidates = HAS_BASE
    ? [shq("origin/" + BASE_ARG), shq(BASE_ARG)]
    : ['"$h"', shq("origin/main"), shq("main"), shq("origin/master"), shq("master")];
  const cmd =
    "h=$(git symbolic-ref -q --short refs/remotes/origin/HEAD || true); " +
    "for r in " + candidates.join(" ") + '; do [ -n "$r" ] || continue; ' +
    'if git rev-parse -q --verify "$r" >/dev/null 2>&1; then printf "%s" "$r"; break; fi; done; ' +
    "echo " + SCOPE_SPLIT + '; bn=$(git branch --show-current || true); printf "%s" "$bn"';
  const out = await probe("base-ref-probe", cmd);
  if (out === null) return null;
  const parts = out.split(SCOPE_SPLIT);
  return {
    baseRef: (parts[0] || "").trim(),
    branchName: (parts.length > 1 ? parts[1] : "").trim() || "(detached HEAD)",
  };
}

// --- asks (verbatim from the zcode master unless a one-shot divergence
// is called out in the header) ----------------------------------------------

function reviewAsk(lensDef, files, lines, overCap, gateLine) {
  const scope =
    "`git diff " + BASE + "` — " + files + " files, ~" + lines + " added lines" +
    (overCap ? " (diff over the harness size cap — page through it with git diff directly)" : "");
  return (
    "Review the change " + scope + " in this repository.\n" +
    "1. Run `git diff " + BASE + "` and read the FULL diff — do not stop at the first issue. Open the changed " +
    "files for context wherever the diff alone is ambiguous; check call sites when a defect depends on them.\n" +
    "2. If AGENTS.md or CLAUDE.md exists at the repo root, read it first and cite any rule a finding violates.\n" +
    "3. Report only findings from your lens: " + lensDef.focus + "\n" +
    "A finding must be: discrete and actionable; introduced by this change; demonstrable from the code (quote the " +
    "deciding lines in evidence); something the author would reasonably fix. Exclude: speculative might-fail " +
    "concerns, pre-existing problems the change does not worsen, style/formatting (the repo's checks own those), " +
    "and intentional behavior changes.\n" +
    "Cite every finding as path:line on the new side of the diff. An empty findings list is the expected answer " +
    "for a clean diff — never invent one to seem busy.\n" +
    "Do not edit any file. " + gateLine + " before you started, so do not re-run the " +
    "test suites; spend your turn on what only a reader can see."
  );
}

// Project mode: there is no diff — the reviewers read the target files
// from the tree, and the bar is "present in the code as it stands".
function reviewAskProject(lensDef, files, candidates, overCap, gateLine) {
  const scope =
    files.length + " files" + (overCap
      ? " (the largest " + files.length + " of " + candidates + " tracked source files — anything left out is a coverage gap the report must name)"
      : "");
  return (
    "Review the current state of this project's code. There is no diff — the target is the file list below, " +
    scope + ", sorted by size:\n" +
    files.map(function (f) { return "- " + f; }).join("\n") + "\n" +
    "1. Read EVERY target file in full — do not stop at the first issue. Check call sites outside the list " +
    "whenever a defect depends on them.\n" +
    "2. If AGENTS.md or CLAUDE.md exists at the repo root, read it first and cite any rule a finding violates.\n" +
    "3. Report only findings from your lens: " + lensDef.focus + "\n" +
    "A finding must be: discrete and actionable; present in the code as it stands; demonstrable from the code " +
    "(quote the deciding lines in evidence); something the author would reasonably fix. Exclude: speculative " +
    "might-fail concerns, style/formatting (the repo's checks own those), and deliberate design choices the " +
    "team has clearly signed off on.\n" +
    "Cite every finding as path:line in the current tree. An empty findings list is the expected answer " +
    "for clean code — never invent one to seem busy.\n" +
    "Do not edit any file. " + gateLine + " before you started, so do not re-run the " +
    "test suites; spend your turn on what only a reader can see."
  );
}

function triageAsk(lensLabel, review) {
  return (
    "Raw findings from the " + lensLabel + " reviewer for the change under review (`git diff " + BASE + "`):\n" +
    JSON.stringify(review.findings, null, 2) +
    "\nYou are the triage editor. For each finding, keep it or drop it. Keep = it meets the bar — real, " +
    "introduced by this change, actionable, worth the author's attention. Drop = a duplicate of another finding " +
    "in this same list, a style nit, speculation, or a pre-existing issue. Never drop something " +
    "merely because it is inconvenient, and never keep what the repo's own checks already decide (they all " +
    "passed). Give every dropped item a one-line reason."
  );
}

// Project mode: the bar is presence in the target, not introduction by a change.
function triageAskProject(lensLabel, review) {
  return (
    "Raw findings from the " + lensLabel + " reviewer for the project code under review:\n" +
    JSON.stringify(review.findings, null, 2) +
    "\nYou are the triage editor. For each finding, keep it or drop it. Keep = it meets the bar — real, " +
    "present in the code as it stands, actionable, worth the author's attention. Drop = a duplicate of a finding " +
    "you have already kept from another lens, a style nit, or speculation. Never drop something merely because " +
    "it is inconvenient, and never keep what the repo's own checks already decide (they all passed). Give every " +
    "dropped item a one-line reason."
  );
}

// the one-shot replacement for the zcode triage agent's shared conversation:
// one final pass that sees every lens's kept findings and dedupes across them
function crossLensAsk(kept) {
  return (
    "Kept findings from every lens after per-lens triage (change: `git diff " + BASE + "`):\n" +
    JSON.stringify(kept, null, 2) +
    "\nYou are the triage editor making the final cross-lens pass. Drop a finding ONLY if it duplicates another " +
    "kept finding — the same underlying defect reported twice. When two entries describe one defect, keep the " +
    "more precise one and drop the other with a reason naming its twin. Never drop anything else here; " +
    "per-lens triage already enforced the flagging bar. Return the kept findings with their lens field intact."
  );
}

function confirmAsk(f) {
  return (
    "You are an independent confirmer. A reviewer reported this finding on the change `git diff " + BASE + "`:\n" +
    JSON.stringify(f, null, 2) +
    "\nVerify it from the code alone. Read the file at that location; confirm the cited lines exist and the claim " +
    "holds; confirm this change introduced it (`git diff " + BASE + " -- <path>` covers those lines). Check a " +
    "call site if the claim depends on one. Do not edit anything, and do not re-run the repo's test suites.\n" +
    "If the claim holds and the change introduced it, answer verified. If you cannot reproduce it, or it predates " +
    "the change, answer unconfirmed and say what you saw instead."
  );
}

function confirmAskProject(f) {
  return (
    "You are an independent confirmer. A reviewer reported this finding in the project's code:\n" +
    JSON.stringify(f, null, 2) +
    "\nVerify it from the code alone. Read the file at that location; confirm the cited lines exist and the " +
    "claim holds. Check a call site if the claim depends on one. Do not edit anything, and do not re-run the " +
    "repo's test suites.\n" +
    "If the claim holds, answer verified. If you cannot reproduce it, answer unconfirmed and say what you saw " +
    "instead."
  );
}

function finalAsk(summary, gateLine) {
  return (
    "Every kept finding has now been through independent confirmation:\n" +
    JSON.stringify(summary, null, 2) +
    "\n" + gateLine + " before review started. Produce the final assessment of this change. Run `git diff " + BASE +
    "` yourself wherever you need to judge it, and read the test files before claiming a test gap.\n" +
    "risk: low | medium | high — what merging this change as-is would risk. testGaps: behaviors this change " +
    "alters that no test covers (empty if none). residualRisks: what remains unverified after the checks and " +
    "the review. verdict: two or three sentences — should this merge, and what must the author fix first."
  );
}

function finalAskProject(summary, gateLine, files) {
  return (
    "Every kept finding has now been through independent confirmation:\n" +
    JSON.stringify(summary, null, 2) +
    "\n" + gateLine + " before review started. Produce the final assessment of the project's code. Read the " +
    "target files yourself wherever you need to judge them (" + files.slice(0, 10).join(", ") +
    (files.length > 10 ? ", ..." : "") + "), and read the test files before claiming a test gap.\n" +
    "risk: low | medium | high — the risk in the code as it stands. testGaps: behaviors with no test covering " +
    "them (empty if none). residualRisks: what remains unverified after the checks and the review. verdict: two " +
    "or three sentences — is the code ready as it stands, and what must be fixed first."
  );
}

function fixerAsk(round, unresolved, gateFeedback) {
  if (round === 1) {
    const opening = PROJECT
      ? "Fix the confirmed findings in the project's code:\n"
      : "Fix the confirmed findings on the change (`git diff " + BASE + "`):\n";
    return (
      opening +
      JSON.stringify(
        unresolved.map(function (t) {
          return {
            where: t.finding.where,
            what: t.finding.what,
            evidence: t.finding.evidence,
            severity: t.finding.severity,
            lens: t.finding.lens,
          };
        }),
        null,
        2,
      ) +
      "\nWork in the working tree; never commit. You may run a single targeted test file for code you touch, " +
      "but the repo's checks re-run the moment you finish — do not run them yourself.\n" +
      "Return addressed (the what-strings you fully fixed), skipped (what you deliberately left, with why), " +
      "changedPaths, and notes (one sentence per change: what was done and why it is minimal)."
    );
  }
  return (
    "Round " + round + ". These findings are still unresolved after the previous round — the independent " +
    "verifiers said, per item:\n" +
    JSON.stringify(
      unresolved.map(function (t) {
        return {
          where: t.finding.where,
          what: t.finding.what,
          evidence: t.finding.evidence,
          severity: t.finding.severity,
          lens: t.finding.lens,
          verifier: t.fixNote,
        };
      }),
      null,
      2,
    ) +
    (gateFeedback
      ? "\nThe repo's own checks are currently FAILING after the last round:\n" + gateFeedback
      : "\nThe repo's own checks passed after the last round.") +
    "\nEach finding above carries its full detail. Fix exactly these, same rules as before: minimal, in the " +
    "repo's style, never commit, never weaken a test to make a finding go away."
  );
}

function verifyAsk(t, notes) {
  return (
    "A reviewer confirmed this finding " + (PROJECT ? "in the project's code" : "on the change (`git diff " + BASE + "`)") +
    ", and the author has since attempted a fix.\n" +
    "Finding: " + JSON.stringify({ where: t.finding.where, what: t.finding.what, severity: t.finding.severity, lens: t.finding.lens }) +
    "\nAuthor's notes: " + (notes || "(none)") +
    "\nVerify in the CURRENT working tree: read the location and its immediate callers or contract; confirm " +
    "the described defect is gone and the fix is minimal and sound.\n" +
    "Answer fixed only if the defect itself is resolved — cosmetic proximity is not a fix. Answer unfixed if " +
    "it still stands. Answer worse if the fix introduced a new problem (say what, in note). Do not edit anything."
  );
}

function fixReviewAsk(paths, gateGreen) {
  return (
    "The author fixed review findings by changing:\n" +
    paths.map(function (p) { return "- " + p; }).join("\n") +
    "\nRead the cumulative diff for exactly these paths (`git diff " + BASE + " -- <path>`, one per path) and " +
    "the current file contents where context matters. Judge the fix code as a fresh reviewer on a new change: " +
    "report only NEW defects these fixes introduce — the same bar as the panel (real, introduced by these " +
    "fixes, demonstrable from the code, the author would fix). Do not re-report the original findings; " +
    "separate verifiers own those.\n" +
    "An empty findings list is the expected answer for clean fixes. Do not edit anything; the repo's own " +
    "checks " + (gateGreen ? "all passed" : "are currently failing") + " after the fixes."
  );
}

function loopFinalAsk(tracked, roundsUsed, gateGreen, changedPaths) {
  return (
    "The fix loop ran " + roundsUsed + " round(s). Every tracked finding and its state:\n" +
    JSON.stringify(
      tracked.map(function (t) {
        return {
          where: t.finding.where,
          what: t.finding.what,
          severity: t.finding.severity,
          lens: t.finding.lens,
          reviewStatus: t.finding.confirmation.status,
          fix: t.fix,
          fixNote: t.fixNote,
        };
      }),
      null,
      2,
    ) +
    "\nThe repo's own checks after the final round: " + (gateGreen ? "all passed" : "FAILING (see lens 'gate' items)") +
    ".\nAll paths the author changed: " + (changedPaths.join(", ") || "(none)") +
    (PROJECT
      ? "\nProduce the final assessment of the project's code INCLUDING the fixes — read the target files " +
        "yourself where you need to judge them, and read the test files before claiming a test gap.\n" +
        "risk: the risk in the code as it stands. testGaps: behaviors still without any test covering them. " +
        "residualRisks: what remains unverified. verdict: two or three sentences — is the code ready as it " +
        "stands now? recommendation: merge | fix-first | human — merge means the code is ready as it stands " +
        "(every finding fixed, the checks green, nothing new surfaced); human when judgment calls or " +
        "unconfirmed residue remain."
      : "\nProduce the final assessment of the change INCLUDING the fixes — run `git diff " + BASE + "` yourself " +
        "where you need to judge it, and read the test files before claiming a test gap.\n" +
        "risk: what merging now would risk. testGaps: behaviors still altered with no test covering them. " +
        "residualRisks: what remains unverified. verdict: two or three sentences — should this merge now? " +
        "recommendation: merge | fix-first | human — merge only if every finding is fixed, the checks are green, " +
        "and nothing new surfaced; human when judgment calls or unconfirmed residue remain.")
  );
}

function findingsMd(items) {
  const lines = [];
  for (const f of items) {
    lines.push(
      "### [" + f.severity.toUpperCase() + " · " + f.status + " · " + f.lens +
      (f.fixStatus === "pending" ? "" : " · fix: " + f.fixStatus) + "] " + f.what,
    );
    lines.push("- where: `" + f.where + "`");
    lines.push("- evidence: " + f.evidence);
    lines.push("");
  }
  return lines;
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
  phase("Scope the change and run the repo's checks");

  let targetFiles = [];
  let targetCandidates = 0;
  let targetOverCap = false;
  let changed = [];
  let addedLines = 0;
  const diffOverCap = false; // numstat cannot overflow; kept for ask parity
  let prMeta = null;
  let branchBaseRef = "";
  let branchName = "";
  let commitCount = 0;

  function failReturn(conclusion, notCovered, mdTitle, mdBody) {
    return {
      conclusion: conclusion,
      findings: [],
      verified: [],
      notCovered: notCovered,
      title: mdTitle,
      markdown: mdBody,
    };
  }

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

  if (PR) {
    const meta = await probePrMeta();
    if (!meta || !meta.baseRefOid) {
      return failReturn(
        "gh pr view failed for \"" + PR_ARG + "\" — is the gh CLI installed and authenticated, " +
        "and is that a valid pull request in this repo's remote?",
        ["the pull request — gh pr view returned nothing usable"],
        "Code review — PR unknown",
        "# Code review — PR unknown\n\ngh pr view returned nothing usable; nothing was reviewed.\n",
      );
    }
    prMeta = meta;
    const headState = await probeHeadState();
    if (headState === null || !headState.head) {
      return failReturn(
        "The review cannot see the git state (rev-parse/status probe returned nothing) — rerun the workflow.",
        ["the pull request — git state probe failed"],
        "Code review — state unknown",
        "# Code review — state unknown\n\nThe git state probe returned nothing; nothing was reviewed.\n",
      );
    }
    if (headState.head !== meta.headRefOid) {
      if (headState.dirty) {
        return failReturn(
          "PR #" + meta.number + " is not checked out and the working tree is dirty — the panel " +
          "reads the working tree, so checking out would hide uncommitted work. Commit or stash, then rerun; " +
          "on a clean tree the review checks the PR out itself.",
          ["the pull request — head not checked out, refused to touch a dirty working tree"],
          "Code review — PR not checked out",
          "# Code review — PR not checked out\n\nThe working tree is dirty and the PR head is not checked out; nothing was reviewed.\n",
        );
      }
      const prev = headState.head || "(unknown)";
      const head2 = await probeCheckoutPr();
      if (head2 !== meta.headRefOid) {
        return failReturn(
          "Could not check out PR #" + meta.number + " (gh pr checkout failed, or HEAD does not " +
          "match the PR head afterward) — check the PR out manually and rerun.",
          ["the pull request — automatic checkout failed"],
          "Code review — PR checkout failed",
          "# Code review — PR checkout failed\n\nAutomatic checkout failed; nothing was reviewed.\n",
        );
      }
      log("checked out PR #" + meta.number + " (previous HEAD " + prev.slice(0, 12) +
        ") — switch back when done reviewing");
    }
    const mbSha = await probeMergeBase(meta.baseRefOid);
    if (!mbSha) {
      return failReturn(
        "No common ancestor between HEAD and the PR's base commit (" + meta.baseRefOid.slice(0, 12) +
        ") — cannot compute the PR diff.",
        ["the pull request — merge-base with the base commit failed"],
        "Code review — PR diff unknown",
        "# Code review — PR diff unknown\n\nNo common ancestor with the PR's base commit; nothing was reviewed.\n",
      );
    }
    BASE = mbSha;
    log("review target: PR #" + meta.number + " " + meta.title + " (" + meta.state + ", by " + meta.author +
      ", base " + meta.baseRefName + ") — diff vs merge-base " + BASE.slice(0, 12));
  } else if (BRANCH_MODE) {
    const detected = await probeBaseBranchAndName();
    if (detected === null) {
      return failReturn(
        "The base-branch probe returned no result — the branch review cannot resolve its base. Rerun the workflow.",
        ["the branch review — base-branch probe failed"],
        "Code review — base unknown",
        "# Code review — base unknown\n\nThe base-branch probe returned nothing; nothing was reviewed.\n",
      );
    }
    branchName = detected.branchName;
    branchBaseRef = detected.baseRef;
    if (!branchBaseRef) {
      return failReturn(
        "Could not detect a base branch for the branch review — pass base explicitly (e.g. base: \"main\").",
        ["the branch review — no base branch resolved"],
        "Code review — base unknown",
        "# Code review — base unknown\n\nNo base branch resolved; nothing was reviewed.\n",
      );
    }
    const mb = await probeMergeBaseWithCount(branchBaseRef);
    if (mb === null) {
      return failReturn(
        "No common ancestor between HEAD and " + branchBaseRef + " — cannot compute the branch diff.",
        ["the branch review — merge-base with " + branchBaseRef + " failed"],
        "Code review — branch diff unknown",
        "# Code review — branch diff unknown\n\nNo common ancestor with " + branchBaseRef + "; nothing was reviewed.\n",
      );
    }
    BASE = mb.sha;
    commitCount = mb.count;
    log("review target: branch " + branchName + " vs " + branchBaseRef + " — merge-base " + BASE.slice(0, 12) +
      ", " + commitCount + " commit(s)");
  }

  if (PROJECT) {
    const sel = await selectProjectFiles();
    if (sel === null) {
      return {
        conclusion: "The target probe returned no result — the review cannot see the project's files. Rerun the workflow.",
        findings: [],
        verified: [],
        notCovered: ["the project file listing — the target probe failed"],
        title: "Code review — target unknown",
        markdown: "# Code review — target unknown\n\nThe project file probe returned nothing; nothing was reviewed.\n",
      };
    }
    targetFiles = sel.files;
    targetCandidates = sel.candidates;
    targetOverCap = targetCandidates > targetFiles.length;
    log(
      "review target: project — " + targetFiles.length + " of " + targetCandidates + " tracked source files" +
      (PATHS_ARG ? " (paths filter: " + PATHS_ARG + ")" : "") +
      (targetOverCap ? " — capped at " + PROJECT_MAX_FILES + ", largest first" : "")
    );
    if (targetFiles.length === 0) {
      return {
        conclusion: "No tracked source files matched the project target" +
          (PATHS_ARG ? " (paths filter: " + PATHS_ARG + ")" : "") + " — nothing to review.",
        findings: [],
        verified: ["project target: no tracked source files matched"],
        notCovered: [],
        title: "Code review — nothing to review",
        markdown: "# Code review — nothing to review\n\nNo tracked source files matched the target filter.\n",
      };
    }
  } else {
    const scope = await gitScope();
    if (scope === null) {
      return {
        conclusion: "The scope probe returned no result — the review cannot see the change. Rerun the workflow.",
        findings: [],
        verified: [],
        notCovered: ["the change scope — the git scope probe failed"],
        title: "Code review — scope unknown",
        markdown: "# Code review — scope unknown\n\nThe git scope probe returned nothing; nothing was reviewed.\n",
      };
    }
    changed = scope.files;
    addedLines = scope.added;
    log(
      "change under review: " +
      (PR ? "PR #" + prMeta.number + " (diff vs merge-base " + BASE.slice(0, 12) + ")"
        : BRANCH_MODE ? "branch " + branchName + " (diff vs merge-base " + BASE.slice(0, 12) + ")"
        : "git diff " + BASE) +
      " — " + changed.length + " files, ~" + addedLines + " added lines" +
      (scope.clean ? " (clean tree)" : " (uncommitted work present)")
    );

    if (changed.length === 0) {
      const nothing =
        PR
          ? "PR #" + prMeta.number + " has no changes against " + prMeta.baseRefName + " — nothing to review."
          : BRANCH_MODE
            ? "Branch " + branchName + " has no changes against " + branchBaseRef + " — nothing to review."
            : "No changes against " + BASE + " — nothing to review.";
      return {
        conclusion: nothing,
        findings: [],
        verified: ["change scope: the review target resolved to an empty diff"],
        notCovered: [],
        title: "Code review — nothing to review",
        markdown: "# Code review — nothing to review\n\n" + nothing + "\n",
      };
    }
  }

  const gate = await runGate();
  const GATE_LINE = gateNote(gate);
  const gateFailed = gate.filter(function (g) { return g.exitCode !== 0; });
  log("repo checks: " + (gate.length - gateFailed.length) + "/" + gate.length + " detected and run");

  if (gateFailed.length > 0) {
    const gateFindings = gateFailed.map(function (g) {
      return {
        where: g.name,
        what: "Repo check failed: " + g.name,
        evidence: g.tail || "(no output)",
        status: "verified",
        severity: "high",
        lens: "gate",
        fixStatus: "pending",
      };
    });
    const gateMd = [
      "# Code review — checks failed, review stopped",
      "",
      PROJECT
        ? "The project (" + targetFiles.length + " target files) failed the repo's own checks, so the "
        : PR
          ? "PR #" + prMeta.number + " (" + changed.length + " files) failed the repo's own checks, so the "
          : BRANCH_MODE
            ? "Branch " + branchName + " (" + changed.length + " files) failed the repo's own checks, so the "
            : "The change (`git diff " + BASE + "` — " + changed.length + " files) failed the repo's own checks, so the ",
      "specialist reviewers were not spent on it. Fix these first, then rerun the review.",
      "",
      "## Failed checks",
      "",
    ].concat(
      gate.map(function (g) {
        return "- " + (g.exitCode === 0 ? "pass" : "**FAIL**") + " — " + g.name +
          (g.exitCode === 0 ? "" : "\n\n  ```\n  " + g.tail + "\n  ```");
      })
    ).join("\n");
    return {
      conclusion:
        (PROJECT ? "The project" : PR ? "PR #" + prMeta.number : BRANCH_MODE ? "Branch " + branchName : "The change") +
        " failed " + gateFailed.length + " of " + gate.length +
        " detected repo checks (" + gateFailed.map(function (g) { return g.name; }).join("; ") + "). Specialist review was skipped — " +
        "these are mechanical fixes; rerun the review after they pass.",
      findings: gateFindings,
      verified: ["the mechanical gate ran the repo's own detected checks — " + gateFailed.length + " failed"],
      notCovered: [
        PROJECT
          ? "specialist review of the project code — skipped because the mechanical gate failed"
          : "specialist review of the diff — skipped because the mechanical gate failed",
      ],
      title: "Code review — checks failed",
      markdown: gateMd,
    };
  }

  phase("Review the change through separate lenses and confirm every finding");

  let modeUsed;
  if (MODE === "fast" || MODE === "full") {
    modeUsed = MODE;
  } else {
    modeUsed = PROJECT
      ? (targetFiles.length <= FAST_MAX_FILES ? "fast" : "full")
      : (addedLines <= FAST_MAX_LINES && changed.length <= FAST_MAX_FILES ? "fast" : "full");
  }
  const panel = modeUsed === "fast" ? [GENERAL] : LENSES;
  log("review mode: " + modeUsed + (modeUsed === "fast" ? " (small diff, one general reviewer)" : " (three specialists)"));

  async function runLens(lensDef) {
    const askText = PROJECT
      ? reviewAskProject(lensDef, targetFiles, targetCandidates, targetOverCap, GATE_LINE)
      : reviewAsk(lensDef, changed.length, addedLines, diffOverCap, GATE_LINE);
    const review = await agent(
      withSystem(lensDef.system, askText),
      { label: lensDef.label + "-review", schema: LENS_SCHEMA }
    );
    if (!review) {
      return { lens: lensDef.label, failed: true, kept: [], dropped: [] };
    }
    log(lensDef.name + ": " + review.findings.length + " finding(s)");
    if (review.findings.length === 0) {
      return { lens: lensDef.label, kept: [], dropped: [] };
    }
    const triaged = await agent(
      withSystem(TRIAGE_SYSTEM, PROJECT ? triageAskProject(lensDef.label, review) : triageAsk(lensDef.label, review)),
      { label: lensDef.label + "-triage", schema: TRIAGE_SCHEMA }
    );
    if (!triaged) {
      // never suppress a possible defect because triage died: the raw
      // findings pass through, and confirmation still judges each one
      log(lensDef.label + ": triage returned no result — raw findings pass through");
      return {
        lens: lensDef.label,
        kept: review.findings.map(function (f) { return { finding: f, lens: lensDef.label }; }),
        dropped: [],
        triageFailed: true,
      };
    }
    return {
      lens: lensDef.label,
      kept: triaged.kept.map(function (f) { return { finding: f, lens: lensDef.label }; }),
      dropped: triaged.dropped,
    };
  }

  const perLens = (await pipeline(panel, runLens)).filter(function (p) { return p; });
  const lensFailures = perLens.filter(function (r) { return r.failed; });
  for (const f of lensFailures) log("lens failed: " + f.lens + " reviewer returned no result");

  let keptAll = perLens.reduce(function (a, r) { return a.concat(r.kept); }, []);
  let allDropped = perLens.reduce(function (a, r) { return a.concat(r.dropped); }, []);

  // cross-lens merge: the one-shot replacement for the shared triage
  // conversation (never suppress on failure — keep everything kept so far)
  if (keptAll.length > 1) {
    const cross = await agent(
      withSystem(TRIAGE_SYSTEM, crossLensAsk(keptAll)),
      { label: "cross-lens-merge", schema: CROSS_TRIAGE_SCHEMA }
    );
    if (cross) {
      keptAll = cross.kept.map(function (f) { return { finding: f, lens: f.lens }; });
      allDropped = allDropped.concat(cross.dropped);
    } else {
      log("cross-lens merge returned no result — per-lens kept findings all proceed to confirmation");
    }
  }

  const confirmations = await pipeline(
    keptAll,
    function (kf) { return agent(PROJECT ? confirmAskProject(kf.finding) : confirmAsk(kf.finding), { label: "confirm-" + kf.lens, schema: CONFIRM_SCHEMA }); }
  );
  const allConfirmed = [];
  for (let i = 0; i < keptAll.length; i++) {
    const c = confirmations[i];
    const confirmation = c
      ? c
      : { status: "unconfirmed", note: "no confirmation result — the confirmer returned nothing; treat as unverified" };
    if (!c) log("confirm " + keptAll[i].finding.where + ": no result");
    allConfirmed.push({
      where: keptAll[i].finding.where,
      what: keptAll[i].finding.what,
      evidence: keptAll[i].finding.evidence,
      severity: keptAll[i].finding.severity,
      lens: keptAll[i].lens,
      confirmation: confirmation,
    });
  }
  allConfirmed.sort(function (a, b) {
    return (SEV_RANK[a.severity] !== undefined ? SEV_RANK[a.severity] : 3) -
           (SEV_RANK[b.severity] !== undefined ? SEV_RANK[b.severity] : 3);
  });
  const summary = allConfirmed.map(function (c) {
    return { where: c.where, what: c.what, severity: c.severity, lens: c.lens, status: c.confirmation.status };
  });

  // -------------------------------------------------------------------------
  // The fix loop: the author fixes, independent verifiers check every fix,
  // the gate re-runs, fresh eyes scan the fix diff. Bounded by rounds.
  const tracked = allConfirmed.map(function (f) {
    return { finding: f, fix: "pending", fixNote: "not yet attempted" };
  });
  let roundsUsed = 0;
  let gateGreen = true;
  const fixerNotes = [];
  const allChangedPaths = [];
  let fixerAborted = false;

  if (FIX_ROUNDS > 0 && allConfirmed.length > 0) {
    phase("Fix the confirmed findings and verify every fix");
    let gateFeedback = "";

    for (let round = 1; round <= FIX_ROUNDS; round++) {
      const unresolved = tracked.filter(function (t) { return t.fix !== "fixed"; });
      if (unresolved.length === 0) {
        break;
      }
      const outcome = await agent(
        withSystem(FIXER_SYSTEM, fixerAsk(round, unresolved, gateFeedback)),
        { label: "fixer-round-" + round, schema: FIX_SCHEMA }
      );
      if (!outcome) {
        log("fix round " + round + ": the fixer returned no result — loop aborted");
        fixerAborted = true;
        break;
      }
      roundsUsed = round;
      for (const n of outcome.notes) fixerNotes.push("round " + round + ": " + n);
      for (const p of outcome.changedPaths) if (allChangedPaths.indexOf(p) === -1) allChangedPaths.push(p);
      log(
        "fix round " + round + ": " + outcome.addressed.length + " addressed · " + outcome.skipped.length +
        " skipped · " + outcome.changedPaths.length + " path(s) changed"
      );

      const roundGate = await runGate();
      const gateBad = roundGate.filter(function (g) { return g.exitCode !== 0; });
      gateGreen = gateBad.length === 0;
      gateFeedback = gateBad.map(function (g) { return g.name + ":\n" + g.tail; }).join("\n\n");
      log("checks after round " + round + ": " + (roundGate.length - gateBad.length) + "/" + roundGate.length + " passed");

      // gate failures are tracked like findings: the fixer must clear them next round
      for (let i = tracked.length - 1; i >= 0; i--) {
        if (tracked[i].finding.lens === "gate") tracked.splice(i, 1);
      }
      for (const g of gateBad) {
        tracked.push({
          finding: {
            where: g.name,
            what: "Repo check failed after the fixes: " + g.name,
            evidence: g.tail || "(no output)",
            severity: "high",
            lens: "gate",
            confirmation: { status: "verified", note: "exit code nonzero after fix round " + round },
          },
          fix: "unfixed",
          fixNote: "round " + round + ": check failing",
        });
        log("gate finding (round " + round + "): " + g.name + " failing");
      }

      // A reader cannot verify a check name: gate-lens entries in the stale
      // pre-fixer snapshot were replaced above by the fresh authoritative
      // gate re-run, so the verify wave covers code findings only.
      const verifiable = unresolved.filter(function (t) { return t.finding.lens !== "gate"; });
      const verifications = await pipeline(
        verifiable,
        function (t) {
          return agent(verifyAsk(t, outcome.notes.join(" | ")), { label: "verify-round-" + round, schema: VERIFY_SCHEMA });
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
        const fixReview = await agent(
          withSystem(FIX_REVIEW_SYSTEM, fixReviewAsk(outcome.changedPaths, gateGreen)),
          { label: "fix-review-round-" + round, schema: LENS_SCHEMA }
        );
        if (fixReview && fixReview.findings.length > 0) {
          const triagedFix = await agent(
            withSystem(TRIAGE_SYSTEM, triageAsk("fix-review", fixReview)),
            { label: "fix-review-triage-" + round, schema: TRIAGE_SCHEMA }
          );
          const fixKept = triagedFix
            ? triagedFix.kept
            : fixReview.findings; // triage died: never suppress possible new defects
          const fixConfs = await pipeline(
            fixKept,
            function (f) { return agent(confirmAsk(f), { label: "confirm-fix-review-" + round, schema: CONFIRM_SCHEMA }); }
          );
          for (let i = 0; i < fixKept.length; i++) {
            const fc = fixConfs[i];
            tracked.push({
              finding: {
                where: fixKept[i].where,
                what: fixKept[i].what,
                evidence: fixKept[i].evidence,
                severity: fixKept[i].severity,
                lens: "fix-review",
                confirmation: fc
                  ? fc
                  : { status: "unconfirmed", note: "no confirmation result — the confirmer returned nothing" },
              },
              fix: "pending",
              fixNote: "new from fix review, round " + round,
            });
          }
        } else if (!fixReview) {
          log("fix review round " + round + ": reviewer returned no result");
        }
      }

      if (tracked.every(function (t) { return t.fix === "fixed"; })) {
        break;
      }
    }
  }

  phase("Synthesize the final review report");

  let finalAdded = addedLines;
  let finalChangedN = changed.length;
  if (PROJECT) {
    finalChangedN = targetFiles.length;
    finalAdded = 0;
  } else if (roundsUsed > 0) {
    const again = await gitScope();
    if (again !== null) {
      finalAdded = again.added;
      finalChangedN = again.files.length;
    }
  }

  const nVerified = tracked.filter(function (t) { return t.finding.confirmation.status === "verified"; }).length;
  const nUnconfirmed = tracked.length - nVerified;
  const nHigh = tracked.filter(function (t) { return t.finding.severity === "high"; }).length;
  const nFixed = tracked.filter(function (t) { return t.fix === "fixed"; }).length;

  let assessment;
  let recommendation;
  let assessmentFailed = false;
  if (roundsUsed > 0) {
    const fa = await agent(
      withSystem(TRIAGE_SYSTEM, loopFinalAsk(tracked, roundsUsed, gateGreen, allChangedPaths)),
      { label: "final-assessment", schema: LOOP_ASSESS_SCHEMA }
    );
    if (fa) {
      assessment = fa;
      recommendation = fa.recommendation;
    } else {
      assessment = fallbackAssessment(tracked, gateGreen, roundsUsed);
      recommendation = "human";
      assessmentFailed = true;
    }
  } else {
    const fa = await agent(
      withSystem(TRIAGE_SYSTEM, PROJECT ? finalAskProject(summary, GATE_LINE, targetFiles) : finalAsk(summary, GATE_LINE)),
      { label: "final-assessment", schema: ASSESS_SCHEMA }
    );
    assessment = fa ? fa : fallbackAssessment(tracked, gateGreen, 0);
    recommendation = "none";
    if (!fa) assessmentFailed = true;
  }

  const reportedFindings = tracked.map(function (t) {
    return {
      where: t.finding.where,
      what: t.finding.what,
      evidence: t.finding.evidence,
      status: t.finding.confirmation.status,
      severity: t.finding.severity,
      lens: t.finding.lens,
      fixStatus: t.fix,
    };
  });

  const reportMd = [
    PROJECT
      ? "# Code review — project (" + finalChangedN + " files)"
      : PR
        ? "# Code review — PR #" + prMeta.number + ": " + prMeta.title +
          " (" + finalChangedN + " files, ~" + finalAdded + " added lines)"
        : BRANCH_MODE
          ? "# Code review — branch " + branchName + " vs " + branchBaseRef +
            " (" + finalChangedN + " files, ~" + finalAdded + " added lines)"
          : "# Code review — " + BASE + " (" + finalChangedN + " files, ~" + finalAdded + " added lines)",
    "",
    "Mode: " + modeUsed + (modeUsed === "fast" ? " — one general reviewer" : " — correctness, security, quality") +
      " · every kept finding confirmed by an independent reader." +
      (PROJECT ? " Target: the project's code as it stands — \"merge\" reads as ready-as-is." : "") +
      (PR
        ? " Target: pull request #" + prMeta.number + " by " + prMeta.author + " → " +
          prMeta.baseRefName + (prMeta.url ? " — " + prMeta.url : "") +
          " — \"merge\" reads as the PR is ready."
        : "") +
      (BRANCH_MODE
        ? " Target: the branch's changes vs " + branchBaseRef + " at the merge-base — \"merge\" reads as the " +
          "branch is ready to merge."
        : ""),
    roundsUsed > 0
      ? "Fix loop: " + roundsUsed + " round(s) — " + nFixed + "/" + tracked.length + " findings fixed, checks " +
        (gateGreen ? "green" : "RED") + ". Fixes sit uncommitted in the working tree."
      : "",
    "",
    "## Verdict — " + assessment.risk + " risk" +
      (roundsUsed > 0 ? " · recommendation: **" + recommendation + "**" : ""),
    "",
    assessment.verdict,
    "",
    "## Mechanical gate (" + gate.length + " detected check" + (gate.length === 1 ? "" : "s") + ") — " +
      (gate.length === 0
        ? "nothing detected in this repo — no mechanical floor"
        : roundsUsed > 0
          ? (gateGreen ? "green after the final fix round" : "RED after the final fix round")
          : "all passed"),
    "",
  ].concat(
    gate.map(function (g) { return "- pass — " + g.name; }),
    [""],
    ["## Findings (" + tracked.length + " confirmed · " + nHigh + " high · " + nFixed + " fixed)", ""],
    tracked.length
      ? findingsMd(reportedFindings)
      : ["None — the reviewers reported nothing that met the bar.", ""],
    roundsUsed > 0
      ? ["## What the fixer did", ""].concat(fixerNotes.length ? fixerNotes.map(function (n) { return "- " + n; }) : ["(no changes)"], [""])
      : [],
    ["## Dropped at triage (" + allDropped.length + ")", ""],
    allDropped.length
      ? allDropped.map(function (d) { return "- `" + d.where + "` — " + d.what + " — _" + d.reason + "_"; })
      : ["None."],
    [""],
    ["## Test gaps", ""],
    assessment.testGaps.length ? assessment.testGaps.map(function (t) { return "- " + t; }) : ["None identified."],
    [""],
    ["## Residual risks", ""],
    assessment.residualRisks.length ? assessment.residualRisks.map(function (r) { return "- " + r; }) : ["None identified."],
    [""],
    ["## How this was checked", ""],
    PROJECT
      ? ["- Project review target: " + targetFiles.length + " of " + targetCandidates + " tracked source files, " +
          "largest first (cap " + PROJECT_MAX_FILES + "); lockfiles, generated and vendored files are excluded " +
          "by type" + (PATHS_ARG ? "; paths filter: " + PATHS_ARG : "") + "."]
      : [],
    gate.length > 0
      ? ["- The repo's own detected checks all ran and passed before review: " + gate.map(function (g) { return g.name; }).join("; ") + "."]
      : ["- The gate detected no checks in this repo — the review ran without a mechanical floor."],
    [
      "- Each finding was re-checked by an independent reader that did not write it (" + nVerified +
      " verified, " + nUnconfirmed + " unconfirmed).",
    ],
    roundsUsed > 0
      ? [
          "- After each fix round the gate re-ran" + (gateGreen ? " and finished green" : " — still failing") +
          ", every attempted fix was verified by an independent reader, and a fresh-eyes reviewer scanned the fix diff.",
          "- The fixes are uncommitted in the working tree — inspect with `git diff` and commit when satisfied.",
        ]
      : []
  ).join("\n");

  const notCovered = [];
  if (PROJECT && targetOverCap) {
    notCovered.push("the project review covered " + targetFiles.length + " of " + targetCandidates + " tracked source files " +
      "(cap " + PROJECT_MAX_FILES + ", largest first) — rerun with paths to target the rest");
  }
  for (const f of lensFailures) {
    notCovered.push("the " + f.lens + " lens was not covered — its reviewer returned no result");
  }
  for (const r of perLens) {
    if (r.triageFailed) {
      notCovered.push("the " + r.lens + " lens ran without triage — its raw findings passed straight to confirmation");
    }
  }
  if (gate.length === 0) {
    notCovered.push("no repo checks were detected by the gate — this review ran without a mechanical floor; ask the repo for its documented check command");
  }
  if (assessmentFailed) {
    notCovered.push("residual: the final assessment agent returned no result — a mechanical fallback assessment was used");
  }
  if (fixerAborted) {
    notCovered.push("residual: the fixer returned no result in an active round — the loop aborted with findings unresolved");
  }
  for (const t of assessment.testGaps) notCovered.push("test gap: " + t);
  for (const r of assessment.residualRisks) notCovered.push("residual: " + r);
  notCovered.push("runtime behavior beyond the repo's test suites was not exercised — this was a static review");
  if (roundsUsed > 0) notCovered.push("the fixes are uncommitted — the commit decision and message remain yours");

  return {
    conclusion:
      roundsUsed > 0
        ? assessment.verdict +
          " — recommendation: " + recommendation + ". " + nFixed + "/" + tracked.length + " findings fixed over " +
          roundsUsed + " round(s); checks " + (gateGreen ? "green" : "RED") +
          ". The fixes sit uncommitted in the working tree."
        : assessment.verdict +
          " — " + tracked.length + " confirmed finding(s), " + nHigh + " high, " + nUnconfirmed +
          " unconfirmed; overall risk " + assessment.risk + "." +
          (allDropped.length ? " (" + allDropped.length + " dropped at triage as duplicates or out of scope.)" : ""),
    findings: reportedFindings,
    verified: [].concat(
      PROJECT
        ? ["review target: the project's tracked source files — " + targetFiles.length + " of " + targetCandidates + " matched"]
        : [],
      PR
        ? ["review target: PR #" + prMeta.number + " (" + prMeta.state + ") — the merge-base diff against " + prMeta.baseRefName]
        : [],
      BRANCH_MODE
        ? ["review target: branch " + branchName + " vs " + branchBaseRef + " — the merge-base diff (" + commitCount + " commit(s))"]
        : [],
      gate.length > 0
        ? ["the mechanical gate ran the repo's own detected checks (all passed): " + gate.map(function (g) { return g.name; }).join("; ")]
        : [],
      ["every reported finding was re-checked by an independent reader that did not write it"],
      roundsUsed > 0
        ? [
            "every attempted fix was verified by an independent reader, and a fresh-eyes reviewer scanned the fix diff",
            "the gate re-ran after the final fix round — " + (gateGreen ? "all green" : "still failing"),
          ]
        : []
    ),
    notCovered: notCovered,
    title: roundsUsed > 0 ? "Code review and fix report" : "Code review report",
    markdown: reportMd,
  };
}

const result = await main();
result;
