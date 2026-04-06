from runlog_core.render import render_task_table

from evolve_helpers import RUNLOG_HOME, assess_fixability, failed_tasks_table, fixability_table, iso_utc_to_moscow, latest_run_for_runner, next_report_path, runner_id_for_env, tasks_for_run, update_index, write_text


def run(_) -> None:
    env = getattr(_, "env", "sandbox")
    run_row = latest_run_for_runner(runner_id_for_env(env))
    if run_row is None:
        print(f"No runs found for {runner_id_for_env(env)}")
        return

    run_id = str(run_row.get("run_id"))
    tasks = tasks_for_run(run_id)
    failed = [t for t in tasks if not bool(t.get("passed"))]
    assessments = [assess_fixability(t, run_row, env) for t in failed]
    blockers = sum(1 for a in assessments if bool(a.get("blocker")))

    print(f"Latest run: {run_id}")
    print(f"Started (UTC): {run_row.get('ts_start', '-')}")
    print(f"Started (MSK): {iso_utc_to_moscow(run_row.get('ts_start'))}")
    print(f"Tasks total: {len(tasks)}, failed: {len(failed)}")
    if failed:
        print(f"Fixability blockers: {blockers}/{len(failed)}")
    print("\nTable:")
    header = (
        f"Run: {run_id} | runner: {run_row.get('runner_id')} | "
        f"benchmark: {run_row.get('benchmark_id')} | mode: {run_row.get('run_mode')}"
    )
    table_text = header + "\n\n" + render_task_table(tasks)
    print(table_text)

    report_path = next_report_path()
    lines = [
        f"# Analyze run {run_id}",
        "",
        f"- runner: {run_row.get('runner_id')}",
        f"- benchmark: {run_row.get('benchmark_id')}",
        f"- run_id: {run_id}",
        f"- ts_start_utc: {run_row.get('ts_start', '-')}",
        f"- ts_start_msk: {iso_utc_to_moscow(run_row.get('ts_start'))}",
        f"- ts_end_utc: {run_row.get('ts_end', '-')}",
        f"- ts_end_msk: {iso_utc_to_moscow(run_row.get('ts_end'))}",
        f"- prompt_version: {run_row.get('prompt_version')}",
        f"- code_version: {run_row.get('code_version')}",
        f"- mode: {run_row.get('pipeline_mode')}",
        f"- tasks total: {len(tasks)}",
        f"- failed: {len(failed)}",
        f"- blockers: {blockers}/{len(failed) if failed else 0}",
        "",
        "## Failed tasks",
        failed_tasks_table(failed),
        "",
        "## Fixability assessment",
        fixability_table(assessments) if assessments else "- none",
        "",
        "## Console summary",
        "```text",
        table_text,
        "```",
    ]
    write_text(report_path, "\n".join(lines).strip() + "\n")
    update_index()
    print(f"\nSaved report: {report_path}")
