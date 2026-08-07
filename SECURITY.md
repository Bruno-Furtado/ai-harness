# Security

This is a public repository. Never commit API keys, credentials, private project data, personal data or unredacted logs.

## Reporting a vulnerability

Do not open a public issue. Use GitHub's [private security advisory](https://github.com/Bruno-Furtado/ai-harness/security/advisories/new) flow and include reproduction steps, impact and a suggested fix when possible.

## Hooks

A hook is executable code that runs on every matching tool call.

- Review a hook before enabling it, in the tool that will run it.
- Keep it small, make it fail closed and never log the payload.
- Test installer changes with `HOME=$(mktemp -d) ./harness install --yes --dry-run` before applying them.
