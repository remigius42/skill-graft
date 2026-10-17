"""Where skill-graft and APM keep their files, derived from the scope's root.

The root is the home folder (user scope) or a project folder (project scope).
"""

import os
from pathlib import Path

_root: Path | None = None


def use(root: Path | None) -> None:
    """Sets the root for this invocation; `None` falls back to the home folder."""
    global _root
    _root = root


def root() -> Path:
    return Path.home() if _root is None else _root


def scope() -> str:
    """`user` when the root is the home folder, else `project`."""
    return "user" if root().resolve() == Path.home().resolve() else "project"


def discover(start: Path) -> Path:
    """The first of `start` and its ancestors holding `.apm/skill-graft/`, stopping
    after the home folder; the home folder if none does."""
    home = Path.home().resolve()
    for folder in [start.resolve(), *start.resolve().parents]:
        if folder == home:
            break
        if (folder / ".apm" / "skill-graft").is_dir():
            return folder
    return Path.home()


def package() -> Path:
    return root() / ".apm" / "skill-graft"


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


def deploy_folders() -> list[Path]:
    return [Path.home() / folder for folder in DEPLOY_FOLDERS]


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
