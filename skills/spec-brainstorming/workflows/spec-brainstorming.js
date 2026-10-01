export const meta = {
  name: "spec-brainstorming",
  description:
    "The panel wave of a spec-brainstorming run — stage 2 only. " +
    "Takes the stage-1 ground (the problem restatement, the audience, " +
    "the constraints), loads the three lens briefs and the shared " +
    "panel protocol from the skill dir at run time, gathers an " +
    "external evidence pack from GitHub and the web with one neutral " +
    "researcher, then spawns The Visionary, The Cynic and The " +
    "Minimalist fresh and in parallel from one payload — none sees " +
    "another's output — and returns the three digests verbatim, " +
    "ready for the session's trade-off matrix. The interactive " +
    "stages (context discovery, matrix, refinement, handoff) never " +
    "run in a workflow: a stop is not a question (the skill's " +
    "D-004). Use when a brainstorming session has its stage-1 " +
    "ground and the panel wave should run in the background — the " +
    "session keeps stages 1, 3, 4 and 5.",
}

// ---------------------------------------------------------------------------
// spec-brainstorming.js — the Claude Code dialect of the panel wave.
// __SKILL_DIR__ below is a placeholder; tools/install-workflow.sh bakes
// the active skill dir into the installed copy (a runtime skill_dir arg
// wins). This script has NO filesystem/shell access of its own (runtime
// rule) — the probe agent below is the only seam that reads the briefs,
// and every lens agent argues from the ask it is handed.
//
// Dialect divergences from the zcode master
// (workflows/spec-brainstorming.dwf.ts), each forced by the one-shot
// agent model — behavior is otherwise identical:
//   - the lens system (mission + brief + protocol) rides at the head of
//     each one-shot ask instead of a persistent agent's system;
//   - briefs are read through a probe agent instead of the zcode
//     facade's command seam;
//   - the final report returns as the `markdown` field.
// The payload sentences, the phases, the digest grammar and the mission
// lines are shared word for word; tests/test_workflow_copies.py pins
// that parity.
// ---------------------------------------------------------------------------

const SKILL_DIR_BAKED = "__SKILL_DIR__";
const skillDir =
  typeof args !== "undefined" && args && typeof args.skill_dir === "string" && args.skill_dir
    ? args.skill_dir
    : SKILL_DIR_BAKED;

const NAME =
  typeof args !== "undefined" && args && typeof args.name === "string" && args.name.trim()
    ? args.name.trim()
    : "the idea";
const PROBLEM =
  typeof args !== "undefined" && args && typeof args.problem === "string" && args.problem.trim()
    ? args.problem.trim()
    : "";
const AUDIENCE =
  typeof args !== "undefined" && args && typeof args.audience === "string" && args.audience.trim()
    ? args.audience.trim()
    : "";
const CONSTRAINTS =
  typeof args !== "undefined" && args && typeof args.constraints === "string" && args.constraints.trim()
    ? args.constraints.trim()
    : "";

