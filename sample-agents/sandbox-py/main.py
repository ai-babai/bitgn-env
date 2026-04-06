import os
import textwrap
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from bitgn.harness_connect import HarnessServiceClientSync
from bitgn.harness_pb2 import StatusRequest, GetBenchmarkRequest, StartPlaygroundRequest, EvalPolicy, EndTrialRequest
from connectrpc.errors import ConnectError

from agent import run_agent

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from runlog_core import RunLogRegistry, resolve_run_mode

BITGN_URL = os.getenv("BENCHMARK_HOST") or "https://api.bitgn.com"

MODEL_ID = "gpt-4.1-2025-04-14"
MODEL_ID = os.getenv("MODEL_ID") or MODEL_ID
LOG_DIR = Path(os.getenv("BITGN_LOG_DIR") or (Path(__file__).resolve().parents[2] / "logs"))

CLI_RED = "\x1B[31m"
CLI_GREEN = "\x1B[32m"
CLI_CLR = "\x1B[0m"
CLI_BLUE = "\x1B[34m"


class JsonlLogger:
    def __init__(self, benchmark_id: str) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.path = LOG_DIR / f"{benchmark_id.replace('/', '-')}-{stamp}.jsonl"

    def log(self, event: str, **fields) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **fields,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=True, default=str) + "\n")


def _extract_expected(score_detail: list[str]) -> list[str]:
    expected: list[str] = []
    for item in score_detail:
        match = re.search(r"Expected:\s*(.+)$", item, flags=re.IGNORECASE)
        if match:
            expected.append(match.group(1).strip())
            continue
        match = re.search(r"expected\s+(.+?),\s*got", item, flags=re.IGNORECASE)
        if match:
            expected.append(match.group(1).strip())
            continue
        match = re.search(r"expected\s+(.+)$", item, flags=re.IGNORECASE)
        if match:
            expected.append(match.group(1).strip())
    return expected


