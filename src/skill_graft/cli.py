"""The `skill-graft` command line."""

import argparse
import sys

from skill_graft import apm, config, init, lock, paths, resolve, update, vendor
from skill_graft.cache import Cache
from skill_graft.errors import SkillGraftError
from skill_graft.hull import Hull


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="skill-graft",
        description="Build your agent skills from other repositories.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="create and register ~/.apm/skill-graft/")
    commands.add_parser(
        "resolve", help="compute the hull, write the lock, and show the tree"
    )
    build = commands.add_parser(
        "build", help="vendor the hull and deploy it through APM"
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
        elif args.command == "resolve":
            loaded, resolved = _resolve()
            lock.write(lock.render(loaded, {}, resolved))
            print(lock.tree(resolved), end="")
            _warn(resolved.warnings)
        elif args.command == "build":
            loaded, resolved = _resolve()
            _warn(resolved.warnings)
            vendor.vendor(resolved.skills)
            lock.write(lock.render(loaded, {}, resolved))  # what was vendored
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


def _resolve() -> tuple[config.Config, Hull]:
    """The config and its hull, every source at its ref."""
    loaded = _load()
    folders = resolve.folders(loaded, Cache(paths.cache()), {})
    return loaded, resolve.resolve(loaded, folders)


def _warn(warnings: list[str]) -> None:
    for warning in warnings:
        print(f"skill-graft: warning: {warning}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
