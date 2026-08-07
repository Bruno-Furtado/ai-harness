# Architecture

## Source of truth

Portable content is stored in the repository. Tool-specific files live under `adapters/`. Where each artifact lands, per tool, is declared once in `targets.json`: the installer reads it, and so does the generator that writes the Integration table in both READMEs, so the docs cannot describe a layout the installer does not implement.

## Public installation surface

The `harness` CLI installs, and it runs two ways from one code path.

From a clone it symlinks, so a `git pull` reaches every tool at once. That is the mode for someone writing their own artifacts.

Installed from PyPI as `ai-harness-cli` it copies, from a bundled tree inside the wheel. Copying is not a stylistic choice: `pip install -U` rewrites the package directory and `pipx upgrade` recreates the whole venv, so a symlink into either would dangle after the first upgrade, silently, and the user would only find out when a skill stopped appearing.

Either way it never replaces an existing real file, and it removes only what it put there.

Skills use the open `skills/<name>/SKILL.md` layout from agentskills.io, which most tools discover on their own and which the `npx skills` CLI can install from this repository too. Templates stay in `docs/templates/` so they are never installed as if they were real artifacts. See [authoring.md](authoring.md) for the format of each artifact.

## Compatibility

OpenCode, Claude Code and Codex can consume `AGENTS.md` and Agent Skills, but their agent, command and hook configuration differs. Hermes consumes skills and workspace rules. Do not claim full compatibility for a host until its adapter has been tested with a supported version.

## Cross-model validation

The `proposal-validator` agent is read-only and does not pin a model. It should run on a different model from the one that produced the proposal. This is a review aid, not a guarantee of correctness.

## Security boundary

The secret hook is a guard against common mistakes. It does not replace host permissions, GitHub secret scanning, review or least-privilege configuration.
