#!/usr/bin/env python3
"""Generate the approval guard — spec-kit-guard.py and REGISTER.md — for
one harness with a Claude-shaped PreToolUse hook contract.

The kit ships no hook: no harness hook contract is verified by this
repository (HARNESS-FACTS.md), so the kit never edits a harness
settings file. This generator renders the guard script and the exact
registration text; tools/sync.sh installs both under a kit-owned
directory (~/.claude/spec-dev-kit/, ~/.zcode/spec-dev-kit/) through
the same ownership ledger every kit deploy uses and prints what to
paste. Whether a harness honors the registration is the owner's live
check (REGISTER.md names it).

Targets:

- claude  REGISTER.md carries the `hooks.PreToolUse` entry for
          ~/.claude/settings.json — a command hook.
- zcode   REGISTER.md carries the `hooks` member for
          ~/.zcode/cli/config.json or <repo>/.zcode/config.json — a
          process hook.

    tools/hooks.py --target claude|zcode
                   --freeze <installed freeze.py> --out <dir>
    tools/hooks.py --check --target ... --freeze ... --out <dir>
    tools/hooks.py --stage <dir> --target ... --freeze ... --out <dir>

--freeze is the absolute path of the freeze.py this harness's sessions
run: the guard calls it by path (rule P2), so that one baked line is
the whole difference between targets. --out names the root even when
nothing is written to it: REGISTER.md carries the installed script's
absolute path, so a --check or --stage render must be made for the
destination it describes.

Output discipline: the complete set is rendered into a staging dir and
planned against the destination before the first write, and each file
lands via a destination-local temp replaced atomically — a refused
destination aborts with --out untouched. A destination is this
generator's to replace only when its current hash sits in the
destination's .spec-dev-kit-deployed ledger (a prior deploy); a
foreign file at a generated name — even a byte-identical one — exits
nonzero and is never clobbered or adopted. The generator deletes
nothing in the destination: a file a later kit no longer generates is
sync's stale sweep.

--check renders to scratch and byte-compares an installed root —
MISSING, DRIFT or OK per file, destination untouched. --stage renders
to a directory of the caller's choice and writes nothing else: an
installer's plan step, which must see the exact bytes an apply would
land. The guard is machine-installed, never committed, so
tools/drift-check.py has no `guards` set to compare: --check here is
where an installed root is verified, and tools/sync.sh --check runs it.

Exit: 0 written or current · 1 a foreign file at a generated name ·
2 usage or validation error.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ownership

GUARD_NAME = "spec-kit-guard.py"
REGISTER_NAME = "REGISTER.md"
NAMES = (GUARD_NAME, REGISTER_NAME)

MATCHERS = {
    "claude": "Write|Edit|MultiEdit|NotebookEdit|Bash|Read",
    "zcode": "Write|Edit|ApplyPatch|Bash|Read",
}

# The generated script's own docstring, verbatim.
GUARD_DOC = r"""SpecDevKit approval guard — a PreToolUse hook for
any harness whose hook contract is Claude-shaped.

Reads ONE JSON object on stdin and answers with exit codes alone: 0
allow, 2 deny with one reason line on stderr. Unreadable input or any
internal error ALLOWS, with the error on stderr — a broken guard must
never brick a session. It writes no file and runs nothing but the
installed freeze.py <spec-dir> --verify.

Fields read (all optional; a missing one means "cannot tell" — the
call is allowed): tool_name; tool_input.file_path, .content,
.old_string, .new_string, .command; and a caller identity where the
harness provides one (agent_type, subagent_type, agent_id, agent_name).
Rules, the first to fire denying:

P1  Approval records and the approver list are written only by
    freeze.py --approve: a file-writing call (Write, Edit, MultiEdit,
    NotebookEdit, ApplyPatch, or any call carrying content or
    new_string) whose target lies under specs/<name>/approvals/ or is
    specs/.approvers.
P2  `Status: approved` follows a verifying approval: a file-writing
    call on specs/<name>/spec.md whose new text sets **Status:** to
    approved, active or done is denied unless the installed
    `freeze.py <spec-dir> --verify` exits 0. Any other Status edit
    runs nothing.
