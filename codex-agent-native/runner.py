# pyright: reportMissingImports=false

import json
import os
import re
import select
import subprocess
import sys
import time
import threading
from argparse import ArgumentParser
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bitgn.harness_connect import HarnessServiceClientSync
from bitgn.harness_pb2 import (
    EndTrialRequest,
    EvalPolicy,
    GetBenchmarkRequest,
    StartRunRequest,
    StartPlaygroundRequest,
    StartTrialRequest,
    StatusRequest,
    SubmitRunRequest,
)
from bitgn.vm.mini_pb2 import ReadRequest
from bitgn.vm.pcm_pb2 import ReadRequest as PcmReadRequest
from connectrpc.errors import ConnectError
from google.protobuf.json_format import MessageToDict
from urllib import error as urlerror
from urllib import request as urlrequest

from tool_gateway import ToolGateway
import harness_seed
from workspace import create_task_workspace

BITGN_URL = os.getenv("BENCHMARK_HOST") or "https://api.bitgn.com"
BENCHMARK_ID = os.getenv("BENCHMARK_ID") or "bitgn/sandbox"
AGENT_ENV = (os.getenv("AGENT_ENV") or "").strip().lower()
CODEX_MODEL = os.getenv("CODEX_MODEL") or "gpt-5.3-codex"
CODEX_PROFILE = (os.getenv("CODEX_PROFILE") or "").strip()
CODEX_BACKEND = (os.getenv("CODEX_BACKEND") or "omniroute").strip().lower()
BITGN_API_KEY = (os.getenv("BITGN_API_KEY") or "").strip()
BITGN_RUN_NAME = (os.getenv("BITGN_RUN_NAME") or f"codex-native {CODEX_MODEL}").strip()
NATIVE_SESSION_TIMEOUT_SEC = int(os.getenv("NATIVE_SESSION_TIMEOUT_SEC") or 420)
NATIVE_RUNS_DIR = os.getenv("NATIVE_RUNS_DIR") or str(
    Path(__file__).resolve().parent / "runs"
)
NATIVE_LOG_LEVEL = (os.getenv("NATIVE_LOG_LEVEL") or "info").strip().lower()
NATIVE_PARALLELISM = max(1, int(os.getenv("NATIVE_PARALLELISM") or 2))
BITGN_FEEDBACK_MODE = (os.getenv("BITGN_FEEDBACK_MODE") or "strict").strip().lower()
MANIFEST_LOCK = threading.Lock()


def _feedback_optional() -> bool:
    return BITGN_FEEDBACK_MODE in {"optional", "best_effort", "soft"}


def _prepare_leaderboard_trials(
    *, client: HarnessServiceClientSync, task_ids: list[str]
) -> tuple[dict[str, dict[str, str]], str | None]:
    if not BITGN_API_KEY:
        return {}, None
    ordered_task_ids = list(dict.fromkeys(task_ids))
    requested = set(ordered_task_ids)
    run_req = StartRunRequest(
        benchmark_id=BENCHMARK_ID,
        name=BITGN_RUN_NAME or f"codex-native {CODEX_MODEL}",
    )
    if hasattr(run_req, "api_key"):
        setattr(run_req, "api_key", BITGN_API_KEY)
        run = client.start_run(run_req)
        run_id = str(run.run_id)
        trial_ids = [str(tid) for tid in run.trial_ids]
    else:
        run_id, trial_ids = _start_run_via_connect_json(
            benchmark_id=BENCHMARK_ID,
            name=BITGN_RUN_NAME or f"codex-native {CODEX_MODEL}",
            api_key=BITGN_API_KEY,
        )
        _cli(
            "[LEADERBOARD] Using Connect JSON fallback for StartRun "
            "(SDK has no api_key field)."
        )

    seeds: dict[str, dict[str, str]] = {}
    for trial_id in trial_ids:
        trial = client.start_trial(StartTrialRequest(trial_id=trial_id))
        task_id = str(trial.task_id)
        if requested and task_id not in requested:
            continue
        if task_id in seeds:
            continue
        seeds[task_id] = {
            "trial_id": str(trial.trial_id),
            "task_id": task_id,
            "instruction": str(trial.instruction),
            "harness_url": str(trial.harness_url),
        }
        if len(seeds) == len(requested):
            break
    missing = [task_id for task_id in ordered_task_ids if task_id not in seeds]
    if missing:
        _cli(
            "[LEADERBOARD] Could not prepare trials for tasks: "
            + ", ".join(missing)
            + ". Falling back to playground mode."
        )
        try:
            client.submit_run(SubmitRunRequest(run_id=run_id, force=True))
        except ConnectError:
            pass
        return {}, None
    _cli(f"[LEADERBOARD] Prepared run_id={run_id} tasks={len(seeds)}")
    return seeds, run_id


