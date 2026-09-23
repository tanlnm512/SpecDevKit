/* zcode-workflow
description: "Three-stage code review of a git change with an optional fix loop.
  The repo's own CI checks run first as the gate; the diff is then reviewed
  through separate lenses (correctness, security, quality & tests — or one
  general reviewer on small diffs), triaged by one editor, and every kept
  finding is independently confirmed. With fix_rounds > 0 an iterative loop
  follows: an author agent fixes the confirmed findings in the working tree,
  each fix is independently verified, the checks re-run, a fresh-eyes reviewer
  scans the fix diff, and the run ends with a risk-gated merge recommendation
  (merge / fix-first / human)."
whenToUse: Use when the user asks to review a change in this repo — "review the
  diff", "review this change", "review the last commit" — or to review and fix
  it ("review and fix the findings"). Pass base to choose the diff (default
  working tree; HEAD~1 for the last commit) and fix_rounds > 0 to let the
  author-fix loop run.
args:
  base:
    type: string
    description: Base ref the change is reviewed against. Default HEAD (working-tree
      changes). HEAD~1 reviews the last commit; any branch, tag or sha.
  fix_rounds:
    type: number
    description: "0 = review only (default). N = after the review, run up to N fix
      rounds: an author agent fixes the confirmed findings in the working tree,
      every fix is independently verified, the repo checks re-run, and a
      fresh-eyes reviewer scans the fix diff. Ends with a risk-gated merge
      recommendation; fixes stay uncommitted."
  mode:
    type: string
    description: fast = one general reviewer; full = three specialists (correctness,
      security, quality & tests); auto (default) picks fast for small diffs
      (<=400 added lines, <=5 files) and full otherwise.
*/

interface Finding {
  /** "path:line" on the new side of the diff — where the problem lives. */
  where: string;
  /** One sentence: what is wrong and why it matters. Not the fix. */
  what: string;
  /** The lines read, or command output, that demonstrate the problem is real. */
  evidence: string;
  /** high = data loss, crash, wrong result or security compromise; medium = a real defect the author should fix; low = minor. */
  severity: "low" | "medium" | "high";
}

interface LensReview {
  /** Findings from this reviewer's lens only; empty is the expected answer for a clean diff. */
  findings: Finding[];
}

interface DroppedFinding {
  where: string;
  what: string;
  /** One line: why triage dropped it (duplicate, style, speculation, pre-existing). */
  reason: string;
}

interface TriageVerdict {
  /** Findings worth the author's attention after dedup and scope checks. */
  kept: Finding[];
  /** Findings dropped at triage, each with its reason. */
  dropped: DroppedFinding[];
}

interface Confirmation {
  /** verified = reproduced independently from the code; unconfirmed = the confirmer could not reproduce it. */
  status: "verified" | "unconfirmed";
  /** One sentence: what the confirmer checked and what was seen. */
  note: string;
}

interface ConfirmedFinding extends Finding {
  lens: string;
  confirmation: Confirmation;
}

interface Assessment {
  /** Overall risk of merging this change as-is. */
  risk: "low" | "medium" | "high";
  /** Behaviors this change alters that no test covers. */
  testGaps: string[];
  /** What remains unverified after the checks and the review. */
  residualRisks: string[];
  /** Two or three sentences: should this merge, and what must the author fix first. */
  verdict: string;
}

interface FinalAssessment extends Assessment {
  /** merge = every finding fixed, checks green, nothing new — recommend merging; fix-first = ordinary findings remain; human = judgment calls or residue a human must decide. */
  recommendation: "merge" | "fix-first" | "human";
}

interface GateResult {
  name: string;
  exitCode: number;
  tail: string;
}

interface ReportedFinding {
  /** "path:line" with the problem, or the check name for gate findings. */
  where: string;
  /** One sentence: what is wrong. */
  what: string;
  /** What showed it — the lines read, or the command and output that proved it. */
  evidence: string;
  /** "verified" when an independent reader or a deterministic check confirmed it; "unconfirmed" when confirmation failed. */
  status: "verified" | "unconfirmed";
  /** How much it matters. Reserve "high" for data loss, a crash, a wrong result, or a security compromise. */
  severity: "low" | "medium" | "high";
  /** Which review lens found it (correctness, security, quality, general, fix-review, or gate). */
  lens: string;
  /** After a fix round: latest fix verification (fixed | unfixed | worse | pending when no round ran). */
  fixStatus: "fixed" | "unfixed" | "worse" | "pending";
}

