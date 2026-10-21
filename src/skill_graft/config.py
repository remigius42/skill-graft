"""Reads `skill-graft.toml`: sources, entries, binds, renames, reserved names."""

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
class PathSource:
    folder: Path


@dataclass(frozen=True)
class GitSource:
    url: str
    branch: str | None
    ref: str | None
    # The folder of the tree read as the source's root, as written; None: the root.
    subdirectory: str | None = None


Source = PathSource | GitSource


class PatchFile(NamedTuple):
    path: str  # as written in the TOML
    data: bytes


# A full commit name: SHA-1 or SHA-256.
REF = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")

# The URL forms git is handed. Other schemes, and `<transport>::<address>`, make
# git run a remote helper; a relative path would resolve against git's folder.
URL = re.compile(r"(https?|ssh|git|file)://.+")
SCP = re.compile(r"([^@/:\s]+@)?[^/:\s]+:.+")


@dataclass(frozen=True)
class Config:
    sources: dict[str, Source]
    entries: list[SkillId]
    warnings: list[str]
    # Where references to a name from a source resolve; None: nowhere.
    binds: dict[SkillId, SkillId | None]
    # The deployed name the user gives a skill.
    renames: dict[SkillId, str]
    # What each skill of a source deploys prefixed with, by alias.
    prefixes: dict[str, str]
    # Names no skill may deploy as.
    reserved: list[str]
    # Each patched skill's patches, in apply order.
    patches: dict[SkillId, list[PatchFile]]


def deployed(config: Config, skill: SkillId) -> str:
    """The name `skill` deploys as: its rename, else its default name."""
    return config.renames.get(skill, default_name(config, skill))


def default_name(config: Config, skill: SkillId) -> str:
    """The name `skill` deploys as without a rename: its source's prefix, if any,
    before its name."""
    return config.prefixes.get(skill.alias, "") + skill.name


def load() -> Config:
    return parse(text(), paths.config_file())


def text() -> str:
    """The config file's text, decoded from UTF-8 bytes: no newline translation."""
    file = paths.config_file()
    try:
        return file.read_bytes().decode()
    except FileNotFoundError:
        if paths.scope() == "project":
            raise SkillGraftError(
                f"{file} not found: restore it, or delete {paths.package()} and run "
                f"`skill-graft init --project` in {paths.root()}"
            ) from None
        raise SkillGraftError(f"{file} not found: run `skill-graft init`") from None
    except UnicodeDecodeError as error:
        raise SkillGraftError(f"{file}: {error}") from None


