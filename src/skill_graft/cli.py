"""The `skill-graft` command line."""

import argparse
import contextlib
import json
import os
import re
import shutil
import sys
import textwrap
from collections.abc import Callable
from importlib import metadata
from pathlib import Path
from typing import Any, NoReturn, TypeGuard

from skill_graft.commands import edit, explain, init_package, resolve, scope, update
from skill_graft.infra import apm, paths
from skill_graft.infra.cache import Cache
from skill_graft.infra.errors import SkillGraftError, notice, warnings_last
from skill_graft.pipeline import compute, config, lock, patch, vendor
from skill_graft.pipeline.hull import Hull


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


class _Version(argparse.Action):
    """Prints the installed version and exits, read only when asked for."""

    def __init__(self, option_strings: list[str], dest: str, **kwargs: Any) -> None:
        super().__init__(
            option_strings, dest, nargs=0, default=argparse.SUPPRESS, **kwargs
        )

    def __call__(self, parser: argparse.ArgumentParser, *_: Any) -> NoReturn:
        try:
            distribution = metadata.distribution("skill-graft")
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
    version = fields["Version"].strip() if "Version" in fields else None
    return version if _printable(version) else "unknown"


def _printable(text: object) -> TypeGuard[str]:
    """Whether `text` is a non-empty string of printable ASCII without spaces: one
    word, safe on one line of any terminal."""
    return isinstance(text, str) and re.fullmatch(r"[!-~]+", text) is not None


def _origin(distribution: metadata.Distribution) -> str:
    """` (<revision> @ <commit>)` for a git install, from the installer's direct_url.json
    (PEP 610); anything else, malformed or unreadable included, adds nothing."""
    try:
        direct_url = json.loads(distribution.read_text("direct_url.json") or "{}")
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
    parser.add_argument(
        "--version", action=_Version, help="print the installed version and exit"
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
    install = build.add_mutually_exclusive_group()
    install.add_argument(
        "--no-install", action="store_true", help="stop before running APM"
    )
    install.add_argument(
        "--into",
        type=_into,
        metavar="DIR",
        help=(
            "vendor into DIR/.apm/skills/ and write DIR/skill-graft.lock instead, "
            "leaving the package as it is; never runs APM. DIR must be an existing, "
            "empty folder outside any package, source and the cache"
        ),
    )
    update_parser = commands.add_parser(
        "update",
        help="move git sources' refs to their branch tips",
        description=(
            "Fetch each git source's branch tip, resolve the hull there, and only "
            "if that succeeds write the new ref into skill-graft.toml and the lock. "
            "Prints the hull diff, each changed file of each changed or added skill, "
            "and any patch hunk that no longer applies. To review an update, run "
            "`update --dry-run --diff review.diff`, read the file in an editor, then "
            "run the `apply:` line it prints, `update --expect <digest>`."
        ),
    )
    update_parser.add_argument(
        "aliases",
        nargs="*",
        metavar="source",
        help="a source alias; default: every git source",
    )
    update_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show the new shas, write nothing but --diff's file",
    )
    update_parser.add_argument(
        "--diff",
        type=Path,
        metavar="FILE",
        help=(
            "write the Deployed diff, each changed skill's text as deployed, to FILE, "
            "a new file or one it wrote before, named *.diff; read it in an editor"
        ),
    )
    update_parser.add_argument(
        "--expect",
        metavar="DIGEST",
        help=(
            "update only if the new hull's digest is DIGEST, as the `apply:` line of "
            "a dry run with --diff gives it: so exactly the hull reviewed is written"
        ),
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
            "in its fragment instead; nothing is uploaded, but the URL names the "
            "GitHub and GitLab repositories of the sources"
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
            "into every reference to the skill. Renaming a skill to the name it "
            "deploys as without one (its source's prefix, if any, before its own "
            "name) undoes its rename. Never builds."
        ),
    )
    rename.add_argument("skill", metavar="skill-id", help="<source alias>/<name>")
    rename.add_argument("name", help="the name it deploys as")
    bind = commands.add_parser(
        "bind",
        help="bind a name to a skill or to nothing, then resolve",
        description=(
            "Set `[bind]` key <source alias>/<name> in skill-graft.toml to a skill "
            "ID, so every reference to <name> from that source resolves to it, or "
            "to false, so <name> from that source is no reference. Keeps comments "
            "and formatting, as add does. Never builds."
        ),
    )
    bind.add_argument("key", metavar="alias/name", help="<source alias>/<name>")
    bind.add_argument(
        "target", help="a skill ID (<source alias>/<name>), or the word false"
    )
    unbind = commands.add_parser(
        "unbind",
        help="remove a bind, then resolve",
        description=(
            "Delete `[bind]` key <source alias>/<name> from skill-graft.toml, so "
            "references to <name> from that source resolve by default again. Keeps "
            "comments and formatting, as add does. Never builds."
        ),
    )
    unbind.add_argument("key", metavar="alias/name", help="<source alias>/<name>")
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
        project = args.command == "init" and args.project
        with warnings_last() as warnings, scope.of(args.command, project) as current:
            if args.command == "build" and args.into is not None:
                notice(f"into: {args.into.absolute()}")
                _check_into(args.into)
            if args.command == "init":
                init_package.init(args.project)
            elif args.command == "update":
                update.update(
                    current,
                    warnings,
                    args.aliases,
                    args.dry_run,
                    args.diff,
                    args.expect,
                )
            elif args.command == "add":
                edit.add(current, warnings, args.skills)
            elif args.command == "remove":
                edit.remove(current, warnings, args.skills)
            elif args.command == "rename":
                edit.rename(current, warnings, args.skill, args.name)
            elif args.command == "bind":
                edit.bind(current, warnings, args.key, args.target)
            elif args.command == "unbind":
                edit.unbind(current, warnings, args.key)
            elif args.command == "why":

                def why(loaded: config.Config, resolved: Hull) -> None:
                    warnings.extend(resolved.warnings)
                    target = explain.find(
                        resolved,
                        args.skill,
                        lambda text: compute.known(loaded, "why", text),
                    )
                    print(explain.why(resolved, target), end="")

                _explain(warnings, why)
            elif args.command == "tree":

                def tree(loaded: config.Config, resolved: Hull) -> None:
                    warnings.extend(resolved.warnings)
                    if args.format == "mermaid":  # --link needs it
                        cache = Cache(paths.cache())
                        repositories = explain.repositories(loaded, cache, resolved)
                        diagram = explain.mermaid(resolved, repositories)
                        if args.link:
                            print(explain.link(diagram))
                        else:
                            print(diagram, end="")
                    else:
                        print(explain.tree(resolved), end="")

                _explain(warnings, tree)
            elif args.command == "resolve":
                resolve.resolve(current, warnings)
            elif args.command == "build":
                # `--into` mirrors the package's layout in another folder.
                given: Path | None = args.into
                into = None if given is None else given.resolve()
                skills = paths.skills() if into is None else into / ".apm" / "skills"
                started = False
                try:
                    loaded = resolve.load(warnings)
                    if given is not None:
                        _check_into_sources(given, loaded)
                    with compute.compute_hull(loaded) as resolved:
                        warnings.extend(resolved.warnings)
                        started = True  # from here on `into` may hold our writes
                        vendor.vendor(resolved, skills)
                    # Hashes the vendored copies, so the lock holds what was vendored.
                    copies = {
                        s: lock.folder_hash(skills / resolved.deployed[s])
                        for s in resolved.skills
                    }
                    lock_file = None if into is None else into / "skill-graft.lock"
                    lock.write(lock.render(loaded, {}, resolved, copies), lock_file)
                except BaseException:
                    # After the work folder is gone, which a TMPDIR may put in `into`.
                    if into is not None and started:
                        _undo_into(into)
                    raise
                if (
                    into is None
                ):  # its hint, `resolve`, would rewrite the package's lock
                    # Once nothing before APM can fail.
                    explain.announce_suggestions(resolved)
                    if not args.no_install:
                        apm.install()
    except (SkillGraftError, OSError) as error:
        print(f"skill-graft: {error}", file=sys.stderr)
        return 1
    return 0


