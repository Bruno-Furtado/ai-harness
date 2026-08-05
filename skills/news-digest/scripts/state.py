#!/usr/bin/env python3
"""Manage the news-digest state home.

Stdlib only. The state home holds user-private files and must stay outside the
skill directory: it defaults to ~/.local/share/news-digest and can be moved
with $NEWS_DIGEST_HOME or --home.

Subcommands: init, mark-shown, feedback, compact-profile, prune, status, sources-add.
All output is compact by design: aggregates and counts, never full history.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = SKILL_DIR / "assets"

PROFILE_SKELETON = """# News profile

What the user marked relevant (+) and irrelevant (-), compacted. Rewrite this
file from `state.py compact-profile` output; keep it under 800 characters.

(no feedback yet)
"""


def state_home(arg: str | None) -> Path:
    import os

    if arg:
        return Path(arg).expanduser()
    env = os.environ.get("NEWS_DIGEST_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".local" / "share" / "news-digest"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_seen(home: Path) -> dict:
    path = home / "seen.json"
    if not path.exists():
        return {"items": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup = path.with_suffix(".corrupt.json")
        shutil.copy(path, backup)
        print(f"warning: seen.json was corrupt; backed up to {backup.name}, starting fresh")
        return {"items": {}}


def save_seen(home: Path, seen: dict) -> None:
    (home / "seen.json").write_text(json.dumps(seen, indent=1) + "\n", encoding="utf-8")


def load_last_shortlist(home: Path) -> dict[str, dict]:
    path = home / ".last_shortlist.jsonl"
    items: dict[str, dict] = {}
    if not path.exists():
        return items
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("id"):
            items[item["id"]] = item
    return items


def cmd_init(home: Path) -> int:
    home.mkdir(parents=True, exist_ok=True)
    (home / "digests").mkdir(exist_ok=True)
    created = []
    copies = [
        (ASSETS_DIR / "sources.starter.yaml", home / "sources.yaml"),
        (ASSETS_DIR / "config.example.yaml", home / "config.yaml"),
    ]
    for source, target in copies:
        if not target.exists():
            if not source.exists():
                print(f"error: missing asset {source}", file=sys.stderr)
                return 2
            shutil.copy(source, target)
            created.append(target.name)
    for name, content in [
        ("seen.json", '{"items": {}}\n'),
        ("feedback.jsonl", ""),
        ("profile.md", PROFILE_SKELETON),
    ]:
        path = home / name
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            created.append(name)
    print(f"state home: {home}")
    print("created: " + (", ".join(created) if created else "nothing (already initialized)"))
    if (home / "sources.yaml").exists() and "sources.yaml" in created:
        print("next: replace the example sections in sources.yaml with the user's topics, then run fetch_feeds.py --check")
    return 0


def cmd_mark_shown(home: Path, ids: list[str], use_stdin: bool) -> int:
    if use_stdin:
        ids.extend(sys.stdin.read().split())
    if not ids:
        print("error: no ids given (use arguments or --stdin)", file=sys.stderr)
        return 2
    shortlist = load_last_shortlist(home)
    seen = load_seen(home)
    items = seen.setdefault("items", {})
    sys.path.insert(0, str(Path(__file__).parent))
    import fetch_feeds  # local import keeps hash logic in one place

    marked, unknown = 0, []
    for item_id in ids:
        entry = shortlist.get(item_id)
        if entry is None:
            unknown.append(item_id)
            items[item_id] = now_iso()
            marked += 1
            continue
        items[fetch_feeds.hash12(fetch_feeds.norm_url(entry["url"]))] = now_iso()
        items[fetch_feeds.hash12(fetch_feeds.norm_title(entry["title"]))] = now_iso()
        marked += 1
    save_seen(home, seen)
    note = f", {len(unknown)} unknown ids stored as-is" if unknown else ""
    print(f"marked {marked} items as seen{note}; total seen: {len(items)}")
    return 0


def cmd_feedback(home: Path, item_id: str, verdict: str, note: str) -> int:
    shortlist = load_last_shortlist(home)
    entry = shortlist.get(item_id, {})
    record = {
        "ts": now_iso(),
        "id": item_id,
        "verdict": verdict,
        "note": note,
        "title": entry.get("title", ""),
        "source": entry.get("source", ""),
        "section": entry.get("section", ""),
    }
    with (home / "feedback.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    label = entry.get("title") or "unresolved id"
    print(f"recorded {verdict} for {item_id} ({label})")
    return 0


def cmd_compact_profile(home: Path) -> int:
    path = home / "feedback.jsonl"
    if not path.exists() or path.stat().st_size == 0:
        print("no feedback yet")
        return 0
    plus_source: dict[str, int] = {}
    minus_source: dict[str, int] = {}
    plus_section: dict[str, int] = {}
    minus_section: dict[str, int] = {}
    notes = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        verdict = record.get("verdict", "")
        source = record.get("source") or "?"
        section = record.get("section") or "?"
        if verdict == "+":
            plus_source[source] = plus_source.get(source, 0) + 1
            plus_section[section] = plus_section.get(section, 0) + 1
        elif verdict == "-":
            minus_source[source] = minus_source.get(source, 0) + 1
            minus_section[section] = minus_section.get(section, 0) + 1
        if record.get("note"):
            notes.append(f"{record['ts'][:10]} {verdict} {record['note']}")

    def top(counter: dict[str, int], limit: int = 5) -> str:
        ranked = sorted(counter.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        return ", ".join(f"{name} ({count})" for name, count in ranked) or "-"

    print("feedback aggregates (rewrite profile.md from this, keep it under 800 chars):")
    print(f"liked sources: {top(plus_source)}")
    print(f"disliked sources: {top(minus_source)}")
    print(f"liked sections: {top(plus_section)}")
    print(f"disliked sections: {top(minus_section)}")
    print(f"recent notes ({min(len(notes), 10)} of {len(notes)}):")
    for note in notes[-10:]:
        print(f"  {note}")
    return 0


def cmd_prune(home: Path, days: int, max_feedback: int) -> int:
    seen = load_seen(home)
    items = seen.get("items", {})
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    kept = {}
    for key, ts in items.items():
        try:
            when = datetime.fromisoformat(ts)
        except ValueError:
            removed += 1
            continue
        if when >= cutoff:
            kept[key] = ts
        else:
            removed += 1
    seen["items"] = kept
    save_seen(home, seen)

    feedback_path = home / "feedback.jsonl"
    trimmed = 0
    if feedback_path.exists():
        lines = [l for l in feedback_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        if len(lines) > max_feedback:
            trimmed = len(lines) - max_feedback
            feedback_path.write_text("\n".join(lines[-max_feedback:]) + "\n", encoding="utf-8")
    print(f"pruned {removed} seen entries (kept {len(kept)}), trimmed {trimmed} feedback lines")
    return 0


def cmd_status(home: Path) -> int:
    seen = load_seen(home).get("items", {})
    feedback_lines = 0
    feedback_path = home / "feedback.jsonl"
    if feedback_path.exists():
        feedback_lines = sum(1 for l in feedback_path.read_text(encoding="utf-8").splitlines() if l.strip())
    sections = feeds = 0
    sources_path = home / "sources.yaml"
    if sources_path.exists():
        sys.path.insert(0, str(Path(__file__).parent))
        import fetch_feeds

        try:
            data = fetch_feeds.load_structured(sources_path) or {}
            sections = len(data.get("sections") or [])
            feeds = sum(len(s.get("feeds") or []) for s in data.get("sections") or [])
        except Exception as exc:  # noqa: BLE001 - status must not crash
            print(f"warning: could not parse sources.yaml: {exc}")
    last = home / ".last_shortlist.jsonl"
    last_run = "never"
    if last.exists():
        age = datetime.now(timezone.utc) - datetime.fromtimestamp(last.stat().st_mtime, tz=timezone.utc)
        hours = int(age.total_seconds() // 3600)
        last_run = f"{hours}h ago" if hours else "less than 1h ago"
    digests = len(list((home / "digests").glob("*.md"))) if (home / "digests").exists() else 0
    print(f"state home: {home}")
    print(f"sections: {sections}, feeds: {feeds}")
    print(f"seen items: {len(seen)}, feedback entries: {feedback_lines}")
    print(f"last shortlist: {last_run}, archived digests: {digests}")
    return 0


def cmd_sources_add(home: Path, section: str, url: str, name: str, tier: int) -> int:
    sources_path = home / "sources.yaml"
    if not sources_path.exists():
        print(f"error: {sources_path} not found; run init first", file=sys.stderr)
        return 2
    sys.path.insert(0, str(Path(__file__).parent))
    import fetch_feeds

    try:
        data = fetch_feeds.load_structured(sources_path) or {}
    except Exception as exc:  # noqa: BLE001
        print(f"error: could not parse {sources_path}: {exc}", file=sys.stderr)
        return 2
    sections = data.setdefault("sections", [])
    target = None
    for entry in sections:
        if entry.get("name") == section:
            target = entry
            break
    if target is None:
        target = {"name": section, "feeds": []}
        sections.append(target)
        print(f"created new section: {section}")
    feed_list = target.setdefault("feeds", [])
    normalized_new = fetch_feeds.norm_url(url)
    for feed in feed_list:
        if fetch_feeds.norm_url(str(feed.get("url", ""))) == normalized_new:
            print(f"feed already present in section '{section}': {url}")
            return 0
    feed_list.append({"name": name or url, "url": url, "tier": tier})
    sources_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"added feed to section '{section}': {url} (tier {tier})")
    print("verify with: fetch_feeds.py --check")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", help="state home directory")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create the state home (idempotent)")

    mark = sub.add_parser("mark-shown", help="mark shortlist ids as seen")
    mark.add_argument("ids", nargs="*")
    mark.add_argument("--stdin", action="store_true", help="read ids from stdin, one per line")

    feedback = sub.add_parser("feedback", help="record +/- feedback for an item")
    feedback.add_argument("id")
    feedback.add_argument("verdict", choices=["+", "-"])
    feedback.add_argument("note", nargs="*", help="free text note")

    sub.add_parser("compact-profile", help="print feedback aggregates for rewriting profile.md")

    prune = sub.add_parser("prune", help="drop old seen entries and cap the feedback log")
    prune.add_argument("--days", type=int, default=30)
    prune.add_argument("--max-feedback", type=int, default=500)

    sub.add_parser("status", help="print compact state counters")

    add = sub.add_parser("sources-add", help="append a feed to a section")
    add.add_argument("section")
    add.add_argument("url")
    add.add_argument("--name", default="")
    add.add_argument("--tier", type=int, default=2)

    args = parser.parse_args()
    home = state_home(args.home)

    if args.command == "init":
        return cmd_init(home)
    if args.command == "mark-shown":
        return cmd_mark_shown(home, list(args.ids), args.stdin)
    if args.command == "feedback":
        return cmd_feedback(home, args.id, args.verdict, " ".join(args.note))
    if args.command == "compact-profile":
        return cmd_compact_profile(home)
    if args.command == "prune":
        return cmd_prune(home, args.days, args.max_feedback)
    if args.command == "status":
        return cmd_status(home)
    if args.command == "sources-add":
        return cmd_sources_add(home, args.section, args.url, args.name, args.tier)
    return 2


if __name__ == "__main__":
    sys.exit(main())
