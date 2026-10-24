"""Moves each git source's ref to the tip of its branch."""

import shlex
import tempfile
from collections.abc import Iterator, MutableMapping
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, cast

import tomlkit

from skill_graft.commands import edit, explain
from skill_graft.infra import git, paths
from skill_graft.infra.cache import Cache
from skill_graft.infra.errors import SkillGraftError, warn
from skill_graft.pipeline import compute, config, deployed, lock, patch, rename
from skill_graft.pipeline.config import Config, GitSource, SkillId
from skill_graft.pipeline.hull import Hull


def update(loaded: Config, aliases: list[str], dry_run: bool = False) -> None:
    """Moves the selected git sources to their tips, if every entry resolves there.

    Prints one line per source first, so a resolution error still shows the shas
    it would have written. A dry run writes only to a temporary folder, reading
    the real cache.
    """
    if not dry_run:
        _update(loaded, aliases, Cache(paths.cache()), write=True)
        return
    try:
        with tempfile.TemporaryDirectory(prefix="skill-graft-") as tmp:
            git_cache = Cache(Path(tmp), Cache(paths.cache()))
            try:
                _update(loaded, aliases, git_cache, write=False)
            except patch.PatchError as error:
                raise _fetch_hint(error, Path(tmp)) from None
    finally:
        print("dry run: skill-graft.toml and skill-graft.lock not written")


def _fetch_hint(error: patch.PatchError, tmp: Path) -> patch.PatchError:
    """The error, pointing at no upstream folder that goes away with `tmp`."""
    fetch = "run `update` without `--dry-run` to fetch the tip"
    hints = {
        skill: fetch
        for skill, upstream, _ in error.failures
        if upstream.is_relative_to(tmp)
    }
    # A hidden character in a tip's skill is named by its path in `tmp` too.
    gone = {skill for skill, line in error.hidden if line.startswith(f"{tmp}/")}
    hidden = []
    for i, (skill, line) in enumerate(error.hidden):
        hidden.append((skill, line))
        after = error.hidden[i + 1 : i + 2]
        if skill in gone and (not after or after[0][0] != skill):  # its last line
            hidden.append((skill, fetch))
    return patch.PatchError(error.failures, error.other, hints, hidden)


def _update(loaded: Config, aliases: list[str], git_cache: Cache, write: bool) -> None:
    selected = _select(loaded, aliases)
    compute.check_refs(loaded, selected)
    for alias, source in selected.items():
        if source.branch is not None:
            _check_branch(alias, source.branch)
    compute.check_entries(loaded)  # before any remote: compute_hull would be too late
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
    with compute.compute_hull(loaded, git_cache, tips) as hull:
        hashes = lock.skill_hashes(hull)
        warn(hull.warnings)
        with _previous(loaded, selected, git_cache) as previous:
            marked = _print_diff(previous, hull, hashes)
            if not isinstance(previous, str):
                _print_edited(previous[1], lock.read())
    moved = {alias: tip for alias, tip in tips.items() if tip != selected[alias].ref}
    if write:
        text = lock.render(loaded, tips, hull, hashes)  # may fail: before any write
        if moved:
            _write_refs(moved)
        lock.write(text)  # even if no ref moved: a path source may have changed
    explain.announce_suggestions(hull, dry_run=not write)  # once the writes succeeded
    if not write and marked:
        given = "".join(f"{shlex.quote(alias)} " for alias in aliases)
        print(f"review: skill-graft update {given}--dry-run --diff <file>")


