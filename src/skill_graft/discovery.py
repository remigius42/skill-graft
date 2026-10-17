"""Finds the skills in a source."""

import os
import re
from dataclasses import dataclass
from pathlib import Path

from skill_graft import paths, references
from skill_graft.config import NAME, SkillId
from skill_graft.errors import SkillGraftError

# A comment: `#` after whitespace, to the end of the line.
COMMENT = re.compile(r"\s+#.*$")


def skill_folders(source: Path, confined: bool = False) -> list[Path]:
    """Every folder under `source` holding a `SKILL.md`, not looking inside one.

    Follows symlinked folders, visiting each resolved folder once, and skips `.git`,
    the package and any other `.apm/skill-graft`, so build never reads its own
    output or another package's vendored copies. When `confined`, as for
    a git source, whose links someone else wrote, only links that stay inside
    `source` are followed.
    """
    found = []
    package = paths.package().resolve()
    root = source.resolve()
    visited = {root}
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
                and not _package(Path(dirpath) / name)
                and not _package(real)
                and (not confined or real.is_relative_to(root))
            ):
                visited.add(real)
                keep.append(name)
        dirnames[:] = keep
    return found


def _package(folder: Path) -> bool:
    """Whether `folder` is named as a package: `skill-graft` inside `.apm`."""
    return folder.name == "skill-graft" and folder.parent.name == ".apm"


def read_name(folder: Path) -> str:
    """The `name:` of the front matter opening `SKILL.md`, else the folder name.

    Reads only plain and quoted one-line values; anything else is an error, never
    a silent fallback to the folder name.
    """
    skill_md = folder / "SKILL.md"
    try:
        text = skill_md.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        raise SkillGraftError(f"{skill_md}: cannot be read: {error}") from None
    found = references.name_line(text)
    if found is None:
        return folder.name
    following = text[found[1] :].splitlines()[:1]
    continued = bool(following) and following[0][:1].isspace()
    value = _scalar(text[found[0] : found[1]].rstrip("\r\n").removeprefix("name:"))
    if value is None or continued:
        raise SkillGraftError(f"{skill_md}: unsupported form of `name:`")
    return value


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

    A skill whose name cannot be read (`unreadable`), or is read but is not one
    path segment (`invalid`), is filed under its folder name: an entry naming that
    folder gets the error, other entries never see it.
    """

    folders: dict[str, list[Path]]
    unreadable: dict[str, list[SkillGraftError]]
    invalid: dict[str, list[SkillGraftError]]


def index(source: Path, confined: bool = False) -> Index:
    skills = Index({}, {}, {})
    for folder in skill_folders(source, confined):
        try:
            name = read_name(folder)
        except SkillGraftError as error:
            skills.unreadable.setdefault(folder.name, []).append(error)
            continue
        if NAME.fullmatch(name):
            skills.folders.setdefault(name, []).append(folder)
        else:
            skills.invalid.setdefault(folder.name, []).append(
                SkillGraftError(
                    f"{folder / 'SKILL.md'}: name {name!r} is not one path segment"
                )
            )
    return skills


def find(skills: Index, skill_id: SkillId, who: str | None = None) -> Path:
    """The folder of the one skill named `skill_id.name`.

    Errors name `who` asked: by default the entry `skill_id`.
    """
    who = who or f"entry '{skill_id}'"
    matches = skills.folders.get(skill_id.name, [])
    if unreadable := skills.unreadable.get(skill_id.name):
        if matches:
            # The unreadable skill may be named this too: never pick silently.
            raise SkillGraftError(
                f"{who} is ambiguous: it matches {matches[0]}, but {unreadable[0]}"
            )
        raise unreadable[0]
    # An invalid name is known not to be this one, so it only explains a miss.
    if (invalid := skills.invalid.get(skill_id.name)) and not matches:
        raise invalid[0]
    if not matches:
        raise SkillGraftError(f"{who}: no skill {skill_id.name!r} found")
    if len(matches) > 1:
        folders = ", ".join(str(m) for m in matches)
        raise SkillGraftError(f"{who}: several skills match: {folders}")
    return matches[0]
