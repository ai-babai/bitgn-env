import json
import re
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.1.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _duration_sec(ts_start: str, ts_end: str) -> float:
    started = datetime.fromisoformat(ts_start)
    ended = datetime.fromisoformat(ts_end)
    return max(0.0, (ended - started).total_seconds())


def resolve_run_mode(task_filter: list[str]) -> str:
    if not task_filter:
        return "all"
    if len(task_filter) == 1:
        return "single"
    return "subset"


def classify_fail(score_detail: list[str]) -> tuple[str, str]:
    if not score_detail:
        return "", ""
    text = " | ".join(score_detail)
    lower = text.lower()

    if "expected outcome" in lower and "got" in lower:
        return "outcome_mismatch", score_detail[0]
    if "missing required ref" in lower:
        return "missing_ref", score_detail[0]
    if "missing file write" in lower:
        return "missing_file_write", score_detail[0]
    if "missing file delete" in lower:
        return "missing_file_delete", score_detail[0]
    if "missing expected change" in lower:
        return "missing_file_change", score_detail[0]
    if "answer is incorrect" in lower:
        return "answer_mismatch", score_detail[0]
    if "json mismatch" in lower:
        return "json_mismatch", score_detail[0]
    if "no answer provided" in lower:
        return "no_answer", score_detail[0]
    if re.search(r"expected\s+.+?\s*,\s*got", lower):
        return "expected_got_mismatch", score_detail[0]
    return "other", score_detail[0]


@dataclass
class _RunState:
    run_id: str
    ts_start: str
    project_id: str
    runner_id: str
    benchmark_id: str
    run_mode: str
    selected_task_ids: list[str] | None
    raw_log_path: str | None
    prompt_version: str | None
    code_version: str | None
    pipeline_mode: str | None


@dataclass
class _TaskState:
    task_run_id: str
    run_id: str
    ts_start: str
    project_id: str
    runner_id: str
    benchmark_id: str
    prompt_version: str | None
    code_version: str | None
    pipeline_mode: str | None
    task_id: str
    raw_log_path: str | None


class RunLogRegistry:
    def __init__(self, home: str | None = None) -> None:
        default_home = "/Users/skif/develop/runlog-registry"
        self.home = Path(home or default_home)
        self.index_dir = self.home / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.runs_file = self.index_dir / "runs.jsonl"
        self.tasks_file = self.index_dir / "task_runs.jsonl"
        self._runs: dict[str, _RunState] = {}
        self._tasks: dict[str, _TaskState] = {}
        self._lock = threading.Lock()

    def _append(self, path: Path, row: dict[str, Any]) -> None:
        line = json.dumps(row, ensure_ascii=True, default=str) + "\n"
        with self._lock:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line)

    def start_run(
        self,
        *,
        project_id: str,
        runner_id: str,
        benchmark_id: str,
        run_mode: str,
        selected_task_ids: list[str] | None,
        raw_log_path: str | None,
        prompt_version: str | None = None,
        code_version: str | None = None,
        pipeline_mode: str | None = None,
    ) -> str:
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
        with self._lock:
            self._runs[run_id] = _RunState(
                run_id=run_id,
                ts_start=_now_iso(),
                project_id=project_id,
                runner_id=runner_id,
                benchmark_id=benchmark_id,
                run_mode=run_mode,
                selected_task_ids=selected_task_ids,
                raw_log_path=raw_log_path,
                prompt_version=prompt_version,
                code_version=code_version,
                pipeline_mode=pipeline_mode,
            )
        return run_id

    def start_task(
        self,
        *,
        run_id: str,
        task_id: str,
        raw_log_path: str | None = None,
    ) -> str:
        task_run_id = f"taskrun_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
        with self._lock:
            run = self._runs[run_id]
            self._tasks[task_run_id] = _TaskState(
                task_run_id=task_run_id,
                run_id=run_id,
                ts_start=_now_iso(),
                project_id=run.project_id,
                runner_id=run.runner_id,
                benchmark_id=run.benchmark_id,
                prompt_version=run.prompt_version,
                code_version=run.code_version,
                pipeline_mode=run.pipeline_mode,
                task_id=task_id,
                raw_log_path=raw_log_path or run.raw_log_path,
            )
        return task_run_id

    def finish_task(
        self,
        *,
        task_run_id: str,
        status: str,
        passed: bool,
        score: float | None,
        steps: int,
        llm_calls: int,
        tokens_prompt: int | None,
        tokens_completion: int | None,
        tokens_total: int | None,
        expected: list[str],
        score_detail: list[str],
        submission: dict[str, Any] | None,
        raw_log_path: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            state = self._tasks.pop(task_run_id)
        ts_end = _now_iso()
        fail_group, fail_note = classify_fail(score_detail if not passed else [])
        row = {
            "schema_version": SCHEMA_VERSION,
            "task_run_id": state.task_run_id,
            "run_id": state.run_id,
            "project_id": state.project_id,
            "runner_id": state.runner_id,
            "benchmark_id": state.benchmark_id,
            "prompt_version": state.prompt_version,
            "code_version": state.code_version,
            "pipeline_mode": state.pipeline_mode,
            "task_id": state.task_id,
            "ts_start": state.ts_start,
            "ts_end": ts_end,
            "duration_sec": _duration_sec(state.ts_start, ts_end),
            "status": status,
            "passed": passed,
            "score": score,
            "steps": steps,
            "llm_calls": llm_calls,
            "tokens_prompt": tokens_prompt,
            "tokens_completion": tokens_completion,
            "tokens_total": tokens_total,
            "expected": expected,
            "score_detail": score_detail,
            "submission": submission,
            "fail_group": fail_group,
            "fail_note": fail_note,
            "raw_log_path": raw_log_path or state.raw_log_path,
        }
        self._append(self.tasks_file, row)
        return row

    def finish_run(
        self,
        *,
        run_id: str,
        status: str,
        tasks_planned: int,
        tasks_finished: int,
        tasks_passed: int,
        tasks_failed: int,
        raw_log_path: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            state = self._runs.pop(run_id)
        ts_end = _now_iso()
        row = {
            "schema_version": SCHEMA_VERSION,
            "run_id": state.run_id,
            "project_id": state.project_id,
            "runner_id": state.runner_id,
            "benchmark_id": state.benchmark_id,
            "prompt_version": state.prompt_version,
            "code_version": state.code_version,
            "pipeline_mode": state.pipeline_mode,
            "run_mode": state.run_mode,
            "selected_task_ids": state.selected_task_ids,
            "ts_start": state.ts_start,
            "ts_end": ts_end,
            "duration_sec": _duration_sec(state.ts_start, ts_end),
            "tasks_planned": tasks_planned,
            "tasks_finished": tasks_finished,
            "tasks_passed": tasks_passed,
            "tasks_failed": tasks_failed,
            "status": status,
            "raw_log_path": raw_log_path or state.raw_log_path,
        }
        self._append(self.runs_file, row)
        return row
