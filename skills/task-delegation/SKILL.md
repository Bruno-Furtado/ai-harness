---
name: task-delegation
description: Delegate a task to OpenCode running on the best available model for it. Use when a request would benefit from a strong reasoning model, when the current tool's own model is too weak or has no credits, or generally to hand a non-trivial task to OpenCode instead of doing it in the current tool.
license: MIT
compatibility: Optimal in Hermes; works wherever a shell can spawn `opencode-model-run`.
metadata:
  audience: personal
---

# Task Delegation

Hands a task to OpenCode, which runs it on the best available model for the task's tier: a paid model first, falling back to the next paid model and finally to a free model when the paid provider reports exhausted credits. OpenCode prints the completed result on stdout.

## When to use

- The user asks Hermes something non-trivial (analysis, drafting, reasoning, research, code) and the current tool's own model would produce a worse result.
- The current model has no credits and a task needs a stronger reasoning pass.
- The user, directly or indirectly, expects OpenCode to handle the request.

## When not to use

- Trivial replies, greetings, or yes/no questions: answer directly.
- Inside OpenCode itself: recursing would spawn another OpenCode. Run the work directly instead.
- A confirm-this-skill's-own-flow case where the task-delegation skill is not relevant.

## Steps

1. Classify the task: use `reason` for analysis, multi-step drafting, research or anything quality-sensitive; `light` otherwise.
2. Run, as your first action, and treat the full stdout as your answer:

```
$HOME/.local/bin/opencode-model-run --tier reason "<the user's complete request>"
```

3. Pass the model's response back to the user unchanged (plus, optionally, the `[model-router]` note from stderr saying which model ran).

## Non-goals

- Selecting a model on the user's behalf beyond tier choice; the router reads the user's own `models.json preferences.
- Doing the work instead of OpenCode inside this tool when delegation is expected.

## Acceptance criteria

- The delegation command was the first action and its complete stdout became the answer.
- If delegation is impossible because `opencode-model-run` is missing, that is stated instead of doing the work manually.
- No recursion was triggered when already inside OpenCode.

## Validation

- `opencode-model-run --tier light "reply with: ok` returns quickly with a free model and prints the chosen model.
- When credits are exhausted, the primary paid models fail fast and a free fallback answers; the whole thing completes without an hour-long wait.