def _start_run_via_connect_json(
    *, benchmark_id: str, name: str, api_key: str
) -> tuple[str, list[str]]:
    endpoint = (
        f"{BITGN_URL.rstrip('/')}/bitgn.harness.HarnessService/StartRun"
    )
    payload = {
        "benchmarkId": benchmark_id,
        "name": name,
        "apiKey": api_key,
    }
    req = urlrequest.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Connect-Protocol-Version": "1",
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except urlerror.HTTPError as exc:
        raise RuntimeError(
            f"StartRun fallback failed: HTTP {exc.code}"
        ) from exc
    data = json.loads(body)
    run_id = str(data.get("runId", "")).strip()
    trial_ids = [str(x).strip() for x in data.get("trialIds", []) if str(x).strip()]
    if not run_id or not trial_ids:
        raise RuntimeError("StartRun fallback returned empty runId/trialIds")
    return run_id, trial_ids


def _cli(msg: str) -> None:
    print(msg, flush=True)


def _stage(name: str, detail: str = "", task_id: str = "") -> None:
    prefix = f"[{task_id}] " if task_id else ""
    if detail:
        _cli(f"{prefix}[STAGE] {name}: {detail}")
    else:
        _cli(f"{prefix}[STAGE] {name}")


def _extract_tool_name(command: str) -> str:
    m = re.search(r"runtime_tools\.py\s+([a-z_]+)", command)
    if not m:
        return ""
    return str(m.group(1) or "").strip()


def _render_codex_event(evt: dict[str, Any]) -> str | None:
    t = str(evt.get("type", ""))
    if t == "turn.started":
        return "[CODEX] turn started"
    if t == "turn.completed":
        usage = evt.get("usage")
        if isinstance(usage, dict):
            inp = int(usage.get("input_tokens", 0) or 0)
            out = int(usage.get("output_tokens", 0) or 0)
            return (
                f"[CODEX] turn completed tokens: in={inp} out={out} total={inp + out}"
            )
        return "[CODEX] turn completed"
    if t == "item.started":
        item = evt.get("item")
        if isinstance(item, dict) and str(item.get("type", "")) == "command_execution":
            tool = _extract_tool_name(str(item.get("command", "")))
            if tool:
                return f"[CODEX] tool start: {tool}"
            return "[CODEX] command start"
    if t == "item.completed":
        item = evt.get("item")
        if isinstance(item, dict) and str(item.get("type", "")) == "command_execution":
            tool = _extract_tool_name(str(item.get("command", "")))
            code = item.get("exit_code")
            status = str(item.get("status", ""))
            if tool:
                return f"[CODEX] tool done: {tool} status={status} code={code}"
            return f"[CODEX] command done status={status} code={code}"
        if (
            isinstance(item, dict)
            and str(item.get("type", "")) == "agent_message"
            and NATIVE_LOG_LEVEL == "debug"
        ):
            text = str(item.get("text", "")).strip().replace("\n", " ")
            if text:
                if len(text) > 240:
                    text = text[:240] + "..."
                return f"[CODEX] {text}"
    if NATIVE_LOG_LEVEL == "debug":
        return f"[CODEX RAW] {json.dumps(evt, ensure_ascii=True)}"
    return None


