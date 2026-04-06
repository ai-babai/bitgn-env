# codex-agent-analytics architecture

This module is an analysis-only companion for `codex-agent-native`.

## Boundary

- Read artifacts from `../codex-agent-native/runs/`.
- Generate analysis and proposals.
- Do not mutate solver runtime modules automatically.

## Draft harness map (best-practice reference)

The following structure is a draft reference from harness-engineering best practices.
It is not mandatory to fully implement now.
Use it as a growth map for service files and governance docs.

```text
AGENTS.md
ARCHITECTURE.md
docs/
  design-docs/
    index.md
    core-beliefs.md
    ...
  exec-plans/
    active/
    completed/
    tech-debt-tracker.md
  generated/
    db-schema.md
  product-specs/
    index.md
    new-user-onboarding.md
    ...
  references/
    design-system-reference-llms.txt
    nixpacks-llms.txt
    uv-llms.txt
    ...
  DESIGN.md
  FRONTEND.md
  PLANS.md
  PRODUCT_SENSE.md
  QUALITY_SCORE.md
  RELIABILITY.md
  SECURITY.md
```