def main() -> None:

    # optional task ids could be included as tasks to run, e.g. `python main.py task1 task2`
    task_filter = sys.argv[1:]


    scores = []
    benchmark_id = "bitgn/sandbox"
    logger = JsonlLogger(benchmark_id=benchmark_id)
    logger.log("run_started", benchmark_id=benchmark_id, model_id=MODEL_ID, bitgn_url=BITGN_URL)
    registry = RunLogRegistry(home=os.getenv("RUNLOG_HOME"))
    run_id = registry.start_run(
        project_id="bitgn-env",
        runner_id="sample-sandbox-py",
        benchmark_id=benchmark_id,
        run_mode=resolve_run_mode(task_filter),
        selected_task_ids=task_filter or None,
        raw_log_path=str(logger.path),
    )
    run_status = "ok"
    tasks_planned = 0
    tasks_finished = 0
    tasks_passed = 0
    tasks_failed = 0
    try:
        client = HarnessServiceClientSync(BITGN_URL)
        print("Connecting to BitGN", client.status(StatusRequest()))
        res = client.get_benchmark(GetBenchmarkRequest(benchmark_id=benchmark_id))
        print(f"{EvalPolicy.Name(res.policy)} benchmark: {res.benchmark_id} with {len(res.tasks)} tasks.\n{CLI_GREEN}{res.description}{CLI_CLR}")

        tasks_to_run = [t for t in res.tasks if not task_filter or t.task_id in task_filter]
        tasks_planned = len(tasks_to_run)


        for t in tasks_to_run:
            print(f"{'='*30} Starting task: {t.task_id} {'='*30}")
            logger.log("task_started", benchmark_id=benchmark_id, task_id=t.task_id)
            task_run_id = registry.start_task(
                run_id=run_id,
                task_id=t.task_id,
                raw_log_path=str(logger.path),
            )
            metrics: dict[str, int | None] = {
                "steps": 0,
                "llm_calls": 0,
                "tokens_prompt": None,
                "tokens_completion": None,
                "tokens_total": None,
            }

            trial = client.start_playground(StartPlaygroundRequest(
                benchmark_id=benchmark_id,
                task_id=t.task_id,
            ))

            print(f"{CLI_BLUE}{trial.instruction}{CLI_CLR}\n{'-'*80}")
            logger.log(
                "task_instruction",
                benchmark_id=benchmark_id,
                task_id=t.task_id,
                instruction=trial.instruction,
            )

            task_submission: dict[str, object] | None = None

            def on_agent_event(event: str, payload: dict[str, object]) -> None:
                nonlocal task_submission
                logger.log(event, benchmark_id=benchmark_id, task_id=t.task_id, **payload)
                if event == "agent_step" and payload.get("phase") == "reasoning":
                    metrics["steps"] = int(metrics["steps"] or 0) + 1
                if event == "prompt_sections" and "steering_prompt" in payload:
                    metrics["llm_calls"] = int(metrics["llm_calls"] or 0) + 1
                if event == "model_usage":
                    tp = payload.get("tokens_prompt")
                    tc = payload.get("tokens_completion")
                    if isinstance(tp, int):
                        metrics["tokens_prompt"] = int(metrics["tokens_prompt"] or 0) + tp
                    if isinstance(tc, int):
                        metrics["tokens_completion"] = int(metrics["tokens_completion"] or 0) + tc
                    if metrics["tokens_prompt"] is not None and metrics["tokens_completion"] is not None:
                        metrics["tokens_total"] = int(metrics["tokens_prompt"] or 0) + int(metrics["tokens_completion"] or 0)
                if event == "submission":
                    task_submission = payload

            try:
                run_agent(MODEL_ID, trial.harness_url, trial.instruction, event_hook=on_agent_event)
            except Exception as e:
                print(e)
                logger.log("agent_error", benchmark_id=benchmark_id, task_id=t.task_id, error=str(e))

            result = client.end_trial(EndTrialRequest(trial_id=trial.trial_id))


            if result.score >= 0:
                scores.append((t.task_id, result.score))

                style = CLI_GREEN if result.score == 1 else CLI_RED

                explain = textwrap.indent("\n".join(result.score_detail), "  ")
                print(f"\n{style}Score: {result.score:0.2f}\n{explain}\n{CLI_CLR}")
                logger.log(
                    "task_finished",
                    benchmark_id=benchmark_id,
                    task_id=t.task_id,
                    score=result.score,
                    success=result.score == 1,
                    score_detail=list(result.score_detail),
                    expected=_extract_expected(list(result.score_detail)),
                    submission=task_submission,
                )
                passed = result.score == 1
                registry.finish_task(
                    task_run_id=task_run_id,
                    status="ok",
                    passed=passed,
                    score=float(result.score),
                    steps=int(metrics["steps"] or 0),
                    llm_calls=int(metrics["llm_calls"] or 0),
                    tokens_prompt=metrics["tokens_prompt"] if isinstance(metrics["tokens_prompt"], int) else None,
                    tokens_completion=metrics["tokens_completion"] if isinstance(metrics["tokens_completion"], int) else None,
                    tokens_total=metrics["tokens_total"] if isinstance(metrics["tokens_total"], int) else None,
                    expected=_extract_expected(list(result.score_detail)),
                    score_detail=list(result.score_detail),
                    submission=task_submission,
                    raw_log_path=str(logger.path),
                )
                tasks_finished += 1
                if passed:
                    tasks_passed += 1
                else:
                    tasks_failed += 1

    except ConnectError as e:
        print(f"{e.code}: {e.message}")
        logger.log("run_error", benchmark_id=benchmark_id, error=str(e.message), code=str(e.code))
        run_status = "error"
    except KeyboardInterrupt:
        print(f"{CLI_RED}Interrupted{CLI_CLR}")
        logger.log("run_interrupted", benchmark_id=benchmark_id)
        run_status = "aborted"

    # print scores as table
    if scores:
        for tid, score in scores:
            style = CLI_GREEN if score == 1 else CLI_RED
            print(f"{tid}: {style}{score:0.2f}{CLI_CLR}")

        # print average
        total = sum([t[1] for t in scores]) / len(scores) * 100.0
        print(f"FINAL: {total:0.2f}%")
        logger.log(
            "run_finished",
            benchmark_id=benchmark_id,
            tasks_total=len(scores),
            tasks_success=sum(1 for _, s in scores if s == 1),
            avg_score=total,
            log_file=str(logger.path),
        )

    if run_status == "ok" and tasks_finished < tasks_planned:
        run_status = "partial"
    registry.finish_run(
        run_id=run_id,
        status=run_status,
        tasks_planned=tasks_planned,
        tasks_finished=tasks_finished,
        tasks_passed=tasks_passed,
        tasks_failed=tasks_failed,
        raw_log_path=str(logger.path),
    )


if __name__ == "__main__":
    main()
