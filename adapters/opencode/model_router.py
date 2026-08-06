#!/usr/bin/env python3
"""Run a task on OpenCode using the best available model for its tier.

Reads the tier model lists and credit signals from $OPCODE_MODELS_FILE
(default ~/.config/opencode/models.json). Tries the primary models in
order, then the free list. A run is abandoned early when the provider
reports exhausted credits on stderr (so the free fallback starts fast)
or when it exceeds the tier timeout. The whole cascade is bounded by
total_budget_seconds, because a caller such as a scheduler gives up long
before every model has burned a full timeout. Prints the OpenCode response
on stdout and a one-line note about the chosen model on stderr.

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
        return None, f"could not start opencode: {exc}", False, False, 127

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
    ap.add_argument("--tier", required=True, help="a tier name present in the models file")
    ap.add_argument("--cwd", default=None)
    ap.add_argument(
        "--budget",
        type=int,
        default=0,
        help="seconds to spend across all attempts before giving up (0 = no budget)",
    )
    ap.add_argument(
        "--model",
        default=None,
        help="run exactly this model and skip the cascade, for comparing models",
    )
    ap.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="skip this model in the cascade; repeatable. Use it to guarantee a second "
        "opinion comes from a different model than the first pass",
    )
    ap.add_argument("prompt", nargs="+", help="task to delegate")
    args = ap.parse_args()

    config = load_config(os.environ.get("OPCODE_MODELS_FILE", str(DEFAULT_CONFIG)))
    if args.tier not in config["tiers"]:
        known = ", ".join(sorted(config["tiers"]))
        sys.exit(f"model router: unknown tier {args.tier!r}; the models file defines: {known}")
    tier = config["tiers"][args.tier]
    primaries = tier.get("primary", [])
    frees = tier.get("free", [])
    signals = config.get("credit_signals", [])
    timeout = config.get("timeout_seconds", {}).get(args.tier, 300)
    budget = args.budget or config.get("total_budget_seconds", {}).get(args.tier, 0)
    prompt = " ".join(args.prompt)
    bin_path = find_opencode()

    if args.model:
        attempts = [(args.model, "pinned")]
    else:
        attempts = [(m, "primary") for m in primaries] + [(m, "free") for m in frees]
        excluded = set(args.exclude)
        if excluded:
            attempts = [(m, k) for m, k in attempts if m not in excluded]
            if not attempts:
                sys.exit(
                    f"model router: every model in tier {args.tier} was excluded; "
                    "the tier needs at least one model the other pass did not use"
                )
    if not attempts:
        sys.exit("model router: no models configured for tier")

    started = time.time()
    for model, kind in attempts:
        spent = time.time() - started
        if budget and spent >= budget:
            print(
                f"[model-router] giving up after {int(spent)}s, over the {budget}s budget "
                f"for tier={args.tier}",
                file=sys.stderr,
            )
            break
        # Never let one attempt run past what is left of the budget: a caller
        # such as a scheduler gives up long before 12 full timeouts elapse.
        attempt_timeout = min(timeout, budget - spent) if budget else timeout
        out, stderr, credit_hit, timed_out, rc = run(
            bin_path, model, prompt, attempt_timeout, args.cwd, signals
        )
        if credit_hit:
            print(f"[model-router] {model}: credits exhausted; trying next", file=sys.stderr)
            continue
        if timed_out:
            print(
                f"[model-router] {model}: timed out after {int(attempt_timeout)}s; trying next",
                file=sys.stderr,
            )
            continue
        text = (out or "").strip()
        if rc == 0 and text:
            print(f"[model-router] ran {model} (tier={args.tier}, {kind})", file=sys.stderr)
            sys.stdout.write(text)
            return 0
        reason = (stderr or "").strip().splitlines()[-1][:160] if (stderr or "").strip() else "no output"
        print(f"[model-router] {model}: failed rc={rc} ({reason}); trying next", file=sys.stderr)

    print("[model-router] all models failed; check stderr above", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())