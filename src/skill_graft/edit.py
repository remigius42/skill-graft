"""Edits skill-graft.toml in place: `add`, `remove` and `rename`.

Each edit resolves the edited text first and writes nothing unless it resolves.
"""

import tempfile
from collections import deque
from pathlib import Path
from typing import cast

import tomlkit
from tomlkit.items import Array, Table

from skill_graft import config, files, lock, paths, resolve
from skill_graft.cache import Cache
from skill_graft.config import SkillId
from skill_graft.errors import SkillGraftError, notice, warn
from skill_graft.hull import Hull


def read() -> tomlkit.TOMLDocument:
    """The config as `tomlkit` keeps it: comments and formatting included."""
    # Bytes, as config.load reads them: no newline translation, no locale encoding.
    return tomlkit.parse(paths.config_file().read_bytes().decode())


def write(document: tomlkit.TOMLDocument) -> None:
    """Replaces the config atomically; a symlink's target, not the link."""
    files.atomic_write(paths.config_file().resolve(), tomlkit.dumps(document).encode())


def add(skills: list[str]) -> None:
    """Appends each skill ID to `entries`."""
    document = read()
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
    hull = _finish(document)
    # The hull before the edit: what the other entries reach.
    parents = _reach(hull, [e for e in hull.entries if str(e) not in added])
    for skill in hull.entries:
        if str(skill) in added and skill in parents:
            notice(f"`{skill}` was already in the hull, via `{parents[skill]}`")


def remove(skills: list[str]) -> None:
    """Deletes each skill ID from `entries`."""
    document = read()
    array = cast(Array, document.get("entries", tomlkit.array()))
    for text in dict.fromkeys(skills):
        if text not in array:
            raise SkillGraftError(f"`{text}` is no entry")
        array.remove(text)
    hull = _finish(document)
    parents = _reach(hull, hull.entries)  # the remaining entries
    for skill, parent in parents.items():
        if str(skill) in skills:
            notice(f"`{skill}` stays in the hull, via `{parent}`")


def rename(text: str, name: str) -> None:
    """Sets the skill's `[rename]` value to `name`."""
    document = read()
    loaded = config.parse(tomlkit.dumps(document), paths.config_file())
    skill = resolve.known(loaded, "rename", text)
    if not config.NAME.fullmatch(name):
        raise SkillGraftError(
            f"rename: {name!r} is not a skill name: {config.NAME.pattern}"
        )
    if config.deployed(loaded, skill) == name:
        notice(f"`{skill}` already deploys as `{name}`")
        return
    if "rename" not in document:
        document.add("rename", tomlkit.table())
    table = cast(Table, document["rename"])
    if name == skill.name:  # its own name: the rename is undone
        del table[text]
    else:
        table[text] = name
    _finish(document)


def _reach(hull: Hull, seeds: list[SkillId]) -> dict[SkillId, SkillId]:
    """What `seeds` reach over slash and Skill tool edges: each skill's parent.

    A skill's edges do not depend on the entries, so the edited hull answers for
    any subset of them. Breadth-first, so a parent is reached before its child.
    """
    parents: dict[SkillId, SkillId] = {}
    seen = set(seeds)
    queue = deque(seeds)
    while queue:
        current = queue.popleft()
        for edge in hull.edges:
            if (
                edge.source == current
                and edge.kind != "prose"
                and edge.target not in seen
            ):
                seen.add(edge.target)
                parents[edge.target] = current
                queue.append(edge.target)
    return parents


def _finish(document: tomlkit.TOMLDocument) -> Hull:
    """Resolves the edited config; only if it resolves, writes it and the lock."""
    text = tomlkit.dumps(document)
    # Relative paths start where `load` starts them, even for a symlinked file.
    loaded = config.parse(text, paths.config_file())
    warn(loaded.warnings)
    with tempfile.TemporaryDirectory(prefix="skill-graft-") as work:
        folders = resolve.folders(loaded, Cache(paths.cache()), {})
        hull = resolve.resolve(loaded, folders, Path(work))
        lock_text = lock.render(loaded, {}, hull)  # hashes the patched copies
    write(document)
    lock.write(lock_text)
    print(lock.tree(hull) + lock.suggestions(hull), end="")
    warn(hull.warnings)
    return hull
