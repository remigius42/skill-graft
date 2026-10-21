"""Writes `skill-graft.lock`: where the hull came from. Output only, never read."""

import hashlib
import os
import stat
from pathlib import Path

import tomlkit

from skill_graft import files, paths, rename
from skill_graft.config import Config, GitSource, SkillId
from skill_graft.errors import notice
from skill_graft.hull import Edge, Hull


def render(
    config: Config,
    refs: dict[str, str],
    hull: Hull,
    hashes: dict[SkillId, str] | None = None,
) -> str:
    """The lock's text: git sources at `refs`, else their ref; all sorted but a skill's patches.

    Hashes each skill as `hashes` gives, else as it would be vendored.
    """
    hashes = skill_hashes(hull) if hashes is None else hashes
    document = tomlkit.document()
    document["version"] = 1
    sources = tomlkit.table()
    for alias in sorted(config.sources):
        source = config.sources[alias]
        table = tomlkit.table()
        if isinstance(source, GitSource):
            table["git"] = source.url
            table["ref"] = refs.get(alias) or source.ref
        else:
            table["path"] = _source_path(source.folder)
        sources[alias] = table
    document["sources"] = sources
    skills = tomlkit.aot()
    for skill_id in sorted(hull.skills):
        item: dict[str, object] = {
            "id": str(skill_id),
            "entry": skill_id in hull.entries,
        }
        if (deployed := hull.deployed[skill_id]) != skill_id.name:
            item["deployed"] = deployed
        # Relative to its source, so the lock reads the same on every machine.
        root = hull.roots[skill_id.alias]
        item["upstream"] = hull.upstream[skill_id].relative_to(root).as_posix()
        if skill_id in hull.patches:  # in apply order, never sorted
            item["patches"] = hull.patches[skill_id]
        skills.append(tomlkit.item(item | {"hash": hashes[skill_id]}))
    document["skills"] = skills
    edges = tomlkit.aot()
    for edge in sorted({(e.source, e.target, e.kind, e.bind) for e in hull.edges}):
        source_id, target, kind, bind = edge
        item = {"from": str(source_id), "to": str(target), "kind": kind}
        edges.append(tomlkit.item(item | ({"bind": True} if bind else {})))
    document["edges"] = edges
    suggestions = tomlkit.aot()
    for skill_id in sorted(hull.suggestions):
        mentions = sorted(str(s) for s in hull.suggestions[skill_id])
        suggestions.append(tomlkit.item({"id": str(skill_id), "from": mentions}))
    document["suggestions"] = suggestions
    # A string, not a tomlkit comment: tomlkit hoists an empty section above that.
    header = "# Written by skill-graft; never read. Do not edit.\n"
    return header + tomlkit.dumps(document)


def _source_path(folder: Path) -> str:
    """A path source's folder; in project scope, relative to the package when it
    is inside the project, so a committed lock reads the same on every machine."""
    # In project scope the root is already resolved: `discover` or the working folder.
    if paths.scope() == "project" and folder.is_relative_to(paths.root()):
        return Path(os.path.relpath(folder, paths.package())).as_posix()
    return str(folder)


def tree(hull: Hull) -> str:
    """The hull as `cargo tree` prints: one line per edge, repeats marked `(*)`.

    Each entry expands at the top level; any other skill at its first line. A
    renamed or prefixed skill shows its deployed name, a patched one `(patched)`.
    A prose edge shows only when the build rewrites it; it pulls nothing in, so
    its target expands elsewhere: `(*)`.
    """
    children = shown_edges(hull)
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
                f"{node_label(hull, edge.target)} ({edge_label(edge)})"
            )
            lines.append(line + (" (*)" if repeat else ""))
            if not repeat:
                expand(edge.target, prefix + ("    " if last else "│   "))

    for entry in hull.entries:
        lines.append(node_label(hull, entry))
        expand(entry, "")
    return "".join(f"{line}\n" for line in lines)


def shown_edges(hull: Hull) -> dict[SkillId, list[Edge]]:
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


def node_label(hull: Hull, skill_id: SkillId) -> str:
    """A skill as tree lines name it: its deployed name if it differs, `(patched)`."""
    deployed = hull.deployed[skill_id]
    return (
        str(skill_id)
        + ("" if deployed == skill_id.name else f" as {deployed}")
        + (" (patched)" if skill_id in hull.patches else "")
    )


def edge_label(edge: Edge) -> str:
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


def skill_hashes(hull: Hull) -> dict[SkillId, str]:
    """Each hull skill's hash as it would be vendored: rewrites applied."""
    rewrites = rename.rewrites(hull)
    return {
        skill: folder_hash(folder, rewrites.get(skill, {}))
        for skill, folder in hull.skills.items()
    }


def folder_hash(folder: Path, overrides: dict[Path, bytes] | None = None) -> str:
    """SHA-256 of the folder as vendored: each file's path, exec bit and bytes.

    Symlinks are followed, as the copy does; `.git` is skipped, as it is not copied.
    A file in `overrides`, by path relative to `folder`, is hashed with its bytes.
    """
    overrides = overrides or {}
    digest = hashlib.sha256()
    for relative, file in sorted(
        (b"/".join(os.fsencode(part) for part in f.relative_to(folder).parts), f)
        for f in files.skill_entries(folder)
        if not f.is_dir()
    ):
        content = overrides.get(file.relative_to(folder))
        if content is None:
            content = file.read_bytes()
        executable = b"1" if file.stat().st_mode & stat.S_IXUSR else b"0"
        digest.update(b"\0".join([relative, executable, b"%d" % len(content), b""]))
        digest.update(content)
    return f"sha256:{digest.hexdigest()}"


def write(text: str) -> None:
    """Replaces the lock in the package folder atomically."""
    files.atomic_write(paths.package() / "skill-graft.lock", text.encode())
