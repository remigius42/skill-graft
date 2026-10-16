"""Finds the skills in a source."""

import os
from pathlib import Path


def skill_folders(source: Path) -> list[Path]:
    """Every folder under `source` holding a `SKILL.md`, not looking inside one.

    Follows symlinked folders, visiting each resolved folder once, and skips `.git`.
    """
    found = []
    visited = {source.resolve()}
    for dirpath, dirnames, filenames in os.walk(source, followlinks=True):
        if "SKILL.md" in filenames:
            found.append(Path(dirpath))
            dirnames.clear()
            continue
        keep = []
        for name in sorted(dirnames):
            real = (Path(dirpath) / name).resolve()
            if name != ".git" and real not in visited:
                visited.add(real)
                keep.append(name)
        dirnames[:] = keep
    return found
