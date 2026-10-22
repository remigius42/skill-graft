"""Resolves the hull from the config: the step `build`, `resolve` and `update` share."""

import os
import tempfile
from collections.abc import Generator, Iterable
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

from skill_graft.infra import paths
from skill_graft.infra.cache import Cache
from skill_graft.infra.errors import SkillGraftError
from skill_graft.pipeline import discovery, hull, patch, rename
from skill_graft.pipeline.config import (
    Config,
    GitSource,
    SkillId,
    deployed,
    parse_skill_id,
)
from skill_graft.pipeline.hull import Hull


def check_refs(config: Config, given: Iterable[str]) -> None:
    """Every git source needs a ref, its own or a `given` one, used or not."""
    given = set(given)
    for alias, source in config.sources.items():
        if isinstance(source, GitSource) and not (alias in given or source.ref):
            raise SkillGraftError(
                f"source {alias!r} has no ref: run `skill-graft update {alias}`"
            )


def _folders(config: Config, cache: Cache, refs: dict[str, str]) -> dict[str, Path]:
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
        if entry is None:
            how = "does not exist"
        elif entry.is_symlink():
            how = "runs through a symlink"
        elif not entry.is_dir(follow_symlinks=False):
            how = "is not a folder"
        else:
            folder /= part
            continue
        raise SkillGraftError(
            f"source {alias!r}: subdirectory {subdirectory!r} {how} at {ref}"
        )
    return folder


def known(config: Config, where: str, text: str) -> SkillId:
    """The skill ID `text`, its source declared and holding that skill."""
    skill = parse_skill_id(where, text, config.sources)
    folder = _folders(config, Cache(paths.cache()), {})[skill.alias]
    index = _indexes(config, {skill.alias: folder})[skill.alias]
    discovery.find(index, skill, f"{where}: `{skill}`")
    return skill


def _indexes(config: Config, folders: dict[str, Path]) -> dict[str, discovery.Index]:
    """Every source's skills by name, a git source's confined to its checkout."""
    return {
        alias: discovery.index(folder, isinstance(config.sources[alias], GitSource))
        for alias, folder in folders.items()
    }


def _roots(config: Config, folders: dict[str, Path]) -> dict[str, Path]:
    """Every source's root: its folder, or the tree holding a git source's
    subdirectory, one level up per part."""
    result = {}
    for alias, folder in folders.items():
        source = config.sources[alias]
        if isinstance(source, GitSource) and source.subdirectory:
            folder = folder.parents[source.subdirectory.count("/")]
        result[alias] = folder
    return result


@contextmanager
def compute_hull(
    config: Config, cache: Cache | None = None, refs: dict[str, str] | None = None
) -> Generator[Hull]:
    """The hull, its skills found and checked for stray symlinks and name clashes.

    Reads every source, git ones at `refs`, else their ref, through `cache`, by
    default the user's. Clashing entries are reported before anything is searched.
    Patched copies go in a temporary folder removed on exit: a patched skill's
    path in `skills` is valid only inside the `with`.
    """
    with tempfile.TemporaryDirectory(prefix="skill-graft-") as work:
        cache = Cache(paths.cache()) if cache is None else cache
        folders = _folders(config, cache, refs or {})
        rename.check_unique(
            config, {entry: deployed(config, entry) for entry in config.entries}
        )
        result = hull.walk(
            config, _indexes(config, folders), _roots(config, folders), Path(work)
        )
        rename.check_unique(config, result.deployed)
        warnings = rename.unused(config, result.skills)
        warnings += patch.unused(config, result.skills)
        warnings += rename.check_reserved(config, result.deployed)
        yield replace(result, warnings=result.warnings + warnings)
