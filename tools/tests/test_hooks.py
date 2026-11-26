"""Tests for tools/hooks.py — the approval guard and its generator.
Run via tools/tests/run.sh (needs Python >= 3.10).

The policy table runs through the generated script's own decide():
every case renders spec-kit-guard.py as sync installs it, executes that
text, and calls the function the harness reaches through stdin — one
style for every rule (spec-design D-072, D-073). A second class pins
the stdin/exit-code contract end to end. The generator cases follow
test_agent_defs.py's OwnershipLedgerTests: staging, the ledger, a
foreign file refused.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "hooks", REPO_ROOT / "tools" / "hooks.py")
hooks = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hooks)

LEDGER = ".spec-dev-kit-deployed"
APPROVAL = "specs/pay/approvals/approval.md"
SPEC = "specs/pay/spec.md"


def fake_freeze(home: Path, exit_code: int) -> Path:
    """A stand-in for the installed freeze.py: logs every --verify it is
    asked for and exits with exit_code."""
    home.mkdir(parents=True, exist_ok=True)
    script = home / "freeze.py"
    log = home / "verify.log"
    script.write_text(
        "import pathlib, sys\n"
        f"pathlib.Path({str(log)!r}).open('a').write(' '.join(sys.argv[1:]) + '\\n')\n"
        f"sys.exit({exit_code})\n")
    return script


def load_guard(freeze_py) -> dict:
    """The rendered script, executed: its namespace."""
    source = hooks.render_guard(str(freeze_py)).decode()
    namespace = {"__name__": "spec_kit_guard"}
    exec(compile(source, "spec-kit-guard.py", "exec"), namespace)
    return namespace


def write(path, text=None):
    tool_input = {"file_path": path, "content": text}
    return {"tool_name": "Write", "tool_input": tool_input}


def edit(path, old, new):
    return {"tool_name": "Edit", "tool_input": {
        "file_path": path, "old_string": old, "new_string": new}}


def shell(command):
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def read(path, **identity):
    return dict(identity, tool_name="Read", tool_input={"file_path": path})


def patch(path, old, new):
    """An ApplyPatch call: raw text, none of the typed fields."""
    return {"tool_name": "ApplyPatch", "tool_input": {
        "input": f"*** Begin Patch\n*** Update File: {path}\n"
                 f"@@\n-{old}\n+{new}\n*** End Patch\n"}}


APPROVING = ("approved", "active", "done")

SHELL_ROWS = (
    ("cat " + APPROVAL, None),
    ("cat notes.md > " + APPROVAL, "P1"),
    ("cat " + SPEC + " 2>/dev/null", None),
    ("head -n 1 " + APPROVAL, None),
    ("head -n 1 x >> specs/.approvers", "P1"),
    ("tail -n 3 " + APPROVAL, None),
    ("tail -n 3 x > " + SPEC, "P2"),
    ("less " + APPROVAL, None),
    ("less -o specs/.approvers " + SPEC, "P1"),
    ("grep -c ok " + APPROVAL, None),
    ("grep ok " + APPROVAL + " > out.txt", "P1"),
    ("rg -n ok " + SPEC, None),
    ("rg ok " + APPROVAL + " --pre=sh", "P1"),
    ("ls specs/pay/approvals", None),
    ("ls specs/pay/approvals > specs/.approvers", "P1"),
    ("wc -l " + APPROVAL, None),
    ("wc -l " + APPROVAL + " | sh", "P1"),
    ("sed -n 1,5p " + SPEC, None),
    ("sed -nE 1,5p " + SPEC, None),
    ("sed -i s/draft/approved/ " + SPEC, "P2"),
    ("sed -n '1w " + APPROVAL + "' notes.md", "P1"),
    ("git log --oneline -- " + APPROVAL, None),
    ("git log -- " + APPROVAL + " --output=specs/.approvers", "P1"),
    ("git add " + APPROVAL, "P1"),
    ("git show HEAD -- " + SPEC, None),
    ("git show HEAD -- " + SPEC + " > specs/.approvers", "P1"),
    ("git diff -- " + APPROVAL, None),
    ("git diff --output=" + APPROVAL + " " + SPEC, "P1"),
    ("sha256sum " + APPROVAL, None),
    ("sha256sum " + APPROVAL + " 2>&1", None),
    ("sha256sum " + APPROVAL + " > specs/.approvers", "P1"),
    ("shasum " + APPROVAL, None),
    ("shasum " + APPROVAL + " >> specs/.approvers", "P1"),
    ("ssh-keygen -Y verify -f specs/.approvers -s " + APPROVAL + ".sig x", None),
    ("ssh-keygen -Y sign -f key " + APPROVAL, "P1"),
)

OTHER_SHELL_ROWS = (
    ("echo x >> " + APPROVAL, "P1"),
    ("rm " + APPROVAL, "P1"),
    ("cp my-key specs/.approvers", "P1"),
    ("mv notes.md " + APPROVAL, "P1"),
    ("tee " + APPROVAL, "P1"),
    ("touch " + SPEC, "P2"),
    ('python3 -c "open(\'specs/pay/approvals/approval.md\', \'w\')"', "P1"),
    ("rm -rf specs/*/approvals", "P1"),
    ("rm -rf Specs/Pay/Approvals", "P1"),
    ("echo 'x' >> 'specs/pay/approvals/approval.md'", "P1"),
    ("python3 t.py --file=" + APPROVAL, "P1"),
    ("cat $(pwd)/" + APPROVAL, "P1"),
    ("cat `pwd`/" + APPROVAL, "P1"),
    ("cat notes.md | tee " + APPROVAL, "P1"),
    ("cat README.md", None),
    ("python3 graph.py specs/pay --run", None),
    ('cat "specs/pay/approvals/approval.md"', None),
    ("cat Specs/Pay/Approvals/approval.md", None),
    ("ls my-specs/pay/approvals specs/approvals/x.md", None),
)

# Calls carrying none of the typed fields, read as text alone.
TEXT_P1_ROWS = (
    (patch(APPROVAL, "a", "b"), "P1"),
    ({"tool_name": "ApplyPatch", "tool_input": {
        "input": "*** Begin Patch\n*** Add File: specs/.approvers\n+key\n"
                 "*** End Patch"}}, "P1"),
    (patch("/repo/specs/pay/approvals/approval.md.sig", "a", "b"), "P1"),
    ({"tool_name": "some-tool", "tool_input": {"text": "signers: Specs/.Approvers"}},
     "P1"),
    (patch("specs/pay/plan.md", "a", "b"), None),
    (patch("src/specs.md", "a", "b"), None),
    ({"tool_name": "some-tool", "tool_input": {
        "text": "specs/approvals/x.md, my-specs/pay/approvals/x.md"}}, None),
    ({"tool_name": "ApplyPatch", "tool_input": {"input": ["not", "text"]}}, None),
)


class GuardP1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="guard-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.guard = load_guard(fake_freeze(self.tmp / "verifying", 0))

    def test_writes_to_the_record_and_the_approver_list_are_denied(self):
        rows = (
            ("Write", {"file_path": APPROVAL, "content": "forged\n"}),
            ("Edit", {"file_path": APPROVAL, "old_string": "a", "new_string": "b"}),
            ("MultiEdit", {"file_path": "specs/pay/approvals", "edits": []}),
            ("NotebookEdit", {"notebook_path": "specs/pay/approvals/approval.md",
                              "new_source": "x"}),
            ("ApplyPatch", {"file_path": APPROVAL, "input": "patch"}),
            ("Write", {"file_path": "specs/.approvers", "content": "key\n"}),
            ("Edit", {"file_path": "/repo/specs/pay/approvals/approval.md.sig",
                      "old_string": "a", "new_string": "b"}),
            ("Write", {"file_path": "./Specs/Pay/Approvals/Approval.md", "content": "x"}),
            ("Write", {"file_path": "specs/pay/plan.md/../approvals/approval.md",
                       "content": "x"}),
            ("some-other-tool", {"file_path": APPROVAL, "new_string": "b"}),
        )
        for tool, tool_input in rows:
            with self.subTest(tool=tool, tool_input=tool_input):
                self.assertEqual(
                    self.guard["decide"]({"tool_name": tool, "tool_input": tool_input}),
                    "P1")

    def test_writes_outside_them_are_allowed(self):
        for path in ("specs/pay/spec.md", "specs/pay/plan.md", "specs/pay/approval.md",
                     "specs/approvals/x.md", "specs/pay/spec.md.bak",
                     "my-specs/pay/approvals/x.md", "specs/.approvers.bak", "README.md"):
            with self.subTest(path=path):
                self.assertIsNone(self.guard["decide"](write(path, "x")))

    def test_raw_text_naming_a_record_is_denied_and_other_text_is_not(self):
        for payload, expected in TEXT_P1_ROWS:
            with self.subTest(payload=payload):
                self.assertEqual(self.guard["decide"](payload), expected)


class GuardP2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="guard-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.refusing = load_guard(fake_freeze(self.tmp / "refusing", 1))
        self.verifying = load_guard(fake_freeze(self.tmp / "verifying", 0))
        # nothing is installed at this path: a verify that ran would raise
        self.unrunnable = load_guard(self.tmp / "absent" / "freeze.py")

    def approving_edits(self):
        for status in APPROVING:
            yield edit(SPEC, "**Status**: draft", f"**Status**: {status}")
            yield {"tool_name": "MultiEdit", "tool_input": {
                "file_path": SPEC, "edits": [
                    {"old_string": "x", "new_string": "y"},
                    {"old_string": "**Status**: draft",
                     "new_string": f"**Status**: `{status}`"}]}}
        yield edit(SPEC, "draft", "done")
        yield write(SPEC, "# spec\n\n**Status**: active\n")

    def test_an_approving_status_is_denied_while_the_record_does_not_verify(self):
        for payload in self.approving_edits():
            with self.subTest(payload=payload):
                self.assertEqual(self.refusing["decide"](payload), "P2")

    def test_an_approving_status_is_allowed_once_the_record_verifies(self):
        for payload in self.approving_edits():
            with self.subTest(payload=payload):
                self.assertIsNone(self.verifying["decide"](payload))

    def test_verify_runs_the_installed_freeze_on_the_edited_specs_dir(self):
        self.verifying["decide"](edit(SPEC, "**Status**: draft", "**Status**: approved"))
        self.verifying["decide"](edit("/repo/specs/pay/spec.md", "a", "**Status**: done"))
        self.assertEqual(
            (self.tmp / "verifying" / "verify.log").read_text().splitlines(),
            ["specs/pay --verify", "/repo/specs/pay --verify"])

    def test_any_other_status_edit_runs_nothing(self):
        for old, new in (("**Status**: draft", "**Status**: superseded"),
                         ("**Status**: draft", "**Status**: archived"),
                         ("approved", "draft"), ("some text", "some other text")):
            with self.subTest(old=old, new=new):
                self.assertIsNone(self.unrunnable["decide"](edit(SPEC, old, new)))
        self.assertIsNone(self.unrunnable["decide"](write(SPEC, "**Status**: draft\n")))
        self.assertIsNone(self.unrunnable["decide"](
            edit("specs/pay/plan.md", "**Status**: draft", "**Status**: approved")))

    def test_a_missing_freeze_fails_open_at_the_decide_level(self):
        with self.assertRaises(RuntimeError):
            self.unrunnable["decide"](edit(SPEC, "**Status**: draft", "**Status**: approved"))

    def test_raw_text_setting_an_approving_status_follows_the_record(self):
        rows = (
            patch(SPEC, "**Status**: draft", "**Status**: approved"),
            patch("/repo/specs/pay/spec.md", "x", "**Status**: active"),
            {"tool_name": "some-tool", "tool_input": {"text": SPEC + "\n**Status**: done\n"}},
            {"tool_name": "some-tool", "tool_input": {
                "path": SPEC, "text": "+**Status**: `approved`\n"}},
        )
        for payload in rows:
            with self.subTest(payload=payload):
                self.assertEqual(self.refusing["decide"](payload), "P2")
                self.assertIsNone(self.verifying["decide"](payload))
        self.assertEqual(
            (self.tmp / "verifying" / "verify.log").read_text().splitlines(),
            ["specs/pay --verify", "/repo/specs/pay --verify",
             "specs/pay --verify", "specs/pay --verify"])
        # no approving Status line added: nothing runs, so a freeze.py
        # that is not even installed cannot be missed
        for payload in (
                patch(SPEC, "**Status**: draft", "**Status**: superseded"),
                patch(SPEC, "a", "b"),
                patch(SPEC, "**Status**: approved", "**Status**: draft"),
                {"tool_name": "some-tool", "tool_input": {"text": "**Status**: approved"}}):
            with self.subTest(payload=payload):
                self.assertIsNone(self.unrunnable["decide"](payload))


class GuardP3Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="guard-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.freeze = fake_freeze(self.tmp / "freeze", 0)
        self.guard = load_guard(self.freeze)

    def test_every_read_only_family_reads_and_never_writes(self):
        for command, expected in SHELL_ROWS:
            with self.subTest(command=command):
                self.assertEqual(self.guard["decide"](shell(command)), expected)

    def test_anything_else_naming_the_paths_is_denied_with_the_owned_rule(self):
        for command, expected in OTHER_SHELL_ROWS:
            with self.subTest(command=command):
                self.assertEqual(self.guard["decide"](shell(command)), expected)

    def test_only_the_installed_freeze_is_the_freeze(self):
        installed = str(self.freeze)
        stranger = self.tmp / "elsewhere" / "freeze.py"
        stranger.parent.mkdir()
        shutil.copyfile(self.freeze, stranger)
        tail = " && cat " + APPROVAL
        for command in (f"python3 {installed} specs/pay --verify{tail}",
                        f"{installed} specs/pay --verify{tail}",
                        f"python3 {installed} specs/pay --approve{tail}"):
            with self.subTest(command=command):
                self.assertIsNone(self.guard["decide"](shell(command)))
        for command in (f"python3 {stranger} specs/pay --verify{tail}",
                        f"python3 {installed} specs/pay --verify; rm -rf specs/pay/approvals",
                        f"python3 -c 'import sys' {installed}{tail}"):
            with self.subTest(command=command):
                self.assertEqual(self.guard["decide"](shell(command)), "P1")

    def test_a_command_naming_no_guarded_path_is_not_judged(self):
        for command in ("", "echo x >> notes.md", "rm -rf specs/pay",
                        "cd specs/pay && echo x > approvals/approval.md",
                        "sed -i s/a/b/ specs/pay/plan.md"):
            with self.subTest(command=command):
                self.assertIsNone(self.guard["decide"](shell(command)))


class GuardP4Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="guard-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.guard = load_guard(fake_freeze(self.tmp / "freeze", 0))

    def test_the_tester_is_denied_the_implementation_docs(self):
        for field in ("agent_type", "subagent_type", "agent_id", "agent_name"):
            for name in ("spec-tester", "tester", "spec-tester #2", "Tester.md"):
                for leaf in ("tech-spec.md", "plan.md", "task.md"):
                    payload = read(f"specs/pay/{leaf}", **{field: name})
                    with self.subTest(payload=payload):
                        self.assertEqual(self.guard["decide"](payload), "P4")
        for tool in ("NotebookRead", "view"):
            self.assertEqual(self.guard["decide"](
                {"tool_name": tool, "agent_type": "tester",
                 "tool_input": {"file_path": "/repo/specs/pay/task.md"}}), "P4")

    def test_every_other_read_is_allowed(self):
        for payload in (read("specs/pay/tech-spec.md"),
                        read("specs/pay/spec.md", agent_type="spec-tester"),
                        read("specs/pay/tech-spec.md", agent_type="spec-developer"),
                        read("specs/pay/tech-spec.md", agent_type="contester"),
                        read("specs/pay/notes/tech-spec.md", agent_type="tester"),
                        read("specs/pay/tech-spec.md", agent_type=["tester"]),
                        {"tool_name": "Grep", "agent_type": "tester",
                         "tool_input": {"pattern": "x", "path": "specs/pay/plan.md"}}):
            with self.subTest(payload=payload):
                self.assertIsNone(self.guard["decide"](payload))


class GuardFailOpenTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="guard-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.guard = load_guard(fake_freeze(self.tmp / "freeze", 0))

    def test_a_missing_field_cannot_tell_and_allows(self):
        for payload in ({}, {"tool_name": "Write"}, {"tool_name": "Write", "tool_input": {}},
                        {"tool_name": "Write", "tool_input": {"content": "x"}},
                        {"tool_input": {"command": "cat " + APPROVAL}},
                        {"tool_name": None, "tool_input": None},
                        {"tool_name": ["Read"], "tool_input": {"file_path": SPEC}},
                        {"tool_name": "Edit", "tool_input": {"file_path": 5, "new_string": "x"}},
                        {"tool_name": "Edit", "tool_input": {
                            "file_path": SPEC, "old_string": "a", "new_string": "b"}},
                        {"tool_name": "Edit", "tool_input": {
                            "file_path": SPEC, "old_string": "a", "new_string": ["approved"]}},
                        {"tool_name": "Bash", "tool_input": {"command": ["rm", APPROVAL]}},
                        {"tool_name": "Bash", "tool_input": {"command": "not a dict"},
                         "x": 1}):
            with self.subTest(payload=payload):
                self.assertIsNone(self.guard["decide"](payload))

    def test_a_payload_that_is_not_an_object_is_refused_by_decide(self):
        for payload in (None, [], "x", 5):
            with self.subTest(payload=payload):
                with self.assertRaises(TypeError):
                    self.guard["decide"](payload)


class GuardScriptTests(unittest.TestCase):
    """The contract a harness sees: stdin in, exit codes out."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="guard-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.script = self.tmp / hooks.GUARD_NAME
        self.script.write_bytes(hooks.render_guard(
            str(fake_freeze(self.tmp / "freeze", 1))))

    def hook(self, stdin):
        return subprocess.run([sys.executable, str(self.script)], input=stdin,
                              capture_output=True, text=True, timeout=60)

    def test_unreadable_input_allows_and_says_so(self):
        for stdin in ("", "{not json", "[]", "null", '"a string"'):
            with self.subTest(stdin=stdin):
                result = self.hook(stdin)
                self.assertEqual((result.returncode, result.stdout), (0, ""))
                self.assertEqual(len(result.stderr.splitlines()), 1)
                self.assertIn("spec-kit guard: cannot decide", result.stderr)
                self.assertIn("allowing", result.stderr)

    def test_a_deny_is_exit_2_with_one_reason_line(self):
        for payload, rule in ((write(APPROVAL, "x"), "P1"),
                              (patch(APPROVAL, "a", "b"), "P1"),
                              (edit(SPEC, "**Status**: draft", "**Status**: approved"), "P2"),
                              (shell("echo x >> " + APPROVAL), "P1"),
                              (read("specs/pay/task.md", agent_type="tester"), "P4")):
            with self.subTest(rule=rule):
                result = self.hook(json.dumps(payload))
                self.assertEqual((result.returncode, result.stdout), (2, ""))
                self.assertEqual(result.stderr, hooks.REASONS[rule] + "\n")

    def test_an_allow_is_exit_0_and_silent(self):
        result = self.hook(json.dumps(read("README.md")))
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_an_internal_error_allows_and_says_so(self):
        self.script.write_bytes(hooks.render_guard(str(self.tmp / "absent" / "freeze.py")))
        result = self.hook(json.dumps(
            edit(SPEC, "**Status**: draft", "**Status**: approved")))
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(len(result.stderr.splitlines()), 1)
        self.assertIn("freeze.py is not installed", result.stderr)


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="hooks-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_gen(self, target, freeze, out, *flags):
        """(exit code, stdout) — hooks.py as sync.sh calls it."""
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = hooks.main([*flags, "--target", target, "--freeze", freeze,
                             "--out", str(out)])
        return rc, buf.getvalue()

    def ledger_entries(self, out: Path) -> dict:
        lines = (out / LEDGER).read_text().splitlines()
        return {name: sha for sha, name in (line.split(" ", 1) for line in lines)}

    def test_render_is_byte_stable_and_differs_only_in_the_baked_path(self):
        claude_freeze = "/home/me/.claude/skills/spec-design/scripts/freeze.py"
        a, c = self.tmp / "a", self.tmp / "c"
        self.run_gen("claude", claude_freeze, a)
        first = (a / hooks.GUARD_NAME).read_bytes()
        register = (a / hooks.REGISTER_NAME).read_bytes()
        self.run_gen("claude", claude_freeze, a)
        self.assertEqual(((a / hooks.GUARD_NAME).read_bytes(),
                          (a / hooks.REGISTER_NAME).read_bytes()), (first, register))
        self.run_gen("zcode", "/home/me/.agents/skills/spec-design/scripts/freeze.py", c)
        other = (c / hooks.GUARD_NAME).read_bytes()
        self.assertEqual(
            [i for i, (x, y) in enumerate(zip(first.splitlines(), other.splitlines()))
             if x != y],
            [first.splitlines().index(f'FREEZE_PY = "{claude_freeze}"'.encode())])
        self.assertEqual(len(first.splitlines()), len(other.splitlines()))
        self.assertTrue(first.startswith(b"#!/usr/bin/env python3\n"))

    def test_registration_text_is_literal_per_target(self):
        for target, settings, expected in (
                ("claude", "~/.claude/settings.json",
                 '{{"matcher": "Write|Edit|MultiEdit|NotebookEdit|Bash|Read", "hooks": '
                 '[{{"type": "command", "command": "python3 \\"{guard}\\""}}]}}'),
                ("zcode", "~/.zcode/cli/config.json",
                 '"hooks": {{"enabled": true, "events": {{"PreToolUse": [{{"matcher": '
                 '"Write|Edit|ApplyPatch|Bash|Read", "hooks": [{{"type": "process", '
                 '"command": "python3", "args": ["{guard}"]}}]}}]}}}}')):
            with self.subTest(target=target):
                out = self.tmp / target
                self.run_gen(target, "/home/me/freeze.py", out)
                guard = os.path.abspath(out / hooks.GUARD_NAME)
                text = (out / hooks.REGISTER_NAME).read_text()
                self.assertEqual(hooks.registration(target, guard), expected.format(guard=guard))
                self.assertIn("    " + expected.format(guard=guard) + "\n", text)
                self.assertIn(settings, text)
                self.assertIn(hooks.REASONS["P1"], text)
                self.assertIn("`echo x >> specs/<name>/approvals/approval.md`", text)
                # five lines on what it does and does not prove
                self.assertEqual(text.count("\n- "), 5)

    def test_ledger_records_both_files(self):
        out = self.tmp / "out"
        self.run_gen("claude", "/home/me/freeze.py", out)
        self.assertEqual(sorted(self.ledger_entries(out)), sorted(hooks.NAMES))
        for name, sha in self.ledger_entries(out).items():
            self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), sha)
        self.assertEqual(sorted(p.name for p in out.iterdir()),
                         sorted((LEDGER, hooks.GUARD_NAME, hooks.REGISTER_NAME)))

    def test_foreign_file_is_refused_and_kept(self):
        out = self.tmp / "out"
        self.run_gen("claude", "/home/me/freeze.py", out)
        rendered = (out / hooks.REGISTER_NAME).read_bytes()
        shutil.rmtree(out)
        out.mkdir()
        # byte-identical to what would be generated, and still not ours
        (out / hooks.REGISTER_NAME).write_bytes(rendered)
        (out / hooks.GUARD_NAME).write_text("# hand-made\n")
        rc, output = self.run_gen("claude", "/home/me/freeze.py", out)
        self.assertEqual(rc, 1)
        self.assertIn("REFUSE", output)
        self.assertEqual((out / hooks.GUARD_NAME).read_text(), "# hand-made\n")
        self.assertEqual((out / hooks.REGISTER_NAME).read_bytes(), rendered)
        self.assertFalse((out / LEDGER).exists())

    def test_drifted_deploy_is_refused_and_ledger_untouched(self):
        out = self.tmp / "out"
        self.run_gen("claude", "/home/me/freeze.py", out)
        ledger_before = (out / LEDGER).read_bytes()
        (out / hooks.GUARD_NAME).write_text("# hand-edited\n")
        rc, output = self.run_gen("claude", "/home/me/freeze.py", out)
        self.assertEqual(rc, 1)
        self.assertIn("REFUSE", output)
        self.assertEqual((out / hooks.GUARD_NAME).read_text(), "# hand-edited\n")
        self.assertEqual((out / LEDGER).read_bytes(), ledger_before)

    def test_owned_update_is_applied_and_reledgered(self):
        out = self.tmp / "out"
        self.run_gen("claude", "/home/me/freeze.py", out)
        self.run_gen("claude", "/home/me/other/freeze.py", out)
        self.assertIn('FREEZE_PY = "/home/me/other/freeze.py"',
                      (out / hooks.GUARD_NAME).read_text())
        self.assertEqual(
            self.ledger_entries(out)[hooks.GUARD_NAME],
            hashlib.sha256((out / hooks.GUARD_NAME).read_bytes()).hexdigest())

    def test_check_reports_missing_drift_and_ok_without_writing(self):
        out = self.tmp / "out"
        out.mkdir()
        rc, output = self.run_gen("claude", "/home/me/freeze.py", out, "--check")
        self.assertEqual((rc, output.count("MISSING"), list(out.iterdir())), (1, 2, []))
        self.run_gen("claude", "/home/me/freeze.py", out)
        rc, output = self.run_gen("claude", "/home/me/freeze.py", out, "--check")
        self.assertEqual((rc, output.count("OK  ")), (0, 2))
        (out / hooks.REGISTER_NAME).write_text("# hand-edited\n")
        before = sorted((p.name, p.read_bytes()) for p in out.iterdir())
        rc, output = self.run_gen("claude", "/home/me/freeze.py", out, "--check")
        self.assertEqual(rc, 1)
        self.assertIn("DRIFT " + str(out / hooks.REGISTER_NAME), output)
        self.assertIn("OK  " + str(out / hooks.GUARD_NAME), output)
        self.assertEqual(sorted((p.name, p.read_bytes()) for p in out.iterdir()), before)

    def test_usage_and_a_relative_freeze_path_are_refused(self):
        for argv, message in (
                (["--target", "codex", "--freeze", "/x", "--out", str(self.tmp)],
                 "usage:"),
                (["--target", "claude", "--freeze", "scripts/freeze.py",
                  "--out", str(self.tmp)], "absolute path"),
                (["--target", "claude", "--out", str(self.tmp)], "usage:"),
                (["--bogus"], "unknown arg")):
            with self.subTest(argv=argv), self.assertRaises(SystemExit) as caught:
                hooks.main(argv)
            self.assertIn(message, str(caught.exception.code))
        self.assertEqual(list(self.tmp.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
