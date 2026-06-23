from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load_yaml(name: str) -> dict[str, Any]:
    path = ROOT / "config" / name
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}
