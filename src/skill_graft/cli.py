"""The `skill-graft` command line."""

import argparse
import json
import re
import sys
import textwrap
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn, TypeGuard

from skill_graft.infra.errors import (
    SkillGraftError,
    flush_stdout,
    print_error,
    warnings_last,
)

if TYPE_CHECKING:
    from _typeshed import SupportsWrite

WINDOWS = "native Windows is unsupported: run skill-graft in WSL"
# What a dry run writes, in `--dry-run`'s help.
_ONLY_DIFF_FILE = "nothing but the --diff-file FILE"
# The installed distribution, found whatever the case (importlib normalizes it).
_DISTRIBUTION = "skill-graft"
# Its metadata field, found whatever the case (`email.message.Message`).
_VERSION = "Version"
# Help texts as argparse wraps them: each whitespace run one space.
_WHITESPACE = re.compile(r"\s+")


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
    return _WHITESPACE.sub(" ", text).strip()


class _Command(argparse.ArgumentParser):
    """A command's parser, wrapping help as the top level does, and taking each option
    only by its full name."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(formatter_class=_Formatter, allow_abbrev=False, **kwargs)

    def print_help(self, file: "SupportsWrite[str] | None" = None) -> None:
        """Writes the help itself: argparse ignores a failed write, which, with stdout
        unbuffered, leaves no buffered help for `main`'s flush to fail on. Started
        with stdout closed, writes to stderr, as argparse does."""
        if file is None:
            file = sys.stdout
        (file or sys.stderr).write(self.format_help())


class _Version(argparse.Action):
    """Prints the installed version and exits, read only when asked for."""

    def __init__(self, option_strings: list[str], dest: str, **kwargs: Any) -> None:
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser: argparse.ArgumentParser, *_: Any) -> NoReturn:
        try:
            distribution = metadata.distribution(_DISTRIBUTION)
        except metadata.PackageNotFoundError:
            version, origin = "unknown", ""
        else:
            version, origin = _version(distribution), _origin(distribution)
        print(f"skill-graft {version}{origin}")
        parser.exit()


def _version(distribution: metadata.Distribution) -> str:
    """The version its metadata names, or `unknown` when it cannot be read or is not
    printable ASCII without spaces."""
    try:
        fields = distribution.metadata
    except (OSError, ValueError):  # unreadable or undecodable
        return "unknown"
    # Check first: CPython deprecates indexing a missing field and will make it raise
    # KeyError (`PackageMetadata` declares no `.get`).
    version = fields[_VERSION].strip() if _VERSION in fields else None
    return version if _printable(version) else "unknown"


def _printable(text: object) -> TypeGuard[str]:
    """Whether `text` is a non-empty string of printable ASCII without spaces: one
    word, safe on one line of any terminal."""
    return isinstance(text, str) and re.fullmatch(r"[!-~]+", text) is not None


def _origin(distribution: metadata.Distribution) -> str:
    """` (<revision> @ <commit>)` for a git install, from the installer's
    direct_url.json (PEP 610); anything else, malformed or unreadable included, adds
    nothing."""
    try:
        text = distribution.read_text("direct_url.json")
        if text is None:  # no such file, or unreadable
            return ""
        direct_url = json.loads(text)
    except (OSError, ValueError, RecursionError):  # unreadable, not JSON, too deep
        return ""
    vcs_info = direct_url.get("vcs_info") if isinstance(direct_url, dict) else None
    if not isinstance(vcs_info, dict) or vcs_info.get("vcs") != "git":
        return ""
    commit = vcs_info.get("commit_id")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-fA-F]{7,}", commit):
        return ""
    revision = vcs_info.get("requested_revision")
    if _printable(revision) and not _abbreviates(revision, commit):
        return f" ({revision} @ {commit[:7]})"
    return f" ({commit[:7]})"


def _abbreviates(revision: str, commit: str) -> bool:
    """Whether `revision` is `commit`, in full or as git's shortest default abbreviation
    or longer: a shorter hex name is a branch or tag."""
    return len(revision) >= 7 and commit.lower().startswith(revision.lower())


class _Parser(_Command):
    """The top-level parser: a usage error also lists the commands."""

    commands: str = ""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n\ncommands:\n{self.commands}")


# The help texts, by command and argument: at module level, as mutmut mutates
# only functions, so their wording is never mutated (CONTRIBUTING.md).
_TEXT = {
    "skill-graft: description": (
        "Build your agent skills from other people's repositories: the entries "
        "you ask for, every skill they reach, renamed and patched as the "
        "package's skill-graft.toml declares, deployed through APM. The package "
        "is the nearest .apm/skill-graft/ above the working folder, else "
        "~/.apm/skill-graft/."
    ),
    "skill-graft --version": "print the installed version and exit",
    "init": "create and register ~/.apm/skill-graft/",
    "init: description": (
        "Create ~/.apm/skill-graft/ with a commented skill-graft.toml and an "
        "apm.yml, and register it with `apm install -g`. Refuses if the folder "
        "exists."
    ),
    "init --project": (
        "create ./.apm/skill-graft/ instead, a package for this project, and "
        "register it with `apm install ./.apm/skill-graft` here"
    ),
    "resolve": "compute the hull, vendor it, write the lock, and show the tree",
    "resolve: description": (
        "Compute the hull (the entries and every skill their slash and Skill "
        "tool references reach), vendor its skills under their deployed names "
        "into the package's .apm/skills/, patched and renamed, write "
        "skill-graft.lock, and print the tree, then the skills prose mentions "
        "outside the hull. Reads each git source at its ref, fetching only a "
        "commit not yet cached. Run it after editing skill-graft.toml or a "
        "patch by hand."
    ),
    "deploy": "deploy what skill-graft.lock records through APM",
    "deploy: description": (
        "Deploy what skill-graft.lock records: resolve, refuse a hull other "
        "than the lock's (run `skill-graft resolve` to accept it) or an edited "
        "vendored copy, vendor the hull into the package's .apm/skills/, and "
        "deploy through `apm install`: with -g for ~/.apm/skill-graft/, in the "
        "project root for a project's package. A path source's changed skill "
        "is deployed as is, and named."
    ),
    "deploy --no-apm-install": "stop before running APM",
    "deploy --into": (
        "vendor into DIR/.apm/skills/ and write DIR/skill-graft.lock instead, "
        "leaving the package as it is; never runs APM. DIR must be an existing, "
        "empty folder outside any package, source and the cache"
    ),
    "update": "move git sources' refs to their branch tips",
    "update: description": (
        "Fetch each git source's branch tip, resolve the hull there, and only "
        "if that succeeds write the new ref into skill-graft.toml and the lock. "
        "Prints the hull diff, each changed file of each changed or added skill, "
        "and any patch hunk that no longer applies. To review an update, run "
        "`update --dry-run --diff-file review.diff`, read the file in an editor, "
        "then run the `apply:` line it prints, `update --expect <hull-digest>`."
    ),
    "update aliases": "a source alias; default: every git source",
    "update --dry-run": f"show the new shas, write {_ONLY_DIFF_FILE}",
    "update --diff-file": (
        "write the Deployed diff, each changed skill's text as deployed, to FILE, a "
        "new file or one it wrote before, named *.diff; read it in an editor"
    ),
    "update --expect": (
        "update only if the new hull has this hull digest, as the `apply:` line "
        "of a dry run with --diff-file gives it: so exactly the hull reviewed is "
        "written"
    ),
    "tree": "show the hull as a tree, writing nothing",
    "tree: description": (
        "Compute the hull as resolve does and print its tree, without the prose "
        "suggestions and without writing the lock; or print it as a Mermaid "
        "flowchart, to paste into Markdown."
    ),
    "tree --format": "text (default): resolve's tree; mermaid: a Mermaid flowchart",
    "tree --link": (
        "with --format mermaid: print a mermaid.live URL that holds the diagram "
        "in its fragment instead; nothing is uploaded, but the URL names the "
        "GitHub and GitLab repositories of the sources"
    ),
    "why": "show why a skill is in the hull, writing nothing",
    "why: description": (
        "Compute the hull as resolve does and print the paths that reach a "
        "skill, as an inverted tree: the skill first, then each skill whose "
        "slash or Skill tool reference reaches it, up to the entries."
    ),
    "why skill": (
        "a skill ID (<source alias>/<name>), or the name a hull skill deploys as"
    ),
    "vet": "flag the lines of each skill worth reading, writing nothing",
    "vet: description": (
        "Compute the hull as resolve does and scan each skill as it would "
        "deploy, patches and renames applied, every file of it, for where it "
        "may make an agent read, write or send outside the project, run code, "
        "gain privilege, persist, widen its permissions, or hide from review. "
        "Print a flag per line: <skill id> <file>:<line> <category> <owasp ids> "
        "<pattern>, line 0 for a whole file; file names as ASCII, never the "
        "text it matched. Exits 0 whatever it flags: a flag is not a fault, and "
        "no flag is not a pass. Never reads the lock or runs APM."
    ),
    "vet skills": (
        "<source alias>/<name>; default: every hull skill. One outside the hull "
        "is vetted with every skill its add would bring in"
    ),
    "vet --into": (
        "also write each skill vetted, as scanned, to DIR/<alias>/<name>/, once "
        "every skill is scanned; nothing on an error. DIR must be an existing, "
        "empty folder outside any package, source and the cache"
    ),
    "add": "add skills to the entries, then resolve",
    "add: description": (
        "Append each skill ID to `entries` in skill-graft.toml, keeping its "
        "comments and formatting. The edited config is resolved first; only if "
        "it resolves are skill-graft.toml and the lock written and the tree "
        "printed. Never deploys."
    ),
    "add skills": "<source alias>/<name>",
    "remove": "remove skills from the entries, then resolve",
    "remove: description": (
        "Delete each skill ID from `entries` in skill-graft.toml, keeping its "
        "other comments and formatting, as add does. A removed skill another "
        "entry reaches stays in the hull. Never deploys."
    ),
    "remove skills": "an entry to remove",
    "rename": "give a skill a new deployed name, then resolve",
    "rename: description": (
        "Set the skill's value in [rename] of skill-graft.toml, keeping its "
        "comments and formatting, as add does. The new deployed name is carried "
        "into every reference to the skill. Renaming a skill to the name it "
        "deploys as without one (its source's prefix, if any, before its own "
        "name) undoes its rename. Never deploys."
    ),
    "rename skill": "<source alias>/<name>",
    "rename name": "the name it deploys as",
    "bind": "bind a name to a skill or to nothing, then resolve",
    "bind: description": (
        "Set `[bind]` key <source alias>/<name> in skill-graft.toml to a skill "
        "ID, so every reference to <name> from that source resolves to it, or "
        "to false, so <name> from that source is no reference. Keeps comments "
        "and formatting, as add does. Never deploys."
    ),
    "bind key": "<source alias>/<name>",
    "bind target": "a skill ID (<source alias>/<name>), or the word false",
    "unbind": "remove a bind, then resolve",
    "unbind: description": (
        "Delete `[bind]` key <source alias>/<name> from skill-graft.toml, so "
        "references to <name> from that source resolve by default again. Keeps "
        "comments and formatting, as add does. Never deploys."
    ),
    "unbind key": "<source alias>/<name>",
    "help": "show the help of skill-graft or of a command",
    "help: description": "Show the same text as `skill-graft [command] --help`.",
    # Of each command that writes the lock, keyed by the first: resolve, add, remove,
    # rename, bind, unbind.
    "resolve: review": (
        "To review what it would vendor first, run it with --dry-run --diff-file "
        "review.diff and read review.diff in an editor, never by printing it to a "
        "terminal."
    ),
    "resolve --dry-run": f"resolve and print the hull diff, writing {_ONLY_DIFF_FILE}",
    "resolve --diff-file": (
        "write the Deployed diff, each added or changed skill's text as deployed, to "
        "FILE, a new file or one it wrote before, named *.diff; read it in an editor"
    ),
}


def _parser() -> tuple[_Parser, dict[str, argparse.ArgumentParser]]:
    """The parser and each command's own, by name."""
    parser = _Parser(
        prog="skill-graft",
        description=_TEXT["skill-graft: description"],
    )
    parser.add_argument(
        "--version", action=_Version, help=_TEXT["skill-graft --version"]
    )
    commands = parser.add_subparsers(
        dest="command", metavar="command", parser_class=_Command
    )
    init_parser = commands.add_parser(
        "init",
        help=_TEXT["init"],
        description=_TEXT["init: description"],
    )
    init_parser.add_argument(
        "--project",
        action="store_true",
        help=_TEXT["init --project"],
    )
    resolve = commands.add_parser(
        "resolve",
        help=_TEXT["resolve"],
        description=_TEXT["resolve: description"],
    )
    deploy = commands.add_parser(
        "deploy",
        help=_TEXT["deploy"],
        description=_TEXT["deploy: description"],
    )
    install = deploy.add_mutually_exclusive_group()
    install.add_argument(
        "--no-apm-install", action="store_true", help=_TEXT["deploy --no-apm-install"]
    )
    install.add_argument(
        "--into",
        type=_into,
        metavar="DIR",
        help=_TEXT["deploy --into"],
    )
    update_parser = commands.add_parser(
        "update",
        help=_TEXT["update"],
        description=_TEXT["update: description"],
    )
    update_parser.add_argument(
        "aliases",
        nargs="*",
        metavar="source",
        help=_TEXT["update aliases"],
    )
    update_parser.add_argument(
        "--dry-run",
        action="store_true",
        help=_TEXT["update --dry-run"],
    )
    _diff_file_option(update_parser, _TEXT["update --diff-file"])
    update_parser.add_argument(
        "--expect",
        metavar="hull-digest",
        help=_TEXT["update --expect"],
    )
    tree = commands.add_parser(
        "tree",
        help=_TEXT["tree"],
        description=_TEXT["tree: description"],
    )
    tree.add_argument(
        "--format",
        choices=["text", "mermaid"],
        # No default: `tree` prints text for any format but `mermaid`.
        help=_TEXT["tree --format"],
    )
    tree.add_argument(
        "--link",
        action="store_true",
        help=_TEXT["tree --link"],
    )
    why = commands.add_parser(
        "why",
        help=_TEXT["why"],
        description=_TEXT["why: description"],
    )
    why.add_argument(
        "skill",
        help=_TEXT["why skill"],
    )
    vet_parser = commands.add_parser(
        "vet",
        help=_TEXT["vet"],
        description=_TEXT["vet: description"],
    )
    vet_parser.add_argument(
        "skills",
        nargs="*",
        metavar="skill-id",
        help=_TEXT["vet skills"],
    )
    vet_parser.add_argument(
        "--into",
        type=_into,
        metavar="DIR",
        help=_TEXT["vet --into"],
    )
    add = commands.add_parser(
        "add",
        help=_TEXT["add"],
        description=_TEXT["add: description"],
    )
    add.add_argument("skills", nargs="+", metavar="skill-id", help=_TEXT["add skills"])
    remove = commands.add_parser(
        "remove",
        help=_TEXT["remove"],
        description=_TEXT["remove: description"],
    )
    remove.add_argument(
        "skills", nargs="+", metavar="skill-id", help=_TEXT["remove skills"]
    )
    rename = commands.add_parser(
        "rename",
        help=_TEXT["rename"],
        description=_TEXT["rename: description"],
    )
    rename.add_argument("skill", metavar="skill-id", help=_TEXT["rename skill"])
    rename.add_argument("name", help=_TEXT["rename name"])
    bind = commands.add_parser(
        "bind",
        help=_TEXT["bind"],
        description=_TEXT["bind: description"],
    )
    bind.add_argument("key", metavar="alias/name", help=_TEXT["bind key"])
    bind.add_argument("target", help=_TEXT["bind target"])
    unbind = commands.add_parser(
        "unbind",
        help=_TEXT["unbind"],
        description=_TEXT["unbind: description"],
    )
    unbind.add_argument("key", metavar="alias/name", help=_TEXT["unbind key"])
    for staging in (resolve, add, remove, rename, bind, unbind):
        _review_options(staging)
    help_parser = commands.add_parser(
        "help",
        help=_TEXT["help"],
        description=_TEXT["help: description"],
    )
    # Not `command`: the subcommand's namespace would overwrite the top level's.
    help_parser.add_argument("topic", nargs="?", metavar="command")
    parser.commands = "".join(
        f"  {action.dest:<10}{action.help}\n" for action in commands._choices_actions
    )
    return parser, dict(commands.choices)


