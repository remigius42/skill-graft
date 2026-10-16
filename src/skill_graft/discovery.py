"""Finds the skills in a source."""

import os
import re
from pathlib import Path

from skill_graft.errors import SkillGraftError

# A comment: `#` after whitespace, to the end of the line.
COMMENT = re.compile(r"\s+#.*$")


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


def read_name(folder: Path) -> str:
    """The `name:` of the front matter opening `SKILL.md`, else the folder name.

    Reads only plain and quoted one-line values; anything else is an error, never
    a silent fallback to the folder name.
    """
    skill_md = folder / "SKILL.md"
    lines = skill_md.read_text(encoding="utf-8-sig").splitlines()
    fences = [i for i, line in enumerate(lines) if line.rstrip() == "---"][:2]
    if fences[:1] != [0] or len(fences) < 2:
        return folder.name
    for line in lines[1 : fences[1]]:
        if line.startswith("name:"):
            value = COMMENT.sub("", line.removeprefix("name:")).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                return value[1:-1]
            if not value or value[0] in ">|&*[{":
                raise SkillGraftError(f"{skill_md}: unsupported form of `name:`")
            return value
    return folder.name
