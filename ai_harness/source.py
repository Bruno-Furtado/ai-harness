"""Where the artifacts come from, and how they get installed.

Two modes, one code path. In a clone the artifacts live next to the package and
get symlinked, so `git pull` reaches every tool at once. Installed from PyPI
they live inside the wheel and get copied, because `pip install -U` rewrites
that directory and a symlink into it would dangle silently after the first
upgrade.
"""

from __future__ import annotations

import json
from pathlib import Path

CLONE = "clone"
PACKAGE = "package"

# The directory the wheel unpacks the artifacts into. See pyproject.toml.
BUNDLED = "_artifacts"


class Source:
    """The artifact tree, plus how to install from it."""

    def __init__(self, root: Path, mode: str):
        self.root = root
        self.mode = mode

    @property
    def default_method(self) -> str:
        return "link" if self.mode == CLONE else "copy"

    @property
    def targets_file(self) -> Path:
        return self.root / "targets.json"

    def read_targets(self) -> dict:
        return json.loads(self.targets_file.read_text(encoding="utf-8"))

    def describe(self) -> str:
        return "from a clone" if self.mode == CLONE else "from the installed package"

    def explain_method(self) -> str:
        if self.mode == CLONE:
            return "symlink, so a git pull reaches every tool"
        return "copy, so an upgrade cannot leave dangling links"


def resolve(override: str = "") -> Source:
    """Find the artifact tree.

    `override` exists for tests and for running the packaged CLI against a
    working copy. Everything else is detected.
    """
    if override:
        root = Path(override).expanduser().resolve()
        if not (root / "targets.json").is_file():
            raise SourceError("no targets.json under %s" % root)
        mode = CLONE if (root / ".git").exists() else PACKAGE
        return Source(root, mode)

    bundled = Path(__file__).resolve().parent / BUNDLED
    if (bundled / "targets.json").is_file():
        return Source(bundled, PACKAGE)

    checkout = Path(__file__).resolve().parent.parent
    if (checkout / "targets.json").is_file():
        return Source(checkout, CLONE)

    raise SourceError(
        "cannot find the artifacts. Run ./harness from a clone, or reinstall "
        "the package with pip install -U ai-harness-cli"
    )


class SourceError(Exception):
    pass
