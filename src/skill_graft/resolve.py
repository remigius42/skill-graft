"""Resolves the hull from the config: the step `build`, `resolve` and `update` share."""

from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

from skill_graft import discovery, hull, rename
from skill_graft.cache import Cache
from skill_graft.config import Config, GitSource, deployed
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
    rename.check_unique(
        config, {entry: deployed(config, entry) for entry in config.entries}
    )
    indexes = {
        alias: discovery.index(folder, isinstance(config.sources[alias], GitSource))
        for alias, folder in folders.items()
    }
    result = hull.walk(config, indexes)
    rename.check_unique(config, result.deployed)
    warnings = rename.unused(config, result.skills)
    warnings += rename.check_reserved(config, result.deployed)
    return replace(result, warnings=result.warnings + warnings)
