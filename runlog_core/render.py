import json
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def _fmt_moscow(ts: object) -> str:
    raw = str(ts or "").strip()
    if not raw:
        return "-"
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return "-"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MOSCOW_TZ).isoformat(timespec="seconds")


def _fmt_tokens(p: int | None, c: int | None, t: int | None) -> str:
    if t is None and p is None and c is None:
        return "-"
    pp = p or 0
    cc = c or 0
    tt = t if t is not None else pp + cc
    return f"{tt} (P:{pp}, C:{cc})"


def _pad(s: str, w: int) -> str:
    if len(s) >= w:
        return s[:w]
    return s + " " * (w - len(s))


def render_task_table(task_rows: list[dict]) -> str:
    rows = sorted(task_rows, key=lambda r: (str(r.get("benchmark_id", "")), str(r.get("task_id", ""))))
    headers = ["Task", "Pass", "Time", "Tokens", "Steps", "Fail Group", "Fail Note"]
    data: list[list[str]] = []
    for r in rows:
        data.append(
            [
                str(r.get("task_id", "")),
                "yes" if r.get("passed") else "no",
                f"{float(r.get('duration_sec', 0.0)):.1f}s",
                _fmt_tokens(r.get("tokens_prompt"), r.get("tokens_completion"), r.get("tokens_total")),
                str(int(r.get("steps", 0) or 0)),
                str(r.get("fail_group", "") or "-"),
                str(r.get("fail_note", "") or "-"),
            ]
        )

    max_width = [12, 4, 7, 32, 5, 18, 70]
    widths = [len(h) for h in headers]
    for row in data:
        for i, cell in enumerate(row):
            widths[i] = min(max_width[i], max(widths[i], len(cell)))

    line = " | ".join(_pad(h, widths[i]) for i, h in enumerate(headers))
    sep = "-+-".join("-" * w for w in widths)
    out = [line, sep]
    for row in data:
        out.append(" | ".join(_pad(row[i], widths[i]) for i in range(len(headers))))

    total = len(rows)
    passed = sum(1 for r in rows if r.get("passed"))
    failed = total - passed
    total_time = sum(float(r.get("duration_sec", 0.0) or 0.0) for r in rows)
    total_steps = sum(int(r.get("steps", 0) or 0) for r in rows)
    tp = sum(int(r.get("tokens_prompt", 0) or 0) for r in rows)
    tc = sum(int(r.get("tokens_completion", 0) or 0) for r in rows)
    tt = sum(int(r.get("tokens_total", 0) or 0) for r in rows)

    out.append("")
    out.append(f"Total tasks: {total}, passed: {passed}, failed: {failed}")
    out.append(f"Total time: {total_time:.1f}s, total tokens: {tt} (P:{tp}, C:{tc}), total steps: {total_steps}")
    return "\n".join(out)


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def latest_run_table(registry_home: Path) -> str:
    runs_path = registry_home / "index" / "runs.jsonl"
    tasks_path = registry_home / "index" / "task_runs.jsonl"
    runs = _load_jsonl(runs_path)
    if not runs:
        return "No runs found"
    latest = runs[-1]
    run_id = latest.get("run_id")
    tasks = [t for t in _load_jsonl(tasks_path) if t.get("run_id") == run_id]
    header = (
        f"Run: {run_id} | runner: {latest.get('runner_id')} | benchmark: {latest.get('benchmark_id')} | "
        f"mode: {latest.get('run_mode')} | start(UTC): {latest.get('ts_start', '-')} | "
        f"start(MSK): {_fmt_moscow(latest.get('ts_start'))}"
    )
    return header + "\n\n" + render_task_table(tasks)
