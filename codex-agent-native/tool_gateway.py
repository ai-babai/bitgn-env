# pyright: reportMissingImports=false

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
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


def _is_frontmatter_only_markdown(content: str) -> bool:
    text = str(content or "").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return False
    split_idx = text.find("\n---\n", 4)
    if split_idx != -1:
        body = text[split_idx + 5 :]
        return body.strip() == ""
    if text.endswith("\n---"):
        return True
    return False


def _extract_markdown_body(content: str) -> str:
    text = str(content or "").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return text
    split_idx = text.find("\n---\n", 4)
    if split_idx != -1:
        return text[split_idx + 5 :]
    if text.endswith("\n---"):
        return ""
    return text


def _has_queue_markers(content: str) -> bool:
    text = str(content or "")
    return all(
        marker in text
        for marker in (
            "bulk_processing_workflow",
            "queue_batch_timestamp",
            "queue_order_id",
            "queue_target",
        )
    )


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
        self.block_outbox_write = os.getenv(
            "PAC1_BLOCK_OUTBOX_WRITE", ""
        ).strip().lower() in {"1", "true", "yes", "on"}
        self._seen_outbox_writes: set[str] = set()
        self._seen_queue_writes: set[str] = set()

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
            path_raw = str(args.get("path", ""))
            path = path_raw.lstrip("/")
            local_path = (self.workspace.root / path) if path else Path("")

            if self.block_outbox_write and path.startswith("60_outbox/outbox/"):
                return {}

            if path.startswith("60_outbox/outbox/"):
                if str(args.get("content", "")).strip() == "":
                    return {}
                if local_path.exists() and local_path.is_file():
                    existing = local_path.read_text(encoding="utf-8")
                    if existing.strip():
                        return {}

            if (
                path.startswith("60_outbox/outbox/")
                and path in self._seen_outbox_writes
            ):
                return {}

            content = _normalize_json_write_content(path, str(args.get("content", "")))

            if (
                path.endswith(".md")
                and local_path.exists()
                and local_path.is_file()
                and _is_frontmatter_only_markdown(content)
            ):
                existing = local_path.read_text(encoding="utf-8")
                if _extract_markdown_body(existing).strip():
                    return {}

            if (
                path.endswith(".md")
                and local_path.exists()
                and local_path.is_file()
                and local_path.read_text(encoding="utf-8") == content
            ):
                return {}

            if _has_queue_markers(content) and path in self._seen_queue_writes:
                return {}

            self.vm.write(
                PcmWriteRequest(
                    path=path,
                    content=content,
                    start_line=int(args.get("start_line", 0) or 0),
                    end_line=int(args.get("end_line", 0) or 0),
                )
            )
            if path.startswith("60_outbox/outbox/"):
                self._seen_outbox_writes.add(path)
            if _has_queue_markers(content):
                self._seen_queue_writes.add(path)
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
            try:
                self.vm.answer(
                    PcmAnswerRequest(
                        message=str(args.get("message", args.get("answer", "WIP"))),
                        outcome=OUTCOME_BY_NAME[outcome],
                        refs=[str(r) for r in refs],
                    )
                )
            except Exception:
                # Offline fallback: keep local run artifacts consistent even when VM is unreachable.
                return {}
            return {}
        raise ValueError(f"Unknown pac1 tool: {tool}")


def summarize_tool_result(payload: dict[str, Any], limit: int = 1200) -> str:
    text = json.dumps(payload, ensure_ascii=True)
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def print_tool_result(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True))
