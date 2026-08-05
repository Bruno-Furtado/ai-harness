# Architecture

## Source of truth

Portable content is stored in the repository. Tool-specific files live under
`adapters/`. The sync script links individual items and refuses to replace
existing real files.

## Public installation surface

Skills use the open `skills/<name>/SKILL.md` layout from agentskills.io. The
`npx skills` CLI discovers that layout and can install it for many tools. The
initial repository intentionally has no published skill; templates are kept in
`docs/templates/` so they are not accidentally installed.

## Compatibility

OpenCode, Claude Code and Codex can consume `AGENTS.md` and Agent Skills, but
their agent, command and hook configuration differs. Hermes consumes skills and
workspace rules. Do not claim full compatibility for a host until its adapter
has been tested with a supported version.

## Cross-model validation

The validator is read-only and uses a configurable model. It should be a
different model from the one that produced the proposal. This is a review aid,
not a guarantee of correctness.

## Security boundary

The secret hook is a guard against common mistakes. It does not replace host
permissions, GitHub secret scanning, review or least-privilege configuration.