def _into(value: str) -> Path:
    """`--into`'s folder; an empty value would mean the working folder."""
    if not value:
        raise argparse.ArgumentTypeError("must not be empty")
    return Path(value)


def _check_into(into: Path) -> None:
    """Refuses an `--into` folder `build` could not use without harm: anything but an
    existing, empty folder, or one in a package or in or around the cache."""
    if not into.exists():
        raise SkillGraftError(f"--into {into}: no such folder")
    if not into.is_dir():
        raise SkillGraftError(f"--into {into}: not a folder")
    if any(into.iterdir()):
        raise SkillGraftError(f"--into {into}: not empty")
    resolved = paths.folded(into.resolve())
    # As given too, but without `..`: a path only passing through a package is fine.
    given = paths.folded(Path(os.path.normpath(into.absolute())))
    if any(paths.in_package(p) for p in (given, resolved)):
        raise SkillGraftError(f"--into {into}: inside a package (.apm/skill-graft)")
    if paths.overlap(resolved, paths.folded(cache := paths.cache().resolve())):
        raise SkillGraftError(f"--into {into}: overlaps the cache {cache}")


def _check_into_sources(into: Path, loaded: config.Config) -> None:
    """Refuses an `--into` folder inside a path source, compared resolved."""
    folded = paths.folded(into.resolve())
    for alias, source in sorted(loaded.sources.items()):
        if isinstance(source, config.PathSource) and folded.is_relative_to(
            paths.folded(source.folder)
        ):
            raise SkillGraftError(f"--into {into}: inside source {alias!r}")


def _undo_into(into: Path) -> None:
    """Removes what a failed `build --into` wrote in `into`, and nothing else there.

    Never raises: the build's own error is the one to report.
    """
    folder = into / ".apm"
    for name in ("skills.new", "skills.old", "skills"):  # `.new` stays on Ctrl-C
        shutil.rmtree(folder / name, ignore_errors=True)
    with contextlib.suppress(OSError):
        (into / "skill-graft.lock").unlink(missing_ok=True)
    with contextlib.suppress(OSError):  # kept if another process wrote into it
        folder.rmdir()


def _explain(warnings: list[str], show: Callable[[config.Config, Hull], None]) -> None:
    """Runs `show` on the hull; on one failing only on hidden characters, on the
    hull as walked, so the user sees what pulls them in, then fails."""
    loaded = resolve.load(warnings)
    try:
        with compute.compute_hull(loaded) as resolved:
            show(loaded, resolved)
    except patch.PatchError as error:
        if error.hull is None:
            raise
        try:
            show(loaded, error.hull)
        except SkillGraftError as shown:  # both matter: the hidden characters too
            raise SkillGraftError(f"{shown}\n{error}") from None
        raise


if __name__ == "__main__":
    sys.exit(main())
