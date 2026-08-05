---
name: news-digest
description: Builds a personal news digest from the user's own feed sources, with dedupe memory, cross-model validation and a learning feedback loop. Use when the user asks for their news digest, daily briefing or morning news, when recording feedback on digest items, or when a scheduled job produces the daily digest.
license: MIT
compatibility: Requires python3 and network access. Mutable state lives outside this skill directory.
metadata:
  audience: personal
---

# News Digest

Builds a personal digest from RSS/Atom sources the user owns, filters out items already shown and low-signal news, validates the draft with a second model, saves a markdown archive and learns from feedback.

## When to use

- The user asks for their news digest, daily briefing or "what is the news".
- The user gives feedback on digest items, for example "+2 -1" or "more of this".
- A scheduled job produces the daily digest.

## When not to use

- Breaking news lookup about one specific topic: answer directly with web tools.
- Any request that must bypass the dedupe memory, such as re-reading a source in full.

## State location

All mutable state lives outside this skill directory, in the state home:

- `$NEWS_DIGEST_HOME` when set, otherwise `~/.local/share/news-digest`.

Never write files inside the skill directory: it is usually a symlink into a repository, and this rule holds regardless of which tool loads the skill. The scripts in `scripts/` already follow it; follow it for manual edits too.

State files: `sources.yaml` (sections and feeds), `config.yaml` (run options), `seen.json` (dedupe memory), `feedback.jsonl` (marked items), `profile.md` (learned taste), `digests/YYYY-MM-DD.md` (archive).

## Running the scripts

Run the scripts from the skill directory (the folder that contains `SKILL.md`) as the working directory, for example `python3 scripts/fetch_feeds.py`. If the tool cannot set the working directory, call them by their absolute path `python3 <skill-dir>/scripts/fetch_feeds.py`. The scripts resolve the state home and their assets from where they live, so they are otherwise independent of the working directory.

## Inputs

- First run: ask the user which topics (sections) and sources they want. Run `state.py init`, then write their `sources.yaml` using `assets/sources.starter.yaml` as the format reference. Confirm every feed with `fetch_feeds.py --check` and remove or replace failures.
- Normal runs: an existing state home.

## Steps

1. Ensure state exists: `python3 scripts/state.py init`. It is idempotent. If `sources.yaml` still holds only the example sections, run the guided setup from Inputs before continuing.
2. Collect: `python3 scripts/fetch_feeds.py --json` and read the JSONL shortlist from stdout. Note feed warnings on stderr for later pruning.
3. Read `profile.md` from the state home.
4. Rank and select following `references/curation-criteria.md`: drop obvious and repeated stories, dedupe across outlets, prefer the user's profile. Respect the per-section cap from `config.yaml`.
5. Write the draft in the user's language, defaulting to the language of the conversation, using the output template in the criteria file.
6. Validate the draft with the `news-validator` agent or an equivalent second-model pass. Apply the findings before delivery.
7. Save the final digest to `digests/YYYY-MM-DD.md` in the state home and show it to the user.
8. Run `python3 scripts/state.py mark-shown --stdin` with the shown item ids, one per line, so nothing repeats tomorrow.
9. On feedback ("+2 -1", "more of X", "stop showing Y"): run `state.py feedback` per marked item. When patterns emerge, run `state.py compact-profile` and rewrite `profile.md` from its aggregates. Confirm the change in one short line.
10. Weekly, or when stderr shows repeated feed failures: propose source removals or additions. Additions need explicit user approval. Record approved feeds with `state.py sources-add` and verify with `fetch_feeds.py --check`.

## Cross-model validation

The drafting pass and the validation pass must run on different models. This skill pins no model: configure the second model in the tool you use, for example the `news-validator` agent model in the tool's local configuration. Agreement from the same model is not validation, and if you cannot guarantee a different model, say so explicitly in the output.

## Acceptance criteria

- Every digest item traces back to a fetched candidate and carries source, tier and link.
- No item repeats a previously shown story, including the same event covered by another outlet.
- Sections come from the user's `sources.yaml`, never from hardcoded topics.
- The validation pass ran on a different model, or the output states that it could not.
- State was written only under the state home.

## Validation

- `fetch_feeds.py --check` reports every feed reachable, or the failures were reported to the user.
- `state.py status` shows seen and feedback counts growing across runs.
- Request a second-model review before important changes to this skill.

## Scheduled delivery (optional)

This skill is delivery-agnostic: the markdown archive is written on every run. On tools with a scheduler, register the run there. On Hermes, after `hermes gateway setup` pairs a messaging platform such as Telegram, schedule with `hermes cron add "every day at 7am run the news-digest skill and send me the result"`. Scheduler and gateway configuration are user-side setup and are never stored in this skill.
