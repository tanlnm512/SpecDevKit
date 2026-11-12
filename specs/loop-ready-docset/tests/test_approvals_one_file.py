"""TC-013/TC-014 — the approve gate records ONE approvals/approval.md
holding `## Contract review` + `## Freeze`, and a tampered half of
either section is refused (FR-009, NFR-004).

Run: python3 specs/loop-ready-docset/tests/test_approvals_one_file.py
ApprovalsOneFileTests.<method>
"""

import contextlib
import hashlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
_SCRIPTS = str(REPO / "skills" / "spec-design" / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import check  # noqa: E402 - repo-relative scripts dir prepended above
import freeze  # noqa: E402

FIXTURE = REPO / "skills" / "spec-design" / "examples" / "mini-spec"


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def scratch_docset(tmp: Path, name: str = "demo") -> Path:
    """The mini-spec docset plus the repo it cites, copied so the survey's
    evidence stays real under the tmp root."""
    (tmp / "specs").mkdir(parents=True, exist_ok=True)
    dst = tmp / "specs" / name
    shutil.copytree(FIXTURE / "specs" / "mini-spec", dst)
    shutil.copytree(FIXTURE / "repo", tmp / "repo")
    return dst


def review_payload(spec_dir: Path, blocks: int = 0) -> str:
    """The saved review payload: fingerprint line, auditor digest, one
    ruling line per BLOCK."""
    text = (f"Docset fingerprint: {freeze.docset_fingerprint(spec_dir)}\n\n"
            f"digest: BLOCK {blocks} · WARN 0 · NIT 0 · worst none\n")
    return text + "".join(
        f"ruling: {n} — repaired\n" for n in range(1, blocks + 1))


def record_approval(spec_dir: Path, payload: Path) -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        rc = freeze.record(spec_dir, spec_dir.parent.parent,
                           review=str(payload))
    assert rc == 0, "freeze.py --record refused the fixture"


def approve(spec_dir: Path, payload: Path) -> None:
    """The approve gate's record, then the Status word it unblocks."""
    record_approval(spec_dir, payload)
    write(spec_dir / "spec.md", (spec_dir / "spec.md").read_text(
        encoding="utf-8").replace("**Status**: draft", "**Status**: approved"))


def run_check(spec_dir: Path) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = check.main([str(spec_dir)])
    return code, buf.getvalue()


class ApprovalsOneFileTests(unittest.TestCase):
    def test_one_file_holds_both_sections_and_validates(self):
        # TC-013
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            spec = scratch_docset(tmp)
            approve(spec, write(tmp / "review-payload.md",
                                review_payload(spec)))

            approvals = spec / "approvals"
            self.assertEqual([p.name for p in approvals.iterdir()],
                             ["approval.md"],
                             "the approve gate writes exactly one file")
            record = (approvals / "approval.md").read_text(encoding="utf-8")

            review = record.split("## Contract review\n", 1)[1].split(
                "\n## Freeze\n", 1)[0]
            fingerprint = freeze.docset_fingerprint(spec)
            self.assertIn(f"Docset fingerprint: {fingerprint}", review)
            self.assertIn("digest: BLOCK 0 · WARN 0 · NIT 0 · worst none",
                          review)

            self.assertIn("## Freeze", record)
            for name in ("plan.md", "survey.md", "test.md"):
                raw = (spec / name).read_bytes()
                self.assertIn(f"- `{name}`: exact "
                              f"sha256:{hashlib.sha256(raw).hexdigest()} "
                              f"length:{len(raw)}", record)
            entries = {name: (kind, digest, length)
                       for name, kind, digest, length in freeze.ENTRY.findall(record)}
            self.assertIn("tech-spec.md", entries)
            self.assertEqual(entries["tech-spec.md"][0], "prefix")
            self.assertIsNotNone(freeze.APPROVED_AT.search(record),
                                 "the frozen anchor survives the fold")

            code, out = run_check(spec)
            self.assertEqual(code, 0, out)

    def test_tampered_section_refused(self):
        # TC-014
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            spec = scratch_docset(tmp, "frozen-half")
            approve(spec, write(tmp / "payload-a.md",
                                review_payload(spec, blocks=1)))
            record = spec / "approvals" / "approval.md"
            text = record.read_text(encoding="utf-8")
            record.write_text(text.replace(
                "sha256:" + freeze.ENTRY.search(text).group(3),
                "sha256:" + "0" * 64), encoding="utf-8")
            code, out = run_check(spec)
            self.assertEqual(code, 1, out)
            self.assertIn("changed after approval", out)

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            spec = scratch_docset(tmp, "review-half")
            approve(spec, write(tmp / "payload-b.md",
                                review_payload(spec, blocks=1)))
            record = spec / "approvals" / "approval.md"
            record.write_text(
                record.read_text(encoding="utf-8")
                .replace("ruling: 1 — repaired\n", ""), encoding="utf-8")
            code, out = run_check(spec)
            self.assertEqual(code, 1, out)
            self.assertIn("0 ruling line(s)", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
