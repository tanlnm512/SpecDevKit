import json
import tempfile
import unittest
from pathlib import Path


class LoadConfigTest(unittest.TestCase):
    def test_loads_settings(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "settings.json").write_text(json.dumps({"currency": "USD"}))
            from app import load_config
            self.assertEqual(load_config(root), {"currency": "USD"})


if __name__ == "__main__":
    unittest.main()
