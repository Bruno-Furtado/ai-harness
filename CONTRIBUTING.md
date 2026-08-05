# Contributing

Contributions are welcome through pull requests.

## Before opening a pull request

1. Create a branch from `main`.
2. Keep the change focused.
3. Define acceptance criteria in the change description.
4. Run the local checks from `AGENTS.md`.
5. Validate important behavior with a second model.
6. Review the final diff for secrets and unrelated changes.

## Adding an artifact

Read [docs/authoring.md](docs/authoring.md) for the format of each artifact and start from the matching file in `docs/templates/`. Keep skills under `skills/<name>/SKILL.md`, document tool-specific behavior in `adapters/`, and do not add provider tokens, pinned models or machine-specific paths.

## Pull requests

Pull requests must explain the problem, the proposed change, acceptance criteria and verification performed. Do not merge directly to `main` except for an emergency correction by the repository owner.