interface WorkflowReport {
  /** Two or three sentences answering what the user asked for. */
  conclusion: string;
  findings: ReportedFinding[];
  /** What the run checked and how: the commands it ran, the files it covered. */
  verified: string[];
  /** What the run did not look at or could not check, and why. */
  notCovered: string[];
}

interface LensDef {
  label: string;
  name: string;
  system: string;
  focus: string;
}

interface FixOutcome {
  /** The what-strings of findings the fixer believes it fully addressed this round. */
  addressed: string[];
  /** Findings deliberately not addressed, each with why. */
  skipped: { what: string; why: string }[];
  /** Workspace-relative paths the fixer changed this round. */
  changedPaths: string[];
  /** One sentence per change: what was done and why it is the minimal fix. */
  notes: string[];
}

interface Verification {
  /** fixed = genuinely resolved in the current tree; unfixed = still present; worse = the fix introduced a new problem. */
  status: "fixed" | "unfixed" | "worse";
  /** One sentence: what was checked and what was seen. */
  note: string;
}

interface TrackedFinding {
  finding: ConfirmedFinding;
  /** Latest fix status across loop rounds. */
  fix: "pending" | "fixed" | "unfixed" | "worse";
  fixNote: string;
}

// Tunables live here, in control flow only — never inside ask text.
const BASE = typeof args.base === "string" && args.base.trim() ? args.base.trim() : "HEAD";
const MODE = typeof args.mode === "string" && args.mode.trim() ? args.mode.trim().toLowerCase() : "auto";
const FIX_ROUNDS =
  typeof args.fix_rounds === "number" && Number.isInteger(args.fix_rounds) && args.fix_rounds >= 0
    ? args.fix_rounds
    : 0;
const FAST_MAX_LINES = 400;
const FAST_MAX_FILES = 5;
const SEV_RANK: Record<string, number> = { high: 0, medium: 1, low: 2 };

const HONESTY =
  " If your instructions are impossible to satisfy, escalate and say so plainly rather than working around it.";

