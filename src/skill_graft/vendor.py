"""Writes the entries into the package's `.apm/skills/`."""

import shutil

from skill_graft import discovery, paths
from skill_graft.config import Config, SkillId
from skill_graft.errors import SkillGraftError


def vendor(config: Config) -> None:
    """Replaces `.apm/skills/` with one copy per entry, swapped in when complete.

    Every entry is resolved and checked first, so a failure writes nothing.
    """
    folders = {
        entry: discovery.find(config.sources[entry.alias], entry)
        for entry in config.entries
    }
    _check_deployed_names(config.entries)
    skills = paths.skills()
    new = skills.with_name("skills.new")
    old = skills.with_name("skills.old")
    for stale in (new, old):
        shutil.rmtree(stale, ignore_errors=True)
    new.mkdir(parents=True)
    for entry, folder in folders.items():
        try:
            shutil.copytree(
                folder, new / entry.name, ignore=shutil.ignore_patterns(".git")
            )
        except OSError as error:
            shutil.rmtree(new)
            raise SkillGraftError(f"copying {folder} failed: {error}") from None
    if skills.exists():
        skills.rename(old)
    new.rename(skills)
    shutil.rmtree(old, ignore_errors=True)


def _check_deployed_names(entries: list[SkillId]) -> None:
    """Without renames, an entry's deployed name is its name."""
    by_name: dict[str, list[str]] = {}
    for entry in entries:
        by_name.setdefault(entry.name, []).append(str(entry))
    for name, ids in by_name.items():
        if len(ids) > 1:
            raise SkillGraftError(
                f"deployed name {name!r} is taken by several entries: {', '.join(ids)}"
            )
