import json

from evolve_helpers import PROMPT_PROPOSALS_ROOT, active_prompt_version, experience_candidates, failed_tasks_table, latest_run_for_runner, load_prompt_pack, md_escape, next_prop_path, now_iso, runner_id_for_env, tasks_for_run, update_index, write_text


def _prompt_fix_for_failure(detail_text: str) -> tuple[str, str]:
    low = detail_text.lower()
    if "unexpected ref" in low:
        return (
            "strict_ref_minimization",
            "Do not include AGENTS.MD in final refs when answer directive comes from another file.",
        )
    if "missing required ref" in low:
        return (
            "dynamic_policy_ref_grounding",
            "Derive required policy/skill ref from AGENTS instruction (scan folder -> read policy -> cite that exact path).",
        )
    if "no answer provided" in low:
        return (
            "structured_output_reliability",
            "Require deterministic fallback decision with report_completion when model output is empty/unparseable.",
        )
    if "answer is incorrect" in low:
        return (
            "exact_answer_compliance",
            "Prioritize exact-answer directive patterns and suppress free-form completion text.",
        )
    if "missing expected change" in low or "missing file write" in low or "missing file delete" in low:
        return (
            "action_before_completion",
            "Require one concrete tool action matching task intent before report_completion.",
        )
    return (
        "general_prompt_tightening",
        "Tighten planning and completion checklist for this failure pattern.",
    )


def _capability_tags_from_failure(detail_text: str) -> list[str]:
    low = detail_text.lower()
    tags: list[str] = []
    if "ref" in low:
        tags.append("ref_hygiene")
    if "answer" in low or "precise" in low:
        tags.append("exact_output")
    if "no answer" in low:
        tags.append("structured_output")
    if "outcome" in low:
        tags.append("outcome_policy")
    return tags


def run(_) -> None:
    env = getattr(_, "env", "sandbox")
    run_row = latest_run_for_runner(runner_id_for_env(env))
    if run_row is None:
        print(f"No runs found for {runner_id_for_env(env)}")
        return

    run_id = str(run_row.get("run_id"))
    tasks = tasks_for_run(run_id)
    failed = [t for t in tasks if not bool(t.get("passed"))]
    only_tasks = [str(x) for x in list(getattr(_, "tasks", []) or []) if str(x)]
    if only_tasks:
        allow = set(only_tasks)
        failed = [t for t in failed if str(t.get("task_id", "")) in allow]
    current = active_prompt_version()
    pack = load_prompt_pack(current)

    proposal = {
        "ts": now_iso(),
        "from_prompt_version": current,
        "based_on_run_id": run_id,
        "scope_tasks": only_tasks,
        "failed_tasks": [t.get("task_id") for t in failed],
        "suggestions": [],
    }

    for t in failed:
        task_id = str(t.get("task_id"))
        details = t.get("score_detail")
        if not isinstance(details, list):
            details = []
        detail0 = str(details[0]) if details else ""
        action, fix = _prompt_fix_for_failure(detail0)
        fail_group = str(t.get("fail_group") or "")
        candidates = experience_candidates(fail_group, env, _capability_tags_from_failure(detail0))
        if candidates:
            top = candidates[0]
            action = str(top.get("fix_kind", action)) + ":experience"
            fix = str(top.get("general_rule", fix))
        proposal["suggestions"].append(
            {
                "task_id": task_id,
                "action": action,
                "reason": detail0 if detail0 else "failed",
                "prompt_fix": fix,
                "fail_group": fail_group,
            }
        )

    proposal_root = PROMPT_PROPOSALS_ROOT / current
    proposal_path = next_prop_path(proposal_root)
    lines = [
        f"# Prompt proposal {proposal_path.stem}",
        "",
        f"- from prompt_version: {current}",
        f"- code_version: {run_row.get('code_version')}",
        f"- run_id: {run_id}",
        f"- benchmark: {run_row.get('benchmark_id')}",
        f"- ts: {proposal.get('ts')}",
        "",
        "## Failed tasks",
        failed_tasks_table(failed),
        "",
        "## Suggestions",
    ]

    suggestions = proposal.get("suggestions", [])
    if isinstance(suggestions, list) and suggestions:
        for item in suggestions:
            if isinstance(item, dict):
                lines.append(
                    f"- `{md_escape(str(item.get('task_id')) )}`: `{md_escape(str(item.get('action')) )}`"
                )
                lines.append(
                    f"  - fail: {md_escape(str(item.get('reason')))}"
                )
                lines.append(
                    f"  - prompt fix: {md_escape(str(item.get('prompt_fix')))}"
                )
    else:
        lines.append("- No prompt suggestions")

    lines.extend(
        [
            "",
            "## Current prompt pack",
            "```json",
            json.dumps(pack, ensure_ascii=True, indent=2),
            "```",
        ]
    )
    write_text(proposal_path, "\n".join(lines).strip() + "\n")
    update_index()

    print(json.dumps({"current_prompt_pack": pack, "proposal": proposal}, ensure_ascii=True, indent=2))
    print(f"Saved prompt proposal: {proposal_path}")
