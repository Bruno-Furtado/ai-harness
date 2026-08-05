---
name: agent-name
description: What this agent does and when to delegate to it.
# Tool-specific keys are optional and ignored elsewhere.
# OpenCode: mode, permission, model
# Claude Code: tools, disallowedTools, model
# See docs/authoring.md for the full table.
mode: subagent
permission:
  edit: deny
---

# Agent Name

## Scope

What this agent does.

## Non-goals

What it must not do. State any restriction here as well, because frontmatter restrictions only apply in the tool that defines them.

## Method

1. Inspect the relevant context.
2. Perform the focused work.
3. Report evidence and unresolved risks.

## Acceptance criteria

- Criterion one.
- Criterion two.

## Validation

List the checks that prove the criteria are met.
