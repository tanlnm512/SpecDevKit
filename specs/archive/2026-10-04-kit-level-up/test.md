# Test Cases: kit-level-up

**Spec**: [spec.md](spec.md) | **Created**: 2026-10-03
Black-box, business-language verification traced to requirements. Each case
has an observable pass condition. No implementation details.

## TC-001 — Baseline pass files a dated transcript for every in-scope eval case
- **Story**: US1 · **Traces to**: FR-001, AC1
- **Given** the fifteen in-scope standing eval cases across the three skills (spec-code-review E1–E4, spec-brainstorming B1–B5, spec-to-prod E1–E6)
- **When** the baseline pass completes
- **Then** each case has exactly one filed transcript under its skill's evals results folder, named by run date and case id, fifteen in total and none named off-convention
- **Pass condition**: `test "$(find skills -type f -path '*evals/results/*.md' | wc -l | tr -d ' ')" -eq 15 && test "$(find skills -type f -path '*evals/results/*.md' ! -name '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-*.md' | wc -l | tr -d ' ')" -eq 0`

## TC-002 — Every filed transcript carries per-criterion verdicts
- **Story**: US1 · **Traces to**: FR-001, AC1
- **Given** the fifteen filed baseline transcripts
- **When** each transcript is inspected
- **Then** every one records a verdict — pass, fail, or finding — for its case's pass criteria, with no transcript filed as a bare log
- **Pass condition**: `test "$(grep -rilE 'pass|fail|finding' skills/*/evals/results | wc -l | tr -d ' ')" -eq 15`

## TC-003 — The never-average judging rule stays stated in every case file (standing guard)
- **Story**: US1 · **Traces to**: FR-002
- **Given** the three eval case files, each already stating that a failed criterion is a finding and is never averaged
- **When** any case is judged — by the runner or by a human following the same rule
- **Then** the rule the requirement relies on is present in all three files; the guard fails if any file ever drops it
- **Pass condition**: `tr '\n' ' ' < skills/spec-code-review/evals/cases.md | grep -qiE "never average|don't average" && tr '\n' ' ' < skills/spec-brainstorming/evals/cases.md | grep -qiE "never average|don't average" && tr '\n' ' ' < skills/spec-to-prod/evals/cases.md | grep -qiE "never average|don't average"`

## TC-004 — A failed criterion is recorded as criterion, evidence, and finding — never averaged
- **Story**: US1 · **Traces to**: FR-002
- **Given** a baseline case run in which at least one pass criterion failed
- **When** that run's results file is read
- **Then** the file names the failed criterion, quotes the transcript evidence for it, and records the finding — findings aggregate per case, and no average across criteria or cases appears anywhere
- **Pass condition**: Manual observation — in the results file of any run with a failed criterion, the failure is recorded as criterion plus quoted transcript evidence plus finding, and no average or aggregate score across criteria or cases appears anywhere in the file.

## TC-005 — A contract-bent case stops as a kill-criterion finding, never a silent workaround
- **Story**: US1 · **Traces to**: FR-003, AC2
- **Given** a case whose pass criteria cannot all be met inside the skill's own contracts
- **When** the run attempts it
- **Then** the run records the contract bent, stops that case with a kill-criterion finding, and falls back to the seeded fixture path where one exists — no criterion is recorded as passed through improvisation, and nothing is worked around off the record
- **Pass condition**: Manual observation — for any case that could not complete inside the skill's own contracts, the recorded finding names the bent contract and the case is marked stopped as a kill-criterion finding, with no criterion passed via a step outside the skill's contracts and no workaround absent from the record.

