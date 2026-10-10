#!/usr/bin/env python3
"""Mechanical half of the kit grading rubric (rubrics/kit-grading-rubric.md).

Discovers every skill and agent brief; computes
the machine-decidable checks the rubric names; prints a markdown report
with per-dimension mechanical scores plus the unfilled judgment
worksheet. The report is the deliverable — the exit status reflects
only internal errors, never a low grade.

Usage:
  grade.py [--skip-suites] [--skip-sync] [--json] [--out FILE]

Skipped checks are reported as skipped, never credited (rubric §4).
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"

# Dimension tables mirror rubrics/kit-grading-rubric.md §3 exactly;
# tools/tests/test_grade.py fails on any drift between the two.
SKILL_DIMS = [
    ("S1", "Contract & prompt design", 20, 0),
    ("S2", "Architecture & state model", 20, 0),
    ("S3", "Verification machinery", 15, 10),
    ("S4", "Evidence & evals", 20, 20),
    ("S5", "Context efficiency", 10, 5),
    ("S6", "Honesty & dogfooding", 15, 10),
]
AGENT_DIMS = [
    ("A1", "Structure & digest contract", 25, 25),
    ("A2", "Separation of powers", 25, 20),
    ("A3", "Cost tiering & portability", 15, 10),
    ("A4", "Anti-theater & precision language", 20, 0),
    ("A5", "Method breadth & actionability", 15, 0),
]

JUDGMENT_ITEMS = {
    "skill": [
        ("S1", "Contract & prompt design", 20,
         "ranked principles; anti-patterns name failure modes; grammar contracts; trigger-precise use"),
        ("S2", "Architecture & state model", 20,
         "one mechanical state source; gates never auto-satisfied; exclusive ownership; bounded loops"),
        ("S3", "Checker bites (judgment half)", 5,
         "mentally mutate a real artifact — does the checker catch it?"),
        ("S5", "Layering (judgment half)", 5,
         "heavy content on-demand, not one flat per-run read"),
        ("S6", "Operator-verifiable claims (judgment half)", 5,
         "in-run claims checkable without trusting the session"),
    ],
    "agent": [
        ("A2", "Blocker routing (judgment half)", 5,
         "blockers route to the orchestrator; no silent scope growth"),
        ("A3", "Tier fit (judgment half)", 5,
         "tier assignment fits the role's judgment load"),
        ("A4", "Anti-theater & precision language", 20,
         "refuses speculation; requires reachable evidence; zero-findings-is-success"),
        ("A5", "Method breadth & actionability", 15,
         "enumerable without anchoring; steps executable as written"),
    ],
}

HARDCODED_MODEL = re.compile(
    r"^model:\s*(sonnet|opus|haiku|gpt-[\w.-]*|glm-[\w.-]*|"
    r"gemini-[\w.-]*|claude-[\w.-]*)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# The kit's real brief grammar: spec-to-prod roles carry Method/Done
# when, panel agents carry How to work/Output. Both are complete.
AGENT_SECTIONS = [
    ("frontmatter name", re.compile(r"^name:\s+\S", re.M), 3),
    ("frontmatter description", re.compile(r"^description:", re.M), 2),
    ("mission", re.compile(r"\*\*Mission\*\*", re.M), 4),
    ("method", re.compile(r"^#{1,3}\s+(?:How to work|Method)\b", re.M), 4),
    ("output contract", re.compile(r"^#{1,3}\s+(?:Output|Done when)\b", re.M), 4),
    (
        "rules barrier",
        re.compile(r"^#{1,3}\s+(?:Guardrails|Hard rules|Readers never edit|Digest only)", re.M),
        4,
    ),
    ("digest grammar", re.compile(r"digest:|findings list|angle:", re.I), 4),
]


def sh(cmd, cwd=None, timeout=300):
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
    )


def bucket(n, brackets, floor):
    for limit, score in brackets:
        if n <= limit:
            return score
    return floor


def discover_skills():
    return sorted(
        p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md") if p.is_file()
    )


def discover_agents():
    out = []
    for skill in discover_skills():
        for p in sorted((SKILLS_DIR / skill / "agents").glob("*.md")):
            if p.name.startswith("_"):
                continue
            out.append((skill, p))
    return out


def skill_protocol_text(skill):
    agents_dir = SKILLS_DIR / skill / "agents"
    for name in ("_shared-protocol.md", "_panel-protocol.md"):
        p = agents_dir / name
        if p.exists():
            return p.read_text(encoding="utf-8")
    return ""


# ---------------------------------------------------------------- skill ----


def load_kit_cases():
    sys.path.insert(0, str(ROOT / "tools"))
    import evals as kit_evals  # reuse the standing loader, not a copy

    return kit_evals.load_cases()


def skill_eval_points(skill, cases):
    """S4 — corpus shape: coverage, repeat runs, real-repo evidence,
    breadth. Counts come from the recorded results the eval runner
    already owns; no case text is re-parsed here."""
    results_dir = SKILLS_DIR / skill / "evals" / "results"
    mine = [c for c in cases if c.skill == skill]
    covered = 0
    repeats = 0
    for c in mine:
        dates = set()
        for p in results_dir.glob(f"*-{c.cid.lower()}.md"):
            m = re.match(r"(\d{4}-\d{2}-\d{2})-", p.name)
            if m:
                dates.add(m.group(1))
        covered += bool(dates)
        repeats += len(dates) >= 2
    coverage_pts = round(8 * covered / len(mine), 2) if mine else 0
    # A result self-labels its repo (evals.py render_results): a real
    # remote counts; scratch/local runs say so and never do.
    real_repo = any(
        re.search(r"^- repo: \S*(git|github|http)", p.read_text(encoding="utf-8"), re.I | re.M)
        or re.search(r"real[- ]repo|working repo", p.read_text(encoding="utf-8"), re.I)
        for p in results_dir.glob("*.md")
    )
    every_skill = all(
        any((SKILLS_DIR / s / "evals" / "results").glob("*.md"))
        for s in discover_skills()
    )
    return {
        "S4": {
            "earned": coverage_pts + (4 if repeats else 0)
            + (4 if real_repo else 0) + (4 if every_skill else 0),
            "max": 20,
            "detail": (
                f"coverage {covered}/{len(mine) or 1} cases with results "
                f"(=>{coverage_pts}/8), repeat-run cases: {repeats} (4), "
                f"real-repo result: {'yes' if real_repo else 'no'} (4), "
                f"all-skills corpus: {'yes' if every_skill else 'no'} (4)"
            ),
        }
    }


def skill_dogfood_targets(skill):
    """Every in-repo artifact of the skill's own type, with the command
    that proves it passes its own gate — the check that catches a kit
    whose outputs drift past its own checkers."""
    if skill == "spec-brainstorming":
        checker = SKILLS_DIR / skill / "scripts" / "check.py"
        return [
            (str(p.relative_to(ROOT)), [sys.executable, str(checker), str(p)])
            for p in sorted(ROOT.glob("brainstorms/*.md"))
        ]
    if skill == "spec-to-prod":
        checker = SKILLS_DIR / skill / "scripts" / "check.py"
        dirs = [SKILLS_DIR / skill / "examples" / "mini-spec" / "specs" / "mini-spec"]
        dirs += [
            p.parent
            for p in sorted((ROOT / "specs").glob("*/spec.md"))
            if p.parent.name not in ("context", "archive")
        ]
        return [
            (str(d.relative_to(ROOT)), [sys.executable, str(checker), str(d)])
            for d in dirs
        ]
    if skill == "spec-code-review":
        return [
            (f"examples/review-target/{rel}", None)
            for rel in ("base/app.py", "change.diff", "EXPECTED.md")
        ]
    return []


def skill_dogfood(skill):
    targets = skill_dogfood_targets(skill)
    if not targets:
        # Distinguish "nothing of its type exists" from a mapping blind
        # spot: an unmapped skill must be named, not silently zeroed.
        known = skill in ("spec-brainstorming", "spec-to-prod", "spec-code-review")
        return {"earned": 0, "max": 7, "detail": (
            f"NO DOGFOOD MAPPING for skill '{skill}' — add one to "
            "skill_dogfood_targets or document why none applies"
            if not known else "no own-type artifacts found in this repo")}
    passed, misses = 0, []
    for name, cmd in targets:
        if cmd is None:
            ok = (SKILLS_DIR / skill / name).exists()
        else:
            try:
                ok = sh(cmd).returncode == 0
            except subprocess.TimeoutExpired:
                ok = False
        passed += ok
        if not ok:
            misses.append(name)
    return {
        "earned": round(7 * passed / len(targets), 2),
        "max": 7,
        "detail": f"own-artifact dogfood {passed}/{len(targets)}"
        + (f" — FAILING: {', '.join(misses)}" if misses else ""),
    }


def grade_skill(skill, cases, skip_suites):
    d = SKILLS_DIR / skill
    checks = {}

    pack_files = ["SKILL.md", "VERSION", "CHANGELOG.md",
                  ".claude-plugin/plugin.json", "evals/cases.md", "tests/run.sh"]
    pack_hits = sum((d / f).exists() for f in pack_files)
    checker = (d / "scripts" / "check.py").exists() or (d / "scripts" / "gate.sh").exists()
    tests = sorted((d / "tests").glob("test_*.py"))
    suite_pass = None
    suite_note = "skipped (--skip-suites)"
    if not skip_suites and tests:
        passed = 0
        for t in tests:
            try:
                r = sh([sys.executable, str(t)], cwd=d, timeout=600)
            except subprocess.TimeoutExpired:
                r = None
            passed += r is not None and r.returncode == 0
        suite_pass = passed == len(tests)
        suite_note = f"suite {passed}/{len(tests)} files passing"
    s3_suite = 5.0 if suite_pass else 0.0
    checks["S3"] = {
        "earned": round(3 * pack_hits / len(pack_files), 2) + (2 if checker else 0) + s3_suite,
        "max": 10,
        "detail": f"packaging {pack_hits}/{len(pack_files)}, checker "
                  f"{'present' if checker else 'MISSING'}, {suite_note}",
    }
    checks.update(skill_eval_points(skill, cases))

    lines = len((d / "SKILL.md").read_text(encoding="utf-8").splitlines())
    s5 = bucket(lines, [(300, 5), (600, 4), (900, 3)], 2)
    checks["S5"] = {"earned": s5, "max": 5, "detail": f"SKILL.md {lines} lines"}

    dog = skill_dogfood(skill)
    oi = d / "observations" / "open-items.md"
    disclosed = oi.exists() and bool(
        re.search(r"accepted limitation|known.{0,40}limitation",
                  oi.read_text(encoding="utf-8"), re.I | re.S)
    )
    checks["S6"] = {
        "earned": dog["earned"] + (3 if disclosed else 0),
        "max": 10,
        "detail": dog["detail"] + f"; limitations disclosed: {'yes' if disclosed else 'no'}",
    }
    return {"unit": f"skill:{skill}", "lines": lines, "suite_pass": suite_pass,
            "checks": checks}


# --------------------------------------------------------------- agent -----


def grade_agent(skill, path):
    text = path.read_text(encoding="utf-8")
    # Powers rules live in the prepend-protocol the brief itself names —
    # grade the contract the agent actually reads: brief + protocol.
    effective = text + "\n" + skill_protocol_text(skill)

    earned, missing = 0, []
    for name, rx, pts in AGENT_SECTIONS:
        # Frontmatter is the brief's own; content sections may be
        # delegated to the prepend-protocol (the kit's DRY contract:
        # "your brief does not repeat these").
        hay = text if name.startswith("frontmatter") else effective
        if rx.search(hay):
            earned += pts
        else:
            missing.append(name)

    disallowed = re.search(r"^disallowedTools:\n((?:\s+-\s+\S+.*\n)+)", text, re.M)
    blocked = disallowed.group(1) if disallowed else ""
    # A disallowedTools entry carrying Agent/Task/SendMessage is a
    # stronger spawn prohibition than prose — count either.
    no_spawn = bool(re.search(r"never spawn|do (?:not|NOT) spawn", effective, re.I)) or bool(
        re.search(r"\bAgent\b|\bTask\b|\bSendMessage\b", blocked)
    )
    no_commit = bool(re.search(r"never commit|NEVER commit|do (?:not|NOT) commit", effective, re.I))
    tools_line = re.search(r"^tools:\s*(.+)$", text, re.M)
    write_scoped = bool(re.search(r"\bWrite\b|\bEdit\b", blocked)) or tools_line is not None

    model_hits = HARDCODED_MODEL.findall(text)
    lines = len(text.splitlines())
    checks = {
        "A1": {"earned": earned, "max": 25,
               "detail": ("all sections present" if not missing
                          else f"missing: {', '.join(missing)}")},
        "A2": {"earned": (5 if no_spawn else 0) + (5 if no_commit else 0)
                        + (10 if write_scoped else 0),
               "max": 20,
               "detail": f"no-spawn {'Y' if no_spawn else 'N'}, no-commit "
                         f"{'Y' if no_commit else 'N'}, write-scope "
                         f"{'Y' if write_scoped else 'N'} (brief+protocol)"},
        "A3": {"earned": max(0, 10 - 3 * len(model_hits)), "max": 10,
               "detail": ("no hardcoded model names" if not model_hits
                          else f"hardcoded model: {', '.join(model_hits)}")},
    }
    return {"unit": f"agent:{path.stem}", "skill": skill, "lines": lines,
            "checks": checks}



# --------------------------------------------------------------- report ----


def mech_score(unit, dims):
    """Weighted mechanical composite over the dimensions that carry
    mechanical points; judgment dimensions are excluded by design."""
    total_w = earned_w = 0.0
    for did, _, _, mech in dims:
        c = unit["checks"].get(did)
        if not mech or c is None or not c["max"]:
            continue
        total_w += mech
        earned_w += mech * min(10.0, 10.0 * c["earned"] / c["max"])
    return round(earned_w / total_w, 2) if total_w else None


def render_report(data):
    lines = [
        f"# Kit grade report — {date.today():%Y-%m-%d}",
        "",
        "Mechanical half, computed by `tools/grade.py`. Fill each unit's",
        "judgment checklist per `rubrics/kit-grading-rubric.md` SS5-6 to",
        "reach the final composite.",
        "",
        "## Repo context",
        f"- drift-check: {'PASS' if data['drift_ok'] else 'FAIL'}",
        f"- sync --check: "
        + ("TIMED OUT (reported, not credited)" if data["stale"] < 0
           else f"{data['stale']} stale deployed file(s)"
                + (" — apply rubric principle 3 (dogfood cap)" if data["stale"] else "")),
        "",
    ]
    for label, units, dims, jkey in (
        ("Skills", data["skills"], SKILL_DIMS, "skill"),
        ("Agents", data["agents"], AGENT_DIMS, "agent"),
    ):
        lines.append(f"## {label}")
        for u in units:
            score = mech_score(u, dims)
            lines.append(f"### {u['unit']} — mechanical {score}/10 · {u['lines']} lines")
            lines.append("| dim | earned/max | detail |")
            lines.append("|-----|-----------|--------|")
            for did, name, _, mech in dims:
                c = u["checks"].get(did)
                if c and mech:
                    lines.append(f"| {did} {name} | {c['earned']}/{c['max']} | {c['detail']} |")
            lines.append("")
            lines.append("Judgment (fill, with verbatim evidence):")
            for jid, title, pts, prompt in JUDGMENT_ITEMS[jkey]:
                lines.append(f"- [ ] **{jid} {title} ({pts} pts)** — {prompt} → `__ /10`")
            lines.append("")
    lines.append("## Defects found this session (assessor fills)")
    lines.append("- (path + why it caps a score, per rubric principle 3)")
    return "\n".join(lines) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--skip-suites", action="store_true",
                   help="do not run skill test suites (reported as skipped)")
    p.add_argument("--skip-sync", action="store_true",
                   help="do not run tools/sync.sh --check")
    p.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    p.add_argument("--out", help="write the report to this path as well")
    args = p.parse_args(argv)

    drift = sh([sys.executable, str(ROOT / "tools" / "drift-check.py")])
    stale = 0
    if not args.skip_sync:
        try:
            sync = sh(["bash", str(ROOT / "tools" / "sync.sh"), "--check"], timeout=120)
            stale = len(re.findall(r"^STALE ", sync.stdout + sync.stderr, re.M))
        except subprocess.TimeoutExpired:
            stale = -1

    tools_suite_pass = None
    if not args.skip_suites:
        passed = 0
        tests = sorted((ROOT / "tools" / "tests").glob("test_*.py"))
        for t in tests:
            try:
                r = sh([sys.executable, str(t)], cwd=ROOT / "tools", timeout=900)
            except subprocess.TimeoutExpired:
                r = None
            passed += r is not None and r.returncode == 0
        tools_suite_pass = passed == len(tests)

    cases = load_kit_cases()
    skills = [grade_skill(s, cases, args.skip_suites) for s in discover_skills()]
    suite_by_skill = {u["unit"].split(":", 1)[1]: u["suite_pass"] for u in skills}
    agents = [grade_agent(s, p) for s, p in discover_agents()]
    data = {
        "date": str(date.today()),
        "drift_ok": drift.returncode == 0,
        "stale": stale,
        "skills": skills,
        "agents": agents,
    }
    report = render_report(data)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
    print(json.dumps(data, indent=2) if args.json else report, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
