import argparse
from pathlib import Path

from .render import latest_run_table


def main() -> None:
    parser = argparse.ArgumentParser(description="Runlog registry utilities")
    parser.add_argument("command", choices=["latest"], help="Command to execute")
    parser.add_argument(
        "--home",
        default="/Users/skif/develop/runlog-registry",
        help="Registry home path",
    )
    args = parser.parse_args()

    home = Path(args.home)
    if args.command == "latest":
        print(latest_run_table(home))


if __name__ == "__main__":
    main()
