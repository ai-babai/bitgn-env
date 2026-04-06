# Harness engineering structure draft

Reference source:
- https://openai.com/ru-RU/index/harness-engineering/

Status:
- Draft orientation only.
- Not a mandatory immediate implementation.

Target map for gradual growth:

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

Adoption policy for this repo:

- Add sections only when repeated analysis signals show that missing docs are blocking improvement.
- Prefer minimal deltas and keep each new section scoped to one active hypothesis.
- Maintain traceability from proposal -> new doc section -> measured run impact.
