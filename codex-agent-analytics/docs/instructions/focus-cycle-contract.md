# Focus Cycle Contract

One analysis run should yield one focus cycle.

Required elements:

- `primary_task_id`: single main task.
- `problem`: concise, evidence-backed failure statement.
- `solution_type`: `rules` or `code_blocking`.
- `affected_tasks`: tasks likely impacted by the same fix.

Constraints:

- `affected_tasks[0]` must be `primary_task_id`.
- Do not generate separate independent solutions per task in one run.
- Verification should be explicit for primary task first.
