#!/usr/bin/env python3
"""Collect the day's Claude Code and OpenCode session transcripts for the dream skill.

Reads Claude Code JSONL transcripts and the OpenCode SQLite database, extracts
user and assistant text, and writes one compact extract per session under the
state home. Deterministic: no model involved.

Usage: collect.py [--since EPOCH] [--hours H] [--max-chars N]

Window resolution order: --since, then --hours, then state.json last_run, then
the last 24 hours. Each run wipes the transcripts directory first: extracts are
temporary working files, not an archive.

Sessions with no user line are skipped: those are unattended scheduled runs.
A missing or unreadable OpenCode database is reported, never fatal, so the
Claude Code side of the window still gets collected.

Environment: DREAM_HOME for the state home, DREAM_OPENCODE_DB to point at a
different OpenCode database.
"""

import argparse
import glob
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

MAX_LINE = 500
MAX_SESSION = 12000
MAX_TOTAL = 60000

CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
OPENCODE_DB = Path(
    os.environ.get("DREAM_OPENCODE_DB") or Path.home() / ".local" / "share" / "opencode" / "opencode.db"
)

TAG_BLOCKS = [
    re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL),
    re.compile(r"<local-command-stdout>.*?</local-command-stdout>", re.DOTALL),
    re.compile(r"<local-command-stderr>.*?</local-command-stderr>", re.DOTALL),
    re.compile(r"<command-message>.*?</command-message>", re.DOTALL),
    re.compile(r"<command-name>.*?</command-name>", re.DOTALL),
    re.compile(r"<command-args>.*?</command-args>", re.DOTALL),
]


def state_home():
    return Path(os.environ.get("DREAM_HOME") or Path.home() / ".local" / "share" / "dream")


