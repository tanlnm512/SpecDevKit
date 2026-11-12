"""TC-008/TC-009 — the checker accepts the hotfix target headers on hotfix
specs only and names an unresolvable target in its failure; TC-010/TC-011 —
hotfix lineage groups under the patched release or the named spec in the
generated release notes (FR-005, FR-006, FR-007).

Run: python3 specs/loop-ready-docset/tests/test_hotfix_lineage.py
HotfixLineageTests.<method>
"""

import contextlib
import io
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
for _skill in ("spec-release", "spec-design"):
    _scripts = str(_ROOT / "skills" / _skill / "scripts")
    if _scripts not in sys.path:
        sys.path.insert(0, _scripts)

import release  # noqa: E402 - repo-relative scripts dir prepended above
import check  # noqa: E402 - repo-relative scripts dir prepended above

TODAY = "2026-01-15"


def delivered_spec(name: str, what: str, type_line: str, headers: str = "") -> str:
    return f"""# Spec: {name}

**Status**: done
**Tier**: tiny
{type_line}{headers}**Created**: {TODAY}

## What
{what}

## Tasks
- [x] T001 Ship the change (FR-001)
  done {TODAY} — the proof command exits 0

Delivered: commit @ abc1234def
"""


FEATURE = "**Type**: feature\n"
HOTFIX = "**Type**: hotfix\n"


def draft_spec(name: str, what: str, type_line: str, headers: str = "") -> str:
    return f"""# Spec: {name}

**Status**: draft
**Tier**: tiny
{type_line}{headers}**Created**: {TODAY}

## What
{what}

## Tasks
- [ ] T001 Guard the failing path (FR-001) [P]
  - Touches: `src/{name}.py`
"""


