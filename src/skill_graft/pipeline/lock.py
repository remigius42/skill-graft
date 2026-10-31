"""Writes `skill-graft.lock`, where the hull came from; reads back its hashes."""

import hashlib
import json
import os
import tomllib
from pathlib import Path
from typing import Any

import tomlkit

from skill_graft.infra import files, paths
from skill_graft.pipeline import deployed, rename
from skill_graft.pipeline.config import Config, GitSource, SkillId
from skill_graft.pipeline.hull import Hull


def render(
    scope: paths.Scope,
    config: Config,
    refs: dict[str, str],
    hull: Hull,
    hashes: dict[SkillId, str] | None = None,
) -> str:
    """The lock's text: git sources at `refs`, else their ref; all sorted but a skill's
    patches.

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
            table["path"] = _source_path(scope, source.folder)
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


def _source_path(scope: paths.Scope, folder: Path) -> str:
    """A path source's folder; in project scope, relative to the package when it
    is inside the project, so a committed lock reads the same on every machine."""
    # In project scope the root is already resolved: `discover` or the working folder.
    if not scope.user and folder.is_relative_to(scope.root):
        return Path(os.path.relpath(folder, scope.package)).as_posix()
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


def copy_problems(skills: Path, locked: dict[str, Any]) -> list[str]:
    """One line per entry of `skills` that is not a copy the loaded lock `locked`
    records: a folder whose hash differs from the lock's for the skill deployed
    under its name, or no skill is, and a file; empty for a missing `skills`.

    A copy the lock records but `skills` lacks is no problem: it is vendored again.
    """
    if not skills.exists():
        return []
    hashes = {_deployed(item): item["hash"] for item in locked["skills"]}
    problems = []
    for entry in sorted(skills.iterdir()):
        if entry.name not in hashes or not entry.is_dir():
            problems.append(f"{entry}: not in skill-graft.lock")
        elif folder_hash(entry) != hashes[entry.name]:
            problems.append(f"{entry}: differs from skill-graft.lock")
    return problems


def deployed_names(locked: dict[str, Any]) -> set[str]:
    """The deployed name of each skill the loaded lock `locked` records."""
    return {_deployed(item) for item in locked["skills"]}


def _deployed(item: dict[str, Any]) -> str:
    """A lock skill's deployed name: `deployed`, else the name in its ID."""
    return str(item.get("deployed") or str(item["id"]).partition("/")[2])


def drift(
    new: dict[str, Any], old: dict[str, Any] | None, path_aliases: set[str]
) -> tuple[list[str], str | None]:
    """How the loaded lock `new` differs from `old`: the skills of the path sources
    `path_aliases` whose hash alone differs, and the reason to refuse `new`, `None`
    when nothing else does.

    A path source's folder is no difference, nor the hash of its skills that have
    no patches in either lock; a patched one's is, as a git source's.
    """
    if old is None:
        return [], "skill-graft.lock is missing or unreadable"
    if old.get("version") != 1:
        return [], "skill-graft.lock is of another version"
    if (old_hashes := recorded(old)) is None or not isinstance(old["sources"], dict):
        return [], "skill-graft.lock is missing or unreadable"
    new_hashes = recorded(new) or {}
    patched = {s["id"] for data in (new, old) for s in data["skills"] if "patches" in s}

    def trusted(skill_id: object) -> bool:
        alias = str(skill_id).partition("/")[0]
        return alias in path_aliases and str(skill_id) not in patched

    def shape(data: dict[str, Any]) -> dict[str, Any]:
        """`data` without what a path source may change."""
        sources = {
            alias: {k: v for k, v in source.items() if k != "path"}
            if alias in path_aliases
            else source
            for alias, source in data["sources"].items()
        }
        skills = [
            {k: v for k, v in s.items() if not (k == "hash" and trusted(s["id"]))}
            for s in data["skills"]
        ]
        return data | {"sources": sources, "skills": skills}

    differ = sorted(
        (s for s, digest in new_hashes.items() if old_hashes.get(s, digest) != digest),
        key=str,
    )
    changed = [str(s) for s in differ if trusted(s)]
    new_shape, old_shape = shape(new), shape(old)
    if new_shape == old_shape:
        return changed, None
    parts = [f"{s} changed" for s in differ if not trusted(s)]
    parts += [f"{s} added" for s in sorted(new_hashes.keys() - old_hashes, key=str)]
    parts += [f"{s} removed" for s in sorted(old_hashes.keys() - new_hashes, key=str)]
    before = {s["id"]: s for s in old_shape["skills"]}
    for skill in new_shape["skills"]:
        if (was := before.get(skill["id"])) is not None:
            keys = sorted((skill.keys() | was.keys()) - {"id", "hash"})
            parts += [
                f"{key} of {skill['id']} changed"
                for key in keys
                if skill.get(key) != was.get(key)
            ]
    sources, were = new_shape["sources"], old_shape["sources"]
    parts += [f"source {a} added" for a in sorted(sources.keys() - were.keys())]
    parts += [f"source {a} removed" for a in sorted(were.keys() - sources.keys())]
    parts += [
        f"source {a} changed"
        for a in sorted(sources.keys() & were.keys())
        if sources[a] != were[a]
    ]
    links, linked = _links(new), _links(old)
    parts += [f"{link} added" for link in sorted(links - linked)]
    parts += [f"{link} removed" for link in sorted(linked - links)]
    if not parts:
        return changed, "the hull differs from skill-graft.lock in what it records"
    return changed, f"the hull differs from skill-graft.lock: {', '.join(parts)}"


def _links(data: dict[str, Any]) -> set[str]:
    """Each edge and suggestion of the loaded lock `data`, as a refusal names it:
    `<from> → <to> (<kind>)`."""
    links = set()
    for edge in data.get("edges", []):
        if isinstance(edge, dict):
            kind = f"{edge.get('kind')}{', bind' if edge.get('bind') else ''}"
            links.add(f"{edge.get('from')} → {edge.get('to')} ({kind})")
    for item in data.get("suggestions", []):
        if isinstance(item, dict):
            for mention in item.get("from", []):
                links.add(f"{mention} → {item.get('id')} (suggestion)")
    return links


def write(text: str, file: Path) -> None:
    """Replaces the lock `file` atomically."""
    files.atomic_write(file, text.encode())


def load(file: Path) -> dict[str, Any] | None:
    """The lock `file` as TOML; None if it is missing or unreadable."""
    try:
        return tomllib.loads(file.read_bytes().decode())
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None


def recorded(data: dict[str, Any] | None) -> dict[SkillId, str] | None:
    """Each skill's hash as the loaded lock `data` records it; None if there is no
    lock or it is of another version."""
    if data is None:
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
