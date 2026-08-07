"""The face of the CLI: cover, palette, selector and summary.

Written against the standard library on purpose. Every other Python file in
this repository is stdlib only, and the scripts run on whatever python3 the
host has, so the installer asking for a package would be the odd one out. It
also keeps the wheel dependency free, which is why pip install is instant.

Everything printed here is ASCII. Colour and spacing carry the look; a
decorative glyph would break on a non UTF-8 locale, which is exactly the kind
of machine someone is on when they are setting a new tool up.
"""

from __future__ import annotations

import os
import shutil
import sys

try:  # Windows outside WSL has no termios, and importing it there is fatal.
    import termios
    import tty

    HAS_TERMIOS = True
except ImportError:  # pragma: no cover - platform dependent
    HAS_TERMIOS = False

# Straight from .github/assets/banner.svg, so the terminal and the README
# cover read as the same thing.
WHITE = (249, 250, 251)
BLUE = (59, 130, 246)
GREEN = (16, 185, 129)
PURPLE = (167, 139, 250)
GRAY = (148, 163, 184)
AMBER = (217, 119, 6)

_BASIC = {WHITE: 97, BLUE: 34, GREEN: 32, PURPLE: 35, GRAY: 90, AMBER: 33}

HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"


class Cancelled(Exception):
    """The user pressed q or Ctrl-C. Nothing has been written."""


def _colour_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM", "") in ("", "dumb"):
        return False
    return sys.stdout.isatty()


COLOUR = _colour_enabled()
TRUECOLOR = os.environ.get("COLORTERM", "") in ("truecolor", "24bit")


def paint(text: str, rgb, bold: bool = False) -> str:
    if not COLOUR:
        return text
    if TRUECOLOR:
        code = "38;2;%d;%d;%d" % rgb
    else:
        code = str(_BASIC.get(rgb, 39))
    prefix = "\x1b[1;%sm" % code if bold else "\x1b[%sm" % code
    return "%s%s\x1b[0m" % (prefix, text)


def width() -> int:
    return max(40, min(shutil.get_terminal_size((80, 24)).columns, 100))


def cover(version: str) -> None:
    """The node from the banner, plus the wordmark.

    Deliberately small. A full figlet wordmark is eleven characters wide before
    styling and wraps on a narrow terminal, which looks worse than no art.
    """
    node_blue = paint("o", BLUE, bold=True)
    node_green = paint("o", GREEN, bold=True)
    node_purple = paint("o", PURPLE, bold=True)
    hub = paint("o", WHITE, bold=True)
    edge = lambda s: paint(s, GRAY)  # noqa: E731 - a label, not a function

    name = paint("ai-harness", WHITE, bold=True)
    tag = paint("agents / skills / commands / hooks / rules", GRAY)

    print()
    print("   %s   %s" % (node_blue, node_green))
    print("    %s %s      %s  %s" % (edge("\\"), edge("/"), name, paint(version, GRAY)))
    print("     %s" % hub)
    print("     %s       %s" % (edge("|"), tag))
    print("     %s" % node_purple)
    print()


def step(number: int, total: int, title: str) -> None:
    print("%s  %s" % (paint("%d/%d" % (number, total), BLUE, bold=True), title))


def clip(text: str, room: int) -> str:
    """Keep a line on one physical row.

    Wrapping is not just ugly here: the selector redraws by moving the cursor
    up one row per line it drew, so a line that wraps makes it overwrite the
    wrong rows and the list smears down the screen.
    """
    return text if len(text) <= room else text[: max(1, room - 3)] + "..."


def detail(text: str) -> None:
    print("      %s" % paint(clip(text, width() - 6), GRAY))


def success(text: str) -> None:
    print("%s  %s" % (paint("ok", GREEN, bold=True), text))


def warn(text: str) -> None:
    print("%s  %s" % (paint("!!", AMBER, bold=True), text))


def count(number: int, noun: str) -> str:
    return "%s %s" % (paint(str(number), PURPLE, bold=True), noun)


def blank() -> None:
    print()


def interactive() -> bool:
    return HAS_TERMIOS and sys.stdin.isatty() and sys.stdout.isatty()


