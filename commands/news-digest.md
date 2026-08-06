---
description: Build the personal news digest, validate the selection with a second model and deliver one short message.
---

Build the user's news digest following the `news-digest` skill, end to end, producing the archive and this response.

Optional filter: `$ARGUMENTS` may name specific sections to include (for example `cloud ia`). When empty, cover every section in the user's configured sources.

Collect candidates with `fetch_feeds.py --compact`, rank them per the curation criteria and emit selection lines, `<id>|<title>|<why>`, with every title translated into the `digest_language` from `config.yaml`. Then send those lines and the compact shortlist to the `news-validator` subagent for an independent pass, and nothing else. The validator must run on a model different from this one; if no differently configured model is available, say so to the user, outside the delivered message, instead of silently self-validating.

Apply the validator's findings, then pipe the final selection lines into `render_digest.py --format brief`. Present its stdout exactly as printed, with no preamble, no process note and no summary of your own around it. Then run `state.py mark-shown --from-last`.

After presenting, invite feedback (for example `+1 -3` or "more of X") and record it with `state.py feedback --from-last "<the reply verbatim>"`.

## Non-goals

- Do not invent sections: only sections present in the user's `sources.yaml` are shown.
- Do not emit urls, prose or a rendered digest yourself: the renderer owns the format.
- Do not wrap the delivered message in commentary. The message is the deliverable.
- Do not bypass the dedupe memory (for example, re-showing a story marked as seen).
- Do not assume a validator ran on another model or claim a validation that did not happen.

## Acceptance criteria

- Digest sections come from the user's configured sources, not hardcoded topics.
- Every item is written in the configured `digest_language`, whatever language its source used.
- The renderer reported no warning about the character limit, so the result fits one message.
- The validator pass ran on a different model, or the limitation was disclosed.
- The archive file exists under the state home and the shown items were marked as seen.

## Validation

Before reporting done, run `state.py status` and confirm the seen counter grew by the number of shown items.
