"""Edits skill-graft.toml in place: `add`, `remove`, `rename`, `bind` and `unbind`.

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


def read() -> tuple[tomlkit.TOMLDocument, config.Config, str]:
    """The config as `tomlkit` keeps it, comments and formatting included; as
    `load` reads it; and its text, to restore.

    Checked as `load` checks it first, so an edit only ever sees a valid config.
    """
    text = config.text()
    loaded = config.parse(text, paths.config_file())  # before tomlkit sees it
    return tomlkit.parse(text), loaded, text


def write(document: tomlkit.TOMLDocument) -> None:
    """Replaces the config atomically; a symlink's target, not the link."""
    files.atomic_write(paths.config_file().resolve(), tomlkit.dumps(document).encode())


def add(skills: list[str]) -> None:
    """Appends each skill ID to `entries`."""
    document, _, before = read()
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
    hull = _finish(document, before)
    # The hull before the edit: what the other entries reach.
    parents = _reach(hull, [e for e in hull.entries if str(e) not in added])
    for skill in hull.entries:
        if str(skill) in added and skill in parents:
            notice(f"`{skill}` was already in the hull, via `{parents[skill]}`")


def remove(skills: list[str]) -> None:
    """Deletes each skill ID from `entries`."""
    document, _, before = read()
    array = cast(Array, document.get("entries", tomlkit.array()))
    for text in dict.fromkeys(skills):
        if text not in array:
            raise SkillGraftError(f"`{text}` is no entry")
        array.remove(text)
    hull = _finish(document, before)
    parents = _reach(hull, hull.entries)  # the remaining entries
    for skill, parent in parents.items():
        if str(skill) in skills:
            notice(f"`{skill}` stays in the hull, via `{parent}`")


def rename(text: str, name: str) -> None:
    """Sets the skill's `[rename]` value to `name`."""
    document, loaded, before = read()
    if not config.NAME.fullmatch(name):  # before looking anything up
        raise SkillGraftError(
            f"rename: {name!r} is not a skill name: {config.NAME.pattern}"
        )
    skill = resolve.known(loaded, "rename", text)
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
    _finish(document, before)


def bind(key: str, target: str) -> None:
    """Sets `[bind]` key `key` to the skill ID `target`, or to `false`."""
    document, loaded, before = read()
    skill = config.parse_skill_id("bind", key, loaded.sources)
    # Resolving checks the target; a no-op skips that, so it is checked here first:
    # one gone upstream is no longer bound. Present too: a missing key reads as None.
    if skill in loaded.binds:
        bound = None if target == "false" else resolve.known(loaded, "bind", target)
        if loaded.binds[skill] == bound:
            notice(f"`{key}` is already bound to `{target}`")
            return
    if "bind" not in document:
        document.add("bind", tomlkit.table())
    cast(Table, document["bind"])[key] = False if target == "false" else target
    _finish(document, before)


def unbind(key: str) -> None:
    """Deletes `[bind]` key `key`, leaving the table."""
    document, loaded, before = read()
    # Parsed first, so a malformed key or undeclared alias is said so, as by `bind`.
    if config.parse_skill_id("unbind", key, loaded.sources) not in loaded.binds:
        raise SkillGraftError(f"`{key}` is not bound")
    del cast(Table, document["bind"])[key]
    _finish(document, before)


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


def _finish(document: tomlkit.TOMLDocument, before: str) -> Hull:
    """Resolves the edited config; only if it resolves, writes it and the lock.

    `before` is the text the edit started from, restored if the lock fails.
    """
    text = tomlkit.dumps(document)
    # Relative paths start where `load` starts them, even for a symlinked file.
    loaded = config.parse(text, paths.config_file())
    warn(loaded.warnings)
    with tempfile.TemporaryDirectory(prefix="skill-graft-") as work:
        folders = resolve.folders(loaded, Cache(paths.cache()), {})
        hull = resolve.resolve(loaded, folders, Path(work))
        lock_text = lock.render(loaded, {}, hull)  # hashes the patched copies
    write(document)
    try:
        lock.write(lock_text)
    except OSError:  # leave neither file changed
        files.atomic_write(paths.config_file().resolve(), before.encode())
        raise
    print(lock.tree(hull) + lock.suggestions(hull), end="")
    warn(hull.warnings)
    return hull
