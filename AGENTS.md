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

## Pull requests

Every pull request, opened by a person or by an agent, must carry:

- an assignee, so it has an owner;
- at least one label, because release notes are grouped by label;
- the milestone of the version it targets.

The `Pull request` workflow fails when any of the three is missing. Create the label or the milestone that does not exist yet instead of leaving the field empty.

Use the existing labels first: `bug`, `enhancement`, `documentation`, `ci`. A pull request that mixes a fix and documentation carries both.

## Releases

Versions follow semantic versioning. Patch for a fix that breaks no install, minor for a new artifact or a newly supported tool, major for anything that breaks an existing install, such as moving where an artifact lives or renaming something `sync.sh` links.

Every `v*` tag becomes a release. Pushing the tag is the only manual step:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The `Release` workflow rejects a tag that is not semantic versioning, skips a release that already exists, marks a tag with a suffix as a prerelease, and generates the notes from the merged pull request labels. Never publish a release by hand: push the tag and let the workflow do it, so the notes always match the labels.
