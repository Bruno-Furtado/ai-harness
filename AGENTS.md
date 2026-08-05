# ai-harness

## Purpose

This repository contains portable configuration for coding agents. Keep the
portable source separate from tool-specific adapters.

## Language and writing

- Write repository files in English unless the file is `README.pt-BR.md`.
- Keep both READMEs concise, direct and human-readable.
- Use short sentences and concrete verbs.
- Do not use em dashes, hype, marketing language or claims that are not tested.

## Artifact standards

- Skills live at `skills/<name>/SKILL.md` and follow agentskills.io.
- Skill names use lowercase letters, numbers and single hyphens.
- Every agent, command and skill must state scope, non-goals, acceptance criteria and validation steps.
- Agents must not claim success without evidence.
- Validators are read-only by default.

## Safety

- Never commit secrets, credentials, private paths or personal data.
- Do not add a hook that executes arbitrary input without validation.
- Do not change existing user configuration during sync.
- Prefer a dry run before any installation or destructive action.

## Verification

Run these checks before opening a pull request:

```bash
bash -n sync.sh hooks/*.sh
./sync.sh --dry-run
./sync.sh --check
```

Review the diff and test any adapter in the tool it targets.
