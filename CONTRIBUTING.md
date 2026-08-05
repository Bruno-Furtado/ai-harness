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

Every pull request must carry an assignee, at least one label and the milestone of the version it targets. The `Pull request` workflow fails when one of them is missing, so this is checked rather than assumed. Labels are not decoration here: release notes are grouped by label through `.github/release.yml`, and an unlabeled change lands under "Other changes". Create the label or the milestone that does not exist yet instead of leaving the field empty.

## Releases

Versions follow [Semantic Versioning](https://semver.org). For a configuration repository that means:

- **Patch** for a fix that changes no format and breaks no existing install.
- **Minor** for a new skill, agent, command, hook or rule, and for a new supported tool.
- **Major** for a change that breaks an existing install, such as moving where an artifact lives or renaming something `sync.sh` links.

A release is cut when the milestone is done. Pushing the tag is the only manual step, and every `v*` tag becomes a release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The `Release` workflow rejects a tag that is not semantic versioning, skips a release that already exists, treats `v1.0.0-rc.1` and similar as a prerelease, and generates the notes from the merged pull request labels. Do not publish a release by hand, or the notes stop matching the labels.

Every pull request carries an assignee, the labels that describe it and the milestone of the version it targets. Labels are not decoration here: release notes are grouped by label, so an unlabeled pull request lands under "Other changes".

## Releases

Versions follow [Semantic Versioning](https://semver.org). For a configuration repository that means:

- **Patch** for a fix that changes no format and breaks no existing install.
- **Minor** for a new skill, agent, command, hook or rule, and for a new supported tool.
- **Major** for a change that breaks an existing install, such as moving where an artifact lives or renaming something `sync.sh` links.

A release is cut by hand when the milestone is done. Push the tag and the `Release` workflow publishes the notes, generated from the merged pull request labels according to `.github/release.yml`:

```bash
git tag v0.1.0
git push origin v0.1.0
```
