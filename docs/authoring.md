# Authoring artifacts

This guide explains how to add a skill, agent, command, hook or rule to this repository, and which parts of each format are portable.

## Portable first

Only two things in this repository work the same way in every tool:

- **Agent Skills** (`skills/<name>/SKILL.md`), an open standard specified at [agentskills.io](https://agentskills.io/specification).
- **`AGENTS.md`**, read natively by most coding agents.

Agents, commands and hooks have no open standard. Each tool defines its own frontmatter keys and its own hook payload. So the rule here is: put the meaning in `name`, `description` and the body, because every tool reads those, and treat tool-specific keys as extras that other tools ignore. When a behavior only exists in one tool, document it under `adapters/` instead of assuming it everywhere.

Prefer a skill whenever the content is instructions or a procedure. Reach for an agent or a command only when you need the tool's own delegation or menu.

## Skills

Location: `skills/<name>/SKILL.md`. The folder name is the skill name.

Frontmatter, per the [specification](https://agentskills.io/specification):

| Field | Required | Constraint |
| --- | :---: | --- |
| `name` | Yes | Up to 64 characters, lowercase letters, numbers and hyphens. No leading or trailing hyphen, no double hyphen. Must match the folder name. |
| `description` | Yes | Up to 1024 characters. Must say what the skill does **and** when to use it. |
| `license` | No | License name or the name of a bundled license file. |
| `compatibility` | No | Up to 500 characters. Environment requirements, such as required binaries or network access. |
| `metadata` | No | Map of string keys to string values. |
| `allowed-tools` | No | Space separated list of pre approved tools. Experimental, support varies by tool. |

Optional folders next to `SKILL.md`: `scripts/` for executable code, `references/` for documentation loaded on demand, `assets/` for templates and data.

Agents load skills progressively: the name and description are always in context, the body is loaded when the skill is triggered, and the extra files only when the body points to them. Keep `SKILL.md` under 500 lines and move long reference material into `references/`.

Validate and distribute:

```bash
skills-ref validate ./skills/<name>
npx skills add Bruno-Furtado/ai-harness
```

Start from [templates/SKILL.md](templates/SKILL.md).

## Agents

Location: `agents/<name>.md`. Start from [templates/agent.md](templates/agent.md).

Keep `name` and `description` in every agent file. Everything else is tool specific:

| Key | OpenCode | Claude Code | Codex | Hermes |
| --- | --- | --- | --- | --- |
| `name` | Not used, the identity comes from the file name | Required | No agent format | No agent format |
| `description` | Required | Required | | |
| `mode: subagent` | Supported | Ignored | | |
| `permission: { edit, bash }` | Supported | Ignored | | |
| `tools`, `disallowedTools` | Ignored | Supported | | |
| `model` | `provider/model-id` | Alias or full model id | | |

Two consequences worth remembering:

- A restriction written only in frontmatter holds in one tool and silently disappears in the others. Always state the restriction in the body as well, since the body is the one part every tool reads.
- Do not hardcode a model. The model depends on what the person installing the agent has access to. For the validator the only rule that matters is using a different model from the one that produced the proposal.

Tools without an agent format still get the content: install the same guidance as a skill, or keep it in `rules/global.md`.

## Commands

Location: `commands/<name>.md`. The file name becomes the command name. Start from [templates/command.md](templates/command.md).

`description` is the only key worth keeping in the portable file. The body is the prompt, and both OpenCode and Claude Code expand `$ARGUMENTS` and the positional `$1`, `$2` placeholders.

| Key | Tool |
| --- | --- |
| `agent`, `subtask`, `model` | OpenCode |
| `argument-hint`, `allowed-tools`, `model`, `disable-model-invocation` | Claude Code |

Codex reads the files linked into `~/.codex/prompts` as plain prompts and does not document frontmatter for them, so write a body that stands on its own and never depend on a key to carry meaning.

## Hooks

Location: `hooks/<name>.sh`. Start from [templates/hook.sh](templates/hook.sh).

The contract is in [hooks/README.md](../hooks/README.md): read the payload from standard input, exit `0` to allow, exit `2` to block when the host supports it, write a short explanation to standard error, and never log the payload or the environment.

Hook events and payload shapes differ between tools, so the wiring lives in `adapters/`. Treat a hook as executable code that runs on every matching tool call: keep it small, make it fail closed, and match on file paths rather than on loose words, otherwise ordinary work gets blocked.

## Rules

Location: `rules/global.md`. `sync.sh` links this file as the global `AGENTS.md` and as the global rules file of each tool that has one.

Rules are standing instructions that apply to every project, so keep them short and behavioral. Anything about a specific project, a specific stack or a single workflow belongs in that project's own `AGENTS.md` or in a skill.

## Before opening a pull request

```bash
for file in sync.sh hooks/*.sh docs/templates/hook.sh; do bash -n "$file"; done
./sync.sh --dry-run
./sync.sh --check
```

Then confirm:

- The artifact states scope, non goals, acceptance criteria and validation.
- Acceptance criteria were defined before the implementation, not after.
- The behavior was tested in at least one tool that will actually load it.
- A second model reviewed important design or security decisions.
- The diff has no secrets, no machine specific paths and no unrelated changes.