def parse(text: str, file: Path) -> Config:
    """The config `text` holds, read as `file`: relative paths start at its folder."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise SkillGraftError(f"{file}: {error}") from None
    known = {"sources", "entries", "bind", "rename", "reserved", "patches"}
    if unknown := sorted(data.keys() - known):
        raise SkillGraftError(f"{unknown[0]!r} is unsupported in skill-graft.toml")
    sources, prefixes = _sources(data.get("sources", {}), file.parent)
    entries = _entries(data.get("entries", []), sources)
    binds = _binds(data.get("bind", {}), sources)
    renames = _renames(data.get("rename", {}), sources)
    reserved = _reserved(data.get("reserved", []))
    patches = _patches(data.get("patches", {}), sources, file.parent)
    return Config(
        sources,
        entries,
        _overlap_warnings(sources),
        binds,
        renames,
        prefixes,
        reserved,
        patches,
    )


def _sources(raw: object, base: Path) -> tuple[dict[str, Source], dict[str, str]]:
    """The sources by alias, and the prefix of each source that has one."""
    if not isinstance(raw, dict):
        raise SkillGraftError("'sources' must hold [sources.<alias>] tables")
    sources: dict[str, Source] = {}
    prefixes: dict[str, str] = {}
    for alias, table in raw.items():
        if not NAME.fullmatch(alias):
            raise SkillGraftError(
                f"source alias {alias!r}: expected one path segment, {NAME.pattern}"
            )
        if not isinstance(table, dict):
            raise SkillGraftError(f"'sources.{alias}' must be a table")
        if "path" in table and "git" in table:
            raise SkillGraftError(f"'sources.{alias}' has both 'path' and 'git'")
        if "path" in table:
            _check_keys(alias, table, {"path", "prefix"})
            folder = _source_folder(alias, _string(alias, table, "path"), base)
            sources[alias] = PathSource(folder)
        elif "git" in table:
            _check_keys(
                alias, table, {"git", "branch", "ref", "prefix", "subdirectory"}
            )
            sources[alias] = _git_source(alias, table)
        else:
            _check_keys(alias, table, {"prefix"})
            raise SkillGraftError(f"'sources.{alias}' needs 'path' or 'git'")
        if "prefix" in table:
            prefix = table["prefix"]
            if not (isinstance(prefix, str) and NAME.fullmatch(prefix)):
                raise SkillGraftError(
                    f"'sources.{alias}.prefix' must be a name: {NAME.pattern}"
                )
            prefixes[alias] = prefix
    return sources, prefixes


def _check_keys(alias: str, table: dict[str, object], allowed: set[str]) -> None:
    if unknown := sorted(table.keys() - allowed):
        raise SkillGraftError(f"'sources.{alias}.{unknown[0]}' is unsupported")


def _string(alias: str, table: dict[str, object], key: str) -> str:
    value = table[key]
    if not isinstance(value, str):
        raise SkillGraftError(f"'sources.{alias}.{key}' must be a string")
    return value


def _git_source(alias: str, table: dict[str, object]) -> GitSource:
    url = _string(alias, table, "git")
    scp = SCP.fullmatch(url) and "::" not in url and "://" not in url
    if url.startswith("-") or not (URL.fullmatch(url) or scp or url[:1] == "/"):
        raise SkillGraftError(
            f"'sources.{alias}.git' = {url!r}: expected an https, http, ssh, git or "
            "file URL, user@host:path, or an absolute path"
        )
    branch = _string(alias, table, "branch") if "branch" in table else None
    if branch is not None and (not branch or branch.startswith(("refs/", "-"))):
        raise SkillGraftError(
            f"'sources.{alias}.branch' = {branch!r}: expected a branch name like 'main'"
        )
    ref = _string(alias, table, "ref") if "ref" in table else None
    if ref is not None and not REF.fullmatch(ref):
        raise SkillGraftError(
            f"'sources.{alias}.ref' = {ref!r}: expected a full commit sha, "
            "40 or 64 lowercase hex digits"
        )
    subdirectory = (
        _string(alias, table, "subdirectory") if "subdirectory" in table else None
    )
    if subdirectory is not None and not _relative_folder(subdirectory):
        raise SkillGraftError(
            f"'sources.{alias}.subdirectory' = {subdirectory!r}: expected a folder "
            "relative to the repository root, like 'skills': no empty, '.', '..' or "
            "'.git' part, no control character, not into a package (.apm/skill-graft)"
        )
    return GitSource(url, branch, ref, subdirectory)


def _relative_folder(path: str) -> bool:
    """`path` as `a/b`: no empty, `.`, `..` or `.git` segment (the export never
    writes `.git`), no control character, and not into a package, whose vendored
    copies a source never offers."""
    return (
        all(
            part not in ("", ".", "..") and part.lower() != ".git"
            for part in path.split("/")
        )
        and not any(ord(c) < 32 or c == "\x7f" for c in path)
        and not paths.in_package(Path(path))
    )


def _source_folder(alias: str, raw: str, base: Path) -> Path:
    folder = (base / Path(raw).expanduser()).resolve()
    if not folder.is_dir():
        raise SkillGraftError(f"source {alias!r}: {raw} is not a folder")
    for package in paths.packages():
        if paths.overlap(folder, package.resolve()):
            raise SkillGraftError(
                f"source {alias!r}: {raw} overlaps {package}, which build rewrites"
            )
    return folder


def _overlap_warnings(sources: dict[str, Source]) -> list[str]:
    deploys = [(deploy, deploy.resolve()) for deploy in paths.deploy_folders()]
    return [
        f"source {alias!r} overlaps {deploy}, where APM deploys skills"
        for alias, source in sources.items()
        if isinstance(source, PathSource)
        for deploy, resolved in deploys
        if paths.overlap(source.folder, resolved)
    ]


def _entries(raw: object, sources: dict[str, Source]) -> list[SkillId]:
    if not isinstance(raw, list) or not all(isinstance(e, str) for e in raw):
        raise SkillGraftError("'entries' must be a list of strings")
    entries: list[SkillId] = []
    for entry in raw:
        skill_id = _entry(entry, sources)
        if skill_id in entries:
            raise SkillGraftError(f"entry {entry!r} is repeated")
        entries.append(skill_id)
    return entries


def _binds(raw: object, sources: dict[str, Source]) -> dict[SkillId, SkillId | None]:
    if not isinstance(raw, dict):
        raise SkillGraftError("'bind' must be a table of \"<alias>/<name>\" keys")
    binds: dict[SkillId, SkillId | None] = {}
    for key, value in raw.items():
        where = f'bind."{key}"'
        if value is False:
            target = None
        elif isinstance(value, str):
            target = parse_skill_id(where, value, sources)
        else:
            raise SkillGraftError(f"{where} must be a skill ID or false")
        binds[parse_skill_id(where, key, sources)] = target
    return binds


def _renames(raw: object, sources: dict[str, Source]) -> dict[SkillId, str]:
    if not isinstance(raw, dict):
        raise SkillGraftError("'rename' must be a table of \"<alias>/<name>\" keys")
    renames: dict[SkillId, str] = {}
    for key, value in raw.items():
        where = f'rename."{key}"'
        if not (isinstance(value, str) and NAME.fullmatch(value)):
            raise SkillGraftError(f"{where} must be a name: {NAME.pattern}")
        renames[parse_skill_id(where, key, sources)] = value
    return renames


def _reserved(raw: object) -> list[str]:
    if not isinstance(raw, list) or not all(
        isinstance(name, str) and NAME.fullmatch(name) for name in raw
    ):
        raise SkillGraftError(f"'reserved' must be a list of names: {NAME.pattern}")
    return raw


def _patches(
    raw: object, sources: dict[str, Source], base: Path
) -> dict[SkillId, list[PatchFile]]:
    """Each key's patch files, read now: a missing one is an error, used or not."""
    if not isinstance(raw, dict):
        raise SkillGraftError("'patches' must be a table of \"<alias>/<name>\" keys")
    patches: dict[SkillId, list[PatchFile]] = {}
    for key, value in raw.items():
        where = f'patches."{key}"'
        if not (
            isinstance(value, list)
            and value
            and all(isinstance(path, str) for path in value)
        ):
            raise SkillGraftError(f"{where} must be a non-empty list of patch files")
        skill_id = parse_skill_id(where, key, sources)
        seen: set[Path] = set()
        patches[skill_id] = []
        for path in value:
            file = (base / Path(path).expanduser()).resolve()
            if file in seen:
                raise SkillGraftError(f"{where} lists {path} twice")
            seen.add(file)
            patches[skill_id].append(PatchFile(path, _patch_data(where, path, file)))
    return patches


