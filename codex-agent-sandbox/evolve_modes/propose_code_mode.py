import json

from evolve_helpers import CODE_PROPOSALS_PATH, CODE_PROPOSALS_ROOT, active_code_version, append_jsonl, experience_candidates, failed_tasks_table, latest_run_for_runner, md_escape, next_prop_path, now_iso, runner_id_for_env, tasks_for_run, update_index, write_text


def _code_fix_for_failure(detail: str) -> tuple[str, str]:
    low = detail.lower()
    if "unexpected ref" in low:
        return (
            "normalize_completion_refs",
            "Add ref-normalizer before answer submission and drop AGENTS.MD when directive source differs.",
        )
    if "missing required ref" in low:
        return (
            "dynamic_required_ref_extractor",
            "Extract required ref path from AGENTS/policy text and enforce exact citation on completion.",
        )
    if "no answer provided" in low:
        return (
            "structured_output_failsafe",
            "Handle codex empty/invalid output with guaranteed fallback completion payload to avoid empty answers.",
        )
    if "missing expected change" in low or "missing file write" in low or "missing file delete" in low:
        return (
            "tool_action_completion_gate",
            "Enforce code-level completion gate requiring task-aligned file action before completion.",
        )
    if "answer is incorrect" in low:
        return (
            "answer_format_validator",
            "Add final answer validator for exact tokens required by task instructions.",
        )
    return (
        "runner_safety_improvement",
        "Tighten runtime checks and completion gating for this failure type.",
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
    proposal = {
        "ts": now_iso(),
        "run_id": run_id,
        "type": "code_proposal",
        "scope_tasks": only_tasks,
        "items": [],
    }

    for t in failed:
        details = t.get("score_detail")
        if not isinstance(details, list):
            details = []
        detail0 = str(details[0]) if details else "failed"
        proposal_key, proposal_text = _code_fix_for_failure(detail0)
        fail_group = str(t.get("fail_group") or "")
        candidates = experience_candidates(fail_group, env, _capability_tags_from_failure(detail0))
        if candidates:
            top = candidates[0]
            proposal_key = str(top.get("fix_kind", "code")) + ":experience"
            proposal_text = str(top.get("general_rule", proposal_text))
        proposal["items"].append(
            {
                "task_id": t.get("task_id"),
                "reason": detail0,
                "proposal_key": proposal_key,
                "proposal": proposal_text,
                "fail_group": fail_group,
            }
        )

    append_jsonl(CODE_PROPOSALS_PATH, proposal)

    code_version = str(run_row.get("code_version") or active_code_version())
    proposal_root = CODE_PROPOSALS_ROOT / code_version
    proposal_path = next_prop_path(proposal_root)
    lines = [
        f"# Code proposal {proposal_path.stem}",
        "",
        f"- code_version: {code_version}",
        f"- prompt_version: {run_row.get('prompt_version')}",
        f"- run_id: {run_id}",
        f"- benchmark: {run_row.get('benchmark_id')}",
        f"- ts: {proposal.get('ts')}",
        "",
        "## Failed tasks",
        failed_tasks_table(failed),
        "",
        "## Proposals (requires user approval)",
    ]
    items = proposal.get("items", [])
    if isinstance(items, list) and items:
        for item in items:
            if isinstance(item, dict):
                lines.append(
                    f"- `{md_escape(str(item.get('task_id')) )}`: `{md_escape(str(item.get('proposal_key')) )}`"
                )
                lines.append(
                    f"  - fail: {md_escape(str(item.get('reason')) )}"
                )
                lines.append(
                    f"  - code fix: {md_escape(str(item.get('proposal')))}"
                )
    else:
        lines.append("- No code proposals")

    write_text(proposal_path, "\n".join(lines).strip() + "\n")
    update_index()

    print(json.dumps(proposal, ensure_ascii=True, indent=2))
    print(f"Saved to {CODE_PROPOSALS_PATH}")
    print(f"Saved code proposal: {proposal_path}")
