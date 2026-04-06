import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from runlog_core.registry import classify_fail

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
VERSIONS_DIR = PROMPTS_DIR / "versions"
ACTIVE_VERSION_FILE = PROMPTS_DIR / "active_version.txt"
CHANGELOG_PATH = Path(__file__).resolve().parent / "CHANGELOG_PROMPTS.jsonl"
CODE_PROPOSALS_PATH = Path(__file__).resolve().parent / "CODE_PROPOSALS.jsonl"
CODE_VERSION_FILE = Path(__file__).resolve().parent / "CODE_VERSION"

EVOLUTION_DIR = Path(__file__).resolve().parent / "evolution"
PROMPT_PROPOSALS_ROOT = EVOLUTION_DIR / "proposals" / "prompts"
CODE_PROPOSALS_ROOT = EVOLUTION_DIR / "proposals" / "code"
PROMPT_DECISIONS_ROOT = EVOLUTION_DIR / "decisions" / "prompts"
REPORTS_ROOT = EVOLUTION_DIR / "reports"
INDEX_PATH = EVOLUTION_DIR / "index.md"

RUNLOG_HOME = Path(os.getenv("RUNLOG_HOME") or "/Users/skif/develop/runlog-registry")
TASK_RUNS_PATH = RUNLOG_HOME / "index" / "task_runs.jsonl"
RUNS_PATH = RUNLOG_HOME / "index" / "runs.jsonl"
EXPERIENCE_PATH = Path(__file__).resolve().parent / "experience" / "records.jsonl"
MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_utc_to_moscow(ts: str | None) -> str:
    if not ts:
        return "-"
    raw = str(ts).strip()
    if not raw:
        return "-"
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return "-"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MOSCOW_TZ).isoformat(timespec="seconds")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    raw = str(ts).strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=True, default=str) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def active_prompt_version() -> str:
    if ACTIVE_VERSION_FILE.exists():
        raw = ACTIVE_VERSION_FILE.read_text(encoding="utf-8").strip()
        if raw:
            return raw
    return "p0001"


def active_code_version() -> str:
    if CODE_VERSION_FILE.exists():
        raw = CODE_VERSION_FILE.read_text(encoding="utf-8").strip()
        if raw:
            return raw
    return "c0001"


