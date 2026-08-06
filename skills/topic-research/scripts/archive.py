#!/usr/bin/env python3
"""Resolve the citation markers in a synthesis, save it and search past runs.

The model writes prose with `[id]` markers and never writes a url. This
script turns each marker into a numbered reference resolved from the
shortlist, so an invented link is impossible by construction. Same idea as
render_digest.py in the news-digest skill.

An id that is not in the shortlist becomes `[?]` and a warning, because a
citation that cannot be resolved is exactly what the reader needs to see.

Commands:
  render    read the synthesis on stdin, print the resolved report
  search    find past research by topic or title, offline
  list      show the most recent research files

Stdout: the resolved report (render) or the matches (search, list).
Stderr: warnings and a summary.
Exit codes: 0 ok, 2 nothing usable to work with.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sources import parse_date, slugify, state_home  # noqa: E402

MARKER = re.compile(r"\[([0-9a-f]{12})\]")
WORD = re.compile(r"[a-z0-9]+")


def load_shortlist(home: Path) -> dict[str, dict] | None:
    """Return the id index, or None when the collector has not run at all.

    An existing but empty file is not an error: the collector ran and the
    window was empty, and that report still deserves to be written.
    """
    path = home / ".last_shortlist.jsonl"
    if not path.exists():
        print(f"error: {path} not found; run collect.py first", file=sys.stderr)
        return None
    index = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            index[record["id"]] = record
    return index


def load_last_run(home: Path) -> dict:
    path = home / ".last_run.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"warning: {path} is corrupt, ignoring it", file=sys.stderr)
        return {}


def resolve(text: str, shortlist: dict[str, dict]) -> tuple[str, list[dict], int]:
    """Replace every `[id]` with `[n]` and collect the references in order."""
    order: list[str] = []
    unknown = 0

    def swap(match: re.Match) -> str:
        nonlocal unknown
        item_id = match.group(1)
        record = shortlist.get(item_id)
        if record is None:
            unknown += 1
            print(f"warning: citation {item_id} is not in the shortlist", file=sys.stderr)
            return "[?]"
        if item_id not in order:
            order.append(item_id)
        return f"[{order.index(item_id) + 1}]"

    return MARKER.sub(swap, text), [shortlist[i] for i in order], unknown


def render_references(records: list[dict]) -> str:
    lines = ["## References", ""]
    for number, record in enumerate(records, start=1):
        published = record.get("published", "")[:10] or "no date"
        signal = ""
        if record.get("primary") is not None:
            signal = f", {record['primary']}"
            if record.get("secondary"):
                signal += f" and {record['secondary']}"
            signal += f" {record.get('label', '')}".rstrip()
        lines.append(
            f"{number}. [{record['title']}]({record['url']}) "
            f"({record['source']}, {published}{signal})"
        )
    return "\n".join(lines)


def render_status(last_run: dict) -> str:
    rows = last_run.get("sources") or []
    if not rows:
        return ""
    def group(state: str) -> list[str]:
        return [row["source"] for row in rows if row["state"] == state]

    parts = []
    for label, state in (("active", "active"), ("limited", "limited"), ("degraded", "degraded"), ("off", "off")):
        names = group(state)
        if names:
            parts.append(f"{label}: {', '.join(names)}")
    reasons = [f"{row['source']} {row['reason']}" for row in rows if row["state"] == "degraded"]
    line = "Sources, " + "; ".join(parts) + "."
    if reasons:
        line += " Degraded because " + "; ".join(reasons) + "."
    return line


def update_index(home: Path, entry: dict) -> None:
    path = home / "index.json"
    entries = []
    if path.exists():
        try:
            entries = json.loads(path.read_text(encoding="utf-8")).get("research") or []
        except json.JSONDecodeError:
            print(f"warning: {path} was corrupt and has been rewritten", file=sys.stderr)
    entries = [e for e in entries if e.get("file") != entry["file"]]
    entries.append(entry)
    entries.sort(key=lambda e: e.get("date", ""), reverse=True)
    path.write_text(
        json.dumps({"research": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def cmd_render(home: Path, topic: str | None, stamp: str, no_archive: bool) -> int:
    shortlist = load_shortlist(home)
    if shortlist is None:
        return 2
    if not shortlist:
        print("warning: the last run collected nothing, so no citation can resolve", file=sys.stderr)
    last_run = load_last_run(home)
    topic = topic or last_run.get("topic") or "research"
    body = sys.stdin.read().strip()
    if not body:
        print("error: nothing on stdin", file=sys.stderr)
        return 2

    resolved, records, unknown = resolve(body, shortlist)
    status = render_status(last_run)
    parts = [f"# {topic}", "", resolved.strip()]
    if records:
        parts.extend(["", render_references(records)])
    if status:
        parts.extend(["", status])
    report = "\n".join(parts) + "\n"

    if not no_archive:
        folder = home / "research"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{stamp}-{slugify(topic)}.md"
        path.write_text(report, encoding="utf-8")
        update_index(
            home,
            {
                "date": stamp,
                "topic": topic,
                "file": path.name,
                "items": [
                    {"id": r["id"], "title": r["title"], "source": r["source"], "url": r["url"]}
                    for r in records
                ],
            },
        )
        print(f"saved {path}", file=sys.stderr)

    sys.stdout.write(report)
    print(
        f"resolved {len(records)} citations, {unknown} unresolved, "
        f"{len(shortlist)} items were available",
        file=sys.stderr,
    )
    return 0


def cmd_search(home: Path, query: str) -> int:
    path = home / "index.json"
    if not path.exists():
        print("no research archive yet", file=sys.stderr)
        return 0
    entries = json.loads(path.read_text(encoding="utf-8")).get("research") or []
    terms = set(WORD.findall(query.lower()))
    if not terms:
        print("error: empty query", file=sys.stderr)
        return 2
    matches = []
    for entry in entries:
        haystack = " ".join(
            [entry.get("topic", "")] + [item["title"] for item in entry.get("items") or []]
        ).lower()
        words = set(WORD.findall(haystack))
        hits = len(terms & words)
        if hits:
            matches.append((hits, entry))
    matches.sort(key=lambda pair: (pair[0], pair[1].get("date", "")), reverse=True)
    if not matches:
        print(f"no earlier research matches {query!r}")
        return 0
    for hits, entry in matches[:10]:
        print(f"{entry['date']}  {entry['topic']}  ({len(entry.get('items') or [])} sources, {entry['file']})")
        print(f"          matched {hits} of {len(terms)} terms")
    return 0


def cmd_list(home: Path, limit: int) -> int:
    path = home / "index.json"
    if not path.exists():
        print("no research archive yet", file=sys.stderr)
        return 0
    entries = json.loads(path.read_text(encoding="utf-8")).get("research") or []
    for entry in entries[:limit]:
        print(f"{entry['date']}  {entry['topic']}  ({entry['file']})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", help="state home directory")
    sub = parser.add_subparsers(dest="command", required=True)
    render = sub.add_parser("render", help="resolve citations, save and print the report")
    render.add_argument("--topic", help="report title (default: the topic of the last run)")
    render.add_argument("--date", help="report date, YYYY-MM-DD (default: today)")
    render.add_argument("--no-archive", action="store_true", help="print without saving")
    searcher = sub.add_parser("search", help="find earlier research, offline")
    searcher.add_argument("query")
    lister = sub.add_parser("list", help="show recent research")
    lister.add_argument("--limit", type=int, default=15)
    args = parser.parse_args()

    home = state_home(args.home)
    if args.command == "render":
        stamp = args.date or date.today().isoformat()
        if not parse_date(stamp) and not _valid_stamp(stamp):
            print(f"error: {stamp!r} is not a date", file=sys.stderr)
            return 2
        return cmd_render(home, args.topic, stamp, args.no_archive)
    if args.command == "search":
        return cmd_search(home, args.query)
    return cmd_list(home, args.limit)


def _valid_stamp(stamp: str) -> bool:
    try:
        datetime.strptime(stamp, "%Y-%m-%d")
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    sys.exit(main())
