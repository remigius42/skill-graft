"""Edits skill-graft.toml in place: `add`, `remove`, `rename`, `bind` and `unbind`.

Each edit resolves the edited text first and writes nothing unless it resolves.
"""

import shlex
import tempfile
from collections import deque
from collections.abc import Generator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import cast

import tomlkit
from tomlkit.items import Array, Table

from skill_graft.commands import explain, review, transaction
from skill_graft.infra import files, paths
from skill_graft.infra.cache import Cache
from skill_graft.infra.errors import SkillGraftError, notice
from skill_graft.pipeline import compute, config, lock
from skill_graft.pipeline.config import SkillId
from skill_graft.pipeline.hull import Hull, PatchError


def read(scope: paths.Scope) -> tuple[tomlkit.TOMLDocument, config.Config]:
    """The config as `tomlkit` keeps it, comments and formatting included, and as
    `load` reads it.

    Checked as `load` checks it first, so an edit only ever sees a valid config.
    """
    text = config.text(scope)
    loaded = config.parse(scope, text)  # before tomlkit sees it
    return tomlkit.parse(text), loaded


@contextmanager
def _reading(
    scope: paths.Scope, warnings: list[str]
) -> Generator[tuple[tomlkit.TOMLDocument, config.Config]]:
    """`read`'s result; if the edit fails, the warnings of the config read, which
    the edited one shares: an edit never changes its sources."""
    document, loaded = read(scope)
    try:
        yield document, loaded
    except BaseException:
        warnings.extend(loaded.warnings)
        raise


def write(scope: paths.Scope, document: tomlkit.TOMLDocument) -> None:
    """Replaces the config atomically; a symlink's target, not the link."""
    files.atomic_write(scope.config_file.resolve(), tomlkit.dumps(document).encode())


def add(
    scope: paths.Scope, warnings: list[str], skills: list[str], dry_run: bool = False
) -> None:
    """Appends each skill ID to `entries`."""
    with _running(["add", *skills], dry_run) as run:
        _add(scope, warnings, skills, run)


def _add(
    scope: paths.Scope, warnings: list[str], skills: list[str], run: "_Run"
) -> None:
    with _reading(scope, warnings) as (document, _):
        if "entries" not in document:
            document["entries"] = tomlkit.array()  # before the first table
        array = cast(Array, document["entries"])
        added = []
        for text in dict.fromkeys(skills):  # each once, in the order given
            if text in array:
                notice(f"`{text}` is already an entry")
            else:
                array.append(text)
                added.append(text)
        if not added:
            return
        run.edits()
        hull = _finish(scope, warnings, document, run)
    # The hull before the edit: what the other entries reach.
    parents = _reach(hull, [e for e in hull.entries if str(e) not in added])
    for skill in hull.entries:
        if str(skill) in added and skill in parents:
            notice(f"`{skill}` was already in the hull, via `{parents[skill]}`")


def remove(
    scope: paths.Scope, warnings: list[str], skills: list[str], dry_run: bool = False
) -> None:
    """Deletes each skill ID from `entries`."""
    with _running(["remove", *skills], dry_run) as run:
        _remove(scope, warnings, skills, run)


def _remove(
    scope: paths.Scope, warnings: list[str], skills: list[str], run: "_Run"
) -> None:
    with _reading(scope, warnings) as (document, _):
        array = cast(Array, document.get("entries", tomlkit.array()))
        for text in dict.fromkeys(skills):
            if text not in array:
                raise SkillGraftError(f"`{text}` is no entry")
            array.remove(text)
        run.edits()
        hull = _finish(scope, warnings, document, run)
    parents = _reach(hull, hull.entries)  # the remaining entries
    for skill, parent in parents.items():
        if str(skill) in skills:
            notice(f"`{skill}` stays in the hull, via `{parent}`")


def rename(
    scope: paths.Scope, warnings: list[str], text: str, name: str, dry_run: bool = False
) -> None:
    """Sets the skill's `[rename]` value to `name`."""
    with _running(["rename", text, name], dry_run) as run:
        _rename(scope, warnings, text, name, run)


def _rename(
    scope: paths.Scope, warnings: list[str], text: str, name: str, run: "_Run"
) -> None:
    with _reading(scope, warnings) as (document, loaded):
        if not config.NAME.fullmatch(name):  # before looking anything up
            raise SkillGraftError(
                f"rename: {name!r} is not a skill name: {config.NAME.pattern}"
            )
        skill = compute.known(scope, loaded, run.cache, "rename", text)
        if config.deployed(loaded, skill) == name:
            notice(f"`{skill}` already deploys as `{name}`")
            return
        if "rename" not in document:
            document.add("rename", tomlkit.table())
        table = cast(Table, document["rename"])
        # The name it deploys as without a key: the rename is undone. With no key that
        # is its deployed name, handled above, so the key exists.
        if name == config.default_name(loaded, skill):
            del table[text]
        else:
            table[text] = name
        run.edits()
        _finish(scope, warnings, document, run)


def bind(
    scope: paths.Scope,
    warnings: list[str],
    key: str,
    target: str,
    dry_run: bool = False,
) -> None:
    """Sets `[bind]` key `key` to the skill ID `target`, or to `false`."""
    with _running(["bind", key, target], dry_run) as run:
        _bind(scope, warnings, key, target, run)


