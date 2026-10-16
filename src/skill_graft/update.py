"""Moves each git source's ref to the tip of its branch."""

from skill_graft import config, git, paths, resolve
from skill_graft.cache import Cache
from skill_graft.config import Config, GitSource
from skill_graft.errors import SkillGraftError


def update(aliases: list[str]) -> list[str]:
    """Fetches the selected git sources; returns one line per source."""
    loaded = config.load()
    selected = _select(loaded, aliases)
    resolve.check_refs(loaded, selected)
    for alias, source in selected.items():
        if source.branch is not None:
            _check_branch(alias, source.branch)
    git_cache = Cache(paths.cache())
    tips: dict[tuple[str, str | None], str] = {}
    lines = []
    for alias, source in selected.items():
        place = (source.url, source.branch)
        if place not in tips:
            tips[place] = _tip(alias, source)
        tip = tips[place]
        if not git_cache.has_commit(source.url, tip):
            git_cache.fetch(alias, source.url)
        lines.append(f"{alias} {tip}" + (" (unchanged)" if tip == source.ref else ""))
    return lines


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
        for line in output.decode().splitlines():
            sha, _, name = line.partition("\t")
            if name == "HEAD" and not sha.startswith("ref:"):
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
