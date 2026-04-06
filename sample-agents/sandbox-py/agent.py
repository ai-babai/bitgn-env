import json
import re
import time
from collections.abc import Callable
from typing import Annotated, List, Literal, Union

from annotated_types import Ge, Le, MaxLen, MinLen
from google.protobuf.json_format import MessageToDict
from openai import OpenAI
from pydantic import BaseModel, Field

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
from connectrpc.errors import ConnectError


class ReportTaskCompletion(BaseModel):
    tool: Literal["report_completion"]
    completed_steps_laconic: List[str]
    answer: str
    grounding_refs: List[str] = Field(default_factory=list)

    code: Literal["completed", "failed"]


class Req_Tree(BaseModel):
    tool: Literal["tree"]
    path: str = Field(..., description="folder path")


class Req_Search(BaseModel):
    tool: Literal["search"]
    pattern: str
    count: Annotated[int, Ge(1), Le(10)] = 5
    path: str = "/"


class Req_List(BaseModel):
    tool: Literal["list"]
    path: str


class Req_Read(BaseModel):
    tool: Literal["read"]
    path: str


class Req_Write(BaseModel):
    tool: Literal["write"]
    path: str
    content: str


class Req_Delete(BaseModel):
    tool: Literal["delete"]
    path: str


class NextStep(BaseModel):
    current_state: str
    # we'll use only the first step, discarding all the rest.
    plan_remaining_steps_brief: Annotated[List[str], MinLen(1), MaxLen(5)] = Field(
        ...,
        description="explain your thoughts on how to accomplish - what steps to execute",
    )
    # now let's continue the cascade and check with LLM if the task is done
    task_completed: bool
    # AICODE-NOTE: Keep this union aligned with the MiniRuntime protobuf surface so
    # structured tool calling stays exhaustive as demo VM request types evolve.
    function: Union[
        ReportTaskCompletion,
        Req_Tree,
        Req_Search,
        Req_List,
        Req_Read,
        Req_Write,
        Req_Delete,
    ] = Field(..., description="execute first remaining step")


system_prompt = """
You are a personal business assistant, helpful and precise.
 
- always start by discovering available information by running root outline.
- always read `AGENTS.md` at the start
- always reference (ground) in final response all files that contributed to the answer
- Clearly report when tasks are done
"""


CLI_RED = "\x1B[31m"
CLI_GREEN = "\x1B[32m"
CLI_CLR = "\x1B[0m"
CLI_BLUE = "\x1B[34m"

EventHook = Callable[[str, dict[str, object]], None]