def _bind(
    scope: paths.Scope, warnings: list[str], key: str, target: str, run: "_Run"
) -> None:
    with _reading(scope, warnings) as (document, loaded):
        skill = config.parse_skill_id("bind", key, loaded.sources)
        # Checked here, reading only its source, though resolving checks it too: a
        # typo is reported before another source's missing ref, and a no-op skips
        # resolving, yet one gone upstream is no longer bound.
        bound = (
            None
            if target == "false"
            else compute.known(scope, loaded, run.cache, "bind", target)
        )
        # `binds.get` would read a missing key as None, `false`'s value: check it is
        # present.
        if skill in loaded.binds and loaded.binds[skill] == bound:
            notice(f"`{key}` is already bound to `{target}`")
            return
        if "bind" not in document:
            document.add("bind", tomlkit.table())
        cast(Table, document["bind"])[key] = False if target == "false" else target
        run.edits()
        _finish(scope, warnings, document, run)


def unbind(
    scope: paths.Scope, warnings: list[str], key: str, dry_run: bool = False
) -> None:
    """Deletes `[bind]` key `key`, leaving the table."""
    with _running(["unbind", key], dry_run) as run:
        _unbind(scope, warnings, key, run)


def _unbind(scope: paths.Scope, warnings: list[str], key: str, run: "_Run") -> None:
    with _reading(scope, warnings) as (document, loaded):
        # Parsed first, so a malformed key or undeclared alias is said so, as by `bind`.
        if config.parse_skill_id("unbind", key, loaded.sources) not in loaded.binds:
            raise SkillGraftError(f"`{key}` is not bound")
        del cast(Table, document["bind"])[key]
        run.edits()
        _finish(scope, warnings, document, run)


def _reach(hull: Hull, seeds: list[SkillId]) -> dict[SkillId, SkillId]:
    """What `seeds` reach over slash and Skill tool edges: each skill's parent.

    A skill's edges do not depend on the entries, so the edited hull answers for
    any subset of them. Breadth-first, so a parent is reached before its child.
    """
    targets: dict[SkillId, list[SkillId]] = {}
    for edge in hull.edges:  # in scan order
        if edge.kind != "prose":
            targets.setdefault(edge.source, []).append(edge.target)
    parents: dict[SkillId, SkillId] = {}
    seen = set(seeds)
    queue = deque(seeds)
    while queue:
        current = queue.popleft()
        for target in targets.get(current, []):
            if target not in seen:
                seen.add(target)
                parents[target] = current
                queue.append(target)
    return parents


def _finish(
    scope: paths.Scope,
    warnings: list[str],
    document: tomlkit.TOMLDocument,
    run: "_Run",
) -> Hull:
    """Resolves the edited config; only if it resolves, writes it and the lock,
    leaving neither changed if the lock fails. A dry run writes neither, and
    prints the Hull diff first."""
    text = tomlkit.dumps(document)
    # Relative paths start where `load` starts them, even for a symlinked file.
    loaded = config.parse(scope, text)
    warnings.extend(loaded.warnings)
    shown = {}
    with transaction.resolving(
        scope, loaded, warnings, run.cache, write=not run.dry_run
    ) as resolution:
        if run.dry_run:  # while the patched copies exist
            hull = resolution.hull
            hashes = resolution.hashes = lock.skill_hashes(hull)
            before = review.vendored(scope.skills, lock.load(scope.lock_file))
            shown = review.print_diff(before, hull, hashes)
        resolution.writes.append(
            (scope.config_file.resolve(), lambda: write(scope, document))
        )
    run.changed = bool(shown)
    explain.show(resolution.hull)
    return resolution.hull


class _Run:
    """One edit's run: its cache, a dry run's layered over a temporary folder the
    run removes, and the lines a dry run prints last."""

    def __init__(self, stack: ExitStack, command: list[str], dry_run: bool) -> None:
        self.stack = stack
        self.command = " ".join(shlex.quote(arg) for arg in command)
        self.dry_run = dry_run
        self.cache = Cache.default()
        self.tmp: Path | None = None
        self.changed = False  # whether the Hull diff marks a skill `+` or `~`
        if dry_run:
            self.tmp = Path(
                stack.enter_context(tempfile.TemporaryDirectory(prefix="skill-graft-"))
            )
            self.cache = Cache(self.tmp, self.cache)

    def edits(self) -> None:
        """Past the no-op check: a dry run's last lines, the hint first, printed
        even on a failure."""
        if not self.dry_run:
            return
        self.stack.callback(
            print,
            "dry run: skill-graft.toml, skill-graft.lock and .apm/skills/ not written",
        )
        self.stack.callback(self._hint)

    def _hint(self) -> None:
        if self.changed:
            print(f"review: skill-graft {self.command} --dry-run --diff <file>")


@contextmanager
def _running(command: list[str], dry_run: bool) -> Generator[_Run]:
    """The run of the edit `command` names; a failing patch named, in a dry run,
    with how to keep what it fetched."""
    with ExitStack() as stack:
        run = _Run(stack, command, dry_run)
        try:
            yield run
        except PatchError as error:
            if run.tmp is None:
                raise
            keep = (
                f"run `skill-graft {run.command}` without `--dry-run` "
                "to keep what it fetched"
            )
            raise review.fetch_hint(error, run.tmp, keep) from None
