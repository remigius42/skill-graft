"""The `skill-graft` command line."""

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="skill-graft",
        description="Build your agent skills from other repositories.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="create and register ~/.apm/skill-graft/")
    build = commands.add_parser(
        "build", help="vendor the entries and deploy them through APM"
    )
    build.add_argument(
        "--no-install", action="store_true", help="stop before running APM"
    )
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
