"""Edits skill-graft.toml in place: `add`, `remove` and `rename`.

Each edit resolves the edited text first and writes nothing unless it resolves.
"""

import tempfile
from pathlib import Path
from typing import cast

import tomlkit
from tomlkit.items import Array

from skill_graft import config, files, lock, paths, resolve
from skill_graft.cache import Cache
from skill_graft.errors import warn


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
    array = cast(Array, document["entries"])
    for text in skills:
        array.append(text)
    _finish(document)


def _finish(document: tomlkit.TOMLDocument) -> None:
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
