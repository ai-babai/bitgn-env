from argparse import Namespace

from evolve_helpers import assess_fixability, fail_group_counts_for_run, latest_run_for_runner, passed_count_for_run, runner_id_for_env, selected_tasks_for_scope, tasks_for_run
from evolve_modes.analyze_mode import run as run_analyze
from evolve_modes.apply_prompts_mode import run as run_apply_prompts
from evolve_modes.propose_code_mode import run as run_propose_code
from evolve_modes.propose_prompts_mode import run as run_propose_prompts
from evolve_modes.solve_mode import run as run_solve


def run(args):
    env = getattr(args, "env", "sandbox")
    allow_blocked_prompt = bool(getattr(args, "allow_blocked_prompt", False))
    rid = runner_id_for_env(env)
    print(f"FULL STEP env={env} runner={rid}")
    before = latest_run_for_runner(rid)
    before_run_id = str(before.get("run_id")) if before else ""
    before_passed = passed_count_for_run(before_run_id) if before_run_id else 0
    before_fail_groups = fail_group_counts_for_run(before_run_id) if before_run_id else {}
    before_rows = tasks_for_run(before_run_id) if before_run_id else []
    before_failed_by_id = {str(r.get("task_id")): r for r in before_rows if not bool(r.get("passed")) and r.get("task_id")}

    explicit_tasks = list(getattr(args, "tasks", []) or [])
    if explicit_tasks:
        solve_tasks = explicit_tasks
        selection_meta = {"selection": "explicit", "selected_tasks": solve_tasks}
    else:
        solve_tasks, selection_meta = selected_tasks_for_scope(
            env=env,
            task_scope=str(getattr(args, "task_scope", "all") or "all"),
            affected_from=str(getattr(args, "affected_from", "last-apply") or "last-apply"),
            max_affected=int(getattr(args, "max_affected", 0) or 0),
        )

    assessment_rows: list[dict] = []
    blocked_tasks: list[str] = []
    if before:
        assess_task_ids: list[str]
        if solve_tasks:
            assess_task_ids = [str(t) for t in solve_tasks]
        else:
            assess_task_ids = [str(k) for k in before_failed_by_id.keys()]
        for tid in assess_task_ids:
            task_row = before_failed_by_id.get(tid)
            if task_row is None:
                continue
            a = assess_fixability(task_row, before, env)
            assessment_rows.append(a)
            if bool(a.get("blocker")):
                blocked_tasks.append(tid)
    blocked_set = set(blocked_tasks)

    if blocked_tasks:
        print(f"CODE BLOCKERS DETECTED: {blocked_tasks}")
    if allow_blocked_prompt and blocked_tasks:
        print("ALLOW BLOCKED PROMPT: enabled (will continue prompt evolution for blocked tasks)")

    if solve_tasks and blocked_set and not allow_blocked_prompt:
        solve_tasks_effective = [str(t) for t in solve_tasks if str(t) not in blocked_set]
    else:
        solve_tasks_effective = list(solve_tasks)

    prompt_scope_tasks: list[str] = []
    if solve_tasks_effective:
        prompt_scope_tasks = list(solve_tasks_effective)
    elif not solve_tasks and assessment_rows:
        prompt_scope_tasks = [
            str(a.get("task_id"))
            for a in assessment_rows
            if allow_blocked_prompt or not bool(a.get("blocker"))
        ]

    blocked_only = bool(assessment_rows) and not bool(prompt_scope_tasks)

    run_analyze(Namespace(env=env))

    if blocked_only and not allow_blocked_prompt:
        print("PROMPT EVOLUTION STOPPED: selected scope is code-blocked")
    else:
        run_propose_prompts(Namespace(env=env, tasks=prompt_scope_tasks))
        run_apply_prompts(Namespace(env=env, hypothesis=args.hypothesis or "", tasks=prompt_scope_tasks))

    code_scope_tasks = blocked_tasks or prompt_scope_tasks
    run_propose_code(Namespace(env=env, tasks=code_scope_tasks))

    print(f"TASK SELECTION: {selection_meta}")
    solve_parallelism = int(getattr(args, "parallelism", 1) or 1)
    solve_executed = True
    if solve_tasks and not solve_tasks_effective and not allow_blocked_prompt:
        print("SOLVE STOPPED: all selected tasks are code-blocked")
        solve_executed = False
    elif not solve_tasks and blocked_only and not allow_blocked_prompt:
        print("SOLVE STOPPED: latest failed scope is code-blocked")
        solve_executed = False
    else:
        run_solve(
            Namespace(
                env=env,
                sync=False,
                all=not bool(solve_tasks_effective),
                tasks=solve_tasks_effective,
                parallelism=solve_parallelism,
            )
        )

    if solve_executed:
        run_analyze(Namespace(env=env))

    after = latest_run_for_runner(rid)
    if after is None:
        print("FULL STEP: no run found after solve")
        return
    after_run_id = str(after.get("run_id"))
    after_passed = passed_count_for_run(after_run_id)
    after_fail_groups = fail_group_counts_for_run(after_run_id)

    result = {
        "before_run_id": before_run_id,
        "after_run_id": after_run_id,
        "before_passed": before_passed,
        "after_passed": after_passed,
        "delta": after_passed - before_passed,
        "before_fail_groups": before_fail_groups,
        "after_fail_groups": after_fail_groups,
        "selection": selection_meta,
        "blocked_tasks": blocked_tasks,
        "prompt_scope_tasks": prompt_scope_tasks,
        "solve_tasks_effective": solve_tasks_effective,
        "allow_blocked_prompt": allow_blocked_prompt,
        "stopped_by_code_blocker": blocked_only and not allow_blocked_prompt,
        "solve_executed": solve_executed,
    }

    print("\n=== FULL STEP RESULT ===")
    print(f"before run: {before_run_id or '-'}")
    print(f"after run:  {after_run_id}")
    print(f"passed: {before_passed} -> {after_passed} (delta {after_passed - before_passed:+d})")
    print(f"fail groups before: {before_fail_groups}")
    print(f"fail groups after:  {after_fail_groups}")
    if blocked_tasks:
        print(f"blocked tasks: {blocked_tasks}")
    print(f"solve executed: {solve_executed}")

    return result
