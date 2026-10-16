"""Reads `skill-graft.toml`: path sources and entries."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from skill_graft import paths
from skill_graft.errors import SkillGraftError

# A source alias or skill name: one path segment, so `<alias>/<name>` splits cleanly.
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class SkillId(NamedTuple):
    alias: str
    name: str

    def __str__(self) -> str:
        return f"{self.alias}/{self.name}"


@dataclass(frozen=True)
class Config:
    sources: dict[str, Path]
    entries: list[SkillId]


def load() -> Config:
    file = paths.config_file()
    try:
        data = tomllib.loads(file.read_text())
    except FileNotFoundError:
        raise SkillGraftError(f"{file} not found: run `skill-graft init`") from None
    except tomllib.TOMLDecodeError as error:
        raise SkillGraftError(f"{file}: {error}") from None
    if unknown := sorted(data.keys() - {"sources", "entries"}):
        raise SkillGraftError(f"{unknown[0]!r} is unsupported in skill-graft.toml")
    sources = _sources(data.get("sources", {}), file.parent)
    return Config(sources, _entries(data.get("entries", []), sources))


def _sources(raw: object, base: Path) -> dict[str, Path]:
    if not isinstance(raw, dict):
        raise SkillGraftError("'sources' must hold [sources.<alias>] tables")
    sources = {}
    for alias, table in raw.items():
        if not NAME.fullmatch(alias):
            raise SkillGraftError(
                f"source alias {alias!r}: expected one path segment, {NAME.pattern}"
            )
        if not isinstance(table, dict):
            raise SkillGraftError(f"'sources.{alias}' must be a table")
        if unknown := sorted(table.keys() - {"path"}):
            raise SkillGraftError(f"'sources.{alias}.{unknown[0]}' is unsupported")
        if "path" not in table:
            raise SkillGraftError(f"'sources.{alias}.path' is missing")
        if not isinstance(table["path"], str):
            raise SkillGraftError(f"'sources.{alias}.path' must be a string")
        sources[alias] = _source_folder(alias, table["path"], base)
    return sources


def _source_folder(alias: str, raw: str, base: Path) -> Path:
    folder = (base / Path(raw).expanduser()).resolve()
    if not folder.is_dir():
        raise SkillGraftError(f"source {alias!r}: {raw} is not a folder")
    return folder


def _entries(raw: object, sources: dict[str, Path]) -> list[SkillId]:
    if not isinstance(raw, list) or not all(isinstance(e, str) for e in raw):
        raise SkillGraftError("'entries' must be a list of strings")
    entries: list[SkillId] = []
    for entry in raw:
        skill_id = _entry(entry, sources)
        if skill_id in entries:
            raise SkillGraftError(f"entry {entry!r} is repeated")
        entries.append(skill_id)
    return entries


def _entry(entry: str, sources: dict[str, Path]) -> SkillId:
    alias, _, name = entry.partition("/")
    if not alias or not name or "/" in name:
        raise SkillGraftError(f"entry {entry!r}: expected <source alias>/<skill name>")
    if alias not in sources:
        raise SkillGraftError(f"entry {entry!r}: no source {alias!r} is declared")
    return SkillId(alias, name)
