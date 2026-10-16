from pathlib import Path

import pytest
from conftest import write_config

from skill_graft.config import SkillId, load
from skill_graft.errors import SkillGraftError


def test_home_relative_path(home: Path) -> None:
    (home / "skills").mkdir()
    write_config('[sources.own]\npath = "~/skills"\n')
    assert load().sources == {"own": (home / "skills").resolve()}


def test_relative_path_is_taken_from_the_config_folder(home: Path) -> None:
    config = write_config('[sources.own]\npath = "../../mine"\n')
    (home / "mine").mkdir()
    assert load().sources == {"own": (config.parent / "../../mine").resolve()}


def test_missing_folder() -> None:
    write_config('[sources.own]\npath = "~/nowhere"\n')
    with pytest.raises(SkillGraftError, match=r"own.*~/nowhere"):
        load()


def test_entries(home: Path) -> None:
    (home / "skills").mkdir()
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/skills"\n')
    assert load().entries == [SkillId("own", "chisel")]
    assert str(load().entries[0]) == "own/chisel"


def test_empty_config_builds_nothing() -> None:
    write_config("")
    config = load()
    assert config.sources == {}
    assert config.entries == []


def test_entry_with_an_undeclared_alias() -> None:
    write_config('entries = ["mp/tdd"]\n')
    with pytest.raises(SkillGraftError, match=r"mp/tdd.*'mp'"):
        load()


@pytest.mark.parametrize("entry", ["tdd", "/tdd", "mp/", "mp/a/b"])
def test_malformed_entry(entry: str) -> None:
    write_config(f'entries = ["{entry}"]\n')
    with pytest.raises(SkillGraftError, match=f"'{entry}'"):
        load()
