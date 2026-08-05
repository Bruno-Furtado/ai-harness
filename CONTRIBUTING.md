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

| Artifact | Where it goes | Start from |
| --- | --- | --- |
| Skill | `skills/<name>/SKILL.md`, folder name equal to `name` | [`docs/templates/SKILL.md`](docs/templates/SKILL.md) |
| Agent | `agents/<name>.md` | [`docs/templates/agent.md`](docs/templates/agent.md) |
| Command | `commands/<name>.md`, file name becomes the command | [`docs/templates/command.md`](docs/templates/command.md) |
| Hook | `hooks/<name>.sh` | [`docs/templates/hook.sh`](docs/templates/hook.sh) |
| Rule | `rules/global.md` | the file itself |

Tool-specific behavior goes in `adapters/`. Never add provider tokens, pinned models or machine-specific paths. [docs/authoring.md](docs/authoring.md) has the fields each format accepts and how to validate the result.

## Pull requests

Pull requests must explain the problem, the proposed change, acceptance criteria and verification performed. Do not merge directly to `main` except for an emergency correction by the repository owner.

Every pull request must carry an assignee, at least one label and the milestone of the version it targets. The `Pull request` workflow fails when one of them is missing. Labels are not decoration here: release notes are grouped by label through `.github/release.yml`, and an unlabeled change lands under "Other changes".

## Releases

Versions follow [Semantic Versioning](https://semver.org):

- **Patch** for a fix that changes no format.
- **Minor** for a new artifact or a newly supported tool.
- **Major** for a change that breaks an existing install.

Push the tag when the milestone is done, and the `Release` workflow publishes the notes:

```bash
git tag v0.1.0
git push origin v0.1.0
```