def _copy_bitgn_rules_snapshot_to_root(*, workspace_root: str) -> None:
    files_root = Path(workspace_root) / "initial_files" / "bitgn-rules"
    if not files_root.exists():
        return
    for path in files_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(files_root)
        target = Path(workspace_root) / rel
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def _resolve_tasks(argv: list[str]) -> list[str]:
    items = [str(x).strip() for x in argv if str(x).strip()]
    if not items:
        return []
    out: list[str] = []
    for item in items:
        parts = [p.strip() for p in item.split(",") if p.strip()]
        for p in parts:
            out.append(p)
    return list(dict.fromkeys(out))


def _resolve_local_run_id() -> str:
    value = (os.getenv("LOCAL_RUN_ID") or "").strip()
    if value:
        clean = "".join(
            ch for ch in value if ch.isalnum() or ch in {"-", "_", "."}
        ).strip("._-")
        if clean.startswith("local_run_"):
            return clean
        return (
            f"local_run_{clean}"
            if clean
            else f"local_run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{os.getpid()}"
        )
    return f"local_run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{os.getpid()}"


def _append_run_manifest(
    *, base_dir: str, local_run_id: str, row: dict[str, Any]
) -> None:
    manifest_dir = Path(base_dir) / local_run_id
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_dir / "run_manifest.jsonl"
    line = json.dumps(row, ensure_ascii=True, default=str) + "\n"
    with MANIFEST_LOCK:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)


def _parse_cli(argv: list[str]) -> tuple[list[str], int]:
    parser = ArgumentParser(description="Run codex-native on selected tasks")
    parser.add_argument("tasks", nargs="+", help="Task ids (space or comma separated)")
    parser.add_argument(
        "-p",
        "--parallelism",
        type=int,
        default=NATIVE_PARALLELISM,
        help="Task parallelism (default: 2)",
    )
    ns = parser.parse_args(argv)
    return _resolve_tasks(list(ns.tasks)), max(1, int(ns.parallelism or 1))


def detect_env() -> str:
    if AGENT_ENV:
        return AGENT_ENV
    if "pac1" in BENCHMARK_ID:
        return "pac1"
    return "sandbox"


def _score_payload(
    score: float | None,
    detail: list[str],
    submission: dict[str, Any],
    usage: dict[str, Any],
    steps: int,
    feedback_status: str = "scored",
    feedback_error: str = "",
) -> dict[str, Any]:
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "score": score,
        "passed": (None if score is None else bool(score == 1)),
        "score_detail": detail,
        "submission": submission,
        "usage": usage,
        "steps": steps,
        "feedback_status": feedback_status,
        "feedback_error": feedback_error,
    }


def _session_instruction(env: str, instruction: str, workspace_root: str) -> str:
    tool_help = (
        "context/tree/find/search/list/read/write/delete/mkdir/move/report_completion"
        if env == "pac1"
        else "tree/search/list/read/write/delete/report_completion"
    )
    local_rules_agents = harness_seed.render_local_rules_prompt()
    return (
        "You are an autonomous BitGN task agent.\n"
        "Default rules are from local-rules AGENTS content embedded below.\n"
        "BitGN runtime rules must be read from root `AGENTS.MD` and process docs.\n"
        "You may re-read local policy files from `local-rules/` during the session if needed.\n"
        "Treat `local-rules/` as read-only policy memory, not as task facts source.\n"
        "When local-rules guidance conflicts with BitGN VM policy/docs, follow BitGN VM policy/docs.\n"
        "Do not mutate `local-rules/` and do not use `local-rules/*` in grounding_refs.\n"
        "Solve the task by calling runtime tools yourself via shell command:\n"
        "python runtime_tools.py <tool> key=value ...\n"
        "For list fields, pass comma-separated values (example: grounding_refs=AGENTS.MD,notes.md).\n"
        "When task is complete, you MUST call report_completion exactly once.\n"
        "After first successful report_completion, stop immediately and do not call more tools.\n"
        "External evaluator feedback may be unavailable; still finish via report_completion once.\n"
        "Do not ask for confirmation. Keep actions minimal and task-focused.\n"
        f"Environment: {env}. Allowed tools: {tool_help}.\n"
        f"Workspace root for artifacts: {workspace_root}.\n\n"
        "Local rules (default):\n"
        "```text\n"
        f"{local_rules_agents}\n"
        "```\n\n"
        "Task instruction:\n"
        f"{instruction}\n"
    )


