# pyright: reportMissingImports=false

import json
import time
from datetime import datetime, timezone
from typing import Any

from bitgn.vm.mini_connect import MiniRuntimeClientSync
from bitgn.vm.mini_pb2 import (
    AnswerRequest,
    DeleteRequest,
    ListRequest,
    OutlineRequest,
    ReadRequest,
    SearchRequest,
    WriteRequest,
)
from bitgn.vm.pcm_connect import PcmRuntimeClientSync
from bitgn.vm.pcm_pb2 import (
    AnswerRequest as PcmAnswerRequest,
    ContextRequest,
    DeleteRequest as PcmDeleteRequest,
    FindRequest,
    ListRequest as PcmListRequest,
    MkDirRequest,
    MoveRequest,
    Outcome,
    ReadRequest as PcmReadRequest,
    SearchRequest as PcmSearchRequest,
    TreeRequest,
    WriteRequest as PcmWriteRequest,
)
from google.protobuf.json_format import MessageToDict
from workspace import TaskWorkspace

OUTCOME_BY_NAME = {
    "OUTCOME_OK": Outcome.OUTCOME_OK,
    "OUTCOME_DENIED_SECURITY": Outcome.OUTCOME_DENIED_SECURITY,
    "OUTCOME_NONE_CLARIFICATION": Outcome.OUTCOME_NONE_CLARIFICATION,
    "OUTCOME_NONE_UNSUPPORTED": Outcome.OUTCOME_NONE_UNSUPPORTED,
    "OUTCOME_ERR_INTERNAL": Outcome.OUTCOME_ERR_INTERNAL,
}


def _normalize_json_write_content(path: str, content: str) -> str:
    p = str(path or "").strip().lower()
    if not p.endswith(".json"):
        return content
    if '\\"' not in content:
        return content

    try:
        json.loads(content)
        return content
    except Exception:
        pass

    candidate = content.replace('\\"', '"')
    try:
        json.loads(candidate)
        return candidate
    except Exception:
        return content


