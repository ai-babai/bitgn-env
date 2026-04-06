import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


DECISION_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "current_state": {"type": "string"},
        "plan": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "task_completed": {"type": "boolean"},
        "tool": {
            "type": "string",
            "enum": [
                "tree",
                "search",
                "list",
                "read",
                "write",
                "delete",
                "report_completion",
            ],
        },
        "args": {
            "type": "object",
            "properties": {
                "path": {"type": ["string", "null"]},
                "pattern": {"type": ["string", "null"]},
                "count": {"type": ["integer", "null"]},
                "content": {"type": ["string", "null"]},
                "answer": {"type": ["string", "null"]},
                "grounding_refs": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
            },
            "required": ["path", "pattern", "count", "content", "answer", "grounding_refs"],
            "additionalProperties": False,
        },
    },
    "required": ["current_state", "plan", "task_completed", "tool", "args"],
    "additionalProperties": False,
}


class CodexBridge:
    def __init__(self, model: str, workdir: str, timeout_sec: int = 180) -> None:
        self.model = model
        self.workdir = workdir
        self.timeout_sec = timeout_sec

    def decide(self, prompt: str, schema: dict[str, object] | None = None) -> tuple[dict[str, object], dict[str, int | None]]:
        with tempfile.TemporaryDirectory(prefix="codex-bridge-") as temp_dir:
            temp_path = Path(temp_dir)
            schema_path = temp_path / "schema.json"
            out_path = temp_path / "decision.json"
            schema_path.write_text(json.dumps(schema or DECISION_SCHEMA), encoding="utf-8")

            cmd = [
                "codex",
                "exec",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(out_path),
                "--json",
                "--model",
                self.model,
                "--cd",
                self.workdir,
                prompt,
            ]

            try:
                proc = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_sec,
                )
            except subprocess.CalledProcessError as exc:
                # Fallback: when strict schema fails, retry without schema and parse JSON from the final message.
                fallback_cmd = [
                    "codex",
                    "exec",
                    "--skip-git-repo-check",
                    "--sandbox",
                    "read-only",
                    "--output-last-message",
                    str(out_path),
                    "--json",
                    "--model",
                    self.model,
                    "--cd",
                    self.workdir,
                    prompt + "\nReturn only one valid JSON object that follows the described tool contract.",
                ]
                proc = subprocess.run(
                    fallback_cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_sec,
                )

            usage: dict[str, int | None] = {
                "tokens_prompt": None,
                "tokens_completion": None,
                "tokens_total": None,
            }
            for line in proc.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    evt: dict[str, Any] = json.loads(line)
                except Exception:
                    continue
                if evt.get("type") == "turn.completed" and isinstance(evt.get("usage"), dict):
                    u = evt["usage"]
                    inp = int(u.get("input_tokens", 0) or 0)
                    out = int(u.get("output_tokens", 0) or 0)
                    usage = {
                        "tokens_prompt": inp,
                        "tokens_completion": out,
                        "tokens_total": inp + out,
                    }

            if not out_path.exists() or not out_path.read_text(encoding="utf-8").strip():
                raise RuntimeError(
                    "codex exec produced no structured decision payload; "
                    f"stdout={proc.stdout[:600]} stderr={proc.stderr[:600]}"
                )

            return json.loads(out_path.read_text(encoding="utf-8")), usage
