import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
NATIVE_RUNS_DIR = Path(
    os.getenv("NATIVE_RUNS_DIR")
    or str((ROOT.parent / "codex-agent-native" / "runs").resolve())
)

ANALYSIS_DIR = ROOT / "analysis"
REPORTS_DIR = ROOT / "reports"
PROPOSALS_RULES_DIR = ROOT / "proposals" / "rules"
PROPOSALS_CODE_DIR = ROOT / "proposals" / "code"
RULES_PROPOSALS_JSONL = ROOT / "RULES_PROPOSALS.jsonl"
CODE_PROPOSALS_JSONL = ROOT / "CODE_PROPOSALS.jsonl"
INDEX_PATH = ROOT / "index.md"

RULES_VERSIONS_DIR = ROOT / "rules_versions"
RULES_ACTIVE_VERSION = RULES_VERSIONS_DIR / "active_version.txt"
RULES_CHANGELOG = ROOT / "RULES_CHANGELOG.jsonl"
CODE_VERSION_FILE = ROOT / "CODE_VERSION"


@dataclass
class RunTask:
    task_id: str
    workspace: Path
    score: float | None
    passed: bool | None
    run_manifest_row: dict[str, Any]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=True, default=str) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    return raw


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
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def resolve_local_run_id(explicit: str = "") -> str:
    value = explicit.strip()
    if value:
        candidate = NATIVE_RUNS_DIR / value
        if not candidate.exists():
            raise FileNotFoundError(f"local run not found: {candidate}")
        return value

    if not NATIVE_RUNS_DIR.exists():
        raise FileNotFoundError(f"native runs dir not found: {NATIVE_RUNS_DIR}")

    candidates = [p for p in NATIVE_RUNS_DIR.glob("local_run_*") if p.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"no local_run_* dirs in {NATIVE_RUNS_DIR}")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0].name


def load_run_manifest(local_run_id: str) -> list[dict[str, Any]]:
    path = NATIVE_RUNS_DIR / local_run_id / "run_manifest.jsonl"
    rows = load_jsonl(path)
    if not rows:
        raise FileNotFoundError(f"manifest is missing or empty: {path}")
    return rows


