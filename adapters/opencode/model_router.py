#!/usr/bin/env python3
"""Run a task on OpenCode using the best available model for its tier.

Reads the tier model lists and credit signals from $OPCODE_MODELS_FILE
(default ~/.config/opencode/models.json). Tries the primary models in
order, then the free list. A run is abandoned early when the provider
reports exhausted credits on stderr (so the free fallback starts fast)
or when it exceeds the tier timeout. Prints the OpenCode response on
stdout and a one-line note about the chosen model on stderr.

This file is model-agnostic by design: no model id is hardcoded here.
"""
import argparse
import json
import os
import pathlib
import signal
import subprocess
import sys
import threading
import time

DEFAULT_CONFIG = pathlib.Path.home() / ".config" / "opencode" / "models.json"
KNOWN_BINS = [
    "/opt/homebrew/bin/opencode",
    str(pathlib.Path.home() / ".local" / "bin" / "opencode"),
    str(pathlib.Path.home() / ".config" / "opencode" / "opencode"),
]


def find_opencode():
    override = os.environ.get("OPENCODE_BIN")
    if override:
        return override
    import shutil
    found = shutil.which("opencode")
    if found:
        return found
    for candidate in KNOWN_BINS:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    sys.exit("model router: opencode binary not found")


def load_config(path):
    try:
        data = json.loads(pathlib.Path(path).read_text())
    except FileNotFoundError:
        sys.exit(f"model router: config not found at {path}")
    tiers = data.get("tiers", {}) if isinstance(data, dict) else {}
    if "reason" not in tiers or "light" not in tiers:
        sys.exit("model router: config needs tiers.reason and tiers.light")
    return data


def has_credit_signal(line, signals):
    low = (line or "").lower()
    return any(s.lower() in low for s in signals)


def kill_proc(proc):
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run(bin_path, model, prompt, timeout, cwd, signals):
    cmd = [bin_path, "run", "-m", model, "--auto", "--print-logs", prompt]
    proc = None
    credit = threading.Event()
    log_chunks = []

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd or os.getcwd(),
            start_new_session=True,
        )
    except OSError as exc:
        return None, f"could not start opencode: {exc}", True

    def reader():
        for line in proc.stderr:
            log_chunks.append(line)
            if not credit.is_set() and has_credit_signal(line, signals):
                credit.set()

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()

    deadline = time.time() + timeout
    while time.time() < deadline:
        if credit.is_set() or proc.poll() is not None:
            break
        time.sleep(0.4)

    timed_out = proc.poll() is None
    if timed_out:
        kill_proc(proc)
    out = ""
    try:
        out = proc.stdout.read()
    except Exception:
        pass
    thread.join(timeout=5)
    try:
        for line in proc.stderr:
            log_chunks.append(line)
    except Exception:
        pass
    stderr_text = "".join(log_chunks)
    return out, stderr_text, credit.is_set(), timed_out, proc.returncode


def main():
    ap = argparse.ArgumentParser(description="Run a task on OpenCode on the best model for its tier")
    ap.add_argument("--tier", choices=["reason", "light"], required=True)
    ap.add_argument("--cwd", default=None)
    ap.add_argument("prompt", nargs="+", help="task to delegate")
    args = ap.parse_args()

    config = load_config(os.environ.get("OPCODE_MODELS_FILE", str(DEFAULT_CONFIG)))
    tier = config["tiers"][args.tier]
    primaries = tier.get("primary", [])
    frees = tier.get("free", [])
    signals = config.get("credit_signals", [])
    timeout = config.get("timeout_seconds", {}).get(args.tier, 300)
    prompt = " ".join(args.prompt)
    bin_path = find_opencode()

    attempts = [(m, "primary") for m in primaries] + [(m, "free") for m in frees]
    if not attempts:
        sys.exit("model router: no models configured for tier")

    for model, kind in attempts:
        out, stderr, timed_out, credit_hit, rc = run(
            bin_path, model, prompt, timeout, args.cwd, signals
        )
        if credit_hit:
            print(f"[model-router] {model}: credits exhausted; trying next", file=sys.stderr)
            continue
        if timed_out:
            print(f"[model-router] {model}: timed out after {timeout}s; trying next", file=sys.stderr)
            continue
        text = (out or "").strip()
        if rc == 0 and text:
            print(f"[model-router] ran {model} (tier={args.tier}, {kind})", file=sys.stderr)
            sys.stdout.write(text)
            return 0
        print(f"[model-router] {model}: failed rc={rc}; trying next", file=sys.stderr)

    print("[model-router] all models failed; check stderr above", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())