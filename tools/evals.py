#!/usr/bin/env python3
"""Eval-case runner for the kit's standing eval scenarios.

Discovers cases from skills/*/evals/cases.md, tells mechanical from
conversational by each case's Run: line, and records per-criterion
verdicts under the case's skill's evals/results/. The runner records;
the observer judges. A conversational case may pin criteria to shell
`Check C<n>` bullets: run prints the mechanical verdict sheet and
validate executes the checks against --repo and merges them with the
transcript verdicts (a check wins over an observer verdict; a
contradiction is a finding). Held-out cases' criteria are read only at
judging time — never while authoring the skill.

Usage:
  evals.py list                             each case's latest result:
                                            fresh, stale, or none
  evals.py run <skill>/<case-id> [--overwrite]
                                            mechanical: executes and
                                            records; conversational with
                                            checks: dry-run sheet only
  evals.py validate <skill>/<case-id> [transcript] [--contract-bent T]
                                            [--repo DIR] [--overwrite]
  evals.py procedure <skill>/<case-id>      print the session procedure
  evals.py report                           per-skill benchmark: coverage,
                                            freshness, verdict pass-rate

Transcript verdict grammar (validate mode): any line naming a criterion
with a verdict and evidence, e.g. "- C1: pass — <evidence>" or
"C2: fail: <evidence>". Every criterion not covered by a Check bullet
needs a transcript verdict with evidence.
"""

import argparse
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES_GLOB = "skills/*/evals/cases.md"
RESULTS_DIR = "evals/results"
CASE_HEADING = re.compile(r"^## ([A-Za-z]+\d+)\s+—\s+(.+)$", re.M)
VERDICT_LINE = re.compile(
    r"^\s*[-*]?\s*C(\d+)\s*[:\-]\s*(pass|fail|finding)\b\s*[:\-—]?\s*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)
# What a run reads: a result is fresh while these are unchanged.
SURFACE_PARTS = ("SKILL.md", "agents", "commands", "contracts", "gates",
                 "protocol", "references", "scripts", "templates")
SURFACE_LINE = re.compile(r"^- surface: ([0-9a-f]{12})$", re.M)
VERDICTS_HEADING = re.compile(r"^#+\s*Verdicts\s*$", re.IGNORECASE | re.MULTILINE)


def _join_bullet(lines, start, first):
    """A bullet's full text: the first line's value plus its wrapped
    continuations (indented, never a new bullet)."""
    parts = [first]
    for line in lines[start + 1:]:
        if not line.startswith("  ") or line.lstrip().startswith("- "):
            break
        parts.append(line.strip())
    return " ".join(p for p in parts if p).strip()


def bullet_value(block, field):
    """A `- **<field>**:` bullet's value, continuations joined — a bullet's
    text wraps across lines, and the value is all of it."""
    lines = block.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^- \*\*" + field + r"\*\*: (.*)$", line)
        if m:
            return _join_bullet(lines, i, m.group(1))
    return ""


def checks_of(block):
    """The case's `- **Check C<n>**:` bullets as [(n, command)] — the
    criteria proven mechanically instead of judged from a transcript."""
    lines = block.splitlines()
    found = []
    for i, line in enumerate(lines):
        m = re.match(r"^- \*\*Check C(\d+)\*\*: (.*)$", line)
        if m:
            cmd = _join_bullet(lines, i, m.group(2))
            if cmd:
                found.append((int(m.group(1)), cmd))
    return found


def check_defects(case):
    """(out-of-range, duplicated) Check bullets — a malformed case,
    never a pass."""
    ns = [n for n, _ in case.checks]
    out_of_range = sorted({n for n in ns if not 1 <= n <= len(case.criteria)})
    dupes = sorted({n for n in ns if ns.count(n) > 1})
    return out_of_range, dupes


class Case:
    def __init__(self, skill, cid, title, run_value, criteria, source,
                 checks=None, held_out=False):
        self.skill = skill
        self.cid = cid
        self.title = title
        self.run_value = run_value
        self.criteria = criteria
        self.source = source
        self.checks = checks or []
        self.held_out = held_out

    @property
    def selector(self):
        return f"{self.skill}/{self.cid.lower()}"

    @property
    def conversational(self):
        return self.run_value.startswith("session:")

    @property
    def kind(self):
        return "conversational" if self.conversational else "mechanical"

    @property
    def checked(self):
        return {n for n, _ in self.checks}

    @property
    def procedure(self):
        return self.run_value[len("session:"):].strip()

    @property
    def results_path(self):
        return ROOT / "skills" / self.skill / RESULTS_DIR / f"{date.today():%Y-%m-%d}-{self.cid.lower()}.md"


def load_cases():
    cases = []
    for path in sorted(ROOT.glob(CASES_GLOB)):
        skill = path.parts[-3]
        text = path.read_text(encoding="utf-8")
        heads = list(CASE_HEADING.finditer(text))
        for i, h in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            block = text[h.start():end]
            run = bullet_value(block, "Run")
            crit = bullet_value(block, "Pass criteria")
            bullets = crit.split(";") if crit else []
            cases.append(Case(
                skill=skill,
                cid=h.group(1),
                title=h.group(2).strip(),
                run_value=run,
                criteria=[b for b in bullets if b.strip()],
                source=str(path.relative_to(ROOT)),
                checks=checks_of(block),
                held_out=bullet_value(block, "Held-out").lower() == "yes",
            ))
    return cases


def find_case(cases, selector):
    want = selector.strip().lower()
    for c in cases:
        if c.selector == want:
            return c
    return None


def surface_hash(skill):
    root = ROOT / "skills" / skill
    files = []
    for part in SURFACE_PARTS:
        p = root / part
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files += [f for f in p.rglob("*")
                      if f.is_file() and "__pycache__" not in f.parts]
    h = hashlib.sha256()
    for f in sorted(files):
        h.update(f.relative_to(root).as_posix().encode())
        h.update(b"\0")
        h.update(f.read_bytes())
        h.update(b"\0")
    return h.hexdigest()[:12]


def latest_result(case):
    """(state, path) of the case's newest result: none, unstamped, stale,
    or fresh against the skill's current surface."""
    hits = sorted((ROOT / "skills" / case.skill / RESULTS_DIR).glob(
        f"*-{case.cid.lower()}.md"))
    if not hits:
        return "none", None
    m = SURFACE_LINE.search(hits[-1].read_text(encoding="utf-8"))
    if not m:
        return "unstamped", hits[-1]
    state = "fresh" if m.group(1) == surface_hash(case.skill) else "stale"
    return state, hits[-1]


def repo_context():
    """Where the case ran, so real-repo evidence labels itself — a
    result that claims a real repo must name it (kit rubric S4)."""
    try:
        r = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, cwd=ROOT, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return f"{ROOT.name} (no remote — scratch/local)"


def run_checks(case, repo):
    """Execute a case's Check bullets against repo — per-criterion
    mechanical verdicts with run evidence, judged by exit code."""
    out = []
    for n, cmd in case.checks:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           cwd=repo)
        tail = (r.stdout.strip() or r.stderr.strip()).splitlines()
        evidence = f"check `{cmd}` exited {r.returncode}"
        if tail:
            evidence += "; " + tail[-1][:200]
        out.append((n, "pass" if r.returncode == 0 else "fail", evidence))
    return out


