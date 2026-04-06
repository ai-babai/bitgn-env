import subprocess
import os
from pathlib import Path


def run(args) -> None:
    root = Path(__file__).resolve().parents[2]
    cmd = [str(root / "run-codex-sandbox.sh")]
    env = getattr(args, "env", "sandbox")
    env_map = os.environ.copy()
    if env == "pac1":
        env_map["BENCHMARK_ID"] = "bitgn/pac1-dev"
        env_map["AGENT_ENV"] = "pac1"
    else:
        env_map["BENCHMARK_ID"] = "bitgn/sandbox"
        env_map["AGENT_ENV"] = "sandbox"
    if args.sync:
        cmd.append("--sync")
    if args.all:
        cmd.append("--all")
    if args.tasks:
        cmd.extend(args.tasks)
    parallelism = int(getattr(args, "parallelism", 1) or 1)
    env_map["TASK_PARALLELISM"] = str(max(1, parallelism))
    print(
        f"RUN SOLVE env={env} benchmark={env_map['BENCHMARK_ID']} tasks={'all' if args.all else args.tasks} parallelism={env_map['TASK_PARALLELISM']}"
    )
    subprocess.run(cmd, check=True, env=env_map)
