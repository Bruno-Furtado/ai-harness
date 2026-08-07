<p><small>🇧🇷 <a href="README.pt-BR.md">Versão em português</a></small></p>

<p align="center">
  <img src="./.github/assets/banner.svg" alt="ai-harness">
</p>

<h3 align="center">Tool agnostic agents, skills, commands, hooks and rules, in one place</h3>

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

If your Python is managed by the system and pip refuses, use `pipx install ai-harness-cli` or `uv tool install ai-harness-cli`.

To write your own artifacts, clone this repository and run `./harness` from it. A clone links instead of copying, so a `git pull` reaches every tool at once.

```bash
harness update   # bring the latest artifacts and reconcile
harness check    # audit what is installed
harness remove   # take back only what harness installed
```

## Catalog

<!-- catalog:start -->

### Skills

| Name | What it does |
| --- | --- |
| [dream](skills/dream/SKILL.md) | Reviews the day's sessions and proposes memory changes, one evidence-cited item at a time. |
| [news-digest](skills/news-digest/SKILL.md) | Builds a personal digest from your own feeds, with dedupe memory and a second-model check. |
| [task-delegation](skills/task-delegation/SKILL.md) | Hands a task to OpenCode, which runs it on the best model available for that tier. |
| [topic-research](skills/topic-research/SKILL.md) | Collects what people said about a topic across several sources and reports it with citations. |

### Agents

| Name | What it does |
| --- | --- |
| [code-reviewer](agents/code-reviewer.md) | Reviews a change and reports risks, regressions and missing tests. Never edits files. |
| [news-digest-validator](agents/news-digest-validator.md) | Checks a digest selection for duplicates, obvious stories and weak translations before delivery. |
| [proposal-validator](agents/proposal-validator.md) | Gives a second opinion on a plan, a change or a report, on a different model. Read-only. |

### Commands

| Name | What it does |
| --- | --- |
| [dream](commands/dream.md) | Runs the dream memory routine, or applies, lists and dismisses its proposals. |
| [news-digest](commands/news-digest.md) | Builds the news digest and delivers it as one short message. |
| [review-changes](commands/review-changes.md) | Reviews the current git changes for correctness, security and missing tests. |
| [topic-research](commands/topic-research.md) | Researches a topic and writes a report where every claim cites a collected item. |
| [validate-proposal](commands/validate-proposal.md) | Sends the current plan, change or report for an independent second opinion. |

### Hooks

| Name | What it does |
| --- | --- |
| [protect-secrets](hooks/protect-secrets.sh) | Blocks tool calls that reference .env, credential, secret, certificate or key files. |

### Rules

| Name | What it does |
| --- | --- |
| [global](rules/global.md) | Standing rules for every project: working style, validation, safety and communication. |

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

Then invoke an artifact by the name in the catalog: `/news-digest` as a command, `code-reviewer` as a subagent, and a skill by asking for what it does.

Hooks are the exception. A hook is executable code, and no tool accepts one by symlink alone, so each tool is wired once. [hooks/README.md](hooks/README.md) has the how.

## Tool support

| Tool | Skills | Agents | Commands | Rules | Hooks | Notes |
| --- | :---: | :---: | :---: | :---: | :---: | --- |
| OpenCode | Yes | Yes | Yes | Yes | Adapter | Hooks arrive through a plugin |
| Claude Code | Yes | Yes | Yes | Yes | Yes | |
| Codex | Yes | Partial | Partial | Yes | Yes | No subagent format, and prompts document no frontmatter, so only the body carries over |
| Hermes | Yes | No | No | Workspace | No | Reads rules from the workspace, so there is no global file to install |

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
| `harness`, `ai_harness/` | The installer |
| `targets.json` | Where every artifact lands, per tool |
| `CONTRIBUTING.md` | How to propose a change and how releases are cut |

## Design rules

- One job per artifact. `name` and `description` stay portable, and any restriction is stated in the body too.
- Acceptance criteria before the implementation, evidence before calling it done.
- No credentials, no pinned models, no machine specific paths.

The reasoning behind each one is in [docs/authoring.md](docs/authoring.md).

---

<sub>Any other tool that reads Agent Skills and `AGENTS.md` picks up the skills and the rules on its own. Point it at `skills/` and at `rules/global.md`. The rest depends on what that tool supports.</sub>

<p align="center">Made with ❤️ in Curitiba 🌳 ☔️</p>
