#!/usr/bin/env python3
"""Run the whole digest in one command and print the message to deliver.

Only two steps need a model: ranking the candidates and translating them.
Everything else is deterministic, so it lives here instead of in an agent's
instructions. That matters for scheduled runs, where the orchestrating model
may be a small free one that skips steps or answers with a summary of itself.

The model is reached through a command, never an API of its own, so any
runner works:

    NEWS_DIGEST_MODEL_CMD="opencode-model-run --tier reason"
    NEWS_DIGEST_VALIDATE_CMD="opencode-model-run --tier light"

The command receives the prompt as its last argument and must print the
completion on stdout. Set the validate command to a different model from the
select command, or cross-model validation is only agreement with itself.

Stdout: the rendered brief, or nothing when there is no news worth sending.
Exit codes: 0 ok, 1 the model produced nothing usable, 2 broken state.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_feeds import compact_line, load_structured, state_home  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
SELECTION_LINE = re.compile(r"^\s*(?:[-*]|\d+[.)])?\s*([0-9a-f]{12})\s*\|(.+)$")
DROP_LINE = re.compile(r"^\s*DROP\s+([0-9a-f]{12})\b(.*)$", re.IGNORECASE)

SELECT_PROMPT = """You are curating a personal news digest for one reader.

Write every title and reason in {language}. The sources are in many languages;
translate whatever you pick. Never leave the original headline in, not even in
parentheses. Proper nouns, product names and acronyms stay as they are.

Pick at most {max_items} items in total and at most {max_per_section} per section.
Fewer is better than padding. Drop a story when it is saturated across outlets,
when it is a launch announcement with no substance, or when it is a rewrite with
no new fact. Rank by profile match first, source tier second, novelty third.

When two candidates are equally relevant, take the one from a source the reader
has not seen recently. These sources have gone the longest without an item:
{stale_sources}

In politics, keep what changes a rule, a tax, an interest rate, a contract or
the technology sector. Leave out electoral horse race and backroom manoeuvring.

A candidate's section comes from the feed that carried it, and some feeds are
broader than the section they sit in. Drop any candidate that does not match
what its section is for. You cannot move an item to another section, so a
misfit is a drop, never a reshuffle. What each section is for:
{section_focus}

For each item you keep:
- title: at most 60 characters, carrying the news on its own, no clickbait.
- reason: the concrete consequence for this reader, at most 12 words. If you
  cannot name one, drop the item instead of writing filler.

Never use an em dash, a hyphen as punctuation, or an emoji.

Output one line per selected item, best first, and nothing else. No preamble,
no headers, no code fence, no urls:

<id>|<title>|<reason>

Reader profile:
{profile}

Candidates, one per line as id|section|tier|source|title:
{shortlist}
"""

VALIDATE_PROMPT = """You are reviewing a news digest selection before it is sent.

Check for: the same story selected twice under different headlines; stories so
saturated across outlets that the reader has seen them everywhere; reasons that
name no concrete consequence; items whose title or reason is not in {language},
or whose translation lost the meaning; items that do not match what their
section is for, listed here:
{section_focus}

Do not rewrite anything and do not comment. Output one line per item that should
be removed, and nothing else:

DROP <id> <short reason>

If every item should stay, output exactly: PASS

Selection, as id|title|reason:
{selection}

