#!/usr/bin/env python3
"""Manage the news-digest state home.

Stdlib only. The state home holds user-private files and must stay outside the
skill directory: it defaults to ~/.local/share/news-digest and can be moved
with $NEWS_DIGEST_HOME or --home.

Subcommands: init, mark-shown, feedback, compact-profile, prune, status,
sources-add, sources-remove, sources-report.
All output is compact by design: aggregates and counts, never full history.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = SKILL_DIR / "assets"

GENERATED_START = "<!-- generated:start -->"
GENERATED_END = "<!-- generated:end -->"

PROFILE_SKELETON = f"""# News profile

What the user marked relevant (+) and irrelevant (-). The block below is
rewritten by `state.py compact-profile --write`; anything outside it is kept.

{GENERATED_START}
(no feedback yet)
{GENERATED_END}

## Notes

Free text about what this reader wants. Keep the whole file under 800 characters.
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


def load_last_digest(home: Path) -> list[dict]:
    """The items delivered in the last digest, in the order they were numbered."""
    path = home / ".last_digest.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("items", [])
    except json.JSONDecodeError:
        print(f"warning: {path.name} is corrupt, ignoring it", file=sys.stderr)
        return []


def load_stats(home: Path) -> dict:
    path = home / "stats.json"
    if not path.exists():
        return {"feeds": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"feeds": {}}
    data.setdefault("feeds", {})
    return data


