"""Where skill-graft and APM keep their files.

A `Scope` derives every path from its root, the home folder (user scope) or a
project folder (project scope), and is passed to whatever reads one; nothing
holds it globally. The cache belongs to no scope.
"""

import os
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path


@dataclass(frozen=True)
class Scope:
    """A scope, known by its root; every other path derives from it."""

    root: Path

    @cached_property
    def user(self) -> bool:
        """Whether the root is the home folder, compared resolved."""
        return self.root.resolve() == Path.home().resolve()

    @property
    def package(self) -> Path:
        return _package_in(self.root)

    @property
    def lock_file(self) -> Path:
        return self.package / "skill-graft.lock"

    @property
    def skills(self) -> Path:
        return self.package / ".apm" / "skills"

    @property
    def config_file(self) -> Path:
        return self.package / "skill-graft.toml"

    @property
    def manifest(self) -> Path:
        """APM's manifest for the scope, which lists the package once registered."""
        if self.user:
            return Path.home() / ".apm" / "apm.yml"
        return self.root / "apm.yml"

    @property
    def deploy_folders(self) -> list[Path]:
        """The user scope's deploy folders, and in project scope the project's too."""
        folders = [Path.home() / folder for folder in DEPLOY_FOLDERS]
        if not self.user:
            folders += [self.root / folder for folder in PROJECT_DEPLOY_FOLDERS]
        return folders

    @property
    def packages(self) -> list[Path]:
        """The scope's package, and in project scope the user scope's too."""
        if self.user:
            return [self.package]
        return [self.package, _package_in(Path.home())]


def discover(start: Path) -> Path:
    """The first of `start` and its ancestors holding `.apm/skill-graft/`, stopping
    after the home folder; the home folder if none does."""
    home = Path.home().resolve()
    for folder in [start.resolve(), *start.resolve().parents]:
        if folder == home:
            break
        if _package_in(folder).is_dir():
            return folder
    return Path.home()


def _package_in(folder: Path) -> Path:
    """Where a package lives in `folder`, the home folder or a project root."""
    return folder / ".apm" / "skill-graft"


def in_package(path: Path) -> bool:
    """Whether `path` is a package (`.apm/skill-graft`) or inside one, by its parts."""
    parts = path.parts
    return any(parts[i : i + 2] == (".apm", "skill-graft") for i in range(len(parts)))


def folded(path: Path) -> Path:
    """`path` in lower case: on a case-insensitive filesystem `.APM/Skill-Graft` is
    a package, and `~/Own` a source `~/own`. Refusing a lookalike elsewhere is
    harmless."""
    return Path(str(path).lower())


def cache() -> Path:
    """Where git sources are cached: `$XDG_CACHE_HOME`, if absolute, else `~/.cache`."""
    xdg = os.environ.get("XDG_CACHE_HOME", "")
    root = Path(xdg) if os.path.isabs(xdg) else Path.home() / ".cache"
    return root / "skill-graft"


# Where APM 0.33.0 deploys skills at user scope, one folder per group of targets.
DEPLOY_FOLDERS = (
    ".agents/skills",
    ".claude/skills",
    ".config/opencode/skills",
    ".gemini/antigravity-cli/skills",
    ".grok/skills",
    ".hermes/skills",
    ".kiro/skills",
    ".openclaw/skills",
)


# Where APM 0.33.0 deploys skills at project scope, under the project root.
PROJECT_DEPLOY_FOLDERS = (
    ".agents/skills",
    ".claude/skills",
    ".grok/skills",
    ".kiro/skills",
)


def overlap(a: Path, b: Path) -> bool:
    """Whether one folder is, or is inside, the other."""
    return a.is_relative_to(b) or b.is_relative_to(a)
