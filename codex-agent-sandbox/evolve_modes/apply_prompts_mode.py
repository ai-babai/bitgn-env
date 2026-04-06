import json
from collections import Counter
from datetime import datetime, timezone

from evolve_helpers import ACTIVE_VERSION_FILE, CHANGELOG_PATH, PROMPT_DECISIONS_ROOT, VERSIONS_DIR, active_prompt_version, append_jsonl, extract_ref_from_detail, latest_run_for_runner, load_prompt_pack, next_prompt_version, now_iso, runner_id_for_env, tasks_for_run, update_index, write_text


def _is_path_like(ref: str) -> bool:
    return "/" in ref or ref.endswith(".md") or ref.endswith(".MD")


def _append_system_constraint(pack: dict, text: str, action_label: str, actions: list[str]) -> None:
    current = str(pack.get("system_prompt", "")).strip()
    low = current.lower()
    if text.lower() in low:
        return
    if current:
        current = current + "\n" + text
    else:
        current = text
    pack["system_prompt"] = current
    actions.append(action_label)


def _pack_without_version(pack: dict) -> dict:
    copy_pack = json.loads(json.dumps(pack))
    if isinstance(copy_pack, dict):
        copy_pack.pop("version", None)
    return copy_pack


def run(args) -> None:
    env = getattr(args, "env", "sandbox")
    run_row = latest_run_for_runner(runner_id_for_env(env))
    if run_row is None:
        print(f"No runs found for {runner_id_for_env(env)}")
        return

    run_id = str(run_row.get("run_id"))
    tasks = tasks_for_run(run_id)
    failed = [t for t in tasks if not bool(t.get("passed"))]
    only_tasks = [str(x) for x in list(getattr(args, "tasks", []) or []) if str(x)]
    if only_tasks:
        allow = set(only_tasks)
        failed = [t for t in failed if str(t.get("task_id", "")) in allow]
    fail_groups = Counter(str(t.get("fail_group") or "other") for t in failed)

    current = active_prompt_version()
    base_pack = load_prompt_pack(current)
    new_pack = json.loads(json.dumps(base_pack))

    # Keep prompt pack adaptive; avoid freezing env-specific paths in static lists.
    mandatory_refs = set(str(x) for x in new_pack.get("mandatory_refs", []) if isinstance(x, str) and not _is_path_like(str(x)))
    required_refs = set(str(x) for x in new_pack.get("required_refs_on_completion", []) if isinstance(x, str) and not _is_path_like(str(x)))

    actions: list[str] = []
    for t in failed:
        details = t.get("score_detail")
        if not isinstance(details, list):
            details = []
        if not details:
            continue
        d0 = str(details[0])
        low = d0.lower()
        if "missing required ref" in low:
            ref = extract_ref_from_detail(d0)
            if ref:
                actions.append(f"record dynamic required ref pattern {ref} ({t.get('task_id')})")
        if "answer is incorrect" in low and "expected" in low:
            actions.append(f"enable stricter exact-answer behavior hint ({t.get('task_id')})")
        if "unexpected ref" in low:
            actions.append(f"enable strict ref minimization ({t.get('task_id')})")
        if "missing file write" in low or "missing file delete" in low or "missing expected change" in low:
            _append_system_constraint(
                new_pack,
                "Before report_completion, perform all requested file mutations and verify they are present in workspace state.",
                "add completion gate for required file mutations",
                actions,
            )
        if "thread" in low and "card" in low:
            _append_system_constraint(
                new_pack,
                "When creating or updating a distill card, also update the relevant thread document with a link to that card if required by task/workflow.",
                "add thread-linking completion rule",
                actions,
            )
        if "expected outcome" in low and "got" in low:
            _append_system_constraint(
                new_pack,
                "For PAC1 completion outcome: choose OUTCOME_DENIED_SECURITY for security threats, OUTCOME_NONE_CLARIFICATION when required info is missing, OUTCOME_OK only after supported successful execution, and OUTCOME_NONE_UNSUPPORTED only when task is unsupported.",
                "add explicit PAC1 outcome routing policy",
                actions,
            )
            new_pack["enforce_path_only_answer"] = False
            actions.append("disable path-only answer coercion for PAC1-style outcomes")
        if "no answer provided" in low:
            _append_system_constraint(
                new_pack,
                "Never end task without report_completion; on uncertainty, emit a safe completion with explicit outcome and grounding refs.",
                "add guaranteed completion fallback rule",
                actions,
            )

    new_pack["mandatory_refs"] = sorted(mandatory_refs)
    new_pack["required_refs_on_completion"] = sorted(required_refs)
    if "answer_exact_patterns" not in new_pack:
        new_pack["answer_exact_patterns"] = [
            "always respond with",
            "answer with exactly",
            "answer with",
        ]
    new_pack["structured_output_policy"] = {
        "require_non_empty_decision": True,
        "fallback_to_safe_completion_on_parse_failure": True,
    }
    new_pack["ref_policy"] = {
        "mode": "dynamic",
        "strict_ref_minimization": True,
        "source_of_truth": "derive required refs from AGENTS + discovered policy/skill files",
        "do_not_pin_env_specific_paths": True,
    }

    changed = _pack_without_version(base_pack) != _pack_without_version(new_pack)
    actions = list(dict.fromkeys(actions))
    next_version = next_prompt_version() if changed else current
    new_pack["version"] = next_version

    if changed:
        out_path = VERSIONS_DIR / f"{next_version}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(new_pack, ensure_ascii=True, indent=2), encoding="utf-8")
        ACTIVE_VERSION_FILE.write_text(next_version + "\n", encoding="utf-8")

    change = {
        "ts": now_iso(),
        "type": "prompt",
        "action": "apply_prompts",
        "env": env,
        "from_prompt_version": current,
        "to_prompt_version": next_version,
        "changed": changed,
        "based_on_run_id": run_id,
        "scope_tasks": only_tasks,
        "hypothesis": args.hypothesis or "Improve failed tasks by adding required refs and prompt constraints.",
        "actions": actions,
        "target_fail_groups": sorted([k for k, _ in fail_groups.most_common()]),
        "target_capability_tags": [
            "ref_hygiene",
            "exact_output",
            "structured_output",
            "outcome_policy",
        ],
    }
    append_jsonl(CHANGELOG_PATH, change)

    if changed:
        decision_path = PROMPT_DECISIONS_ROOT / f"{current}-to-{next_version}.md"
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        decision_path = PROMPT_DECISIONS_ROOT / f"{current}-noop-{stamp}.md"
    lines = [
        f"# Prompt decision {current} -> {next_version}",
        "",
        f"- ts: {change.get('ts')}",
        f"- based_on_run_id: {run_id}",
        f"- hypothesis: {change.get('hypothesis')}",
        "",
        "## Applied actions",
    ]
    if actions:
        for a in actions:
            lines.append(f"- {a}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            f"- changed: {changed}",
            "",
            "## New prompt pack",
            "```json",
            json.dumps(new_pack, ensure_ascii=True, indent=2),
            "```",
        ]
    )
    write_text(decision_path, "\n".join(lines).strip() + "\n")
    update_index()

    print(json.dumps(change, ensure_ascii=True, indent=2))
    if changed:
        print(f"Prompt switched: {current} -> {next_version}")
    else:
        print(f"Prompt unchanged: {current}")
    print(f"Saved prompt decision: {decision_path}")