def _read_key() -> str:
    """One keypress, with the three byte arrow sequences folded in."""
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        char = sys.stdin.read(1)
        if char == "\x1b":
            # An arrow arrives as ESC [ A. A lone ESC is a quit.
            following = sys.stdin.read(2)
            return {"[A": "up", "[B": "down", "[C": "right", "[D": "left"}.get(
                following, "escape"
            )
        if char in ("\r", "\n"):
            return "enter"
        if char == "\x03":
            raise KeyboardInterrupt
        return char
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)


HINTS = "arrows move   space pick   a all   n none   enter ok   q quit"
# Clipping the key hints would hide how to quit, which is the one a stuck user
# needs most. A shorter spelling beats a truncated one.
HINTS_NARROW = "arrows  space  a/n  enter  q"


def _render(options, chosen, cursor, first: bool) -> int:
    room = width()
    lines = []
    for index, (label, hint) in enumerate(options):
        mark = "[x]" if index in chosen else "[ ]"
        pointer = ">" if index == cursor else " "
        # Measure in plain text: the colour escapes carry no width, so laying
        # the row out on the painted string would overshoot the terminal.
        head = "  %s %s %s" % (pointer, mark, label)
        pad = max(1, 26 - len(label))
        if hint and len(head) + pad + len(hint) > room:
            hint = ""

        painted_mark = paint(mark, BLUE, bold=True) if index in chosen else mark
        painted_label = paint(label, WHITE, bold=True) if index == cursor else label
        row = "  %s %s %s" % (pointer, painted_mark, painted_label)
        if hint:
            row += "%s%s" % (" " * pad, paint(hint, GRAY))
        lines.append(row)

    hints = HINTS if len(HINTS) + 6 <= room else HINTS_NARROW
    lines.append("")
    lines.append("      %s" % paint(clip(hints, room - 6), GRAY))

    if not first:
        # Walk back over what we drew last time and overwrite it in place.
        sys.stdout.write("\x1b[%dA" % len(lines))
    for line in lines:
        sys.stdout.write("\x1b[2K" + line + "\n")
    sys.stdout.flush()
    return len(lines)


def select(options, preselected) -> list:
    """Multi select. Returns the chosen indexes, or raises Cancelled.

    `options` is a list of (label, hint). The hint is the destination or the
    reason something is offered, shown dim on the right.
    """
    if not options:
        return []

    chosen = set(preselected)
    cursor = 0
    first = True

    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()
    try:
        while True:
            _render(options, chosen, cursor, first)
            first = False

            key = _read_key()
            if key == "up":
                cursor = (cursor - 1) % len(options)
            elif key == "down":
                cursor = (cursor + 1) % len(options)
            elif key == " ":
                chosen.symmetric_difference_update({cursor})
            elif key == "a":
                chosen = set(range(len(options)))
            elif key == "n":
                chosen = set()
            elif key == "enter":
                return sorted(chosen)
            elif key in ("q", "escape"):
                raise Cancelled()
    except KeyboardInterrupt:
        raise Cancelled()
    finally:
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()


def select_numbered(options, preselected) -> list:
    """Fallback for terminals without termios, which means Windows.

    Ugly next to the arrow selector, and the only thing standing between a
    Windows user and an ImportError on the first line.
    """
    for index, (label, hint) in enumerate(options, start=1):
        mark = "x" if index - 1 in preselected else " "
        suffix = "   %s" % hint if hint else ""
        print("  %d) [%s] %s%s" % (index, mark, label, suffix))
    print()
    raw = input("      numbers separated by comma, or enter to keep the marked ones: ")
    raw = raw.strip()
    if not raw:
        return sorted(preselected)

    picked = []
    for piece in raw.replace(" ", "").split(","):
        if piece.isdigit() and 1 <= int(piece) <= len(options):
            picked.append(int(piece) - 1)
    return sorted(set(picked))


def choose(options, preselected) -> list:
    if interactive():
        return select(options, preselected)
    return select_numbered(options, preselected)


def confirm(question: str) -> bool:
    if not sys.stdin.isatty():
        return True
    try:
        answer = input("      %s [Y/n] " % question).strip().lower()
    except (KeyboardInterrupt, EOFError):
        raise Cancelled()
    return answer in ("", "y", "yes")
