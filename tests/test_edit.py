"""The `edit` spec: `add`, `remove` and `rename` change skill-graft.toml in place."""

import tomllib
from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import skill, write_config

from skill_graft.cli import main

Capsys: TypeAlias = pytest.CaptureFixture[str]


def package(home: Path) -> Path:
    return home / ".apm" / "skill-graft"


def entries(home: Path) -> list[str]:
    data = tomllib.loads((package(home) / "skill-graft.toml").read_text())
    result = data.get("entries", [])
    assert isinstance(result, list)
    return result


def test_add_succeeds(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "mp" / "notes")
    write_config('entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n')

    assert main(["add", "mp/notes"]) == 0

    assert entries(home) == ["mp/tdd", "mp/notes"]
    assert 'id = "mp/notes"' in (package(home) / "skill-graft.lock").read_text()
    assert capsys.readouterr().out == "mp/tdd\nmp/notes\n"
    assert not (package(home) / ".apm").exists()


def test_edit_fails_to_resolve(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "mp" / "notes", "/x\n")
    for alias in ("a", "b"):
        skill(home / alias / "x")
    config = write_config(
        'entries = ["mp/tdd"]\n'
        '[sources.mp]\npath = "~/mp"\n[sources.a]\npath = "~/a"\n'
        '[sources.b]\npath = "~/b"\n'
    )
    assert main(["resolve"]) == 0
    before = (config.read_bytes(), (package(home) / "skill-graft.lock").read_bytes())
    capsys.readouterr()

    assert main(["add", "mp/notes"]) == 1

    after = (config.read_bytes(), (package(home) / "skill-graft.lock").read_bytes())
    assert after == before
    assert capsys.readouterr().out == ""


def test_symlinked_config(home: Path, capsys: Capsys) -> None:
    skill(home / "dotfiles" / "skills" / "tdd")
    skill(home / "dotfiles" / "skills" / "notes")
    package(home).mkdir(parents=True)
    target = home / "dotfiles" / "skill-graft.toml"
    # Relative to ~/.apm/skill-graft/, as `load` reads it, not to the link's target.
    target.write_text(
        'entries = ["s/tdd"]\n[sources.s]\npath = "../../dotfiles/skills"\n'
    )
    link = package(home) / "skill-graft.toml"
    link.symlink_to(target)

    assert main(["add", "s/notes"]) == 0

    assert link.is_symlink()
    assert 'entries = ["s/tdd", "s/notes"]' in target.read_text()
