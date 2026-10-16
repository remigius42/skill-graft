"""Moves each git source's ref to the tip of its branch."""

import os
import shutil
import tempfile
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, cast

import tomlkit

from skill_graft import config, git, paths, resolve
from skill_graft.cache import Cache
from skill_graft.config import Config, GitSource
from skill_graft.errors import SkillGraftError


def update(aliases: list[str], dry_run: bool = False) -> None:
    """Moves the selected git sources to their tips, if every entry resolves there.

    Prints one line per source first, so a resolution error still shows the shas
    it would have written. A dry run writes only to a temporary folder, reading
    the real cache.
    """
    if not dry_run:
        _update(aliases, Cache(paths.cache()), write=True)
        return
    try:
        with tempfile.TemporaryDirectory(prefix="skill-graft-") as tmp:
            _update(aliases, Cache(Path(tmp), Cache(paths.cache())), write=False)
    finally:
        print("dry run: skill-graft.toml not written")


def _update(aliases: list[str], git_cache: Cache, write: bool) -> None:
    loaded = config.load()
    selected = _select(loaded, aliases)
    resolve.check_refs(loaded, selected)
    for alias, source in selected.items():
        if source.branch is not None:
            _check_branch(alias, source.branch)
    places: dict[tuple[str, str | None], str] = {}
    tips = {}
    for alias, source in selected.items():
        place = (source.url, source.branch)
        if place not in places:
            places[place] = _tip(alias, source)
        tips[alias] = places[place]
        if not git_cache.has_commit(source.url, tips[alias]):
            git_cache.fetch(alias, source.url)
        unchanged = " (unchanged)" if tips[alias] == source.ref else ""
        print(f"{alias} {tips[alias]}{unchanged}")
    resolve.resolve(loaded, resolve.folders(loaded, git_cache, tips))
    moved = {alias: tip for alias, tip in tips.items() if tip != selected[alias].ref}
    if moved and write:
        _write_refs(moved)


def _write_refs(refs: dict[str, str]) -> None:
    """Sets each `sources.<alias>.ref`, keeping every comment and all formatting.

    Replaces the file a symlinked `skill-graft.toml` points to, not the link.
    """
    file = paths.config_file().resolve()
    # Bytes, as config.load reads them: no newline translation, no locale encoding.
    document = tomlkit.parse(file.read_bytes().decode())
    # A table, inline table, or proxy over split tables, by how the user wrote
    # it; config.load already checked that each is a table.
    sources = cast(MutableMapping[str, Any], document["sources"])
    for alias, ref in refs.items():
        cast(MutableMapping[str, Any], sources[alias])["ref"] = ref
    with tempfile.NamedTemporaryFile(
        "wb", dir=file.parent, prefix=f".{file.name}.", delete=False
    ) as tmp:
        tmp.write(tomlkit.dumps(document).encode())
    shutil.copymode(file, tmp.name)
    os.replace(tmp.name, file)


def _select(loaded: Config, aliases: list[str]) -> dict[str, GitSource]:
    """The named git sources, or all of them; naming a path source is an error."""
    for alias in aliases:
        if alias not in loaded.sources:
            raise SkillGraftError(f"no source {alias!r} is declared")
        if not isinstance(loaded.sources[alias], GitSource):
            raise SkillGraftError(
                f"{alias!r} is a path source; update only moves git sources"
            )
    return {
        alias: source
        for alias, source in loaded.sources.items()
        if isinstance(source, GitSource) and (not aliases or alias in aliases)
    }


def _check_branch(alias: str, branch: str) -> None:
    """Refuses revision syntax (`main~3`, `main@{1}`), which names another commit.

    Checks `refs/heads/<branch>` rather than `--branch <branch>`, which would
    expand `@{-1}` in whatever repository the user runs skill-graft from.
    """
    try:
        git.run("check-ref-format", f"refs/heads/{branch}", context=alias)
    except SkillGraftError:
        raise SkillGraftError(
            f"'sources.{alias}.branch' = {branch!r} is not a valid branch name"
        ) from None


def _tip(alias: str, source: GitSource) -> str:
    """The sha of the source's branch tip, as the remote reports it now."""
    context = f"source {alias!r} ({source.url})"
    if source.branch is None:
        output = git.run(
            "ls-remote", "--symref", "--", source.url, "HEAD", context=context
        )
        # A default branch needs both lines: `ref: refs/heads/<b>` and its sha. A
        # detached HEAD has only the sha, of a commit perhaps on no branch.
        branch, sha = False, None
        for line in output.decode().splitlines():
            value, _, name = line.partition("\t")
            if name == "HEAD" and value.startswith("ref: refs/heads/"):
                branch = True
            elif name == "HEAD":
                sha = value
        if branch and sha:
            return sha
        raise SkillGraftError(
            f"{context}: the remote names no default branch; "
            'set `branch = "…"` in its [sources] table'
        )
    ref = f"refs/heads/{source.branch}"
    output = git.run("ls-remote", "--", source.url, ref, context=context)
    for line in output.decode().splitlines():
        sha, _, name = line.partition("\t")
        if name == ref:
            return sha
    raise SkillGraftError(f"{context}: no branch {source.branch!r}")
