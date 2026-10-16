"""Where skill-graft and APM keep their files, all derived from `HOME`."""

from pathlib import Path


def package() -> Path:
    return Path.home() / ".apm" / "skill-graft"


def config_file() -> Path:
    return package() / "skill-graft.toml"


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
