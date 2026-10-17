"""The `patches` spec end to end: a skill's patches apply before its references are read."""

from pathlib import Path

import pytest
from conftest import build, make_patch, skill, vendored, write_config

Capsys = pytest.CaptureFixture[str]


def write_patch(name: str, data: bytes) -> None:
    folder = Path.home() / ".apm" / "skill-graft" / "patches"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(data)


def configure_patched(entries: str, patches: str, extra: str = "") -> None:
    write_config(
        f'entries = [{entries}]\n{extra}[sources.mp]\npath = "~/mp"\n'
        f"[patches]\n{patches}\n"
    )


def test_patch_adds_a_reference(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "# tdd\n")
    skill(home / "mp" / "grilling")
    write_patch(
        "tdd.patch",
        make_patch(
            tmp_path, {"SKILL.md": "# tdd\n"}, {"SKILL.md": "# tdd\nRun /grilling.\n"}
        ),
    )
    configure_patched('"mp/tdd"', '"mp/tdd" = ["patches/tdd.patch"]')

    assert build(capsys) == (0, "")

    assert vendored() == {"tdd", "grilling"}
    skills = home / ".apm" / "skill-graft" / ".apm" / "skills"
    assert (skills / "tdd" / "SKILL.md").read_text() == "# tdd\nRun /grilling.\n"
    assert (home / "mp" / "tdd" / "SKILL.md").read_text() == "# tdd\n"


def test_patch_removes_a_reference(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "# tdd\nRun /grilling.\n")
    skill(home / "mp" / "grilling")
    write_patch(
        "tdd.patch",
        make_patch(
            tmp_path, {"SKILL.md": "# tdd\nRun /grilling.\n"}, {"SKILL.md": "# tdd\n"}
        ),
    )
    configure_patched('"mp/tdd"', '"mp/tdd" = ["patches/tdd.patch"]')

    assert build(capsys) == (0, "")

    assert vendored() == {"tdd"}


def test_rename_on_top(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "# tdd\n")
    skill(home / "mp" / "grilling")
    write_patch(
        "tdd.patch",
        make_patch(
            tmp_path, {"SKILL.md": "# tdd\n"}, {"SKILL.md": "# tdd\nRun /grilling.\n"}
        ),
    )
    configure_patched(
        '"mp/tdd"',
        '"mp/tdd" = ["patches/tdd.patch"]\n[rename]\n"mp/grilling" = "mp-grilling"',
    )

    assert build(capsys) == (0, "")

    skills = home / ".apm" / "skill-graft" / ".apm" / "skills"
    assert (skills / "tdd" / "SKILL.md").read_text() == "# tdd\nRun /mp-grilling.\n"


def tdd_patched(home: Path, tmp_path: Path) -> None:
    """Entry `mp/tdd`, with a patch adding a line to its `SKILL.md`."""
    skill(home / "mp" / "tdd", "# tdd\n")
    write_patch(
        "tdd.patch",
        make_patch(tmp_path, {"SKILL.md": "# tdd\n"}, {"SKILL.md": "# tdd\nmore\n"}),
    )
    configure_patched('"mp/tdd"', '"mp/tdd" = ["patches/tdd.patch"]')


def test_upstream_checked_first(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    tdd_patched(home, tmp_path)
    (home / "secret").write_text("secret\n")
    (home / "mp" / "tdd" / "notes.md").symlink_to(home / "secret")

    code, err = build(capsys)

    assert code == 1
    assert f"{home / 'mp' / 'tdd' / 'notes.md'} points outside the skill" in err
    assert not list(tmp_path.rglob("work*"))


def test_not_utf8_named_by_upstream_path(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    tdd_patched(home, tmp_path)
    (home / "mp" / "tdd" / "notes.md").write_bytes(b"\xff\n")

    code, err = build(capsys)

    assert code == 0
    assert str(home / "mp" / "tdd" / "notes.md") in err
    assert "skill-graft-" not in err


def test_build_writes_nothing(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    tdd_patched(home, tmp_path)
    assert build(capsys)[0] == 0
    package = home / ".apm" / "skill-graft"
    lock_before = (package / "skill-graft.lock").read_bytes()
    (home / "mp" / "tdd" / "SKILL.md").write_text("# changed\n")

    code, err = build(capsys)

    assert code == 1
    assert "patches/tdd.patch" in err
    assert (package / "skill-graft.lock").read_bytes() == lock_before
    assert (
        package / ".apm" / "skills" / "tdd" / "SKILL.md"
    ).read_text() == "# tdd\nmore\n"


def test_no_git(
    home: Path, tmp_path: Path, capsys: Capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    tdd_patched(home, tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    code, err = build(capsys)

    assert code == 1
    assert "[patches] needs git" in err


def test_path_sources_without_patches(
    home: Path, tmp_path: Path, capsys: Capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    skill(home / "mp" / "tdd")
    configure_patched('"mp/tdd"', "")
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    assert build(capsys) == (0, "")