## TC-006 — The runner lists every case across the three skills with kind and source file
- **Story**: US2 · **Traces to**: FR-004, AC3
- **Given** the runner installed in the kit's tools folder
- **When** it is invoked to list cases
- **Then** it prints all fifteen cases, each labeled mechanical or conversational, each naming its source case file, spanning all three skills
- **Pass condition**: `test "$(python3 tools/evals.py list | grep -c 'cases.md')" -eq 15 && test "$(python3 tools/evals.py list | grep 'cases.md' | grep -icE 'mechanical|conversational')" -eq 15 && test "$(python3 tools/evals.py list | grep -oE '(spec-code-review|spec-brainstorming|spec-to-prod)/evals/cases\.md' | sort -u | wc -l | tr -d ' ')" -eq 3`

## TC-007 — The runner is stdlib-only
- **Story**: US2 · **Traces to**: FR-004
- **Given** the runner's source
- **When** its imports are inspected
- **Then** every imported module is Python standard library — no third-party dependency is introduced
- **Pass condition**: `python3 -c "import ast,sys; t=ast.parse(open('tools/evals.py').read()); m={a.name.split('.')[0] for n in ast.walk(t) if isinstance(n,ast.Import) for a in n.names}; m|={n.module.split('.')[0] for n in ast.walk(t) if isinstance(n,ast.ImportFrom) and n.module and not n.level}; assert m<=set(sys.stdlib_module_names), m-set(sys.stdlib_module_names)"`

## TC-008 — The runner executes the seeded mechanical case and records its results
- **Story**: US2 · **Traces to**: FR-004, FR-006, AC4
- **Given** the cheapest in-scope mechanical case — spec-code-review E2, the seeded-fixture case — whose case file carries its Run: procedure
- **When** the runner executes that named case
- **Then** it follows the case's Run: procedure, writes the case's results file, and exits zero because all pass criteria hold
- **Pass condition**: `python3 tools/tests/test_evals.py FixtureTests`

## TC-009 — A failed pass criterion exits nonzero
- **Story**: US2 · **Traces to**: FR-004, AC4
- **Given** a mechanical case whose execution ends with at least one failed pass criterion
- **When** the runner executes it
- **Then** the console names the failed criterion, the process exits with a nonzero status, and the failure is recorded in the case's results file
- **Pass condition**: Manual observation — run the runner on a mechanical case whose execution fails a criterion; the failed criterion is named in the console output, the exit status is nonzero, and the case's results file records the failure.

## TC-010 — A conversational case states it cannot auto-execute and prints the session procedure
- **Story**: US2 · **Traces to**: FR-005, AC5
- **Given** a conversational in-scope case (spec-brainstorming B1) with no transcript handed in
- **When** the runner is pointed at that case
- **Then** it states the case cannot be auto-executed and prints the session procedure a human follows
- **Pass condition**: `python3 -c "import subprocess; o=subprocess.run(['python3','tools/evals.py','run','spec-brainstorming/b1'],capture_output=True,text=True).stdout.lower(); assert 'conversational' in o and 'procedure' in o, o"`

## TC-011 — The runner validates an existing transcript and records the verdict
- **Story**: US2 · **Traces to**: FR-005, AC5
- **Given** the baseline transcript filed for that conversational case
- **When** the runner is handed that transcript to validate
- **Then** it checks the transcript against the case's pass criteria, records the verdict file, and names the results path it wrote
- **Pass condition**: `o=$(python3 tools/evals.py validate spec-brainstorming/b1 "$(ls skills/spec-brainstorming/evals/results/*-b1.md | head -1)" 2>&1); echo "$o" | grep -q 'refusing to overwrite'`

## TC-012 — Every in-scope case carries a Run: line (standing guard)
- **Story**: US2 · **Traces to**: FR-006
- **Given** the three eval case files holding 4, 5, and 6 in-scope cases respectively
- **When** the files are scanned
- **Then** each case carries a Run: line naming its execution procedure — the single source of truth both the runner and a human follow; the guard fails if any case loses its line
- **Pass condition**: `test "$(grep -c '\*\*Run\*\*:' skills/spec-code-review/evals/cases.md)" -eq 4 && test "$(grep -c '\*\*Run\*\*:' skills/spec-brainstorming/evals/cases.md)" -eq 5 && test "$(grep -c '\*\*Run\*\*:' skills/spec-to-prod/evals/cases.md)" -eq 6`

