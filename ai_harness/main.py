"""Command routing and the step by step flow.

Nothing is written before the summary. That is the contract the whole UI is
built around: the person sees what will happen, where, and how many of them,
and only then confirms.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from . import __version__, links, source, state, targets, ui

STEPS = 4


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harness",
        description="Install the ai-harness artifacts into the tools you use.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="install",
        choices=("install", "update", "check", "remove"),
        help="install (default), update, check or remove",
    )
    parser.add_argument("--yes", "-y", action="store_true", help="take every default")
    parser.add_argument("--dry-run", action="store_true", help="show without writing")
    parser.add_argument("--tools", default="", help="comma separated tool ids")
    parser.add_argument("--artifacts", default="", help="comma separated artifact ids")
    parser.add_argument("--link", action="store_true", help="force symlinks")
    parser.add_argument("--copy", action="store_true", help="force copies")
    parser.add_argument("--source", default="", help="use this artifact tree")
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def _method(args, src: source.Source) -> str:
    if args.link and args.copy:
        raise SystemExit("error: --link and --copy cannot be combined")
    if args.link:
        return "link"
    if args.copy:
        return "copy"
    return src.default_method


def _split(raw: str) -> list:
    return [piece for piece in raw.replace(" ", "").split(",") if piece]


def _short(path: Path, home: Path) -> str:
    """Paths are long and the terminal is narrow. ~ buys back a lot of room."""
    text = str(path)
    prefix = str(home)
    return "~" + text[len(prefix):] if text.startswith(prefix) else text


def _validate(kind: str, given, known) -> list:
    unknown = [item for item in given if item not in known]
    if unknown:
        raise SystemExit(
            "error: unknown %s: %s. known: %s"
            % (kind, ", ".join(unknown), ", ".join(known))
        )
    return given


def _pick_tools(catalog, args, home, previous) -> list:
    known = [tool.id for tool in catalog.tools]

    if args.tools:
        return _validate("tool", _split(args.tools), known)

    if args.yes or not ui.interactive():
        # Same reach as the old sync.sh: everything, everywhere.
        return known

    if previous:
        preselected = [known.index(t) for t in previous if t in known]
        hint_source = "installed last time"
    else:
        preselected = [i for i, tool in enumerate(catalog.tools) if tool.installed_hint(home)]
        hint_source = "found on this machine"
    if not preselected:
        preselected = list(range(len(known)))
        hint_source = "none detected, so all are offered"

    ui.step(2, STEPS, "Which tools should it install into?")
    ui.detail("pre-checked: %s" % hint_source)
    ui.blank()

    options = [("%s" % tool.label, "~/%s" % tool.config_dir) for tool in catalog.tools]
    chosen = ui.choose(options, preselected)
    ui.blank()
    return [known[i] for i in chosen]


def _pick_artifacts(catalog, args, tool_ids, previous) -> list:
    offered = catalog.artifacts_for(tool_ids)
    known = [artifact.id for artifact in offered]

    if args.artifacts:
        return _validate("artifact", _split(args.artifacts), known)

    if args.yes or not ui.interactive():
        return known

    if previous:
        preselected = [known.index(a) for a in previous if a in known]
    else:
        preselected = list(range(len(known)))
    if not preselected:
        preselected = list(range(len(known)))

    ui.step(3, STEPS, "And which artifacts?")
    ui.detail("only what the chosen tools can read is listed")
    ui.blank()

    options = []
    for artifact in offered:
        readers = [t.label for t in catalog.tools if t.id in tool_ids and t.supports(artifact.id)]
        options.append((artifact.label, ", ".join(readers)))

    chosen = ui.choose(options, preselected)
    ui.blank()
    return [known[i] for i in chosen]


def _report(results, verbose: bool) -> dict:
    tally = {}
    for result in results:
        tally[result.status] = tally.get(result.status, 0) + 1
        if result.failed:
            ui.warn("%s: %s" % (result.status, result.destination))
            if result.detail:
                ui.detail(result.detail)
        elif verbose:
            ui.detail(str(result.destination))
    return tally


def _hook_note(catalog, tool_ids, artifact_ids) -> None:
    if "hooks" not in artifact_ids:
        return
    pending = [
        catalog.tool(t).label
        for t in tool_ids
        if catalog.tool(t).hooks == "snippet"
    ]
    if not pending:
        return
    ui.blank()
    ui.warn("one step left, and it is manual")
    ui.detail(
        "a hook is executable code, so %s need a snippet pasted once"
        % " and ".join(pending)
    )
    ui.detail("how: hooks/README.md")


def _selection(catalog, args, home, saved):
    tool_ids = _pick_tools(catalog, args, home, saved.get("tools"))
    if not tool_ids:
        raise ui.Cancelled()
    artifact_ids = _pick_artifacts(catalog, args, tool_ids, saved.get("artifacts"))
    if not artifact_ids:
        raise ui.Cancelled()
    return tool_ids, artifact_ids


def _install(args, src, catalog, home, saved) -> int:
    method = _method(args, src)

    ui.cover(__version__)
    ui.step(1, STEPS, "Where things stand")
    ui.detail(
        "python %d.%d, running %s"
        % (sys.version_info[0], sys.version_info[1], src.describe())
    )
    ui.detail("artifacts: %s" % _short(src.root, home))
    if args.link or args.copy:
        ui.detail("method: %s, forced by a flag" % method)
    else:
        ui.detail("method: %s" % src.explain_method())
    ui.blank()

    tool_ids, artifact_ids = _selection(catalog, args, home, saved)
    operations = targets.plan(catalog, src.root, home, tool_ids, artifact_ids)

    ui.step(4, STEPS, "About to install")
    ui.detail(
        "%s into %s, by %s"
        % (ui.count(len(operations), "items"), ui.count(len(tool_ids), "tools"), method)
    )
    if args.dry_run:
        ui.blank()
        for operation in operations:
            print("  %s" % operation.destination)
        ui.blank()
        ui.success("dry run, nothing was written")
        return 0

    if not args.yes and ui.interactive() and not ui.confirm("go ahead?"):
        raise ui.Cancelled()
    ui.blank()

    results = links.install(operations, method, dry_run=False)
    tally = _report(results, verbose=False)

    done = tally.get(links.CREATED, 0) + tally.get(links.UPDATED, 0)
    unchanged = tally.get(links.OK, 0)
    conflicts = tally.get(links.CONFLICT, 0)

    entries = [str(r.destination) for r in results if not r.failed]
    state.save(src.mode, method, tool_ids, artifact_ids, entries)

    ui.success(
        "%s installed, %s already in place" % (ui.count(done, "items"), ui.count(unchanged, "items"))
    )
    if conflicts:
        ui.warn("%s left untouched, listed above" % ui.count(conflicts, "items"))

    _hook_note(catalog, tool_ids, artifact_ids)
    return 1 if conflicts else 0


def _check(args, src, catalog, home, saved) -> int:
    if not saved:
        ui.warn("nothing installed by this CLI yet")
        ui.detail("run harness install first")
        return 0

    method = saved.get("method", src.default_method)
    tool_ids = saved.get("tools", [])
    artifact_ids = saved.get("artifacts", [])
    operations = targets.plan(catalog, src.root, home, tool_ids, artifact_ids)
    results = links.audit(operations, method)
    tally = _report(results, verbose=False)

    ok = tally.get(links.OK, 0)
    broken = sum(tally.get(status, 0) for status in (links.MISSING, links.CONFLICT, links.STALE))

    if broken:
        ui.warn("%s in place, %s need attention" % (ui.count(ok, "items"), ui.count(broken, "items")))
        ui.detail("harness install puts the missing ones back")
        return 1

    ui.success("%s in place, installed by %s" % (ui.count(ok, "items"), method))
    return 0


def _update(args, src, catalog, home, saved) -> int:
    ui.cover(__version__)

    pulled = True
    if src.mode == source.CLONE:
        ui.step(1, 2, "Pulling the latest artifacts")
        result = subprocess.run(
            ["git", "-C", str(src.root), "pull", "--ff-only"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            # The checkout on disk is still perfectly installable, so this is a
            # warning and not a stop: reconciling what is already here is worth
            # more than refusing to do anything.
            pulled = False
            ui.warn("could not pull, continuing with the artifacts already here")
            for line in (result.stderr or result.stdout).strip().splitlines()[:2]:
                ui.detail(line.strip())
        else:
            ui.detail(
                result.stdout.strip().splitlines()[-1]
                if result.stdout.strip()
                else "already up to date"
            )
    else:
        ui.step(1, 2, "Updating the package")
        ui.detail("this CLI ships the artifacts, so the package is the update")
        ui.detail("run: pip install -U ai-harness-cli")
        ui.detail("then run harness update again to reconcile")

    ui.blank()
    ui.step(2, 2, "Reconciling what is installed")
    if not saved:
        ui.warn("nothing installed by this CLI yet, so there is nothing to reconcile")
        return 0

    method = saved.get("method", src.default_method)
    operations = targets.plan(
        catalog, src.root, home, saved.get("tools", []), saved.get("artifacts", [])
    )
    results = links.install(operations, method, dry_run=args.dry_run)
    tally = _report(results, verbose=False)

    if args.dry_run:
        ui.success("dry run, nothing was written")
        return 0

    entries = [str(r.destination) for r in results if not r.failed]
    state.save(src.mode, method, saved.get("tools", []), saved.get("artifacts", []), entries)

    changed = tally.get(links.CREATED, 0) + tally.get(links.UPDATED, 0)
    ui.success(
        "%s refreshed, %s already current"
        % (ui.count(changed, "items"), ui.count(tally.get(links.OK, 0), "items"))
    )
    return 0 if pulled else 1


def _remove(args, src, catalog, home, saved) -> int:
    if not saved:
        ui.warn("nothing installed by this CLI, so there is nothing to remove")
        return 0

    method = saved.get("method", src.default_method)
    operations = targets.plan(
        catalog, src.root, home, saved.get("tools", []), saved.get("artifacts", [])
    )
    results = links.remove(operations, method, dry_run=args.dry_run)
    tally = _report(results, verbose=False)

    kept = tally.get(links.KEPT, 0)
    if args.dry_run:
        ui.success("dry run, %s would be removed" % ui.count(tally.get(links.PLANNED, 0), "items"))
        return 0

    state.clear()
    ui.success("%s removed" % ui.count(tally.get(links.REMOVED, 0), "items"))
    if kept:
        ui.detail("%d left alone, because they were not installed by this CLI" % kept)
    return 0


HANDLERS = {
    "install": _install,
    "update": _update,
    "check": _check,
    "remove": _remove,
}


def main(argv=None) -> int:
    args = _parser().parse_args(argv)

    try:
        src = source.resolve(args.source)
    except source.SourceError as error:
        print("error: %s" % error, file=sys.stderr)
        return 1

    catalog = targets.Catalog(src.read_targets())
    home = Path.home()
    saved = state.load()

    try:
        return HANDLERS[args.command](args, src, catalog, home, saved)
    except ui.Cancelled:
        ui.blank()
        ui.warn("cancelled, nothing was written")
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
