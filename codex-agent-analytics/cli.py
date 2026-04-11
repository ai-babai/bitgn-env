import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from analytics_helpers import (
    ANALYSIS_DIR,
    CODE_PROPOSALS_JSONL,
    PROPOSALS_CODE_DIR,
    PROPOSALS_RULES_DIR,
    REPORTS_DIR,
    ROOT,
    RULES_ACTIVE_VERSION,
    RULES_CHANGELOG,
    RULES_PROPOSALS_JSONL,
    RULES_VERSIONS_DIR,
    RunTask,
    active_rules_version,
    append_jsonl,
    classify_fail,
    ensure_code_version_store,
    ensure_rules_version_store,
    load_run_manifest,
    md_escape,
    next_numbered_path,
    next_prop_path,
    now_iso,
    now_stamp,
    parse_task_ids,
    read_json,
    resolve_local_run_id,
    safe_json_from_text,
    select_tasks,
    summarize_tool_calls,
    update_index,
    write_json,
    write_text,
)


INSTR_DIR = ROOT / "docs" / "instructions"
PROMPT_POLICY_PATH = INSTR_DIR / "codex-analyzer-prompt.md"
OUTPUT_CONTRACT_PATH = INSTR_DIR / "output-contract.md"
FOCUS_CONTRACT_PATH = INSTR_DIR / "focus-cycle-contract.md"
TARGET_PATH_POLICY_PATH = INSTR_DIR / "target-path-policy.md"
HARNESS_STRUCTURE_REF_PATH = (
    ROOT / "docs" / "references" / "harness-engineering-structure-draft.md"
)
PROMPTS_DIR = INSTR_DIR / "prompts"
ANALYZE_PREAMBLE_PATH = PROMPTS_DIR / "analyze-preamble.md"
APPLY_PREAMBLE_PATH = PROMPTS_DIR / "apply-preamble.md"
DEPLOY_PREAMBLE_PATH = PROMPTS_DIR / "deploy-preamble.md"

APPLIES_DIR = ROOT / "applies"
DEPLOY_DIR = ROOT / "deploy"
DEPLOY_BACKUPS_DIR = DEPLOY_DIR / "backups"
APPLY_LOG_PATH = ROOT / "APPLY_LOG.jsonl"
DEPLOY_LOG_PATH = ROOT / "DEPLOY_LOG.jsonl"
NATIVE_RULES_TARGET = (
    ROOT.parent / "codex-agent-native" / "local-rules" / "AGENTS.md"
).resolve()
NATIVE_RULES_DIR = NATIVE_RULES_TARGET.parent
CODEX_PROFILE = (os.getenv("CODEX_PROFILE") or "").strip()
CODEX_BACKEND = (os.getenv("CODEX_BACKEND") or "omniroute").strip().lower()

ALLOWED_CODE_TARGETS = {
    "codex-agent-native/runner.py",
    "codex-agent-native/runtime_tools.py",
    "codex-agent-native/tool_gateway.py",
    "codex-agent-native/workspace.py",
    "codex-agent-native/harness_seed.py",
}

CODE_TARGET_ALIASES = {
    "runner.py": "codex-agent-native/runner.py",
    "runtime_tools.py": "codex-agent-native/runtime_tools.py",
    "tool_gateway.py": "codex-agent-native/tool_gateway.py",
    "workspace.py": "codex-agent-native/workspace.py",
    "harness_seed.py": "codex-agent-native/harness_seed.py",
}

RUNTIME_MAX_AGENTS_LINES = 100
RUNTIME_SOFT_AGENTS_LINES = 95
RUNTIME_MAX_AGENTS_LINE_LENGTH = 320
RUNTIME_MAX_INCLUDE_FILES = 8
RUNTIME_MAX_INCLUDE_FILE_LINES = 80
RUNTIME_MAX_INCLUDE_TOTAL_LINES = 220
RUNTIME_MAX_INCLUDE_LINE_LENGTH = 320
_RULES_INCLUDE_RE = re.compile(r"^\s*!include\s+([A-Za-z0-9_./-]+)\s*$")


def _read_doc(path: Path, fallback: str) -> str:
    if path.exists():
        try:
            raw = path.read_text(encoding="utf-8").strip()
            if raw:
                return raw
        except Exception:
            return fallback
    return fallback


def _mode_preamble(mode: str) -> str:
    key = mode.strip().lower()
    mapping = {
        "analyze": ANALYZE_PREAMBLE_PATH,
        "apply": APPLY_PREAMBLE_PATH,
        "deploy": DEPLOY_PREAMBLE_PATH,
    }
    path = mapping.get(key)
    if not path:
        return ""
    return _read_doc(path, "")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    return _sha256_text(path.read_text(encoding="utf-8"))


def _normalize_rules_include_path(raw: str) -> str:
    value = str(raw or "").strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    if not value:
        raise ValueError("Empty include path")
    if value.startswith("/"):
        raise ValueError(f"Include path must be relative: {value}")

    p = Path(value)
    if any(part in {"", ".", ".."} for part in p.parts):
        raise ValueError(f"Invalid include path segments: {value}")
    if not p.parts or p.parts[0] != "includes":
        raise ValueError(f"Include path must stay under includes/: {value}")
    if p.suffix.lower() != ".md":
        raise ValueError(f"Include path must target .md file: {value}")
    if any(part.startswith("._") for part in p.parts):
        raise ValueError(f"Include path cannot use macOS metadata files: {value}")
    return p.as_posix()


