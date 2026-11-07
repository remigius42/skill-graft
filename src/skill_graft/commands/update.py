"""Moves each git source's ref to the tip of its branch."""

import re
import shlex
import tomllib
from collections.abc import Generator, MutableMapping
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, cast

import tomlkit

from skill_graft.commands import edit, explain, review, transaction
from skill_graft.infra import files, git, paths
from skill_graft.infra.cache import Cache
from skill_graft.infra.errors import SkillGraftError, lines_of
from skill_graft.pipeline import (
    compute,
    config,
    deployed,
    lock,
    rename,
)
from skill_graft.pipeline.config import Config, GitSource, SkillId
from skill_graft.pipeline.hull import PatchError

# Its header: what `update --diff-file` compares.
HEADER = review.header("at the current refs against the new ones")


def update(
    scope: paths.Scope,
    warnings: list[str],
    aliases: list[str],
    dry_run: bool,
    diff_file: Path | None = None,
    expect: str | None = None,
) -> None:
    """Moves the selected git sources to their tips, if every entry resolves there.

    Prints one line per source first, so a resolution error still shows the shas
    it would have written. A dry run writes only to a temporary folder, reading
    the real cache, and `diff_file`. Writes `diff_file`'s Deployed diff, if given;
    refuses a hull whose digest is not `expect`, if given.
    """
    loaded = transaction.load(scope, warnings)
    if expect is not None and not re.fullmatch("[0-9a-f]{64}", expect):
        raise SkillGraftError(
            f"--expect {expect}: expected 64 hex digits, as an `apply:` line gives"
        )
    target = None if diff_file is None else review.check_target(diff_file)
    if target is not None:
        review.clear(target)
    # The flags to run again with: `--expect`'s digest changes with the sources.
    flags = " --dry-run" if dry_run or expect is not None else ""
    if diff_file is not None:
        flags += f" --diff-file {shlex.quote(str(diff_file))}"
    with ExitStack() as stack:
        if dry_run:
            # Registered first, so it runs last, even on a failure.
            stack.callback(
                print, "dry run: skill-graft.toml and skill-graft.lock not written"
            )
        git_cache = review.dry_cache(stack) if dry_run else Cache.default()
        try:
            _update(
                scope,
                warnings,
                loaded,
                aliases,
                git_cache,
                not dry_run,
                target,
                expect,
                flags,
            )
        except PatchError as error:
            if not dry_run:
                raise
            raise review.fetch_hint(
                error,
                git_cache.root,
                "run `update` without `--dry-run` to fetch the tip",
            ) from None


def _update(
    scope: paths.Scope,
    warnings: list[str],
    loaded: Config,
    aliases: list[str],
    git_cache: Cache,
    write: bool,
    target: Path | None,
    expect: str | None,
    flags: str,
) -> None:
    selected = _select(loaded, aliases)
    compute.check_refs(loaded, selected, flags)
    for alias, source in selected.items():
        if source.branch is not None:
            _check_branch(alias, source.branch)
    compute.check_entries(loaded)  # before any remote: compute_hull would be too late
    transaction.check_copies(scope.skills, lock.load(scope.lock_file))  # so is this
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
    # The lock even if no ref moved: a path source may have changed.
    with transaction.resolving(
        scope, loaded, warnings, git_cache, tips, write=write
    ) as resolution:
        hull = resolution.hull
        hashes = resolution.hashes = lock.skill_hashes(hull)
        locked = lock.load(scope.lock_file)  # once: both checks read the same lock
        with _previous(scope, loaded, selected, git_cache) as previous:
            shown = review.print_diff(previous, hull, hashes)
            edited = []
            if not isinstance(previous, str):  # else every skill is shown in full
                edited = _print_edited(previous.hashes, lock.recorded(locked))
            given = "".join(f"{shlex.quote(alias)} " for alias in aliases)
            rerun = f"skill-graft update {given}--dry-run --diff-file <file>"
            digest = lock.digest(hull, hashes)
            if expect is not None and digest != expect:
                raise SkillGraftError(
                    f"the hull is not the one reviewed: its hull digest is {digest}, "
                    f"not {expect}; review it again: {rerun}"
                )
            # The file and its text, built before any write.
            written = (
                None
                if target is None
                else (
                    target,
                    review.deployed_diff(
                        HEADER, loaded, tips, previous, hull, hashes, shown, edited
                    ).encode(),
                )
            )
        moved = {
            alias: tip for alias, tip in tips.items() if tip != selected[alias].ref
        }
        if write and written is not None:  # first: no diff of what was not written
            resolution.writes.append((written[0], lambda: files.atomic_write(*written)))
        if write and moved:
            resolution.writes.append(
                (scope.config_file.resolve(), lambda: _write_refs(scope, moved))
            )
    # Once the writes succeeded; with no ref moved, `resolve` sees these tips.
    explain.announce_suggestions(hull, dry_run=not write and bool(moved))
    if write:
        return
    if written is not None:
        files.atomic_write(*written)
    if target is None and (shown or isinstance(previous, str)):
        print(f"review: {rerun}")
    elif not edited:  # all the text of what it would deploy was shown
        # Parsed, not text: an editor may have reformatted the lock. Where a path
        # source is recorded is no difference, as for `deploy`.
        if not moved and locked is not None and _same_hull(loaded, resolution, locked):
            print("nothing to apply")
        else:
            print(f"apply: skill-graft update {given}--expect {digest}")


