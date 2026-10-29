"""Edits skill-graft.toml in place: `add`, `remove`, `rename`, `bind` and `unbind`.

Each edit resolves the edited text first and writes nothing unless it resolves.
"""

from collections import deque
from collections.abc import Generator
from contextlib import contextmanager
from typing import cast

import tomlkit
from tomlkit.items import Array, Table

from skill_graft.commands import explain, resolve
from skill_graft.infra import files, paths
from skill_graft.infra.errors import SkillGraftError, notice
from skill_graft.pipeline import compute, config
from skill_graft.pipeline.config import SkillId
from skill_graft.pipeline.hull import Hull


def read() -> tuple[tomlkit.TOMLDocument, config.Config]:
    """The config as `tomlkit` keeps it, comments and formatting included, and as
    `load` reads it.

    Checked as `load` checks it first, so an edit only ever sees a valid config.
    """
    text = config.text()
    loaded = config.parse(text, paths.config_file())  # before tomlkit sees it
    return tomlkit.parse(text), loaded


@contextmanager
def _reading(
    warnings: list[str],
) -> Generator[tuple[tomlkit.TOMLDocument, config.Config]]:
    """`read`'s result; if the edit fails, the warnings of the config read, which
    the edited one shares: an edit never changes its sources."""
    document, loaded = read()
    try:
        yield document, loaded
    except BaseException:
        warnings.extend(loaded.warnings)
        raise


def write(document: tomlkit.TOMLDocument) -> None:
    """Replaces the config atomically; a symlink's target, not the link."""
    files.atomic_write(paths.config_file().resolve(), tomlkit.dumps(document).encode())


def add(scope: paths.Scope, warnings: list[str], skills: list[str]) -> None:
    """Appends each skill ID to `entries`."""
    with _reading(warnings) as (document, _):
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
        hull = _finish(scope, warnings, document)
    # The hull before the edit: what the other entries reach.
    parents = _reach(hull, [e for e in hull.entries if str(e) not in added])
    for skill in hull.entries:
        if str(skill) in added and skill in parents:
            notice(f"`{skill}` was already in the hull, via `{parents[skill]}`")


def remove(scope: paths.Scope, warnings: list[str], skills: list[str]) -> None:
    """Deletes each skill ID from `entries`."""
    with _reading(warnings) as (document, _):
        array = cast(Array, document.get("entries", tomlkit.array()))
        for text in dict.fromkeys(skills):
            if text not in array:
                raise SkillGraftError(f"`{text}` is no entry")
            array.remove(text)
        hull = _finish(scope, warnings, document)
    parents = _reach(hull, hull.entries)  # the remaining entries
    for skill, parent in parents.items():
        if str(skill) in skills:
            notice(f"`{skill}` stays in the hull, via `{parent}`")


def rename(scope: paths.Scope, warnings: list[str], text: str, name: str) -> None:
    """Sets the skill's `[rename]` value to `name`."""
    with _reading(warnings) as (document, loaded):
        if not config.NAME.fullmatch(name):  # before looking anything up
            raise SkillGraftError(
                f"rename: {name!r} is not a skill name: {config.NAME.pattern}"
            )
        skill = compute.known(loaded, "rename", text)
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
        _finish(scope, warnings, document)


def bind(scope: paths.Scope, warnings: list[str], key: str, target: str) -> None:
    """Sets `[bind]` key `key` to the skill ID `target`, or to `false`."""
    with _reading(warnings) as (document, loaded):
        skill = config.parse_skill_id("bind", key, loaded.sources)
        # Resolving checks the target; a no-op skips that, so it is checked here
        # first: one gone upstream is no longer bound. Present too: a missing key
        # reads as None.
        if skill in loaded.binds:
            bound = None if target == "false" else compute.known(loaded, "bind", target)
            if loaded.binds[skill] == bound:
                notice(f"`{key}` is already bound to `{target}`")
                return
        if "bind" not in document:
            document.add("bind", tomlkit.table())
        cast(Table, document["bind"])[key] = False if target == "false" else target
        _finish(scope, warnings, document)


def unbind(scope: paths.Scope, warnings: list[str], key: str) -> None:
    """Deletes `[bind]` key `key`, leaving the table."""
    with _reading(warnings) as (document, loaded):
        # Parsed first, so a malformed key or undeclared alias is said so, as by `bind`.
        if config.parse_skill_id("unbind", key, loaded.sources) not in loaded.binds:
            raise SkillGraftError(f"`{key}` is not bound")
        del cast(Table, document["bind"])[key]
        _finish(scope, warnings, document)


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
    scope: paths.Scope, warnings: list[str], document: tomlkit.TOMLDocument
) -> Hull:
    """Resolves the edited config; only if it resolves, writes it and the lock,
    leaving neither changed if the lock fails."""
    text = tomlkit.dumps(document)
    # Relative paths start where `load` starts them, even for a symlinked file.
    loaded = config.parse(text, paths.config_file())
    warnings.extend(loaded.warnings)
    with resolve.resolving(scope, loaded, warnings) as resolution:
        resolution.writes.append(
            (paths.config_file().resolve(), lambda: write(document))
        )
    explain.show(resolution.hull)
    return resolution.hull
