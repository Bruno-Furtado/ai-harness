<p><small>🇧🇷 <a href="README.pt-BR.md">Versão em português</a></small></p>

<p align="center">
  <img src="./.github/assets/banner.svg" width="420" alt="ai-harness">
</p>

<h3 align="center">Your agents, skills, hooks, commands and rules in one place</h3>

<p align="center">
  <a href="https://github.com/Bruno-Furtado/ai-harness/actions/workflows/ci.yml"><img src="https://github.com/Bruno-Furtado/ai-harness/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-22C55E?style=flat" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/standard-agentskills.io-3B82F6?style=flat" alt="Agent Skills">
  <img src="https://img.shields.io/badge/standard-AGENTS.md-3B82F6?style=flat" alt="AGENTS.md">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/tool-OpenCode-111827?style=flat" alt="OpenCode">
  <img src="https://img.shields.io/badge/tool-Claude_Code-D97706?style=flat" alt="Claude Code">
  <img src="https://img.shields.io/badge/tool-Codex-059669?style=flat" alt="Codex">
  <img src="https://img.shields.io/badge/tool-Hermes-7C3AED?style=flat" alt="Hermes">
</p>

## What it is

`ai-harness` is a small, public collection of reusable agent configuration. It keeps the portable parts in open formats and leaves tool-specific integration in adapters.

The goal is simple: write once, use the same work across OpenCode, Claude Code, Codex, Hermes and other tools.

## Install

```bash
git clone https://github.com/Bruno-Furtado/ai-harness.git
cd ai-harness
./sync.sh --dry-run
./sync.sh
```

`sync.sh` creates symlinks from this repository into the configuration directory of each supported tool. It never replaces an existing real file, and `--dry-run` prints every change before anything is applied. Use `./sync.sh --check` to audit the links and `./sync.sh --unlink` to remove only the links that point back here.

## Tool support

| Tool | Skills | Agents | Commands | Rules | Hooks |
| --- | :---: | :---: | :---: | :---: | :---: |
| OpenCode | Yes | Yes | Yes | Yes | Adapter |
| Claude Code | Yes | Yes | Yes | Yes | Yes |
| Codex | Yes | Partial | Partial | Yes | Yes |
| Hermes | Yes | No | No | Yes | No |
| Other tools | Agent Skills | Depends on tool | Depends on tool | `AGENTS.md` | Depends on tool |

## Contents

| Path | Purpose |
| --- | --- |
| `agents/` | Read-only reviewer and cross-model validator examples |
| `skills/` | Installable skills following agentskills.io |
| `commands/` | Reusable command prompts |
| `hooks/` | Small security hooks shared by adapters |
| `rules/` | Personal global rules |
| `adapters/` | Tool-specific integration examples |
| `docs/authoring.md` | How to create a skill, agent, command, hook or rule |
| `docs/templates/` | Templates with acceptance criteria and validation sections |
| `sync.sh` | Safe, idempotent symlink setup for the owner |

## Creating an artifact

Read [docs/authoring.md](docs/authoring.md). It covers where each artifact lives, which frontmatter fields are portable, which ones belong to a single tool, and how to validate the result before committing.

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

This project is licensed under the **MIT License**. See the [`LICENSE`](LICENSE) file for the full terms.

---

<p align="center">Made with ❤️ in Curitiba 🌳 ☔️</p>
