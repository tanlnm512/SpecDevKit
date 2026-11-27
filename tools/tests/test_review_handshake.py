"""The review oracle ships alone, with no digests.py, so it carries its
own copy of the tool alias table — the names a kit def dialect maps a
required tool to, any of which meets it. The two tables are pinned
equal here, the model test_ci_triage.py's twin pins."""
import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ORACLE = REPO_ROOT / "skills" / "spec-review" / "scripts" / "review_orchestrator.py"


def load(name, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReviewHandshakeTests(unittest.TestCase):
    def test_the_oracle_alias_table_is_the_digest_schemas(self):
        digests = load("kit_digests", REPO_ROOT / "skills" / "spec-design"
                       / "scripts" / "digests.py")
        sys.path.insert(0, str(ORACLE.parent))
        oracle = load("kit_review_oracle", ORACLE)
        self.assertEqual(oracle.TOOL_ALIASES, digests.TOOL_ALIASES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
