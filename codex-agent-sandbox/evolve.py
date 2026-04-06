import argparse

from evolve_modes import (
    run_analyze,
    run_apply_prompts,
    run_autopilot,
    run_full_step,
    run_propose_code,
    run_propose_prompts,
    run_solve,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Codex-agent evolution pipeline")
    sp = p.add_subparsers(dest="mode", required=True)

    s = sp.add_parser("solve", help="Run benchmark solve mode")
    s.add_argument("--env", choices=["sandbox", "pac1"], default="sandbox", help="Environment adapter")
    s.add_argument("tasks", nargs="*", help="Optional task ids")
    s.add_argument("--all", action="store_true", help="Run full benchmark")
    s.add_argument("--sync", action="store_true", help="Sync dependencies before run")
    s.add_argument("--parallelism", "--parallels", type=int, default=1, help="Task parallelism inside solve run")
    s.set_defaults(func=run_solve)

    a = sp.add_parser("analyze", help="Analyze latest run failures")
    a.add_argument("--env", choices=["sandbox", "pac1"], default="sandbox", help="Environment adapter")
    a.set_defaults(func=run_analyze)

    pp = sp.add_parser("propose-prompts", help="Propose prompt-only changes")
    pp.add_argument("--env", choices=["sandbox", "pac1"], default="sandbox", help="Environment adapter")
    pp.set_defaults(func=run_propose_prompts)

    pc = sp.add_parser("propose-code", help="Propose code changes (no apply)")
    pc.add_argument("--env", choices=["sandbox", "pac1"], default="sandbox", help="Environment adapter")
    pc.set_defaults(func=run_propose_code)

    ap = sp.add_parser("apply-prompts", help="Apply prompt changes and version switch")
    ap.add_argument("--env", choices=["sandbox", "pac1"], default="sandbox", help="Environment adapter")
    ap.add_argument("--hypothesis", default="", help="Hypothesis for changelog")
    ap.set_defaults(func=run_apply_prompts)

    fs = sp.add_parser("full-step", help="Run one full prompt-only evolution step")
    fs.add_argument("--env", choices=["sandbox", "pac1"], default="sandbox", help="Environment adapter")
    fs.add_argument("--hypothesis", default="", help="Hypothesis for apply-prompts in this step")
    fs.add_argument("--task-scope", choices=["all", "affected"], default="all", help="Task selection scope for solve stage")
    fs.add_argument("--affected-from", choices=["last-apply", "last-failed"], default="last-apply", help="Source for affected task selection")
    fs.add_argument("--max-affected", type=int, default=0, help="Optional max number of affected tasks to run (0 = unlimited)")
    fs.add_argument("--parallelism", "--parallels", type=int, default=1, help="Task parallelism inside solve stage")
    fs.add_argument("--allow-blocked-prompt", action="store_true", help="Allow prompt evolution even when code blockers are detected")
    fs.add_argument("tasks", nargs="*", help="Optional task ids for solve stage")
    fs.set_defaults(func=run_full_step)

    au = sp.add_parser("autopilot", help="Run N prompt-only evolution steps")
    au.add_argument("--env", choices=["sandbox", "pac1"], default="sandbox", help="Environment adapter")
    au.add_argument("--n", type=int, default=3, help="Number of evolution steps")
    au.add_argument(
        "--no-improve-limit",
        type=int,
        default=2,
        help="Stop after this many non-improving consecutive steps",
    )
    au.add_argument("--hypothesis", default="", help="Hypothesis text for apply-prompts")
    au.add_argument("--task-scope", choices=["all", "affected"], default="all", help="Task selection scope for each evolution step")
    au.add_argument("--affected-from", choices=["last-apply", "last-failed"], default="last-apply", help="Source for affected task selection")
    au.add_argument("--max-affected", type=int, default=0, help="Optional max number of affected tasks per step (0 = unlimited)")
    au.add_argument("--parallelism", "--parallels", type=int, default=1, help="Task parallelism for solve stage in each step")
    au.add_argument("tasks", nargs="*", help="Optional fixed task ids for each evolution step")
    au.set_defaults(func=run_autopilot)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
