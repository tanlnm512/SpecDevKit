"""The capability handshake accepts every tool name the kit's own def
dialects map a required tool to: a Droid developer reports Execute and
Create, an omp one lowercase names — none may be refused for its
harness's spelling. The alias table and the dialect maps are pinned
together here."""

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HandshakeNamesTests(unittest.TestCase):
    def test_mapped_names_satisfy_and_a_short_report_does_not(self):
        digests = _load("kit_digests", REPO / "skills" / "spec-design"
                        / "scripts" / "digests.py")
        agent_defs = _load("kit_agent_defs", REPO / "tools" / "agent-defs.py")
        missing = digests.tools_missing
        self.assertEqual(missing("developer", {"Create", "Execute"}), ())
        self.assertEqual(missing("developer", {"write", "bash"}), ())
        self.assertEqual(missing("developer", {"ApplyPatch", "Execute"}), ())
        self.assertEqual(missing("auditor", {"Read"}), ())
        self.assertEqual(missing("developer", {"Read"}),
                         ("Write or Edit", "Bash"))
        for kit_tool, droid_name in agent_defs.DROID_TOOLS.items():
            with self.subTest(droid=droid_name):
                if kit_tool == "read":
                    self.assertEqual(missing("auditor", {droid_name}), ())
                elif kit_tool == "bash":
                    self.assertNotIn("Bash",
                                     missing("developer", {droid_name}))
                elif kit_tool in ("write", "edit"):
                    self.assertNotIn("Write or Edit",
                                     missing("developer", {droid_name}))


if __name__ == "__main__":
    unittest.main()
