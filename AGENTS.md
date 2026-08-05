# ai-harness

## Purpose

This repository contains portable configuration for coding agents. Keep the portable source separate from tool-specific adapters.

## Language and writing

- Write repository files in English unless the file is `README.pt-BR.md`.
- Keep both READMEs concise, direct and human-readable.
- Use short sentences and concrete verbs.
- Do not use em dashes, hype, marketing language or claims that are not tested.

## Artifact standards

- Skills live at `skills/<name>/SKILL.md` and follow agentskills.io.
- Skill names use lowercase letters, numbers and single hyphens.
- Every agent, command and skill must state scope, non-goals, acceptance criteria and validation steps.
- Every agent, command and skill keeps `name` and `description` portable, and states any restriction in the body too, because frontmatter keys only apply in the tool that defines them.
- Do not pin a model in a committed artifact. The model is a choice of whoever installs it.
- Agents must not claim success without evidence.
- Validators are read-only by default.
- `docs/authoring.md` is the reference for every format.

## Safety

- Never commit secrets, credentials, private paths or personal data.
- Do not add a hook that executes arbitrary input without validation.
- Do not change existing user configuration during sync.
- Prefer a dry run before any installation or destructive action.

## Verification

Run these checks before opening a pull request:

```bash
for file in sync.sh hooks/*.sh docs/templates/hook.sh; do bash -n "$file"; done
./sync.sh --dry-run
./sync.sh --check
```

`bash -n` only parses its first argument, so always check one file per call.

Review the diff and test any adapter in the tool it targets.
