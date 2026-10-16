"""Reads `skill-graft.toml`: path sources and entries."""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

from skill_graft import paths
from skill_graft.errors import SkillGraftError


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
    _reject_unsupported(data)
    sources = {
        alias: _source_folder(alias, table["path"], file.parent)
        for alias, table in data.get("sources", {}).items()
    }
    entries = [_entry(entry, sources) for entry in data.get("entries", [])]
    return Config(sources, entries)


def _reject_unsupported(data: dict[str, Any]) -> None:
    if unknown := sorted(data.keys() - {"sources", "entries"}):
        raise SkillGraftError(f"{unknown[0]!r} is unsupported in skill-graft.toml")
    for alias, table in data.get("sources", {}).items():
        if unknown := sorted(table.keys() - {"path"}):
            raise SkillGraftError(f"'sources.{alias}.{unknown[0]}' is unsupported")


def _source_folder(alias: str, raw: str, base: Path) -> Path:
    folder = (base / Path(raw).expanduser()).resolve()
    if not folder.is_dir():
        raise SkillGraftError(f"source {alias!r}: {raw} is not a folder")
    return folder


def _entry(entry: str, sources: dict[str, Path]) -> SkillId:
    alias, _, name = entry.partition("/")
    if not alias or not name or "/" in name:
        raise SkillGraftError(f"entry {entry!r}: expected <source alias>/<skill name>")
    if alias not in sources:
        raise SkillGraftError(f"entry {entry!r}: no source {alias!r} is declared")
    return SkillId(alias, name)