function shq(s) {
  return "'" + String(s).replace(/'/g, "'\\''") + "'";
}

const PROBE_SCHEMA = {
  type: "object",
  properties: { stdout: { type: "string" } },
  required: ["stdout"],
  additionalProperties: false,
};

const DIGEST_SCHEMA = {
  type: "object",
  properties: {
    angle: { type: "string" },
    pitch: { type: "string" },
    points: { type: "array", items: { type: "string" } },
    watch: { type: "string" },
  },
  required: ["angle", "pitch", "points", "watch"],
  additionalProperties: false,
};

const EVIDENCE_SCHEMA = {
  type: "object",
  properties: {
    pack: { type: "string" },
  },
  required: ["pack"],
  additionalProperties: false,
};

// ONE probe per file read: runs the exact command and returns its
// combined stdout verbatim through a schema — the script's only seam
// to the shell (same pattern as the sibling skills' probe agents).
async function probe(label, command) {
  const r = await agent(
    "Run this exact shell command from the workspace root and return ONLY its " +
    "combined stdout verbatim in the stdout field (empty string if none):\n  " +
    command,
    { label: label, schema: PROBE_SCHEMA }
  );
  if (!r || typeof r.stdout !== "string") {
    log(label + ": probe returned no result");
    return null;
  }
  return r.stdout;
}

// One seat per lens. The mission line is the degrade floor: what the
// lens argues from when its brief cannot be read — the full rubric
// lives in the brief, the brief is the source of truth.
var LENSES = [
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

// The external evidence pack, gathered in its own phase before the
// lenses spawn; payloadAsk() reads it at lens-spawn time.
var evidencePack = "";

// The ask every lens answers — the payload contract of
// contracts/run.md. Load-bearing sentences; the zcode master
// carries them word for word, and tests/test_workflow_copies.py
// pins that parity.
function payloadAsk() {
  return (
    "Argue this idea from your lens only.\n\n" +
    "The idea, in the idea-owner's words:\n" + PROBLEM + "\n\n" +
    "Audience: " + (AUDIENCE || "not established — name the gap as an assumption, never a fact") + "\n" +
    "Constraints: " + (CONSTRAINTS || "not established — name the gap as an assumption, never a fact") + "\n\n" +
    "External evidence pack (GitHub + web, gathered before you spawned — cite it, verify against it):\n" +
    (evidencePack || "not gathered — every external claim is an assumption") + "\n\n" +
    "Ground every point in what is stated here; name assumptions as assumptions, never invent facts.\n" +
    "Cite a source for every load-bearing claim — file:line for in-repo, URL + access date for external; what has no source is an assumption, said as one.\n" +
    "Before writing your digest, attack your own strongest point once; argue what survives.\n" +
    "Return only your digest: angle, pitch, points (2-3 lines), watch — one line per field. " +
    "If you cannot satisfy your brief, say so in watch rather than working around it."
  );
}

async function main() {
  if (!PROBLEM) {
    return {
      conclusion:
        "No problem restatement was given — the panel wave has nothing to argue. " +
        "Run stage 1 in the session first (one clarifying question, the user " +
        "answers), then dispatch this workflow with that answer as the problem arg.",
      angles: [],
      verified: [],
      notCovered: ["no lens ran — the payload was empty (stage 1 is the session's, always)"],
      title: "Brainstorm panel wave — nothing to argue",
      markdown:
        "## Brainstorm panel wave — nothing to argue\n\nNo problem restatement was " +
        "given. Stage 1 (one clarifying question) is the session's, always — " +
        "answer it there, then re-run with `problem` set.",
    };
  }

  phase("Load the lens briefs and the shared panel protocol");

  async function readBrief(file) {
    const out = await probe("brief-probe", "cat " + shq(skillDir + "/agents/" + file));
    return out === null ? "" : out.trim();
  }

  const protocol = await readBrief("_panel-protocol.md");
  const briefBodies = await Promise.all(LENSES.map(function (l) { return readBrief(l.brief); }));
  const missingBriefs = LENSES.filter(function (_, i) { return !briefBodies[i]; });
  if (!protocol) log("panel protocol did not load — lenses argue from briefs plus mission lines only");
  missingBriefs.forEach(function (l) {
    log(l.name + ": brief did not load — arguing from the inline mission line");
  });

  function researchAsk() {
    return (
      "You are the evidence researcher of a brainstorming panel — a neutral " +
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
      "gathered (no tools, no network), return an empty pack — never invent a source."
    );
  }

  async function gatherEvidence() {
    const r = await agent(researchAsk(), { label: "evidence-researcher", schema: EVIDENCE_SCHEMA });
    const pack = r && typeof r.pack === "string" ? r.pack.trim() : "";
    if (!pack) {
      log("external evidence pack did not load — external claims in the digests are assumptions, not sourced");
      return "";
    }
    log("evidence pack gathered — " + pack.split("\n").filter(function (s) { return s.trim().indexOf("-") === 0; }).length + " sourced finding(s)");
    return pack;
  }

  phase("Gather external evidence from GitHub and the web");
  evidencePack = await gatherEvidence();

  function lensAsk(i) {
    const parts = [LENSES[i].mission];
    if (briefBodies[i]) parts.push(briefBodies[i]);
    if (protocol) parts.push(protocol);
    // the one-shot model: the system rides at the head of the ask
    return parts.join("\n\n---\n\n") + "\n\n===\n\nTask:\n\n" + payloadAsk();
  }

  phase("Argue the idea from three independent lenses");

  // Fresh, parallel, one payload — none sees another's output (D-002).
  const digests = (await pipeline(
    LENSES,
    function (l, i) {
      return agent(lensAsk(i), { label: l.label + "-lens", schema: DIGEST_SCHEMA });
    }
  ));
  const failed = LENSES.filter(function (_, i) { return !digests[i]; });
  failed.forEach(function (l) {
    log(l.name + ": returned no digest — the session must re-ask this lens");
  });
  const angles = digests.filter(function (d) { return d; });
  angles.forEach(function (d) {
    log(d.angle + ": digest returned — " + d.points.length + " point(s)");
  });

  phase("Assemble the labeled angles for the session");

  const md =
    "## The panel wave — " + NAME + "\n\n" +
    angles
      .map(function (d) {
        return (
          "### " + d.angle + "\n\n" +
          d.pitch + "\n\n" +
          d.points.map(function (p) { return "- " + p; }).join("\n") + "\n\n" +
          "Watch: " + d.watch + "\n"
        );
      })
      .join("\n") +
    "\nThe trade-off matrix, the socratic refinement and the handoff are the " +
    "session's — a workflow has no user-turn primitive (D-004).\n";

  return {
    conclusion:
      "The panel wave returned " + angles.length + " of 3 digests for " + NAME +
      " — present them distinctly labeled, build the trade-off matrix (no " +
      "recommendation), then refine socratically. The matrix, the refinement " +
      "and the handoff are the session's: a workflow has no user-turn " +
      "primitive (D-004).",
    angles: angles,
    verified: [
      "three lens seats spawned fresh and in parallel from one payload — none saw another's output",
      "each lens carried its full brief and the shared panel protocol, loaded from the skill dir at run time",
      "every digest follows the pinned grammar: angle, pitch, points (2-3 lines), watch",
    ].concat(
      evidencePack
        ? ["external evidence pack gathered from GitHub and the web before the lenses spawned"]
        : []
    ),
    notCovered: []
      .concat(
        !evidencePack
          ? ["external evidence pack did not load — external claims in the digests are assumptions, not sourced"]
          : []
      )
      .concat(
        missingBriefs.map(function (l) {
          return l.name + " argued from its inline mission line only — its brief did not load; re-run in-session with the full brief if its rubric matters here";
        })
      )
      .concat(
        failed.map(function (l) {
          return l.name + " returned no digest — the session must re-ask this lens before the matrix";
        })
      )
      .concat(
        !protocol
          ? ["the shared panel protocol did not load — lens rules (argue your lens, digest only) rode the mission lines only"]
          : []
      )
      .concat([
        "stage 1 (context discovery), stage 3 (trade-off matrix), stage 4 (refinement) and stage 5 (handoff) are the session's, always",
      ]),
    title: "Brainstorm panel wave — " + NAME,
    markdown: md,
  };
}

const result = await main();
result;