def recorded_verdicts(path):
    """(passed, total, failed) from a result file's Verdicts section —
    the Findings section repeats the fails and must not count twice."""
    if path is None:
        return 0, 0, 0
    section = re.split(r"^#+\s+Findings", path.read_text(encoding="utf-8"),
                       maxsplit=1, flags=re.M)[0]
    rows = [(int(cid), v.lower())
            for cid, v, _ in VERDICT_LINE.findall(section)]
    passed = sum(1 for _, v in rows if v == "pass")
    failed = sum(1 for _, v in rows if v == "fail")
    return passed, len(rows), failed


def render_results(case, verdicts, findings, contract_bent, via):
    lines = [
        f"# Eval result — {case.selector}",
        "",
        f"- selector: {case.selector}",
        f"- date: {date.today():%Y-%m-%d}",
        f"- kind: {case.kind}",
        f"- source: {case.source}",
        f"- repo: {repo_context()}",
        f"- surface: {surface_hash(case.skill)}",
        f"- recorded via: {via}",
        "",
        "## Verdicts",
        "",
    ]
    for cid, verdict, evidence in verdicts:
        lines.append(f"- C{cid}: {verdict} — {evidence}")
    lines += ["", "## Findings", ""]
    if findings:
        for cid, evidence in findings:
            lines.append(f"- C{cid}: {evidence}")
    else:
        lines.append("None — every criterion passed.")
    if contract_bent:
        lines += ["", "## Contract-bent", "", contract_bent]
    return "\n".join(lines) + "\n"