def main(argv: list[str] | None = None) -> int:
    """Runs the command line, then flushes stdout, also after argparse's exits: so
    `help`, `--version` and `--help` find a closed stdout as a command does.

    Refuses native Windows first, whatever the command line."""
    platform = sys.platform  # compared directly, mypy would skip the branch
    if platform == "win32":
        print(f"skill-graft: {WINDOWS}", file=sys.stderr)
        return 1
    try:
        status = _main(argv)
    except SystemExit as exit:
        if _fails_on_flush(exit.code not in (0, None)):
            raise SystemExit(1) from None
        raise
    except OSError as error:  # a print outside any command, `--version`'s or help's
        print_error(error)
        _fails_on_flush(True)  # discards the rest, silently
        return 1
    return 1 if _fails_on_flush(status != 0) else status


def _fails_on_flush(failed: bool) -> bool:
    """Flushes stdout; whether that fails a command that had not failed, printing the
    error line as for the command's own."""
    try:
        flush_stdout()
    except OSError as error:
        if not failed:
            print_error(error)
            return True
    return False


def _review_options(parser: argparse.ArgumentParser) -> None:
    """The options a command that writes the lock offers to review it first."""
    parser.description = f"{parser.description} {_TEXT['resolve: review']}"
    parser.add_argument(
        "--dry-run", action="store_true", help=_TEXT["resolve --dry-run"]
    )
    _diff_file_option(parser, _TEXT["resolve --diff-file"])


