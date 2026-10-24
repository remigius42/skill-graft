"""Writes `skill-graft.lock`, where the hull came from; reads back its hashes."""

import hashlib
import json
import os
import tomllib
from pathlib import Path

import tomlkit

from skill_graft.infra import files, paths
from skill_graft.pipeline import deployed, rename
from skill_graft.pipeline.config import Config, GitSource, SkillId
from skill_graft.pipeline.hull import Hull


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
            if source.subdirectory:
                table["subdirectory"] = source.subdirectory
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
    header = "# Written by skill-graft; update reads its hashes. Do not edit.\n"
    return header + tomlkit.dumps(document)


def _source_path(folder: Path) -> str:
    """A path source's folder; in project scope, relative to the package when it
    is inside the project, so a committed lock reads the same on every machine."""
    # In project scope the root is already resolved: `discover` or the working folder.
    if paths.scope() == "project" and folder.is_relative_to(paths.root()):
        return Path(os.path.relpath(folder, paths.package())).as_posix()
    return str(folder)


def skill_hashes(hull: Hull) -> dict[SkillId, str]:
    """Each hull skill's hash as it would be vendored: rewrites applied."""
    rewrites = rename.rewrites(hull)
    return {
        skill: folder_hash(folder, rewrites.get(skill, {}))
        for skill, folder in hull.skills.items()
    }


def folder_hash(folder: Path, overrides: dict[Path, bytes] | None = None) -> str:
    """SHA-256 of the folder as vendored: each file's path, exec bit and bytes,
    as `deployed.walk` reads them, `overrides` in place, one file held at a time."""
    digest = hashlib.sha256()
    for relative, content, executable in deployed.walk(folder, overrides or {}):
        fields = [os.fsencode(relative), b"1" if executable else b"0"]
        digest.update(b"\0".join([*fields, b"%d" % len(content), b""]))
        digest.update(content)
    return f"sha256:{digest.hexdigest()}"


def digest(hull: Hull, hashes: dict[SkillId, str]) -> str:
    """The Hull digest: SHA-256 of each skill's ID, deployed name and hash, sorted,
    so equal digests deploy the same text under the same names."""
    triples = sorted([str(s), hull.deployed[s], hashes[s]] for s in hull.skills)
    return hashlib.sha256(json.dumps(triples, ensure_ascii=True).encode()).hexdigest()


def write(text: str, file: Path | None = None) -> None:
    """Replaces the lock (default: the package's) atomically."""
    file = paths.package() / "skill-graft.lock" if file is None else file
    files.atomic_write(file, text.encode())


def read(file: Path | None = None) -> dict[SkillId, str] | None:
    """Each skill's hash as the lock (default: the package's) records it; None if
    it is missing, unreadable or of another version."""
    file = paths.package() / "skill-graft.lock" if file is None else file
    try:
        data = tomllib.loads(file.read_bytes().decode())
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None
    skills = data.get("skills")
    if data.get("version") != 1 or not isinstance(skills, list):
        return None
    hashes = {}
    for item in skills:
        if not isinstance(item, dict):
            return None
        skill_id, digest = item.get("id"), item.get("hash")
        if not (isinstance(skill_id, str) and isinstance(digest, str)):
            return None
        alias, _, name = skill_id.partition("/")
        hashes[SkillId(alias, name)] = digest
    return hashes
