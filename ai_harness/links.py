"""Placing, auditing and removing artifacts.

Three guarantees carried over from sync.sh, and they are the reason this file
is small and boring on purpose:

  never overwrite   an occupied real path, or a link pointing somewhere else,
                    is reported as a conflict, never replaced
  remove only ours  removal touches a path only when it still matches what we
                    installed there
  audit honestly    a destination we never chose is not a failure
"""

from __future__ import annotations

import filecmp
import os
import shutil
from pathlib import Path

# Outcomes, ordered by how much the user needs to know about them.
OK = "ok"
CREATED = "created"
PLANNED = "planned"
UPDATED = "updated"
CONFLICT = "conflict"
MISSING = "missing"
STALE = "stale"
REMOVED = "removed"
KEPT = "kept"


class Result:
    def __init__(self, status: str, destination: Path, detail: str = ""):
        self.status = status
        self.destination = destination
        self.detail = detail

    @property
    def failed(self) -> bool:
        return self.status in (CONFLICT, MISSING, STALE)


def _same_link(destination: Path, source: Path) -> bool:
    return destination.is_symlink() and Path(os.readlink(destination)) == source


def _same_copy(destination: Path, source: Path) -> bool:
    if destination.is_symlink() or not destination.exists():
        return False
    if source.is_dir():
        return destination.is_dir()
    return filecmp.cmp(str(source), str(destination), shallow=False)


def install(operations, method: str, dry_run: bool) -> list:
    results = []
    for operation in operations:
        results.append(_install_one(operation, method, dry_run))
    return results


def _install_one(operation, method: str, dry_run: bool) -> Result:
    source, destination = operation.source, operation.destination

    if method == "link" and _same_link(destination, source):
        return Result(OK, destination)
    if method == "copy" and _same_copy(destination, source):
        return Result(OK, destination)

    if destination.is_symlink():
        target = os.readlink(destination)
        if method == "copy":
            # A leftover link from clone mode. Replacing it is the whole point
            # of running install again, so it is an update, not a conflict.
            return _write(operation, method, dry_run, UPDATED)
        return Result(CONFLICT, destination, "links to %s" % target)

    if destination.exists():
        if method == "copy":
            return _write(operation, method, dry_run, UPDATED)
        return Result(CONFLICT, destination, "a real path is already there")

    return _write(operation, method, dry_run, CREATED)


def _write(operation, method: str, dry_run: bool, status: str) -> Result:
    source, destination = operation.source, operation.destination
    if dry_run:
        return Result(PLANNED, destination)

    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.is_symlink() or destination.is_file():
        destination.unlink()
    elif destination.is_dir():
        shutil.rmtree(destination)

    if method == "link":
        destination.symlink_to(source)
    elif source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)

    return Result(status, destination)


def audit(operations, method: str) -> list:
    """Report what is in place, without asking for what was never chosen."""
    results = []
    for operation in operations:
        source, destination = operation.source, operation.destination

        if method == "link":
            if _same_link(destination, source):
                results.append(Result(OK, destination))
            elif destination.is_symlink():
                results.append(
                    Result(CONFLICT, destination, "links to %s" % os.readlink(destination))
                )
            elif destination.exists():
                results.append(Result(CONFLICT, destination, "a real path is there"))
            else:
                results.append(Result(MISSING, destination))
            continue

        if _same_copy(destination, source):
            results.append(Result(OK, destination))
        elif destination.exists() or destination.is_symlink():
            results.append(Result(STALE, destination, "differs from the source"))
        else:
            results.append(Result(MISSING, destination))

    return results


def remove(operations, method: str, dry_run: bool) -> list:
    """Take back only what still matches what we installed.

    Anything else belongs to someone else, and the point of this rule is that
    running remove can never cost a user a file they wrote.
    """
    results = []
    for operation in operations:
        source, destination = operation.source, operation.destination
        ours = _same_link(destination, source) if method == "link" else _same_copy(
            destination, source
        )

        if not ours:
            if destination.exists() or destination.is_symlink():
                results.append(Result(KEPT, destination, "not ours to remove"))
            continue

        if dry_run:
            results.append(Result(PLANNED, destination))
            continue

        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        else:
            shutil.rmtree(destination)
        results.append(Result(REMOVED, destination))

    return results