class HotfixLineageTests(unittest.TestCase):
    def collected(self, specs: dict[str, str]) -> list[dict]:
        root = Path(tempfile.mkdtemp(prefix="hotfix-lineage-"))
        self.addCleanup(shutil.rmtree, root, True)
        out = []
        for name, spec_md in specs.items():
            spec_dir = root / "specs" / name
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec.md").write_text(spec_md, encoding="utf-8")
            out.append(release.spec_facts(root, spec_dir, []))
        return out

    def notes(self, included: list[dict]) -> str:
        facts = {"included": included, "deps": [], "backlog": [], "outside": []}
        return release.generated_section(facts, "1.2.3", TODAY,
                                         release.changelog_style(""))

    def group(self, section_text: str, heading: str) -> str:
        m = re.search(rf"^### {heading}\n\n(.*?)(?=\n### |\Z)",
                      section_text, re.M | re.S)
        self.assertIsNotNone(m, f"no ### {heading} group in:\n{section_text}")
        return m.group(1)

    def spec_tree(self, specs: dict[str, str],
                  tag: str = "") -> dict[str, Path]:
        root = Path(tempfile.mkdtemp(prefix="hotfix-lineage-"))
        self.addCleanup(shutil.rmtree, root, True)
        dirs: dict[str, Path] = {}
        for name, spec_md in specs.items():
            spec_dir = root / "specs" / name
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec.md").write_text(spec_md, encoding="utf-8")
            dirs[name] = spec_dir
        if tag:
            for argv in (["git", "init", "-q", str(root)],
                         ["git", "-C", str(root), "config",
                          "user.email", "t@t"],
                         ["git", "-C", str(root), "config", "user.name", "t"],
                         ["git", "-C", str(root), "add", "."],
                         ["git", "-C", str(root), "commit", "-q",
                          "-m", "seed"],
                         ["git", "-C", str(root), "tag", "-a", tag,
                          "-m", f"release {tag}"]):
                subprocess.run(argv, check=True, capture_output=True)
        return dirs

    def checked(self, spec_dir: Path) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = check.main([str(spec_dir)])
        return code, buf.getvalue()

    def test_hotfix_grouped_under_patched_release_or_spec(self):
        tagged, named, legacy, feature = self.collected({
            "crash-fix": delivered_spec("crash-fix",
                                        "The cart stops crashing at checkout.",
                                        HOTFIX, "**Hotfix for**: v1.2.2\n"),
            "login-fix": delivered_spec("login-fix",
                                        "The login loop rejects expired tokens.",
                                        HOTFIX, "**Fixes spec**: cart-flow\n"),
            "legacy-fix": delivered_spec("legacy-fix",
                                         "The export no longer truncates rows.",
                                         HOTFIX, "**Hotfix for**: <tag>\n"),
            "cart-flow": delivered_spec("cart-flow",
                                        "The cart tracks quantities per line.",
                                        FEATURE),
        })
        self.assertEqual(tagged["hotfix_target"], {"tag": "v1.2.2", "spec": ""})
        self.assertEqual(named["hotfix_target"], {"tag": "", "spec": "cart-flow"})
        self.assertEqual(legacy["hotfix_target"], {"tag": "", "spec": ""})
        section = self.notes([tagged, named, legacy, feature])
        fixed = self.group(section, "Fixed")
        added = self.group(section, "Added")
        self.assertIn("- The cart stops crashing at checkout. (crash-fix)"
                      " — patches v1.2.2", fixed)
        self.assertIn("- The login loop rejects expired tokens. (login-fix)"
                      " — fixes cart-flow", fixed)
        self.assertIn("- The cart tracks quantities per line. (cart-flow)", added)
        self.assertNotIn("crash-fix", added)
        self.assertNotIn("login-fix", added)
        plain = "- The export no longer truncates rows. (legacy-fix)"
        self.assertIn(plain, fixed)
        self.assertNotIn(plain + " —", fixed)

    def test_multiple_hotfixes_nest_and_dual_targets_group_both(self):
        first, dual = self.collected({
            "crash-fix": delivered_spec("crash-fix",
                                        "The cart stops crashing at checkout.",
                                        HOTFIX, "**Hotfix for**: v1.2.2\n"),
            "login-fix": delivered_spec("login-fix",
                                        "The login loop rejects expired tokens.",
                                        HOTFIX,
                                        "**Hotfix for**: v1.2.2\n"
                                        "**Fixes spec**: cart-flow\n"),
        })
        self.assertEqual(dual["hotfix_target"], {"tag": "v1.2.2", "spec": "cart-flow"})
        section = self.notes([first, dual])
        fixed = self.group(section, "Fixed")
        self.assertIn("- The cart stops crashing at checkout. (crash-fix)"
                      " — patches v1.2.2", fixed)
        self.assertIn("- The login loop rejects expired tokens. (login-fix)"
                      " — patches v1.2.2 — fixes cart-flow", fixed)
        self.assertEqual(fixed.count("patches v1.2.2"), 2)

    def test_target_headers_accepted_on_hotfix_specs_only(self):
        tag = "v1.2.2"
        dirs = self.spec_tree({
            "crash-fix": draft_spec("crash-fix",
                                    "The cart stops crashing at checkout.",
                                    HOTFIX, f"**Hotfix for**: {tag}\n"),
            "login-fix": draft_spec("login-fix",
                                    "The login loop rejects expired tokens.",
                                    HOTFIX, "**Fixes spec**: cart-flow\n"),
            "both-fix": draft_spec("both-fix",
                                   "The export no longer truncates rows.",
                                   HOTFIX, f"**Hotfix for**: {tag}\n"
                                           "**Fixes spec**: cart-flow\n"),
            "cart-flow": draft_spec("cart-flow",
                                    "The cart tracks quantities per line.",
                                    FEATURE),
            "cart-metrics": draft_spec("cart-metrics",
                                       "The cart reports revenue per sale.",
                                       FEATURE, f"**Hotfix for**: {tag}\n"
                                                "**Fixes spec**: cart-flow\n"),
        }, tag=tag)
        for name in ("crash-fix", "login-fix", "both-fix"):
            with self.subTest(spec=name):
                code, out = self.checked(dirs[name])
                self.assertEqual(code, 0, out)
                self.assertIn("PASS (0 fail, 0 warn)", out)
        code, out = self.checked(dirs["cart-metrics"])
        self.assertEqual(code, 1, out)
        self.assertIn("a `**Type**: feature` spec carries neither", out)
        targetless = self.spec_tree({
            "blank-fix": draft_spec("blank-fix",
                                    "The nightly cron no longer double-fires.",
                                    HOTFIX)})
        code, out = self.checked(targetless["blank-fix"])
        self.assertEqual(code, 1, out)
        self.assertIn("no lineage target", out)

    def test_unresolvable_target_named_in_failure(self):
        dirs = self.spec_tree({
            "ghost-release-fix": draft_spec("ghost-release-fix",
                                            "The crash on launch is gone.",
                                            HOTFIX,
                                            "**Hotfix for**: v9.9.9\n"),
            "ghost-spec-fix": draft_spec("ghost-spec-fix",
                                         "The export no longer truncates rows.",
                                         HOTFIX,
                                         "**Fixes spec**: ghost\n"),
        }, tag="v1.2.2")
        for name, named in (("ghost-release-fix", "`**Hotfix for**: v9.9.9`"),
                            ("ghost-spec-fix", "`**Fixes spec**: ghost`")):
            with self.subTest(spec=name):
                code, out = self.checked(dirs[name])
                self.assertEqual(code, 1, out)
                self.assertIn(named, out)


if __name__ == "__main__":
    unittest.main()
