## Summary

Describe the problem and the change.

## Acceptance criteria

- [ ] The requested behavior is explicit.
- [ ] Scope is limited to the request.
- [ ] Documentation is updated when needed.

## Validation

- [ ] `bash -n sync.sh hooks/*.sh` passes.
- [ ] `./sync.sh --dry-run` was reviewed.
- [ ] Relevant behavior was tested in the target tool.
- [ ] A second model reviewed important design or security decisions.

## Security

- [ ] No credentials, private data or machine-specific secrets are included.
- [ ] Hook and adapter changes were reviewed for unsafe execution.
