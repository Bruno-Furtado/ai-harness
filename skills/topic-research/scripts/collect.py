#!/usr/bin/env python3
"""Run a query plan against the configured sources and print a shortlist.

The model writes the plan and judges the result. This script does the
mechanical part: fetch, filter by window, deduplicate, rank by engagement
inside each source, and report every source as active, degraded or off.

A source that fails is reported as degraded on stderr. It is never silently
dropped, because a quiet gap reads as "nothing happened" and that is the one
lie this skill must not tell.

Stdin: nothing.
Stdout: one compact line per item (--compact) or one JSON object (--json).
Stderr: one status line per source, then a summary.
Exit codes: 0 ok (partial failures reported), 2 no usable plan.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sources import (  # noqa: E402
    RateLimited,
    hash12,
    http_get,
    http_json,
    load_config,
    norm_title,
    norm_url,
    parse_date,
    read_credential,
    source_status,
    state_home,
    strip_html,
)

ATOM_NS = "http://www.w3.org/2005/Atom"
ILLEGAL_XML_BYTES = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]")
DEFAULT_DAYS = 30
DEFAULT_PER_SOURCE = 12
DEFAULT_MAX_ITEMS = 60


def now() -> datetime:
    return datetime.now(timezone.utc)


def make_item(
    source: str,
    title: str,
    url: str,
    published: datetime | None,
    primary: int | None = None,
    secondary: int | None = None,
    label: str = "",
    extra: str = "",
) -> dict:
    return {
        "id": hash12(norm_url(url)),
        "source": source,
        "title": re.sub(r"\s+", " ", (title or "").strip()) or "(untitled)",
        "url": url.strip(),
        "published": published.isoformat() if published else "",
        "primary": primary,
        "secondary": secondary,
        "label": label,
        "extra": extra,
    }


def in_window(item: dict, cutoff: datetime, keep_undated: bool) -> bool:
    if not item["published"]:
        return keep_undated
    dt = parse_date(item["published"])
    return bool(dt and dt >= cutoff)


# --- collectors ------------------------------------------------------------
# Every collector takes the resolved plan entry and returns raw items. It may
# raise: the driver turns an exception into a degraded status line.

def collect_hackernews(entry: dict, cutoff: datetime, limit: int) -> list[dict]:
    items = []
    for query in entry["queries"]:
        data = http_json(
            "https://hn.algolia.com/api/v1/search",
            params={
                "query": query,
                "tags": "story",
                "numericFilters": f"created_at_i>{int(cutoff.timestamp())}",
                "hitsPerPage": limit,
            },
        )
        for hit in data.get("hits", []):
            story_id = hit.get("objectID")
            if not story_id:
                continue
            items.append(
                make_item(
                    "hackernews",
                    hit.get("title") or hit.get("story_title") or "",
                    f"https://news.ycombinator.com/item?id={story_id}",
                    parse_date(hit.get("created_at", "")),
                    primary=int(hit.get("points") or 0),
                    secondary=int(hit.get("num_comments") or 0),
                    label="points and comments",
                    extra=hit.get("url") or "",
                )
            )
    return items


def collect_github(entry: dict, cutoff: datetime, limit: int) -> list[dict]:
    items = []
    pushed = cutoff.date().isoformat()
    for query in entry["queries"]:
        data = http_json(
            "https://api.github.com/search/repositories",
            params={
                "q": f"{query} pushed:>={pushed}",
                "sort": "stars",
                "order": "desc",
                "per_page": limit,
            },
            headers={"Accept": "application/vnd.github+json"},
        )
        for repo in data.get("items", []):
            items.append(
                make_item(
                    "github",
                    f"{repo.get('full_name', '')}: {strip_html(repo.get('description') or '', 120)}",
                    repo.get("html_url", ""),
                    parse_date(repo.get("pushed_at", "")),
                    primary=int(repo.get("stargazers_count") or 0),
                    secondary=int(repo.get("open_issues_count") or 0),
                    label="stars",
                )
            )
    return items


def collect_arxiv(entry: dict, cutoff: datetime, limit: int) -> list[dict]:
    """arXiv asks for one request every few seconds and throttles per IP.

    It answers 429 and then 503 when it decides an address is too eager, so
    this collector waits longer between attempts than the others.
    """
    items = []
    for query in entry["queries"]:
        raw = http_get(
            "https://export.arxiv.org/api/query",
            params={
                "search_query": f'all:"{query}"',
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "max_results": limit,
            },
            retries=3,
            backoff=5.0,
        )
        root = ET.fromstring(ILLEGAL_XML_BYTES.sub(b"", raw))
        for node in root.findall(f"{{{ATOM_NS}}}entry"):
            title = " ".join((node.findtext(f"{{{ATOM_NS}}}title") or "").split())
            link = ""
            for candidate in node.findall(f"{{{ATOM_NS}}}link"):
                if candidate.get("rel", "alternate") == "alternate":
                    link = candidate.get("href", "")
                    break
            if not link:
                continue
            items.append(
                make_item(
                    "arxiv",
                    title,
                    link,
                    parse_date(node.findtext(f"{{{ATOM_NS}}}published") or ""),
                    label="no engagement signal, ranked by recency",
                )
            )
    return items


def collect_polymarket(entry: dict, cutoff: datetime, limit: int) -> list[dict]:
    """Open markets matching the topic, ranked by money committed.

    Markets are forward looking, so the window does not apply to them: an
    open market is current by definition. That is why keep_undated is on for
    this source.
    """
    items = []
    for query in entry["queries"]:
        data = http_json(
            "https://gamma-api.polymarket.com/public-search",
            params={"q": query, "limit_per_type": limit},
        )
        events = data.get("events") if isinstance(data, dict) else None
        for event in events or []:
            slug = event.get("slug")
            if not slug:
                continue
            try:
                volume = int(float(event.get("volume") or 0))
            except (TypeError, ValueError):
                volume = 0
            items.append(
                make_item(
                    "polymarket",
                    event.get("title") or slug,
                    f"https://polymarket.com/event/{slug}",
                    None,
                    primary=volume,
                    label="dollars of volume",
                    extra=f"ends {event.get('endDate', '')[:10]}",
                )
            )
    return items


def _reddit_token() -> str | None:
    client_id = read_credential("REDDIT_CLIENT_ID")
    secret = read_credential("REDDIT_CLIENT_SECRET")
    if not (client_id and secret):
        return None
    import base64

    basic = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    data = http_json(
        "https://www.reddit.com/api/v1/access_token",
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=b"grant_type=client_credentials",
    )
    return data.get("access_token")


def _reddit_window(cutoff: datetime) -> str:
    days = max((now() - cutoff).days, 1)
    for limit, name in ((1, "day"), (7, "week"), (31, "month"), (365, "year")):
        if days <= limit:
            return name
    return "all"


def collect_reddit(entry: dict, cutoff: datetime, limit: int) -> list[dict]:
    token = _reddit_token()
    window = _reddit_window(cutoff)
    if token:
        return _reddit_api(entry, window, limit, token)
    return _reddit_public(entry, window, limit)


def _reddit_api(entry: dict, window: str, limit: int, token: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    items = []
    targets = [("/search", {"q": q}) for q in entry["queries"]]
    targets += [
        (f"/r/{sub.strip('/')}/search", {"q": q, "restrict_sr": "true"})
        for sub in entry["communities"]
        for q in entry["queries"]
    ]
    for path, params in targets:
        data = http_json(
            f"https://oauth.reddit.com{path}",
            params={**params, "sort": "top", "t": window, "limit": limit, "type": "link"},
            headers=headers,
        )
        for child in (data.get("data") or {}).get("children") or []:
            post = child.get("data") or {}
            if not post.get("permalink"):
                continue
            created = post.get("created_utc")
            items.append(
                make_item(
                    "reddit",
                    post.get("title") or "",
                    f"https://www.reddit.com{post['permalink']}",
                    datetime.fromtimestamp(created, timezone.utc) if created else None,
                    primary=int(post.get("score") or 0),
                    secondary=int(post.get("num_comments") or 0),
                    label="score and comments",
                    extra=f"r/{post.get('subreddit', '')}",
                )
            )
    return items


def _reddit_public(entry: dict, window: str, limit: int) -> list[dict]:
    """Public feeds: no score, and the host rate limits after a request or two.

    Kept because it is the only path that works with no account at all. The
    driver marks the source limited so the synthesis never presents these
    items as ranked by engagement.
    """
    items = []
    urls = [
        f"https://www.reddit.com/search.rss?{urllib.parse.urlencode({'q': q, 'sort': 'top', 't': window, 'type': 'link'})}"
        for q in entry["queries"]
    ]
    urls += [
        f"https://www.reddit.com/r/{sub.strip('/')}/top.rss?t={window}"
        for sub in entry["communities"]
    ]
    for url in urls:
        raw = http_get(url, retries=1, backoff=4.0)
        root = ET.fromstring(ILLEGAL_XML_BYTES.sub(b"", raw))
        for node in root.findall(f"{{{ATOM_NS}}}entry")[:limit]:
            link = ""
            for candidate in node.findall(f"{{{ATOM_NS}}}link"):
                link = candidate.get("href", "")
                if link:
                    break
            if not link:
                continue
            items.append(
                make_item(
                    "reddit",
                    node.findtext(f"{{{ATOM_NS}}}title") or "",
                    link,
                    parse_date(node.findtext(f"{{{ATOM_NS}}}updated") or ""),
                    label="no score on the public feed",
                )
            )
    return items


def collect_bluesky(entry: dict, cutoff: datetime, limit: int) -> list[dict]:
    handle = read_credential("BSKY_HANDLE")
    password = read_credential("BSKY_APP_PASSWORD")
    session = http_json(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"identifier": handle, "password": password}).encode("utf-8"),
    )
    token = session.get("accessJwt")
    if not token:
        raise RuntimeError("createSession returned no access token")
    items = []
    for query in entry["queries"]:
        data = http_json(
            "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts",
            params={"q": query, "sort": "top", "limit": limit},
            headers={"Authorization": f"Bearer {token}"},
        )
        for post in data.get("posts", []):
            uri = post.get("uri", "")
            author = (post.get("author") or {}).get("handle", "")
            rkey = uri.rsplit("/", 1)[-1] if uri else ""
            if not (author and rkey):
                continue
            record = post.get("record") or {}
            items.append(
                make_item(
                    "bluesky",
                    strip_html(record.get("text") or "", 160),
                    f"https://bsky.app/profile/{author}/post/{rkey}",
                    parse_date(record.get("createdAt") or post.get("indexedAt") or ""),
                    primary=int(post.get("likeCount") or 0),
                    secondary=int(post.get("repostCount") or 0) + int(post.get("replyCount") or 0),
                    label="likes, reposts and replies",
                    extra=f"@{author}",
                )
            )
    return items


def collect_x(entry: dict, cutoff: datetime, limit: int) -> list[dict]:
    """X through the xAI API, which is model mediated by design.

    The model that runs the search is the user's choice and is read from
    XAI_MODEL. Nothing in this repository pins a model.
    """
    api_key = read_credential("XAI_API_KEY")
    model = read_credential("XAI_MODEL")
    prompt = (
        "Search X for posts about: {topic}\n"
        "Only posts published between {start} and {end}.\n"
        "Return ONLY valid JSON, no other text, in this exact shape:\n"
        '{{"items":[{{"text":"","url":"https://x.com/user/status/123",'
        '"date":"YYYY-MM-DD","likes":0,"reposts":0}}]}}\n'
        "At most {limit} items, highest engagement first."
    )
    items = []
    for query in entry["queries"]:
        payload = {
            "model": model,
            "tools": [
                {
                    "type": "x_search",
                    "from_date": cutoff.date().isoformat(),
                    "to_date": now().date().isoformat(),
                }
            ],
            "input": [
                {
                    "role": "user",
                    "content": prompt.format(
                        topic=query,
                        start=cutoff.date().isoformat(),
                        end=now().date().isoformat(),
                        limit=limit,
                    ),
                }
            ],
        }
        data = http_json(
            "https://api.x.ai/v1/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps(payload).encode("utf-8"),
            timeout=90,
        )
        for post in _x_items(data):
            url = str(post.get("url") or "")
            if not url.startswith("https://x.com/"):
                continue
            items.append(
                make_item(
                    "x",
                    strip_html(str(post.get("text") or ""), 160),
                    url,
                    parse_date(str(post.get("date") or "")),
                    primary=int(post.get("likes") or 0),
                    secondary=int(post.get("reposts") or 0),
                    label="likes and reposts, as reported by the model",
                )
            )
    return items


def _x_items(data: dict) -> list[dict]:
    """Pull the JSON block out of the response, whichever shape it arrives in."""
    text = ""
    output = data.get("output")
    if isinstance(output, str):
        text = output
    elif isinstance(output, list):
        for block in output:
            if isinstance(block, dict):
                for part in block.get("content") or []:
                    if isinstance(part, dict) and part.get("text"):
                        text = part["text"]
                        break
                text = text or str(block.get("text") or "")
            elif isinstance(block, str):
                text = block
            if text:
                break
    if not text:
        for choice in data.get("choices") or []:
            text = (choice.get("message") or {}).get("content") or ""
            if text:
                break
    match = re.search(r'\{[\s\S]*"items"[\s\S]*\}', text)
    if not match:
        raise RuntimeError("the xAI response carried no items block")
    return json.loads(match.group()).get("items") or []


def collect_youtube(entry: dict, cutoff: datetime, limit: int) -> list[dict]:
    items = []
    for query in entry["queries"]:
        result = subprocess.run(
            [
                "yt-dlp",
                f"ytsearch{limit}:{query}",
                "--dump-json",
                "--skip-download",
                "--no-warnings",
                "--ignore-errors",
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0 and not result.stdout.strip():
            raise RuntimeError((result.stderr or "yt-dlp failed").strip().splitlines()[-1])
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            video = json.loads(line)
            upload = video.get("upload_date") or ""
            published = parse_date(f"{upload[:4]}-{upload[4:6]}-{upload[6:8]}") if len(upload) == 8 else None
            items.append(
                make_item(
                    "youtube",
                    video.get("title") or "",
                    video.get("webpage_url") or "",
                    published,
                    primary=int(video.get("view_count") or 0),
                    secondary=int(video.get("comment_count") or 0),
                    label="views",
                    extra=video.get("channel") or "",
                )
            )
    return items


def collect_tiktok(entry: dict, cutoff: datetime, limit: int) -> list[dict]:
    key = read_credential("SCRAPECREATORS_API_KEY")
    items = []
    for query in entry["queries"]:
        data = http_json(
            "https://api.scrapecreators.com/v1/tiktok/search/keyword",
            params={"query": query, "sort_by": "relevance"},
            headers={"x-api-key": key},
            timeout=45,
        )
        entries = data.get("search_item_list") or data.get("data") or []
        for raw in entries[:limit]:
            video = raw.get("aweme_info", raw) if isinstance(raw, dict) else {}
            stats = video.get("statistics") if isinstance(video.get("statistics"), dict) else {}
            author = (video.get("author") or {}) if isinstance(video.get("author"), dict) else {}
            handle = author.get("unique_id") or ""
            url = (video.get("share_url") or "").split("?")[0]
            if not url and handle and video.get("aweme_id"):
                url = f"https://www.tiktok.com/@{handle}/video/{video['aweme_id']}"
            if not url:
                continue
            created = video.get("create_time")
            items.append(
                make_item(
                    "tiktok",
                    strip_html(video.get("desc") or "", 160),
                    url,
                    datetime.fromtimestamp(created, timezone.utc) if created else None,
                    primary=int(stats.get("digg_count") or 0),
                    secondary=int(stats.get("comment_count") or 0),
                    label="likes and comments",
                    extra=f"@{handle}" if handle else "",
                )
            )
    return items


def collect_instagram(entry: dict, cutoff: datetime, limit: int) -> list[dict]:
    key = read_credential("SCRAPECREATORS_API_KEY")
    items = []
    for query in entry["queries"]:
        data = http_json(
            "https://api.scrapecreators.com/v2/instagram/reels/search",
            params={"query": query},
            headers={"x-api-key": key},
            timeout=45,
        )
        reels = data.get("reels") or data.get("items") or data.get("data") or []
        for raw in reels[:limit]:
            media = raw.get("media", raw) if isinstance(raw, dict) else {}
            code = media.get("code") or media.get("shortcode")
            if not code:
                continue
            created = media.get("taken_at") or media.get("taken_at_timestamp")
            caption = media.get("caption")
            text = caption.get("text") if isinstance(caption, dict) else (caption or "")
            items.append(
                make_item(
                    "instagram",
                    strip_html(str(text), 160),
                    f"https://www.instagram.com/reel/{code}",
                    datetime.fromtimestamp(created, timezone.utc) if created else None,
                    primary=int(media.get("like_count") or 0),
                    secondary=int(media.get("comment_count") or 0),
                    label="likes and comments",
                )
            )
    return items


COLLECTORS = {
    "hackernews": collect_hackernews,
    "github": collect_github,
    "arxiv": collect_arxiv,
    "polymarket": collect_polymarket,
    "reddit": collect_reddit,
    "bluesky": collect_bluesky,
    "x": collect_x,
    "youtube": collect_youtube,
    "tiktok": collect_tiktok,
    "instagram": collect_instagram,
}
KEEP_UNDATED = {"polymarket"}


# --- plan ------------------------------------------------------------------

def normalize_entry(raw) -> dict:
    """Accept a string, a list of queries or the full object form."""
    if isinstance(raw, str):
        return {"queries": [raw], "communities": []}
    if isinstance(raw, list):
        return {"queries": [str(q) for q in raw if str(q).strip()], "communities": []}
    if isinstance(raw, dict):
        queries = raw.get("queries") or raw.get("query") or []
        if isinstance(queries, str):
            queries = [queries]
        communities = raw.get("communities") or raw.get("subreddits") or []
        if isinstance(communities, str):
            communities = [communities]
        return {
            "queries": [str(q) for q in queries if str(q).strip()],
            "communities": [str(c) for c in communities if str(c).strip()],
        }
    return {"queries": [], "communities": []}


def load_plan(path: Path) -> dict:
    plan = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(plan, dict) or not plan.get("topic"):
        raise ValueError("the plan needs at least a topic and a sources map")
    sources = plan.get("sources") or {}
    if not isinstance(sources, dict) or not sources:
        raise ValueError("the plan has no sources map")
    plan["sources"] = {
        name: normalize_entry(entry) for name, entry in sources.items() if name in COLLECTORS
    }
    return plan


# --- ranking ---------------------------------------------------------------

def score_items(items: list[dict]) -> None:
    """Give every item a 0 to 100 score, computed inside its own source.

    Cross source engagement numbers are not comparable: 300 upvotes and 300
    views mean different things. Ranking inside the source and comparing
    positions keeps the merged list honest, and an item with no engagement
    signal is ranked by recency instead.
    """
    by_source: dict[str, list[dict]] = {}
    for item in items:
        by_source.setdefault(item["source"], []).append(item)
    for group in by_source.values():
        graded = [i for i in group if i["primary"] is not None]
        ungraded = [i for i in group if i["primary"] is None]
        graded.sort(key=lambda i: ((i["primary"] or 0) + (i["secondary"] or 0)), reverse=True)
        ungraded.sort(key=lambda i: i["published"], reverse=True)
        for rank, item in enumerate(graded):
            item["score"] = round(100 * (len(graded) - rank) / max(len(graded), 1))
        for rank, item in enumerate(ungraded):
            # No signal to rank by, so these never outrank a measured item.
            item["score"] = round(60 * (len(ungraded) - rank) / max(len(ungraded), 1))


def dedupe(items: list[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for item in items:
        # Full normalized title, not a prefix: two different posts often share
        # their first words, and merging them would hide one of them entirely.
        key = norm_title(item["title"]) or item["id"]
        current = best.get(key)
        if current is None or item["score"] > current["score"]:
            best[key] = item
    return list(best.values())


def raw_signal(item: dict) -> str:
    if item["primary"] is None:
        return "unknown"
    if item["secondary"]:
        return f"{item['primary']}+{item['secondary']}"
    return str(item["primary"])


def age_days(item: dict) -> str:
    dt = parse_date(item["published"])
    return str((now() - dt).days) if dt else "?"


def compact_line(item: dict) -> str:
    def clean(value: str) -> str:
        return re.sub(r"\s+", " ", str(value).replace("|", "/")).strip()

    return "|".join(
        (
            item["id"],
            item["source"],
            str(item["score"]),
            raw_signal(item),
            age_days(item),
            clean(item["title"]),
        )
    )


# --- driver ----------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, help="path to the query plan JSON")
    parser.add_argument("--home", help="state home directory")
    parser.add_argument("--days", type=int, help="lookback window in days")
    parser.add_argument("--per-source", type=int, help="cap on items fetched per source")
    parser.add_argument("--max-items", type=int, help="cap on the whole shortlist")
    parser.add_argument("--only", help="comma separated source allowlist")
    parser.add_argument("--skip", help="comma separated source blocklist")
    parser.add_argument("--compact", action="store_true", help="print the compact shortlist")
    parser.add_argument("--json", action="store_true", help="print the full JSONL shortlist")
    args = parser.parse_args()

    home = state_home(args.home)
    config = load_config(home)
    try:
        plan = load_plan(Path(args.plan).expanduser())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: could not read the plan: {exc}", file=sys.stderr)
        return 2

    days = args.days or plan.get("days") or int(config.get("days", DEFAULT_DAYS))
    per_source = args.per_source or int(config.get("per_source", DEFAULT_PER_SOURCE))
    max_items = args.max_items or int(config.get("max_items", DEFAULT_MAX_ITEMS))
    cutoff = now() - timedelta(days=days)
    only = {s.strip() for s in (args.only or "").split(",") if s.strip()}
    skip = {s.strip() for s in (args.skip or "").split(",") if s.strip()}

    collected: list[dict] = []
    statuses: list[tuple[str, str, int, str]] = []
    for name, entry in plan["sources"].items():
        if only and name not in only:
            continue
        if name in skip:
            statuses.append((name, "off", 0, "skipped on the command line"))
            continue
        if not entry["queries"] and not entry["communities"]:
            statuses.append((name, "off", 0, "the plan gave it no query"))
            continue
        state, reason = source_status(name)
        if state == "off":
            statuses.append((name, "off", 0, reason))
            continue
        try:
            items = COLLECTORS[name](entry, cutoff, per_source)
        except RateLimited as exc:
            statuses.append((name, "degraded", 0, str(exc)))
            continue
        except Exception as exc:  # noqa: BLE001 - one broken source must not end the run
            statuses.append((name, "degraded", 0, f"{type(exc).__name__}: {exc}"))
            continue
        fresh = [i for i in items if in_window(i, cutoff, name in KEEP_UNDATED)]
        collected.extend(fresh)
        note = reason if state == "limited" else ""
        if not fresh and items:
            note = (note + "; " if note else "") + f"{len(items)} items, all outside the window"
        statuses.append((name, state, len(fresh), note))

    score_items(collected)
    shortlist = dedupe(collected)
    shortlist.sort(key=lambda i: (i["score"], i["published"]), reverse=True)
    total = len(shortlist)
    shortlist = shortlist[:max_items]

    home.mkdir(parents=True, exist_ok=True)
    (home / ".last_shortlist.jsonl").write_text(
        "".join(json.dumps(i, ensure_ascii=False) + "\n" for i in shortlist), encoding="utf-8"
    )
    (home / ".last_run.json").write_text(
        json.dumps(
            {
                "topic": plan["topic"],
                "days": days,
                "ran_at": now().isoformat(),
                "sources": [
                    {"source": n, "state": s, "items": c, "reason": r} for n, s, c, r in statuses
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if args.json:
        for item in shortlist:
            print(json.dumps(item, ensure_ascii=False))
    else:
        for item in shortlist:
            print(compact_line(item))

    for name, state, count, reason in statuses:
        suffix = f" ({reason})" if reason else ""
        print(f"source-status: {name} {state} items={count}{suffix}", file=sys.stderr)
    capped = f", capped from {total}" if total > len(shortlist) else ""
    degraded = sum(1 for _, state, _, _ in statuses if state == "degraded")
    print(
        f"summary: {len(shortlist)} items{capped} from "
        f"{sum(1 for _, s, _, _ in statuses if s in ('active', 'limited'))} sources, "
        f"{degraded} degraded (window {days}d, topic {plan['topic']!r})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
