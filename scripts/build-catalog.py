#!/usr/bin/env python3
"""Regenerate the generated tables in both READMEs.

Two of them, from two sources.

The catalog comes from docs/catalog.json, not from the artifact frontmatter:
`description` is trigger text, written for a model and often several lines
long. Keeping the table text out of the artifact also keeps the frontmatter
portable, with no key invented by this repository. The generator fails when an
artifact has no entry, or an entry has no artifact, so a new artifact cannot
ship without a line in both languages.

The integration table comes from targets.json, the same file the harness CLI
installs from. It used to be transcribed by hand in two languages, with nothing
checking it against the installer, so it could drift silently.
"""

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "docs" / "catalog.json"
TARGETS = ROOT / "targets.json"
START = "<!-- catalog:start -->"
END = "<!-- catalog:end -->"
TARGETS_START = "<!-- integration:start -->"
TARGETS_END = "<!-- integration:end -->"

# kind -> (directory label, heading in English, heading in Portuguese)
SECTIONS = (
    ("skill", "Skills", "Skills"),
    ("agent", "Agents", "Agents"),
    ("command", "Commands", "Commands"),
    ("hook", "Hooks", "Hooks"),
    ("rule", "Rules", "Rules"),
)

HEADERS = {
    "en": ("Name", "What it does"),
    "pt": ("Nome", "O que faz"),
}

# How to invoke an artifact is the tool's job to surface, not this table's.
FIELDS = ("does",)

INTEGRATION_HEADER = {"en": "Artifact", "pt": "Artefato"}

READMES = {
    "en": ROOT / "README.md",
    "pt": ROOT / "README.pt-BR.md",
}


def discover():
    """Return {kind: [(name, path relative to the repository root)]}."""
    found = {kind: [] for kind, _, _ in SECTIONS}

    for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
        found["skill"].append((skill.parent.name, skill.relative_to(ROOT)))
    for agent in sorted((ROOT / "agents").glob("*.md")):
        found["agent"].append((agent.stem, agent.relative_to(ROOT)))
    for command in sorted((ROOT / "commands").glob("*.md")):
        found["command"].append((command.stem, command.relative_to(ROOT)))
    for hook in sorted((ROOT / "hooks").glob("*.sh")):
        found["hook"].append((hook.stem, hook.relative_to(ROOT)))
    for rule in sorted((ROOT / "rules").glob("*.md")):
        found["rule"].append((rule.stem, rule.relative_to(ROOT)))

    return found


def check_coverage(found, catalog):
    """Every artifact needs an entry, and every entry needs an artifact."""
    artifacts = {f"{kind}/{name}" for kind, items in found.items() for name, _ in items}
    problems = []

    for key in sorted(artifacts - set(catalog)):
        problems.append(f"{key} has no entry in {CATALOG.relative_to(ROOT)}")
    for key in sorted(set(catalog) - artifacts):
        problems.append(f"{key} is listed in {CATALOG.relative_to(ROOT)} but no artifact matches")

    for key in sorted(artifacts & set(catalog)):
        entry = catalog[key]
        for language in HEADERS:
            for field in FIELDS:
                if not str(entry.get(language, {}).get(field, "")).strip():
                    problems.append(f"{key} is missing a non-empty '{language}.{field}'")

    return problems


def cell(text):
    """A pipe inside a cell ends the column, so escape it."""
    return text.replace("|", "\\|")


def render(found, catalog, language):
    name_header, does_header = HEADERS[language]
    lines = []

    for kind, heading_en, heading_pt in SECTIONS:
        items = found[kind]
        if not items:
            continue
        lines.append(f"### {heading_en if language == 'en' else heading_pt}")
        lines.append("")
        lines.append(f"| {name_header} | {does_header} |")
        lines.append("| --- | --- |")
        for name, path in items:
            entry = catalog[f"{kind}/{name}"][language]
            lines.append(f"| [{name}]({path}) | {cell(entry['does'])} |")
        lines.append("")

    return "\n".join(lines).rstrip()


def render_integration(targets, language):
    """The Integration table, straight from what the installer reads."""
    tools = targets["tools"]
    artifacts = [a for a in targets["artifacts"] if a.get("table", True)]
    unsupported = targets["unsupported"][language]

    header = [INTEGRATION_HEADER[language]] + [tool["label"] for tool in tools]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * len(header)) + " |",
    ]

    for artifact in artifacts:
        row = [f"`{artifact['doc']}`"]
        for tool in tools:
            destination = tool.get("install", {}).get(artifact["id"])
            row.append(f"`~/{destination}`" if destination else unsupported)
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def splice(text, block, path, start=START, end=END):
    if start not in text or end not in text:
        raise SystemExit(f"error: {path.name} has no {start} / {end} markers")
    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)
    return f"{head}{start}\n\n{block}\n\n{end}{tail}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report an out-of-date catalog instead of rewriting it",
    )
    args = parser.parse_args()

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    targets = json.loads(TARGETS.read_text(encoding="utf-8"))
    found = discover()

    problems = check_coverage(found, catalog)
    if problems:
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        return 1

    stale = False
    for language, path in READMES.items():
        current = path.read_text(encoding="utf-8")
        updated = splice(current, render(found, catalog, language), path)
        updated = splice(
            updated,
            render_integration(targets, language),
            path,
            TARGETS_START,
            TARGETS_END,
        )
        if current == updated:
            continue
        if args.check:
            stale = True
            diff = difflib.unified_diff(
                current.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile=f"{path.name} (committed)",
                tofile=f"{path.name} (generated)",
            )
            sys.stderr.writelines(diff)
        else:
            path.write_text(updated, encoding="utf-8")
            print(f"updated: {path.relative_to(ROOT)}")

    if stale:
        print("error: run python3 scripts/build-catalog.py and commit the result", file=sys.stderr)
        return 1

    print("catalog up to date" if args.check else "catalog written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
