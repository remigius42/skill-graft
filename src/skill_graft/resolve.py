"""Resolves the entries to skill folders: the step `build` and `update` share."""

import os
from collections.abc import Iterable
from pathlib import Path

from skill_graft import discovery
from skill_graft.cache import Cache
from skill_graft.config import Config, GitSource, SkillId
from skill_graft.errors import SkillGraftError


def check_refs(config: Config, given: Iterable[str]) -> None:
    """Every git source needs a ref, its own or a `given` one, used or not."""
    given = set(given)
    for alias, source in config.sources.items():
        if isinstance(source, GitSource) and not (alias in given or source.ref):
            raise SkillGraftError(
                f"source {alias!r} has no ref: run `skill-graft update {alias}`"
            )


def folders(config: Config, cache: Cache, refs: dict[str, str]) -> dict[str, Path]:
    """The folder of each source an entry uses: git ones at `refs`, else their ref."""
    check_refs(config, refs.keys())
    result = {}
    for alias in dict.fromkeys(entry.alias for entry in config.entries):
        source = config.sources[alias]
        if isinstance(source, GitSource):
            ref = refs.get(alias) or source.ref
            assert ref is not None  # check_refs
            result[alias] = cache.checkout(alias, source.url, ref)
        else:
            result[alias] = source.folder
    return result


def resolve(config: Config, folders: dict[str, Path]) -> dict[SkillId, Path]:
    """Each entry's skill folder, checked for clashes and stray symlinks."""
    _check_deployed_names(config.entries)
    indexes = {
        alias: discovery.index(folder, isinstance(config.sources[alias], GitSource))
        for alias, folder in folders.items()
    }
    resolved = {
        entry: discovery.find(indexes[entry.alias], entry) for entry in config.entries
    }
    for folder in resolved.values():
        _check_symlinks(folder)
    return resolved


def _check_symlinks(folder: Path) -> None:
    """A skill is its whole folder: a symlink may only lead to a file inside it.

    A link to a folder, even one inside, is refused: it can form a cycle.
    """
    root = folder.resolve()
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [name for name in dirnames if name != ".git"]  # never copied
        for name in dirnames + filenames:
            link = Path(dirpath) / name
            if not link.is_symlink():
                continue
            target = Path(os.path.realpath(link))
            if not target.is_relative_to(root):
                raise SkillGraftError(f"{link} points outside the skill, to {target}")
            if target.is_dir():
                raise SkillGraftError(
                    f"{link} points to a folder; only file links work"
                )


def _check_deployed_names(entries: list[SkillId]) -> None:
    """Without renames, an entry's deployed name is its name.

    Compared ignoring case: on a case-insensitive file system the folders collide.
    """
    by_name: dict[str, list[SkillId]] = {}
    for entry in entries:
        by_name.setdefault(entry.name.casefold(), []).append(entry)
    for clashing in by_name.values():
        if len(clashing) > 1:
            names = " / ".join(sorted({repr(entry.name) for entry in clashing}))
            ids = ", ".join(str(entry) for entry in clashing)
            raise SkillGraftError(
                f"deployed name {names} is taken by several entries: {ids}"
            )