def load_state(home):
    try:
        return json.loads((home / "state.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def clean_transcripts(home):
    tdir = home / "transcripts"
    tdir.mkdir(parents=True, exist_ok=True)
    for f in tdir.iterdir():
        if f.is_file():
            f.unlink()


def strip_noise(text):
    for pat in TAG_BLOCKS:
        text = pat.sub("", text)
    return text.strip()


def clip(text):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_LINE:
        text = text[:MAX_LINE].rstrip() + " [...]"
    return text


def claude_sessions(since):
    """Yield (path, mtime) for JSONL transcripts touched since the window start."""
    for path in glob.glob(str(CLAUDE_PROJECTS / "*" / "*.jsonl")):
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if mtime >= since:
            yield Path(path), mtime


def parse_claude(path, since):
    """Extract (role, timestamp, text) lines from a Claude Code transcript."""
    lines = []
    # The directory name is the working directory with every separator turned
    # into a hyphen, so it cannot be reversed: a project named bruno-furtado
    # looks exactly like two path segments. Each entry carries the real cwd.
    project = path.parent.name
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if entry.get("isSidechain"):
                continue
            if entry.get("cwd"):
                project = entry["cwd"]
            etype = entry.get("type")
            if etype not in ("user", "assistant"):
                continue
            ts = entry.get("timestamp", "")
            try:
                epoch = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
            except (ValueError, AttributeError):
                continue
            if epoch < since:
                continue
            content = (entry.get("message") or {}).get("content")
            texts = []
            if isinstance(content, str):
                texts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        texts.append(block.get("text", ""))
            text = strip_noise(" ".join(texts))
            if text:
                lines.append(("user" if etype == "user" else "assistant", epoch, text))
    return project, lines


def opencode_sessions(since):
    """Extract top-level OpenCode sessions with text parts since the window start."""
    if not OPENCODE_DB.exists():
        return
    db = sqlite3.connect(f"file:{OPENCODE_DB}?mode=ro", uri=True)
    try:
        rows = db.execute(
            "SELECT id, title, directory, time_created, time_updated FROM session"
            " WHERE time_updated >= ? AND parent_id IS NULL ORDER BY time_updated",
            (int(since * 1000),),
        ).fetchall()
        for sid, title, directory, created, updated in rows:
            lines = []
            msg_rows = db.execute(
                "SELECT id, json_extract(data, '$.role'), time_created FROM message"
                " WHERE session_id = ? ORDER BY time_created",
                (sid,),
            ).fetchall()
            for mid, role, mcreated in msg_rows:
                if role not in ("user", "assistant"):
                    continue
                texts = [
                    r[0]
                    for r in db.execute(
                        "SELECT json_extract(data, '$.text') FROM part"
                        " WHERE message_id = ? AND json_extract(data, '$.type') = 'text'"
                        " ORDER BY time_created",
                        (mid,),
                    ).fetchall()
                    if r[0]
                ]
                text = strip_noise(" ".join(texts))
                if text:
                    lines.append((role, mcreated / 1000, text))
            if lines:
                yield sid, title or "", directory or "", created / 1000, lines
    finally:
        db.close()


def fit_budget(lines, cap):
    """Keep every user line when possible; drop oldest assistant lines first."""
    total = sum(len(t) for _, _, t in lines)
    if total <= cap:
        return lines, 0
    kept = list(lines)
    omitted = 0
    for role_to_drop in ("assistant", "user"):
        i = 0
        while total > cap and i < len(kept):
            if kept[i] is not None and kept[i][0] == role_to_drop:
                total -= len(kept[i][2])
                omitted += 1
                kept[i] = None
            i += 1
        if total <= cap:
            break
    return [l for l in kept if l], omitted


def write_extract(tdir, label, header, lines):
    lines, omitted = fit_budget([(r, e, clip(t)) for r, e, t in lines], MAX_SESSION)
    out = ["# " + header, ""]
    counts = {"user": 0, "assistant": 0}
    for role, epoch, text in lines:
        counts[role] += 1
        tag = ("u" if role == "user" else "a") + f"{counts[role]:03d}"
        when = datetime.fromtimestamp(epoch).strftime("%H:%M")
        out.append(f"[{label}:{tag}] ({when}) {text}")
    if omitted:
        out.append(f"[{label}:...] {omitted} older line(s) omitted by the size budget")
    body = "\n".join(out) + "\n"
    (tdir / f"{label}.md").write_text(body, encoding="utf-8")
    return len(body), counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=float, default=None)
    ap.add_argument("--hours", type=float, default=None)
    ap.add_argument("--max-chars", type=int, default=MAX_TOTAL)
    args = ap.parse_args()

    home = state_home()
    home.mkdir(parents=True, exist_ok=True)
    state = load_state(home)

    now = time.time()
    if args.since is not None:
        since = args.since
    elif args.hours is not None:
        since = now - args.hours * 3600
    elif state.get("last_run"):
        since = state["last_run"]
    else:
        since = now - 24 * 3600

    clean_transcripts(home)
    tdir = home / "transcripts"

    def write_meta(sessions):
        # Always written, even with nothing to read, because proposals.py takes
        # last_run from window_end. Without it a later save would stamp the
        # current time and skip over a window nobody looked at.
        meta = {
            "window_start": since,
            "window_end": now,
            "sessions": [
                {"label": f"S{i}", "source": s["source"], "id": s["id"], "where": s["where"]}
                for i, s in enumerate(sessions, 1)
            ],
        }
        (tdir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    sessions = []
    for path, _mtime in sorted(claude_sessions(since), key=lambda x: x[1]):
        project, lines = parse_claude(path, since)
        if lines:
            start = datetime.fromtimestamp(lines[0][1]).strftime("%Y-%m-%d %H:%M")
            sessions.append({
                "source": "claude-code",
                "id": path.stem,
                "where": project,
                "start": start,
                "lines": lines,
            })
    # A broken or moved OpenCode database must not cost us the Claude Code
    # sessions, which have nothing to do with it.
    opencode_error = None
    try:
        opencode_rows = list(opencode_sessions(since))
    except sqlite3.Error as exc:
        opencode_rows, opencode_error = [], str(exc)
        print(f"warning: could not read the OpenCode database: {exc}", file=sys.stderr)
    for sid, title, directory, created, lines in opencode_rows:
        start = datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M")
        sessions.append({
            "source": "opencode",
            "id": sid,
            "where": f"{directory} | {title}".strip(" |"),
            "start": start,
            "lines": lines,
        })

    for s in sessions:
        s["user_lines"] = sum(1 for role, _, _ in s["lines"] if role == "user")
    # A session with no user line is a scheduled job talking to itself: nothing
    # to learn, only budget to spend.
    with_user = [s for s in sessions if s["user_lines"]]
    unattended = len(sessions) - len(with_user)
    sessions = sorted(with_user, key=lambda s: s["start"])
    if not sessions:
        write_meta([])
        note = f"No session with user activity ({unattended} unattended run(s) skipped)."
        if opencode_error:
            note += f"\nOpenCode sessions could not be read: {opencode_error}"
        (tdir / "INDEX.md").write_text(
            f"# Dream extracts | window {datetime.fromtimestamp(since):%Y-%m-%d %H:%M} -> "
            f"{datetime.fromtimestamp(now):%Y-%m-%d %H:%M}\n\n{note}\n",
            encoding="utf-8",
        )
        print("NO_SESSIONS")
        return 0

    # Spend the budget on real conversations first, newest first inside each
    # group, then report chronologically. Cutting in start order threw today's
    # conversation away to keep a scheduled job from yesterday: an unattended
    # run sends one prompt and never answers, so it teaches nothing, while a
    # session the user replied in is where corrections and preferences live.
    total = 0
    written = {}
    order = sorted(
        range(len(sessions)),
        key=lambda i: (sessions[i]["user_lines"] > 1, sessions[i]["start"]),
        reverse=True,
    )
    for i in order:
        s = sessions[i]
        if total >= args.max_chars:
            continue
        label = f"S{i + 1}"
        header = f"{s['source']} session {s['id']} | {s['where']} | started {s['start']}"
        chars, counts = write_extract(tdir, label, header, s["lines"])
        total += chars
        written[i] = counts

    index = [
        f"# Dream extracts | window {datetime.fromtimestamp(since):%Y-%m-%d %H:%M} -> "
        f"{datetime.fromtimestamp(now):%Y-%m-%d %H:%M}",
        "",
    ]
    for i, s in enumerate(sessions):
        label = f"S{i + 1}"
        head = f"- {label}: {s['source']} | {s['where']} | {s['start']} | "
        if i in written:
            counts = written[i]
            # Flagged so the reader weighs the evidence: nobody replied in
            # there, so it cannot show a correction or a stated preference.
            solo = ", single prompt with no follow-up" if s["user_lines"] < 2 else ""
            index.append(
                head + f"{counts['user']} user, {counts['assistant']} assistant lines{solo} | {label}.md"
            )
        else:
            index.append(head + "skipped: global budget spent")
    if unattended:
        index.append("")
        index.append(f"{unattended} session(s) with no user line skipped: unattended runs.")
    if opencode_error:
        index.append("")
        index.append(f"OpenCode sessions are missing from this window: {opencode_error}")

    (tdir / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    write_meta(sessions)
    print(
        f"OK sessions={len(sessions)} extracted={len(written)} skipped_unattended={unattended} "
        f"chars={total} -> {tdir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
