from pathlib import Path
import sys
from typing import Any

import yaml


# Bundled apps read packaged config/model resources from _MEIPASS but write
# recordings beside the executable, never into a temporary bundle directory.
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else RESOURCE_ROOT


def load_yaml(name: str) -> dict[str, Any]:
    path = RESOURCE_ROOT / "config" / name
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}
