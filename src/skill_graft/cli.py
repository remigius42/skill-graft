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
    update_parser.add_argument(
        "--dry-run", action="store_true", help="show the new shas, write nothing"
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            init.init()
        elif args.command == "update":
            update.update(_load(), args.aliases, args.dry_run)
        elif args.command == "build":
            loaded = _load()
            folders = resolve.folders(loaded, Cache(paths.cache()), {})
            resolved = resolve.resolve(loaded, folders)
            _warn(resolved.warnings)
            vendor.vendor(resolved.skills)
            if not args.no_install:
                apm.install()
    except (SkillGraftError, OSError) as error:
        print(f"skill-graft: {error}", file=sys.stderr)
        return 1
    return 0


def _load() -> config.Config:
    """The config, its warnings printed."""
    loaded = config.load()
    _warn(loaded.warnings)
    return loaded


def _warn(warnings: list[str]) -> None:
    for warning in warnings:
        print(f"skill-graft: warning: {warning}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