def _extract_rules_include_paths(agents_text: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for line in agents_text.splitlines():
        m = _RULES_INCLUDE_RE.match(line)
        if not m:
            continue
        rel = _normalize_rules_include_path(m.group(1))
        if rel in seen:
            continue
        seen.add(rel)
        out.append(rel)
    return out


def _validate_runtime_rules_package(
    *, agents_text: str, include_files: dict[str, str]
) -> dict[str, int]:
    agents_lines = len(agents_text.splitlines())
    if agents_lines > RUNTIME_MAX_AGENTS_LINES:
        raise SystemExit(
            f"apply rejected: AGENTS.md exceeds {RUNTIME_MAX_AGENTS_LINES} lines ({agents_lines})"
        )
    for idx, line in enumerate(agents_text.splitlines(), start=1):
        if len(line) > RUNTIME_MAX_AGENTS_LINE_LENGTH:
            raise SystemExit(
                "apply rejected: AGENTS.md line exceeds "
                f"{RUNTIME_MAX_AGENTS_LINE_LENGTH} chars (line {idx})"
            )

    include_paths = _extract_rules_include_paths(agents_text)
    if len(include_paths) > RUNTIME_MAX_INCLUDE_FILES:
        raise SystemExit(
            f"apply rejected: include files exceed {RUNTIME_MAX_INCLUDE_FILES} ({len(include_paths)})"
        )

    total_include_lines = 0
    for rel in include_paths:
        content = include_files.get(rel)
        if content is None:
            raise SystemExit(f"apply rejected: missing include content for {rel}")
        include_lines = len(content.splitlines())
        if include_lines > RUNTIME_MAX_INCLUDE_FILE_LINES:
            raise SystemExit(
                f"apply rejected: include exceeds {RUNTIME_MAX_INCLUDE_FILE_LINES} lines ({rel}: {include_lines})"
            )
        for idx, line in enumerate(content.splitlines(), start=1):
            if len(line) > RUNTIME_MAX_INCLUDE_LINE_LENGTH:
                raise SystemExit(
                    "apply rejected: include line exceeds "
                    f"{RUNTIME_MAX_INCLUDE_LINE_LENGTH} chars ({rel}:{idx})"
                )
        if any(_RULES_INCLUDE_RE.match(line) for line in content.splitlines()):
            raise SystemExit(
                f"apply rejected: nested include directive not allowed in {rel}"
            )
        total_include_lines += include_lines

    if total_include_lines > RUNTIME_MAX_INCLUDE_TOTAL_LINES:
        raise SystemExit(
            f"apply rejected: include total exceeds {RUNTIME_MAX_INCLUDE_TOTAL_LINES} lines ({total_include_lines})"
        )

    return {
        "agents_lines": agents_lines,
        "includes_count": len(include_paths),
        "includes_total_lines": total_include_lines,
    }


def _next_rules_version() -> str:
    max_n = 0
    for p in RULES_VERSIONS_DIR.glob("rv*"):
        if not p.is_dir():
            continue
        m = re.fullmatch(r"rv(\d{4})", p.name)
        if not m:
            continue
        max_n = max(max_n, int(m.group(1)))
    return f"rv{max_n + 1:04d}"


def _resolve_rules_proposal_path(args: argparse.Namespace, rules_version: str) -> Path:
    direct = str(getattr(args, "proposal_path", "") or "").strip()
    if direct:
        p = Path(direct)
        if not p.is_absolute():
            p = (ROOT / p).resolve()
        if not p.exists():
            raise FileNotFoundError(f"proposal path not found: {p}")
        return p

    pid = str(getattr(args, "proposal_id", "") or "").strip()
    if pid:
        stem = pid if pid.startswith("prop-") else f"prop-{pid}"
        p = PROPOSALS_RULES_DIR / rules_version / f"{stem}.md"
        if not p.exists():
            raise FileNotFoundError(
                f"proposal id not found in version {rules_version}: {p}"
            )
        return p

    root = PROPOSALS_RULES_DIR / rules_version
    candidates = [p for p in root.glob("prop-*.md") if p.is_file()]
    if not candidates:
        raise FileNotFoundError(f"no rules proposals found in {root}")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _strip_code_fence(text: str) -> str:
    raw = text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```"):
            if lines[-1].startswith("```"):
                return "\n".join(lines[1:-1]).strip()
            return "\n".join(lines[1:]).strip()
    return raw


def _normalize_text_payload(value: str) -> str:
    text = str(value)
    if "\\n" in text and "\n" not in text:
        text = text.replace("\\r\\n", "\n").replace("\\n", "\n")
    if '\\"' in text and '"' not in text:
        text = text.replace('\\"', '"')
    return text


def _count_changed_lines(before: str, after: str) -> int:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    i = 0
    j = 0
    changed = 0
    while i < len(before_lines) and j < len(after_lines):
        if before_lines[i] == after_lines[j]:
            i += 1
            j += 1
            continue
        changed += 1
        if i + 1 < len(before_lines) and before_lines[i + 1] == after_lines[j]:
            i += 1
        elif j + 1 < len(after_lines) and before_lines[i] == after_lines[j + 1]:
            j += 1
        else:
            i += 1
            j += 1
    changed += (len(before_lines) - i) + (len(after_lines) - j)
    return changed


def _extract_focus_from_rules_proposal(text: str) -> tuple[str, str, str]:
    problem = ""
    solution_type = "rules"
    primary_task = ""
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("- problem:") and not problem:
            problem = s.split(":", 1)[1].strip()
        elif s.startswith("- solution_type:"):
            solution_type = s.split(":", 1)[1].strip() or "rules"
        elif s.startswith("- primary_task:"):
            primary_task = s.split(":", 1)[1].strip()
    return problem, solution_type, primary_task


def _coerce_apply_payload(raw_text: str) -> dict[str, Any]:
    text = _strip_code_fence(raw_text).strip()
    if not text:
        return {}

    parsed = safe_json_from_text(text)
    if isinstance(parsed, dict) and parsed:
        agents = parsed.get("agents_md")
        if isinstance(agents, str) and agents.strip():
            payload = {
                "agents_md": _normalize_text_payload(agents).strip(),
                "extra_files": parsed.get("extra_files", []),
                "harness_docs": parsed.get("harness_docs", []),
            }
            return payload

    return {
        "agents_md": _normalize_text_payload(text),
        "extra_files": [],
        "harness_docs": [],
    }


def _normalize_rules_extra_files(raw: Any) -> list[dict[str, str]]:
    items = raw if isinstance(raw, list) else []
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        rel = _clean_path(str(item.get("path", "")))
        content = item.get("content", "")
        if not isinstance(content, str):
            continue
        content = _normalize_text_payload(content)
        if not rel or rel in seen:
            continue
        if rel.startswith("/") or rel.startswith("../"):
            continue
        if rel.startswith("codex-agent-analytics/rules_versions/"):
            parts = rel.split("/")
            if len(parts) >= 5:
                rel = "/".join(parts[3:])
            else:
                continue
        elif rel.startswith("rules_versions/"):
            parts = rel.split("/")
            if len(parts) >= 4:
                rel = "/".join(parts[2:])
            else:
                continue
        if not rel.startswith("includes/"):
            continue
        if ".." in Path(rel).parts:
            continue
        if not rel.endswith(".md"):
            continue
        seen.add(rel)
        out.append({"path": rel, "content": content.rstrip() + "\n"})
    return out


def _normalize_harness_doc_files(raw: Any) -> list[dict[str, str]]:
    items = raw if isinstance(raw, list) else []
    out: list[dict[str, str]] = []
    seen: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            continue
        rel = _clean_path(str(item.get("path", "")))
        content = item.get("content", "")
        if not isinstance(content, str):
            continue
        content = _normalize_text_payload(content)
        if not rel:
            continue

        if rel.startswith("/") or rel.startswith("../"):
            continue

        if rel.startswith("codex-agent-analytics/"):
            rel = rel[len("codex-agent-analytics/") :]

        if rel in seen:
            continue
        if rel != "ARCHITECTURE.md" and not rel.startswith("docs/"):
            continue
        if ".." in Path(rel).parts:
            continue
        if not (rel.endswith(".md") or rel.endswith(".txt")):
            continue

        promoted = f"codex-agent-analytics/{rel}"
        if not _is_harness_structure_doc_target(promoted):
            continue

        seen.add(rel)
        out.append({"path": rel, "content": content.rstrip() + "\n"})

    return out


def _changed_lines_for_rules_package(
    before_agents: str,
    after_agents: str,
    before_extra: dict[str, str],
    after_extra: dict[str, str],
    before_harness_docs: dict[str, str] | None = None,
    after_harness_docs: dict[str, str] | None = None,
) -> int:
    changed = _count_changed_lines(before_agents, after_agents)
    keys = set(before_extra.keys()) | set(after_extra.keys())
    for key in sorted(keys):
        changed += _count_changed_lines(
            before_extra.get(key, ""), after_extra.get(key, "")
        )
    if before_harness_docs is not None or after_harness_docs is not None:
        docs_before = before_harness_docs or {}
        docs_after = after_harness_docs or {}
        doc_keys = set(docs_before.keys()) | set(docs_after.keys())
        for key in sorted(doc_keys):
            changed += _count_changed_lines(
                docs_before.get(key, ""), docs_after.get(key, "")
            )
    return changed


def _rules_version_extra_files(version_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    includes_dir = version_dir / "includes"
    if not includes_dir.exists():
        return out
    for p in sorted(includes_dir.rglob("*.md")):
        if not p.is_file():
            continue
        if any(part.startswith("._") for part in p.relative_to(version_dir).parts):
            continue
        rel = p.relative_to(version_dir).as_posix()
        out[rel] = p.read_text(encoding="utf-8")
    return out


def _existing_harness_doc_paths() -> list[str]:
    out: list[str] = []
    arch = ROOT / "ARCHITECTURE.md"
    if arch.exists():
        out.append("ARCHITECTURE.md")

    docs_root = ROOT / "docs"
    if docs_root.exists():
        for p in sorted(docs_root.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(ROOT).as_posix()
            if _is_harness_structure_doc_target(f"codex-agent-analytics/{rel}"):
                out.append(rel)
    return out


def _copy_rules_version_tree(*, source_dir: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for child in target_dir.iterdir():
        if child.is_file() or child.is_symlink():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)

    for p in source_dir.rglob("*"):
        rel = p.relative_to(source_dir)
        if any(part.startswith("._") for part in rel.parts):
            continue
        dst = target_dir / rel
        if p.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        if p.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)


def _rules_default_target(rules_version: str) -> str:
    return f"codex-agent-analytics/rules_versions/{rules_version}/AGENTS.md"


def _instruction_doc_targets() -> set[str]:
    out: set[str] = set()
    if not INSTR_DIR.exists():
        return out
    for p in INSTR_DIR.rglob("*.md"):
        rel = p.relative_to(INSTR_DIR).as_posix()
        out.add(f"codex-agent-analytics/docs/instructions/{rel}")
    return out


def _is_harness_structure_doc_target(path: str) -> bool:
    candidate = _clean_path(path)
    if not candidate:
        return False

    exact = {
        "codex-agent-analytics/ARCHITECTURE.md",
        "codex-agent-analytics/docs/DESIGN.md",
        "codex-agent-analytics/docs/FRONTEND.md",
        "codex-agent-analytics/docs/PLANS.md",
        "codex-agent-analytics/docs/PRODUCT_SENSE.md",
        "codex-agent-analytics/docs/QUALITY_SCORE.md",
        "codex-agent-analytics/docs/RELIABILITY.md",
        "codex-agent-analytics/docs/SECURITY.md",
    }
    if candidate in exact:
        return True

    prefixes = (
        "codex-agent-analytics/docs/design-docs/",
        "codex-agent-analytics/docs/exec-plans/",
        "codex-agent-analytics/docs/generated/",
        "codex-agent-analytics/docs/product-specs/",
        "codex-agent-analytics/docs/references/",
    )
    return any(candidate.startswith(prefix) for prefix in prefixes)


def _clean_path(raw: str) -> str:
    value = str(raw or "").strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    return value


def _normalize_include_rel(raw: str) -> str:
    value = _clean_path(raw)
    if not value:
        return ""
    if value.startswith("/") or value.startswith("../"):
        return ""
    if ".." in Path(value).parts:
        return ""
    if not value.startswith("includes/"):
        return ""
    if not value.endswith(".md"):
        return ""
    return value


def _normalize_rules_targets(
    raw: Any, rules_version: str
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    default_target = _rules_default_target(rules_version)
    allowed_docs = _instruction_doc_targets()

    items = raw if isinstance(raw, list) else []
    out: list[dict[str, str]] = []
    validations: list[dict[str, str]] = []

    def add_target(path: str, summary: str) -> None:
        if any(t.get("path") == path for t in out):
            return
        out.append({"path": path, "change_summary": summary or "targeted change"})

    for item in items:
        if not isinstance(item, dict):
            continue
        raw_path = _clean_path(str(item.get("path", "")))
        summary = str(item.get("change_summary", "")).strip() or "targeted change"
        if not raw_path:
            continue

        candidate = raw_path
        if candidate in {
            "AGENTS.md",
            "local-rules.md",
            "docs/instructions/local-rules.md",
        }:
            candidate = default_target

        if candidate.startswith("rules_versions/") and candidate.endswith("/AGENTS.md"):
            final_path = default_target
            status = "normalized"
            reason = "rules_versions path normalized to active rules version"
        elif "/includes/" in candidate and candidate.endswith(".md"):
            rel_include = ""
            if candidate.startswith("rules_versions/"):
                tail = candidate[len("rules_versions/") :]
                _, _, rest = tail.partition("/")
                rel_include = _normalize_include_rel(rest)
            elif candidate.startswith("codex-agent-analytics/rules_versions/"):
                tail = candidate[len("codex-agent-analytics/rules_versions/") :]
                _, _, rest = tail.partition("/")
                rel_include = _normalize_include_rel(rest)
            elif candidate.startswith("includes/"):
                rel_include = _normalize_include_rel(candidate)

            if rel_include:
                final_path = f"codex-agent-analytics/rules_versions/{rules_version}/{rel_include}"
                status = "normalized"
                reason = "rules include path normalized to active rules version"
            else:
                final_path = default_target
                status = "normalized"
                reason = "invalid include path; normalized to active rules AGENTS"
        elif candidate.startswith(
            "codex-agent-analytics/rules_versions/"
        ) and candidate.endswith("/AGENTS.md"):
            final_path = default_target
            status = "normalized"
            reason = "rules AGENTS path normalized to active rules version"
        elif candidate.startswith("docs/instructions/"):
            promoted = f"codex-agent-analytics/{candidate}"
            if promoted in allowed_docs:
                final_path = promoted
                status = "accepted"
                reason = "existing instruction doc target"
            else:
                final_path = default_target
                status = "normalized"
                reason = "instruction path missing; normalized to active rules AGENTS"
        elif candidate.startswith("codex-agent-analytics/docs/instructions/"):
            if candidate in allowed_docs:
                final_path = candidate
                status = "accepted"
                reason = "existing instruction doc target"
            else:
                final_path = default_target
                status = "normalized"
                reason = "instruction path missing; normalized to active rules AGENTS"
        elif candidate == "ARCHITECTURE.md" or candidate.startswith("docs/"):
            promoted = (
                "codex-agent-analytics/ARCHITECTURE.md"
                if candidate == "ARCHITECTURE.md"
                else f"codex-agent-analytics/{candidate}"
            )
            if _is_harness_structure_doc_target(promoted):
                final_path = promoted
                status = "accepted"
                reason = "allowed harness-structure doc target"
            else:
                final_path = default_target
                status = "normalized"
                reason = (
                    "docs path outside harness map; normalized to active rules AGENTS"
                )
        elif (
            candidate.startswith("codex-agent-analytics/docs/")
            or candidate == "codex-agent-analytics/ARCHITECTURE.md"
        ):
            if _is_harness_structure_doc_target(candidate):
                final_path = candidate
                status = "accepted"
                reason = "allowed harness-structure doc target"
            else:
                final_path = default_target
                status = "normalized"
                reason = (
                    "docs path outside harness map; normalized to active rules AGENTS"
                )
        elif candidate == default_target:
            final_path = candidate
            status = "accepted"
            reason = "active rules file"
        else:
            final_path = default_target
            status = "normalized"
            reason = "path outside rules whitelist; normalized to active rules AGENTS"

        add_target(final_path, summary)
        validations.append(
            {
                "status": status,
                "original_path": raw_path,
                "final_path": final_path,
                "reason": reason,
            }
        )

    if not out:
        add_target(
            default_target,
            "Apply one generalized instruction refinement tied to the diagnosed fail group.",
        )
        validations.append(
            {
                "status": "normalized",
                "original_path": "",
                "final_path": default_target,
                "reason": "no valid rules targets provided; defaulted to active rules AGENTS",
            }
        )

    return out, validations


def _normalize_code_targets(
    raw: Any,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    items = raw if isinstance(raw, list) else []
    out: list[dict[str, str]] = []
    validations: list[dict[str, str]] = []

    def add_target(path: str, summary: str) -> None:
        if any(t.get("path") == path for t in out):
            return
        out.append({"path": path, "change_summary": summary or "targeted change"})

    for item in items:
        if not isinstance(item, dict):
            continue
        raw_path = _clean_path(str(item.get("path", "")))
        summary = str(item.get("change_summary", "")).strip() or "targeted change"
        if not raw_path:
            continue

        candidate = CODE_TARGET_ALIASES.get(raw_path, raw_path)
        if candidate in ALLOWED_CODE_TARGETS:
            add_target(candidate, summary)
            validations.append(
                {
                    "status": "accepted",
                    "original_path": raw_path,
                    "final_path": candidate,
                    "reason": "allowed native code target",
                }
            )
        else:
            validations.append(
                {
                    "status": "rejected",
                    "original_path": raw_path,
                    "final_path": "",
                    "reason": "path outside code whitelist",
                }
            )

    return out, validations


def _build_prompt(task: RunTask) -> str:
    instruction = (
        (task.workspace / "instruction.txt").read_text(encoding="utf-8")
        if (task.workspace / "instruction.txt").exists()
        else ""
    )
    score = read_json(task.workspace / "score.json")
    submission = read_json(task.workspace / "submission.json")
    tool_summary = summarize_tool_calls(task.workspace / "tool_calls.jsonl")
    score_detail = score.get("score_detail", [])
    if not isinstance(score_detail, list):
        score_detail = []

    schema = {
        "task_id": task.task_id,
        "status": "pass_or_fail",
        "fail_group": "one_short_token",
        "diagnosis": "1-3 sentences",
        "code_assessment": {
            "classification": "blocking_or_optional",
            "reason": "why this classification",
            "rules_insufficient_evidence": "required when blocking",
        },
        "proposal_rules": {
            "title": "short title",
            "hypothesis": "generalized hypothesis",
            "change": "instruction-level change without task-specific literals",
            "target_files": [
                {
                    "path": "repo-relative path",
                    "change_summary": "specific edit plan",
                }
            ],
            "rollback": "how to revert",
            "simplicity": {
                "max_files_changed": 2,
                "max_lines_changed": 30,
                "single_hypothesis": True,
            },
            "generalization_check": {
                "passes": True,
                "reason": "why",
            },
        },
        "proposal_code": {
            "title": "short title",
            "hypothesis": "runtime/logic hypothesis",
            "change": "code-level improvement proposal only",
            "target_files": [
                {
                    "path": "codex-agent-native/*.py",
                    "change_summary": "specific edit plan",
                }
            ],
            "rollback": "how to revert",
            "is_blocker": True,
            "blocker_reason": "required if blocker",
            "evidence": ["key traces"],
        },
    }

    policy_md = _read_doc(
        PROMPT_POLICY_PATH,
        "Harness-first. Return JSON only. Optional code -> proposal_code null. If unsure choose optional.",
    )
    output_contract_md = _read_doc(
        OUTPUT_CONTRACT_PATH,
        "Provide task_id/status/fail_group/diagnosis/code_assessment/proposal_rules and focus fields.",
    )
    focus_contract_md = _read_doc(
        FOCUS_CONTRACT_PATH,
        "One run should support one focus cycle with primary task and affected tasks.",
    )
    target_path_policy_md = _read_doc(
        TARGET_PATH_POLICY_PATH,
        "Rules targets: active rules AGENTS/includes and instruction docs.",
    )
    harness_structure_ref_md = _read_doc(
        HARNESS_STRUCTURE_REF_PATH,
        "Harness structure map reference is unavailable.",
    )
    mode_preamble = _mode_preamble("analyze")

    return (
        "Execution mode: analyze\n"
        f"{mode_preamble}\n\n"
        "You are analyzing BitGN native solve artifacts. Return JSON only.\n\n"
        "Policy reference (markdown):\n"
        f"{policy_md}\n\n"
        "Focus-cycle contract (markdown):\n"
        f"{focus_contract_md}\n\n"
        "Target path policy (markdown):\n"
        f"{target_path_policy_md}\n\n"
        "Harness structure reference map (markdown):\n"
        f"{harness_structure_ref_md}\n\n"
        "Output contract (markdown):\n"
        f"{output_contract_md}\n\n"
        f"Task id: {task.task_id}\n"
        f"Workspace: {task.workspace}\n"
        f"Instruction:\n{instruction}\n\n"
        f"Score summary:\n{json.dumps(score, ensure_ascii=True, indent=2)}\n\n"
        f"Submission:\n{json.dumps(submission, ensure_ascii=True, indent=2)}\n\n"
        f"Tool summary:\n{json.dumps(tool_summary, ensure_ascii=True, indent=2)}\n\n"
        f"Target JSON schema:\n{json.dumps(schema, ensure_ascii=True, indent=2)}\n"
    )


def _run_codex_analysis(task: RunTask, model: str) -> dict[str, Any]:
    prompt = _build_prompt(task)
    out_path = task.workspace / "analytics_codex_last_message.json"

    cmd = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--output-last-message",
        str(out_path),
        "--model",
        model,
    ]
    if CODEX_PROFILE:
        cmd.extend(["--profile", CODEX_PROFILE])
    elif CODEX_BACKEND == "spark":
        cmd.extend(["-c", "model_provider=openai"])
    cmd.extend(
        [
            "--cd",
            str(ROOT),
            prompt,
        ]
    )

    proc = subprocess.run(cmd, text=True, capture_output=True)
    text = ""
    if out_path.exists():
        text = out_path.read_text(encoding="utf-8")
    if not text.strip():
        text = proc.stdout or ""

    parsed = safe_json_from_text(text)
    parsed["_codex_returncode"] = proc.returncode
    parsed["_codex_stdout_tail"] = (proc.stdout or "")[-2000:]
    parsed["_codex_stderr_tail"] = (proc.stderr or "")[-2000:]
    return parsed


def _fallback_analysis(task: RunTask) -> dict[str, Any]:
    score = read_json(task.workspace / "score.json")
    score_detail = score.get("score_detail", [])
    if not isinstance(score_detail, list):
        score_detail = []
    fail_group = classify_fail([str(x) for x in score_detail])
    passed = bool(score.get("passed", False))

    code_assessment = {
        "classification": "optional",
        "reason": "Fallback mode keeps harness-first default; no proven code blocker extracted.",
        "rules_insufficient_evidence": "",
    }

    return {
        "task_id": task.task_id,
        "status": "pass" if passed else "fail",
        "fail_group": fail_group,
        "diagnosis": "Heuristic fallback analysis due to empty/non-json Codex output.",
        "code_assessment": code_assessment,
        "proposal_rules": {
            "title": "tighten generic completion checklist",
            "hypothesis": "More explicit generic completion policy reduces repeated format/process misses.",
            "change": "Add one generic pre-completion checklist item in rules; avoid task-specific literals.",
            "target_files": [
                {
                    "path": "codex-agent-analytics/rules_versions/rv0001/AGENTS.md",
                    "change_summary": "Append one short generic pre-completion checklist rule.",
                }
            ],
            "rollback": "Revert the added checklist line from next rules version.",
            "simplicity": {
                "max_files_changed": 1,
                "max_lines_changed": 10,
                "single_hypothesis": True,
            },
            "generalization_check": {
                "passes": True,
                "reason": "No task-specific ids or exact expected values in proposal.",
            },
        },
        "proposal_code": None,
        "_fallback": True,
    }


def _normalize_code_assessment(
    row: dict[str, Any], code: dict[str, Any] | None
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    assessment_obj = row.get("code_assessment")
    assessment_raw: dict[str, Any] = (
        assessment_obj if isinstance(assessment_obj, dict) else {}
    )
    classification = str(assessment_raw.get("classification", "")).strip().lower()
    reason = str(assessment_raw.get("reason", "")).strip()
    rules_insufficient_evidence = str(
        assessment_raw.get("rules_insufficient_evidence", "")
    ).strip()

    if classification != "blocking":
        classification = "optional"

    if classification == "optional":
        if not reason:
            reason = "Harness-first default: no proven code blocker signal."
        normalized_assessment = {
            "classification": "optional",
            "reason": reason,
            "rules_insufficient_evidence": "",
        }
        return normalized_assessment, None

    # Blocking is accepted only with explicit proof that rules are insufficient.
    if not reason or not rules_insufficient_evidence:
        normalized_assessment = {
            "classification": "optional",
            "reason": "Downgraded to optional: missing explicit blocker proof or why harness/rules are insufficient.",
            "rules_insufficient_evidence": "",
        }
        return normalized_assessment, None

    if not isinstance(code, dict):
        normalized_assessment = {
            "classification": "optional",
            "reason": "Downgraded to optional: blocking classification was provided without concrete code proposal.",
            "rules_insufficient_evidence": "",
        }
        return normalized_assessment, None

    normalized_assessment = {
        "classification": "blocking",
        "reason": reason,
        "rules_insufficient_evidence": rules_insufficient_evidence,
    }

    code["is_blocker"] = True
    if not str(code.get("blocker_reason", "")).strip():
        code["blocker_reason"] = reason
    return normalized_assessment, code


def _normalize_task_result(row: dict[str, Any], rules_version: str) -> dict[str, Any]:
    rules_raw = row.get("proposal_rules")
    code_raw = row.get("proposal_code")
    rules: dict[str, Any] = rules_raw if isinstance(rules_raw, dict) else {}
    code: dict[str, Any] | None = code_raw if isinstance(code_raw, dict) else None

    rules_targets, rules_target_validation = _normalize_rules_targets(
        rules.get("target_files"), rules_version
    )
    assessment, code = _normalize_code_assessment(row, code)

    if isinstance(code, dict):
        code_targets, code_target_validation = _normalize_code_targets(
            code.get("target_files")
        )
        if not code_targets:
            assessment = {
                "classification": "optional",
                "reason": "Downgraded to optional: blocking proposal has no code targets in whitelist.",
                "rules_insufficient_evidence": "",
            }
            row["code_target_validation"] = code_target_validation
            code = None
        else:
            code["target_files"] = code_targets
            row["code_target_validation"] = code_target_validation
    else:
        row["code_target_validation"] = []

    rules["target_files"] = rules_targets
    row["rules_target_validation"] = rules_target_validation
    row["code_assessment"] = assessment
    row["proposal_rules"] = rules
    row["proposal_code"] = code
    return row


def _pick_primary_task(
    task_results: list[dict[str, Any]], focus_task: str = ""
) -> dict[str, Any]:
    if not task_results:
        return {}

    wanted = focus_task.strip()
    if wanted:
        for row in task_results:
            if str(row.get("task_id", "")).strip() == wanted:
                return row

    failed = [r for r in task_results if not bool(r.get("passed", False))]
    if not failed:
        return task_results[0]

    group_counts: dict[str, int] = {}
    for row in failed:
        fg = str(row.get("fail_group", "other") or "other")
        group_counts[fg] = group_counts.get(fg, 0) + 1

    failed.sort(
        key=lambda r: (
            -group_counts.get(str(r.get("fail_group", "other") or "other"), 0),
            str(r.get("task_id", "")),
        )
    )
    return failed[0]


def _affected_tasks(
    task_results: list[dict[str, Any]], primary_row: dict[str, Any]
) -> list[str]:
    primary_task = str(primary_row.get("task_id", "")).strip()
    if not primary_task:
        return []

    primary_group = str(primary_row.get("fail_group", "")).strip()
    out: list[str] = [primary_task]
    for row in task_results:
        tid = str(row.get("task_id", "")).strip()
        if not tid or tid == primary_task:
            continue
        if bool(row.get("passed", False)):
            continue
        if str(row.get("fail_group", "")).strip() == primary_group:
            out.append(tid)
    return out


def _focus_problem_text(primary_row: dict[str, Any]) -> str:
    task_id = str(primary_row.get("task_id", ""))
    fail_group = str(primary_row.get("fail_group", "other") or "other")
    diagnosis = str(primary_row.get("diagnosis", "")).strip()
    if diagnosis:
        return f"Task {task_id} fails with fail_group={fail_group}. {diagnosis}"
    return f"Task {task_id} fails with fail_group={fail_group}."


def _analyze_task(task: RunTask, model: str) -> dict[str, Any]:
    codex_payload = _run_codex_analysis(task, model=model)
    if (
        not codex_payload
        or "proposal_rules" not in codex_payload
        or "code_assessment" not in codex_payload
    ):
        codex_payload = _fallback_analysis(task)
    codex_payload["task_id"] = task.task_id
    codex_payload["workspace"] = str(task.workspace)
    codex_payload["score"] = task.score
    codex_payload["passed"] = task.passed
    return codex_payload


def run_analyze(args: argparse.Namespace) -> None:
    local_run_id = resolve_local_run_id(getattr(args, "run_id", "") or "")
    rows = load_run_manifest(local_run_id)
    requested_tasks = parse_task_ids(list(getattr(args, "tasks", []) or []))
    tasks = select_tasks(rows, requested_tasks)
    if not tasks:
        raise SystemExit("No tasks selected for analysis")

    rules_version = ensure_rules_version_store()
    code_version = ensure_code_version_store()
    model = str(
        getattr(args, "model", "") or os.getenv("CODEX_MODEL") or "gpt-5.3-codex"
    )
    parallelism = max(1, int(getattr(args, "parallelism", 2) or 2))

    print(
        f"ANALYZE_START local_run_id={local_run_id} tasks={[t.task_id for t in tasks]} parallelism={parallelism} model={model}"
    )

    task_results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(parallelism, len(tasks))) as pool:
        fut_map = {pool.submit(_analyze_task, t, model): t for t in tasks}
        for fut in as_completed(fut_map):
            t = fut_map[fut]
            try:
                payload = fut.result()
            except Exception as exc:
                payload = _fallback_analysis(t)
                payload["_analyze_error"] = str(exc)
                payload["task_id"] = t.task_id
                payload["workspace"] = str(t.workspace)
                payload["score"] = t.score
                payload["passed"] = t.passed
            task_results.append(payload)
            print(f"ANALYZE_TASK task={t.task_id} done")

    task_results.sort(key=lambda x: str(x.get("task_id", "")))
    task_results = [_normalize_task_result(r, rules_version) for r in task_results]

    primary_row = _pick_primary_task(
        task_results, str(getattr(args, "focus_task", "") or "")
    )
    if not primary_row:
        raise SystemExit("No primary task selected for focus analysis")
    primary_task_id = str(primary_row.get("task_id", ""))
    affected_tasks = _affected_tasks(task_results, primary_row)
    problem_text = _focus_problem_text(primary_row)

    primary_code_assessment_obj = primary_row.get("code_assessment")
    primary_rules_obj = primary_row.get("proposal_rules")
    primary_code_obj = primary_row.get("proposal_code")
    primary_code_assessment: dict[str, Any] = (
        primary_code_assessment_obj
        if isinstance(primary_code_assessment_obj, dict)
        else {}
    )
    primary_rules: dict[str, Any] = (
        primary_rules_obj if isinstance(primary_rules_obj, dict) else {}
    )
    primary_code: dict[str, Any] = (
        primary_code_obj if isinstance(primary_code_obj, dict) else {}
    )
    code_is_blocking = (
        bool(primary_code.get("is_blocker", False))
        and str(primary_code_assessment.get("classification", "")).lower() == "blocking"
    )
    solution_type = "code_blocking" if code_is_blocking else "rules"

    analysis_path = next_numbered_path(ANALYSIS_DIR, "a", ".json")
    report_path = next_numbered_path(REPORTS_DIR, "r", ".md")

    analysis_payload = {
        "ts": now_iso(),
        "local_run_id": local_run_id,
        "model": model,
        "parallelism": parallelism,
        "task_count": len(task_results),
        "rules_version": rules_version,
        "code_version": code_version,
        "focus": {
            "primary_task_id": primary_task_id,
            "affected_tasks": affected_tasks,
            "problem": problem_text,
            "solution_type": solution_type,
        },
        "tasks": task_results,
    }
    write_json(analysis_path, analysis_payload)

    rules_root = PROPOSALS_RULES_DIR / rules_version
    code_root = PROPOSALS_CODE_DIR / code_version
    rules_prop_path = next_prop_path(rules_root)
    code_prop_path = next_prop_path(code_root)

    rules_queue_row = {
        "ts": now_iso(),
        "local_run_id": local_run_id,
        "rules_version": rules_version,
        "tasks": [],
    }
    code_queue_row = {
        "ts": now_iso(),
        "local_run_id": local_run_id,
        "code_version": code_version,
        "tasks": [],
    }

    rules_lines = [
        f"# Rules proposal {rules_prop_path.stem}",
        "",
        f"- local_run_id: {local_run_id}",
        f"- rules_version: {rules_version}",
        f"- model: {model}",
        f"- primary_task: {primary_task_id}",
        f"- affected_tasks: {', '.join(affected_tasks)}",
        "",
        "## Focus",
        f"- problem: {md_escape(problem_text)}",
        f"- solution_type: {solution_type}",
        "",
        "## Primary task proposal",
    ]
    code_lines = [
        f"# Code proposal {code_prop_path.stem}",
        "",
        f"- local_run_id: {local_run_id}",
        f"- code_version: {code_version}",
        f"- model: {model}",
        f"- primary_task: {primary_task_id}",
        f"- affected_tasks: {', '.join(affected_tasks)}",
        "- policy: include blocking proposals only",
        "",
        "## Focus",
        f"- problem: {md_escape(problem_text)}",
        f"- solution_type: {solution_type}",
        "",
        "## Primary task proposal",
    ]

    primary_fail_group = str(primary_row.get("fail_group", ""))
    rules_item = {
        "task_id": primary_task_id,
        "fail_group": primary_fail_group,
        "proposal": primary_rules,
        "affected_tasks": affected_tasks,
        "problem": problem_text,
        "solution_type": solution_type,
        "status": "proposed",
    }
    rules_queue_row["tasks"].append(rules_item)

    rules_lines.append(
        f"- `{primary_task_id}` fail_group=`{md_escape(primary_fail_group)}`"
    )
    rules_lines.append(
        f"  - hypothesis: {md_escape(str(primary_rules.get('hypothesis', '')))}"
    )
    rules_lines.append(f"  - change: {md_escape(str(primary_rules.get('change', '')))}")
    rules_targets = primary_rules.get("target_files", [])
    if isinstance(rules_targets, list) and rules_targets:
        rules_lines.append("  - files:")
        for tf in rules_targets:
            if isinstance(tf, dict):
                rules_lines.append(
                    f"    - `{md_escape(str(tf.get('path', '')))}`: {md_escape(str(tf.get('change_summary', '')))}"
                )
    rules_lines.append(
        f"  - rollback: {md_escape(str(primary_rules.get('rollback', '')))}"
    )

    if code_is_blocking:
        code_item = {
            "task_id": primary_task_id,
            "fail_group": primary_fail_group,
            "proposal": primary_code,
            "code_assessment": primary_code_assessment,
            "affected_tasks": affected_tasks,
            "problem": problem_text,
            "solution_type": solution_type,
            "status": "proposed",
        }
        code_queue_row["tasks"].append(code_item)

        code_lines.append(
            f"- `{primary_task_id}` fail_group=`{md_escape(primary_fail_group)}`"
        )
        code_lines.append("  - assessment: blocking")
        code_lines.append(
            f"  - blocker_reason: {md_escape(str(primary_code.get('blocker_reason', '')))}"
        )
        code_lines.append(
            f"  - hypothesis: {md_escape(str(primary_code.get('hypothesis', '')))}"
        )
        code_lines.append(
            f"  - change: {md_escape(str(primary_code.get('change', '')))}"
        )
        code_targets = primary_code.get("target_files", [])
        if isinstance(code_targets, list) and code_targets:
            code_lines.append("  - files:")
            for tf in code_targets:
                if isinstance(tf, dict):
                    code_lines.append(
                        f"    - `{md_escape(str(tf.get('path', '')))}`: {md_escape(str(tf.get('change_summary', '')))}"
                    )
        code_lines.append(
            f"  - rollback: {md_escape(str(primary_code.get('rollback', '')))}"
        )

    if not code_queue_row["tasks"]:
        code_lines.append("- none (no blocking code proposals in selected scope)")

    write_text(rules_prop_path, "\n".join(rules_lines).strip() + "\n")
    write_text(code_prop_path, "\n".join(code_lines).strip() + "\n")
    append_jsonl(RULES_PROPOSALS_JSONL, rules_queue_row)
    append_jsonl(CODE_PROPOSALS_JSONL, code_queue_row)

    report_lines = [
        f"# Analyze report {report_path.stem}",
        "",
        f"- ts: {analysis_payload['ts']}",
        f"- local_run_id: {local_run_id}",
        f"- model: {model}",
        f"- parallelism: {parallelism}",
        f"- task_count: {len(task_results)}",
        f"- rules_version: {rules_version}",
        f"- code_version: {code_version}",
        f"- primary_task: {primary_task_id}",
        f"- affected_tasks: {', '.join(affected_tasks)}",
        "",
        "## Focus cycle",
        f"- problem: {md_escape(problem_text)}",
        f"- solution_type: {solution_type}",
        f"- solution_primary_task: {primary_task_id}",
        f"- solution_affected_tasks: {', '.join(affected_tasks)}",
        "",
        "## Task summary",
        "| task | score | passed | fail_group | status | code_assessment |",
        "|---|---:|:---:|---|---|---|",
    ]
    for row in task_results:
        code_assessment = (
            row.get("code_assessment", {})
            if isinstance(row.get("code_assessment"), dict)
            else {}
        )
        report_lines.append(
            f"| {md_escape(str(row.get('task_id', '')))} | {row.get('score', '')} | {bool(row.get('passed', False))} | {md_escape(str(row.get('fail_group', '')))} | {md_escape(str(row.get('status', '')))} | {md_escape(str(code_assessment.get('classification', 'optional')))} |"
        )

    report_lines.extend(
        [
            "",
            f"- analysis_json: `{analysis_path}`",
            f"- rules_proposal_md: `{rules_prop_path}`",
            f"- code_proposal_md: `{code_prop_path}`",
        ]
    )
    write_text(report_path, "\n".join(report_lines).strip() + "\n")

    update_index()
    print(f"ANALYZE_DONE report={report_path} analysis={analysis_path}")


def run_apply(args: argparse.Namespace) -> None:
    current_version = str(
        getattr(args, "from_version", "") or active_rules_version()
    ).strip()
    source_dir = RULES_VERSIONS_DIR / current_version
    source_agents = source_dir / "AGENTS.md"
    if not source_agents.exists():
        raise SystemExit(f"Source rules AGENTS not found: {source_agents}")

    proposal_path = _resolve_rules_proposal_path(args, current_version)
    proposal_text = proposal_path.read_text(encoding="utf-8")

    to_version = str(getattr(args, "to_version", "") or "").strip()
    if not to_version:
        to_version = _next_rules_version()
    target_dir = RULES_VERSIONS_DIR / to_version
    target_agents = target_dir / "AGENTS.md"

    dry_run = bool(getattr(args, "dry_run", False))
    model = str(
        getattr(args, "model", "") or os.getenv("CODEX_MODEL") or "gpt-5.3-codex"
    )
    mode_preamble = _mode_preamble("apply")

    before_text = source_agents.read_text(encoding="utf-8")
    before_extra_files = _rules_version_extra_files(source_dir)
    before_harness_docs: dict[str, str] = {}
    for rel in _existing_harness_doc_paths():
        p = ROOT / rel
        if p.exists() and p.is_file():
            before_harness_docs[rel] = p.read_text(encoding="utf-8")

    prompt = (
        "Execution mode: apply\n"
        f"{mode_preamble}\n\n"
        "Apply exactly one focused rules-package change (AGENTS.md + optional include/harness file).\n"
        "Do not include task ids or task-specific literals.\n"
        "Keep change small and reversible (<= 30 changed lines preferred).\n"
        f"Hard runtime limit: AGENTS.md must stay <= {RUNTIME_MAX_AGENTS_LINES} lines.\n"
        f"Soft budget: when AGENTS.md would exceed {RUNTIME_SOFT_AGENTS_LINES} lines, move details to includes/*.md or one harness doc.\n"
        "Return JSON only with fields:\n"
        "- agents_md: full updated AGENTS.md content\n"
        "- extra_files: optional list of {path, content} where path is under includes/*.md\n"
        "- harness_docs: optional list of {path, content} where path follows harness structure map under docs/** or ARCHITECTURE.md\n"
        "Keep AGENTS.md concise and move details into includes only when necessary.\n\n"
        f"Current rules version: {current_version}\n"
        f"Target rules version: {to_version}\n"
        f"Proposal path: {proposal_path}\n\n"
        f"Current include files json:\n{json.dumps(before_extra_files, ensure_ascii=True, indent=2)}\n\n"
        f"Current harness docs paths json:\n{json.dumps(sorted(before_harness_docs.keys()), ensure_ascii=True, indent=2)}\n\n"
        "Proposal content:\n"
        f"{proposal_text}\n\n"
        "Current AGENTS.md:\n"
        f"{before_text}\n"
    )

    out_path = ROOT / "tmp_apply_last_message.txt"
    cmd = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--output-last-message",
        str(out_path),
        "--model",
        model,
    ]
    if CODEX_PROFILE:
        cmd.extend(["--profile", CODEX_PROFILE])
    elif CODEX_BACKEND == "spark":
        cmd.extend(["-c", "model_provider=openai"])
    cmd.extend(
        [
            "--cd",
            str(ROOT),
            prompt,
        ]
    )
    proc = subprocess.run(cmd, text=True, capture_output=True)
    updated_text = ""
    if out_path.exists():
        updated_text = out_path.read_text(encoding="utf-8")
    if not updated_text.strip():
        updated_text = proc.stdout or ""
    payload = _coerce_apply_payload(updated_text)
    updated_agents = str(payload.get("agents_md", "")).strip()
    extra_files = _normalize_rules_extra_files(payload.get("extra_files", []))
    harness_docs = _normalize_harness_doc_files(payload.get("harness_docs", []))
    if not updated_agents:
        raise SystemExit("apply failed: empty model output")

    after_extra_files = dict(before_extra_files)
    if extra_files:
        for item in extra_files:
            after_extra_files[item["path"]] = item["content"]
    after_harness_docs = {item["path"]: item["content"] for item in harness_docs}
    before_selected_harness_docs = {
        rel: before_harness_docs.get(rel, "") for rel in after_harness_docs.keys()
    }
    runtime_stats = _validate_runtime_rules_package(
        agents_text=updated_agents, include_files=after_extra_files
    )
    changed_lines = _changed_lines_for_rules_package(
        before_agents=before_text,
        after_agents=updated_agents,
        before_extra=before_extra_files,
        after_extra=after_extra_files,
        before_harness_docs=before_selected_harness_docs,
        after_harness_docs=after_harness_docs,
    )
    changed_include_paths = sorted(
        key
        for key in (set(before_extra_files.keys()) | set(after_extra_files.keys()))
        if before_extra_files.get(key, "") != after_extra_files.get(key, "")
    )
    changed_harness_docs_paths = sorted(
        key
        for key in (
            set(before_selected_harness_docs.keys()) | set(after_harness_docs.keys())
        )
        if before_selected_harness_docs.get(key, "") != after_harness_docs.get(key, "")
    )

    includes_count = runtime_stats["includes_count"]
    includes_total_lines = runtime_stats["includes_total_lines"]
    agents_line_count = runtime_stats["agents_lines"]
    harness_docs_count = len(after_harness_docs)
    changed_limit = (
        220 if harness_docs_count > 0 else (100 if includes_count == 0 else 120)
    )
    if changed_lines > changed_limit:
        raise SystemExit(f"apply rejected: changed lines too large ({changed_lines})")
    if len(changed_include_paths) > 1:
        raise SystemExit(
            f"apply rejected: too many changed include files ({len(changed_include_paths)})"
        )
    if len(changed_harness_docs_paths) > 1:
        raise SystemExit(
            f"apply rejected: too many changed harness docs in one cycle ({len(changed_harness_docs_paths)})"
        )
    if (
        agents_line_count > RUNTIME_SOFT_AGENTS_LINES
        and not changed_include_paths
        and not changed_harness_docs_paths
    ):
        raise SystemExit(
            f"apply rejected: AGENTS.md is {agents_line_count} lines (> {RUNTIME_SOFT_AGENTS_LINES}) without offloading to include/harness docs"
        )

    ts = now_iso()
    apply_id = next_numbered_path(APPLIES_DIR, "a", ".md")
    problem, solution_type, primary_task = _extract_focus_from_rules_proposal(
        proposal_text
    )
    from_hash = _sha256_text(before_text)
    package_text = (
        updated_agents
        + "\n"
        + "\n".join(f"{k}\n{v}" for k, v in sorted(after_extra_files.items()))
        + "\n"
        + "\n".join(f"{k}\n{v}" for k, v in sorted(after_harness_docs.items()))
    )
    to_hash = _sha256_text(package_text)

    if dry_run:
        apply_md = [
            f"# Apply plan {apply_id.stem}",
            "",
            f"- ts: {ts}",
            "- dry_run: true",
            f"- model: {model}",
            f"- proposal: {proposal_path}",
            f"- from_version: {current_version}",
            f"- to_version: {to_version}",
            f"- primary_task: {primary_task}",
            f"- solution_type: {solution_type}",
            f"- problem: {problem}",
            f"- changed_lines_estimate: {changed_lines}",
            f"- from_hash: {from_hash}",
            f"- to_hash: {to_hash}",
            f"- agents_line_count: {agents_line_count}",
            f"- includes_count: {includes_count}",
            f"- includes_total_lines: {includes_total_lines}",
            f"- harness_docs_count: {len(after_harness_docs)}",
        ]
        write_text(apply_id, "\n".join(apply_md).strip() + "\n")
        update_index()
        print(f"APPLY_DRY_RUN done plan={apply_id} changed_lines={changed_lines}")
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    for child in target_dir.iterdir():
        if child.is_file() or child.is_symlink():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)

    target_agents.write_text(updated_agents + "\n", encoding="utf-8")
    for rel, content in after_extra_files.items():
        p = target_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    for rel, content in after_harness_docs.items():
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    RULES_ACTIVE_VERSION.write_text(to_version + "\n", encoding="utf-8")

    apply_row = {
        "ts": ts,
        "mode": "apply",
        "proposal_path": str(proposal_path),
        "from_version": current_version,
        "to_version": to_version,
        "primary_task": primary_task,
        "solution_type": solution_type,
        "problem": problem,
        "changed_lines": changed_lines,
        "from_hash": from_hash,
        "to_hash": to_hash,
        "status": "applied",
        "includes_count": len(after_extra_files),
        "includes_paths": sorted(after_extra_files.keys()),
        "agents_line_count": agents_line_count,
        "includes_total_lines": includes_total_lines,
        "changed_include_paths": changed_include_paths,
        "harness_docs_count": len(after_harness_docs),
        "harness_docs_paths": sorted(after_harness_docs.keys()),
        "changed_harness_docs_paths": changed_harness_docs_paths,
    }
    append_jsonl(APPLY_LOG_PATH, apply_row)
    append_jsonl(RULES_CHANGELOG, apply_row)

    apply_md = [
        f"# Apply report {apply_id.stem}",
        "",
        f"- ts: {ts}",
        "- dry_run: false",
        f"- model: {model}",
        f"- proposal: {proposal_path}",
        f"- from_version: {current_version}",
        f"- to_version: {to_version}",
        f"- active_version_now: {to_version}",
        f"- primary_task: {primary_task}",
        f"- solution_type: {solution_type}",
        f"- problem: {problem}",
        f"- changed_lines: {changed_lines}",
        f"- from_hash: {from_hash}",
        f"- to_hash: {to_hash}",
        f"- updated_file: `{target_agents}`",
        f"- agents_line_count: {agents_line_count}",
        f"- includes_count: {includes_count}",
        f"- includes_total_lines: {includes_total_lines}",
        f"- harness_docs_count: {len(after_harness_docs)}",
    ]
    if changed_include_paths:
        apply_md.append("- includes_files:")
        for rel in changed_include_paths:
            apply_md.append(f"  - `{target_dir / rel}`")
    if changed_harness_docs_paths:
        apply_md.append("- harness_docs_files:")
        for rel in changed_harness_docs_paths:
            apply_md.append(f"  - `{ROOT / rel}`")
    write_text(apply_id, "\n".join(apply_md).strip() + "\n")

    update_index()
    print(f"APPLY_DONE from={current_version} to={to_version} report={apply_id}")


def run_deploy(args: argparse.Namespace) -> None:
    version = str(getattr(args, "rules_version", "") or active_rules_version()).strip()
    source_dir = RULES_VERSIONS_DIR / version
    source = source_dir / "AGENTS.md"
    if not source.exists():
        raise SystemExit(f"deploy source AGENTS not found: {source}")

    target_raw = str(getattr(args, "target", "") or str(NATIVE_RULES_TARGET)).strip()
    target = Path(target_raw).resolve()
    if target != NATIVE_RULES_TARGET:
        raise SystemExit(
            f"deploy target forbidden: {target} (allowed: {NATIVE_RULES_TARGET})"
        )
    target_dir = NATIVE_RULES_DIR

    dry_run = bool(getattr(args, "dry_run", False))
    force_yes = bool(getattr(args, "yes", False))

    source_text = source.read_text(encoding="utf-8")
    source_extra_files = _rules_version_extra_files(source_dir)
    runtime_stats = _validate_runtime_rules_package(
        agents_text=source_text,
        include_files=source_extra_files,
    )
    source_agents_lines = runtime_stats["agents_lines"]
    source_includes_count = runtime_stats["includes_count"]
    source_includes_total_lines = runtime_stats["includes_total_lines"]
    source_hash = _sha256_text(source_text)
    source_tree_hash = _sha256_text(
        "\n".join(
            [
                f"{p.relative_to(source_dir).as_posix()}::{_sha256_file(p)}"
                for p in sorted(source_dir.rglob("*"))
                if p.is_file()
            ]
        )
    )
    target_hash_before = _sha256_file(target)

    deploy_id = next_numbered_path(DEPLOY_DIR, "d", ".md")
    ts = now_iso()

    if dry_run or not force_yes:
        md = [
            f"# Deploy plan {deploy_id.stem}",
            "",
            f"- ts: {ts}",
            f"- dry_run: {str(dry_run or not force_yes).lower()}",
            f"- rules_version: {version}",
            f"- source: `{source}`",
            f"- target: `{target}`",
            f"- source_dir: `{source_dir}`",
            f"- target_dir: `{target_dir}`",
            f"- source_hash: {source_hash}",
            f"- source_tree_hash: {source_tree_hash}",
            f"- source_agents_lines: {source_agents_lines}",
            f"- source_includes_count: {source_includes_count}",
            f"- source_includes_total_lines: {source_includes_total_lines}",
            f"- target_hash_before: {target_hash_before}",
            "- note: use --yes (and without --dry-run) to apply deploy",
        ]
        write_text(deploy_id, "\n".join(md).strip() + "\n")
        update_index()
        print(f"DEPLOY_DRY_RUN plan={deploy_id}")
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    backup_name = f"local-rules.backup_{now_stamp()}"
    backup_path = DEPLOY_BACKUPS_DIR / backup_name
    DEPLOY_BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    if target_dir.exists() and any(target_dir.iterdir()):
        shutil.copytree(target_dir, backup_path, dirs_exist_ok=True)

    _copy_rules_version_tree(source_dir=source_dir, target_dir=target_dir)
    target_hash_after = _sha256_file(target)

    row = {
        "ts": ts,
        "mode": "deploy",
        "rules_version": version,
        "source": str(source),
        "source_dir": str(source_dir),
        "target": str(target),
        "target_dir": str(target_dir),
        "backup": str(backup_path) if backup_path.exists() else "",
        "source_hash": source_hash,
        "source_tree_hash": source_tree_hash,
        "source_agents_lines": source_agents_lines,
        "source_includes_count": source_includes_count,
        "source_includes_total_lines": source_includes_total_lines,
        "target_hash_before": target_hash_before,
        "target_hash_after": target_hash_after,
        "status": "deployed",
    }
    append_jsonl(DEPLOY_LOG_PATH, row)

    md = [
        f"# Deploy report {deploy_id.stem}",
        "",
        f"- ts: {ts}",
        "- dry_run: false",
        f"- rules_version: {version}",
        f"- source: `{source}`",
        f"- target: `{target}`",
        f"- source_dir: `{source_dir}`",
        f"- target_dir: `{target_dir}`",
        f"- backup: `{backup_path}`",
        f"- source_hash: {source_hash}",
        f"- source_tree_hash: {source_tree_hash}",
        f"- source_agents_lines: {source_agents_lines}",
        f"- source_includes_count: {source_includes_count}",
        f"- source_includes_total_lines: {source_includes_total_lines}",
        f"- target_hash_before: {target_hash_before}",
        f"- target_hash_after: {target_hash_after}",
        "- deploy_mode: full_replace_local_rules_dir",
    ]
    write_text(deploy_id, "\n".join(md).strip() + "\n")

    update_index()
    print(f"DEPLOY_DONE version={version} target={target} report={deploy_id}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="codex-agent-analytics")
    sp = p.add_subparsers(dest="mode", required=True)

    a = sp.add_parser("analyze", help="Run Codex analysis on native run artifacts")
    a.add_argument(
        "tasks", nargs="*", help="Optional task ids (space or comma separated)"
    )
    a.add_argument(
        "--run-id", default="", help="Explicit local_run_id from codex-agent-native"
    )
    a.add_argument(
        "-p", "--parallelism", type=int, default=2, help="Parallel analysis sessions"
    )
    a.add_argument(
        "--env", choices=["sandbox", "pac1"], default="sandbox", help="Metadata only"
    )
    a.add_argument("--model", default="", help="Codex model override")
    a.add_argument(
        "--focus-task", default="", help="Primary task id for one-focus solution"
    )
    a.set_defaults(func=run_analyze)

    ap = sp.add_parser(
        "apply", help="Apply one rules proposal into a new rules version"
    )
    ap.add_argument(
        "--proposal-id", default="", help="Rules proposal id (e.g. 001 or prop-001)"
    )
    ap.add_argument(
        "--proposal-path",
        default="",
        help="Absolute or project-relative path to rules proposal md",
    )
    ap.add_argument(
        "--from-version", default="", help="Source rules version (defaults to active)"
    )
    ap.add_argument(
        "--to-version",
        default="",
        help="Target rules version (defaults to next rvXXXX)",
    )
    ap.add_argument("--model", default="", help="Codex model override")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan apply without writing new rules version",
    )
    ap.set_defaults(func=run_apply)

    d = sp.add_parser(
        "deploy",
        help="Deploy selected rules version into native local-rules/ (full replace)",
    )
    d.add_argument(
        "--rules-version",
        default="",
        help="Rules version to deploy (defaults to active)",
    )
    d.add_argument(
        "--target",
        default=str(NATIVE_RULES_TARGET),
        help="Deploy target path (locked to native local-rules)",
    )
    d.add_argument(
        "--dry-run", action="store_true", help="Plan deploy without copying files"
    )
    d.add_argument("--yes", action="store_true", help="Confirm deploy write action")
    d.set_defaults(func=run_deploy)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