def write_results(case, content, overwrite):
    dest = case.results_path
    if dest.exists() and not overwrite:
        print(f"refusing to overwrite {dest} — pass --overwrite to replace recorded evidence", file=sys.stderr)
        return 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dest.parent, suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, dest)
    return 0


def print_receipt(case, verdicts, path):
    print(f"case: {case.selector} ({case.kind})")
    for cid, verdict, _ in verdicts:
        print(f"  C{cid}: {verdict}")
    print(f"results: {path}")


def cmd_list(_):
    cases = load_cases()
    rc = 0
    for c in cases:
        kind = c.kind if c.run_value else "malformed (no Run: bullet)"
        if not c.run_value:
            rc = 2
        print(f"{c.selector:26} {kind:14} {latest_result(c)[0]:9} {c.source}")
    print(f"{len(cases)} case(s)")
    return rc


def cmd_run(args):
    case = find_case(load_cases(), args.selector)
    if case is None:
        print(f"unknown case selector: {args.selector}", file=sys.stderr)
        return 2
    if not case.run_value:
        print(f"{case.selector} has no Run: bullet — fix the case file", file=sys.stderr)
        return 2
    if case.conversational:
        if case.checks:
            oor, dupes = check_defects(case)
            if oor or dupes:
                print(f"{case.selector} has malformed Check bullets "
                      f"(out of range: {oor or 'none'}; duplicated: {dupes or 'none'}) — fix the case file",
                      file=sys.stderr)
                return 2
            sheet = run_checks(case, os.getcwd())
            for n, v, ev in sheet:
                print(f"  C{n}: {v} — {ev}")
            unjudged = [i + 1 for i in range(len(case.criteria))
                        if (i + 1) not in case.checked]
            if unjudged:
                print("judged in session (no Check bullet): "
                      + ", ".join(f"C{n}" for n in unjudged))
            print("dry run only — run the session, then record with: "
                  f"validate {case.selector} <transcript> --repo <scratch>")
            return 0 if all(v == "pass" for _, v, _ in sheet) else 1
        print(f"{case.selector} is conversational — session procedure:")
        print(case.procedure)
        print("run it in a session, then record with: validate")
        return 0
    r = subprocess.run(case.run_value, shell=True, capture_output=True, text=True)
    verdict = "pass" if r.returncode == 0 else "fail"
    tail = (r.stdout.strip() or r.stderr.strip()).splitlines()
    evidence = f"command `{case.run_value}` exited {r.returncode}"
    if tail:
        evidence += "; " + tail[-1][:200]
    verdicts = [(i + 1, verdict, evidence) for i in range(len(case.criteria))] or [(1, verdict, evidence)]
    findings = [(cid, ev) for cid, v, ev in verdicts if v == "fail"]
    content = render_results(case, verdicts, findings, "", via=f"run (exit {r.returncode})")
    rc = write_results(case, content, args.overwrite)
    if rc != 0:
        return rc
    print_receipt(case, verdicts, case.results_path)
    return 0 if r.returncode == 0 else 1


def cmd_validate(args):
    case = find_case(load_cases(), args.selector)
    if case is None:
        print(f"unknown case selector: {args.selector}", file=sys.stderr)
        return 2
    if not case.run_value:
        print(f"{case.selector} has no Run: bullet — fix the case file", file=sys.stderr)
        return 2
    if not case.conversational:
        print(f"{case.selector} is mechanical — use: run", file=sys.stderr)
        return 2
    if not args.transcript:
        print(f"{case.selector} session procedure:")
        print(case.procedure)
        return 0
    text = Path(args.transcript).read_text(encoding="utf-8")
    if not case.criteria:
        print(f"{case.selector} parses to zero criteria — fix the case file's Pass criteria bullet", file=sys.stderr)
        return 2
    oor, dupes = check_defects(case)
    if oor or dupes:
        print(f"{case.selector} has malformed Check bullets "
              f"(out of range: {oor or 'none'}; duplicated: {dupes or 'none'}) — fix the case file",
              file=sys.stderr)
        return 2
    mechanical = run_checks(case, args.repo) if case.checks else []
    found = {}
    for m in VERDICT_LINE.finditer(text):
        cid = int(m.group(1))
        verdict = m.group(2).lower()
        evidence = m.group(3).strip()
        if evidence:
            found[cid] = (cid, verdict, evidence)
    missing = [i + 1 for i in range(len(case.criteria))
               if (i + 1) not in case.checked and (i + 1) not in found]
    if missing or (not found and not mechanical):
        print(
            f"incomplete transcript: criteria missing or evidence-less: "
            f"{', '.join('C%d' % c for c in missing) or '(none parsed)'} — nothing written",
            file=sys.stderr,
        )
        return 1
    checks = {n: (v, ev) for n, v, ev in mechanical}
    ordered = []
    contradictions = []
    for i in range(len(case.criteria)):
        n = i + 1
        if n in checks:
            v, ev = checks[n]
            if n in found and found[n][1] != v:
                contradictions.append(
                    (n, f"observer verdict ({found[n][1]}) contradicts the check — {found[n][2]}"))
            ordered.append((n, v, ev))
        else:
            ordered.append(found[n])
    findings = [(cid, ev) for cid, v, ev in ordered if v == "fail"] + contradictions
    content = render_results(case, ordered, findings, args.contract_bent or "", via="validate")
    rc = write_results(case, content, args.overwrite)
    if rc != 0:
        return rc
    print_receipt(case, ordered, case.results_path)
    return 0


