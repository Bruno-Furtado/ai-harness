# Security

This is a public repository. Never commit API keys, credentials, private
project data, personal data or unredacted logs.

## Reporting a vulnerability

Do not open a public issue for a security vulnerability. Use GitHub's private
security advisory flow for this repository. Include reproduction steps, impact
and a suggested fix when possible.

## Safe changes

- Treat hooks as executable code and review them before enabling them.
- Keep examples free of real secrets.
- Use environment variables for local credentials.
- Prefer deny or ask permissions for tools that can edit files or run commands.
- Test sync changes with `--dry-run` before applying them.
- Review Codex hooks with `/hooks` before trusting them.
