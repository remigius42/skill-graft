"""Where skill-graft and APM keep their files, derived from the scope's root.

The root is the home folder (user scope) or a project folder (project scope).
"""

import os
from pathlib import Path

_root: Path | None = None
_scope = "user"


def use(root: Path | None) -> None:
    """Sets the root for this invocation; `None` falls back to the home folder.
    The scope is decided here, once: `user` when the root is the home folder."""
    global _root, _scope
    _root = root
    home = root is None or root.resolve() == Path.home().resolve()
    _scope = "user" if home else "project"


def root() -> Path:
    return Path.home() if _root is None else _root


def scope() -> str:
    """`user` or `project`, as `use` decided."""
    return _scope


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
    a package, and `~/Own` a source `~/own`. Refusing a lookalike elsewhere is harmless."""
    return Path(str(path).lower())


def package() -> Path:
    return _package_in(root())


def config_file() -> Path:
    return package() / "skill-graft.toml"


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


def deploy_folders() -> list[Path]:
    """The user scope's deploy folders, and in project scope the project's too."""
    folders = [Path.home() / folder for folder in DEPLOY_FOLDERS]
    if scope() == "project":
        folders += [root() / folder for folder in PROJECT_DEPLOY_FOLDERS]
    return folders


def packages() -> list[Path]:
    """The package in effect, and in project scope the user scope's too."""
    if scope() == "user":
        return [package()]
    return [package(), _package_in(Path.home())]


def overlap(a: Path, b: Path) -> bool:
    """Whether one folder is, or is inside, the other."""
    return a.is_relative_to(b) or b.is_relative_to(a)


def skills() -> Path:
    return package() / ".apm" / "skills"


def manifest() -> Path:
    """APM's manifest for the scope, which lists the package once registered."""
    if scope() == "project":
        return root() / "apm.yml"
    return Path.home() / ".apm" / "apm.yml"