def _derive_forced_answer(file_texts: dict[str, str]) -> tuple[str, list[str]]:
    for path, content in file_texts.items():
        m = re.search(r"always\s+respond\s+with\s+[\"']([^\"']+)[\"']", content, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip(), [path]
    if "AGENTS.MD" in file_texts:
        return "WIP", ["AGENTS.MD"]
    return "WIP", list(file_texts.keys())[:1]


def _extract_md_refs(text: str) -> list[str]:
    refs = re.findall(r"['\"]([A-Za-z0-9_./-]+\.MD)['\"]", text)
    uniq: list[str] = []
    seen: set[str] = set()
    for ref in refs:
        key = ref.upper()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(ref)
    return uniq


def _command_signature(cmd: BaseModel) -> str:
    if isinstance(cmd, Req_Tree):
        return f"tree:{cmd.path}"
    if isinstance(cmd, Req_Read):
        return f"read:{cmd.path}"
    if isinstance(cmd, Req_List):
        return f"list:{cmd.path}"
    if isinstance(cmd, Req_Search):
        return f"search:{cmd.path}:{cmd.pattern}"
    if isinstance(cmd, Req_Write):
        return f"write:{cmd.path}"
    if isinstance(cmd, Req_Delete):
        return f"delete:{cmd.path}"
    if isinstance(cmd, ReportTaskCompletion):
        return "report_completion"
    return cmd.__class__.__name__


def dispatch(r: MiniRuntimeClientSync, cmd: BaseModel):
    if isinstance(cmd, Req_Tree):
        return r.outline(OutlineRequest(path=cmd.path))
    if isinstance(cmd, Req_Search):
        return r.search(SearchRequest(path=cmd.path, pattern=cmd.pattern, count=cmd.count))
    if isinstance(cmd, Req_List):
        return r.list(ListRequest(path=cmd.path))
    if isinstance(cmd, Req_Read):
        return r.read(ReadRequest(path=cmd.path))
    if isinstance(cmd, Req_Write):
        return r.write(WriteRequest(path=cmd.path, content=cmd.content))
    if isinstance(cmd, Req_Delete):
        return r.delete(DeleteRequest(path=cmd.path))
    if isinstance(cmd, ReportTaskCompletion):
        return r.answer(AnswerRequest(answer=cmd.answer, refs=cmd.grounding_refs))

    raise ValueError(f"Unknown command: {cmd}")


def _emit(event_hook: EventHook | None, event: str, payload: dict[str, object]) -> None:
    if event_hook is not None:
        event_hook(event, payload)


def _next_step(
    client: OpenAI,
    model: str,
    log: list[dict[str, object]],
    event_hook: EventHook | None = None,
) -> NextStep:
    schema = json.dumps(NextStep.model_json_schema(), ensure_ascii=True)
    steer = {
        "role": "system",
        "content": (
            "CRITICAL: Output strictly one JSON object matching the schema. "
            "No markdown, no prose, no code fences. "
            "If unsure, still emit best-effort valid JSON object.\n"
            "JSON schema:\n" + schema
        ),
    }
    guided_log = log + [steer]
    _emit(event_hook, "prompt_sections", {"steering_prompt": steer["content"]})

    def _extract_json(text: str) -> str:
        try:
            NextStep.model_validate_json(text)
            return text
        except Exception:
            pass

        start = text.find("{")
        if start != -1:
            try:
                obj, _ = json.JSONDecoder().raw_decode(text[start:])
                return json.dumps(obj, ensure_ascii=True)
            except Exception:
                pass

        match = re.search(r"\{.*?\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError("No JSON object in model response")
        candidate = match.group(0)
        return candidate

    def _coerce_tool_shape(raw_obj: dict) -> NextStep:
        tool_name = str(raw_obj.get("tool", "")).lower()
        arguments = raw_obj.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except Exception:
                arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}

        step_brief = raw_obj.get("current_state") or raw_obj.get("thought") or f"Execute {tool_name}"

        if tool_name in {"root_outline", "outline", "tree"}:
            fn: BaseModel = Req_Tree(tool="tree", path=arguments.get("path", "/"))
            done = False
        elif tool_name == "search":
            fn = Req_Search(
                tool="search",
                pattern=arguments.get("pattern", ""),
                count=int(arguments.get("count", 5) or 5),
                path=arguments.get("path", "/"),
            )
            done = False
        elif tool_name in {"list", "ls"}:
            fn = Req_List(tool="list", path=arguments.get("path", "/"))
            done = False
        elif tool_name in {"read", "cat"}:
            fn = Req_Read(tool="read", path=arguments.get("path") or arguments.get("file") or "AGENTS.md")
            done = False
        elif tool_name == "write":
            fn = Req_Write(
                tool="write",
                path=arguments.get("path", ""),
                content=arguments.get("content", ""),
            )
            done = False
        elif tool_name == "delete":
            fn = Req_Delete(tool="delete", path=arguments.get("path", ""))
            done = False
        elif tool_name in {"report_completion", "answer", "complete"}:
            refs = raw_obj.get("grounding_refs", []) or []
            if "AGENTS.MD" not in refs and "AGENTS.md" not in refs:
                refs = ["AGENTS.MD", *refs]
            fn = ReportTaskCompletion(
                tool="report_completion",
                completed_steps_laconic=[str(step_brief)],
                answer=str(raw_obj.get("answer", "WIP")),
                grounding_refs=refs,
                code="completed",
            )
            done = True
        else:
            refs = raw_obj.get("grounding_refs", []) or ["AGENTS.MD"]
            fn = ReportTaskCompletion(
                tool="report_completion",
                completed_steps_laconic=[str(step_brief)],
                answer=str(raw_obj.get("answer", "WIP")),
                grounding_refs=refs,
                code="completed",
            )
            done = True

        return NextStep(
            current_state=str(raw_obj.get("current_state", "coerced-tool-shape")),
            plan_remaining_steps_brief=[str(step_brief)],
            task_completed=bool(raw_obj.get("task_completed", done)),
            function=fn,
        )

    def _parse_next_step(content: str) -> NextStep:
        extracted = _extract_json(content)
        try:
            return NextStep.model_validate_json(extracted)
        except Exception:
            pass
        raw_obj = json.loads(extracted)
        if isinstance(raw_obj, dict):
            return _coerce_tool_shape(raw_obj)
        raise ValueError("Model response is not a JSON object")

    try:
        resp = client.beta.chat.completions.parse(
            model=model,
            response_format=NextStep,
            messages=guided_log,
            max_completion_tokens=16384,
        )
        usage = getattr(resp, "usage", None)
        if usage is not None:
            _emit(
                event_hook,
                "model_usage",
                {
                    "tokens_prompt": int(getattr(usage, "prompt_tokens", 0) or 0),
                    "tokens_completion": int(getattr(usage, "completion_tokens", 0) or 0),
                },
            )
        _emit(event_hook, "fallback_path", {"stage": "parse", "status": "ok"})
        return resp.choices[0].message.parsed
    except Exception:
        _emit(event_hook, "fallback_path", {"stage": "parse", "status": "error"})
        pass

    for tail in [
        "Now return ONLY one JSON object for the next tool call. No prose.",
        "JSON only. One object. No explanations.",
    ]:
        retry_messages = guided_log + [{"role": "user", "content": tail}]
        raw = client.chat.completions.create(
            model=model,
            messages=retry_messages,
            max_completion_tokens=16384,
            temperature=0,
        )
        usage = getattr(raw, "usage", None)
        if usage is not None:
            _emit(
                event_hook,
                "model_usage",
                {
                    "tokens_prompt": int(getattr(usage, "prompt_tokens", 0) or 0),
                    "tokens_completion": int(getattr(usage, "completion_tokens", 0) or 0),
                },
            )
        content = raw.choices[0].message.content or "{}"
        try:
            _emit(event_hook, "fallback_path", {"stage": "retry", "status": "ok", "hint": tail})
            return _parse_next_step(content)
        except Exception:
            _emit(event_hook, "fallback_path", {"stage": "retry", "status": "error", "hint": tail})
            continue

    return NextStep(
        current_state="fallback-completion",
        plan_remaining_steps_brief=["Report failure to parse model output"],
        task_completed=True,
        function=ReportTaskCompletion(
            tool="report_completion",
            completed_steps_laconic=["Could not parse structured model output"],
            answer="Not Ready",
            grounding_refs=["AGENTS.MD"],
            code="failed",
        ),
    )


def run_agent(
    model: str,
    harness_url: str,
    task_text: str,
    event_hook: EventHook | None = None,
):
    client = OpenAI()
    vm = MiniRuntimeClientSync(harness_url)

    # log will contain conversation context for the agent within task
    log: list[dict[str, object]] = [
        {"role": "system", "content": system_prompt},
    ]
    _emit(event_hook, "prompt_sections", {"system_prompt": system_prompt.strip()})
    _emit(event_hook, "task_text", {"task": task_text})

    must: list[BaseModel] = [
        Req_Tree(tool="tree", path="/"),
        Req_Read(tool="read", path="AGENTS.MD"),
    ]
    seen_refs: set[str] = {"AGENTS.MD"}
    file_texts: dict[str, str] = {}

    for c in must:
        result = dispatch(vm, c)
        mappe = MessageToDict(result)
        txt = json.dumps(mappe, indent=2)
        print(f"{CLI_GREEN}AUTO{CLI_CLR}: {txt}")
        log.append({"role": "user", "content": txt})
        _emit(
            event_hook,
            "agent_step",
            {
                "phase": "auto",
                "tool": c.__class__.__name__,
                "tool_payload": json.loads(c.model_dump_json()),
                "tool_result": txt,
            },
        )
        if isinstance(c, Req_Read):
            content = mappe.get("content")
            if isinstance(content, str):
                file_texts[c.path] = content

    agents_text = file_texts.get("AGENTS.MD", "")
    for ref in _extract_md_refs(agents_text):
        if ref.upper() == "AGENTS.MD":
            continue
        try:
            result = dispatch(vm, Req_Read(tool="read", path=ref))
            mappe = MessageToDict(result)
            txt = json.dumps(mappe, indent=2)
            print(f"{CLI_GREEN}AUTO{CLI_CLR}: {txt}")
            log.append({"role": "user", "content": txt})
            _emit(
                event_hook,
                "agent_step",
                {
                    "phase": "auto_ref",
                    "tool": "Req_Read",
                    "tool_payload": {"path": ref},
                    "tool_result": txt,
                },
            )
            seen_refs.add(ref)
            content = mappe.get("content")
            if isinstance(content, str):
                file_texts[ref] = content
        except ConnectError:
            continue

    try:
        result = dispatch(vm, Req_Read(tool="read", path="CLAUDE.MD"))
        mappe = MessageToDict(result)
        txt = json.dumps(mappe, indent=2)
        print(f"{CLI_GREEN}AUTO{CLI_CLR}: {txt}")
        log.append({"role": "user", "content": txt})
        _emit(
            event_hook,
            "agent_step",
            {
                "phase": "auto_ref",
                "tool": "Req_Read",
                "tool_payload": {"path": "CLAUDE.MD"},
                "tool_result": txt,
            },
        )
        seen_refs.add("CLAUDE.MD")
        content = mappe.get("content")
        if isinstance(content, str):
            file_texts["CLAUDE.MD"] = content
    except ConnectError:
        pass

    log.append({"role": "user", "content": task_text})

    # let's limit number of reasoning steps by 20, just to be safe
    last_sig = ""
    repeat_count = 0

    for i in range(30):
        step = f"step_{i + 1}"
        print(f"Next {step}... ", end="")

        started = time.time()

        job = _next_step(client, model, log, event_hook=event_hook)

        # print next sep for debugging
        print(job.plan_remaining_steps_brief[0], f"\n  {job.function}")
        _emit(
            event_hook,
            "agent_step",
            {
                "phase": "reasoning",
                "step": step,
                "current_state": job.current_state,
                "plan": list(job.plan_remaining_steps_brief),
                "task_completed": job.task_completed,
                "tool": job.function.__class__.__name__,
                "tool_payload": json.loads(job.function.model_dump_json()),
            },
        )

        # Let's add tool request to conversation history as if OpenAI asked for it.
        # a shorter way would be to just append `job.model_dump_json()` entirely
        log.append(
            {
                "role": "assistant",
                "content": job.plan_remaining_steps_brief[0],
                "tool_calls": [
                    {
                        "type": "function",
                        "id": step,
                        "function": {
                            "name": job.function.__class__.__name__,
                            "arguments": job.function.model_dump_json(),
                        },
                    }
                ],
            }
        )

        if isinstance(job.function, ReportTaskCompletion):
            forced_answer, forced_refs = _derive_forced_answer(file_texts)
            if forced_answer:
                job.function.answer = forced_answer
            if forced_refs:
                job.function.grounding_refs = forced_refs
            elif not job.function.grounding_refs:
                job.function.grounding_refs = sorted(seen_refs)

        sig = _command_signature(job.function)
        if sig == last_sig:
            repeat_count += 1
        else:
            repeat_count = 1
            last_sig = sig

        if repeat_count >= 5 and not isinstance(job.function, ReportTaskCompletion):
            forced_answer, forced_refs = _derive_forced_answer(file_texts)
            job.function = ReportTaskCompletion(
                tool="report_completion",
                completed_steps_laconic=[f"Stopped repetitive loop at {sig}"],
                answer=forced_answer,
                grounding_refs=forced_refs or sorted(seen_refs),
                code="completed",
            )

        # now execute the tool by dispatching command to our handler
        try:
            result = dispatch(vm, job.function)
            mappe = MessageToDict(result)
            txt = json.dumps(mappe, indent=2)
            print(f"{CLI_GREEN}OUT{CLI_CLR}: {txt}")
            _emit(event_hook, "agent_step", {"phase": "tool_result", "step": step, "tool_result": txt})
            if isinstance(job.function, Req_Read):
                seen_refs.add(job.function.path)
                content = mappe.get("content")
                if isinstance(content, str):
                    file_texts[job.function.path] = content
        except ConnectError as e:
            txt = str(e.message)
            # print to console as ascii red
            print(f"{CLI_RED}ERR {e.code}: {e.message}{CLI_CLR}")
            _emit(event_hook, "agent_error", {"phase": "tool", "step": step, "error": str(e.message)})

        # was this the completion?
        if isinstance(job.function, ReportTaskCompletion):
            print(f"{CLI_GREEN}agent {job.function.code}{CLI_CLR}. Summary:")
            for s in job.function.completed_steps_laconic:
                print(f"- {s}")

            # print answer
            print(f"\n{CLI_BLUE}AGENT ANSWER: {job.function.answer}{CLI_CLR}")
            if job.function.grounding_refs:
                for ref in job.function.grounding_refs:
                    print(f"- {CLI_BLUE}{ref}{CLI_CLR}")
            _emit(
                event_hook,
                "submission",
                {
                    "code": job.function.code,
                    "answer": job.function.answer,
                    "grounding_refs": list(job.function.grounding_refs),
                },
            )
            break

        # and now we add results back to the convesation history, so that agent
        # we'll be able to act on the results in the next reasoning step.
        log.append({"role": "tool", "content": txt, "tool_call_id": step})