def parse_task_ids(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        for part in str(item).split(","):
            clean = part.strip()
            if clean:
                out.append(clean)
    return list(dict.fromkeys(out))


def select_tasks(rows: list[dict[str, Any]], only_task_ids: list[str]) -> list[RunTask]:
    by_task: dict[str, dict[str, Any]] = {}
    for row in rows:
        tid = str(row.get("task_id", "")).strip()
        if not tid:
            continue
        by_task[tid] = row

    task_ids = sorted(by_task.keys())
    if only_task_ids:
        allow = set(only_task_ids)
        task_ids = [t for t in task_ids if t in allow]

    tasks: list[RunTask] = []
    for tid in task_ids:
        row = by_task[tid]
        ws = Path(str(row.get("workspace", "")).strip())
        if not ws.exists():
            continue
        score_raw = row.get("score")
        score = float(score_raw) if isinstance(score_raw, (int, float)) else None
        passed_raw = row.get("passed")
        passed = bool(passed_raw) if isinstance(passed_raw, bool) else None
        tasks.append(
            RunTask(
                task_id=tid,
                workspace=ws,
                score=score,
                passed=passed,
                run_manifest_row=row,
            )
        )
    return tasks


def summarize_tool_calls(path: Path) -> dict[str, Any]:
    rows = load_jsonl(path)
    counts: dict[str, int] = {}
    errors = 0
    for r in rows:
        tool = str(r.get("tool", ""))
        if tool:
            counts[tool] = counts.get(tool, 0) + 1
        if r.get("error"):
            errors += 1
    return {
        "total": len(rows),
        "errors": errors,
        "tool_counts": counts,
    }


def classify_fail(score_detail: list[str]) -> str:
    if not score_detail:
        return "none"
    low = " | ".join(score_detail).lower()
    if "no answer" in low:
        return "no_answer"
    if "missing required ref" in low or "unexpected ref" in low:
        return "ref_mismatch"
    if "answer is incorrect" in low or "expected" in low:
        return "answer_mismatch"
    if "missing file write" in low:
        return "missing_file_write"
    if "missing file delete" in low:
        return "missing_file_delete"
    if "missing expected change" in low:
        return "missing_file_change"
    if "outcome" in low:
        return "outcome_mismatch"
    return "other"


def default_rules_version() -> str:
    return "rv0001"


def active_rules_version() -> str:
    if RULES_ACTIVE_VERSION.exists():
        raw = RULES_ACTIVE_VERSION.read_text(encoding="utf-8").strip()
        if raw:
            return raw
    return default_rules_version()


def ensure_rules_version_store() -> str:
    RULES_VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    version = active_rules_version()
    if not RULES_ACTIVE_VERSION.exists():
        RULES_ACTIVE_VERSION.write_text(version + "\n", encoding="utf-8")

    version_dir = RULES_VERSIONS_DIR / version
    version_dir.mkdir(parents=True, exist_ok=True)
    agents_file = version_dir / "AGENTS.md"
    if not agents_file.exists():
        native_rules_dir = ROOT.parent / "codex-agent-native" / "local-rules"
        native_agents = native_rules_dir / "AGENTS.md"
        if native_agents.exists():
            for p in native_rules_dir.rglob("*"):
                if not p.is_file():
                    continue
                if any(
                    part.startswith("._")
                    for part in p.relative_to(native_rules_dir).parts
                ):
                    continue
                rel = p.relative_to(native_rules_dir)
                dst = version_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            agents_file.write_text("# rules baseline\n", encoding="utf-8")
    return version


def active_code_version() -> str:
    if CODE_VERSION_FILE.exists():
        raw = CODE_VERSION_FILE.read_text(encoding="utf-8").strip()
        if raw:
            return raw
    return "c0001"


def ensure_code_version_store() -> str:
    version = active_code_version()
    if not CODE_VERSION_FILE.exists():
        CODE_VERSION_FILE.write_text(version + "\n", encoding="utf-8")
    return version


def next_numbered_path(root: Path, prefix: str, suffix: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    max_n = 0
    for p in root.glob(f"{prefix}*{suffix}"):
        stem = p.stem
        m = re.match(rf"{re.escape(prefix)}(\d+)$", stem)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return root / f"{prefix}{max_n + 1:04d}{suffix}"


def next_prop_path(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    max_n = 0
    for p in root.glob("prop-*.md"):
        m = re.match(r"prop-(\d+)", p.stem)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return root / f"prop-{max_n + 1:03d}.md"


def safe_json_from_text(text: str) -> dict[str, Any]:
    raw = text.strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(raw[start : end + 1])
            if isinstance(obj, dict):
                return obj
        except Exception:
            return {}
    return {}


def md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def update_index() -> None:
    lines = ["# codex-agent-analytics index", ""]
    sections: list[tuple[str, list[Path]]] = []

    report_files = sorted(
        REPORTS_DIR.glob("r*.md"), key=lambda p: p.stat().st_mtime, reverse=True
    )[:8]
    analysis_files = sorted(
        ANALYSIS_DIR.glob("a*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )[:8]
    rules_props = sorted(
        PROPOSALS_RULES_DIR.rglob("prop-*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:8]
    code_props = sorted(
        PROPOSALS_CODE_DIR.rglob("prop-*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:8]
    apply_reports = sorted(
        (ROOT / "applies").glob("a*.md"), key=lambda p: p.stat().st_mtime, reverse=True
    )[:8]
    deploy_reports = sorted(
        (ROOT / "deploy").glob("d*.md"), key=lambda p: p.stat().st_mtime, reverse=True
    )[:8]

    sections.append(("Latest reports", report_files))
    sections.append(("Latest analysis", analysis_files))
    sections.append(("Latest rules proposals", rules_props))
    sections.append(("Latest code proposals", code_props))
    sections.append(("Latest apply reports", apply_reports))
    sections.append(("Latest deploy reports", deploy_reports))

    for title, files in sections:
        lines.append(f"## {title}")
        if not files:
            lines.append("- (none)")
        else:
            for f in files:
                rel = f.relative_to(ROOT)
                lines.append(f"- [{rel}]({rel.as_posix()})")
        lines.append("")

    lines.append("## Instructions")
    lines.append("- [docs/instructions/index.md](docs/instructions/index.md)")
    lines.append(
        "- [docs/instructions/prompts/index.md](docs/instructions/prompts/index.md)"
    )
    lines.append("")

    lines.append("## References")
    lines.append(
        "- [docs/references/harness-engineering-structure-draft.md](docs/references/harness-engineering-structure-draft.md)"
    )
    lines.append("")

    write_text(INDEX_PATH, "\n".join(lines).strip() + "\n")
