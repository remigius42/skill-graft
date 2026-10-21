"""Resolves the hull from the config: the step `build`, `resolve` and `update` share."""

import os
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

from skill_graft import discovery, hull, patch, paths, rename
from skill_graft.cache import Cache
from skill_graft.config import Config, GitSource, SkillId, deployed, parse_skill_id
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
            if source.subdirectory:
                result[alias] = _subdirectory(
                    alias, result[alias], source.subdirectory, ref
                )
        else:
            result[alias] = source.folder
    return result


def _subdirectory(alias: str, tree: Path, subdirectory: str, ref: str) -> Path:
    """`subdirectory` of `tree`, each part a folder of exactly that name, no symlink.

    Names are compared, not looked up, so a case-insensitive file system refuses
    a case the tree does not have, as Linux does; no test can show that on Linux.
    """
    folder = tree
    for part in subdirectory.split("/"):
        with os.scandir(folder) as entries:
            entry = next((e for e in entries if e.name == part), None)
        if entry is None or not entry.is_dir(follow_symlinks=False):
            symlink = entry is not None and entry.is_symlink()
            how = "runs through a symlink" if symlink else "is not a folder"
            raise SkillGraftError(
                f"source {alias!r}: subdirectory {subdirectory!r} {how} at {ref}"
            )
        folder /= part
    return folder


def known(config: Config, where: str, text: str) -> SkillId:
    """The skill ID `text`, its source declared and holding that skill."""
    skill = parse_skill_id(where, text, config.sources)
    folder = folders(config, Cache(paths.cache()), {})[skill.alias]
    index = indexes(config, {skill.alias: folder})[skill.alias]
    discovery.find(index, skill, f"{where}: `{skill}`")
    return skill


def indexes(config: Config, folders: dict[str, Path]) -> dict[str, discovery.Index]:
    """Every source's skills by name, a git source's confined to its checkout."""
    return {
        alias: discovery.index(folder, isinstance(config.sources[alias], GitSource))
        for alias, folder in folders.items()
    }


def roots(config: Config, folders: dict[str, Path]) -> dict[str, Path]:
    """Every source's root: its folder, or the tree holding a git source's
    subdirectory, one level up per part."""
    result = {}
    for alias, folder in folders.items():
        source = config.sources[alias]
        if isinstance(source, GitSource) and source.subdirectory:
            folder = folder.parents[source.subdirectory.count("/")]
        result[alias] = folder
    return result


def resolve(config: Config, folders: dict[str, Path], work: Path) -> Hull:
    """The hull, its skills found and checked for stray symlinks and name clashes.

    Clashing entries are reported before anything is searched. Patched copies
    go under `work`, which must outlive the hull.
    """
    rename.check_unique(
        config, {entry: deployed(config, entry) for entry in config.entries}
    )
    result = hull.walk(config, indexes(config, folders), roots(config, folders), work)
    rename.check_unique(config, result.deployed)
    warnings = rename.unused(config, result.skills)
    warnings += patch.unused(config, result.skills)
    warnings += rename.check_reserved(config, result.deployed)
    return replace(result, warnings=result.warnings + warnings)
