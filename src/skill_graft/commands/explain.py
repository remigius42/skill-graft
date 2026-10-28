"""Views of the hull: its tree and prose suggestions, why, Mermaid and its mermaid.live link."""

import base64
import json
import zlib
from collections.abc import Callable

from skill_graft.infra.errors import SkillGraftError, notice
from skill_graft.pipeline.config import SkillId, Source
from skill_graft.pipeline.hull import Edge, Hull


def find(hull: Hull, text: str, parse: Callable[[str], SkillId]) -> SkillId:
    """The hull skill `text` names: a skill ID if it holds `/`, else a deployed name.

    `parse` reads a skill ID, raising unless its source has that skill.
    """
    if "/" in text:
        for skill in hull.skills:  # in the hull, it exists: no need to look
            if str(skill) == text:
                return skill
        raise SkillGraftError(_outside(hull, parse(text)))
    for skill, deployed in hull.deployed.items():
        if deployed == text:
            return skill
    for skill, deployed in hull.deployed.items():
        if skill.name == text:
            raise SkillGraftError(
                f"no skill deploys as `{text}`: `{skill}` is deployed as "
                f"`{deployed}`; try `skill-graft why {skill}`"
            )
    if suggested := sorted(s for s in hull.suggestions if s.name == text):
        raise SkillGraftError("; ".join(_outside(hull, s) for s in suggested))
    raise SkillGraftError(f"no skill in the hull deploys as `{text}`")


def _outside(hull: Hull, skill: SkillId) -> str:
    """Why `skill` is not in the hull, and how to add it."""
    mentions = ""
    if skill in hull.suggestions:
        by = ", ".join(f"`{s}`" for s in sorted(hull.suggestions[skill]))
        mentions = f"; {by} mention it in prose, which never pulls a skill in"
    return f"`{skill}` is not in the hull{mentions}: `skill-graft add {skill}`"


def tree(hull: Hull) -> str:
    """The hull as `cargo tree` prints: one line per edge, repeats marked `(*)`.

    Each entry expands at the top level; any other skill at its first line. A
    renamed or prefixed skill shows its deployed name, a patched one `(patched)`.
    A prose edge shows only when the build rewrites it; it pulls nothing in, so
    its target expands elsewhere: `(*)`.
    """
    children = _shown_edges(hull)
    expanded: set[SkillId] = set()
    lines: list[str] = []

    def expand(skill_id: SkillId, prefix: str) -> None:
        expanded.add(skill_id)
        edges = children.get(skill_id, [])
        for i, edge in enumerate(edges):
            last = i == len(edges) - 1
            repeat = (
                edge.kind == "prose"
                or edge.target in expanded
                or edge.target in hull.entries
            )
            line = (
                f"{prefix}{'└── ' if last else '├── '}"
                f"{_node_label(hull, edge.target)} ({_edge_label(edge)})"
            )
            lines.append(line + (" (*)" if repeat else ""))
            if not repeat:
                expand(edge.target, prefix + ("    " if last else "│   "))

    for entry in hull.entries:
        lines.append(_node_label(hull, entry))
        expand(entry, "")
    return "".join(f"{line}\n" for line in lines)


def _shown_edges(hull: Hull) -> dict[SkillId, list[Edge]]:
    """Each skill's edges that get a tree line, in scan order.

    One per target, kind and bind; a prose edge only when the build rewrites it.
    """
    children: dict[SkillId, dict[tuple[SkillId, str, bool], Edge]] = {}
    for edge in hull.edges:
        if edge.kind == "prose" and hull.deployed[edge.target] == edge.name:
            continue
        key = (edge.target, edge.kind, edge.bind)
        children.setdefault(edge.source, {}).setdefault(key, edge)
    return {source: list(edges.values()) for source, edges in children.items()}


def _node_label(hull: Hull, skill_id: SkillId) -> str:
    """A skill as tree lines name it: its deployed name if it differs, `(patched)`."""
    deployed = hull.deployed[skill_id]
    return (
        str(skill_id)
        + ("" if deployed == skill_id.name else f" as {deployed}")
        + (" (patched)" if skill_id in hull.patches else "")
    )


def _edge_label(edge: Edge) -> str:
    """The reference as written, plus `prose` and `bind` when they apply."""
    return ", ".join(
        [edge.text]
        + (["prose"] if edge.kind == "prose" else [])
        + (["bind"] if edge.bind else [])
    )


def suggestions(hull: Hull) -> str:
    """The skills prose mentions outside the hull, and who mentions them."""
    if not hull.suggestions:
        return ""
    lines = [
        f"  {skill}, by {', '.join(sorted(str(s) for s in hull.suggestions[skill]))}"
        for skill in sorted(hull.suggestions)
    ]
    header = (
        "mentioned in prose, not in the hull (`skill-graft add <skill id>` to include):"
    )
    return "".join(f"{line}\n" for line in ["", header, *lines])