Candidates it came from, as id|section|tier|source|title:
{shortlist}
"""


def run_script(name: str, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


RAN_MODEL = re.compile(r"\bran\s+(\S+)")


def run_model(command: str, prompt: str, label: str, extra: list[str] | None = None) -> tuple[str, str]:
    """Run the model command and return its output plus the model it used.

    The model name is read back from the runner's own log line, which is what
    lets the validation pass exclude whatever the selection pass just used.
    A runner that says nothing simply yields an empty name, and the caller
    degrades to whatever its tier offers.
    """
    parts = shlex.split(command)
    if not parts:
        return "", ""
    try:
        proc = subprocess.run([*parts, *(extra or []), prompt], capture_output=True, text=True)
    except OSError as exc:
        print(f"{label}: could not run {parts[0]}: {exc}", file=sys.stderr)
        return "", ""
    used = ""
    for line in proc.stderr.splitlines():
        match = RAN_MODEL.search(line)
        if match:
            used = match.group(1)
    if proc.stderr.strip():
        print(f"{label}: {proc.stderr.strip().splitlines()[-1][:200]}", file=sys.stderr)
    if proc.returncode != 0:
        print(f"{label}: command failed rc={proc.returncode}", file=sys.stderr)
        return "", used
    return proc.stdout, used


def section_focus(home: Path) -> str:
    """What each section is actually about, from the `focus` line in sources.yaml.

    A section carries only a name otherwise, and a name is not an intent. The
    section of an item comes from its feed, so a broad feed drags in stories
    that technically belong to it and clearly do not belong in the digest:
    a construction industry feed under a section meant for home financing
    will offer workplace safety rules. The focus line is what lets the model
    drop those instead of filing them.
    """
    path = home / "sources.yaml"
    if not path.exists():
        return ""
    try:
        data = load_structured(path) or {}
    except Exception:  # noqa: BLE001 - the fetch step already reports parse errors
        return ""
    lines = []
    for section in data.get("sections") or []:
        focus = (section.get("focus") or "").strip()
        if focus:
            lines.append(f"- {section.get('name', '?')}: {focus}")
    return "\n".join(lines)


def stale_sources(home: Path, limit: int = 8) -> str:
    """Sources whose items have not been picked for the longest, oldest first.

    Fed to the selection prompt so the anti-bubble rule has something concrete
    to act on. Without it, asking a model for variety is asking for a guess.
    """
    path = home / "stats.json"
    if not path.exists():
        return "(no history yet)"
    try:
        feeds = json.loads(path.read_text(encoding="utf-8")).get("feeds", {})
    except json.JSONDecodeError:
        return "(no history yet)"
    ranked = sorted(feeds.items(), key=lambda kv: (kv[1].get("last_shown") or "0000-00-00"))
    names = [key.split("/", 1)[-1] for key, row in ranked if row.get("offered")][:limit]
    return ", ".join(names) if names else "(no history yet)"


def parse_selection(text: str) -> list[str]:
    """Keep the lines that look like selections, whatever else the model said."""
    lines = []
    for raw in text.splitlines():
        match = SELECTION_LINE.match(raw)
        if match:
            lines.append(f"{match.group(1)}|{match.group(2).strip()}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", help="state home directory")
    parser.add_argument("--dry-run", action="store_true", help="do not mark items as seen")
    parser.add_argument("--no-validate", action="store_true", help="skip the validation pass")
    parser.add_argument(
        "--reuse-shortlist",
        action="store_true",
        help="skip collection and reuse the last shortlist, so two models can be compared "
        "on identical candidates",
    )
    args = parser.parse_args()

    home = state_home(args.home)
    config = {}
    config_path = home / "config.yaml"
    if config_path.exists():
        try:
            config = load_structured(config_path) or {}
        except Exception as exc:  # noqa: BLE001 - report and continue with defaults
            print(f"warning: could not parse {config_path}: {exc}", file=sys.stderr)

    home_args = ["--home", str(home)] if args.home else []
    if args.reuse_shortlist:
        path = home / ".last_shortlist.jsonl"
        if not path.exists():
            print(f"error: {path} not found; run without --reuse-shortlist first", file=sys.stderr)
            return 2
        shortlist = "\n".join(
            compact_line(json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        print(f"reusing {len(shortlist.splitlines())} candidates from the last run", file=sys.stderr)
    else:
        code, shortlist, stderr = run_script("fetch_feeds.py", "--compact", *home_args)
        for line in stderr.strip().splitlines():
            print(line, file=sys.stderr)
        if code != 0:
            return 2
    shortlist = shortlist.strip()
    if not shortlist:
        print("nothing new in this window", file=sys.stderr)
        return 0

    focus = section_focus(home)
    profile = ""
    profile_path = home / "profile.md"
    if profile_path.exists():
        profile = profile_path.read_text(encoding="utf-8").strip()

    select_cmd = os.environ.get("NEWS_DIGEST_MODEL_CMD", "opencode-model-run --tier reason")
    language = str(config.get("digest_language", "en"))
    prompt = SELECT_PROMPT.format(
        language=language,
        max_items=int(config.get("max_items", 8)),
        max_per_section=int(config.get("max_per_section", 2)),
        stale_sources=stale_sources(home),
        section_focus=focus or "(not declared)",
        profile=profile or "(no profile yet)",
        shortlist=shortlist,
    )
    raw, select_model = run_model(select_cmd, prompt, "select")
    selection = parse_selection(raw)
    if not selection:
        print("error: the model returned no usable selection lines", file=sys.stderr)
        return 1

    validate_cmd = os.environ.get("NEWS_DIGEST_VALIDATE_CMD", "")
    if validate_cmd and config.get("validate", True) and not args.no_validate:
        # Excluding the model that just selected is what makes this a second
        # opinion. Without it, the two passes can land on the same model and
        # the check degrades into the drafter agreeing with itself.
        extra = ["--exclude", select_model] if select_model else []
        verdict, verify_model = run_model(
            validate_cmd,
            VALIDATE_PROMPT.format(
                language=language,
                section_focus=focus or "(not declared)",
                selection="\n".join(selection),
                shortlist=shortlist,
            ),
            "validate",
            extra,
        )
        if select_model and verify_model and select_model == verify_model:
            print(
                f"warning: both passes ran on {select_model}; this was not cross-model validation",
                file=sys.stderr,
            )
        dropped = set()
        for line in verdict.splitlines():
            match = DROP_LINE.match(line)
            if match:
                dropped.add(match.group(1))
                print(f"validator dropped {match.group(1)}:{match.group(2)[:80]}", file=sys.stderr)
        kept = [line for line in selection if line.split("|", 1)[0] not in dropped]
        if kept:
            selection = kept
        else:
            print("validator dropped everything; keeping the original selection", file=sys.stderr)
    elif not validate_cmd:
        print("no NEWS_DIGEST_VALIDATE_CMD set: this run was not validated by a second model", file=sys.stderr)

    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "render_digest.py"), "--format", "brief", *home_args],
        input="\n".join(selection) + "\n",
        capture_output=True,
        text=True,
    )
    for line in proc.stderr.strip().splitlines():
        print(line, file=sys.stderr)
    if proc.returncode != 0 or not proc.stdout.strip():
        return 1

    if not args.dry_run:
        code, out, stderr = run_script("state.py", *home_args, "mark-shown", "--from-last")
        print((out + stderr).strip(), file=sys.stderr)

    sys.stdout.write(proc.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
