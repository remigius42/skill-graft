"""Finds the skills in a source."""

import os
import re
from dataclasses import dataclass
from pathlib import Path

from skill_graft import paths
from skill_graft.config import NAME, SkillId
from skill_graft.errors import SkillGraftError

# A comment: `#` after whitespace, to the end of the line.
COMMENT = re.compile(r"\s+#.*$")


def skill_folders(source: Path) -> list[Path]:
    """Every folder under `source` holding a `SKILL.md`, not looking inside one.

    Follows symlinked folders, visiting each resolved folder once, and skips `.git`
    and the package, so build never reads its own output.
    """
    found = []
    package = paths.package().resolve()
    visited = {source.resolve()}
    for dirpath, dirnames, filenames in os.walk(source, followlinks=True):
        if "SKILL.md" in filenames:
            found.append(Path(dirpath))
            dirnames.clear()
            continue
        keep = []
        for name in sorted(dirnames):
            real = (Path(dirpath) / name).resolve()
            if (
                name != ".git"
                and real not in visited
                and not real.is_relative_to(package)
            ):
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
    try:
        lines = skill_md.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise SkillGraftError(f"{skill_md}: cannot be read: {error}") from None
    fences = [i for i, line in enumerate(lines) if line.rstrip() == "---"][:2]
    if fences[:1] != [0] or len(fences) < 2:
        return folder.name
    front_matter = lines[1 : fences[1]]
    for i, line in enumerate(front_matter):
        if line.startswith("name:"):
            following = front_matter[i + 1 : i + 2]
            continued = bool(following) and following[0][:1].isspace()
            value = _scalar(line.removeprefix("name:"))
            if value is None or continued:
                raise SkillGraftError(f"{skill_md}: unsupported form of `name:`")
            return value
    return folder.name


def _scalar(raw: str) -> str | None:
    """A one-line plain or quoted YAML value without its comment, else None."""
    raw = raw.strip()
    if raw[:1] in ("'", '"'):
        end = raw.find(raw[0], 1)
        if end < 0:
            return None
        rest = raw[end + 1 :]
        if rest.strip() and not COMMENT.match(rest):
            return None
        return raw[1:end]
    value = COMMENT.sub("", raw).strip()
    return value if value and value[0] not in ">|&*[{" else None


@dataclass(frozen=True)
class Index:
    """A source's skills by name, walked once.

    A skill whose name cannot be read, or is not one path segment, is filed under
    its folder name as a problem: an error when an entry names it, else ignored.
    """

    folders: dict[str, list[Path]]
    problems: dict[str, list[SkillGraftError]]


def index(source: Path) -> Index:
    folders: dict[str, list[Path]] = {}
    problems: dict[str, list[SkillGraftError]] = {}
    for folder in skill_folders(source):
        try:
            name = read_name(folder)
        except SkillGraftError as error:
            problems.setdefault(folder.name, []).append(error)
            continue
        if NAME.fullmatch(name):
            folders.setdefault(name, []).append(folder)
        else:
            problems.setdefault(folder.name, []).append(
                SkillGraftError(
                    f"{folder / 'SKILL.md'}: name {name!r} is not one path segment"
                )
            )
    return Index(folders, problems)


def find(skills: Index, skill_id: SkillId) -> Path:
    """The folder of the one skill named `skill_id.name`."""
    matches = skills.folders.get(skill_id.name, [])
    if problems := skills.problems.get(skill_id.name):
        if matches:
            # The unreadable skill may be named this too: never pick silently.
            raise SkillGraftError(
                f"entry '{skill_id}' is ambiguous: it matches {matches[0]}, "
                f"but {problems[0]}"
            )
        raise problems[0]
    if not matches:
        raise SkillGraftError(f"entry '{skill_id}': no skill {skill_id.name!r} found")
    if len(matches) > 1:
        folders = ", ".join(str(m) for m in matches)
        raise SkillGraftError(f"entry '{skill_id}': several skills match: {folders}")
    return matches[0]
