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


def test_no_install_does_not_run_apm(home: Path, fake_apm: FakeApm) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 0

    assert (skills_dir(home) / "chisel" / "SKILL.md").exists()
    assert fake_apm.calls == []


def build_one_skill(home: Path) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')


def test_apm_succeeds(home: Path, fake_apm: FakeApm) -> None:
    build_one_skill(home)

    assert main(["build"]) == 0

    assert fake_apm.calls == [["install", "-g", str(home / ".apm" / "skill-graft")]]


def test_apm_exits_non_zero(
    home: Path, fake_apm: FakeApm, capsys: pytest.CaptureFixture[str]
) -> None:
    build_one_skill(home)
    fake_apm.exit_code = 7

    assert main(["build"]) == 1

    assert "exit code 7" in capsys.readouterr().err


def test_apm_missing(
    home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    build_one_skill(home)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    assert main(["build"]) == 1

    assert "APM is not installed" in capsys.readouterr().err
    assert (skills_dir(home) / "chisel").exists()


@pytest.mark.parametrize("manifest", [None, "dependencies:\n  apm:\n    - /other\n"])
def test_package_not_registered(
    home: Path,
    fake_apm: FakeApm,
    capsys: pytest.CaptureFixture[str],
    manifest: str | None,
) -> None:
    build_one_skill(home)
    fake_apm.register = False
    if manifest is not None:
        (home / ".apm" / "apm.yml").write_text(manifest)

    assert main(["build"]) == 1

    err = capsys.readouterr().err
    assert str(home / ".apm" / "apm.yml") in err
    assert str(home / ".apm" / "skill-graft") in err


@pytest.mark.parametrize(
    "item",
    [
        "- ~/.apm/skill-graft",
        "- '~/.apm/skill-graft/'",
        '- "{package}"',
        "- path: {package}",
        "- path: ~/.apm/skill-graft # pinned",
    ],
)
def test_listed_forms(home: Path, fake_apm: FakeApm, item: str) -> None:
    build_one_skill(home)
    fake_apm.register = False
    line = item.format(package=home / ".apm" / "skill-graft")
    (home / ".apm" / "apm.yml").write_text(f"dependencies:\n  apm:\n    {line}\n")

    assert main(["build"]) == 0


def test_symlinked_home(
    home: Path, tmp_path: Path, fake_apm: FakeApm, monkeypatch: pytest.MonkeyPatch
) -> None:
    link = tmp_path / "link-home"
    link.symlink_to(home)
    monkeypatch.setenv("HOME", str(link))
    build_one_skill(link)
    fake_apm.register = False
    (home / ".apm" / "apm.yml").write_text(
        f"dependencies:\n  apm:\n    - {home / '.apm' / 'skill-graft'}\n"
    )

    assert main(["build"]) == 0


def test_registration_removed_by_hand(home: Path, fake_apm: FakeApm) -> None:
    build_one_skill(home)
    manifest = home / ".apm" / "apm.yml"
    manifest.write_text("dependencies:\n  apm:\n    - /other\n")

    assert main(["build"]) == 0

    assert f"- {home / '.apm' / 'skill-graft'}" in manifest.read_text()
