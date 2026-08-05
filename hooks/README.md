# Hooks

Hooks are small guard scripts. They must fail closed for unsafe input and must not print secret values.

## Contract

- Read the tool event payload from standard input.
- Exit `0` to allow the operation.
- Exit `2` to block or reject the operation when the host supports that contract.
- Write a short, safe explanation to standard error.
- Never log the full payload or environment.

`protect-secrets.sh` blocks obvious references to `.env`, credential, secret, certificate and key files. It is a guard, not a complete security boundary.

Hook events and payloads differ between tools. The adapters document the host-specific wiring, and each hook must be reviewed in the tool that will run it before being enabled.
