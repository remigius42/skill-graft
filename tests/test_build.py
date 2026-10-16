from pathlib import Path

import pytest
from conftest import FakeApm, skill, write_config

from skill_graft.cli import main


def skills_dir(home: Path) -> Path:
    return home / ".apm" / "skill-graft" / ".apm" / "skills"


def test_whole_folder_copied(home: Path) -> None:
    source = skill(home / "src" / "chisel")
    (source / "refs").mkdir()
    (source / "refs" / "notes.md").write_bytes(b"notes\x00\xff")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 0

    vendored = skills_dir(home) / "chisel"
    assert (vendored / "SKILL.md").read_text() == "# skill\n"
    assert (vendored / "refs" / "notes.md").read_bytes() == b"notes\x00\xff"


def test_removed_entry(home: Path) -> None:
    skill(home / "src" / "chisel")
    skill(home / "src" / "tdd")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    main(["build", "--no-install"])
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 0

    assert sorted(p.name for p in skills_dir(home).iterdir()) == ["tdd"]


def test_copy_fails(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill(home / "src" / "chisel")
    broken = skill(home / "src" / "tdd")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    main(["build", "--no-install"])
    (broken / "dangling").symlink_to(home / "nowhere")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 1

    assert "dangling" in capsys.readouterr().err
    assert sorted(p.name for p in skills_dir(home).iterdir()) == ["chisel"]
    assert not (skills_dir(home).parent / "skills.new").exists()


def test_clash_across_sources(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "own" / "tdd")
    skill(home / "own" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/own"\n')
    main(["build", "--no-install"])
    write_config(
        'entries = ["mp/tdd", "own/tdd"]\n'
        '[sources.mp]\npath = "~/mp"\n[sources.own]\npath = "~/own"\n'
    )

    assert main(["build", "--no-install"]) == 1

    err = capsys.readouterr().err
    assert "mp/tdd" in err and "own/tdd" in err
    assert sorted(p.name for p in skills_dir(home).parent.iterdir()) == ["skills"]
    assert sorted(p.name for p in skills_dir(home).iterdir()) == ["chisel"]


def test_git_metadata_is_not_vendored(home: Path) -> None:
    source = skill(home / "chisel")
    (source / ".git").mkdir()
    (source / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/chisel"\n')

    assert main(["build", "--no-install"]) == 0

    assert sorted(p.name for p in (skills_dir(home) / "chisel").iterdir()) == [
        "SKILL.md"
    ]


def test_deploy_folder_warning_is_printed(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill(home / ".agents" / "skills" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/.agents/skills"\n')

    assert main(["build", "--no-install"]) == 0

    assert "warning: source 'own'" in capsys.readouterr().err


def test_no_install_does_not_run_apm(home: Path, fake_apm: FakeApm) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 0

    assert (skills_dir(home) / "chisel" / "SKILL.md").exists()
    assert fake_apm.calls == []
