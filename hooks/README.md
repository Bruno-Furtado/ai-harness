# Hooks

Hooks are small guard scripts. They must fail closed for unsafe input and must not print secret values.

## Wiring

A hook is executable code, and no tool accepts one by symlink alone, so `harness` cannot finish this part for you. Each tool is wired once:

| Tool | How |
| --- | --- |
| Claude Code | Paste [adapters/claude/settings.snippet.json](../adapters/claude/settings.snippet.json) into `~/.claude/settings.json`, replacing the placeholder with the absolute path of this clone |
| Codex | Same, using [adapters/codex/hooks.json](../adapters/codex/hooks.json) |
| OpenCode | Already done. `harness` installs [the plugin](../adapters/opencode/plugins/harness-hooks.ts), which calls the same script |
| Hermes | No hook mechanism |

Editing `settings.json` is left to you on purpose: it is a file you maintain by hand, and an installer rewriting it is how configuration gets lost.

## Contract

- Read the tool event payload from standard input.
- Exit `0` to allow the operation.
- Exit `2` to block or reject the operation when the host supports that contract.
- Write a short, safe explanation to standard error.
- Never log the full payload or environment.

`protect-secrets.sh` blocks obvious references to `.env`, credential, secret, certificate and key files. It is a guard, not a complete security boundary.

Hook events and payloads differ between tools. The adapters document the host-specific wiring, and each hook must be reviewed in the tool that will run it before being enabled.
