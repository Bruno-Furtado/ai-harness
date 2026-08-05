<p><small>🇧🇷 <a href="README.pt-BR.md">Versão em português</a></small></p>

<p align="center">
  <img src="./.github/assets/banner.svg" alt="ai-harness">
</p>

<h3 align="center">Tool agnostic agents, skills, commands, hooks and rules, in one place</h3>

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

Write an agent, a skill, a command, a hook or a rule once and use it in every tool you work with. The portable part follows open standards, Agent Skills and `AGENTS.md`, while the wiring each tool needs stays in `adapters/`, so nothing here is tied to a single vendor.

## Install

```bash
git clone https://github.com/Bruno-Furtado/ai-harness.git
cd ai-harness

./sync.sh --dry-run   # preview every change, nothing is written
./sync.sh             # link the artifacts into each tool
./sync.sh --check     # audit the links later
./sync.sh --unlink    # remove only the links that point back here
```

## Tool support

| Tool | Skills | Agents | Commands | Rules | Hooks | Notes |
| --- | :---: | :---: | :---: | :---: | :---: | --- |
| OpenCode | Yes | Yes | Yes | Yes | Adapter | Hooks arrive through a plugin |
| Claude Code | Yes | Yes | Yes | Yes | Yes | |
| Codex | Yes | Partial | Partial | Yes | Yes | No subagent format, and prompts document no frontmatter, so only the body carries over |
| Hermes | Yes | No | No | Yes | No | Consumes skills and workspace rules only |

Any other tool that reads Agent Skills and `AGENTS.md` gets the skills and the rules. The rest depends on what that tool supports.

## Contents

| Path | What lives there |
| --- | --- |
| `agents/` | Agents, in the format each tool reads |
| `skills/` | Skills in the open Agent Skills layout |
| `commands/` | Prompts that each tool exposes as a command |
| `hooks/` | Guard scripts the adapters share |
| `rules/` | Global rules, linked as `AGENTS.md` |
| `adapters/` | What each tool needs to wire the rest up |
| `docs/` | How to author an artifact and how the pieces fit together |
| `CONTRIBUTING.md` | How to propose a change and how releases are cut |
| `sync.sh` | Links everything into the tools you use |

## Design rules

- One job per artifact. `name` and `description` stay portable, and any restriction is stated in the body too.
- Acceptance criteria before the implementation, evidence before calling it done.
- No credentials, no pinned models, no machine specific paths.

The reasoning behind each one is in [docs/authoring.md](docs/authoring.md).

---

<p align="center">Made with ❤️ in Curitiba 🌳 ☔️</p>
