from argparse import Namespace

from evolve_helpers import fail_group_counts_for_run, latest_run_for_runner, passed_count_for_run, runner_id_for_env, tasks_for_run
from evolve_modes.full_step_mode import run as run_full_step


def run(args) -> None:
    env = getattr(args, "env", "sandbox")
    rid = runner_id_for_env(env)
    n = max(1, int(args.n))
    no_improve_limit = max(1, int(args.no_improve_limit))
    no_improve = 0
    fixed_tasks = list(dict.fromkeys(getattr(args, "tasks", []) or []))
    task_scope = str(getattr(args, "task_scope", "all") or "all")
    use_fixed_affected = bool(fixed_tasks) and task_scope == "affected"
    remaining_tasks = fixed_tasks[:]

    print(f"AUTOPILOT: start n={n}, no_improve_limit={no_improve_limit}")
    if use_fixed_affected:
        print(f"AUTOPILOT: fixed-task affected mode enabled for tasks={fixed_tasks}")
    history: list[dict] = []

    for i in range(1, n + 1):
        if use_fixed_affected and not remaining_tasks:
            print("AUTOPILOT: all fixed tasks are already passed, stop")
            break

        before = latest_run_for_runner(rid)
        before_run_id = str(before.get("run_id")) if before else ""
        before_passed = passed_count_for_run(before_run_id) if before_run_id else 0
        if use_fixed_affected:
            step_tasks = remaining_tasks[:]
        elif fixed_tasks:
            step_tasks = fixed_tasks[:]
        else:
            step_tasks = []
        before_remaining = len(step_tasks)

        print(f"\n--- EVOLUTION STEP {i}/{n} ---")
        print(f"ENV: {env}")
        if use_fixed_affected:
            print(f"FIXED TASKS IN STEP: {step_tasks}")
        step_result = run_full_step(
            Namespace(
                env=env,
                hypothesis=args.hypothesis or "",
                tasks=step_tasks,
                task_scope=getattr(args, "task_scope", "all"),
                affected_from=getattr(args, "affected_from", "last-apply"),
                max_affected=getattr(args, "max_affected", 0),
                parallelism=getattr(args, "parallelism", 1),
            )
        )

        after = latest_run_for_runner(rid)
        if after is None:
            print("AUTOPILOT: no run after full-step, stop")
            break
        after_run_id = str(after.get("run_id"))
        after_passed = passed_count_for_run(after_run_id)
        delta = after_passed - before_passed

        resolved_this_step: list[str] = []
        if use_fixed_affected:
            by_task: dict[str, bool] = {}
            for row in tasks_for_run(after_run_id):
                tid = str(row.get("task_id") or "")
                if tid in step_tasks:
                    by_task[tid] = bool(row.get("passed"))
            next_remaining: list[str] = []
            for tid in step_tasks:
                if by_task.get(tid, False):
                    resolved_this_step.append(tid)
                else:
                    next_remaining.append(tid)
            remaining_tasks = next_remaining

            after_remaining = len(remaining_tasks)
            resolved_delta = before_remaining - after_remaining
        else:
            after_remaining = 0
            resolved_delta = delta

        entry = {
            "step": i,
            "before_run_id": before_run_id,
            "after_run_id": after_run_id,
            "before_passed": before_passed,
            "after_passed": after_passed,
            "delta": delta,
            "fail_groups": fail_group_counts_for_run(after_run_id),
        }
        blocked_tasks = []
        stopped_by_code_blocker = False
        if use_fixed_affected:
            entry["fixed_tasks_step"] = step_tasks
            entry["resolved_tasks"] = resolved_this_step
            entry["remaining_tasks"] = remaining_tasks[:]
            entry["resolved_delta"] = resolved_delta
        if isinstance(step_result, dict):
            entry["full_step_result"] = step_result
            blocked_raw_obj = step_result.get("blocked_tasks")
            blocked_raw = blocked_raw_obj if isinstance(blocked_raw_obj, list) else []
            blocked_tasks = [str(x) for x in blocked_raw if str(x)]
            entry["blocked_tasks"] = blocked_tasks
            stopped_by_code_blocker = bool(step_result.get("stopped_by_code_blocker"))
            entry["stopped_by_code_blocker"] = stopped_by_code_blocker
        history.append(entry)

        print("ITERATION RESULT:")
        if use_fixed_affected:
            print(
                f"STEP {i}: resolved {len(resolved_this_step)}/{before_remaining}, remaining {after_remaining}, run {after_run_id}"
            )
            if resolved_this_step:
                print(f"RESOLVED IN STEP: {resolved_this_step}")
            if remaining_tasks:
                if blocked_tasks:
                    remaining_tasks = [t for t in remaining_tasks if t not in blocked_tasks]
                    entry["remaining_tasks"] = remaining_tasks[:]
                    if remaining_tasks:
                        print(f"REMAINING FOR NEXT STEP: {remaining_tasks}")
                else:
                    print(f"REMAINING FOR NEXT STEP: {remaining_tasks}")
            if resolved_delta <= 0:
                no_improve += 1
            else:
                no_improve = 0
            if stopped_by_code_blocker and not remaining_tasks:
                print("AUTOPILOT: stop early because remaining fixed tasks are code-blocked")
                break
            if not remaining_tasks:
                print("AUTOPILOT: all fixed tasks passed")
                break
        else:
            print(
                f"STEP {i}: passed {before_passed} -> {after_passed} (delta {delta:+d}), run {after_run_id}"
            )
            if delta <= 0:
                no_improve += 1
            else:
                no_improve = 0

        if no_improve >= no_improve_limit:
            print(f"AUTOPILOT: stop early due to {no_improve} consecutive non-improving steps")
            break

    print("\n=== AUTOPILOT SUMMARY ===")
    if not history:
        print("No steps executed")
        return
    for h in history:
        if "fixed_tasks_step" in h:
            print(
                f"step={h['step']} run={h['after_run_id']} resolved={h.get('resolved_delta', 0)} remaining={h.get('remaining_tasks', [])} fails={h['fail_groups']}"
            )
        else:
            print(
                f"step={h['step']} run={h['after_run_id']} passed={h['before_passed']}->{h['after_passed']} delta={h['delta']:+d} fails={h['fail_groups']}"
            )
