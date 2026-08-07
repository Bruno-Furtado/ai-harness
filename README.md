<p><small>🇧🇷 <a href="README.pt-BR.md">Versão em português</a></small></p>

<p align="center">
  <img src="./.github/assets/banner.svg" alt="ai-harness">
</p>

<h3 align="center">Write an agent, a skill, a command, a hook or a rule once.<br>One command installs it into every AI tool you use.</h3>

<p align="center">
  <a href="https://github.com/Bruno-Furtado/ai-harness/actions/workflows/ci.yml"><img src="https://github.com/Bruno-Furtado/ai-harness/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/ai-harness-cli/"><img src="https://img.shields.io/pypi/v/ai-harness-cli?color=3B82F6&style=flat" alt="PyPI"></a>
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

`harness` asks which tools to install into, and which artifacts to bring, then puts them where each tool looks.

```bash
pip install ai-harness-cli
harness
```

To write your own artifacts, clone this repository and run `./harness` from it. A clone links instead of copying, so a `git pull` reaches every tool at once.

```bash
harness update   # bring the latest artifacts and reconcile
harness check    # audit what is installed
harness remove   # take back only what harness installed
```

## Contents

The map of the repository, for writing an artifact or finding where a piece lives.

| Path | What lives there |
| --- | --- |
| `agents/` | Agents, in the format each tool reads |
| `skills/` | Skills in the open Agent Skills layout |
| `commands/` | Prompts that each tool exposes as a command |
| `hooks/` | Guard scripts the adapters share |
| `rules/` | Global rules, linked as `AGENTS.md` |
| `adapters/` | What each tool needs to wire the rest up |
| `docs/` | How to author an artifact and how the pieces fit together |
| `harness`, `ai_harness/` | The installer |
| `targets.json` | Where every artifact lands, per tool |
| `CONTRIBUTING.md` | How to propose a change and how releases are cut |

## Catalog

What you get once it is installed.

<!-- catalog:start -->

### Skills

| Name | What it does |
| --- | --- |
| [dream](skills/dream/SKILL.md) | Reads the day's sessions and suggests what is worth remembering, like the fact that you prefer Postgres. |
| [news-digest](skills/news-digest/SKILL.md) | Reads your feeds and delivers the day's news as one short message, skipping what you already saw. |
| [task-delegation](skills/task-delegation/SKILL.md) | Hands a heavy task to OpenCode so it runs on the strongest model you have available. |
| [topic-research](skills/topic-research/SKILL.md) | Researches a topic across Hacker News, Reddit and GitHub, with a link behind every claim. |

### Agents

| Name | What it does |
| --- | --- |
| [code-reviewer](agents/code-reviewer.md) | Reads your diff and points out bugs, security risks and missing tests. Changes nothing. |
| [news-digest-validator](agents/news-digest-validator.md) | Checks the digest before it reaches you and cuts repeated, obvious or badly translated stories. |
| [proposal-validator](agents/proposal-validator.md) | Sends your plan to a different model, to catch what the first one talked itself into. |

### Commands

| Name | What it does |
| --- | --- |
| [dream](commands/dream.md) | Runs dream and applies the suggestions you approve, one by one. |
| [news-digest](commands/news-digest.md) | Asks for today's digest right now. |
| [review-changes](commands/review-changes.md) | Reviews what you changed, before you open the pull request. |
| [topic-research](commands/topic-research.md) | Researches a topic and writes a report you can check, since every claim cites its source. |
| [validate-proposal](commands/validate-proposal.md) | Sends the plan on the table for an independent second opinion. |

### Hooks

| Name | What it does |
| --- | --- |
| [protect-secrets](hooks/protect-secrets.sh) | Stops the agent from opening .env, key and certificate files, even when you ask by accident. |

### Rules

| Name | What it does |
| --- | --- |
| [global](rules/global.md) | Tells the agent how to work everywhere: ask when unsure, show evidence before claiming it is done. |

<!-- catalog:end -->

## Integration

This is where each artifact lands.

<!-- integration:start -->

| Artifact | Claude Code | OpenCode | Codex | Hermes |
| --- | --- | --- | --- | --- |
| `skills/<name>/` | `~/.claude/skills` | `~/.config/opencode/skills` | `~/.agents/skills` | `~/.hermes/skills` |
| `agents/<name>.md` | `~/.claude/agents` | `~/.config/opencode/agents` | Not supported | Not supported |
| `commands/<name>.md` | `~/.claude/commands` | `~/.config/opencode/commands` | `~/.codex/prompts` | Not supported |
| `rules/global.md` | `~/.claude/CLAUDE.md` | `~/.config/opencode/AGENTS.md` | `~/.codex/AGENTS.md` | Not supported |

<!-- integration:end -->

## Tool support

| Tool | Skills | Agents | Commands | Rules | Hooks |
| --- | :---: | :---: | :---: | :---: | :---: |
| OpenCode | Yes | Yes | Yes | Yes | Adapter |
| Claude Code | Yes | Yes | Yes | Yes | Yes |
| Codex | Yes | Partial | Partial | Yes | Yes |
| Hermes | Yes | No | No | Workspace | No |

Partial means Codex has no subagent format, and its prompts document no frontmatter, so only the body carries over. Workspace means Hermes reads rules from the project, so there is no global file to install.

## Design rules

- One job per artifact. `name` and `description` stay portable, and any restriction is stated in the body too.
- Acceptance criteria before the implementation, evidence before calling it done.
- No credentials, no pinned models, no machine specific paths.

The reasoning behind each one is in [docs/authoring.md](docs/authoring.md).

---

<sub>Any other tool that reads Agent Skills and `AGENTS.md` picks up the skills and the rules on its own. Point it at `skills/` and at `rules/global.md`. The rest depends on what that tool supports.</sub>

<p align="center">Made with ❤️ in Curitiba 🌳 ☔️</p>
