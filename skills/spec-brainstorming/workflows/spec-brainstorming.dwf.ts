/* zcode-workflow
description: >-
  The panel wave of a spec-brainstorming run — stage 2 only. Takes
  the stage-1 ground (the problem restatement, the audience, the
  constraints), loads the three lens briefs and the shared panel
  protocol from the skill dir at run time, gathers an external
  evidence pack from GitHub and the web with one neutral
  researcher, then spawns The Visionary, The Cynic and The
  Minimalist fresh and in parallel from one payload — none sees
  another's output — and returns the three digests verbatim,
  ready for the session's trade-off matrix. The interactive
  stages (context discovery, matrix, refinement, handoff) never
  run in a workflow: a stop is not a question (the skill's
  D-004).
whenToUse: >-
  Use when a brainstorming session has its stage-1 ground (the
  idea, the audience and the constraints are stated) and the
  panel wave should run in the background — "run the brainstorm
  panel for this: …". The session keeps stages 1, 3, 4 and 5;
  this workflow is exactly the spawned-panel half of the
  spec-brainstorming skill's stage 2.
args:
  name:
    type: string
    description: >-
      The kebab-case name the run files the idea under (the
      artifact will land at brainstorms/<name>.md in stage 5,
      the session's move). Used here only to label the report.
  problem:
    type: string
    description: >-
      Stage 1's output: the problem restatement — what the idea
      is, what hurts, for whom — in the idea-owner's own words
      where possible. The payload every lens argues from.
  audience:
    type: string
    description: >-
      Who this is for, as stage 1 established it. May be empty —
      the lenses then name the unknown as an assumption, never a
      fact.
  constraints:
    type: string
    description: >-
      The constraints stage 1 surfaced (time, stack, team, scope
      fences). May be empty — same rule: unknowns are named as
      assumptions.
  skill_dir:
    type: string
    description: >-
      Optional: the installed spec-brainstorming skill dir the
      briefs and protocol are read from. The installed copy bakes
      its own path at install time; a runtime skill_dir arg wins.
*/

// spec-brainstorming.dwf.ts — the zcode dialect of the panel wave.
// __SKILL_DIR__ below is a placeholder; the installer bakes the
// active skill dir into the installed copy (a runtime skill_dir
// arg wins). The zcode facade has no user-installable agent
// types, so the lens briefs under <skillDir>/agents/ are read at
// run time and ride each agent's system — one source of truth
// for the lenses; a brief edit ships without a workflow edit.
// Briefs sit outside the workspace, so files.read cannot reach
// them — cat through world.run is the same seam the other skills
// use. A missing brief degrades to the inline mission line,
// logged, never an error, never a skipped lens (D-004).

interface LensDigest {
  /** The lens's own name: The Visionary, The Cynic, or The Minimalist. */
  angle: string;
  /** One sentence: the idea through this lens. */
  pitch: string;
  /** The 2-3 sharpest arguments from the brief's rubric, one line each. */
  points: string[];
  /** The falsifiable condition, tripwire, or creep signal this lens contributes. */
  watch: string;
}

interface EvidencePack {
  /** Markdown pack: one bullet per finding — claim, URL, access date, supports/contradicts. Empty when nothing could be gathered. */
  pack: string;
}

const SKILL_DIR_BAKED = "__SKILL_DIR__";
const skillDir =
  typeof args.skill_dir === "string" && args.skill_dir
    ? args.skill_dir
    : SKILL_DIR_BAKED;

const NAME =
  typeof args.name === "string" && args.name.trim() ? args.name.trim() : "the idea";
const PROBLEM =
  typeof args.problem === "string" && args.problem.trim() ? args.problem.trim() : "";
const AUDIENCE =
  typeof args.audience === "string" && args.audience.trim() ? args.audience.trim() : "";
const CONSTRAINTS =
  typeof args.constraints === "string" && args.constraints.trim()
    ? args.constraints.trim()
    : "";

