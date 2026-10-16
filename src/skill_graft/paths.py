"""Where skill-graft and APM keep their files, all derived from `HOME`."""

from pathlib import Path


def package() -> Path:
    return Path.home() / ".apm" / "skill-graft"


def config_file() -> Path:
    return package() / "skill-graft.toml"
