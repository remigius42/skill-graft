"""The `skill-graft` command line."""

import argparse
import re
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any, NoReturn

from skill_graft import apm, config, init, lock, paths, resolve, update, vendor
from skill_graft.cache import Cache
from skill_graft.errors import SkillGraftError, warn
from skill_graft.hull import Hull


class _Formatter(argparse.HelpFormatter):
    """Wraps help text without breaking at hyphens: `skill-graft.toml` stays whole."""

    def _split_lines(self, text: str, width: int) -> list[str]:
        return textwrap.wrap(_flat(text), width, break_on_hyphens=False)

    def _fill_text(self, text: str, width: int, indent: str) -> str:
        return textwrap.fill(
            _flat(text),
            width,
            initial_indent=indent,
            subsequent_indent=indent,
            break_on_hyphens=False,
        )


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class _Command(argparse.ArgumentParser):
    """A command's parser, wrapping help as the top level does."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("formatter_class", _Formatter)
        super().__init__(*args, **kwargs)


class _Parser(_Command):
    """The top-level parser: a usage error also lists the commands."""

    commands: str = ""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n\ncommands:\n{self.commands}")


def _parser() -> tuple[_Parser, dict[str, argparse.ArgumentParser]]:
    """The parser and each command's own, by name."""
    parser = _Parser(
        prog="skill-graft",
        description=(
            "Build your agent skills from other people's repositories: the entries "
            "you ask for, every skill they reach, renamed and patched as "
            "~/.apm/skill-graft/skill-graft.toml declares, deployed through APM."
        ),
    )
    commands = parser.add_subparsers(
        dest="command", metavar="command", parser_class=_Command
    )
    commands.add_parser(
        "init",
        help="create and register ~/.apm/skill-graft/",
        description=(
            "Create ~/.apm/skill-graft/ with a commented skill-graft.toml and an "
            "apm.yml, and register it with `apm install -g`. Refuses if the folder "
            "exists."
        ),
    )
    commands.add_parser(
        "resolve",
        help="compute the hull, write the lock, and show the tree",
        description=(
            "Compute the hull (the entries and every skill their slash and Skill "
            "tool references reach), write skill-graft.lock, and print the tree, "
            "then the skills prose mentions outside the hull. Reads each git "
            "source at its ref, fetching only a commit not yet cached."
        ),
    )
    build = commands.add_parser(
        "build",
        help="vendor the hull and deploy it through APM",
        description=(
            "Resolve, vendor the hull's skills under their deployed names into "
            "~/.apm/skill-graft/.apm/skills/, patched and renamed, write the lock, "
            "and deploy through `apm install -g`."
        ),
    )
    build.add_argument(
        "--no-install", action="store_true", help="stop before running APM"
    )
    update_parser = commands.add_parser(
        "update",
        help="move git sources' refs to their branch tips",
        description=(
            "Fetch each git source's branch tip, resolve the hull there, and only "
            "if that succeeds write the new ref into skill-graft.toml and the lock. "
            "Prints the hull diff and any patch hunk that no longer applies."
        ),
    )
    update_parser.add_argument(
        "aliases",
        nargs="*",
        metavar="source",
        help="a source alias; default: every git source",
    )
    update_parser.add_argument(
        "--dry-run", action="store_true", help="show the new shas, write nothing"
    )
    help_parser = commands.add_parser(
        "help",
        help="show the help of skill-graft or of a command",
        description="Show the same text as `skill-graft [command] --help`.",
    )
    # Not `command`: the subcommand's namespace would overwrite the top level's.
    help_parser.add_argument("topic", nargs="?", metavar="command")
    parser.commands = "".join(
        f"  {action.dest:<10}{action.help}\n" for action in commands._choices_actions
    )
    return parser, dict(commands.choices)


def main(argv: list[str] | None = None) -> int:
    parser, commands = _parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.error("a command is required")
    if args.command == "help":
        if args.topic is None:
            parser.print_help()
        elif args.topic in commands:
            commands[args.topic].print_help()
        else:
            parser.error(f"no command {args.topic!r}")
        return 0
    try:
        if args.command == "init":
            init.init()
        elif args.command == "update":
            update.update(_load(), args.aliases, args.dry_run)
        elif args.command == "resolve":
            with tempfile.TemporaryDirectory(prefix="skill-graft-") as work:
                loaded, resolved = _resolve(Path(work))
                lock.write(lock.render(loaded, {}, resolved))
            print(lock.tree(resolved) + lock.suggestions(resolved), end="")
            warn(resolved.warnings)
        elif args.command == "build":
            with tempfile.TemporaryDirectory(prefix="skill-graft-") as work:
                loaded, resolved = _resolve(Path(work))
                warn(resolved.warnings)
                vendor.vendor(resolved)
            # Hashes the vendored copies, so the lock holds exactly what was vendored.
            copies = {
                s: lock.folder_hash(paths.skills() / resolved.deployed[s])
                for s in resolved.skills
            }
            lock.write(lock.render(loaded, {}, resolved, copies))
            if not args.no_install:
                apm.install()
    except (SkillGraftError, OSError) as error:
        print(f"skill-graft: {error}", file=sys.stderr)
        return 1
    return 0


def _load() -> config.Config:
    """The config, its warnings printed."""
    loaded = config.load()
    warn(loaded.warnings)
    return loaded


def _resolve(work: Path) -> tuple[config.Config, Hull]:
    """The config and its hull, every source at its ref, patched copies in `work`."""
    loaded = _load()
    folders = resolve.folders(loaded, Cache(paths.cache()), {})
    return loaded, resolve.resolve(loaded, folders, work)


if __name__ == "__main__":
    sys.exit(main())
