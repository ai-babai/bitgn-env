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
    StartPlaygroundRequest,
    StatusRequest,
)
from bitgn.vm.mini_pb2 import ReadRequest
from bitgn.vm.pcm_pb2 import ReadRequest as PcmReadRequest
from connectrpc.errors import ConnectError
from google.protobuf.json_format import MessageToDict

from tool_gateway import ToolGateway
from harness_seed import (
    copy_local_harness_into_workspace,
    render_local_rules_prompt,
    validate_local_harness,
)
from workspace import create_task_workspace

BITGN_URL = os.getenv("BENCHMARK_HOST") or "https://api.bitgn.com"
BENCHMARK_ID = os.getenv("BENCHMARK_ID") or "bitgn/sandbox"
AGENT_ENV = (os.getenv("AGENT_ENV") or "").strip().lower()
CODEX_MODEL = os.getenv("CODEX_MODEL") or "gpt-5.3-codex"
NATIVE_SESSION_TIMEOUT_SEC = int(os.getenv("NATIVE_SESSION_TIMEOUT_SEC") or 420)
NATIVE_RUNS_DIR = os.getenv("NATIVE_RUNS_DIR") or str(
    Path(__file__).resolve().parent / "runs"
)
NATIVE_LOG_LEVEL = (os.getenv("NATIVE_LOG_LEVEL") or "info").strip().lower()
NATIVE_PARALLELISM = max(1, int(os.getenv("NATIVE_PARALLELISM") or 2))
MANIFEST_LOCK = threading.Lock()


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
    score: float,
    detail: list[str],
    submission: dict[str, Any],
    usage: dict[str, Any],
    steps: int,
) -> dict[str, Any]:
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "score": score,
        "passed": bool(score == 1),
        "score_detail": detail,
        "submission": submission,
        "usage": usage,
        "steps": steps,
    }


def _session_instruction(env: str, instruction: str, workspace_root: str) -> str:
    tool_help = (
        "context/tree/find/search/list/read/write/delete/mkdir/move/report_completion"
        if env == "pac1"
        else "tree/search/list/read/write/delete/report_completion"
    )
    local_rules_agents = render_local_rules_prompt()
    return (
        "You are an autonomous BitGN task agent.\n"
        "Default rules are from local-rules AGENTS content embedded below.\n"
        "BitGN runtime rules must be read from root `AGENTS.MD` and process docs.\n"
        "Solve the task by calling runtime tools yourself via shell command:\n"
        "python runtime_tools.py <tool> key=value ...\n"
        "For list fields, pass comma-separated values (example: grounding_refs=AGENTS.MD,notes.md).\n"
        "When task is complete, you MUST call report_completion exactly once.\n"
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
        "--cd",
        str(Path(__file__).resolve().parent),
        prompt,
    ]

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
    copy_local_harness_into_workspace(target_dir=files_root)

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


def _run_single_task(*, env: str, task_id: str, local_run_id: str) -> dict[str, Any]:

    _stage(
        "TASK_START",
        f"env={env} benchmark={BENCHMARK_ID} task={task_id} local_run_id={local_run_id}",
        task_id=task_id,
    )
    client = HarnessServiceClientSync(BITGN_URL)
    _cli(f"[{task_id}] Connecting to BitGN {client.status(StatusRequest())}")
    benchmark = client.get_benchmark(GetBenchmarkRequest(benchmark_id=BENCHMARK_ID))
    _cli(
        f"[{task_id}] {EvalPolicy.Name(benchmark.policy)} benchmark: {benchmark.benchmark_id}"
    )

    trial = client.start_playground(
        StartPlaygroundRequest(benchmark_id=BENCHMARK_ID, task_id=task_id)
    )
    _cli(f"[{task_id}] Task {task_id}: {trial.instruction}")

    workspace = create_task_workspace(
        base_dir=NATIVE_RUNS_DIR,
        benchmark_id=BENCHMARK_ID,
        task_id=task_id,
        env=env,
        model=CODEX_MODEL,
        local_run_id=local_run_id,
    )
    workspace.instruction_path.write_text(trial.instruction + "\n", encoding="utf-8")
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
        env=env, harness_url=trial.harness_url, workspace=workspace, task_id=task_id
    )
    workspace.write_json(
        workspace.context_path,
        {
            "env": env,
            "task_id": task_id,
            "local_run_id": local_run_id,
            "benchmark_id": BENCHMARK_ID,
            "harness_url": trial.harness_url,
            "workspace_root": str(workspace.root),
        },
    )
    files_root = Path(workspace.root) / "initial_files"
    _stage("LOCAL_RULES_SNAPSHOT", task_id=task_id)
    copied = copy_local_harness_into_workspace(target_dir=files_root)
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
                trial.instruction.strip() + "\n", encoding="utf-8"
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
            instruction=trial.instruction,
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
                "trial_id": trial.trial_id,
                "workspace": str(workspace.root),
                "error": str(exc),
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
        result = client.end_trial(EndTrialRequest(trial_id=trial.trial_id))
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
        )
        workspace.write_json(workspace.score_path, score_payload)
        workspace.append_jsonl(
            workspace.events_path,
            {
                "event": "trial_finished",
                "ts": datetime.now(timezone.utc).isoformat(),
                "score": float(result.score),
                "score_detail": score_detail,
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
                "trial_id": trial.trial_id,
                "workspace": str(workspace.root),
                "score": float(result.score),
                "passed": bool(result.score == 1),
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
        workspace.append_jsonl(
            workspace.events_path,
            {
                "event": "end_trial_error",
                "ts": datetime.now(timezone.utc).isoformat(),
                "error": str(exc.message),
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
                "trial_id": trial.trial_id,
                "workspace": str(workspace.root),
                "error": str(exc.message),
            },
        )
        print(f"[{task_id}] EndTrial failed: {exc.code} {exc.message}")
        print(f"[{task_id}] Workspace: {workspace.root}")
        return {
            "task_id": task_id,
            "ok": False,
            "error": str(exc.message),
            "workspace": str(workspace.root),
        }


def main() -> None:
    task_filter, parallelism = _parse_cli(sys.argv[1:])
    env = detect_env()
    validate_local_harness()

    local_run_id = _resolve_local_run_id()
    _stage(
        "LOCAL_RUN_START",
        f"local_run_id={local_run_id} tasks={task_filter} parallelism={parallelism}",
    )

    results: list[dict[str, Any]] = []
    if parallelism <= 1 or len(task_filter) <= 1:
        for task_id in task_filter:
            results.append(
                _run_single_task(env=env, task_id=task_id, local_run_id=local_run_id)
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
                )
                for task_id in task_filter
            ]
            for fut in as_completed(futures):
                results.append(fut.result())

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
