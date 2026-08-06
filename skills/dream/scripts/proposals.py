#!/usr/bin/env python3
"""Manage dream proposals: the numbered list the user approves or dismisses.

Subcommands:
  save                     Read proposal lines on stdin, store pending, auto-apply
                           only typo/index fixes, print the numbered list.
  list                     Print pending proposals.
  applied 1,3 | all        Mark proposals applied (the agent already edited files).
  dismiss 1,3 | all        Mark proposals dismissed.
  archive-file <name.md>   Move a memory file into archive/ and drop its index
                           line. Only for proposals the user approved.
  status                   Print counts and the last run time.

Proposal line format (one per line on stdin):
  type|class|files|summary|evidence|quote[|fix]

  type:      new-fact | preference | correction | outdated | duplicate | typo | index
  class:     auto | review
  files:     memory file names, comma separated (new files get their proposed name)
  evidence:  citation id from the extracts, like S2:u04
  quote:     short verbatim quote; pipe characters are kept as part of the quote
  fix:       only for auto typo/index: file.md::OLD=>NEW (exact, unique match)

Only typo and index may use class auto. Everything else waits for the user.
Memory files are never deleted: archive-file moves them to archive/.

The contract above is English because the repository is written in English. What
the user reads (summaries, quotes, the numbered report) stays in their language.
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

TYPES = {"new-fact", "preference", "correction", "outdated", "duplicate", "typo", "index"}
AUTO_TYPES = {"typo", "index"}

# The first version of this skill used Portuguese type and class names, and they
# are still sitting in pending.json. Accept them on read so an upgrade does not
# invalidate proposals the user has not answered yet.
TYPE_ALIASES = {
    "fato-novo": "new-fact",
    "preferencia": "preference",
    "preferência": "preference",
    "correcao": "correction",
    "correção": "correction",
    "desatualizada": "outdated",
    "duplicada": "duplicate",
    "typo": "typo",
    "indice": "index",
    "índice": "index",
}
CLASS_ALIASES = {"revisao": "review", "revisão": "review"}

# Shown to the user, so Portuguese with proper accents.
LABELS = {
    "new-fact": "fato novo",
    "preference": "preferência",
    "correction": "correção",
    "outdated": "desatualizada",
    "duplicate": "duplicada",
    "typo": "typo",
    "index": "índice",
}

INDEX_FILE = "MEMORY.md"
RUNS_TO_KEEP = 30

# A stated preference or a correction has to come from the user. An assistant
# line is the agent quoting itself, which proves nothing about what the user
# wants, so the rule is enforced here and not only in the skill prose.
USER_LINE = re.compile(r":u\d+")
NEEDS_USER_LINE = {"preference", "correction"}


def state_home():
    return Path(os.environ.get("DREAM_HOME") or Path.home() / ".local" / "share" / "dream")


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def label(item):
    """Display label, resolving the Portuguese type names of older pending items."""
    tipo = TYPE_ALIASES.get(item["type"], item["type"])
    return LABELS.get(tipo, tipo)


def parse_line(line):
    """Split one proposal line without ever losing a field silently.

    The first five fields cannot contain a pipe. Everything after them is the
    quote, except for an auto proposal, where the text after the last pipe is
    the fix. Splitting greedily on every pipe, as the first version did, either
    ate the fix or truncated the quote.
    """
    parts = line.split("|", 5)
    if len(parts) < 6:
        return None, "fewer than 6 fields"
    tipo, cls, files, summary, evidence, tail = (p.strip() for p in parts)

    tipo = TYPE_ALIASES.get(tipo, tipo)
    cls = CLASS_ALIASES.get(cls, cls)
    if tipo not in TYPES:
        return None, f"unknown type: {tipo}"
    if cls not in ("auto", "review"):
        return None, f"unknown class: {cls}"
    if cls == "auto" and tipo not in AUTO_TYPES:
        return None, "class auto is only valid for typo or index"

    if cls == "auto":
        quote, sep, fix = tail.rpartition("|")
        if not sep:
            return None, "auto without a fix field"
        quote, fix = quote.strip(), fix.strip()
    else:
        quote, fix = tail.strip(), ""

    if not evidence or not quote:
        return None, "evidence and quote are required"
    if tipo in NEEDS_USER_LINE and not USER_LINE.search(evidence):
        return None, f"{tipo} must cite a user line (SN:uNN), got {evidence}"
    return {
        "type": tipo,
        "cls": cls,
        "files": [f.strip() for f in files.split(",") if f.strip()],
        "summary": summary,
        "evidence": evidence,
        "quote": quote,
        "fix": fix,
        "status": "pending",
        "note": "",
    }, None


def safe_memory_path(home, name, allow_index=False):
    """Resolve a memory file name, refusing traversal and, by default, the index."""
    name = os.path.basename(name)
    if not name.endswith(".md") or name == ".md":
        return None
    if name == INDEX_FILE and not allow_index:
        return None
    return home / "memory" / name


def auto_apply(home, item):
    """Apply a typo/index fix: exact, unique string replacement. Never raises."""
    fix = item["fix"]
    fname, sep, pair = fix.partition("::")
    if not sep:
        item["note"] = "fix malformado, sem `::`; ficou pendente"
        return False
    old, sep, new = pair.partition("=>")
    if not sep:
        item["note"] = "fix malformado, sem `=>`; ficou pendente"
        return False
    old, new = old.strip(), new.strip()
    if not old:
        item["note"] = "fix sem trecho a substituir; ficou pendente"
        return False
    # An index fix is a fix to MEMORY.md, so the index is reachable here.
    path = safe_memory_path(home, fname, allow_index=item["type"] == "index")
    if path is None or not path.exists():
        item["note"] = f"arquivo {fname} não encontrado; ficou pendente"
        return False
    content = path.read_text(encoding="utf-8")
    if content.count(old) != 1:
        item["note"] = "trecho do fix não aparece exatamente uma vez; ficou pendente"
        return False
    path.write_text(content.replace(old, new, 1), encoding="utf-8")
    item["note"] = "aplicada automaticamente"
    return True


def render(items, title):
    out = [title, ""]
    for it in items:
        files = ", ".join(it["files"]) or "-"
        out.append(f"{it['n']}. [{label(it)}] {it['summary']} ({files})")
        out.append(f"   Evidência {it['evidence']}: \"{it['quote']}\"")
        if it.get("note") and it["status"] == "pending" and it["cls"] == "auto":
            out.append(f"   Nota: {it['note']}")
    return "\n".join(out)


def rotate_runs(home):
    runs = sorted((home / "runs").glob("*.md"))
    for old in runs[:-RUNS_TO_KEEP]:
        old.unlink()


def cmd_save(home):
    raw = sys.stdin.read()
    lines = [l.strip() for l in raw.splitlines() if l.strip() and not l.startswith("#")]
    data = load_json(home / "pending.json", {"items": []})
    items = data["items"]

    new_items, errors = [], []
    for line in lines:
        item, err = parse_line(line)
        if err:
            errors.append(f"line ignored ({err}): {line[:80]}")
        else:
            new_items.append(item)

    for item in new_items:
        if item["cls"] == "auto":
            try:
                applied = auto_apply(home, item)
            except Exception as exc:  # noqa: BLE001 - one bad fix must not lose the batch
                item["note"] = f"fix falhou ({exc}); ficou pendente"
                applied = False
            item["status"] = "applied" if applied else "pending"

    # A number, once shown to the user, never moves to another proposal.
    # Renumbering the queue on every run meant that answering "dream apply 2"
    # against last night's report could apply a different item than the one the
    # user read. Numbers are handed out once and never reused while the queue
    # is alive; they restart at 1 whenever it empties.
    next_n = data.get("next_n") or max([it.get("n") or 0 for it in items] + [0]) + 1
    for it in new_items:
        it["n"] = next_n
        next_n += 1

    pending = [it for it in items if it["status"] == "pending"] + [it for it in new_items if it["status"] == "pending"]
    done = [it for it in items if it["status"] != "pending"] + [it for it in new_items if it["status"] != "pending"]
    for it in pending:
        if not it.get("n"):
            it["n"] = next_n
            next_n += 1
    data["items"] = pending + done
    data["next_n"] = 1 if not pending else next_n
    data["batch"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_json(home / "pending.json", data)

    meta = load_json(home / "transcripts" / "meta.json", {})
    state = load_json(home / "state.json", {})
    window_end = meta.get("window_end")
    if window_end is None:
        # No meta.json means collect.py did not run in this state home. Stamping
        # the current time here would silently skip a window nobody read, so the
        # previous last_run is kept and the next collection covers the gap.
        print("warning: transcripts/meta.json is missing, last_run left untouched", file=sys.stderr)
    else:
        state["last_run"] = window_end
        save_json(home / "state.json", state)

    if not pending and not new_items:
        print("NO_PROPOSALS")
        for e in errors:
            print(e, file=sys.stderr)
        return 0

    title = f"Propostas do dream ({data['batch']}):"
    report = render(pending, title)
    stuck_auto = [str(it["n"]) for it in pending if it["cls"] == "auto"]
    review = [str(it["n"]) for it in pending if it["cls"] != "auto"]
    # Only this run: counting every applied item ever would inflate the number
    # a little more each night.
    applied_now = [it for it in new_items if it["cls"] == "auto" and it["status"] == "applied"]
    tail = []
    if applied_now:
        tail.append(f"Aplicadas automaticamente nesta rodada: {len(applied_now)} (typo/índice).")
    if stuck_auto:
        tail.append(f"Automáticas com problema, viraram pendentes: {', '.join(stuck_auto)}.")
    if review:
        tail.append(f"Aguardando aprovação: responda \"dream apply {','.join(review)}\" ou \"dream apply all\".")
    if not pending:
        tail.append("Nenhuma pendência.")
    report += "\n\n" + " ".join(tail)
    print(report)

    runs_dir = home / "runs"
    runs_dir.mkdir(exist_ok=True)
    target = (runs_dir / datetime.now().strftime("%Y-%m-%d-%H%M%S")).with_suffix(".md")
    target.write_text(report + "\n", encoding="utf-8")
    rotate_runs(home)
    for e in errors:
        print(e, file=sys.stderr)
    return 0


def parse_nums(arg, items):
    pending = [it for it in items if it["status"] == "pending"]
    if arg == "all":
        return {it["n"] for it in pending}
    try:
        wanted = {int(x) for x in arg.split(",")}
    except ValueError:
        print(f"invalid numbers: {arg}", file=sys.stderr)
        sys.exit(2)
    valid = {it["n"] for it in pending}
    unknown = wanted - valid
    if unknown:
        print(f"no pending proposal with number: {sorted(unknown)}", file=sys.stderr)
    return wanted & valid


def cmd_mark(home, arg, status):
    data = load_json(home / "pending.json", {"items": []})
    nums = parse_nums(arg, data["items"])
    if not nums:
        print("Nada a marcar.")
        return 0
    verb = "aplicada" if status == "applied" else "descartada"
    for it in data["items"]:
        if it["status"] == "pending" and it["n"] in nums:
            it["status"] = status
            print(f"{it['n']}. [{label(it)}] {it['summary']} -> {verb}")
    remaining = [it for it in data["items"] if it["status"] == "pending"]
    if not remaining:
        data["next_n"] = 1
    save_json(home / "pending.json", data)
    print(f"Pendentes restantes: {len(remaining)}")
    return 0


def cmd_list(home):
    data = load_json(home / "pending.json", {"items": []})
    pending = [it for it in data["items"] if it["status"] == "pending"]
    if not pending:
        print("Nenhuma proposta pendente.")
        return 0
    print(render(pending, f"Propostas pendentes ({data.get('batch', '?')}):"))
    print()
    print("Para aprovar: dream apply 1,3 ou dream apply all. Para descartar: dream dismiss 1,3.")
    return 0


def cmd_archive_file(home, name):
    if os.path.basename(name) == INDEX_FILE:
        print(f"refusing to archive the index ({INDEX_FILE})", file=sys.stderr)
        return 2
    path = safe_memory_path(home, name)
    if path is None or not path.exists():
        print(f"memory file not found: {name}", file=sys.stderr)
        return 1
    archive = home / "archive"
    archive.mkdir(exist_ok=True)
    target = archive / path.name
    if target.exists():
        target = archive / f"{path.stem}-{datetime.now():%Y%m%d%H%M%S}.md"
    path.rename(target)

    index = home / "memory" / INDEX_FILE
    if index.exists():
        # Match the markdown link, not the bare name in parentheses, so a line
        # that merely mentions the file in its prose survives.
        link = f"]({path.name})"
        kept = [l for l in index.read_text(encoding="utf-8").splitlines() if link not in l]
        index.write_text("\n".join(kept) + "\n", encoding="utf-8")
    print(f"arquivado: memory/{path.name} -> archive/{target.name}; linha removida do índice")
    return 0


def cmd_status(home):
    data = load_json(home / "pending.json", {"items": []})
    state = load_json(home / "state.json", {})
    memories = [p for p in (home / "memory").glob("*.md") if p.name != INDEX_FILE]
    pending = [it for it in data["items"] if it["status"] == "pending"]
    last = state.get("last_run")
    last_str = datetime.fromtimestamp(last).strftime("%Y-%m-%d %H:%M") if last else "nunca"
    print(f"memórias: {len(memories)} | pendentes: {len(pending)} | último run: {last_str}")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    home = state_home()
    (home / "memory").mkdir(parents=True, exist_ok=True)
    cmd = sys.argv[1]
    if cmd == "save":
        return cmd_save(home)
    if cmd == "list":
        return cmd_list(home)
    if cmd == "applied" and len(sys.argv) == 3:
        return cmd_mark(home, sys.argv[2], "applied")
    if cmd == "dismiss" and len(sys.argv) == 3:
        return cmd_mark(home, sys.argv[2], "dismissed")
    if cmd == "archive-file" and len(sys.argv) == 3:
        return cmd_archive_file(home, sys.argv[2])
    if cmd == "status":
        return cmd_status(home)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
