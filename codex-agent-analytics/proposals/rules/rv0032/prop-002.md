# Rules proposal prop-002

- local_run_id: local_run_20260406T150405Z_3032998
- rules_version: rv0032
- model: gpt-5.3-codex
- primary_task: t01
- affected_tasks: t01

## Focus
- problem: Task t01 fails with fail_group=none. The task passed with score 1.0 and the required deletions were correctly limited to captured cards/threads in `02_distill`. The only issue in trace evidence is avoidable tool-call noise: one invalid PAC tool invocation (`--help`) and a non-essential post-verification search before completion.
- solution_type: rules

## Primary task proposal
- `t01` fail_group=`none`
  - hypothesis: If rules explicitly forbid unsupported/meta tool probes and unnecessary post-verification calls, runs will reduce avoidable errors and token waste without changing task outcomes.
  - change: Add a short instruction block requiring agents to use only documented PAC tools, skip probe-style calls (such as passing help flags as tool names), and stop after scope verification and completion reporting instead of running extra exploratory commands.
  - files:
    - `codex-agent-analytics/rules_versions/rv0032/AGENTS.md`: Add 4-8 lines under execution discipline defining valid-tool usage and early-stop behavior after success checks.
  - rollback: Revert the added tool-hygiene block from the AGENTS rules file.