def load_prompt_pack(version: str) -> dict[str, Any]:
    path = VERSIONS_DIR / f"{version}.json"
    if not path.exists():
        raise FileNotFoundError(f"Prompt version not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def next_prompt_version() -> str:
    versions: list[int] = []
    if VERSIONS_DIR.exists():
        for p in VERSIONS_DIR.glob("p*.json"):
            stem = p.stem
            if len(stem) == 5 and stem.startswith("p") and stem[1:].isdigit():
                versions.append(int(stem[1:]))
    n = max(versions) + 1 if versions else 1
    return f"p{n:04d}"


def latest_run_for_runner(runner_id: str) -> dict[str, Any] | None:
    runs = load_jsonl(RUNS_PATH)
    for row in reversed(runs):
        if row.get("runner_id") == runner_id:
            return row
    return None


def runner_id_for_env(env: str) -> str:
    env_l = (env or "sandbox").strip().lower()
    if env_l == "pac1":
        return "codex-core-pac1"
    return "codex-core-sandbox"


def tasks_for_run(run_id: str) -> list[dict[str, Any]]:
    return [r for r in load_jsonl(TASK_RUNS_PATH) if r.get("run_id") == run_id]


def _changed_prompt_versions_for_env(env: str) -> set[str]:
    out: set[str] = set()
    for row in load_jsonl(CHANGELOG_PATH):
        if str(row.get("type", "")) != "prompt":
            continue
        if str(row.get("env", "sandbox")) != env:
            continue
        if not bool(row.get("changed", False)):
            continue
        ver = str(row.get("to_prompt_version", "")).strip()
        if ver:
            out.add(ver)
    return out


def _task_history(
    *,
    runner_id: str,
    benchmark_id: str,
    task_id: str,
    upto_ts: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    end_dt = _parse_iso(upto_ts)
    rows: list[dict[str, Any]] = []
    for row in load_jsonl(TASK_RUNS_PATH):
        if str(row.get("runner_id", "")) != runner_id:
            continue
        if str(row.get("benchmark_id", "")) != benchmark_id:
            continue
        if str(row.get("task_id", "")) != task_id:
            continue
        row_dt = _parse_iso(str(row.get("ts_start", "")))
        if end_dt is not None and row_dt is not None and row_dt > end_dt:
            continue
        rows.append(row)
    return rows[-max(1, limit) :]


def assess_fixability(task_row: dict[str, Any], run_row: dict[str, Any], env: str, history_limit: int = 6) -> dict[str, Any]:
    task_id = str(task_row.get("task_id", ""))
    runner_id = str(run_row.get("runner_id", ""))
    benchmark_id = str(run_row.get("benchmark_id", ""))
    fail_group = str(task_row.get("fail_group", "") or "other")

    hist = _task_history(
        runner_id=runner_id,
        benchmark_id=benchmark_id,
        task_id=task_id,
        upto_ts=str(task_row.get("ts_start", "")),
        limit=history_limit,
    )

    changed_versions = _changed_prompt_versions_for_env(env)
    attempts = len(hist)
    changed_prompt_attempts = sum(1 for r in hist if str(r.get("prompt_version", "")) in changed_versions)
    distinct_prompt_versions = len(set(str(r.get("prompt_version", "")) for r in hist if r.get("prompt_version")))
    recent_pass = any(bool(r.get("passed")) for r in hist[:-1])

    trailing_same_fail = 0
    for row in reversed(hist):
        if bool(row.get("passed")):
            break
        grp = str(row.get("fail_group", "") or "other")
        if grp != fail_group:
            break
        trailing_same_fail += 1

    prompt_potential = "medium"
    prompt_only = "maybe"
    code_need = "optional"
    blocker = False
    reason = "Mixed signals; continue with one prompt iteration and monitor fail-group shift."

    if fail_group == "no_answer":
        prompt_potential = "low"
        prompt_only = "no"
        code_need = "required"
        blocker = True
        reason = "No completion answer observed; typically a control-flow/error-path issue in runtime logic."
    elif fail_group in {"missing_file_write", "missing_file_delete", "missing_file_change"}:
        if trailing_same_fail >= 2 and changed_prompt_attempts >= 2:
            prompt_potential = "low"
            prompt_only = "no"
            code_need = "required"
            blocker = True
            reason = "Required workspace mutations keep missing across prompt updates; executor-level fix is needed."
        else:
            prompt_potential = "medium"
            prompt_only = "maybe"
            code_need = "optional"
            blocker = False
            reason = "Workflow mutation missing; prompt can help, but code checks may be needed if it repeats."
    elif fail_group == "outcome_mismatch":
        if trailing_same_fail >= 2 and changed_prompt_attempts >= 2:
            prompt_potential = "low"
            prompt_only = "no"
            code_need = "required"
            blocker = True
            reason = "Outcome enum mismatch persists across prompt updates; routing logic is likely the blocker."
        else:
            prompt_potential = "medium"
            prompt_only = "maybe"
            code_need = "optional"
            blocker = False
            reason = "Outcome policy mismatch may still improve with prompt constraints, then validate router behavior."
    elif fail_group in {"missing_ref", "answer_mismatch", "json_mismatch", "expected_got_mismatch"}:
        prompt_potential = "high"
        prompt_only = "yes"
        code_need = "not_needed"
        blocker = False
        reason = "Formatting/reference mismatch usually responds to prompt tightening without runtime changes."

    return {
        "task_id": task_id,
        "fail_group": fail_group,
        "attempts": attempts,
        "changed_prompt_attempts": changed_prompt_attempts,
        "distinct_prompt_versions": distinct_prompt_versions,
        "recent_pass": recent_pass,
        "trailing_same_fail": trailing_same_fail,
        "prompt_potential": prompt_potential,
        "prompt_only": prompt_only,
        "code_need": code_need,
        "blocker": blocker,
        "reason": reason,
    }


def passed_count_for_run(run_id: str) -> int:
    return sum(1 for t in tasks_for_run(run_id) if bool(t.get("passed")))


def fail_group_counts_for_run(run_id: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in tasks_for_run(run_id):
        if bool(t.get("passed")):
            continue
        details = t.get("score_detail")
        if not isinstance(details, list):
            details = []
        grp, _ = classify_fail([str(d) for d in details])
        key = grp or "other"
        counts[key] = counts.get(key, 0) + 1
    return counts


def selected_tasks_for_scope(
    env: str,
    task_scope: str,
    affected_from: str,
    max_affected: int,
) -> tuple[list[str], dict[str, object]]:
    rid = runner_id_for_env(env)
    run_row = latest_run_for_runner(rid)
    if run_row is None:
        return [], {"selection": "none", "reason": "no-run"}

    if task_scope == "all":
        return [], {"selection": "all", "reason": "task_scope=all", "run_id": run_row.get("run_id")}

    run_id = str(run_row.get("run_id"))
    rows = tasks_for_run(run_id)
    failed = [r for r in rows if not bool(r.get("passed"))]
    if not failed:
        return [], {"selection": "all", "reason": "no-failed-tasks", "run_id": run_id, "fallback_used": True}

    target_groups: set[str] = set()
    target_tags: set[str] = set()

    if affected_from == "last-apply":
        changes = load_jsonl(CHANGELOG_PATH)
        for ch in reversed(changes):
            if str(ch.get("type")) != "prompt":
                continue
            if str(ch.get("env", env)) != env:
                continue
            groups = ch.get("target_fail_groups", [])
            tags = ch.get("target_capability_tags", [])
            if isinstance(groups, list):
                target_groups.update(str(g) for g in groups if str(g))
            if isinstance(tags, list):
                target_tags.update(str(t) for t in tags if str(t))
            break

    selected: list[dict[str, Any]] = []
    if target_groups:
        selected = [r for r in failed if str(r.get("fail_group") or "") in target_groups]

    if not selected:
        selected = failed
        fallback = True
    else:
        fallback = False

    if max_affected > 0:
        selected = selected[:max_affected]

    task_ids = [str(r.get("task_id")) for r in selected if r.get("task_id")]
    meta = {
        "selection": "affected",
        "run_id": run_id,
        "affected_from": affected_from,
        "target_fail_groups": sorted(target_groups),
        "target_capability_tags": sorted(target_tags),
        "selected_tasks": task_ids,
        "fallback_used": fallback,
    }
    if not task_ids:
        return [], {"selection": "all", "reason": "affected-empty", "run_id": run_id, "fallback_used": True}
    return task_ids, meta


def latest_n_files(root: Path, n: int = 8) -> list[Path]:
    if not root.exists():
        return []
    files = [p for p in root.rglob("*.md") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:n]


def update_index() -> None:
    EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# Evolution index", ""]

    sections = [
        ("Latest prompt proposals", latest_n_files(PROMPT_PROPOSALS_ROOT)),
        ("Latest code proposals", latest_n_files(CODE_PROPOSALS_ROOT)),
        ("Latest prompt decisions", latest_n_files(PROMPT_DECISIONS_ROOT)),
        ("Latest reports", latest_n_files(REPORTS_ROOT)),
    ]

    for title, files in sections:
        lines.append(f"## {title}")
        if not files:
            lines.append("- (none)")
        else:
            for f in files:
                rel = f.relative_to(EVOLUTION_DIR)
                lines.append(f"- [{rel}]({rel.as_posix()})")
        lines.append("")

    write_text(INDEX_PATH, "\n".join(lines).strip() + "\n")


def next_prop_path(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    max_n = 0
    for p in root.glob("prop-*.md"):
        suffix = p.stem.replace("prop-", "")
        if suffix.isdigit():
            max_n = max(max_n, int(suffix))
    return root / f"prop-{max_n + 1:03d}.md"


def next_report_path() -> Path:
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    max_n = 0
    for p in REPORTS_ROOT.glob("r*.md"):
        stem = p.stem
        if len(stem) == 5 and stem.startswith("r") and stem[1:].isdigit():
            max_n = max(max_n, int(stem[1:]))
    return REPORTS_ROOT / f"r{max_n + 1:04d}.md"


def md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def failed_tasks_table(failed: list[dict[str, Any]]) -> str:
    lines = [
        "| Task | Fail group | Note |",
        "|---|---|---|",
    ]
    for t in failed:
        details = t.get("score_detail")
        if not isinstance(details, list):
            details = []
        fail_group, fail_note = classify_fail([str(d) for d in details])
        lines.append(
            f"| {md_escape(str(t.get('task_id', '')))} | {md_escape(fail_group or '-')} | {md_escape(fail_note or '-')} |"
        )
    return "\n".join(lines)


def fixability_table(assessments: list[dict[str, Any]]) -> str:
    lines = [
        "| Task | Prompt potential | Prompt-only likely | Code need | Blocker | Reason |",
        "|---|---|---|---|---|---|",
    ]
    for row in assessments:
        lines.append(
            "| "
            f"{md_escape(str(row.get('task_id', '')))} | "
            f"{md_escape(str(row.get('prompt_potential', '')))} | "
            f"{md_escape(str(row.get('prompt_only', '')))} | "
            f"{md_escape(str(row.get('code_need', '')))} | "
            f"{md_escape('yes' if bool(row.get('blocker')) else 'no')} | "
            f"{md_escape(str(row.get('reason', '')))} |"
        )
    return "\n".join(lines)


def extract_ref_from_detail(detail: str) -> str | None:
    m = re.search(r"'([^']+)'", detail)
    if m:
        return m.group(1)
    return None


def load_experience_records() -> list[dict[str, Any]]:
    return load_jsonl(EXPERIENCE_PATH)


def append_experience_record(row: dict[str, Any]) -> None:
    append_jsonl(EXPERIENCE_PATH, row)


def experience_candidates(fail_group: str, env: str, capability_tags: list[str]) -> list[dict[str, Any]]:
    env_l = (env or "").lower()
    need = set(capability_tags)
    out: list[dict[str, Any]] = []
    for rec in load_experience_records():
        if str(rec.get("failure_signature", "")) != fail_group:
            continue
        envs = rec.get("applies_to_envs", [])
        if isinstance(envs, list) and env_l not in [str(x).lower() for x in envs] and "all" not in [str(x).lower() for x in envs]:
            continue
        tags = set(str(x) for x in rec.get("capability_tags", []) if isinstance(x, str))
        if need and tags and need.isdisjoint(tags):
            continue
        out.append(rec)
    out.sort(key=lambda x: float(x.get("confidence", 0.0) or 0.0), reverse=True)
    return out
