"""Stable, editable recording-session names for the desktop app."""
from __future__ import annotations

import re
from pathlib import Path

from src.utils.config_loader import ROOT


_NUMBERED_NAME = re.compile(r"^(.*?)(\d+)$")


def next_session_name(current: str = "session_001", root: str | Path = ROOT) -> str:
    """Return the next unused numeric session name, preserving its prefix/width."""
    match = _NUMBERED_NAME.match(current.strip())
    if match is None:
        prefix, start, width = f"{current.strip() or 'session'}_", 1, 3
    else:
        prefix, digits = match.groups()
        start, width = int(digits), len(digits)
    root = Path(root)
    highest = start - 1
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)(?:_(?:raw|processed|metadata))?$")
    for directory in (root / "data" / "raw", root / "data" / "processed"):
        if not directory.exists():
            continue
        for path in directory.iterdir():
            candidate = path.stem
            found = pattern.match(candidate)
            if found is not None:
                highest = max(highest, int(found.group(1)))
    return f"{prefix}{highest + 1:0{width}d}"
