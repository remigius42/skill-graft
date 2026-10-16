"""The `skill-graft` command line."""

import argparse
import sys

from skill_graft import apm, config, init, paths, resolve, update, vendor
from skill_graft.cache import Cache
from skill_graft.errors import SkillGraftError


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
    update_parser = commands.add_parser(
        "update", help="move git sources' refs to their branch tips"
    )
    update_parser.add_argument(
        "aliases", nargs="*", metavar="source", help="default: every git source"
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            init.init()
        elif args.command == "update":
            for line in update.update(args.aliases):
                print(line)
        elif args.command == "build":
            loaded = config.load()
            for warning in loaded.warnings:
                print(f"skill-graft: warning: {warning}", file=sys.stderr)
            folders = resolve.folders(loaded, Cache(paths.cache()), {})
            vendor.vendor(resolve.resolve(loaded, folders))
            if not args.no_install:
                apm.install()
    except (SkillGraftError, OSError) as error:
        print(f"skill-graft: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
