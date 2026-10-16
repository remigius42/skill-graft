"""Writes `skill-graft.lock`: where the hull came from. Output only, never read."""

import hashlib
import os
import stat
import tempfile
from pathlib import Path

import tomlkit

from skill_graft import paths
from skill_graft.config import Config, GitSource
from skill_graft.hull import Hull


def render(config: Config, refs: dict[str, str], hull: Hull) -> str:
    """The lock's text: git sources at `refs`, else their ref; all sorted."""
    document = tomlkit.document()
    document.add(tomlkit.comment("Written by skill-graft; never read. Do not edit."))
    document["version"] = 1
    sources = tomlkit.table()
    for alias in sorted(config.sources):
        source = config.sources[alias]
        table = tomlkit.table()
        if isinstance(source, GitSource):
            table["git"] = source.url
            table["ref"] = refs.get(alias) or source.ref
        else:
            table["path"] = str(source.folder)
        sources[alias] = table
    document["sources"] = sources
    skills = tomlkit.aot()
    for skill_id in sorted(hull.skills):
        skills.append(
            tomlkit.item(
                {
                    "id": str(skill_id),
                    "entry": skill_id in hull.entries,
                    "hash": folder_hash(hull.skills[skill_id]),
                }
            )
        )
    document["skills"] = skills
    edges = tomlkit.aot()
    for edge in sorted({(e.source, e.target, e.kind, e.bind) for e in hull.edges}):
        source_id, target, kind, bind = edge
        item = {"from": str(source_id), "to": str(target), "kind": kind}
        edges.append(tomlkit.item(item | ({"bind": True} if bind else {})))
    document["edges"] = edges
    return tomlkit.dumps(document)


def folder_hash(folder: Path) -> str:
    """SHA-256 of the folder as vendored: each file's path, exec bit and bytes.

    Symlinks are followed, as the copy does; `.git` is skipped, as it is not copied.
    """
    digest = hashlib.sha256()
    files = []
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        files += [Path(dirpath) / name for name in filenames]
    for relative, file in sorted(
        (b"/".join(os.fsencode(part) for part in f.relative_to(folder).parts), f)
        for f in files
    ):
        content = file.read_bytes()
        executable = b"1" if file.stat().st_mode & stat.S_IXUSR else b"0"
        digest.update(b"\0".join([relative, executable, b"%d" % len(content), b""]))
        digest.update(content)
    return f"sha256:{digest.hexdigest()}"


def write(text: str) -> None:
    """Replaces the lock in the package folder atomically."""
    file = paths.package() / "skill-graft.lock"
    with tempfile.NamedTemporaryFile(
        "wb", dir=file.parent, prefix=f".{file.name}.", delete=False
    ) as tmp:
        try:
            tmp.write(text.encode())
            tmp.close()
            os.replace(tmp.name, file)
        except BaseException:
            os.unlink(tmp.name)
            raise
