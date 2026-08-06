#!/usr/bin/env python3
"""Fetch the RSS/Atom feeds from the user's sources.yaml and print a JSONL shortlist.

Stdlib only. All state lives in the state home (see --home), never next to this
script, because the skill directory is usually a symlink into a repository.

Stdout: one JSON object per candidate item (with --json), or one compact
pipe-separated line per item (with --compact, the cheap form for the model).
Stderr: per-feed warnings and a run summary.
Exit codes: 0 ok (partial failures reported), 2 no usable sources file.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

USER_AGENT = "news-digest/0.1 (personal rss reader)"
TRACKING_PARAMS = re.compile(r"^(utm_|fbclid$|gclid$|ocid$|mc_cid$|mc_eid$)")
ILLEGAL_XML_BYTES = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]")
ATOM_NS = "http://www.w3.org/2005/Atom"
DC_NS = "http://purl.org/dc/elements/1.1/"


def state_home(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser()
    env = os.environ.get("NEWS_DIGEST_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".local" / "share" / "news-digest"


# --- minimal YAML subset loader -------------------------------------------
# Supports exactly what our sources/config files need: nested maps and lists
# by indentation, "key: value", "- " items, comments and quoted strings.
# PyYAML is used instead when available. JSON is accepted as-is because
# YAML 1.2 is a superset of JSON.

_MAP_ITEM = re.compile(r"^[A-Za-z0-9_-]+:(\s|$)")


def _strip_comment(line: str) -> str:
    in_single = in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if i == 0 or line[i - 1] in " \t":
                return line[:i]
    return line


def _scalar(text: str):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    low = text.lower()
    if low in ("null", "~", ""):
        return None
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def parse_yaml_subset(text: str):
    rows = []
    for raw in text.splitlines():
        line = _strip_comment(raw).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        rows.append((indent, line.strip()))
    if not rows:
        return None
    pos = 0

    def parse_block(indent: int):
        nonlocal pos
        result = None
        while pos < len(rows):
            ind, content = rows[pos]
            if ind < indent:
                break
            if ind > indent:
                raise ValueError(f"unexpected indentation near: {content!r}")
            if content.startswith("- "):
                if result is None:
                    result = []
                if not isinstance(result, list):
                    raise ValueError("cannot mix list items into a map")
                item_text = content[2:].strip()
                pos += 1
                if _MAP_ITEM.match(item_text):
                    key, value = _split_kv(item_text)
                    entry = {}
                    entry[key] = _value_or_block(value, indent)
                    while (
                        pos < len(rows)
                        and rows[pos][0] == indent + 2
                        and not rows[pos][1].startswith("- ")
                    ):
                        key2, value2 = _split_kv(rows[pos][1])
                        pos += 1
                        entry[key2] = _value_or_block(value2, indent + 2)
                    result.append(entry)
                else:
                    result.append(_scalar(item_text))
            else:
                if result is None:
                    result = {}
                if not isinstance(result, dict):
                    raise ValueError("cannot mix map keys into a list")
                key, value = _split_kv(content)
                pos += 1
                result[key] = _value_or_block(value, indent)
        return result

    def _split_kv(content: str):
        key, _, value = content.partition(":")
        return key.strip(), value.strip()

    def _value_or_block(value: str, indent: int):
        if value != "":
            return _scalar(value)
        if pos < len(rows) and rows[pos][0] > indent:
            return parse_block(rows[pos][0])
        return None

    return parse_block(rows[0][0])


def load_structured(path: Path):
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except ImportError:
        return parse_yaml_subset(text)


# --- helpers ---------------------------------------------------------------

def norm_url(url: str) -> str:
    url = url.strip()
    scheme, _, rest = url.partition("://")
    if not rest:
        return url.lower()
    host, _, path = rest.partition("/")
    path, _, query = path.partition("?")
    if query:
        kept = [p for p in query.split("&") if not TRACKING_PARAMS.match(p.split("=")[0].lower())]
        query = "&".join(kept)
    path = path.rstrip("/")
    out = f"{scheme.lower()}://{host.lower()}/{path}"
    return f"{out}?{query}" if query else out


def norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def hash12(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def strip_html(text: str, limit: int = 200) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[: limit - 1].rstrip() + "…" if len(text) > limit else text


def cap_candidates(shortlist: list[dict], limit: int) -> list[dict]:
    """Keep at most `limit` candidates, taking them round-robin across sections.

    Volume control, not editorial work: a section with 40 fresh items must not
    push a quiet section out of the list the agent gets to see. Order inside a
    section is already tier ascending, then publication descending.
    """
    if limit <= 0 or len(shortlist) <= limit:
        return shortlist
    by_section: dict[str, list[dict]] = {}
    for cand in shortlist:
        by_section.setdefault(cand["section"], []).append(cand)
    queues = list(by_section.values())
    kept: list[dict] = []
    while len(kept) < limit and any(queues):
        for queue in queues:
            if queue:
                kept.append(queue.pop(0))
                if len(kept) >= limit:
                    break
    kept.sort(key=lambda c: c["published"], reverse=True)
    kept.sort(key=lambda c: (c["section"], c["tier"]))
    return kept


def compact_line(cand: dict) -> str:
    """One pipe-separated line per candidate: no url, no summary, no timestamp.

    This is what the model reads. Dropping the url alone saves about half the
    bytes, and the model never needs it: the renderer resolves urls by id.
    """
    def clean(value: str) -> str:
        return re.sub(r"\s+", " ", str(value).replace("|", "/")).strip()

    return "|".join(
        (cand["id"], clean(cand["section"]), str(cand["tier"]), clean(cand["source"]), clean(cand["title"]))
    )


def parse_date(raw: str) -> datetime | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        pass
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def child_text(el: ET.Element, *tags: str) -> str:
    for tag in tags:
        child = el.find(tag)
        if child is not None:
            text = "".join(child.itertext()).strip()
            if text:
                return text
    return ""


def parse_feed(data: bytes) -> list[dict]:
    # XML forbids most control characters, and real feeds do ship them: one
    # stray byte would otherwise cost the whole feed. Stripping is safe on
    # UTF-8 because no continuation byte falls in this range.
    root = ET.fromstring(ILLEGAL_XML_BYTES.sub(b"", data))
    items = []
    if root.find("channel") is not None:
        for it in root.iter("item"):
            items.append(
                {
                    "title": child_text(it, "title"),
                    "url": child_text(it, "link") or child_text(it, "guid"),
                    "published": child_text(it, "pubDate", f"{{{DC_NS}}}date", "date"),
                    "summary": child_text(it, "description"),
                }
            )
    else:
        entries = root.findall(f"{{{ATOM_NS}}}entry") or root.findall("entry")
        for e in entries:
            link = ""
            for candidate in e.findall(f"{{{ATOM_NS}}}link") + e.findall("link"):
                if candidate.get("rel", "alternate") == "alternate" and candidate.get("href"):
                    link = candidate.get("href", "")
                    break
            items.append(
                {
                    "title": child_text(e, f"{{{ATOM_NS}}}title", "title"),
                    "url": link,
                    "published": child_text(
                        e, f"{{{ATOM_NS}}}published", f"{{{ATOM_NS}}}updated", "published", "updated"
                    ),
                    "summary": child_text(e, f"{{{ATOM_NS}}}summary", "summary"),
                }
            )
    return [it for it in items if it["title"] and it["url"]]


def fetch_one(feed: dict, timeout: int) -> tuple[dict, bytes | None, str | None]:
    request = urllib.request.Request(
        feed["url"], headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
        if data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
        return feed, data, None
    except (urllib.error.URLError, TimeoutError, OSError, gzip.BadGzipFile) as exc:
        return feed, None, str(exc)


def host_of(url: str) -> str:
    _, _, rest = url.partition("://")
    return rest.partition("/")[0].lower()


def fetch_host(feeds: list[dict], timeout: int, delay: float) -> list[tuple[dict, bytes | None, str | None]]:
    """Fetch one host's feeds in sequence, spaced out, and stop on 429.

    Hosts are fetched in parallel, feeds of the same host are not. Some
    servers rate limit hard per IP: hitting several of their feeds at once
    gets every one of them rejected, so being polite fetches more news than
    being fast. Once a host answers 429 the rest of its feeds are skipped
    for this run instead of hammering it further.
    """
    results = []
    for index, feed in enumerate(feeds):
        if index:
            time.sleep(delay)
        result = fetch_one(feed, timeout)
        results.append(result)
        error = result[2]
        if error and "429" in error:
            for skipped in feeds[index + 1 :]:
                results.append((skipped, None, "skipped: host answered 429 earlier in this run"))
            break
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", help="state home directory")
    parser.add_argument("--hours", type=int, help="lookback window in hours")
    parser.add_argument("--max-per-feed", type=int, help="candidate cap per feed")
    parser.add_argument("--max-candidates", type=int, help="cap on the whole shortlist")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--json", action="store_true", help="print JSONL shortlist to stdout")
    parser.add_argument("--compact", action="store_true", help="print the compact shortlist to stdout")
    parser.add_argument("--check", action="store_true", help="report feed health and exit")
    args = parser.parse_args()

    home = state_home(args.home)
    sources_path = home / "sources.yaml"
    config_path = home / "config.yaml"
    if not sources_path.exists():
        print(f"error: {sources_path} not found; run state.py init first", file=sys.stderr)
        return 2

    config = {}
    if config_path.exists():
        try:
            config = load_structured(config_path) or {}
        except Exception as exc:  # noqa: BLE001 - report and continue with defaults
            print(f"warning: could not parse {config_path}: {exc}", file=sys.stderr)
    hours = args.hours or int(config.get("lookback_hours", 36))
    max_per_feed = args.max_per_feed or int(config.get("max_per_feed", 8))
    max_candidates = args.max_candidates or int(config.get("max_candidates", 60))
    host_delay = float(config.get("host_delay_seconds", 1.5))

    try:
        sources = load_structured(sources_path)
    except Exception as exc:  # noqa: BLE001 - surface parse errors to the user
        print(f"error: could not parse {sources_path}: {exc}", file=sys.stderr)
        return 2
    sections = (sources or {}).get("sections") or []
    feeds = []
    for section in sections:
        for feed in section.get("feeds") or []:
            if feed.get("url"):
                feeds.append(
                    {
                        "name": feed.get("name") or feed["url"],
                        "url": feed["url"],
                        "tier": int(feed.get("tier", 2)),
                        "section": section.get("name", "default"),
                    }
                )
    if not feeds:
        print("error: sources.yaml has no feeds", file=sys.stderr)
        return 2

    seen_hashes = set()
    seen_path = home / "seen.json"
    if seen_path.exists():
        try:
            seen_hashes = set(json.loads(seen_path.read_text(encoding="utf-8")).get("items", {}))
        except json.JSONDecodeError:
            print(f"warning: {seen_path} is corrupt, ignoring it", file=sys.stderr)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    candidates, failures, quiet = [], [], []

    by_host: dict[str, list[dict]] = {}
    for feed in feeds:
        by_host.setdefault(host_of(feed["url"]), []).append(feed)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [
            pool.submit(fetch_host, group, args.timeout, host_delay) for group in by_host.values()
        ]
        for future in as_completed(futures):
            for feed, data, error in future.result():
                label = f"{feed['section']}/{feed['name']}"
                if error:
                    failures.append(f"{label}: {error}")
                    continue
                try:
                    raw_items = parse_feed(data)  # type: ignore[arg-type]
                except ET.ParseError as exc:
                    failures.append(f"{label}: unparseable feed ({exc})")
                    continue
                fresh = []
                for item in raw_items:
                    dt = parse_date(item["published"])
                    if dt and dt < cutoff:
                        continue
                    item["_dt"] = dt
                    fresh.append(item)
                fresh.sort(
                    key=lambda it: it["_dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True
                )
                if not fresh:
                    quiet.append(label)
                for item in fresh[:max_per_feed]:
                    url_hash = hash12(norm_url(item["url"]))
                    title_hash = hash12(norm_title(item["title"]))
                    if url_hash in seen_hashes or title_hash in seen_hashes:
                        continue
                    candidates.append(
                        {
                            "id": url_hash,
                            "title": item["title"].strip(),
                            "url": item["url"].strip(),
                            "source": feed["name"],
                            "tier": feed["tier"],
                            "section": feed["section"],
                            "published": item["_dt"].isoformat() if item["_dt"] else "",
                            "summary": strip_html(item["summary"]),
                        }
                    )

    # same-story dedupe within this run: identical normalized title keeps the lowest tier
    best_by_title: dict[str, dict] = {}
    for cand in candidates:
        key = norm_title(cand["title"])
        current = best_by_title.get(key)
        if current is None or cand["tier"] < current["tier"]:
            best_by_title[key] = cand
    shortlist = sorted(best_by_title.values(), key=lambda c: c["published"], reverse=True)
    shortlist.sort(key=lambda c: (c["section"], c["tier"]))
    collected = len(shortlist)
    shortlist = cap_candidates(shortlist, max_candidates)

    if not args.check:
        # The archive keeps the full record: the renderer resolves url, source
        # and tier from here, so the model never has to carry them.
        (home / ".last_shortlist.jsonl").write_text(
            "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in shortlist), encoding="utf-8"
        )
    if not args.check:
        if args.compact:
            for cand in shortlist:
                print(compact_line(cand))
        elif args.json:
            for cand in shortlist:
                print(json.dumps(cand, ensure_ascii=False))

    for failure in failures:
        print(f"feed-failure: {failure}", file=sys.stderr)
    capped = f", capped from {collected}" if collected > len(shortlist) else ""
    print(
        f"summary: {len(feeds)} feeds, {len(failures)} failed, {len(quiet)} quiet, "
        f"{len(shortlist)} candidates{capped} (window {hours}h)",
        file=sys.stderr,
    )
    if args.check:
        for feed in feeds:
            label = f"{feed['section']}/{feed['name']}"
            status = "FAILED" if any(f.startswith(label + ":") for f in failures) else "ok"
            note = " (quiet: no fresh items)" if label in quiet else ""
            print(f"{status}\t{feed['url']}{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