const LENSES: LensDef[] = [
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

const GENERAL: LensDef = {
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

function outTail(s: string, n: number): string {
  const t = s.trim();
  return t ? t.split("\n").slice(-n).join("\n") : "";
}

// The repo's own checks, mirroring CI check for check — run once before the
// review and again after every fix round.
async function runGate(): Promise<GateResult[]> {
  const gate: GateResult[] = [];
  {
    const r = await world.run("bash", ["skills/spec-to-prod/tests/run.sh"], { timeoutMs: 600000 });
    gate.push({ name: "skill suite (skills/spec-to-prod/tests/run.sh)", exitCode: r.exitCode, tail: outTail(r.stdout + "\n" + r.stderr, 8) });
  }
  {
    const r = await world.run("bash", ["tools/tests/run.sh"], { timeoutMs: 600000 });
    gate.push({ name: "tooling suite (tools/tests/run.sh)", exitCode: r.exitCode, tail: outTail(r.stdout + "\n" + r.stderr, 8) });
  }
  {
    const r = await world.run("python3", ["-m", "compileall", "-q", "skills", "tools"]);
    gate.push({ name: "compile Python sources (compileall)", exitCode: r.exitCode, tail: outTail(r.stdout + "\n" + r.stderr, 4) });
  }
  {
    const shFiles = (await files.glob("**/*.sh")).filter((p) => !p.startsWith(".git/"));
    let bad = "";
    for (const p of shFiles) {
      const r = await world.run("bash", ["-n", p]);
      if (r.exitCode !== 0) bad += p + " ";
    }
    gate.push({
      name: "shell syntax (bash -n, " + shFiles.length + " scripts)",
      exitCode: bad ? 1 : 0,
      tail: "failing: " + bad.trim(),
    });
  }
  {
    const r = await world.run("python3", ["tools/drift-check.py"]);
    gate.push({ name: "generated-artifact drift (tools/drift-check.py)", exitCode: r.exitCode, tail: outTail(r.stdout + "\n" + r.stderr, 8) });
  }
  {
    const r = await world.run("python3", ["skills/spec-to-prod/scripts/check.py", "skills/spec-to-prod/examples/mini-spec/specs/mini-spec"]);
    gate.push({ name: "representative docset (check.py mini-spec)", exitCode: r.exitCode, tail: outTail(r.stdout + "\n" + r.stderr, 8) });
  }
  return gate;
}

function reviewAsk(lensDef: LensDef, files: number, lines: number, overCap: boolean): string {
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
    "Do not edit any file. The repo's own checks all passed before you started, so do not re-run the test " +
    "suites; spend your turn on what only a reader can see."
  );
}

function triageAsk(lensLabel: string, review: LensReview): string {
  return (
    "Raw findings from the " + lensLabel + " reviewer for the change under review (`git diff " + BASE + "`):\n" +
    JSON.stringify(review.findings, null, 2) +
    "\nYou are the triage editor. For each finding, keep it or drop it. Keep = it meets the bar — real, " +
    "introduced by this change, actionable, worth the author's attention. Drop = a duplicate of a finding you " +
    "have already kept from another lens, a style nit, speculation, or a pre-existing issue. Never drop something " +
    "merely because it is inconvenient, and never keep what the repo's own checks already decide (they all " +
    "passed). Give every dropped item a one-line reason."
  );
}

function confirmAsk(f: Finding): string {
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

function finalAsk(summary: unknown[]): string {
  return (
    "Every kept finding has now been through independent confirmation:\n" +
    JSON.stringify(summary, null, 2) +
    "\nThe repo's own checks (test suites, compileall, shell syntax, drift, representative docset) all passed " +
    "before review started. Produce the final assessment of this change. Run `git diff " + BASE + "` yourself " +
    "wherever you need to judge it, and read the test files before claiming a test gap.\n" +
    "risk: low | medium | high — what merging this change as-is would risk. testGaps: behaviors this change " +
    "alters that no test covers (empty if none). residualRisks: what remains unverified after the checks and " +
    "the review. verdict: two or three sentences — should this merge, and what must the author fix first."
  );
}

function fixerAsk(round: number, unresolved: TrackedFinding[], gateFeedback: string): string {
  if (round === 1) {
    return (
      "Fix the confirmed findings on the change (`git diff " + BASE + "`):\n" +
      JSON.stringify(
        unresolved.map((t) => ({
          where: t.finding.where,
          what: t.finding.what,
          evidence: t.finding.evidence,
          severity: t.finding.severity,
          lens: t.finding.lens,
        })),
        null,
        2,
      ) +
      "\nWork in the working tree; never commit. You may run a single targeted test file for code you touch, " +
      "but the full suites re-run the moment you finish — do not run them yourself.\n" +
      "Return addressed (the what-strings you fully fixed), skipped (what you deliberately left, with why), " +
      "changedPaths, and notes (one sentence per change: what was done and why it is minimal)."
    );
  }
  return (
    "Round " + round + ". These findings are still unresolved after the previous round — the independent " +
    "verifiers said, per item:\n" +
    JSON.stringify(
      unresolved.map((t) => ({ where: t.finding.where, what: t.finding.what, verifier: t.fixNote })),
      null,
      2,
    ) +
    (gateFeedback
      ? "\nThe repo's own checks are currently FAILING after the last round:\n" + gateFeedback
      : "\nThe repo's own checks passed after the last round.") +
    "\nYou hold the full finding detail from earlier rounds in your context. Fix exactly these, same rules as " +
    "before: minimal, in the repo's style, never commit, never weaken a test to make a finding go away."
  );
}

function verifyAsk(t: TrackedFinding, notes: string): string {
  return (
    "A reviewer confirmed this finding on the change (`git diff " + BASE + "`), and the author has since " +
    "attempted a fix.\n" +
    "Finding: " + JSON.stringify({ where: t.finding.where, what: t.finding.what, severity: t.finding.severity, lens: t.finding.lens }) +
    "\nAuthor's notes: " + (notes || "(none)") +
    "\nVerify in the CURRENT working tree: read the location and its immediate callers or contract; confirm " +
    "the described defect is gone and the fix is minimal and sound.\n" +
    "Answer fixed only if the defect itself is resolved — cosmetic proximity is not a fix. Answer unfixed if " +
    "it still stands. Answer worse if the fix introduced a new problem (say what, in note). Do not edit anything."
  );
}

function fixReviewAsk(paths: string[], gateGreen: boolean): string {
  return (
    "The author fixed review findings by changing:\n" +
    paths.map((p) => "- " + p).join("\n") +
    "\nRead the cumulative diff for exactly these paths (`git diff " + BASE + " -- <path>`, one per path) and " +
    "the current file contents where context matters. Judge the fix code as a fresh reviewer on a new change: " +
    "report only NEW defects these fixes introduce — the same bar as the panel (real, introduced by these " +
    "fixes, demonstrable from the code, the author would fix). Do not re-report the original findings; " +
    "separate verifiers own those.\n" +
    "An empty findings list is the expected answer for clean fixes. Do not edit anything; the repo's own " +
    "checks " + (gateGreen ? "all passed" : "are currently failing") + " after the fixes."
  );
}

function loopFinalAsk(
  tracked: TrackedFinding[],
  roundsUsed: number,
  gateGreen: boolean,
  changedPaths: string[],
): string {
  return (
    "The fix loop ran " + roundsUsed + " round(s). Every tracked finding and its state:\n" +
    JSON.stringify(
      tracked.map((t) => ({
        where: t.finding.where,
        what: t.finding.what,
        severity: t.finding.severity,
        lens: t.finding.lens,
        reviewStatus: t.finding.confirmation.status,
        fix: t.fix,
        fixNote: t.fixNote,
      })),
      null,
      2,
    ) +
    "\nThe repo's own checks after the final round: " + (gateGreen ? "all passed" : "FAILING (see lens 'gate' items)") +
    ".\nAll paths the author changed: " + (changedPaths.join(", ") || "(none)") +
    "\nProduce the final assessment of the change INCLUDING the fixes — run `git diff " + BASE + "` yourself " +
    "where you need to judge it, and read the test files before claiming a test gap.\n" +
    "risk: what merging now would risk. testGaps: behaviors still altered with no test covering them. " +
    "residualRisks: what remains unverified. verdict: two or three sentences — should this merge now? " +
    "recommendation: merge | fix-first | human — merge only if every finding is fixed, the checks are green, " +
    "and nothing new surfaced; human when judgment calls or unconfirmed residue remain."
  );
}

function findingsMd(items: ReportedFinding[]): string[] {
  const lines: string[] = [];
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

// ---------------------------------------------------------------------------
phase("Scope the change and run the repo's checks");

const scope = await git.status();
const changed = await git.changedFiles(BASE);
let addedLines = 0;
let diffOverCap = false;
try {
  const d = await git.diff(BASE);
  addedLines = d.split("\n").filter((l) => l.startsWith("+") && !l.startsWith("+++")).length;
} catch {
  diffOverCap = true;
}
log(
  "change under review: git diff " + BASE + " — " + changed.length + " files, ~" + addedLines + " added lines" +
  (scope.clean ? " (clean tree)" : " (uncommitted work present)")
);

if (changed.length === 0) {
  return {
    conclusion: "No changes against " + BASE + " — nothing to review.",
    findings: [],
    verified: ["change scope: git diff " + BASE + " is empty"],
    notCovered: [],
  };
}

const gate = await runGate();

const gateFailed = gate.filter((g) => g.exitCode !== 0);
log("repo checks: " + (gate.length - gateFailed.length) + "/" + gate.length + " passed");

for (const g of gateFailed) {
  report({
    where: g.name,
    what: "Repo check failed: " + g.name,
    evidence: g.tail || "(no output)",
    status: "verified",
    severity: "high",
    lens: "gate",
  });
}

if (gateFailed.length > 0) {
  const gateFindings: ReportedFinding[] = gateFailed.map((g) => ({
    where: g.name,
    what: "Repo check failed: " + g.name,
    evidence: g.tail || "(no output)",
    status: "verified",
    severity: "high",
    lens: "gate",
    fixStatus: "pending",
  }));
  const gateMd = [
    "# Code review — checks failed, review stopped",
    "",
    "The change (`git diff " + BASE + "` — " + changed.length + " files) failed the repo's own checks, so the ",
    "specialist reviewers were not spent on it. Fix these first, then rerun the review.",
    "",
    "## Failed checks",
    "",
    ...gate.map((g) =>
      "- " + (g.exitCode === 0 ? "pass" : "**FAIL**") + " — " + g.name +
      (g.exitCode === 0 ? "" : "\n\n  ```\n  " + g.tail + "\n  ```")
    ),
  ].join("\n");
  try {
    await artifact.markdown("review-report", gateMd, {
      title: "Code review — checks failed",
      description: "The mechanical gate failed; specialist review was skipped.",
      primary: true,
    });
  } catch (e) {
    log("report not published: " + String(e));
  }
  return {
    conclusion:
      "The change failed " + gateFailed.length + " of " + gate.length +
      " repo checks (" + gateFailed.map((g) => g.name).join("; ") + "). Specialist review was skipped — " +
      "these are mechanical fixes; rerun the review after they pass.",
    findings: gateFindings,
    verified: ["all " + gate.length + " repo checks ran (they mirror CI) — " + gateFailed.length + " failed"],
    notCovered: ["specialist review of the diff — skipped because the mechanical gate failed"],
  };
}

// ---------------------------------------------------------------------------
phase("Review the change through separate lenses and confirm every finding");

let modeUsed: string;
if (MODE === "fast" || MODE === "full") {
  modeUsed = MODE;
} else {
  modeUsed = !diffOverCap && addedLines <= FAST_MAX_LINES && changed.length <= FAST_MAX_FILES ? "fast" : "full";
}
const panel: LensDef[] = modeUsed === "fast" ? [GENERAL] : LENSES;
log("review mode: " + modeUsed + (modeUsed === "fast" ? " (small diff, one general reviewer)" : " (three specialists)"));

const triage = agent("Triage editor", {
  system:
    "You are the triage editor of a code review panel. Reviewers hand you their raw findings lens by lens; you " +
    "dedupe across lenses, enforce the flagging bar (real, introduced by the change, actionable), and drop style " +
    "nits, speculation and pre-existing issues with a one-line reason. You are stingy but never suppress a real " +
    "defect to keep the count down.",
});

const perLens = await Promise.all(
  panel.map(async (lensDef) => {
    const review = await agent(lensDef.name, { system: lensDef.system }).ask<LensReview>(
      reviewAsk(lensDef, changed.length, addedLines, diffOverCap),
    );
    log(lensDef.name + ": " + review.findings.length + " finding(s)");
    if (review.findings.length === 0) {
      return { lens: lensDef.label, confirmed: [] as ConfirmedFinding[], dropped: [] as DroppedFinding[] };
    }
    const triaged = await triage.ask<TriageVerdict>(triageAsk(lensDef.label, review));
    const confirmations = await Promise.all(
      triaged.kept.map((f, i) =>
        agent("Confirm " + lensDef.label + " finding " + (i + 1)).ask<Confirmation>(confirmAsk(f)),
      ),
    );
    const confirmed = triaged.kept.map((f, i) => ({ ...f, lens: lensDef.label, confirmation: confirmations[i] }));
    for (const c of confirmed) {
      report({
        where: c.where,
        what: c.what,
        severity: c.severity,
        lens: c.lens,
        status: c.confirmation.status,
      });
    }
    return { lens: lensDef.label, confirmed, dropped: triaged.dropped };
  }),
);

const allConfirmed = perLens
  .flatMap((p) => p.confirmed)
  .sort((a, b) => (SEV_RANK[a.severity] ?? 3) - (SEV_RANK[b.severity] ?? 3));
const allDropped = perLens.flatMap((p) => p.dropped);
const summary = allConfirmed.map((c) => ({
  where: c.where,
  what: c.what,
  severity: c.severity,
  lens: c.lens,
  status: c.confirmation.status,
}));

// ---------------------------------------------------------------------------
// Option C loop: the author fixes, independent verifiers check every fix,
// the repo's checks re-run, fresh eyes scan the fix diff. Bounded by rounds.
const tracked: TrackedFinding[] = allConfirmed.map((f) => ({
  finding: f,
  fix: "pending",
  fixNote: "not yet attempted",
}));
let roundsUsed = 0;
let allResolved = allConfirmed.length === 0;
let gateGreen = true;
const fixerNotes: string[] = [];
const allChangedPaths: string[] = [];

if (FIX_ROUNDS > 0 && allConfirmed.length > 0) {
  phase("Fix the confirmed findings and verify every fix");
  const fixer = agent("Author and fixer", { system: FIXER_SYSTEM });
  let gateFeedback = "";

  for (let round = 1; round <= FIX_ROUNDS; round++) {
    const unresolved = tracked.filter((t) => t.fix !== "fixed");
    if (unresolved.length === 0) {
      allResolved = true;
      break;
    }
    const outcome = await fixer.ask<FixOutcome>(fixerAsk(round, unresolved, gateFeedback));
    roundsUsed = round;
    for (const n of outcome.notes) fixerNotes.push("round " + round + ": " + n);
    for (const p of outcome.changedPaths) if (allChangedPaths.indexOf(p) === -1) allChangedPaths.push(p);
    log(
      "fix round " + round + ": " + outcome.addressed.length + " addressed · " + outcome.skipped.length +
      " skipped · " + outcome.changedPaths.length + " path(s) changed"
    );

    const roundGate = await runGate();
    const gateBad = roundGate.filter((g) => g.exitCode !== 0);
    gateGreen = gateBad.length === 0;
    gateFeedback = gateBad.map((g) => g.name + ":\n" + g.tail).join("\n\n");
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
      report({
        where: g.name,
        what: "Repo check failed after the fixes: " + g.name,
        severity: "high",
        lens: "gate",
        fix: "unfixed",
        round,
      });
    }

    const verifications = await Promise.all(
      unresolved.map((t, i) =>
        agent("Verify round " + round + " fix " + (i + 1)).ask<Verification>(verifyAsk(t, outcome.notes.join(" | "))),
      ),
    );
    for (let i = 0; i < unresolved.length; i++) {
      const v = verifications[i];
      const t = unresolved[i];
      t.fix = v.status;
      t.fixNote = "round " + round + ": " + v.note;
      report({ where: t.finding.where, what: t.finding.what, lens: t.finding.lens, fix: v.status, note: v.note, round });
    }

    if (outcome.changedPaths.length > 0) {
      const fixReview = await agent("Fix reviewer round " + round, { system: FIX_REVIEW_SYSTEM }).ask<LensReview>(
        fixReviewAsk(outcome.changedPaths, gateGreen),
      );
      if (fixReview.findings.length > 0) {
        const triagedFix = await triage.ask<TriageVerdict>(triageAsk("fix-review", fixReview));
        const fixConfs = await Promise.all(
          triagedFix.kept.map((f, i) =>
            agent("Confirm fix-review finding " + round + "-" + (i + 1)).ask<Confirmation>(confirmAsk(f)),
          ),
        );
        for (let i = 0; i < triagedFix.kept.length; i++) {
          const c: ConfirmedFinding = { ...triagedFix.kept[i], lens: "fix-review", confirmation: fixConfs[i] };
          tracked.push({ finding: c, fix: "pending", fixNote: "new from fix review, round " + round });
          report({
            where: c.where,
            what: c.what,
            severity: c.severity,
            lens: "fix-review",
            status: c.confirmation.status,
            round,
          });
        }
      }
    }

    if (tracked.every((t) => t.fix === "fixed")) {
      allResolved = true;
      break;
    }
  }
}

// ---------------------------------------------------------------------------
phase("Synthesize the final review report");

let finalAdded = addedLines;
let finalChangedN = changed.length;
if (roundsUsed > 0) {
  try {
    const d2 = await git.diff(BASE);
    finalAdded = d2.split("\n").filter((l) => l.startsWith("+") && !l.startsWith("+++")).length;
    finalChangedN = (await git.changedFiles(BASE)).length;
  } catch {
    // keep the pre-fix scope numbers
  }
}

const nVerified = tracked.filter((t) => t.finding.confirmation.status === "verified").length;
const nUnconfirmed = tracked.length - nVerified;
const nHigh = tracked.filter((t) => t.finding.severity === "high").length;
const nFixed = tracked.filter((t) => t.fix === "fixed").length;

let assessmentOut: Assessment;
let recommendation: "merge" | "fix-first" | "human" | "none";
if (roundsUsed > 0) {
  const fa = await triage.ask<FinalAssessment>(loopFinalAsk(tracked, roundsUsed, gateGreen, allChangedPaths));
  assessmentOut = fa;
  recommendation = fa.recommendation;
} else {
  assessmentOut = await triage.ask<Assessment>(finalAsk(summary));
  recommendation = "none";
}
const assessment = assessmentOut;

const reportedFindings: ReportedFinding[] = tracked.map((t) => ({
  where: t.finding.where,
  what: t.finding.what,
  evidence: t.finding.evidence,
  status: t.finding.confirmation.status,
  severity: t.finding.severity,
  lens: t.finding.lens,
  fixStatus: t.fix,
}));

const reportMd = [
  "# Code review — " + BASE + " (" + finalChangedN + " files, ~" + finalAdded + " added lines)",
  "",
  "Mode: " + modeUsed + (modeUsed === "fast" ? " — one general reviewer" : " — correctness, security, quality") +
    " · every kept finding confirmed by an independent reader.",
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
  "## Repo checks (all " + gate.length + ", mirroring CI) — " +
    (roundsUsed > 0 ? (gateGreen ? "green after the final fix round" : "RED after the final fix round") : "all passed"),
  "",
  ...gate.map((g) => "- pass — " + g.name),
  "",
  "## Findings (" + tracked.length + " confirmed · " + nHigh + " high · " + nFixed + " fixed)",
  "",
  ...(tracked.length ? findingsMd(reportedFindings) : ["None — the reviewers reported nothing that met the bar.", ""]),
  ...(roundsUsed > 0
    ? ["## What the fixer did", "", ...(fixerNotes.length ? fixerNotes.map((n) => "- " + n) : ["(no changes)"]), ""]
    : []),
  "## Dropped at triage (" + allDropped.length + ")",
  "",
  ...(allDropped.length
    ? allDropped.map((d) => "- `" + d.where + "` — " + d.what + " — _" + d.reason + "_")
    : ["None."]),
  "",
  "## Test gaps",
  "",
  ...(assessment.testGaps.length ? assessment.testGaps.map((t) => "- " + t) : ["None identified."]),
  "",
  "## Residual risks",
  "",
  ...(assessment.residualRisks.length ? assessment.residualRisks.map((r) => "- " + r) : ["None identified."]),
  "",
  "## How this was checked",
  "",
  "- The repo's own checks all ran and passed before review: " + gate.map((g) => g.name).join("; ") + ".",
  "- Each finding was re-checked by an independent reader that did not write it (" + nVerified +
    " verified, " + nUnconfirmed + " unconfirmed).",
  ...(roundsUsed > 0
    ? [
        "- After each fix round the repo checks re-ran" + (gateGreen ? " and finished green" : " — still failing") +
        ", every attempted fix was verified by an independent reader, and a fresh-eyes reviewer scanned the fix diff.",
        "- The fixes are uncommitted in the working tree — inspect with `git diff` and commit when satisfied.",
      ]
    : []),
].join("\n");

try {
  await artifact.markdown("review-report", reportMd, {
    title: roundsUsed > 0 ? "Code review and fix report" : "Code review report",
    description:
      tracked.length === 0
        ? "Clean change: all repo checks passed and no findings survived review."
        : tracked.length + " confirmed finding(s), " + nFixed + " fixed — " + assessment.risk + " risk" +
          (roundsUsed > 0 ? ", recommendation " + recommendation : ""),
    primary: true,
  });
} catch (e) {
  log("report not published: " + String(e));
}

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
  verified: [
    "all " + gate.length + " repo checks ran and passed (they mirror CI): " + gate.map((g) => g.name).join("; "),
    "every reported finding was re-checked by an independent reader that did not write it",
    ...(roundsUsed > 0
      ? [
          "every attempted fix was verified by an independent reader, and a fresh-eyes reviewer scanned the fix diff",
          "the repo checks re-ran after the final fix round — " + (gateGreen ? "all green" : "still failing"),
        ]
      : []),
  ],
  notCovered: [
    ...assessment.testGaps.map((t) => "test gap: " + t),
    ...assessment.residualRisks.map((r) => "residual: " + r),
    "runtime behavior beyond the repo's test suites was not exercised — this was a static review",
    ...(roundsUsed > 0 ? ["the fixes are uncommitted — the commit decision and message remain yours"] : []),
  ],
};