def _patch_data(where: str, path: str, file: Path) -> bytes:
    """A patch file's bytes, refused if `git apply` would skip a change silently."""
    try:
        data = file.read_bytes()
    except OSError as error:
        raise SkillGraftError(f"{where}: cannot read {path}: {error}") from None
    for line in data.splitlines():
        if line.startswith(b"Binary files ") and line.endswith(b" differ"):
            reason = "a `Binary files … differ` line: binary changes are unsupported"
        elif line.startswith(b"GIT binary patch"):
            reason = "a binary hunk: binary changes are unsupported"
        elif line.startswith(b"Only in "):
            reason = "an `Only in` line: write it with `diff -ruN`, -N included"
        else:
            continue
        raise SkillGraftError(f"{where}: {path} holds {reason}")
    return data


def parse_skill_id(where: str, text: str, sources: dict[str, Source]) -> SkillId:
    """`<alias>/<name>`, both one path segment, the alias declared."""
    alias, _, name = text.partition("/")
    if not (NAME.fullmatch(alias) and NAME.fullmatch(name)):
        raise SkillGraftError(f"{where}: {text!r} is not <source alias>/<skill name>")
    if alias not in sources:
        raise SkillGraftError(f"{where}: no source {alias!r} is declared")
    return SkillId(alias, name)


def _entry(entry: str, sources: dict[str, Source]) -> SkillId:
    alias, _, name = entry.partition("/")
    if not alias or not name or "/" in name:
        raise SkillGraftError(f"entry {entry!r}: expected <source alias>/<skill name>")
    if alias not in sources:
        raise SkillGraftError(f"entry {entry!r}: no source {alias!r} is declared")
    return SkillId(alias, name)
