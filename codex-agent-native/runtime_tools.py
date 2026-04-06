import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

from tool_gateway import ToolGateway, print_tool_result
from workspace import open_task_workspace


NATIVE_LOG_LEVEL = (os.getenv("NATIVE_LOG_LEVEL") or "info").strip().lower()


def _cli_tool(msg: str) -> None:
    print(msg, flush=True)


def _short_args(args: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in sorted(args.keys()):
        value = args.get(key)
        if key == "content":
            text = str(value)
            parts.append(f"content_len={len(text)}")
            continue
        text = str(value)
        if len(text) > 60:
            text = text[:60] + "..."
        parts.append(f"{key}={text}")
    return " ".join(parts)


def _load_gateway() -> tuple[ToolGateway, str]:
    workspace_root = os.getenv("NATIVE_TASK_WORKSPACE", "").strip()
    if not workspace_root:
        raise SystemExit("NATIVE_TASK_WORKSPACE is required")
    workspace = open_task_workspace(workspace_root)
    gateway = ToolGateway.from_workspace_context(workspace)
    return gateway, workspace_root


def _read_json_arg() -> dict[str, Any]:
    if len(sys.argv) >= 3:
        raw = sys.argv[2]
        if raw.startswith("{"):
            return json.loads(raw)
        pairs = sys.argv[2:]
        out: dict[str, Any] = {}
        for item in pairs:
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue
            if key in {"count", "limit", "level", "start_line", "end_line", "_step"}:
                try:
                    out[key] = int(value)
                    continue
                except ValueError:
                    pass
            if key in {"number"}:
                out[key] = value.lower() in {"1", "true", "yes", "on"}
                continue
            if key in {"grounding_refs"}:
                refs = [x.strip() for x in value.split(",") if x.strip()]
                out[key] = refs
                continue
            out[key] = value
        return out
    raw_stdin = sys.stdin.read().strip()
    if not raw_stdin:
        return {}
    return json.loads(raw_stdin)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python runtime_tools.py <tool> [json-args]")

    tool = str(sys.argv[1]).strip()
    args = _read_json_arg()
    if not isinstance(args, dict):
        raise SystemExit("Args must be a JSON object")

    gateway, workspace_root = _load_gateway()
    step = int(args.pop("_step", 0) or 0)
    _cli_tool(f"TOOL_CALL tool={tool} step={step} {_short_args(args)}")
    try:
        result = gateway.call(step=step, tool=tool, args=args)
        _cli_tool(f"TOOL_OK tool={tool}")
    except Exception as exc:
        _cli_tool(f"TOOL_ERR tool={tool} err={str(exc)}")
        raise

    if tool == "report_completion":
        ws = open_task_workspace(workspace_root)
        if gateway.env == "pac1":
            refs_raw = args.get("grounding_refs", [])
            refs = refs_raw if isinstance(refs_raw, list) else []
            refs = [str(r).strip().lstrip("/") for r in refs if str(r).strip()]
            refs = [r for r in refs if not r.startswith("task-context-snapshots/")]
            refs = [r for r in refs if not r.startswith("local-rules/")]
            if not refs:
                refs = ["AGENTS.MD"]
            payload = {
                "message": str(args.get("message", args.get("answer", ""))),
                "outcome": str(args.get("outcome", "OUTCOME_NONE_UNSUPPORTED")),
                "grounding_refs": refs,
            }
        else:
            refs_raw = args.get("grounding_refs", [])
            refs = refs_raw if isinstance(refs_raw, list) else []
            refs = [str(r).strip().lstrip("/") for r in refs if str(r).strip()]
            if not refs:
                refs = ["AGENTS.MD"]
            payload = {
                "answer": str(args.get("answer", "")),
                "grounding_refs": refs,
            }
        ws.write_json(ws.submission_path, payload)
        ws.append_jsonl(
            ws.events_path,
            {
                "event": "completion_reported",
                "ts": datetime.now(timezone.utc).isoformat(),
                "tool": tool,
                "submission": payload,
            },
        )

    if NATIVE_LOG_LEVEL == "debug":
        print_tool_result(result)


if __name__ == "__main__":
    main()
