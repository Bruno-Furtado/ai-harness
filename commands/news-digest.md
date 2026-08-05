---
description: Build the personal news digest, validate it with a second model and archive it.
---

Build the user's news digest following the `news-digest` skill, end to end, producing the archive and this response.

Optional filter: `$ARGUMENTS` may name specific sections to include (for example `cloud ia`). When empty, cover every section in the user's configured sources.

Collect candidates with the skill scripts, rank them per the curation criteria and draft the digest in the user's language. Then delegate the draft to the `news-validator` subagent for an independent pass. The validator must run on a model different from this one; if no differently configured model is available, state that clearly in the final output instead of silently self-validating. Apply the validator's findings, archive the digest under the state home, mark the shown items as seen and present the result.

After presenting, invite feedback (for example "+2 -1" or "more of X") and record it with the skill's feedback step.

## Non-goals

- Do not invent sections: only sections present in the user's `sources.yaml` are shown.
- Do not fetch or approve sources beyond those already configured; additions need explicit user approval.
- Do not bypass the dedupe memory (for example, re-showing a story marked as seen).
- Do not assume a validator ran on another model or claim a validation that did not happen.

## Acceptance criteria

- Digest sections come from the user's configured sources, not hardcoded topics.
- The validator pass ran on a different model, or the limitation was disclosed in the output.
- The archive file exists under the state home and the shown items were marked as seen.

## Validation

Before reporting done, run the skill's status command and confirm the seen counter grew by the number of shown items.