def cmd_procedure(args):
    case = find_case(load_cases(), args.selector)
    if case is None:
        print(f"unknown case selector: {args.selector}", file=sys.stderr)
        return 2
    if case.conversational:
        print(f"{case.selector} session procedure:")
        print(case.procedure)
        if case.held_out:
            print("held-out case — its Pass criteria are read only at judging time")
    else:
        print(f"{case.selector} is mechanical — Run command:")
        print(case.run_value)
    return 0


def cmd_report(_):
    cases = load_cases()
    if not cases:
        print("no cases discovered")
        return 0
    header = (f"{'skill':14} {'cases':>5} {'heldout':>7} {'recorded':>8} "
              f"{'fresh':>6} {'unstamped':>9} {'stale':>6} {'pass-rate':>10} {'findings':>8}")
    print(header)
    totals = dict(cases=0, heldout=0, recorded=0, fresh=0, unstamped=0,
                  stale=0, passed=0, total=0, findings=0)
    by_skill = {}
    for c in cases:
        by_skill.setdefault(c.skill, []).append(c)
    for skill in sorted(by_skill):
        row = dict(cases=0, heldout=0, recorded=0, fresh=0, unstamped=0,
                   stale=0, passed=0, total=0, findings=0)
        for c in by_skill[skill]:
            row["cases"] += 1
            row["heldout"] += 1 if c.held_out else 0
            state, path = latest_result(c)
            if state != "none":
                row["recorded"] += 1
            if state in ("fresh", "unstamped", "stale"):
                row[state] += 1
            passed, total, failed = recorded_verdicts(path)
            row["passed"] += passed
            row["total"] += total
            row["findings"] += failed
        rate = f"{row['passed']}/{row['total']}" if row["total"] else "—"
        print(f"{skill:14} {row['cases']:>5} {row['heldout']:>7} {row['recorded']:>8} "
              f"{row['fresh']:>6} {row['unstamped']:>9} {row['stale']:>6} {rate:>10} {row['findings']:>8}")
        for k in totals:
            totals[k] += row[k]
    rate = f"{totals['passed']}/{totals['total']}" if totals["total"] else "—"
    print(f"{'corpus':14} {totals['cases']:>5} {totals['heldout']:>7} {totals['recorded']:>8} "
          f"{totals['fresh']:>6} {totals['unstamped']:>9} {totals['stale']:>6} {rate:>10} {totals['findings']:>8}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list every discovered case with kind + source")
    r = sub.add_parser("run", help="execute a mechanical case; conversational prints the procedure")
    r.add_argument("selector")
    r.add_argument("--overwrite", action="store_true", help="replace an existing results file")
    v = sub.add_parser("validate", help="record a conversational case's transcript verdicts")
    v.add_argument("selector")
    v.add_argument("transcript", nargs="?", help="transcript file carrying per-criterion verdicts")
    v.add_argument("--contract-bent", help="record the contract bent (a kill finding)")
    v.add_argument("--repo", default=".",
                   help="working dir for the case's Check bullets (the prepared scratch repo)")
    v.add_argument("--overwrite", action="store_true")
    pr = sub.add_parser("procedure", help="print a case's session procedure (or Run command)")
    pr.add_argument("selector")
    sub.add_parser("report", help="per-skill eval benchmark: coverage, freshness, pass-rate")
    args = p.parse_args(argv)
    return {"list": cmd_list, "run": cmd_run, "validate": cmd_validate,
            "procedure": cmd_procedure, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
