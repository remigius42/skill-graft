"""Resolves references and walks the hull: the entries and every skill they reach."""

import os
import stat
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from skill_graft import discovery, files, references
from skill_graft.config import Config, SkillId
from skill_graft.errors import SkillGraftError


@dataclass(frozen=True)
class Edge:
    source: SkillId
    target: SkillId
    kind: str  # "slash" or "skill-tool"
    bind: bool  # a bind decided the target
    text: str  # the reference as written


@dataclass(frozen=True)
class Hull:
    skills: dict[SkillId, Path]  # in the order reached
    entries: list[SkillId]
    edges: list[Edge]
    warnings: list[str]


def walk(config: Config, indexes: dict[str, discovery.Index]) -> Hull:
    """Breadth-first from the entries, each skill checked and scanned once."""
    skills = {
        entry: discovery.find(indexes[entry.alias], entry) for entry in config.entries
    }
    edges: list[Edge] = []
    warnings: list[str] = []
    unmatched: set[tuple[SkillId, str]] = set()  # warned once per skill and name
    used: set[SkillId] = set()  # bind keys some reference used
    queue = deque(skills)
    while queue:
        current = queue.popleft()
        check_files(skills[current])  # before reading any file in it
        found, file_warnings = references.scan(skills[current])
        warnings += file_warnings
        for ref in found:
            key = SkillId(current.alias, ref.name)
            bound = key in config.binds
            if bound:
                used.add(key)
                target = config.binds[key]
                if target is None:  # bound to nothing: not a reference
                    continue
            else:
                target = _target(current, ref, indexes)
                if target is None:
                    if (current, ref.name) not in unmatched:
                        unmatched.add((current, ref.name))
                        warnings.append(
                            f"`{current}` calls `{ref.text}`: no declared source has "
                            f'a skill `{ref.name}` (to ignore it: [bind] "{key}" = '
                            "false)"
                        )
                    continue
            if target == current:
                continue
            edges.append(Edge(current, target, ref.kind, bound, ref.text))
            if target not in skills:
                who = (
                    f'[bind] "{key}" = "{target}"'
                    if bound
                    else f"'{current}' calls {ref.text}"
                )
                skills[target] = discovery.find(indexes[target.alias], target, who)
                queue.append(target)
    warnings += [
        f'[bind] "{key}" binds no reference: no skill in the hull from '
        f"{key.alias!r} calls {key.name!r}"
        for key in config.binds
        if key not in used
    ]
    return Hull(skills, list(config.entries), edges, warnings)


def _target(
    current: SkillId, ref: references.Reference, indexes: dict[str, discovery.Index]
) -> SkillId | None:
    """The own source first, else the one other source having the name."""
    if _has(indexes[current.alias], ref.name):
        return SkillId(current.alias, ref.name)
    others = [
        SkillId(alias, ref.name)
        for alias, index in indexes.items()
        if alias != current.alias and _has(index, ref.name)
    ]
    if len(others) > 1:
        ids = ", ".join(sorted(str(other) for other in others))
        raise SkillGraftError(
            f"'{current}' calls {ref.text}, which several sources have: {ids}; "
            f'choose one under [bind]: "{current.alias}/{ref.name}" = "<source>/<name>"'
        )
    return others[0] if others else None


def _has(index: discovery.Index, name: str) -> bool:
    """Whether a skill there is named `name`, or perhaps is: its name is unreadable.

    An invalid name is known not to be `name`, so it never counts.
    """
    return name in index.folders or name in index.unreadable


def check_files(folder: Path) -> None:
    """A skill is its whole folder: a symlink may only lead to a file inside it.

    A link to a folder, even one inside, is refused: it can form a cycle. So is
    a FIFO, socket or device, which reading would block on or never finish.
    """
    root = folder.resolve()
    for link in files.skill_entries(folder):
        if not link.is_symlink():
            mode = link.lstat().st_mode
            if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise SkillGraftError(f"{link} is not a regular file")
            continue
        target = Path(os.path.realpath(link))
        if not target.is_relative_to(root):
            raise SkillGraftError(f"{link} points outside the skill, to {target}")
        if target.is_dir():
            raise SkillGraftError(f"{link} points to a folder; only file links work")
