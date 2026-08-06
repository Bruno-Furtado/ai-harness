#!/usr/bin/env python3
"""Source registry, credential resolution and shared helpers for topic-research.

Also the module the other scripts import from, the same way render_digest.py
imports from fetch_feeds.py in the news-digest skill. Stdlib only.

Credentials are never printed, never passed on a command line and never
written inside this skill directory. `status` reports configured or missing
and nothing else.

Stdout: the source status table (with `status`).
Stderr: warnings.
Exit codes: 0 ok, 2 bad usage or unwritable credential file.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

USER_AGENT = "topic-research/0.1 (personal research)"
TRACKING_PARAMS = re.compile(r"^(utm_|fbclid$|gclid$|ocid$|mc_cid$|mc_eid$)")
KEY_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")


def state_home(arg: str | None = None) -> Path:
    if arg:
        return Path(arg).expanduser()
    env = os.environ.get("TOPIC_RESEARCH_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".local" / "share" / "topic-research"


def config_home() -> Path:
    env = os.environ.get("TOPIC_RESEARCH_CONFIG")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".config" / "topic-research"


# --- credentials -----------------------------------------------------------
# Order: process env, then the credentials file, then the macOS keychain.
# The env wins so a single run can override without touching disk, and the
# keychain comes last because it is the only lookup that can block on a
# system prompt.

def _credentials_file() -> Path:
    return config_home() / "credentials.env"


def _from_file(key: str) -> str | None:
    path = _credentials_file()
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"warning: could not read {path}: {exc}", file=sys.stderr)
        return None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name.strip() == key:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            return value or None
    return None


def _from_keychain(key: str) -> str | None:
    if sys.platform != "darwin" or not shutil.which("security"):
        return None
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", f"topic-research-{key}", "-w"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def read_credential(key: str) -> str | None:
    return os.environ.get(key) or _from_file(key) or _from_keychain(key)


def write_credential(key: str, value: str) -> Path:
    """Append a credential to the credentials file, with 0600 permissions."""
    path = _credentials_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if path.exists():
        lines = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if not line.strip().startswith(f"{key}=")
        ]
    lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return path


# --- source registry -------------------------------------------------------
# `needs` is what makes the source work at all. `upgrades` is what makes an
# already working source better, which today is only Reddit: the public feed
# carries no score, the API does.

SOURCES: dict[str, dict] = {
    "hackernews": {
        "tier": "open",
        "needs": [],
        "engagement": "points and comments",
        "verified": True,
        "note": "Algolia search API, no credential, generous limits.",
    },
    "github": {
        "tier": "open",
        "needs": [],
        "engagement": "stars",
        "verified": True,
        "note": "Unauthenticated REST search, roughly 10 requests per minute.",
    },
    "arxiv": {
        "tier": "open",
        "needs": [],
        "engagement": "none, ranked by recency",
        "verified": True,
        "note": "Atom API over https, one request every three seconds.",
    },
    "polymarket": {
        "tier": "open",
        "needs": [],
        "engagement": "volume in dollars",
        "verified": True,
        "note": "Gamma public-search, money committed as the signal.",
    },
    "reddit": {
        "tier": "open",
        "needs": [],
        "upgrades": ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"],
        "engagement": "score and comments with the API, none without",
        "verified": True,
        "note": "Public feeds rate limit hard and carry no score. A free script app fixes both.",
    },
    "bluesky": {
        "tier": "credential",
        "needs": ["BSKY_HANDLE", "BSKY_APP_PASSWORD"],
        "engagement": "likes, reposts and replies",
        "verified": False,
        "note": "App password, not the account password. Public search is refused.",
    },
    "x": {
        "tier": "credential",
        "needs": ["XAI_API_KEY", "XAI_MODEL"],
        "engagement": "likes and reposts, as reported by the model",
        "verified": False,
        "note": "Model mediated. XAI_MODEL is your choice: this repository pins no model.",
    },
    "youtube": {
        "tier": "binary",
        "needs": ["yt-dlp"],
        "engagement": "views",
        "verified": False,
        "note": "Search only, no transcript download, no credential.",
    },
    "tiktok": {
        "tier": "credential",
        "needs": ["SCRAPECREATORS_API_KEY"],
        "engagement": "likes and comments",
        "verified": False,
        "note": "ScrapeCreators keyword search.",
    },
    "instagram": {
        "tier": "credential",
        "needs": ["SCRAPECREATORS_API_KEY"],
        "engagement": "likes and comments",
        "verified": False,
        "note": "ScrapeCreators reels search.",
    },
}

OPEN_SOURCES = [name for name, spec in SOURCES.items() if spec["tier"] == "open"]


def source_status(name: str) -> tuple[str, str]:
    """Return (state, reason) for one source, without touching the network."""
    spec = SOURCES[name]
    missing = []
    for need in spec["needs"]:
        if spec["tier"] == "binary":
            if not shutil.which(need):
                missing.append(need)
        elif not read_credential(need):
            missing.append(need)
    if missing:
        what = "binary" if spec["tier"] == "binary" else "credential"
        return "off", f"missing {what}: {', '.join(missing)}"
    upgrades = spec.get("upgrades") or []
    if upgrades and not all(read_credential(key) for key in upgrades):
        return "limited", f"no {', '.join(upgrades)}, falling back to the public feed"
    return "active", ""


def enabled_sources() -> list[str]:
    return [name for name in SOURCES if source_status(name)[0] != "off"]


# --- shared helpers --------------------------------------------------------
# Copied from the news-digest skill (scripts/fetch_feeds.py), keeping the same
# names. Skills are symlinked one by one, so a directory has to stand alone:
# a shared library between skills would break that.

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
                    entry = {key: _value_or_block(value, indent)}
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


def load_config(home: Path) -> dict:
    path = home / "config.yaml"
    if not path.exists():
        return {}
    try:
        return load_structured(path) or {}
    except Exception as exc:  # noqa: BLE001 - report and continue with defaults
        print(f"warning: could not parse {path}: {exc}", file=sys.stderr)
        return {}


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
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())


def hash12(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def strip_html(text: str, limit: int = 200) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[: limit - 1].rstrip() + "…" if len(text) > limit else text


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


def slugify(text: str, limit: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (slug[:limit].rstrip("-") or "topic")


# --- http ------------------------------------------------------------------

class RateLimited(Exception):
    """The host answered 429. The caller reports the source as degraded."""


def http_get(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 20,
    retries: int = 2,
    backoff: float = 2.0,
    data: bytes | None = None,
) -> bytes:
    """GET (or POST when data is given) with backoff. Raises on failure.

    A 429 raises RateLimited after the retries are spent, so the caller can
    report the source as degraded instead of pretending the window was empty.
    """
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    request_headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"}
    request_headers.update(headers or {})
    last_error: Exception = RuntimeError("no attempt was made")
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, headers=request_headers, data=data)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read()
            if payload[:2] == b"\x1f\x8b":
                payload = gzip.decompress(payload)
            return payload
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 429:
                last_error = RateLimited(f"{url.split('?')[0]} answered 429")
                wait = _retry_after(exc, backoff, attempt)
            elif exc.code in (500, 502, 503, 504):
                wait = backoff * (2**attempt)
            else:
                raise
        except (urllib.error.URLError, TimeoutError, OSError, gzip.BadGzipFile) as exc:
            last_error = exc
            wait = backoff * (2**attempt)
        if attempt < retries:
            time.sleep(wait)
    raise last_error


def _retry_after(exc: urllib.error.HTTPError, backoff: float, attempt: int) -> float:
    raw = exc.headers.get("Retry-After") if exc.headers else None
    try:
        return min(float(raw), 30.0) if raw else backoff * (2**attempt)
    except (TypeError, ValueError):
        return backoff * (2**attempt)


def http_json(url: str, **kwargs) -> dict | list:
    return json.loads(http_get(url, **kwargs).decode("utf-8", "replace"))


# --- cli -------------------------------------------------------------------

def cmd_status(as_json: bool) -> int:
    rows = []
    for name, spec in SOURCES.items():
        state, reason = source_status(name)
        rows.append(
            {
                "source": name,
                "tier": spec["tier"],
                "state": state,
                "reason": reason,
                "engagement": spec["engagement"],
                "verified": spec["verified"],
            }
        )
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    width = max(len(row["source"]) for row in rows)
    for row in rows:
        flag = "" if row["verified"] else "  (transport not verified yet)"
        suffix = f": {row['reason']}" if row["reason"] else ""
        print(f"{row['source']:<{width}}  {row['state']:<7}  {row['tier']:<10}{suffix}{flag}")
    sys.stdout.flush()
    active = sum(1 for row in rows if row["state"] == "active")
    limited = sum(1 for row in rows if row["state"] == "limited")
    print(
        f"\n{active} active, {limited} limited, {len(rows) - active - limited} off. "
        f"Credentials: {_credentials_file()}",
        file=sys.stderr,
    )
    return 0


def cmd_set_credential(key: str) -> int:
    if not KEY_NAME.match(key):
        print(f"error: {key!r} is not a credential name (expected UPPER_SNAKE_CASE)", file=sys.stderr)
        return 2
    if sys.stdin.isatty():
        print("error: pipe the value on stdin, never as an argument", file=sys.stderr)
        print("       example: printf %s \"$VALUE\" | sources.py set-credential XAI_API_KEY", file=sys.stderr)
        return 2
    value = sys.stdin.read().strip()
    if not value:
        print("error: empty value on stdin", file=sys.stderr)
        return 2
    try:
        path = write_credential(key, value)
    except OSError as exc:
        print(f"error: could not write the credentials file: {exc}", file=sys.stderr)
        return 2
    print(f"stored {key} in {path} (mode 600, value not echoed)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status", help="report every source as active, limited or off")
    status.add_argument("--json", action="store_true")
    setter = sub.add_parser("set-credential", help="store one credential, value read from stdin")
    setter.add_argument("key")
    args = parser.parse_args()

    if args.command == "status":
        return cmd_status(args.json)
    return cmd_set_credential(args.key)


if __name__ == "__main__":
    sys.exit(main())