def _diff_file_option(parser: argparse.ArgumentParser, text: str) -> None:
    """`--diff-file`, writing the Deployed diff, with its help `text`."""
    parser.add_argument("--diff-file", type=Path, metavar="FILE", help=text)


def _main(argv: list[str] | None) -> int:
    # Here, not at load: on native Windows `main` refuses before any command module,
    # which may import a POSIX-only one such as `fcntl`, loads.
    from skill_graft.commands import (
        deploy,
        edit,
        explain,
        housekeeping,
        init_package,
        resolve,
        scope,
        update,
        vet,
    )

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
        project = args.command == "init" and args.project
        with warnings_last() as warnings:
            current = scope.of(args.command, project)
            if args.command == "init":
                init_package.init(current, project)
            elif args.command == "update":
                update.update(
                    current,
                    warnings,
                    args.aliases,
                    args.dry_run,
                    args.diff_file,
                    args.expect,
                )
            elif args.command == "add":
                edit.add(current, warnings, args.skills, args.dry_run, args.diff_file)
            elif args.command == "remove":
                edit.remove(
                    current, warnings, args.skills, args.dry_run, args.diff_file
                )
            elif args.command == "rename":
                edit.rename(
                    current,
                    warnings,
                    args.skill,
                    args.name,
                    args.dry_run,
                    args.diff_file,
                )
            elif args.command == "bind":
                edit.bind(
                    current,
                    warnings,
                    args.key,
                    args.target,
                    args.dry_run,
                    args.diff_file,
                )
            elif args.command == "unbind":
                edit.unbind(current, warnings, args.key, args.dry_run, args.diff_file)
            elif args.command == "why":
                explain.show_why(current, warnings, args.skill)
            elif args.command == "vet":
                vet.vet(current, warnings, args.skills, args.into)
            elif args.command == "tree":
                mermaid = args.format == "mermaid"
                explain.show_tree(current, warnings, mermaid, args.link)
            elif args.command == "resolve":
                resolve.resolve(current, warnings, args.dry_run, args.diff_file)
            elif args.command == "deploy":
                deploy.deploy(current, warnings, args.into, args.no_apm_install)
        status = 0
    except (SkillGraftError, OSError) as error:
        print_error(error)
        status = 1
    # The one place that sees every command end: `init` reads no source, and a
    # dry run writes no cache.
    if args.command != "init" and not vars(args).get("dry_run"):
        housekeeping.prune()
    return status


def _into(value: str) -> Path:
    """`--into`'s folder; an empty value would mean the working folder."""
    if not value:
        raise argparse.ArgumentTypeError("must not be empty")
    return Path(value)


if __name__ == "__main__":
    sys.exit(main())
