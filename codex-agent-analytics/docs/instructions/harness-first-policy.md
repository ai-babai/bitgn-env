# Harness-First Policy

Primary principle: prefer harness/rules changes over code changes.

Rules:

- Default solution type is `rules`.
- Treat each analysis iteration as one focused hypothesis.
- Keep changes small and reversible.
- Avoid task-specific literals.
- Code proposal is exceptional, not normal flow.

Expected behavior:

- If uncertain, choose `optional` for code assessment.
- Propose one harness solution for the primary task.
- List potentially affected tasks only as validation scope.
