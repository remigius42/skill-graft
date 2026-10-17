"""Views of the hull beyond `resolve`'s tree: Mermaid."""

from skill_graft import lock
from skill_graft.hull import Hull


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


def _quote(text: str) -> str:
    """A Mermaid label: quoted, with `"` and backticks as entity codes.

    A backtick inside quotes would start a Mermaid Markdown string.
    """
    return '"' + text.replace('"', "#quot;").replace("`", "#96;") + '"'
