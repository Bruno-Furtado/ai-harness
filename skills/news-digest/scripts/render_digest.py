#!/usr/bin/env python3
"""Render the digest from the model's selection lines.

The model picks and translates; this script formats. Everything factual
(url, source, tier, section) is resolved by id from the shortlist, so the
model never emits a url and an invented link is impossible by construction.

Stdin: one selection line per item, `<id>|<title>|<why>`.
Stdout: the rendered digest, brief by default.
Also writes the archive and `.last_digest.json`, which is what makes
numbered feedback ("+1 -3") resolvable on the next run.

Stdlib only. All state lives in the state home, never next to this script.
Exit codes: 0 ok (problems reported on stderr), 2 no usable shortlist.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_feeds import load_structured, state_home  # noqa: E402

MAX_WHY_WORDS = 12
DASH_RUN = re.compile(r"\s+[—–―-]+\s+")
LONE_DASH = re.compile(r"[—–―]")
EMOJI = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff️⬀-⯿]"
)
FENCE = re.compile(r"^\s*```")
LEADING_INDEX = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+")


def clean_text(text: str) -> str:
    """Strip the punctuation this digest does not use, plus emoji and markup.

    A hyphen between spaces is punctuation and goes; a hyphen inside a word
    (pt-BR, GPT-4, day-to-day) is part of the word and stays.
    """
    text = EMOJI.sub("", text or "")
    text = text.replace("[", "(").replace("]", ")")
    text = DASH_RUN.sub(", ", text)
    text = LONE_DASH.sub(",", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.:;])", r"\1", text)
    return text.strip(" ,;:")


def clip_why(why: str) -> str:
    why = clean_text(why)
    if not why:
        return ""
    words = why.split()
    if len(words) > MAX_WHY_WORDS:
        why = " ".join(words[:MAX_WHY_WORDS])
    why = why.rstrip(" .,;:")
    return why + "." if why else ""


def parse_selection(stream) -> list[tuple[str, str, str]]:
    """Read `<id>|<title>|<why>` lines, tolerating fences and list markers."""
    rows = []
    for raw in stream:
        line = raw.strip()
        if not line or line.startswith("#") or FENCE.match(line):
            continue
        line = LEADING_INDEX.sub("", line)
        parts = [p.strip() for p in line.split("|", 2)]
        if len(parts) < 2 or not parts[0]:
            print(f"skipped unparseable selection line: {line[:80]!r}", file=sys.stderr)
            continue
        rows.append((parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
    return rows


def load_shortlist(home: Path) -> dict[str, dict]:
    path = home / ".last_shortlist.jsonl"
    if not path.exists():
        print(f"error: {path} not found; run fetch_feeds.py first", file=sys.stderr)
        return {}
    index = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            index[record["id"]] = record
    return index


def build_items(rows, shortlist, max_items: int) -> list[dict]:
    items, used = [], set()
    for item_id, title, why in rows:
        if item_id in used:
            print(f"dropped repeated id {item_id}", file=sys.stderr)
            continue
        record = shortlist.get(item_id)
        if record is None:
            print(f"dropped id {item_id}: not in the shortlist", file=sys.stderr)
            continue
        used.add(item_id)
        items.append(
            {
                "id": item_id,
                "title": clean_text(title) or record["title"],
                "why": clip_why(why),
                "url": record["url"],
                "source": record["source"],
                "section": record["section"],
                "tier": record["tier"],
            }
        )
    if max_items > 0 and len(items) > max_items:
        print(f"dropped {len(items) - max_items} items over max_items={max_items}", file=sys.stderr)
        items = items[:max_items]
    # Number in reading order, not in ranking order. Items arrive ranked and
    # are then grouped by section, so numbering before grouping makes the
    # message count 1, 3, 2, which reads as a bug to whoever has to reply
    # with those numbers. Rank still decides section order and the order
    # inside each section.
    items = [item for _, group in group_sections(items) for item in group]
    for ref, item in enumerate(items, start=1):
        item["ref"] = ref
    return items


def group_sections(items: list[dict]) -> list[tuple[str, list[dict]]]:
    """Group by section, keeping the order the sections first appear in."""
    order: list[str] = []
    grouped: dict[str, list[dict]] = {}
    for item in items:
        if item["section"] not in grouped:
            grouped[item["section"]] = []
            order.append(item["section"])
        grouped[item["section"]].append(item)
    return [(name, grouped[name]) for name in order]


def render_brief(items: list[dict], header: str, footer: str) -> str:
    # Standard markdown bold. A single asterisk is italic in markdown, and a
    # channel that converts to its own dialect reads it that way.
    lines = [f"**{header}**"]
    for section, group in group_sections(items):
        lines.append("")
        lines.append(f"**{section}**")
        for item in group:
            suffix = f": {item['why']}" if item["why"] else ""
            lines.append(f"{item['ref']}. [{item['title']}]({item['url']}){suffix}")
    if footer:
        lines.extend(["", footer])
    return "\n".join(lines)


def render_full(items: list[dict], header: str, footer: str) -> str:
    lines = [f"# {header}"]
    for section, group in group_sections(items):
        lines.extend(["", f"## {section}"])
        for item in group:
            suffix = f": {item['why']}" if item["why"] else ""
            lines.append(f"{item['ref']}. [{item['title']}]({item['url']}){suffix}")
            lines.append(f"   {item['source']}, tier {item['tier']}, id {item['id']}")
    if footer:
        lines.extend(["", footer])
    return "\n".join(lines) + "\n"


def fit(items: list[dict], header: str, footer: str, max_chars: int) -> tuple[str, list[dict]]:
    """Shrink from the bottom until the brief fits in one message."""
    kept = list(items)
    text = render_brief(kept, header, footer)
    while len(text) > max_chars and len(kept) > 1:
        dropped = kept.pop()
        print(f"dropped item {dropped['ref']} to fit {max_chars} chars", file=sys.stderr)
        for ref, item in enumerate(kept, start=1):
            item["ref"] = ref
        text = render_brief(kept, header, footer)
    if len(text) > max_chars:
        print(
            f"warning: brief is {len(text)} chars, over the {max_chars} limit; "
            "the channel may split it into more than one message",
            file=sys.stderr,
        )
    return text, kept


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", help="state home directory")
    parser.add_argument("--format", choices=["brief", "full"], default="brief")
    parser.add_argument("--max-items", type=int, help="hard cap on delivered items")
    parser.add_argument("--max-chars", type=int, help="hard cap on the brief, in characters")
    parser.add_argument("--date", help="digest date, YYYY-MM-DD (default: today)")
    parser.add_argument("--no-archive", action="store_true", help="do not write digests/<date>.md")
    args = parser.parse_args()

    home = state_home(args.home)
    config = {}
    config_path = home / "config.yaml"
    if config_path.exists():
        try:
            config = load_structured(config_path) or {}
        except Exception as exc:  # noqa: BLE001 - report and continue with defaults
            print(f"warning: could not parse {config_path}: {exc}", file=sys.stderr)

    max_items = args.max_items or int(config.get("max_items", 8))
    max_chars = args.max_chars or int(config.get("brief_max_chars", 3500))
    stamp = args.date or date.today().isoformat()
    header = str(config.get("brief_header", "Digest {date}")).replace("{date}", stamp)
    footer = str(config.get("brief_footer", 'Reply "+1 -3" to tune.'))

    shortlist = load_shortlist(home)
    if not shortlist:
        return 2
    items = build_items(parse_selection(sys.stdin), shortlist, max_items)
    if not items:
        print("error: no usable items in the selection", file=sys.stderr)
        return 2

    brief, items = fit(items, header, footer, max_chars)

    (home / ".last_digest.json").write_text(
        json.dumps({"date": stamp, "items": items}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not args.no_archive:
        archive_dir = home / "digests"
        archive_dir.mkdir(parents=True, exist_ok=True)
        (archive_dir / f"{stamp}.md").write_text(render_full(items, header, footer), encoding="utf-8")

    sys.stdout.write(brief if args.format == "brief" else render_full(items, header, footer))
    if args.format == "brief":
        sys.stdout.write("\n")
    print(f"rendered {len(items)} items, brief {len(brief)} chars", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