class ToolGateway:
    def __init__(
        self, *, env: str, harness_url: str, workspace: TaskWorkspace, task_id: str
    ) -> None:
        self.env = env
        self.task_id = task_id
        self.workspace = workspace
        if env == "pac1":
            self.vm: Any = PcmRuntimeClientSync(harness_url)
        else:
            self.vm = MiniRuntimeClientSync(harness_url)

    @staticmethod
    def from_workspace_context(workspace: TaskWorkspace) -> "ToolGateway":
        ctx = json.loads(workspace.context_path.read_text(encoding="utf-8"))
        return ToolGateway(
            env=str(ctx.get("env", "sandbox")),
            harness_url=str(ctx.get("harness_url", "")),
            workspace=workspace,
            task_id=str(ctx.get("task_id", "")),
        )

    def _append_tool_call(
        self,
        *,
        step: int,
        tool: str,
        args: dict[str, Any],
        ts_start: float,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> None:
        ts_end = time.time()
        self.workspace.append_jsonl(
            self.workspace.tool_calls_path,
            {
                "ts_start": datetime.fromtimestamp(ts_start, timezone.utc).isoformat(),
                "ts_end": datetime.fromtimestamp(ts_end, timezone.utc).isoformat(),
                "duration_ms": int((ts_end - ts_start) * 1000),
                "task_id": self.task_id,
                "step": step,
                "tool": tool,
                "args": args,
                "result": result,
                "error": error,
            },
        )

    def call(self, *, step: int, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        ts = time.time()
        try:
            out = self._dispatch(tool=tool, args=args)
            if isinstance(out, dict):
                out_dict = out
            else:
                try:
                    out_dict = MessageToDict(out)
                except Exception:
                    out_dict = {}
            self._append_tool_call(
                step=step,
                tool=tool,
                args=args,
                ts_start=ts,
                result=out_dict,
                error=None,
            )
            return out_dict
        except Exception as exc:
            self._append_tool_call(
                step=step,
                tool=tool,
                args=args,
                ts_start=ts,
                result=None,
                error=str(exc),
            )
            raise

    def _dispatch(self, *, tool: str, args: dict[str, Any]):
        if self.env == "pac1":
            return self._dispatch_pac1(tool=tool, args=args)
        return self._dispatch_sandbox(tool=tool, args=args)

    def _dispatch_sandbox(self, *, tool: str, args: dict[str, Any]):
        if tool == "tree":
            return self.vm.outline(OutlineRequest(path=str(args.get("path", "/"))))
        if tool == "search":
            return self.vm.search(
                SearchRequest(
                    path=str(args.get("path", "/")),
                    pattern=str(args.get("pattern", "")),
                    count=max(1, min(int(args.get("count", 5) or 5), 10)),
                )
            )
        if tool == "list":
            return self.vm.list(ListRequest(path=str(args.get("path", "/"))))
        if tool == "read":
            return self.vm.read(ReadRequest(path=str(args.get("path", "AGENTS.MD"))))
        if tool == "write":
            self.vm.write(
                WriteRequest(
                    path=str(args.get("path", "")), content=str(args.get("content", ""))
                )
            )
            return {}
        if tool == "delete":
            self.vm.delete(DeleteRequest(path=str(args.get("path", ""))))
            return {}
        if tool == "report_completion":
            refs = args.get("grounding_refs", [])
            if not isinstance(refs, list):
                refs = []
            try:
                self.vm.answer(
                    AnswerRequest(
                        answer=str(args.get("answer", "WIP")),
                        refs=[str(r) for r in refs],
                    )
                )
                return {}
            except Exception:
                # Offline fallback: keep local run artifacts consistent even when VM is unreachable.
                return {}
        raise ValueError(f"Unknown sandbox tool: {tool}")

    def _dispatch_pac1(self, *, tool: str, args: dict[str, Any]):
        if tool == "context":
            return self.vm.context(ContextRequest())
        if tool == "tree":
            return self.vm.tree(
                TreeRequest(
                    root=str(args.get("root") or args.get("path") or "/"),
                    level=int(args.get("level", 2) or 2),
                )
            )
        if tool == "find":
            kind = str(args.get("kind", "all"))
            kind_map = {"all": "TYPE_ALL", "files": "TYPE_FILES", "dirs": "TYPE_DIRS"}
            return self.vm.find(
                FindRequest(
                    root=str(args.get("root", "/")),
                    name=str(args.get("name", "")),
                    type=kind_map.get(kind, "TYPE_ALL"),
                    limit=int(args.get("limit", 10) or 10),
                )
            )
        if tool == "search":
            return self.vm.search(
                PcmSearchRequest(
                    root=str(args.get("root", "/")),
                    pattern=str(args.get("pattern", "")),
                    limit=int(args.get("limit", 10) or 10),
                )
            )
        if tool == "list":
            return self.vm.list(PcmListRequest(name=str(args.get("path", "/"))))
        if tool == "read":
            return self.vm.read(
                PcmReadRequest(
                    path=str(args.get("path", "AGENTS.MD")),
                    number=bool(args.get("number", False)),
                    start_line=int(args.get("start_line", 0) or 0),
                    end_line=int(args.get("end_line", 0) or 0),
                )
            )
        if tool == "write":
            path = str(args.get("path", ""))
            content = _normalize_json_write_content(path, str(args.get("content", "")))
            self.vm.write(
                PcmWriteRequest(
                    path=path,
                    content=content,
                    start_line=int(args.get("start_line", 0) or 0),
                    end_line=int(args.get("end_line", 0) or 0),
                )
            )
            return {}
        if tool == "delete":
            self.vm.delete(PcmDeleteRequest(path=str(args.get("path", ""))))
            return {}
        if tool == "mkdir":
            self.vm.mk_dir(MkDirRequest(path=str(args.get("path", ""))))
            return {}
        if tool == "move":
            self.vm.move(
                MoveRequest(
                    from_name=str(args.get("from_name", "")),
                    to_name=str(args.get("to_name", "")),
                )
            )
            return {}
        if tool == "report_completion":
            refs = args.get("grounding_refs", [])
            if not isinstance(refs, list):
                refs = []
            outcome = str(args.get("outcome", "OUTCOME_NONE_UNSUPPORTED"))
            if outcome not in OUTCOME_BY_NAME:
                outcome = "OUTCOME_NONE_UNSUPPORTED"
            self.vm.answer(
                PcmAnswerRequest(
                    message=str(args.get("message", args.get("answer", "WIP"))),
                    outcome=OUTCOME_BY_NAME[outcome],
                    refs=[str(r) for r in refs],
                )
            )
            return {}
        raise ValueError(f"Unknown pac1 tool: {tool}")


def summarize_tool_result(payload: dict[str, Any], limit: int = 1200) -> str:
    text = json.dumps(payload, ensure_ascii=True)
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def print_tool_result(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True))
