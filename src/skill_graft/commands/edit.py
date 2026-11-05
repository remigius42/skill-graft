"""Edits skill-graft.toml in place: `add`, `remove`, `rename`, `bind` and `unbind`.

Each edit resolves the edited text first and writes nothing unless it resolves.
"""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

import tomlkit
from tomlkit.items import Array, Table

from skill_graft.commands import explain, review, transaction
from skill_graft.infra import files, paths
from skill_graft.infra.errors import SkillGraftError, notice
from skill_graft.pipeline import compute, config
from skill_graft.pipeline.hull import Hull, reach

# What an edit's dry run does not write.
WRITTEN = "skill-graft.toml, skill-graft.lock and .apm/skills/"
# Its header: what an edit's `--diff-file` compares.
HEADER = review.header(
    "the Vendored copies against what the edited config would vendor"
)


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
    scope: paths.Scope,
    warnings: list[str],
    skills: list[str],
    dry_run: bool = False,
    diff: Path | None = None,
) -> None:
    """Appends each skill ID to `entries`."""
    with review.running(["add", *skills], dry_run, diff, WRITTEN) as run:
        _add(scope, warnings, skills, run)


def _add(
    scope: paths.Scope, warnings: list[str], skills: list[str], run: review.Run
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
        run.proceed()
        hull = _finish(scope, warnings, document, run)
    # The hull before the edit: what the other entries reach.
    parents = reach(hull, [e for e in hull.entries if str(e) not in added])
    for skill in hull.entries:
        if str(skill) in added and skill in parents:
            notice(f"`{skill}` was already in the hull, via `{parents[skill]}`")


def remove(
    scope: paths.Scope,
    warnings: list[str],
    skills: list[str],
    dry_run: bool = False,
    diff: Path | None = None,
) -> None:
    """Deletes each skill ID from `entries`."""
    with review.running(["remove", *skills], dry_run, diff, WRITTEN) as run:
        _remove(scope, warnings, skills, run)


def _remove(
    scope: paths.Scope, warnings: list[str], skills: list[str], run: review.Run
) -> None:
    with _reading(scope, warnings) as (document, _):
        array = cast(Array, document.get("entries", tomlkit.array()))
        for text in dict.fromkeys(skills):
            if text not in array:
                raise SkillGraftError(f"`{text}` is no entry")
            array.remove(text)
        run.proceed()
        hull = _finish(scope, warnings, document, run)
    parents = reach(hull, hull.entries)  # the remaining entries
    for skill, parent in parents.items():
        if str(skill) in skills:
            notice(f"`{skill}` stays in the hull, via `{parent}`")


def rename(
    scope: paths.Scope,
    warnings: list[str],
    text: str,
    name: str,
    dry_run: bool = False,
    diff: Path | None = None,
) -> None:
    """Sets the skill's `[rename]` value to `name`."""
    with review.running(["rename", text, name], dry_run, diff, WRITTEN) as run:
        _rename(scope, warnings, text, name, run)


def _rename(
    scope: paths.Scope, warnings: list[str], text: str, name: str, run: review.Run
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
        run.proceed()
        _finish(scope, warnings, document, run)


def bind(
    scope: paths.Scope,
    warnings: list[str],
    key: str,
    target: str,
    dry_run: bool = False,
    diff: Path | None = None,
) -> None:
    """Sets `[bind]` key `key` to the skill ID `target`, or to `false`."""
    with review.running(["bind", key, target], dry_run, diff, WRITTEN) as run:
        _bind(scope, warnings, key, target, run)


def _bind(
    scope: paths.Scope, warnings: list[str], key: str, target: str, run: review.Run
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
        run.proceed()
        _finish(scope, warnings, document, run)


def unbind(
    scope: paths.Scope,
    warnings: list[str],
    key: str,
    dry_run: bool = False,
    diff: Path | None = None,
) -> None:
    """Deletes `[bind]` key `key`, leaving the table."""
    with review.running(["unbind", key], dry_run, diff, WRITTEN) as run:
        _unbind(scope, warnings, key, run)


def _unbind(scope: paths.Scope, warnings: list[str], key: str, run: review.Run) -> None:
    with _reading(scope, warnings) as (document, loaded):
        # Parsed first, so a malformed key or undeclared alias is said so, as by `bind`.
        if config.parse_skill_id("unbind", key, loaded.sources) not in loaded.binds:
            raise SkillGraftError(f"`{key}` is not bound")
        del cast(Table, document["bind"])[key]
        run.proceed()
        _finish(scope, warnings, document, run)


def _finish(
    scope: paths.Scope,
    warnings: list[str],
    document: tomlkit.TOMLDocument,
    run: review.Run,
) -> Hull:
    """Resolves the edited config; only if it resolves, writes it and the lock,
    leaving neither changed if the lock fails. A dry run writes neither, and
    prints the Hull diff first."""
    text = tomlkit.dumps(document)
    # Relative paths start where `load` starts them, even for a symlinked file.
    loaded = config.parse(scope, text)
    warnings.extend(loaded.warnings)
    with transaction.resolving(
        scope, loaded, warnings, run.cache, write=not run.dry_run
    ) as resolution:
        review.stage(run, scope, loaded, resolution, HEADER)
        resolution.writes.append(
            (scope.config_file.resolve(), lambda: write(scope, document))
        )
    run.committed = True
    explain.show(resolution.hull)
    review.finish(run)
    return resolution.hull
