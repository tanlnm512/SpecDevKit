"""Reference guards: removed command names stay out of runtime prose, and every skill-relative path a SKILL.md, command, brief, or
template names exists in that skill."""
import re
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2] / "skills"
ROOT_AGENTS = SKILLS.parent / "agents"

RETIRED = re.compile(
    r"spec-to-prod|`/spec`|/spec <|/spec-plan|/spec-idea|/spec-gen"
    r"|spec-intent|spec-shape|spec-brainstorming|spec-intake|spec-author"
    r"|spec-execute|spec-code-review|brainstorm-panelist|spec-scout"
    r"|spec-designer|spec-qa\b|spec-reviewer|spec-builder"
    r"|code-review-(?:scout|correctness|security|quality|fixer)"
    r"|design-spec\.md")
PATH_REF = re.compile(
    r"`((?:scripts|references|templates|agents|gates|contracts)/"
    r"[A-Za-z0-9_./-]+\.(?:py|sh|md|json|txt))`")


def runtime_docs():
    for skill in sorted(SKILLS.iterdir()):
        patterns = ("SKILL.md", "commands/*.md", "agents/*.md",
                    "templates/*.md")
        for pattern in patterns:
            yield from ((skill, f) for f in sorted(skill.glob(pattern)))


class RuntimeProseTests(unittest.TestCase):
    def test_no_retired_command_names(self):
        files = [f for _, f in runtime_docs()] + sorted(ROOT_AGENTS.glob("*.md"))
        hits = [f"{f.relative_to(SKILLS.parent)}: {m.group(0)}"
                for f in files
                for m in RETIRED.finditer(f.read_text(encoding="utf-8"))]
        self.assertEqual(hits, [])

    def test_named_skill_paths_exist(self):
        missing = [f"{f.relative_to(SKILLS.parent)}: {m.group(1)}"
                   for skill, f in runtime_docs()
                   for m in PATH_REF.finditer(f.read_text(encoding="utf-8"))
                   if not (skill / m.group(1)).exists()]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