def _same_hull(
    loaded: Config, resolution: transaction.Resolution, locked: dict[str, Any]
) -> bool:
    """Whether the lock `resolution` would write records what `locked` does,
    wherever each path source is recorded."""
    aliases = config.path_aliases(loaded)
    new = tomllib.loads(resolution.lock_text)
    return lock.without_paths(new, aliases) == lock.without_paths(locked, aliases)


@contextmanager
def _previous(
    scope: paths.Scope, loaded: Config, selected: dict[str, GitSource], git_cache: Cache
) -> Generator[review.Before | str]:
    """The hull at the current refs as a Hull diff's old side, open; or why there
    is none.

    Never fetches a commit; fetches the files of a cached one, as any command
    reading that ref would: a lock written on another machine still gets its
    diff. A failure there is a reason, as for refs that do not resolve. Yields
    outside its `try`, so an error in the caller's `with` is never taken for one.
    """
    reason = _uncached(selected, git_cache)
    opened = ExitStack()
    if reason is None:
        try:
            with ExitStack() as stack:  # closed on any error, Ctrl-C too
                hull = stack.enter_context(
                    compute.compute_hull(scope, loaded, git_cache)
                )
                hashes = lock.skill_hashes(hull)
                opened = stack.pop_all()  # kept open for the caller's `with`
        except PatchError as error:  # patches likely rewritten for the tips
            failed = " and ".join(
                what
                for what, found in [
                    ("patches fail", error.failures),
                    ("hidden characters", error.hidden),
                ]
                if found
            )
            if error.other:  # an error that is no patch's: that one matters
                other = "; ".join(error.other)
                reason = f"the current refs do not resolve: {failed} there; {other}"
            else:
                reason = f"{failed} at the current refs"
        except (SkillGraftError, OSError) as error:  # the update itself is still fine
            shown = "; ".join(lines_of(error))
            reason = f"the current refs do not resolve: {shown}"
    if reason is not None:
        yield reason
        return
    with opened:
        rewrites = rename.rewrites(hull)
        yield review.Before(
            hashes,
            lambda skill: deployed.deployed_files(
                hull.skills[skill], rewrites.get(skill, {})
            ),
            lambda skill: (
                hull.upstream[skill].relative_to(hull.roots[skill.alias]).as_posix()
            ),
            {
                alias: source.ref
                for alias, source in loaded.sources.items()
                if isinstance(source, GitSource)
            },
        )


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


def _write_refs(scope: paths.Scope, refs: dict[str, str]) -> None:
    """Sets each `sources.<alias>.ref`, keeping every comment and all formatting.

    Replaces the file a symlinked `skill-graft.toml` points to, not the link.
    """
    # Not edit.read: the config was checked when update loaded it.
    document = tomlkit.parse(config.text(scope))
    # A table, inline table, or proxy over split tables, by how the user wrote
    # it; config.load already checked that each is a table.
    sources = cast(MutableMapping[str, Any], document["sources"])
    for alias, ref in refs.items():
        cast(MutableMapping[str, Any], sources[alias])["ref"] = ref
    edit.write(scope, document)


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
        # A default branch needs both lines: `ref: refs/heads/<b>` and its sha. A
        # detached HEAD has only the sha, of a commit perhaps on no branch.
        branch, sha = False, None
        for value, name in _ls_remote(context, ["--symref"], source.url, ["HEAD"]):
            if name == "HEAD" and value.startswith("ref: refs/heads/"):
                branch = True
            elif name == "HEAD":
                sha = value
        if branch and sha:
            return sha
        if not _ls_remote(context, ["--heads"], source.url, []):
            raise SkillGraftError(f"{context}: the remote has no commits yet")
        raise SkillGraftError(
            f"{context}: the remote names no default branch; "
            'set `branch = "…"` in its [sources] table'
        )
    ref = f"refs/heads/{source.branch}"
    for sha, name in _ls_remote(context, [], source.url, [ref]):
        if name == ref:
            return sha
    raise SkillGraftError(f"{context}: no branch {source.branch!r}")


def _ls_remote(
    context: str, options: list[str], url: str, patterns: list[str]
) -> list[tuple[str, str]]:
    """Each line `git ls-remote` prints for `url`, as its value and its ref."""
    arguments = ["ls-remote", *options, "--", url, *patterns]
    found = []
    for line in git.run(*arguments, context=context).decode().splitlines():
        value, _, name = line.partition("\t")
        found.append((value, name))
    return found