## TC-013 — The constitution gains article C-10 and the agents guide points to it
- **Story**: US3 · **Traces to**: FR-007, AC6
- **Given** the engineering constitution, whose articles end at C-09 today
- **When** the scoping article is appended
- **Then** the constitution contains C-10 stating that every kit increment names the eval case(s) it serves and that two consecutive increments without one stop the program, and the root agents guide carries a pointer line to it
- **Pass condition**: `grep -q 'C-10' specs/CONSTITUTION.md && grep -qiE 'eval case' specs/CONSTITUTION.md && grep -qiE 'two consecutive' specs/CONSTITUTION.md && grep -q 'C-10' AGENTS.md`

## TC-014 — Future increments name their served eval case at approval time (standing process guard)
- **Story**: US3 · **Traces to**: FR-007, AC6
- **Given** the constitution amended with the scoping article
- **When** any future kit increment is approved
- **Then** its spec names the eval case(s) it serves; two consecutive approved increments without a served case stop the program per the article's kill criterion
- **Pass condition**: Manual observation — at each increment approval after this spec, the increment's spec names at least one eval case; two consecutive approvals without one trigger the article's stop rule.

## TC-015 — The delivery summary records the per-skill baseline roll-up
- **Story**: US1 · **Traces to**: FR-008
- **Given** the completed phase-0 baseline pass
- **When** this spec's delivery summary is written
- **Then** it records, per skill, the cases run, passed, failed, and contract-bent — the number future changes diff against
- **Pass condition**: `test "$(grep -ci 'contract-bent' specs/kit-level-up/task.md)" -ge 3 && grep -qi 'passed' specs/kit-level-up/task.md && grep -qi 'failed' specs/kit-level-up/task.md`

## TC-016 — The runner adds no network surface (standing guard)
- **Story**: US2 · **Traces to**: NFR-001
- **Given** the spec scopes security out because the runner introduces no network surface and transcripts record the user's own repos only
- **When** the runner's source is scanned for network-capable imports
- **Then** none are found; the guard fails if one ever creeps in
- **Pass condition**: `test "$(grep -cE '^[[:space:]]*(import|from)[[:space:]]+(socket|ssl|requests|ftplib|smtplib|telnetlib|xmlrpc|websocket|http\.client|urllib\.request)' tools/evals.py)" -eq 0`

## TC-017 — The runner adds no telemetry or upload path (standing guard)
- **Story**: US2 · **Traces to**: NFR-002
- **Given** the spec scopes privacy out because transcripts stay in the local repo with no external upload
- **When** the runner's source is scanned for telemetry, beacon, or analytics hooks
- **Then** none are found; evidence remains local markdown files
- **Pass condition**: `test "$(grep -ciE 'telemetry|analytics|beacon|track_event' tools/evals.py)" -eq 0`

## TC-018 — Listing all cases is instant and spawns nothing
- **Story**: US2 · **Traces to**: NFR-003
- **Given** the runner installed
- **When** it lists all cases
- **Then** the listing completes in under a second, reading case files only — no agent session is started
- **Pass condition**: `python3 -c "import subprocess,time; t=time.monotonic(); r=subprocess.run(['python3','tools/evals.py','list'],capture_output=True); d=time.monotonic()-t; assert r.returncode==0 and d<1.0, (r.returncode,d)"`

## TC-019 — A failed execution never touches prior recorded evidence
- **Story**: US2 · **Traces to**: NFR-004
- **Given** at least one recorded results file for the seeded mechanical case, and a handed-in transcript that is empty — it can satisfy no pass criterion
- **When** the runner validates that broken transcript
- **Then** the runner exits nonzero and the previously recorded results file is byte-for-byte unchanged — a crashed or failing run never overwrites recorded evidence with partial state
- **Pass condition**: `python3 -c "import subprocess,glob,hashlib,os,tempfile; f=sorted(glob.glob('skills/spec-code-review/evals/results/*-e2.md'))[0]; h=hashlib.md5(open(f,'rb').read()).hexdigest(); fd,t=tempfile.mkstemp(); os.close(fd); r=subprocess.run(['python3','tools/evals.py','validate','spec-code-review/e2',t],capture_output=True,text=True); os.remove(t); assert r.returncode!=0, r.stdout+r.stderr; assert hashlib.md5(open(f,'rb').read()).hexdigest()==h, 'results file mutated'"`

