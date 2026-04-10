# Harness engineering structure draft

Reference source:
- https://openai.com/ru-RU/index/harness-engineering/

Status:
- Canonical structure policy for this repo.
- Adopt incrementally; avoid structure bloat.

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
- New file creation is optional, not default: first prefer edits to existing AGENTS/includes/docs.
- Add a new harness file only when all are true:
  - evidence repeats across >=2 runs or >=2 tasks,
  - expected gain is generalizable (not task-specific),
  - rollback is one-step and clearly defined.
- Keep skeleton lean: create only the sections currently used by active work.
