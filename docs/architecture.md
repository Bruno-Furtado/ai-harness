# Architecture

## Source of truth

Portable content is stored in the repository. Tool-specific files live under `adapters/`. The sync script links individual items and refuses to replace existing real files.

## Public installation surface

Skills use the open `skills/<name>/SKILL.md` layout from agentskills.io, which most tools discover on their own and which the `npx skills` CLI can install. Templates stay in `docs/templates/` so they are never installed as if they were real artifacts. See [authoring.md](authoring.md) for the format of each artifact.

## Compatibility

OpenCode, Claude Code and Codex can consume `AGENTS.md` and Agent Skills, but their agent, command and hook configuration differs. Hermes consumes skills and workspace rules. Do not claim full compatibility for a host until its adapter has been tested with a supported version.

## Cross-model validation

The `proposal-validator` agent is read-only and does not pin a model. It should run on a different model from the one that produced the proposal. This is a review aid, not a guarantee of correctness.

## Security boundary

The secret hook is a guard against common mistakes. It does not replace host permissions, GitHub secret scanning, review or least-privilege configuration.
