"""Writes the entries into the package's `.apm/skills/`."""

import os
import shutil
from pathlib import Path

from skill_graft import discovery, paths
from skill_graft.config import Config, SkillId
from skill_graft.errors import SkillGraftError


def vendor(config: Config) -> None:
    """Replaces `.apm/skills/` with one copy per entry, swapped in when complete.

    Every entry is resolved and checked first, so a failure writes nothing beyond
    undoing a run killed mid-swap.
    """
    skills = paths.skills()
    new = skills.with_name("skills.new")
    old = skills.with_name("skills.old")
    _recover(skills, new, old)
    _check_deployed_names(config.entries)
    indexes = {
        alias: discovery.index(config.sources[alias])
        for alias in {entry.alias for entry in config.entries}
    }
    folders = {
        entry: discovery.find(indexes[entry.alias], entry) for entry in config.entries
    }
    for folder in folders.values():
        _check_symlinks(folder)
    new.mkdir(parents=True)
    for entry, folder in folders.items():
        try:
            shutil.copytree(
                folder, new / entry.name, ignore=shutil.ignore_patterns(".git")
            )
        except OSError as error:
            # The copy error is the one to report; the next run clears what is left.
            shutil.rmtree(new, ignore_errors=True)
            raise SkillGraftError(f"copying {folder} failed: {error}") from None
    if skills.exists():
        skills.rename(old)
    new.rename(skills)
    if old.exists():
        shutil.rmtree(old)


def _check_symlinks(folder: Path) -> None:
    """A skill is its whole folder: a symlink may not lead out of it, or back up."""
    root = folder.resolve()
    for dirpath, dirnames, filenames in os.walk(folder):
        for name in dirnames + filenames:
            link = Path(dirpath) / name
            if not link.is_symlink():
                continue
            target = link.resolve()
            if not target.is_relative_to(root):
                raise SkillGraftError(f"{link} points outside the skill, to {target}")
            if link.parent.resolve().is_relative_to(target):
                raise SkillGraftError(f"{link} points back up the skill, to {target}")


def _recover(skills: Path, new: Path, old: Path) -> None:
    """Undoes a run killed mid-swap: `skills.old/` is then the previous build."""
    if old.exists() and not skills.exists():
        old.rename(skills)
    for stale in (new, old):
        if stale.exists():
            shutil.rmtree(stale)


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
