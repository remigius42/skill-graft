"""Resolves the hull from the config: the step `build`, `resolve` and `update` share."""

from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

from skill_graft import discovery, hull
from skill_graft.cache import Cache
from skill_graft.config import Config, GitSource, SkillId
from skill_graft.errors import SkillGraftError
from skill_graft.hull import Hull


def check_refs(config: Config, given: Iterable[str]) -> None:
    """Every git source needs a ref, its own or a `given` one, used or not."""
    given = set(given)
    for alias, source in config.sources.items():
        if isinstance(source, GitSource) and not (alias in given or source.ref):
            raise SkillGraftError(
                f"source {alias!r} has no ref: run `skill-graft update {alias}`"
            )


def folders(config: Config, cache: Cache, refs: dict[str, str]) -> dict[str, Path]:
    """Every declared source's folder: git ones at `refs`, else their ref.

    A reference may resolve in any source, so all are read, used by an entry or not.
    """
    check_refs(config, refs.keys())
    result = {}
    for alias, source in config.sources.items():
        if isinstance(source, GitSource):
            ref = refs.get(alias) or source.ref
            assert ref is not None  # check_refs
            result[alias] = cache.checkout(alias, source.url, ref)
        else:
            result[alias] = source.folder
    return result


def resolve(config: Config, folders: dict[str, Path]) -> Hull:
    """The hull, its skills found and checked for stray symlinks and name clashes.

    Clashing entries are reported before anything is searched.
    """
    _check_deployed_names(config.entries)
    indexes = {
        alias: discovery.index(folder, isinstance(config.sources[alias], GitSource))
        for alias, folder in folders.items()
    }
    result = hull.walk(config, indexes)
    _check_deployed_names(list(result.skills))
    return replace(result, deployed={skill: skill.name for skill in result.skills})


def _check_deployed_names(skills: list[SkillId]) -> None:
    """Without renames, a skill's deployed name is its name.

    Compared ignoring case: on a case-insensitive file system the folders collide.
    """
    by_name: dict[str, list[SkillId]] = {}
    for skill in skills:
        by_name.setdefault(skill.name.casefold(), []).append(skill)
    for clashing in by_name.values():
        if len(clashing) > 1:
            names = " / ".join(sorted({repr(skill.name) for skill in clashing}))
            ids = ", ".join(str(skill) for skill in clashing)
            raise SkillGraftError(
                f"deployed name {names} is taken by several skills: {ids}"
            )
