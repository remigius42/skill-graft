"""The `skill-graft` command line."""

import argparse
import os
import re
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any, NoReturn

from skill_graft import (
    apm,
    config,
    edit,
    explain,
    init,
    lock,
    paths,
    resolve,
    update,
    vendor,
)
from skill_graft.cache import Cache
from skill_graft.errors import SkillGraftError, notice, warn
from skill_graft.hull import Hull


# Commands that write: they name the package they act on before anything else.
WRITERS = ("resolve", "build", "update", "add", "remove", "rename")


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
            "you ask for, every skill they reach, renamed and patched as the "
            "package's skill-graft.toml declares, deployed through APM. The package "
            "is the nearest .apm/skill-graft/ above the working folder, else "
            "~/.apm/skill-graft/."
        ),
    )
    commands = parser.add_subparsers(
        dest="command", metavar="command", parser_class=_Command
    )
    init_parser = commands.add_parser(
        "init",
        help="create and register ~/.apm/skill-graft/",
        description=(
            "Create ~/.apm/skill-graft/ with a commented skill-graft.toml and an "
            "apm.yml, and register it with `apm install -g`. Refuses if the folder "
            "exists."
        ),
    )
    init_parser.add_argument(
        "--project",
        action="store_true",
        help=(
            "create ./.apm/skill-graft/ instead, a package for this project, and "
            "register it with `apm install ./.apm/skill-graft` here"
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
            "the package's .apm/skills/, patched and renamed, write the lock, and "
            "deploy through `apm install`: with -g for ~/.apm/skill-graft/, in the "
            "project root for a project's package."
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
    tree = commands.add_parser(
        "tree",
        help="show the hull as a tree, writing nothing",
        description=(
            "Compute the hull as resolve does and print its tree, without the prose "
            "suggestions and without writing the lock; or print it as a Mermaid "
            "flowchart, to paste into Markdown."
        ),
    )
    tree.add_argument(
        "--format",
        choices=["text", "mermaid"],
        default="text",
        help="text (default): resolve's tree; mermaid: a Mermaid flowchart",
    )
    tree.add_argument(
        "--link",
        action="store_true",
        help=(
            "with --format mermaid: print a mermaid.live URL that holds the diagram "
            "in its fragment instead; nothing is uploaded"
        ),
    )
    why = commands.add_parser(
        "why",
        help="show why a skill is in the hull, writing nothing",
        description=(
            "Compute the hull as resolve does and print the paths that reach a "
            "skill, as an inverted tree: the skill first, then each skill whose "
            "slash or Skill tool reference reaches it, up to the entries."
        ),
    )
    why.add_argument(
        "skill",
        help="a skill ID (<source alias>/<name>), or the name a hull skill deploys as",
    )
    add = commands.add_parser(
        "add",
        help="add skills to the entries, then resolve",
        description=(
            "Append each skill ID to `entries` in skill-graft.toml, keeping its "
            "comments and formatting. The edited config is resolved first; only if "
            "it resolves are skill-graft.toml and the lock written and the tree "
            "printed. Never builds."
        ),
    )
    add.add_argument(
        "skills", nargs="+", metavar="skill-id", help="<source alias>/<name>"
    )
    remove = commands.add_parser(
        "remove",
        help="remove skills from the entries, then resolve",
        description=(
            "Delete each skill ID from `entries` in skill-graft.toml, keeping its "
            "other comments and formatting, as add does. A removed skill another "
            "entry reaches stays in the hull. Never builds."
        ),
    )
    remove.add_argument(
        "skills", nargs="+", metavar="skill-id", help="an entry to remove"
    )
    rename = commands.add_parser(
        "rename",
        help="give a skill a new deployed name, then resolve",
        description=(
            "Set the skill's value in [rename] of skill-graft.toml, keeping its "
            "comments and formatting, as add does. The new deployed name is carried "
            "into every reference to the skill. Renaming a skill to its own name "
            "undoes its rename. Never builds."
        ),
    )
    rename.add_argument("skill", metavar="skill-id", help="<source alias>/<name>")
    rename.add_argument("name", help="the name it deploys as")
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
    if args.command == "tree" and args.link and args.format != "mermaid":
        commands["tree"].error("--link needs --format mermaid")
    try:
        if args.command != "init":
            paths.use(paths.discover(_working_folder()))
        elif args.project:
            paths.use(_working_folder())
        if args.command in WRITERS:  # init names it once its own checks pass
            notice(f"package: {paths.package().absolute()}")
        if args.command == "init":
            init.init(args.project)
        elif args.command == "update":
            update.update(_load(), args.aliases, args.dry_run)
        elif args.command == "add":
            edit.add(args.skills)
        elif args.command == "remove":
            edit.remove(args.skills)
        elif args.command == "rename":
            edit.rename(args.skill, args.name)
        elif args.command == "why":
            with tempfile.TemporaryDirectory(prefix="skill-graft-") as work:
                loaded, resolved = _resolve(Path(work))
            try:
                target = explain.find(
                    resolved,
                    args.skill,
                    lambda text: resolve.known(loaded, "why", text),
                )
                print(explain.why(resolved, target), end="")
            finally:  # after the output, as `tree` and `resolve` print them
                warn(resolved.warnings)
        elif args.command == "tree":
            with tempfile.TemporaryDirectory(prefix="skill-graft-") as work:
                _, resolved = _resolve(Path(work))
            if args.link:
                print(explain.link(explain.mermaid(resolved)))
            elif args.format == "mermaid":
                print(explain.mermaid(resolved), end="")
            else:
                print(lock.tree(resolved), end="")
            warn(resolved.warnings)
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
            lock.announce_suggestions(resolved)  # once nothing before APM can fail
            if not args.no_install:
                apm.install()
    except (SkillGraftError, OSError) as error:
        print(f"skill-graft: {error}", file=sys.stderr)
        return 1
    finally:
        paths.use(None)
    return 0


def _working_folder() -> Path:
    try:
        return Path.cwd()
    except FileNotFoundError:
        # The shell's PWD still names the deleted folder.
        folder = f" {os.environ['PWD']}" if os.environ.get("PWD") else ""
        raise SkillGraftError(f"the working folder{folder} no longer exists") from None


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
