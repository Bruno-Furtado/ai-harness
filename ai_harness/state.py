"""What was installed, so check and remove can be honest about it.

The old sync.sh could work without state: it always installed everything
everywhere, so anything missing was a failure. With a partial selection that
assumption breaks, and a copy carries no trace of where it came from, so the
inventory has to be written down.

It lives outside the repository because in package mode there is no clone.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import __version__

SCHEMA = 1


def state_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "ai-harness" / "state.json"


def load() -> dict:
    path = state_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        # A corrupt state file must not stop someone from reinstalling.
        return {}
    return data if isinstance(data, dict) else {}


def save(mode: str, method: str, tools, artifacts, entries) -> Path:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": SCHEMA,
        "version": __version__,
        "mode": mode,
        "method": method,
        "tools": list(tools),
        "artifacts": list(artifacts),
        "entries": sorted(entries),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def clear() -> None:
    path = state_path()
    if path.is_file():
        path.unlink()