def save_stats(home: Path, stats: dict) -> None:
    (home / "stats.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def feed_key(section: str, source: str) -> str:
    return f"{section or '?'}/{source or '?'}"


def yaml_scalar(value) -> str:
    """Quote only when a bare scalar would not survive a round trip."""
    text = str(value)
    if text == "" or text[0] in "#&*!|>%@`-?:{}[]," or text != text.strip():
        return json.dumps(text, ensure_ascii=False)
    if any(ch in text for ch in (": ", " #", "\n", '"', "'")):
        return json.dumps(text, ensure_ascii=False)
    return text


def dump_sources_yaml(data: dict, header: str) -> str:
    """Write sources.yaml back as YAML.

    The previous version dumped JSON here, which is valid YAML but throws the
    file's comments away. The leading comment block is carried over instead.
    """
    lines = [header] if header else []
    lines.append("sections:")
    for section in data.get("sections") or []:
        lines.append(f"  - name: {yaml_scalar(section.get('name', ''))}")
        if section.get("focus"):
            # Carried over on purpose: dropping it would silently strip every
            # section's intent the first time a feed is added.
            lines.append(f"    focus: {yaml_scalar(section['focus'])}")
        lines.append("    feeds:")
        for feed in section.get("feeds") or []:
            lines.append(f"      - name: {yaml_scalar(feed.get('name', ''))}")
            lines.append(f"        url: {yaml_scalar(feed.get('url', ''))}")
            lines.append(f"        tier: {int(feed.get('tier', 2))}")
    return "\n".join(lines) + "\n"


def leading_comments(path: Path) -> str:
    kept = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            kept.append(line)
            continue
        break
    return "\n".join(kept).rstrip("\n")


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


def cmd_mark_shown(home: Path, ids: list[str], use_stdin: bool, from_last: bool) -> int:
    if from_last:
        ids.extend(item["id"] for item in load_last_digest(home))
    if use_stdin:
        ids.extend(sys.stdin.read().split())
    if not ids:
        print("error: no ids given (use arguments, --stdin or --from-last)", file=sys.stderr)
        return 2
    shortlist = load_last_shortlist(home)
    # The delivered digest is the better source: it carries url and title, so
    # marking still works after the next fetch has overwritten the shortlist.
    resolved = {item["id"]: item for item in load_last_digest(home)}
    for key, value in shortlist.items():
        resolved.setdefault(key, value)
    seen = load_seen(home)
    items = seen.setdefault("items", {})
    sys.path.insert(0, str(Path(__file__).parent))
    import fetch_feeds  # local import keeps hash logic in one place

    marked, unknown = 0, []
    for item_id in ids:
        entry = resolved.get(item_id)
        if entry is None:
            unknown.append(item_id)
            items[item_id] = now_iso()
            marked += 1
            continue
        items[fetch_feeds.hash12(fetch_feeds.norm_url(entry["url"]))] = now_iso()
        items[fetch_feeds.hash12(fetch_feeds.norm_title(entry["title"]))] = now_iso()
        marked += 1
    save_seen(home, seen)

    # Per-feed tally, so sources-report can tell a productive feed from one
    # that fills the shortlist every day and never earns a slot.
    stats = load_stats(home)
    feeds = stats.setdefault("feeds", {})
    for entry in shortlist.values():
        row = feeds.setdefault(feed_key(entry.get("section", ""), entry.get("source", "")), {})
        row["offered"] = row.get("offered", 0) + 1
        # Last time the feed had anything to offer. This, not last_shown, is
        # what tells an abandoned feed from one that publishes and loses.
        row["last_offered"] = now_iso()[:10]
    for item_id in ids:
        entry = resolved.get(item_id)
        if entry is None:
            continue
        row = feeds.setdefault(feed_key(entry.get("section", ""), entry.get("source", "")), {})
        row["shown"] = row.get("shown", 0) + 1
        row["last_shown"] = now_iso()[:10]
    save_stats(home, stats)

    note = f", {len(unknown)} unknown ids stored as-is" if unknown else ""
    print(f"marked {marked} items as seen{note}; total seen: {len(items)}")
    return 0


def write_feedback(home: Path, item_id: str, verdict: str, note: str, entry: dict) -> None:
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


def cmd_feedback(home: Path, item_id: str, verdict: str, note: str) -> int:
    entry = load_last_shortlist(home).get(item_id, {})
    write_feedback(home, item_id, verdict, note, entry)
    label = entry.get("title") or "unresolved id"
    print(f"recorded {verdict} for {item_id} ({label})")
    return 0


def cmd_feedback_from_last(home: Path, reply: str) -> int:
    """Turn a chat reply such as `+1 -3 more cloud pricing` into feedback records.

    The reader answers with the numbers they saw in the message, so the refs
    are resolved through `.last_digest.json`. Without this the loop never
    closes: a reply in a messaging app has no item ids in it.
    """
    items = {item["ref"]: item for item in load_last_digest(home)}
    if not items:
        print("error: no .last_digest.json to resolve item numbers against", file=sys.stderr)
        return 2
    verdicts, words = [], []
    for token in reply.replace(",", " ").split():
        match = re.fullmatch(r"([+-])(\d+)", token)
        if match:
            verdicts.append((match.group(1), int(match.group(2))))
        else:
            words.append(token)
    note = " ".join(words).strip()
    if not verdicts and not note:
        print("error: nothing to record; expected something like '+1 -3' or free text", file=sys.stderr)
        return 2

    recorded, unknown = 0, []
    for verdict, ref in verdicts:
        entry = items.get(ref)
        if entry is None:
            unknown.append(ref)
            continue
        write_feedback(home, entry["id"], verdict, "", entry)
        recorded += 1
    if note:
        # One statement is recorded once, not copied onto every marked item.
        write_feedback(home, "", "0", note, {})
        recorded += 1
    miss = f", unknown item numbers: {unknown}" if unknown else ""
    print(f"recorded {recorded} feedback entries{miss}")
    print("next: state.py compact-profile --write")
    return 0


def write_generated_block(home: Path, block: str) -> None:
    """Replace the generated block of profile.md, keeping the free text around it."""
    path = home / "profile.md"
    text = path.read_text(encoding="utf-8") if path.exists() else PROFILE_SKELETON
    replacement = f"{GENERATED_START}\n{block.strip()}\n{GENERATED_END}"
    if GENERATED_START in text and GENERATED_END in text:
        head, _, rest = text.partition(GENERATED_START)
        _, _, tail = rest.partition(GENERATED_END)
        text = head + replacement + tail
    else:
        text = text.rstrip("\n") + "\n\n" + replacement + "\n"
    path.write_text(text, encoding="utf-8")


def cmd_compact_profile(home: Path, write: bool) -> int:
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

    lines = [
        f"liked sources: {top(plus_source)}",
        f"disliked sources: {top(minus_source)}",
        f"liked sections: {top(plus_section)}",
        f"disliked sections: {top(minus_section)}",
    ]
    if notes:
        lines.append("recent notes:")
        lines.extend(f"- {note}" for note in notes[-10:])

    if write:
        write_generated_block(home, "\n".join(lines))
        print(f"rewrote the generated block of profile.md from {len(notes)} notes")
        return 0
    print("feedback aggregates (use --write to put them into profile.md):")
    for line in lines:
        print(line)
    return 0


def cmd_prune(home: Path, days: int, max_feedback: int) -> int:
    seen = load_seen(home)
    items = seen.get("items", {})
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    kept = {}
    removed = 0
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
    sources_path.write_text(dump_sources_yaml(data, leading_comments(sources_path)), encoding="utf-8")
    print(f"added feed to section '{section}': {url} (tier {tier})")
    print("verify with: fetch_feeds.py --check")
    return 0


def cmd_sources_remove(home: Path, url: str) -> int:
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
    target = fetch_feeds.norm_url(url)
    removed = []
    for section in data.get("sections") or []:
        keep = []
        for feed in section.get("feeds") or []:
            if fetch_feeds.norm_url(str(feed.get("url", ""))) == target:
                removed.append(f"{section.get('name', '?')}/{feed.get('name', url)}")
            else:
                keep.append(feed)
        section["feeds"] = keep
    if not removed:
        print(f"no feed matched {url}")
        return 0
    sources_path.write_text(dump_sources_yaml(data, leading_comments(sources_path)), encoding="utf-8")
    print("removed: " + ", ".join(removed))
    return 0


def cmd_sources_report(home: Path, silent_days: int) -> int:
    """Which feeds earn their slot, which only add noise, which sections starve."""
    sources_path = home / "sources.yaml"
    if not sources_path.exists():
        print(f"error: {sources_path} not found; run init first", file=sys.stderr)
        return 2
    sys.path.insert(0, str(Path(__file__).parent))
    import fetch_feeds

    stats = load_stats(home).get("feeds", {})
    plus: dict[str, int] = {}
    minus: dict[str, int] = {}
    feedback_path = home / "feedback.jsonl"
    if feedback_path.exists():
        for line in feedback_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = feed_key(record.get("section", ""), record.get("source", ""))
            if record.get("verdict") == "+":
                plus[key] = plus.get(key, 0) + 1
            elif record.get("verdict") == "-":
                minus[key] = minus.get(key, 0) + 1

    try:
        data = fetch_feeds.load_structured(sources_path) or {}
    except Exception as exc:  # noqa: BLE001
        print(f"error: could not parse {sources_path}: {exc}", file=sys.stderr)
        return 2

    today = datetime.now(timezone.utc).date()

    def days_since(stamp: str) -> int | None:
        if not stamp:
            return None
        try:
            return (today - datetime.fromisoformat(stamp).date()).days
        except ValueError:
            return None

    print("feed\toffered\tshown\t+\t-\tlast shown\tsilent days")
    dead, starving, abandoned = [], [], []
    for section in data.get("sections") or []:
        section_shown = 0
        for feed in section.get("feeds") or []:
            key = feed_key(section.get("name", ""), feed.get("name", ""))
            row = stats.get(key, {})
            offered, shown = row.get("offered", 0), row.get("shown", 0)
            section_shown += shown
            silent = days_since(row.get("last_offered", ""))
            silent_label = "-" if silent is None else str(silent)
            print(
                f"{key}\t{offered}\t{shown}\t{plus.get(key, 0)}\t{minus.get(key, 0)}\t"
                f"{row.get('last_shown', 'never')}\t{silent_label}"
            )
            if offered >= 10 and shown == 0:
                dead.append(key)
            if silent is not None and silent >= silent_days:
                abandoned.append(f"{key} ({silent}d)")
        if section_shown == 0:
            starving.append(section.get("name", "?"))
    if abandoned:
        print(f"no candidates for {silent_days}+ days, check whether the feed died: " + ", ".join(abandoned))
    if dead:
        print("never selected despite 10+ offers: " + ", ".join(dead))
    if starving:
        print("sections with no selected item yet: " + ", ".join(starving))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", help="state home directory")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create the state home (idempotent)")

    mark = sub.add_parser("mark-shown", help="mark shortlist ids as seen")
    mark.add_argument("ids", nargs="*")
    mark.add_argument("--stdin", action="store_true", help="read ids from stdin, one per line")
    mark.add_argument("--from-last", action="store_true", help="use the items of the last digest")

    feedback = sub.add_parser("feedback", help="record +/- feedback for an item")
    feedback.add_argument("id", nargs="?", default="")
    feedback.add_argument("verdict", nargs="?", choices=["+", "-"], default="")
    feedback.add_argument("note", nargs="*", help="free text note")
    feedback.add_argument(
        "--from-last",
        metavar="REPLY",
        help='a chat reply such as "+1 -3 more cloud pricing", resolved against the last digest',
    )

    profile = sub.add_parser("compact-profile", help="aggregate feedback into profile.md")
    profile.add_argument("--write", action="store_true", help="rewrite the generated block of profile.md")

    prune = sub.add_parser("prune", help="drop old seen entries and cap the feedback log")
    prune.add_argument("--days", type=int, default=30)
    prune.add_argument("--max-feedback", type=int, default=500)

    sub.add_parser("status", help="print compact state counters")

    add = sub.add_parser("sources-add", help="append a feed to a section")
    add.add_argument("section")
    add.add_argument("url")
    add.add_argument("--name", default="")
    add.add_argument("--tier", type=int, default=2)

    remove = sub.add_parser("sources-remove", help="drop a feed by url")
    remove.add_argument("url")

    report = sub.add_parser("sources-report", help="per-feed offered, shown and feedback counts")
    report.add_argument("--silent-days", type=int, default=21, help="flag feeds with no candidate for this long")

    args = parser.parse_args()
    home = state_home(args.home)

    if args.command == "init":
        return cmd_init(home)
    if args.command == "mark-shown":
        return cmd_mark_shown(home, list(args.ids), args.stdin, args.from_last)
    if args.command == "feedback":
        if args.from_last:
            return cmd_feedback_from_last(home, args.from_last)
        if not args.id or not args.verdict:
            print("error: give an id and a verdict, or use --from-last", file=sys.stderr)
            return 2
        return cmd_feedback(home, args.id, args.verdict, " ".join(args.note))
    if args.command == "compact-profile":
        return cmd_compact_profile(home, args.write)
    if args.command == "prune":
        return cmd_prune(home, args.days, args.max_feedback)
    if args.command == "status":
        return cmd_status(home)
    if args.command == "sources-add":
        return cmd_sources_add(home, args.section, args.url, args.name, args.tier)
    if args.command == "sources-remove":
        return cmd_sources_remove(home, args.url)
    if args.command == "sources-report":
        return cmd_sources_report(home, args.silent_days)
    return 2


if __name__ == "__main__":
    sys.exit(main())
