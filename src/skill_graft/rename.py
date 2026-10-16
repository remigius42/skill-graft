"""Deployed names: carried into each renamed skill's `name:` and every reference."""

import re
from pathlib import Path

from skill_graft import references
from skill_graft.config import Config, SkillId
from skill_graft.errors import SkillGraftError
from skill_graft.hull import Hull

# A name YAML reads back as this very string when written plain.
PLAIN = re.compile(r"[a-z][a-z0-9-]*")
# Plain words YAML 1.1 reads as a bool or null.
YAML_WORDS = {"y", "n", "yes", "no", "on", "off", "true", "false", "null"}


def deployed(
    config: Config, skills: list[SkillId]
) -> tuple[dict[SkillId, str], list[str]]:
    """Each skill's deployed name: its rename, else its name; and warnings."""
    names = {skill: config.renames.get(skill, skill.name) for skill in skills}
    warnings = [
        f'[rename] "{key}" renames no skill in the hull'
        for key in config.renames
        if key not in names
    ]
    return names, warnings


def check_unique(names: dict[SkillId, str]) -> None:
    """No two skills share a deployed name.

    Compared ignoring case: on a case-insensitive file system the folders collide.
    """
    by_name: dict[str, list[SkillId]] = {}
    for skill, name in names.items():
        by_name.setdefault(name.casefold(), []).append(skill)
    for clashing in by_name.values():
        if len(clashing) > 1:
            taken = " / ".join(sorted({repr(names[skill]) for skill in clashing}))
            ids = ", ".join(str(skill) for skill in clashing)
            last = clashing[-1]
            raise SkillGraftError(
                f"deployed name {taken} is taken by several skills: {ids}; rename "
                f'one: [rename] "{last}" = "{last.alias}-{last.name}"'
            )


def rewrites(hull: Hull) -> dict[SkillId, dict[Path, bytes]]:
    """Per hull skill, the files whose vendored bytes differ from upstream.

    A reference whose target's deployed name differs from the name written is
    rewritten in place; a renamed skill's `SKILL.md` gets its new `name:`. Keyed
    by the path relative to the skill's folder; unchanged files are left out.
    """
    result: dict[SkillId, dict[Path, bytes]] = {}
    for skill, folder in hull.skills.items():
        by_file: dict[Path, list[tuple[tuple[int, int], str]]] = {}
        for ref, target in hull.occurrences.get(skill, []):
            if (new := hull.deployed[target]) != ref.name:
                by_file.setdefault(ref.file, []).append((ref.span, new))
        renamed = hull.deployed[skill] != skill.name
        if renamed:
            by_file.setdefault(folder / "SKILL.md", [])
        changed = {}
        for file, spans in by_file.items():
            text = file.read_bytes().decode("utf-8")
            for (start, end), new in sorted(spans, reverse=True):  # back to front
                text = f"{text[:start]}{new}{text[end:]}"
            if renamed and file == folder / "SKILL.md":
                text = set_name(text, hull.deployed[skill])
            changed[file.relative_to(folder)] = text.encode()
        if changed:
            result[skill] = changed
    return result


def set_name(text: str, name: str) -> str:
    """`text` of a `SKILL.md` whose front matter `name:` is `name`.

    Replaces the `name:` line, else adds one atop the front matter, else adds a
    front matter. Line endings and a BOM are kept.
    """
    value = name if PLAIN.fullmatch(name) and name not in YAML_WORDS else f'"{name}"'
    if span := references.name_line(text):
        line = text[span[0] : span[1]]
        ending = line[len(line.rstrip("\r\n")) :]
        return f"{text[: span[0]]}name: {value}{ending}{text[span[1] :]}"
    bom = "﻿" if text.startswith("﻿") else ""
    body = text.removeprefix(bom)
    if _has_front_matter(body):
        first = body.splitlines(keepends=True)[0]
        ending = first[len(first.rstrip("\r\n")) :]
        return f"{bom}{first}name: {value}{ending}{body[len(first) :]}"
    return f"{bom}---\nname: {value}\n---\n{body}"


def _has_front_matter(text: str) -> bool:
    """Whether `text` opens with a `---` fence that a later one closes."""
    fences = [i for i, line in enumerate(text.splitlines()) if line.rstrip() == "---"]
    return fences[:1] == [0] and len(fences) > 1
