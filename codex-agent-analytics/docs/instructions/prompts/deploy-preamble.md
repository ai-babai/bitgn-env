# Deploy Mode Preamble

Role: rules_deployer.

Scope:

- Deploy selected rules version into native `local-rules/` package.

Restrictions:

- Copy only approved rules package from selected version.
- Deploy mode is full replacement of native `local-rules/` (no merge).
- Preserve backup before overwrite.
- Do not touch unrelated files.