P3  The same two rules for the shell: a command naming one of those
    paths is allowed only as a read-only use — every simple command one
    of the read-only list or an invocation of the installed freeze.py,
    no redirect that writes, no command substitution. This rule is a
    tripwire, not a boundary: the signature on the approval record is
    the boundary (spec-design D-071).
P4  The tester is implementation-blind, best effort: a Read,
    NotebookRead or view of specs/<name>/{tech-spec.md,plan.md,task.md}
    is denied when the caller identity names the tester. With no
    identity in the payload P4 allows and says nothing (spec-design
    D-073).

A call that carries none of the typed fields — ApplyPatch, or any tool
whose input is raw text — is read by P1 and P2 as text alone: denied
by P1 when its text mentions an approval path, by P2 when it names a
specs/<name>/spec.md and holds a **Status:** line reading approved,
active or done. That branch is a text tripwire, not a parse: every
string value of the call is scanned and nothing is understood.

Paths are matched on their components, case-insensitively, at any
depth. A path this script cannot recognize is not seen.
"""

# The one line a render rewrites: the generated script binds the
# installed freeze.py; None here, where nothing is installed.
FREEZE_PY = None

# --- guard source: spec-kit-guard.py ---
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit", "ApplyPatch")
READ_TOOLS = ("Read", "NotebookRead", "view")
APPROVING_STATUS = ("approved", "active", "done")
BLIND_FILES = ("tech-spec.md", "plan.md", "task.md")
IDENTITY_FIELDS = ("agent_type", "subagent_type", "agent_id", "agent_name")
# A call carrying `command` is the shell rule's, never the text tripwire's.
TYPED_FIELDS = ("file_path", "content", "old_string", "new_string", "command")

STATUS_LINE = re.compile(r"^\*\*Status\*\*:\s*`?([A-Za-z]+)", re.M)
TEXT_STATUS_LINE = re.compile(r"^\+?\*\*Status\*\*:\s*`?([A-Za-z]+)", re.M)
ONE_WORD = re.compile(r"[A-Za-z]+")
IDENTITY_WORD = re.compile(r"[^a-z0-9]+")

READ_ONLY = (("cat",), ("head",), ("tail",), ("less",), ("grep",), ("rg",),
             ("ls",), ("wc",), ("git", "log"), ("git", "show"),
             ("git", "diff"), ("sha256sum",), ("shasum",),
             ("ssh-keygen", "-Y", "verify"))
SED_READ_ONLY = re.compile(r"-n[^i]*")
SED_WRITES = re.compile(r"(?:^|[,;{}])\s*(?:[$0-9,/!%~]*\s*)?[we]\s")
WRITE_OPTIONS = {
    "rg": re.compile(r"--pre(?:=.*)?"),
    "less": re.compile(r"-[oO]|--log-file|--LOG-FILE"),
}
PYTHON = re.compile(r"(?:.*/)?python(?:\d+(?:\.\d+)*)?")
OPERATOR_CHARS = "|&;<>(){}"
NULL_TARGET = "/dev/null"
PATH_IN_TEXT = re.compile(
    r"(?<![\w.-])(?:(?:\.|~)?/)?(?:[\w.~+@-]+/)*"
    r"specs/[^\s'\"`|;&<>(){}]*", re.I)

REASONS = {
    "P1": "spec-kit guard: P1 — approval records are written only by "
          "freeze.py <spec-dir> --approve (spec-design D-072)",
    "P2": "spec-kit guard: P2 — Status: approved follows a verifying "
          "approval: freeze.py <spec-dir> --verify must pass first "
          "(spec-design D-072)",
    "P4": "spec-kit guard: P4 — the tester is implementation-blind: read "
          "spec.md only, never tech-spec.md, plan.md or task.md "
          "(spec-design D-073)",
}


def _lower_parts(path):
    return [part.lower()
            for part in os.path.normpath(os.path.expanduser(path)).split("/")]


def _is_approval_path(path):
    """Under specs/<name>/approvals/, or specs/.approvers itself."""
    low = _lower_parts(path)
    return any(
        low[i + 2:i + 3] == ["approvals"]
        or low[i + 1:i + 2] == [".approvers"] and len(low) == i + 2
        for i, part in enumerate(low) if part == "specs")


def _spec_dir_of(path, leafs):
    """The spec dir when path is specs/<name>/<leaf> for one of leafs and
    nothing follows the leaf; None for any other path."""
    parts = os.path.normpath(os.path.expanduser(path)).split("/")
    low = [part.lower() for part in parts]
    for i, part in enumerate(low[:-2]):
        if part == "specs" and low[i + 2] in leafs and len(parts) == i + 3:
            return "/".join(parts[:i + 2])
    return None


def _new_texts(tool_input):
    """(new text, old text) of every text the call writes in place of
    old: content, new_string, and each edit of a MultiEdit."""
    texts = [(tool_input[key], tool_input.get("old_string"))
             for key in ("content", "new_string")
             if isinstance(tool_input.get(key), str)]
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        texts += [(edit["new_string"], edit.get("old_string"))
                  for edit in edits
                  if isinstance(edit, dict)
                  and isinstance(edit.get("new_string"), str)]
    return texts


def _sets_approving_status(new, old):
    """A `**Status**:` line in the new text reading approved, active or
    done — or one bare approving word replacing one bare word, the
    shape of a word-level edit of that line."""
    statuses = [status.lower() for status in STATUS_LINE.findall(new)]
    if statuses:
        return any(status in APPROVING_STATUS for status in statuses)
    old = old.strip() if isinstance(old, str) else ""
    return (new.strip().lower() in APPROVING_STATUS
            and ONE_WORD.fullmatch(old) is not None)


def _verifies(spec_dir):
    """The installed freeze.py --verify's verdict on one spec dir. A
    freeze.py that cannot run raises, and the caller fails open."""
    if not FREEZE_PY or not os.path.isfile(FREEZE_PY):
        raise RuntimeError(f"freeze.py is not installed at {FREEZE_PY}")
    try:
        return subprocess.run(
            [sys.executable, FREEZE_PY, spec_dir, "--verify"],
            capture_output=True, text=True, timeout=60).returncode == 0
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"freeze.py --verify did not run: {e}") from e


def _names_tester(payload):
    """A caller identity naming the tester — spec-tester, tester — as a
    whole word."""
    return any(
        isinstance(payload.get(field), str) and "tester" in
        IDENTITY_WORD.split(payload[field].lower())
        for field in IDENTITY_FIELDS)


def _lex(command):
    """A shell command line as (kind, text) tokens, quote-aware: "word"
    for a shell word, "op" for one run of operator characters or a
    newline, "sub" for a backtick or $( — quoted or not. An operator
    inside quotes stays in its word; a backslash escapes the next
    character."""
    tokens, buf, quote = [], [], None
    i = 0
    while i < len(command):
        c = command[i]
        if quote == "'":
            if c == "'":
                quote = None
            else:
                buf.append(c)
        elif c == "\\" and quote != "'" and i + 1 < len(command):
            i += 1
            buf.append(command[i])
        elif quote == '"':
            if c == '"':
                quote = None
            elif c == "`" or command[i:i + 2] == "$(":
                tokens.append(("sub", ""))
            else:
                buf.append(c)
        elif c in "'\"":
            quote = c
        elif c == "`" or command[i:i + 2] == "$(":
            tokens.append(("sub", ""))
            i += 1
        elif c in " \t":
            if buf:
                tokens.append(("word", "".join(buf)))
                buf = []
        elif c == "\n" or c in OPERATOR_CHARS:
            if buf:
                tokens.append(("word", "".join(buf)))
                buf = []
            run = c
            while c != "\n" and i + 1 < len(command) \
                    and command[i + 1] in OPERATOR_CHARS:
                i += 1
                run += command[i]
            tokens.append(("op", run))
        else:
            buf.append(c)
        i += 1
    if buf:
        tokens.append(("word", "".join(buf)))
    return tokens


def _is_redirect(op):
    return op[0] in "<>" or op[0] == "&" and ">" in op


def _parse(command):
    """A shell command line as (argv lists, writes, substitutes): one
    argv per simple command with redirect operators and their targets
    removed; writes is true when a redirect writes somewhere other
    than /dev/null or duplicates a descriptor."""
    tokens = _lex(command)
    argvs, argv = [], []
    writes = False

    def end_command():
        if argv:
            argvs.append(list(argv))
            argv.clear()

    i = 0
    while i < len(tokens):
        kind, text = tokens[i]
        i += 1
        if kind == "word":
            argv.append(text)
        elif kind != "sub" and _is_redirect(text):
            fd = argv.pop() if argv and argv[-1].isdigit() else ""
            has_target = i < len(tokens) and tokens[i][0] == "word"
            target = tokens[i][1] if has_target else ""
            if has_target:
                i += 1
            if not (fd and text == ">&" and target.isdigit()
                    or target == NULL_TARGET):
                writes = True
        elif kind == "op":
            end_command()
    end_command()
    return argvs, writes, any(kind == "sub" for kind, _ in tokens)


def _reads_only(argv):
    """A simple command that can only read: one of READ_ONLY, or sed
    with -n and no in-place flag."""
    if argv[0] == "sed":
        return len(argv) > 1 and SED_READ_ONLY.fullmatch(argv[1]) is not None
    return any(argv[:len(prefix)] == list(prefix) for prefix in READ_ONLY)


def _writes_by_option(argv):
    """A read-only command's own way to write or run something: git's
    --output, rg's --pre, less's log file, sed's w and e commands."""
    if any(word.startswith("--output") for word in argv):
        return True
    if argv[0] == "sed":
        return any(SED_WRITES.search(word) for word in argv[2:])
    option = WRITE_OPTIONS.get(argv[0])
    return (option is not None
            and any(option.fullmatch(word) for word in argv[1:]))


def _is_freeze_call(argv):
    """The installed freeze.py, run directly or under a Python
    interpreter: the one program besides the read-only list a guarded
    path may be handed to."""
    if not FREEZE_PY:
        return False
    if argv[0] == FREEZE_PY:
        return True
    return (len(argv) > 1 and PYTHON.fullmatch(argv[0]) is not None
            and argv[1] == FREEZE_PY)


def _named_paths(text):
    """Every specs/ path a text names — inside quotes, a --name=value
    option, a patch header or a python literal alike."""
    return [m.group().rstrip(".,") for m in PATH_IN_TEXT.finditer(text)]


def _text_denial(tool_input):
    """P1 or P2 from the text alone of a call that carries none of the
    typed fields — an ApplyPatch, or any tool whose input is raw text.
    A text tripwire, not a parse: every string value of the call is
    scanned, nothing is understood."""
    texts = [value for value in tool_input.values() if isinstance(value, str)]
    named = [path for text in texts for path in _named_paths(text)]
    if any(_is_approval_path(path) for path in named):
        return "P1"
    statuses = [status.lower()
                for text in texts for status in TEXT_STATUS_LINE.findall(text)]
    spec_dirs = sorted({spec_dir for spec_dir in
                        (_spec_dir_of(path, ("spec.md",)) for path in named)
                        if spec_dir})
    if (spec_dirs and any(status in APPROVING_STATUS for status in statuses)
            and not all(_verifies(spec_dir) for spec_dir in spec_dirs)):
        return "P2"
    return None


def _shell_denial(command):
    """P1 or P2 when a shell command names an approval path or a
    spec.md in anything but a read-only use; None when it names neither
    or reads only."""
    named = _named_paths(command)
    approvals = [path for path in named if _is_approval_path(path)]
    if not approvals and not any(
            _spec_dir_of(path, ("spec.md",)) for path in named):
        return None
    argvs, writes, substitutes = _parse(command)
    reads_only = not writes and not substitutes and all(
        (_reads_only(argv) and not _writes_by_option(argv))
        or _is_freeze_call(argv) for argv in argvs if argv)
    return None if reads_only else "P1" if approvals else "P2"


def decide(payload):
    """The rule that denies the call — "P1", "P2" or "P4" — or None when
    the call is allowed; the first rule in order to fire wins. Raises
    TypeError on a payload that is not a JSON object."""
    if not isinstance(payload, dict):
        raise TypeError("hook payload is not a JSON object")
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    path = tool_input.get("file_path")
    if not isinstance(path, str):
        path = tool_input.get("notebook_path")
    command = tool_input.get("command")
    texts = _new_texts(tool_input)
    writing = (tool in WRITE_TOOLS or bool(texts)
               or isinstance(tool_input.get("edits"), list))
    if writing and isinstance(path, str):
        if _is_approval_path(path):
            return "P1"
        spec_dir = _spec_dir_of(path, ("spec.md",))
        if (spec_dir
                and any(_sets_approving_status(new, old) for new, old in texts)
                and not _verifies(spec_dir)):
            return "P2"
    if not any(isinstance(tool_input.get(key), str) for key in TYPED_FIELDS):
        return _text_denial(tool_input)
    if isinstance(command, str):
        rule = _shell_denial(command)
        if rule:
            return rule
    if (tool in READ_TOOLS and isinstance(path, str)
            and _spec_dir_of(path, BLIND_FILES) and _names_tester(payload)):
        return "P4"
    return None


def run_hook():
    """The hook's exit status: 0 allow, 2 deny with one reason line on
    stderr. Unreadable input or an internal error allows and says so."""
    try:
        rule = decide(json.loads(sys.stdin.read()))
    except Exception as e:
        print(f"spec-kit guard: cannot decide ({type(e).__name__}: "
              f"{' '.join(str(e).split())}) — allowing", file=sys.stderr)
        return 0
    if rule is None:
        return 0
    print(REASONS[rule], file=sys.stderr)
    return 2


# --- end guard source ---

_BEGIN = "# --- guard source: spec-kit-guard.py ---\n"
_END = "# --- end guard source ---\n"


def guard_source() -> str:
    """This file's own guard block, verbatim: the code the generated
    script runs, kept executable here so it is imported, compiled and
    tested where it is written."""
    own = Path(__file__).read_text(encoding="utf-8")
    return own.split(_BEGIN, 1)[1].split(_END, 1)[0]


def registration(target: str, guard: str) -> str:
    """The text to paste, exactly as the target's settings file takes
    it; guard is the installed script's absolute path."""
    quoted = json.dumps(str(guard))
    if target == "claude":
        command = json.dumps(f'python3 "{guard}"')
        return (f'{{"matcher": "{MATCHERS[target]}", '
                f'"hooks": [{{"type": "command", "command": {command}}}]}}')
    return (f'"hooks": {{"enabled": true, "events": {{"PreToolUse": '
            f'[{{"matcher": "{MATCHERS[target]}", '
            f'"hooks": [{{"type": "process", "command": "python3", '
            f'"args": [{quoted}]}}]}}]}}}}')


LEADS = {
    "claude": "The kit never edits a harness settings file. Paste the entry\n"
              "below into `~/.claude/settings.json` — the `PreToolUse` list\n"
              "of its `hooks` object — then start a new session:",
    "zcode": "The kit never edits a harness config file. Paste the member\n"
             "below into `~/.zcode/cli/config.json`, or into\n"
             "`<repo>/.zcode/config.json` for this repository alone —\n"
             "at the file's top level, then start a new session:",
}

REGISTER = """\
# Register the approval guard — {harness}

{lead}

    {registration}

What it does, and what it does not prove:

- It denies every session and spawned agent the writes that forge an
  approval: anything under `specs/<name>/approvals/`, the approver
  list `specs/.approvers`, and a `spec.md` edit that sets
  `**Status**:` to `approved`, `active` or `done` while
  `freeze.py <spec-dir> --verify` fails.
- The shell is held to a read-only allowlist on those paths. That rule
  is a tripwire, not a boundary: the SSH signature on the approval
  record is the boundary (spec-design D-071).
- The tester is denied `tech-spec.md`, `plan.md` and `task.md` only
  where the harness names the caller in the hook payload; with no
  caller identity that rule allows and says nothing (spec-design
  D-073).
- It fails open: unreadable input, an internal error, a field it does
  not know or a path it cannot recognize all allow. A tool whose input
  is raw text (ApplyPatch) gets a text tripwire, not a parse: what its
  text does not spell out is not seen.
- It writes nothing and runs nothing but the installed
  `freeze.py --verify`; the approval record is still written only by
  the owner's own `freeze.py <spec-dir> --approve`.

Verify it live: in the new session, have it try
`echo x >> specs/<name>/approvals/approval.md` — the call is denied and
the reason line reads `{p1}`. Until a session shows that, the
registration shape is an open assumption (HARNESS-FACTS.md): a harness
that ignores it runs unguarded, and nothing here fails.
"""


def render_guard(freeze_py: str) -> bytes:
    modules = ("json", "os", "re", "subprocess", "sys")
    imports = "".join(f"import {module}\n" for module in modules) + "\n"
    tail = '\n\nif __name__ == "__main__":\n    sys.exit(run_hook())\n'
    header = ('#!/usr/bin/env python3\n"""' + GUARD_DOC + '"""\n\n'
              + imports + f"FREEZE_PY = {json.dumps(freeze_py)}\n\n\n")
    return (header + guard_source() + tail).encode()


def render_register(target: str, outd: Path) -> bytes:
    return REGISTER.format(
        harness={"claude": "Claude Code", "zcode": "ZCode"}[target],
        lead=LEADS[target],
        registration=registration(target, os.path.abspath(outd / GUARD_NAME)),
        p1=REASONS["P1"]).encode()


def put(stage: Path, outd: Path, name: str):
    tmp = outd / f".{name}.tmp"
    tmp.write_bytes((stage / name).read_bytes())
    tmp.replace(outd / name)


def record_ledger(outd: Path, written):
    """Merge this run's deploys into the destination ledger, atomically;
    entries for names this run did not generate are kept."""
    ledger = outd / ownership.LEDGER_NAME
    entries = ownership.read_ledger(ledger)
    for d in written:
        entries[d.name] = d.src_sha
    tmp = outd / f"{ownership.LEDGER_NAME}.tmp"
    tmp.write_text("".join(f"{entries[n]} {n}\n" for n in sorted(entries)))
    tmp.replace(ledger)


def report(outd: Path, stage: Path) -> int:
    """--check: byte-compare an installed root against the staging
    render, writing nothing; 1 names what is missing or drifted."""
    rc = 0
    for name in NAMES:
        dest = outd / name
        if not dest.is_file():
            print(f"MISSING {dest} — not installed (rerun tools/sync.sh)")
            rc = 1
        elif dest.read_bytes() != (stage / name).read_bytes():
            print(f"DRIFT {dest} — rerun tools/sync.sh")
            rc = 1
        else:
            print(f"OK  {dest}")
    return rc


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = False
    target = freeze = out = stage_at = None
    it = iter(argv)
    for a in it:
        if a == "--check":
            check = True
            continue
        val = next(it, None)
        if a == "--target":
            target = val
        elif a == "--freeze":
            freeze = val
        elif a == "--out":
            out = val
        elif a == "--stage":
            stage_at = val
        else:
            sys.exit(f"unknown arg: {a}")
    if target not in MATCHERS or not freeze or not out:
        sys.exit("usage: hooks.py --target {claude|zcode} --freeze <installed "
                 "freeze.py> --out <dir> [--check | --stage <dir>]")
    if not os.path.isabs(freeze):
        sys.exit("--freeze must be the installed freeze.py's absolute path: "
                 f"{freeze}")

    outd = Path(out)
    if stage_at:
        staged = Path(stage_at)
        staged.mkdir(parents=True, exist_ok=True)
        (staged / GUARD_NAME).write_bytes(render_guard(freeze))
        (staged / REGISTER_NAME).write_bytes(render_register(target, outd))
        print(f"{target} guard  {len(NAMES)} files staged -> {staged}")
        return 0

    stage = Path(tempfile.mkdtemp(prefix="hooks-stage-"))
    try:
        (stage / GUARD_NAME).write_bytes(render_guard(freeze))
        (stage / REGISTER_NAME).write_bytes(render_register(target, outd))
        if check:
            return report(outd, stage)

        try:
            planned, refused = [], []
            for name in NAMES:
                d = ownership.plan_file(stage / name, outd / name, name=name)
                (refused if d.kind == ownership.REFUSE else planned).append(d)
        except (ValueError, OSError) as e:
            print(f"ERROR {e}", file=sys.stderr)
            return 2
        if refused:
            for d in refused:
                print(f"REFUSE {outd / d.name} — foreign file (differs from "
                      f"generated, not a prior deploy); resolve manually")
            return 1

        outd.mkdir(parents=True, exist_ok=True)
        written = []
        for d in planned:
            if d.kind == ownership.UNCHANGED:
                continue
            put(stage, outd, d.name)
            written.append(d)
        if written:
            record_ledger(outd, written)
        print(f"{target} guard  {len(NAMES)} files -> {outd}")
        return 0
    finally:
        shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