def announce_suggestions(hull: Hull, dry_run: bool = False) -> None:
    """For `build` and `update`: one line pointing to `resolve`, which lists them.

    After a dry run `resolve` still reads the old refs, so the hint says to update.
    """
    if not hull.suggestions:
        return
    count = f"{len(hull.suggestions)} prose suggestion(s)"
    if dry_run:
        notice(f"{count} at the new tips: update, then run skill-graft resolve")
    else:
        notice(f"{count}: run skill-graft resolve")


def why(hull: Hull, skill: SkillId) -> str:
    """The inverted tree, as `cargo tree -i`: `skill`, then what reaches it.

    Children are the skills whose slash or Skill tool reference resolves to the
    parent, in hull order. An entry below the root ends the path; any other
    skill expands once, its later lines marked `(*)`.
    """
    callers: dict[SkillId, dict[tuple[SkillId, str, bool], Edge]] = {}
    for edge in hull.edges:
        if edge.kind != "prose":  # the walk records no self-references
            key = (edge.source, edge.kind, edge.bind)
            callers.setdefault(edge.target, {}).setdefault(key, edge)
    order = {s: i for i, s in enumerate(hull.skills)}
    expanded = {skill}
    lines = [_node_label(hull, skill) + _entry(hull, skill)]

    def expand(target: SkillId, prefix: str) -> None:
        edges = sorted(callers.get(target, {}).values(), key=lambda e: order[e.source])
        for i, edge in enumerate(edges):
            last = i == len(edges) - 1
            entry = edge.source in hull.entries
            repeat = not entry and edge.source in expanded
            line = (
                f"{prefix}{'└─← ' if last else '├─← '}"
                f"{_node_label(hull, edge.source)} ({_edge_label(edge)})"
            )
            lines.append(line + _entry(hull, edge.source) + (" (*)" if repeat else ""))
            if not (entry or repeat):
                expanded.add(edge.source)
                expand(edge.source, prefix + ("    " if last else "│   "))

    expand(skill, "")
    # The base a new patch is written against; the lock records it only relative.
    lines.append(f"upstream: {hull.upstream[skill]}")
    return "".join(f"{line}\n" for line in lines)


def _entry(hull: Hull, skill: SkillId) -> str:
    return " (entry)" if skill in hull.entries else ""


def mermaid(hull: Hull, sources: dict[str, Source]) -> str:
    """The hull as a Mermaid `flowchart TD`: one arrow per tree line, no repeats.

    Nodes are `n0…` in hull order, as skill IDs hold `/`, inside one subgraph
    `s0…` per source in order of its first skill. Arrows follow every subgraph,
    so Mermaid moves no node into the subgraph an arrow is written in. Prose
    arrows are dotted.
    """
    ids = {skill: f"n{i}" for i, skill in enumerate(hull.skills)}
    groups: dict[str, list[SkillId]] = {}
    for skill in hull.skills:
        groups.setdefault(skill.alias, []).append(skill)
    lines = ["flowchart TD"]
    for i, (alias, skills) in enumerate(groups.items()):
        lines.append(f"  subgraph s{i}[{_quote(alias)}]")
        for skill in skills:
            entry = ":::entry" if skill in hull.entries else ""
            lines.append(f"    {ids[skill]}[{_quote(_node_label(hull, skill))}]{entry}")
        lines.append("  end")
    for source, edges in _shown_edges(hull).items():
        for edge in edges:
            arrow = "-.->" if edge.kind == "prose" else "-->"
            label = _quote(_edge_label(edge))
            lines.append(f"  {ids[source]} {arrow}|{label}| {ids[edge.target]}")
    lines.append(
        "  classDef entry fill:#fde68a,stroke:#b45309,stroke-width:3px,color:#451a03"
    )
    return "".join(f"{line}\n" for line in lines)


def link(diagram: str) -> str:
    """A mermaid.live URL holding `diagram` in its fragment, which no request sends.

    The editor's `pako` form: its JSON state zlib-deflated, in url-safe base64
    without padding. The editor fills in the state's other fields.
    """
    state = {"code": diagram, "mermaid": json.dumps({"theme": "default"})}
    data = zlib.compress(json.dumps(state).encode(), 9)
    encoded = base64.urlsafe_b64encode(data).decode().rstrip("=")
    return f"https://mermaid.live/edit#pako:{encoded}"


def _quote(text: str) -> str:
    """A Mermaid label: quoted, with `"` and backticks as entity codes.

    A backtick inside quotes would start a Mermaid Markdown string.
    """
    return '"' + text.replace('"', "#quot;").replace("`", "#96;") + '"'
