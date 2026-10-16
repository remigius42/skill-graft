"""The `git-sources` spec, through `skill-graft build --no-install`."""

from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import Upstream, build, configure, skill, vendored, write_config

Capsys: TypeAlias = pytest.CaptureFixture[str]


def package_files(home: Path) -> set[Path]:
    package = home / ".apm" / "skill-graft"
    return {p for p in package.rglob("*") if ".apm" not in p.relative_to(package).parts}


def test_skill_from_git(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit(
        {"skills/tdd/SKILL.md": "# tdd\n", "skills/tdd/refs/x.md": "x\n"}
    )
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
    )
    before = package_files(home)

    assert build(capsys) == (0, "")

    tdd = home / ".apm" / "skill-graft" / ".apm" / "skills" / "tdd"
    assert (tdd / "SKILL.md").read_text() == "# tdd\n"
    assert (tdd / "refs" / "x.md").read_text() == "x\n"
    assert not (tdd / ".git").exists()
    assert (home / ".cache" / "skill-graft" / "repos").is_dir()
    assert package_files(home) == before


def test_build_reads_the_ref_not_the_tip(tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"tdd/SKILL.md": "old\n"})
    upstream.commit({"tdd/SKILL.md": "new\n"})
    config = write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
    )
    text = config.read_text()

    assert build(capsys) == (0, "")

    skills = config.parent / ".apm" / "skills"
    assert (skills / "tdd" / "SKILL.md").read_text() == "old\n"
    assert config.read_text() == text


def test_discovery_stays_inside_a_git_source(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    skill(home / "local" / "secret")
    upstream = Upstream(tmp_path / "up")
    upstream.commit({"skills/tdd/SKILL.md": "# tdd\n"})
    (upstream.path / "out").symlink_to(home / "local")
    (upstream.path / "in").symlink_to("skills")
    sha = upstream.commit({})
    git = f'[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'

    write_config('entries = ["mp/secret"]\n' + git)
    code, err = build(capsys)
    assert code == 1 and "mp/secret" in err

    write_config('entries = ["mp/tdd"]\n' + git)
    assert build(capsys) == (0, "")
    assert vendored() == {"tdd"}


@pytest.mark.parametrize("entries", ['["mp/tdd"]', '["own/chisel"]'])
def test_git_source_without_ref(
    home: Path, tmp_path: Path, capsys: Capsys, entries: str
) -> None:
    skill(home / "src" / "chisel")
    configure(["own/chisel"], own="~/src")
    build(capsys)
    upstream = Upstream(tmp_path / "up")
    upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    write_config(
        f"entries = {entries}\n"
        f'[sources.own]\npath = "~/src"\n[sources.mp]\ngit = "{upstream.url}"\n'
    )

    code, err = build(capsys)

    assert code == 1
    assert "'mp'" in err and "skill-graft update mp" in err
    assert vendored() == {"chisel"}
    assert not (home / ".cache").exists()
