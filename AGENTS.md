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
- Every name uses lowercase letters, numbers and single hyphens, at most three words, and matches the file or folder it lives in.
- A skill is a noun phrase for the capability. An agent is `<scope>-<role>`, never a bare role, and an agent owned by a skill takes that skill's name as its scope. A command is either the name of the skill it opens or `<verb>-<object>`. Hooks and repository scripts are `<verb>-<object>`.
- A command that opens a skill stays thin: description, `$ARGUMENTS` contract, what to deliver, and the skill's name. The procedure lives in `SKILL.md` only.
- Adding or renaming an artifact requires a line in `docs/catalog.json` in both languages, then `python3 scripts/build-catalog.py` to regenerate the README catalog.
- Where an artifact lands, per tool, lives in `targets.json` alone. The installer and the Integration table in both READMEs both read it, so never edit that table by hand.
- Every agent, command and skill must state scope, non-goals, acceptance criteria and validation steps.
- Every agent, command and skill keeps `name` and `description` portable, and states any restriction in the body too, because frontmatter keys only apply in the tool that defines them.
- Do not pin a model in a committed artifact. The model is a choice of whoever installs it.
- Agents must not claim success without evidence.
- Validators are read-only by default.
- `docs/authoring.md` is the reference for every format.

## Safety

- Never commit secrets, credentials, private paths or personal data.
- Do not add a hook that executes arbitrary input without validation.
- Do not change existing user configuration during an install. An occupied path is a conflict to report, never something to overwrite.
- Remove only what the installer put there. A path that no longer matches what was installed belongs to the user.
- Prefer a dry run before any installation or destructive action.

## Verification

Run these checks before opening a pull request:

```bash
for file in hooks/*.sh docs/templates/hook.sh; do bash -n "$file"; done
python3 -m compileall -q ai_harness skills scripts
python3 scripts/build-catalog.py --check
HOME=$(mktemp -d) ./harness install --yes --dry-run
```

`bash -n` only parses its first argument, so always check one file per call.

Never point the installer at your real `HOME` while testing it. A throwaway `HOME` is the difference between a failed test and a config directory you have to repair by hand.

Review the diff and test any adapter in the tool it targets.

## Pull requests

Every pull request, opened by a person or by an agent, must carry:

- an assignee, so it has an owner;
- at least one label, because release notes are grouped by label;
- the milestone of the version it targets.

The `Pull request` workflow fails when any of the three is missing. Create the label or the milestone that does not exist yet instead of leaving the field empty.

Use the existing labels first: `bug`, `enhancement`, `documentation`, `ci`. A pull request that mixes a fix and documentation carries both.

## Releases

Versions follow semantic versioning. Patch for a fix that breaks no install, minor for a new artifact or a newly supported tool, major for anything that breaks an existing install, such as moving where an artifact lives or renaming something `harness` installs.

The version lives in `ai_harness/__init__.py`, and the release workflow refuses a tag that disagrees with it. Bump it in the same pull request as the change it ships.

Every `v*` tag becomes a release, and the same workflow publishes `ai-harness-cli` to PyPI. Pushing the tag is the only manual step:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The `Release` workflow rejects a tag that is not semantic versioning, skips a release that already exists, marks a tag with a suffix as a prerelease, and generates the notes from the merged pull request labels. Never publish a release by hand: push the tag and let the workflow do it, so the notes always match the labels.
