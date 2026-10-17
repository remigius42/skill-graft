"""Resolves references and walks the hull: the entries and every skill they reach."""

from collections import deque
from dataclasses import dataclass
from pathlib import Path

from skill_graft import discovery, files, patch, references
from skill_graft.config import Config, SkillId, deployed
from skill_graft.errors import SkillGraftError


@dataclass(frozen=True)
class Edge:
    source: SkillId
    target: SkillId
    kind: str  # "slash", "skill-tool" or "prose"
    bind: bool  # a bind decided the target
    text: str  # the reference as written
    name: str  # the name as written


@dataclass(frozen=True)
class Hull:
    skills: dict[SkillId, Path]  # in the order reached
    entries: list[SkillId]
    edges: list[Edge]
    warnings: list[str]
    # Every reference in a skill resolved to a hull skill, self-references included.
    occurrences: dict[SkillId, list[tuple[references.Reference, SkillId]]]
    # Skills outside the hull that prose mentions, and the skills mentioning them.
    suggestions: dict[SkillId, set[SkillId]]
    # Each skill's deployed name.
    deployed: dict[SkillId, str]
    # Each skill's folder as its source has it; `skills` holds the patched copy.
    upstream: dict[SkillId, Path]
    # Each patched skill's patch files, as written, in apply order.
    patches: dict[SkillId, list[str]]
    # Each source's folder as walked; the lock records upstream relative to it.
    roots: dict[str, Path]


def walk(config: Config, indexes: dict[str, discovery.Index], work: Path) -> Hull:
    """Breadth-first from the entries, each skill checked, patched and scanned once.

    A patched skill is copied under `work`, which must outlive the hull.
    """
    skills = {
        entry: discovery.find(indexes[entry.alias], entry) for entry in config.entries
    }
    edges: list[Edge] = []
    warnings: list[str] = []
    occurrences: dict[SkillId, list[tuple[references.Reference, SkillId]]] = {}
    prose: list[tuple[SkillId, references.Reference, SkillId, bool, SkillId]] = []
    unmatched: set[tuple[SkillId, str]] = set()  # warned once per skill and name
    used: set[SkillId] = set()  # bind keys some reference used
    upstream: dict[SkillId, Path] = {}
    queue = deque(skills)
    # Skills whose patches failed: the walk goes on, to report them all at once.
    failed: list[tuple[SkillId, Path, list[str]]] = []
    try:
        while queue:
            current = queue.popleft()
            upstream[current] = skills[current]
            files.check_files(skills[current])  # before reading any file in it
            if current in config.patches:
                try:
                    skills[current] = patch.apply(
                        current, upstream[current], config.patches[current], work
                    )
                except patch.PatchFailed as error:  # its references stay unread
                    failed.append((current, upstream[current], error.lines))
                    continue
            found, file_warnings = references.scan(skills[current])
            warnings += [  # naming the upstream file, not the copy, which goes away
                w.replace(str(skills[current]), str(upstream[current]))
                for w in file_warnings
            ]
            for ref in found:
                key = SkillId(current.alias, ref.name)
                bound = key in config.binds
                if bound:
                    used.add(key)
                    target = config.binds[key]
                    if target is None:  # bound to nothing: not a reference
                        continue
                elif ref.kind == "prose":
                    target = _prose_target(current, ref, indexes[current.alias])
                    if target is None:  # matches nothing: not a reference
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
                if ref.kind == "prose":  # never extends the hull: sorted out below
                    prose.append((current, ref, target, bound, key))
                    continue
                occurrences.setdefault(current, []).append((ref, target))
                if target == current:
                    continue
                edges.append(Edge(current, target, ref.kind, bound, ref.text, ref.name))
                if target not in skills:
                    who = (
                        f'[bind] "{key}" = "{target}"'
                        if bound
                        else f"'{current}' calls {ref.text}"
                    )
                    skills[target] = discovery.find(indexes[target.alias], target, who)
                    queue.append(target)
    except (SkillGraftError, OSError) as error:
        if not failed:
            raise
        raise patch.PatchError(failed, str(error)) from None
    if failed:  # the hull is incomplete: no warning about it would be right
        raise patch.PatchError(failed)
    suggestions: dict[SkillId, set[SkillId]] = {}
    for current, ref, target, bound, key in prose:
        if target in skills:
            occurrences.setdefault(current, []).append((ref, target))
            if target != current:
                edges.append(Edge(current, target, "prose", bound, ref.text, ref.name))
        else:
            if bound:  # a bound target must exist, whatever the form
                discovery.find(indexes[target.alias], target, f'[bind] "{key}"')
            suggestions.setdefault(target, set()).add(current)
    warnings += [
        f'[bind] "{key}" binds no reference: no skill in the hull from '
        f"{key.alias!r} calls {key.name!r}"
        for key in config.binds
        if key not in used
    ]
    names = {skill: deployed(config, skill) for skill in skills}
    patched = {
        skill: [file.path for file in config.patches[skill]]
        for skill in skills
        if skill in config.patches
    }
    return Hull(
        skills,
        list(config.entries),
        edges,
        warnings,
        occurrences,
        suggestions,
        names,
        upstream,
        patched,
        {alias: index.root for alias, index in indexes.items()},
    )


def _prose_target(
    current: SkillId, ref: references.Reference, own: discovery.Index
) -> SkillId | None:
    """The one skill of that name in the own source; prose never looks further.

    Never raises: an ambiguous or unreadable match is no reference.
    """
    if len(own.folders.get(ref.name, [])) == 1 and ref.name not in own.unreadable:
        return SkillId(current.alias, ref.name)
    return None


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
