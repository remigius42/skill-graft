"""Views of the hull beyond `resolve`'s tree: why, Mermaid and its mermaid.live link."""

import base64
import json
import zlib

from skill_graft import lock
from skill_graft.config import SkillId
from skill_graft.hull import Edge, Hull


def why(hull: Hull, skill: SkillId) -> str:
    """The inverted tree, as `cargo tree -i`: `skill`, then what reaches it.

    Children are the skills whose slash or Skill tool reference resolves to the
    parent, in hull order. An entry below the root ends the path; any other
    skill expands once, its later lines marked `(*)`.
    """
    callers: dict[SkillId, dict[tuple[SkillId, str, bool], Edge]] = {}
    for edge in hull.edges:
        if edge.kind != "prose" and edge.source != edge.target:
            key = (edge.source, edge.kind, edge.bind)
            callers.setdefault(edge.target, {}).setdefault(key, edge)
    order = {s: i for i, s in enumerate(hull.skills)}
    expanded = {skill}
    lines = [lock.node_label(hull, skill) + _entry(hull, skill)]

    def expand(target: SkillId, prefix: str) -> None:
        edges = sorted(callers.get(target, {}).values(), key=lambda e: order[e.source])
        for i, edge in enumerate(edges):
            last = i == len(edges) - 1
            entry = edge.source in hull.entries
            repeat = not entry and edge.source in expanded
            line = (
                f"{prefix}{'└─← ' if last else '├─← '}"
                f"{lock.node_label(hull, edge.source)} ({lock.edge_label(edge)})"
            )
            lines.append(line + _entry(hull, edge.source) + (" (*)" if repeat else ""))
            if not (entry or repeat):
                expanded.add(edge.source)
                expand(edge.source, prefix + ("    " if last else "│   "))

    expand(skill, "")
    return "".join(f"{line}\n" for line in lines)


def _entry(hull: Hull, skill: SkillId) -> str:
    return " (entry)" if skill in hull.entries else ""


def mermaid(hull: Hull) -> str:
    """The hull as a Mermaid `flowchart TD`: one arrow per tree line, no repeats.

    Nodes are `n0…` in hull order, as skill IDs hold `/`. Prose arrows are dotted.
    """
    ids = {skill: f"n{i}" for i, skill in enumerate(hull.skills)}
    lines = ["flowchart TD"]
    for skill, node in ids.items():
        entry = ":::entry" if skill in hull.entries else ""
        lines.append(f"  {node}[{_quote(lock.node_label(hull, skill))}]{entry}")
    for source, edges in lock.shown_edges(hull).items():
        for edge in edges:
            arrow = "-.->" if edge.kind == "prose" else "-->"
            label = _quote(lock.edge_label(edge))
            lines.append(f"  {ids[source]} {arrow}|{label}| {ids[edge.target]}")
    lines.append("  classDef entry stroke-width:3px")
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