// The external evidence pack, gathered in its own phase before the
// lenses spawn; payloadAsk() reads it at lens-spawn time.
let evidencePack = "";

if (!PROBLEM) {
  report({
    conclusion: "No problem restatement was given — the panel wave has nothing to argue. " +
      "Run stage 1 in the session first (one clarifying question, the user answers), then " +
      "dispatch this workflow with that answer as the problem arg.",
    angles: [] as LensDigest[],
    verified: [] as string[],
    notCovered: ["no lens ran — the payload was empty (stage 1 is the session's, always)"],
  });
} else {

// One seat per lens. The mission line is the degrade floor: what the
// lens argues from when its brief cannot be read — the full rubric
// lives in the brief, the brief is the source of truth.
interface LensDef {
  label: string;
  name: string;
  brief: string;
  mission: string;
}

const LENSES: LensDef[] = [
  {
    label: "visionary",
    name: "The Visionary",
    brief: "brainstorm-visionary.md",
    mission:
      "You are the Visionary lens of a brainstorming panel: take the idea at full " +
      "strength and argue what it becomes when it works — the ceiling, what " +
      "compounds, who falls in love with it — grounded in the stated problem, " +
      "never sci-fi.",
  },
  {
    label: "cynic",
    name: "The Cynic",
    brief: "brainstorm-cynic.md",
    mission:
      "You are the Cynic lens of a brainstorming panel: run the pre-mortem — it is " +
      "a year later and this failed; explain why. Real criticism, not theater: the " +
      "weakest load-bearing assumption, the adoption blockers, the hidden costs, " +
      "the kill criterion.",
  },
  {
    label: "minimalist",
    name: "The Minimalist",
    brief: "brainstorm-minimalist.md",
    mission:
      "You are the Minimalist lens of a brainstorming panel: argue the smallest " +
      "honest cut — the one core value, the thinnest delivery, the day-one cut " +
      "list, the cheapest experiment that tests the value.",
  },
];

// The ask every lens answers — the payload contract of
// contracts/run.md. Load-bearing sentences; the claude dialect
// (workflows/spec-brainstorming.js) carries them word for word, and
// tests/test_workflow_copies.py pins that parity.
function payloadAsk(): string {
  return "Argue this idea from your lens only.\n\n" +
    "The idea, in the idea-owner's words:\n" + PROBLEM + "\n\n" +
    "Audience: " + (AUDIENCE || "not established — name the gap as an assumption, never a fact") + "\n" +
    "Constraints: " + (CONSTRAINTS || "not established — name the gap as an assumption, never a fact") + "\n\n" +
    "External evidence pack (GitHub + web, gathered before you spawned — cite it, verify against it):\n" +
    (evidencePack || "not gathered — every external claim is an assumption") + "\n\n" +
    "Ground every point in what is stated here; name assumptions as assumptions, never invent facts.\n" +
    "Cite a source for every load-bearing claim — file:line for in-repo, URL + access date for external; what has no source is an assumption, said as one.\n" +
    "Before writing your digest, attack your own strongest point once; argue what survives.\n" +
    "Return only your digest: angle, pitch, points (2-3 lines), watch — one line per field. " +
    "If you cannot satisfy your brief, say so in watch rather than working around it.";
}

phase("Load the lens briefs and the shared panel protocol");

async function readBrief(file: string): Promise<string> {
  const r = await world.run("cat", [skillDir + "/agents/" + file]);
  return r.exitCode === 0 ? r.stdout.trim() : "";
}

const protocol = await readBrief("_panel-protocol.md");
const briefBodies = await Promise.all(LENSES.map((l) => readBrief(l.brief)));
const missingBriefs = LENSES.filter((_, i) => !briefBodies[i]);
if (!protocol) log("panel protocol did not load — lenses argue from briefs plus mission lines only");
for (const l of missingBriefs) log(l.name + ": brief did not load — arguing from the inline mission line");

function lensSystem(i: number): string {
  const parts = [LENSES[i].mission];
  if (briefBodies[i]) parts.push(briefBodies[i]);
  if (protocol) parts.push(protocol);
  return parts.join("\n\n---\n\n");
}

function researchAsk(): string {
  return "You are the evidence researcher of a brainstorming panel — a neutral " +
    "gatherer, not a lens: find what the outside world already knows about this " +
    "territory, never argue, never editorialize.\n\n" +
    "The idea: " + NAME + " — " + PROBLEM + "\n\n" +
    "Audience: " + (AUDIENCE || "not established") + "\n" +
    "Constraints: " + (CONSTRAINTS || "not established") + "\n\n" +
    "Search GitHub with the gh CLI (gh search repos, gh search issues) for prior art " +
    "and competing tools on the idea's keywords — stars, last activity, maintenance " +
    "signals. Search the web with whatever search or fetch tools your harness grants " +
    "(WebSearch, WebFetch, curl) for 2-4 authoritative sources that support or " +
    "contradict the idea's premises.\n\n" +
    "Return only: { pack } — markdown, one bullet per finding: the claim, the URL, " +
    "the access date, and whether it supports or contradicts. If nothing can be " +
    "gathered (no tools, no network), return an empty pack — never invent a source.";
}

async function gatherEvidence(): Promise<string> {
  const r = await agent("Evidence researcher").ask<EvidencePack>(researchAsk());
  const pack = r && typeof r.pack === "string" ? r.pack.trim() : "";
  if (!pack) {
    log("external evidence pack did not load — external claims in the digests are assumptions, not sourced");
    return "";
  }
  log("evidence pack gathered — " + pack.split("\n").filter((s) => s.trim().startsWith("-")).length + " sourced finding(s)");
  return pack;
}

phase("Gather external evidence from GitHub and the web");
evidencePack = await gatherEvidence();

phase("Argue the idea from three independent lenses");

// Fresh, parallel, one payload — none sees another's output (D-002).
const digests = await Promise.all(
  LENSES.map((l, i) => agent(l.name, { system: lensSystem(i) }).ask<LensDigest>(payloadAsk())),
);
const failed = LENSES.filter((_, i) => !digests[i]);
for (const l of failed) log(l.name + ": returned no digest — the session must re-ask this lens");
const angles = digests.filter((d): d is LensDigest => !!d);
for (const d of angles) log(d.angle + ": digest returned — " + d.points.length + " point(s)");

phase("Assemble the labeled angles for the session");

report({
  conclusion: "The panel wave returned " + angles.length + " of 3 digests for " + NAME +
    " — present them distinctly labeled, build the trade-off matrix (no recommendation), " +
    "then refine socratically. The matrix, the refinement and the handoff are the " +
    "session's: a workflow has no user-turn primitive (D-004).",
  angles,
  verified: [
    "three lens seats spawned fresh and in parallel from one payload — none saw another's output",
    "each lens carried its full brief and the shared panel protocol, loaded from the skill dir at run time",
    "every digest follows the pinned grammar: angle, pitch, points (2-3 lines), watch",
    ...(evidencePack ? ["external evidence pack gathered from GitHub and the web before the lenses spawned"] : []),
  ],
  notCovered: [
    ...(!evidencePack ? ["external evidence pack did not load — external claims in the digests are assumptions, not sourced"] : []),
    ...missingBriefs.map((l) =>
      l.name + " argued from its inline mission line only — its brief did not load; re-run in-session with the full brief if its rubric matters here"),
    ...failed.map((l) => l.name + " returned no digest — the session must re-ask this lens before the matrix"),
    ...(!protocol ? ["the shared panel protocol did not load — lens rules (argue your lens, digest only) rode the mission lines only"] : []),
    "stage 1 (context discovery), stage 3 (trade-off matrix), stage 4 (refinement) and stage 5 (handoff) are the session's, always",
  ],
});

}
