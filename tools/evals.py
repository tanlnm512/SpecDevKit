#!/usr/bin/env python3
"""Eval-case runner for the kit's standing eval scenarios.

Discovers cases from skills/*/evals/cases.md (D-004), tells mechanical
from conversational by each case's Run: line (D-001), and records
per-criterion verdicts under the case's skill's evals/results/ (D-002).
The runner records; the observer judges (D-005).

Usage:
  evals.py list
  evals.py run <skill>/<case-id> [--overwrite]
                                            mechanical cases only
  evals.py validate <skill>/<case-id> [transcript] [--contract-bent T]
                                            [--overwrite]
  evals.py procedure <skill>/<case-id>      print the session procedure

Transcript verdict grammar (validate mode): any line naming a criterion
with a verdict and evidence, e.g. "- C1: pass — <evidence>" or
"C2: fail: <evidence>". Every enumerated criterion needs both.
"""

import argparse
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
VERDICTS_HEADING = re.compile(r"^#+\s*Verdicts\s*$", re.IGNORECASE | re.MULTILINE)


def bullet_value(block, field):
    """A `- **<field>**:` bullet's value, continuations joined — a bullet's
    text wraps across lines, and the value is all of it (D-002)."""
    lines = block.splitlines()
    start = None
    for i, line in enumerate(lines):
        m = re.match(r"^- \*\*" + field + r"\*\*: (.*)$", line)
        if m:
            start = i
            parts = [m.group(1)]
            break
    if start is None:
        return ""
    for line in lines[start + 1:]:
        if not line.startswith("  ") or line.lstrip().startswith("- "):
            break
        parts.append(line.strip())
    return " ".join(p for p in parts if p).strip()


class Case:
    def __init__(self, skill, cid, title, run_value, criteria, source):
        self.skill = skill
        self.cid = cid
        self.title = title
        self.run_value = run_value
        self.criteria = criteria
        self.source = source

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
            ))
    return cases


def find_case(cases, selector):
    want = selector.strip().lower()
    for c in cases:
        if c.selector == want:
            return c
    return None


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


def render_results(case, verdicts, findings, contract_bent, via):
    lines = [
        f"# Eval result — {case.selector}",
        "",
        f"- selector: {case.selector}",
        f"- date: {date.today():%Y-%m-%d}",
        f"- kind: {case.kind}",
        f"- source: {case.source}",
        f"- repo: {repo_context()}",
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
        print(f"{c.selector:26} {kind:14} {c.source}")
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
    found = {}
    for m in VERDICT_LINE.finditer(text):
        cid = int(m.group(1))
        verdict = m.group(2).lower()
        evidence = m.group(3).strip()
        if evidence:
            found[cid] = (cid, verdict, evidence)
    missing = [i + 1 for i in range(len(case.criteria)) if (i + 1) not in found]
    if missing or not found:
        print(
            f"incomplete transcript: criteria missing or evidence-less: "
            f"{', '.join('C%d' % c for c in missing) or '(none parsed)'} — nothing written",
            file=sys.stderr,
        )
        return 1
    ordered = [found[i + 1] for i in range(len(case.criteria))]
    findings = [(cid, ev) for cid, v, ev in ordered if v == "fail"]
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
    else:
        print(f"{case.selector} is mechanical — Run command:")
        print(case.run_value)
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
    v.add_argument("--contract-bent", help="record the contract bent (FR-003 kill finding)")
    v.add_argument("--overwrite", action="store_true")
    pr = sub.add_parser("procedure", help="print a case's session procedure (or Run command)")
    pr.add_argument("selector")
    args = p.parse_args(argv)
    return {"list": cmd_list, "run": cmd_run, "validate": cmd_validate, "procedure": cmd_procedure}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
