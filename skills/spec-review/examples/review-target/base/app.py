"""Tiny storefront app — fixture base, deliberately boring."""
from pathlib import Path

CONFIG_NAME = "settings.json"


def load_config(root: Path) -> dict:
    raw = (root / CONFIG_NAME).read_text()
    import json
    return json.loads(raw)