## TC-020 — Every runner execution prints the receipt: case, verdicts, results path
- **Story**: US2 · **Traces to**: NFR-005
- **Given** the seeded mechanical case
- **When** the runner executes it
- **Then** the console names the case, prints its criteria verdicts, and names the results path it wrote — the console line is the receipt, the results file is the record
- **Pass condition**: `python3 -c "import importlib.util,contextlib,io,tempfile,pathlib; d=pathlib.Path(tempfile.mkdtemp()); c=d/'skills'/'fx'/'evals'; c.mkdir(parents=True); (c/'cases.md').write_text(chr(10).join(['# Eval cases','','## C1 — conv case','- **Pass criteria**: it holds','- **Run**: session: do it in a session',''])); spec=importlib.util.spec_from_file_location('ev','tools/evals.py'); ev=importlib.util.module_from_spec(spec); spec.loader.exec_module(ev); ev.ROOT=d; tr=d/'t.md'; tr.write_text(chr(10).join(['## Verdicts','','- C1: pass — observed in the transcript'])); buf=io.StringIO(); _r=contextlib.redirect_stdout(buf); _r.__enter__(); rc=ev.main(['validate','fx/c1',str(tr)]); _r.__exit__(None,None,None); out=buf.getvalue(); assert rc==0 and 'fx/c1' in out and 'C1: pass' in out and 'results' in out, out"`

## TC-021 — No UI toolkit enters the runner (standing guard)
- **Story**: US2 · **Traces to**: NFR-006
- **Given** the spec scopes accessibility out because the surfaces are CLI output and markdown files only
- **When** the runner's source is scanned for UI toolkit imports
- **Then** none are found
- **Pass condition**: `test "$(grep -ciE 'tkinter|pyqt|pyside|electron|urwid|textual' tools/evals.py)" -eq 0`

## Coverage matrix
<!-- Every FR and applicable NFR appears; `check.py` fails a requirement with no TC. -->
| Requirement | Test cases | Type (auto/manual) |
|-------------|------------|--------------------|
| FR-001      | TC-001, TC-002 | auto |
| FR-002      | TC-003, TC-004 | auto / manual |
| FR-003      | TC-005     | manual |
| FR-004      | TC-006, TC-007, TC-008, TC-009 | auto / manual |
| FR-005      | TC-010, TC-011 | auto |
| FR-006      | TC-012     | auto |
| FR-007      | TC-013, TC-014 | auto / manual |
| FR-008      | TC-015     | auto |
| NFR-001     | TC-016     | auto |
| NFR-002     | TC-017     | auto |
| NFR-003     | TC-018     | auto |
| NFR-004     | TC-019     | auto |
| NFR-005     | TC-020     | auto |
| NFR-006     | TC-021     | auto |

Notes for the orchestrator:
- Manual cases (TC-004, TC-005, TC-009, TC-014) are conditional behaviors — a failing
  criterion, a contract bent, a future approval — that only show in a real run or at
  approval time; each states its observation precisely and has no fake command.
- The runner invocation forms used in pass conditions (`list`, `run <skill>-<case>`,
  `validate <skill>-<case> <transcript>`) are the business contract the implementer
  satisfies, derived from the spec's own verbs; case ids are skill-prefixed because
  case numbers (E1–E4) collide across skills.
- The three N/A NFRs (NFR-001, NFR-002, NFR-006) are covered by standing guards
  pinning the spec's own scoping rationale, not marked MISSING — each rationale is
  an observable claim about the delivered runner.
