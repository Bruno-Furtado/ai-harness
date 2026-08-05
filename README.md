<div align="center">

![cover](./assets/banner.svg)

[![CI](https://github.com/Bruno-Furtado/ai-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/Bruno-Furtado/ai-harness/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-22C55E?style=flat)](./LICENSE)
![Agent Skills](https://img.shields.io/badge/standard-agentskills.io-3B82F6?style=flat)
![AGENTS.md](https://img.shields.io/badge/standard-AGENTS.md-3B82F6?style=flat)
![OpenCode](https://img.shields.io/badge/tool-OpenCode-111827?style=flat)
![Claude Code](https://img.shields.io/badge/tool-Claude_Code-D97706?style=flat)
![Codex](https://img.shields.io/badge/tool-Codex-059669?style=flat)
![Hermes](https://img.shields.io/badge/tool-Hermes-7C3AED?style=flat)

</div>

<div align="center">
Your agents, skills, hooks, commands and rules in one place.
</div>

[Portuguese version](README.pt-BR.md)

## What it is

`ai-harness` is a small, public collection of reusable agent configuration. It keeps the portable parts in open formats and leaves tool-specific integration in adapters.

The goal is simple: write once, use the same work across OpenCode, Claude Code, Codex, Hermes and other tools.

## Install

Install skills from this repository with the open skills CLI:

```bash
npx skills add Bruno-Furtado/ai-harness
```

This repository starts with templates and no published skill. The command becomes useful as soon as a skill is added under `skills/<name>/SKILL.md`.

To use the complete collection locally:

```bash
git clone https://github.com/Bruno-Furtado/ai-harness.git
cd ai-harness
./sync.sh --dry-run
./sync.sh
```

## Tool support

| Tool | Skills | Agents | Commands | Rules | Hooks |
| --- | :---: | :---: | :---: | :---: | :---: |
| OpenCode | Yes | Yes | Yes | Yes | Adapter |
| Claude Code | Yes | Yes | Yes | Yes | Yes |
| Codex | Yes | Partial | Partial | Yes | Yes |
| Hermes | Yes | No | No | Yes | No |
| Other tools | Via `npx skills` | Depends on tool | Depends on tool | `AGENTS.md` | Depends on tool |

## Contents

| Path | Purpose |
| --- | --- |
| `agents/` | Read-only reviewer and cross-model validator examples |
| `skills/` | Installable skills following agentskills.io |
| `commands/` | Reusable command prompts |
| `hooks/` | Small security hooks shared by adapters |
| `rules/` | Personal global rules |
| `adapters/` | Tool-specific integration examples |
| `docs/templates/` | Templates with acceptance criteria and validation sections |
| `sync.sh` | Safe, idempotent symlink setup for the owner |

## Design rules

- Keep each artifact focused on one job.
- State assumptions before acting.
- Define acceptance criteria before implementation.
- Verify the result before reporting success.
- Use a second model for plans and important changes.
- Do not commit credentials, private data or provider tokens.
- Prefer the smallest change that solves the problem.

## Security

The repository is public. Do not add secrets or private project context. CI checks for leaked secrets and shell issues. Read [SECURITY.md](SECURITY.md) before adding hooks or integrations.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Changes go through pull requests. The `main` branch is protected.

## License

MIT. See [LICENSE](LICENSE).

<div align="center">
  <sub>Made with ♥ in Curitiba 🇧🇷 🌲 ☔️</sub>
</div>