def _run_codex_session(
    *, env: str, instruction: str, workspace_root: str, workspace: Any, task_id: str
) -> dict[str, Any]:
    prompt = _session_instruction(env, instruction, workspace_root)
    workspace.codex_prompt_path.write_text(prompt + "\n", encoding="utf-8")
    out_path = workspace.codex_last_message_path
    cmd = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--json",
        "--output-last-message",
        str(out_path),
        "--model",
        CODEX_MODEL,
    ]
    if CODEX_PROFILE:
        cmd.extend(["--profile", CODEX_PROFILE])
    elif CODEX_BACKEND == "spark":
        cmd.extend(["-c", "model_provider=openai"])
    cmd.extend([
        "--cd",
        str(Path(__file__).resolve().parent),
        prompt,
    ])

    env_map = os.environ.copy()
    env_map["NATIVE_TASK_WORKSPACE"] = workspace_root

    started_at = datetime.now(timezone.utc)
    _stage(
        "CODEX_SESSION_START",
        f"model={CODEX_MODEL} timeout={max(60, NATIVE_SESSION_TIMEOUT_SEC)}s",
        task_id=task_id,
    )
    proc = subprocess.Popen(
        cmd,
        env=env_map,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    if proc.stdout is None:
        raise RuntimeError("codex session stdout pipe is unavailable")

    deadline = time.monotonic() + float(max(60, NATIVE_SESSION_TIMEOUT_SEC))
    stdout_tail: deque[str] = deque(maxlen=200)
    usage = {
        "tokens_prompt": 0,
        "tokens_completion": 0,
        "tokens_total": 0,
        "llm_calls": 0,
    }
    while True:
        if time.monotonic() > deadline:
            proc.kill()
            raise TimeoutError(
                f"codex session timeout after {max(60, NATIVE_SESSION_TIMEOUT_SEC)}s"
            )

        ready, _, _ = select.select([proc.stdout], [], [], 0.25)
        if ready:
            raw_line = proc.stdout.readline()
            if raw_line:
                line = raw_line.rstrip("\n")
                stdout_tail.append(line)
                workspace.append_jsonl(
                    workspace.codex_session_raw_path,
                    {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "line": line,
                    },
                )
                if not line.strip():
                    continue
                try:
                    evt: dict[str, Any] = json.loads(line)
                    workspace.append_jsonl(
                        workspace.codex_session_parsed_path,
                        {
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "type": evt.get("type"),
                            "item_type": (evt.get("item") or {}).get("type")
                            if isinstance(evt.get("item"), dict)
                            else None,
                            "item_id": (evt.get("item") or {}).get("id")
                            if isinstance(evt.get("item"), dict)
                            else None,
                            "status": (evt.get("item") or {}).get("status")
                            if isinstance(evt.get("item"), dict)
                            else None,
                            "exit_code": (evt.get("item") or {}).get("exit_code")
                            if isinstance(evt.get("item"), dict)
                            else None,
                            "tool": _extract_tool_name(
                                str((evt.get("item") or {}).get("command", ""))
                            )
                            if isinstance(evt.get("item"), dict)
                            else "",
                            "usage": evt.get("usage")
                            if isinstance(evt.get("usage"), dict)
                            else None,
                        },
                    )
                    rendered = _render_codex_event(evt)
                    if rendered:
                        _cli(f"[{task_id}] {rendered}")
                    if evt.get("type") == "turn.completed" and isinstance(
                        evt.get("usage"), dict
                    ):
                        u = evt["usage"]
                        inp = int(u.get("input_tokens", 0) or 0)
                        out = int(u.get("output_tokens", 0) or 0)
                        usage["llm_calls"] += 1
                        usage["tokens_prompt"] += inp
                        usage["tokens_completion"] += out
                        usage["tokens_total"] += inp + out
                except Exception:
                    if NATIVE_LOG_LEVEL == "debug":
                        _cli(f"[{task_id}] [CODEX TEXT] {line}")
            elif proc.poll() is not None:
                break
        elif proc.poll() is not None:
            break

    returncode = int(proc.wait())
    finished_at = datetime.now(timezone.utc)
    duration_ms = int((finished_at - started_at).total_seconds() * 1000)
    _stage("CODEX_SESSION_END", f"returncode={returncode}", task_id=task_id)
    stdout = "\n".join(stdout_tail)

    workspace.write_json(
        workspace.codex_session_meta_path,
        {
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_ms": duration_ms,
            "model": CODEX_MODEL,
            "profile": CODEX_PROFILE,
            "backend": CODEX_BACKEND,
            "env": env,
            "returncode": returncode,
            "usage": usage,
        },
    )

    return {
        "returncode": returncode,
        "stdout": stdout,
        "stderr": "",
        "usage": usage,
    }


def _hydrate_initial_workspace_files(
    *, gateway: ToolGateway, env: str, workspace_root: str
) -> None:
    files_root = Path(workspace_root) / "initial_files"
    files_root.mkdir(parents=True, exist_ok=True)
    harness_seed.copy_local_harness_into_workspace(target_dir=files_root)

    def save_text(rel_path: str, content: str) -> None:
        clean = rel_path.strip().replace("\\", "/").lstrip("/")
        if not clean:
            return
        if clean.lower().endswith(".md"):
            pass
        target = files_root / "bitgn-rules" / clean
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    if env == "pac1":
        core_candidates = [
            "AGENTS.MD",
            "README.md",
            "99_process/process_tasks.md",
            "99_process/document_capture.md",
            "99_process/document_cleanup.md",
            "02_distill/AGENTS.md",
            "02_distill/cards/_card-template.md",
            "02_distill/threads/_thread-template.md",
        ]
        for rel in core_candidates:
            try:
                ts = time.time()
                read_pb = gateway.vm.read(
                    PcmReadRequest(path=rel, number=False, start_line=0, end_line=0)
                )
                read_out = MessageToDict(read_pb)
                content = str(read_out.get("content", ""))
                gateway._append_tool_call(
                    step=-11,
                    tool="read",
                    args={"path": rel, "number": False, "start_line": 0, "end_line": 0},
                    ts_start=ts,
                    result=read_out,
                    error=None,
                )
                save_text(rel, content)
            except Exception:
                continue
    else:
        # sandbox mini runtime: keep deterministic minimal snapshot
        try:
            ts = time.time()
            read_pb = gateway.vm.read(ReadRequest(path="AGENTS.MD"))
            read_out = MessageToDict(read_pb)
            content = str(read_out.get("content", ""))
            gateway._append_tool_call(
                step=-11,
                tool="read",
                args={"path": "AGENTS.MD"},
                ts_start=ts,
                result=read_out,
                error=None,
            )
            save_text("AGENTS.MD", content)
        except Exception:
            pass


def _run_single_task(
    *,
    env: str,
    task_id: str,
    local_run_id: str,
    trial_seed: dict[str, str] | None = None,
    leaderboard_run_id: str | None = None,
) -> dict[str, Any]:

    _stage(
        "TASK_START",
        f"env={env} benchmark={BENCHMARK_ID} task={task_id} local_run_id={local_run_id}",
        task_id=task_id,
    )
    client = HarnessServiceClientSync(BITGN_URL)
    if trial_seed is None:
        _cli(f"[{task_id}] Connecting to BitGN {client.status(StatusRequest())}")
        benchmark = client.get_benchmark(GetBenchmarkRequest(benchmark_id=BENCHMARK_ID))
        _cli(
            f"[{task_id}] {EvalPolicy.Name(benchmark.policy)} benchmark: {benchmark.benchmark_id}"
        )
        trial = client.start_playground(
            StartPlaygroundRequest(benchmark_id=BENCHMARK_ID, task_id=task_id)
        )
        trial_id = str(trial.trial_id)
        harness_url = str(trial.harness_url)
        instruction = str(trial.instruction)
    else:
        trial_id = str(trial_seed.get("trial_id", ""))
        harness_url = str(trial_seed.get("harness_url", ""))
        instruction = str(trial_seed.get("instruction", ""))
        if not trial_id or not harness_url:
            raise RuntimeError(
                f"Prepared trial seed is invalid for task {task_id}: {trial_seed}"
            )
        _cli(f"[{task_id}] Using prepared leaderboard trial {trial_id}")

    _cli(f"[{task_id}] Task {task_id}: {instruction}")

    workspace = create_task_workspace(
        base_dir=NATIVE_RUNS_DIR,
        benchmark_id=BENCHMARK_ID,
        task_id=task_id,
        env=env,
        model=CODEX_MODEL,
        local_run_id=local_run_id,
    )
    workspace.instruction_path.write_text(instruction + "\n", encoding="utf-8")
    _stage("WORKSPACE_READY", str(workspace.root), task_id=task_id)
    workspace.append_jsonl(
        workspace.events_path,
        {
            "event": "task_started",
            "ts": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "local_run_id": local_run_id,
            "benchmark_id": BENCHMARK_ID,
            "env": env,
            "workspace": str(workspace.root),
        },
    )

    gateway = ToolGateway(
        env=env, harness_url=harness_url, workspace=workspace, task_id=task_id
    )
    workspace.write_json(
        workspace.context_path,
        {
            "env": env,
            "task_id": task_id,
            "local_run_id": local_run_id,
            "benchmark_id": BENCHMARK_ID,
            "harness_url": harness_url,
            "workspace_root": str(workspace.root),
        },
    )
    files_root = Path(workspace.root) / "initial_files"
    _stage("LOCAL_RULES_SNAPSHOT", task_id=task_id)
    copied = harness_seed.copy_local_harness_into_workspace(target_dir=files_root)
    workspace.append_jsonl(
        workspace.events_path,
        {
            "event": "local_rules_snapshot",
            "ts": datetime.now(timezone.utc).isoformat(),
            "copied_files": copied,
        },
    )
    try:
        _stage("BITGN_RULES_HYDRATION", task_id=task_id)
        _hydrate_initial_workspace_files(
            gateway=gateway, env=env, workspace_root=str(workspace.root)
        )
        _copy_bitgn_rules_snapshot_to_root(workspace_root=str(workspace.root))
        snapshot_root = Path(workspace.root) / "initial_files"
        has_snapshot = snapshot_root.exists() and any(
            p.is_file() for p in snapshot_root.rglob("*")
        )
        if not has_snapshot:
            snapshot_root.mkdir(parents=True, exist_ok=True)
            (snapshot_root / "TASK_INSTRUCTION.md").write_text(
                instruction.strip() + "\n", encoding="utf-8"
            )
        workspace.append_jsonl(
            workspace.events_path,
            {
                "event": "initial_files_hydrated",
                "ts": datetime.now(timezone.utc).isoformat(),
                "target": str(Path(workspace.root) / "initial_files"),
                "fallback_used": not has_snapshot,
            },
        )
    except Exception as exc:
        workspace.append_jsonl(
            workspace.events_path,
            {
                "event": "initial_files_hydration_error",
                "ts": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
            },
        )

    try:
        session_result = _run_codex_session(
            env=env,
            instruction=instruction,
            workspace_root=str(workspace.root),
            workspace=workspace,
            task_id=task_id,
        )
        workspace.write_json(
            workspace.codex_last_message_path,
            {
                "returncode": session_result.get("returncode"),
                "stderr": session_result.get("stderr", "")[:4000],
            },
        )
        workspace.append_jsonl(
            workspace.events_path,
            {
                "event": "codex_session_finished",
                "ts": datetime.now(timezone.utc).isoformat(),
                "returncode": session_result.get("returncode"),
            },
        )
        if session_result.get("stdout"):
            session_stdout = str(session_result.get("stdout", ""))
            tail = session_stdout[-4000:]
            workspace.append_jsonl(
                workspace.events_path,
                {
                    "event": "codex_session_stdout_tail",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "text": tail,
                },
            )

        if workspace.submission_path.exists():
            submission = json.loads(
                workspace.submission_path.read_text(encoding="utf-8")
            )
        else:
            raise RuntimeError(
                "Codex session finished without explicit report_completion (submission.json missing)"
            )

        tool_calls = 0
        if workspace.tool_calls_path.exists():
            tool_calls = sum(
                1
                for _ in workspace.tool_calls_path.read_text(
                    encoding="utf-8"
                ).splitlines()
                if _.strip()
            )
        agent_result = {
            "submission": submission,
            "usage": session_result.get("usage", {}),
            "steps": tool_calls,
        }
    except Exception as exc:
        workspace.append_jsonl(
            workspace.events_path,
            {
                "event": "agent_error",
                "ts": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
            },
        )
        _append_run_manifest(
            base_dir=NATIVE_RUNS_DIR,
            local_run_id=local_run_id,
            row={
                "ts": datetime.now(timezone.utc).isoformat(),
                "local_run_id": local_run_id,
                "benchmark_id": BENCHMARK_ID,
                "task_id": task_id,
                "trial_id": trial_id,
                "workspace": str(workspace.root),
                "error": str(exc),
                "leaderboard_run_id": leaderboard_run_id,
            },
        )
        return {
            "task_id": task_id,
            "ok": False,
            "error": str(exc),
            "workspace": str(workspace.root),
        }

    try:
        _stage("TRIAL_FINISH", task_id=task_id)
        result = client.end_trial(EndTrialRequest(trial_id=trial_id))
        score_detail = list(result.score_detail)
        score_payload = _score_payload(
            score=float(result.score),
            detail=score_detail,
            submission=agent_result.get("submission", {})
            if isinstance(agent_result, dict)
            else {},
            usage=agent_result.get("usage", {})
            if isinstance(agent_result, dict)
            else {},
            steps=int(agent_result.get("steps", 0) or 0)
            if isinstance(agent_result, dict)
            else 0,
            feedback_status="scored",
        )
        workspace.write_json(workspace.score_path, score_payload)
        workspace.append_jsonl(
            workspace.events_path,
            {
                "event": "trial_finished",
                "ts": datetime.now(timezone.utc).isoformat(),
                "score": float(result.score),
                "score_detail": score_detail,
                "feedback_status": "scored",
            },
        )
        _append_run_manifest(
            base_dir=NATIVE_RUNS_DIR,
            local_run_id=local_run_id,
            row={
                "ts": datetime.now(timezone.utc).isoformat(),
                "local_run_id": local_run_id,
                "benchmark_id": BENCHMARK_ID,
                "task_id": task_id,
                "trial_id": trial_id,
                "workspace": str(workspace.root),
                "score": float(result.score),
                "passed": bool(result.score == 1),
                "feedback_status": "scored",
                "leaderboard_run_id": leaderboard_run_id,
            },
        )
        print(json.dumps(score_payload, ensure_ascii=True, indent=2))
        print(f"[{task_id}] Workspace: {workspace.root}")
        return {
            "task_id": task_id,
            "ok": bool(result.score == 1),
            "passed": bool(result.score == 1),
            "score": float(result.score),
            "workspace": str(workspace.root),
        }
    except ConnectError as exc:
        submission = (
            agent_result.get("submission", {}) if isinstance(agent_result, dict) else {}
        )
        usage = agent_result.get("usage", {}) if isinstance(agent_result, dict) else {}
        steps = (
            int(agent_result.get("steps", 0) or 0)
            if isinstance(agent_result, dict)
            else 0
        )
        feedback_error = str(exc.message)
        workspace.append_jsonl(
            workspace.events_path,
            {
                "event": "end_trial_error",
                "ts": datetime.now(timezone.utc).isoformat(),
                "error": feedback_error,
            },
        )

        if _feedback_optional():
            score_payload = _score_payload(
                score=None,
                detail=[f"feedback unavailable: {feedback_error}"],
                submission=submission,
                usage=usage,
                steps=steps,
                feedback_status="unavailable",
                feedback_error=feedback_error,
            )
            workspace.write_json(workspace.score_path, score_payload)
            workspace.append_jsonl(
                workspace.events_path,
                {
                    "event": "trial_finished_without_feedback",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "feedback_error": feedback_error,
                },
            )
            _append_run_manifest(
                base_dir=NATIVE_RUNS_DIR,
                local_run_id=local_run_id,
                row={
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "local_run_id": local_run_id,
                    "benchmark_id": BENCHMARK_ID,
                    "task_id": task_id,
                    "trial_id": trial_id,
                    "workspace": str(workspace.root),
                    "score": None,
                    "passed": None,
                    "feedback_status": "unavailable",
                    "feedback_error": feedback_error,
                    "completion_status": "submitted",
                    "leaderboard_run_id": leaderboard_run_id,
                },
            )
            print(
                f"[{task_id}] EndTrial feedback unavailable (optional mode): {exc.code} {feedback_error}"
            )
            print(f"[{task_id}] Workspace: {workspace.root}")
            return {
                "task_id": task_id,
                "ok": True,
                "passed": None,
                "score": None,
                "feedback_status": "unavailable",
                "workspace": str(workspace.root),
            }

        _append_run_manifest(
            base_dir=NATIVE_RUNS_DIR,
            local_run_id=local_run_id,
            row={
                "ts": datetime.now(timezone.utc).isoformat(),
                "local_run_id": local_run_id,
                "benchmark_id": BENCHMARK_ID,
                "task_id": task_id,
                "trial_id": trial_id,
                "workspace": str(workspace.root),
                "error": feedback_error,
                "feedback_status": "failed",
                "leaderboard_run_id": leaderboard_run_id,
            },
        )
        print(f"[{task_id}] EndTrial failed: {exc.code} {feedback_error}")
        print(f"[{task_id}] Workspace: {workspace.root}")
        return {
            "task_id": task_id,
            "ok": False,
            "error": feedback_error,
            "workspace": str(workspace.root),
        }


def main() -> None:
    task_filter, parallelism = _parse_cli(sys.argv[1:])
    env = detect_env()
    harness_seed.validate_local_harness()

    leaderboard_trials: dict[str, dict[str, str]] = {}
    leaderboard_run_id: str | None = None
    if BITGN_API_KEY:
        try:
            prep_client = HarnessServiceClientSync(BITGN_URL)
            _cli(f"[LEADERBOARD] Preparing run against {BITGN_URL}")
            leaderboard_trials, leaderboard_run_id = _prepare_leaderboard_trials(
                client=prep_client,
                task_ids=task_filter,
            )
        except ConnectError as exc:
            _cli(
                f"[LEADERBOARD] Failed to start leaderboard run ({exc.code}: {exc.message}). "
                "Falling back to playground mode."
            )
        except Exception as exc:
            _cli(
                "[LEADERBOARD] Failed to prepare leaderboard run "
                f"({exc}). Falling back to playground mode."
            )

    local_run_id = _resolve_local_run_id()
    _stage(
        "LOCAL_RUN_START",
        f"local_run_id={local_run_id} tasks={task_filter} parallelism={parallelism}",
    )

    results: list[dict[str, Any]] = []
    if parallelism <= 1 or len(task_filter) <= 1:
        for task_id in task_filter:
            results.append(
                _run_single_task(
                    env=env,
                    task_id=task_id,
                    local_run_id=local_run_id,
                    trial_seed=leaderboard_trials.get(task_id),
                    leaderboard_run_id=leaderboard_run_id,
                )
            )
    else:
        max_workers = min(parallelism, len(task_filter))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(
                    _run_single_task,
                    env=env,
                    task_id=task_id,
                    local_run_id=local_run_id,
                    trial_seed=leaderboard_trials.get(task_id),
                    leaderboard_run_id=leaderboard_run_id,
                )
                for task_id in task_filter
            ]
            for fut in as_completed(futures):
                results.append(fut.result())

    if leaderboard_run_id:
        try:
            submit_client = HarnessServiceClientSync(BITGN_URL)
            submit_client.submit_run(
                SubmitRunRequest(run_id=leaderboard_run_id, force=True)
            )
            _stage("LEADERBOARD_SUBMIT", f"run_id={leaderboard_run_id}")
        except ConnectError as exc:
            _cli(
                f"[LEADERBOARD] Submit failed for run {leaderboard_run_id}: "
                f"{exc.code} {exc.message}"
            )
            raise SystemExit(2) from exc

    total = len(results)
    passed = sum(1 for r in results if bool(r.get("passed", False)))
    failed = sum(1 for r in results if not bool(r.get("ok", False)))
    _stage(
        "LOCAL_RUN_FINISH",
        f"local_run_id={local_run_id} total={total} passed={passed} failed={failed}",
    )
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
