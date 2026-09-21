"""Tests for the generated plugin manifests and the version triple.

Every skill's VERSION file, SKILL.md frontmatter version, and generated
.claude-plugin/plugin.json version must agree — v2.5.0 shipped with
plugin.json still at 2.3.0 and SKILL.md at 2.4.0, and nothing tied all
three together. tools/plugin-manifest.py is regenerate-only and runs
manually, so the guard is a test: it fails until the manifests are
regenerated.
"""
import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FM_VERSION = re.compile(r'^  version: "(.+)"$', re.M)
FM_NAME = re.compile(r"^name: (\S+)$", re.M)
CHANGELOG_HEADING = re.compile(r"(?m)^## (\d+\.\d+\.\d+)")


def skills():
    return sorted(d for d in (REPO_ROOT / "skills").glob("*")
                  if (d / "SKILL.md").is_file())


def changelog_head(skill: Path):
    """The newest CHANGELOG.md version heading and that entry's body
    (from the heading to the next one). (None, "") with no heading."""
    text = (skill / "CHANGELOG.md").read_text()
    heads = list(CHANGELOG_HEADING.finditer(text))
    if not heads:
        return None, ""
    end = heads[1].start() if len(heads) > 1 else len(text)
    return heads[0].group(1), text[heads[0].start():end]


class VersionTripleTests(unittest.TestCase):
    def test_version_file_matches_skill_md_frontmatter(self):
        for skill in skills():
            with self.subTest(skill=skill.name):
                v_file = (skill / "VERSION").read_text().strip()
                fm = FM_VERSION.search((skill / "SKILL.md").read_text())
                self.assertIsNotNone(
                    fm, f"{skill.name}: no frontmatter version in SKILL.md")
                self.assertEqual(
                    v_file, fm.group(1),
                    f"{skill.name}: VERSION vs SKILL.md frontmatter")

    def test_plugin_json_matches_version_and_name(self):
        for skill in skills():
            with self.subTest(skill=skill.name):
                v_file = (skill / "VERSION").read_text().strip()
                pj = json.loads(
                    (skill / ".claude-plugin" / "plugin.json").read_text())
                self.assertEqual(
                    pj["version"], v_file,
                    f"{skill.name}: plugin.json version vs VERSION — "
                    f"rerun tools/plugin-manifest.py")
                fm_name = FM_NAME.search((skill / "SKILL.md").read_text())
                self.assertIsNotNone(fm_name)
                self.assertEqual(pj["name"], fm_name.group(1))


class ChangelogAlignmentTests(unittest.TestCase):
    def test_changelog_head_is_the_version_file_version(self):
        for skill in skills():
            with self.subTest(skill=skill.name):
                v_file = (skill / "VERSION").read_text().strip()
                head, _ = changelog_head(skill)
                self.assertIsNotNone(
                    head, f"{skill.name}: no version heading in CHANGELOG.md")
                self.assertEqual(
                    head, v_file,
                    f"{skill.name}: CHANGELOG.md newest entry vs VERSION")

    def test_current_entry_carries_a_migration_note(self):
        for skill in skills():
            with self.subTest(skill=skill.name):
                _, body = changelog_head(skill)
                self.assertRegex(
                    body, r"(?m)^Migration:",
                    f"{skill.name}: newest CHANGELOG.md entry has no "
                    f"'Migration:' note (start a paragraph with 'Migration:' "
                    f"— the upgrade path, or 'none required')")


class MarketplaceCatalogTests(unittest.TestCase):
    def test_catalog_matches_skill_dirs_exactly(self):
        catalog = json.loads(
            (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text())
        listed = {p["name"] for p in catalog["plugins"]}
        on_disk = {s.name for s in skills()}
        self.assertEqual(listed, on_disk,
                         "marketplace.json vs skills/*/ — "
                         "rerun tools/plugin-manifest.py")
        for p in catalog["plugins"]:
            self.assertEqual(p["source"], f"./skills/{p['name']}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