@contextmanager
def _previous(
    loaded: Config, selected: dict[str, GitSource], git_cache: Cache
) -> Iterator[tuple[Hull, dict[SkillId, str]] | str]:
    """The hull at the current refs and each skill's hash, open; or why there is none.

    Never fetches: the diff is not worth a remote call. A cached commit whose tree
    was never exported is exported, as any command reading that ref would. Yields
    outside its `try`, so an error in the caller's `with` is never taken for one.
    """
    reason = _uncached(selected, git_cache)
    stack = ExitStack()
    if reason is None:
        try:
            hull = stack.enter_context(compute.compute_hull(loaded, git_cache))
            hashes = lock.skill_hashes(hull)
        except patch.PatchError as error:  # patches likely rewritten for the tips
            stack.close()
            failed = " and ".join(
                what
                for what, found in [
                    ("patches fail", error.failures),
                    ("hidden characters", error.hidden),
                ]
                if found
            )
            if error.other:  # an error that is no patch's: that one matters
                reason = (
                    f"the current refs do not resolve: {failed} there; {error.other}"
                )
            else:
                reason = f"{failed} at the current refs"
        except (SkillGraftError, OSError) as error:  # the update itself is still fine
            stack.close()
            reason = f"the current refs do not resolve: {error}"
    if reason is not None:
        yield reason
        return
    with stack:
        yield hull, hashes


def _uncached(selected: dict[str, GitSource], git_cache: Cache) -> str | None:
    """Why a selected source's current ref cannot be read without a fetch, if so."""
    for alias, source in selected.items():
        if source.ref is None:
            return f"{alias!r} had no ref"
        if not git_cache.has_commit(source.url, source.ref):
            return (
                f"{alias!r} ref {source.ref} is not in the cache; likely its branch "
                "not fetched since it was pushed, history rewritten upstream, or a "
                "ref set to a commit on no branch, such as a tag's"
            )
    return None


def _print_diff(
    previous: tuple[Hull, dict[SkillId, str]] | str,
    hull: Hull,
    new: dict[SkillId, str],
) -> bool:
    """`+`, `-` or `~` per skill added, removed or changed, by skill ID; under each
    `+` and `~`, its files that differ. Whether it marked a skill `+` or `~`."""
    if isinstance(previous, str):
        print(f"no previous hull to compare ({previous})")
        return False
    old_hull, old = previous
    lines = []
    marked = False
    old_rewrites, new_rewrites = rename.rewrites(old_hull), rename.rewrites(hull)
    for skill in sorted(old.keys() | new.keys()):
        if old.get(skill) == new.get(skill):
            continue
        if skill not in new:
            lines.append(f"- {skill}")
            continue
        marked = True
        lines.append(f"{'+' if skill not in old else '~'} {skill}")
        before = (
            deployed.deployed_files(old_hull.skills[skill], old_rewrites.get(skill, {}))
            if skill in old
            else {}
        )
        after = deployed.deployed_files(hull.skills[skill], new_rewrites.get(skill, {}))
        lines += [f"  {line}" for line in deployed.summary(before, after)]
    print(
        "\n".join(["hull (+ added, - removed, ~ changed):", *lines])
        if lines
        else "hull unchanged"
    )
    return marked


def _print_edited(
    old: dict[SkillId, str], locked: dict[SkillId, str] | None
) -> list[SkillId]:
    """Each skill the old hull and the lock do not hold alike, named: edited since
    the lock was written, by a path source, a patch or the config. Every skill of
    the old hull if there is no lock to read."""
    edited = sorted(
        old
        if locked is None
        else {
            skill
            for skill in old.keys() | locked.keys()
            if old.get(skill) != locked.get(skill)
        }
    )
    for skill in edited:
        print(f"edited since skill-graft.lock was written, not shown: {skill}")
    return edited


def _write_refs(refs: dict[str, str]) -> None:
    """Sets each `sources.<alias>.ref`, keeping every comment and all formatting.

    Replaces the file a symlinked `skill-graft.toml` points to, not the link.
    """
    # Not edit.read: the config was checked when update loaded it.
    document = tomlkit.parse(config.text())
    # A table, inline table, or proxy over split tables, by how the user wrote
    # it; config.load already checked that each is a table.
    sources = cast(MutableMapping[str, Any], document["sources"])
    for alias, ref in refs.items():
        cast(MutableMapping[str, Any], sources[alias])["ref"] = ref
    edit.write(document)


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
        if not git.run("ls-remote", "--heads", "--", source.url, context=context):
            raise SkillGraftError(f"{context}: the remote has no commits yet")
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
