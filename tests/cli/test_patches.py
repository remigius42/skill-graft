"""The `patches` spec end to end: a skill's patches apply before its references are read."""

import os
from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import build, make_patch, skill, vendored, write_config, write_patch

from skill_graft.cli import main

Capsys: TypeAlias = pytest.CaptureFixture[str]


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

    assert code == 1
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


def test_context_changed(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    tdd_patched(home, tmp_path)
    (home / "mp" / "tdd" / "SKILL.md").write_text("# changed\n")

    assert main(["resolve"]) == 1

    err = capsys.readouterr().err
    assert "patches/tdd.patch: SKILL.md: hunk @@ -1 +1,2 @@ does not apply" in err
    assert f"redo it against {home / 'mp' / 'tdd'}" in err
    assert not (home / ".apm" / "skill-graft" / "skill-graft.lock").exists()


def test_two_skills_fail(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    for name in ("tdd", "notes"):
        skill(home / "mp" / name, "# changed\n")
        write_patch(
            f"{name}.patch",
            make_patch(tmp_path, {"SKILL.md": "# x\n"}, {"SKILL.md": "# x\nmore\n"}),
        )
    configure_patched(
        '"mp/tdd", "mp/notes"',
        '"mp/tdd" = ["patches/tdd.patch"]\n"mp/notes" = ["patches/notes.patch"]',
    )

    code, err = build(capsys)

    assert code == 1
    assert "patches/tdd.patch: SKILL.md: hunk" in err
    assert "patches/notes.patch: SKILL.md: hunk" in err


def test_another_error_after_a_patch_failure(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    tdd_patched(home, tmp_path)
    (home / "mp" / "tdd" / "SKILL.md").write_text("# changed\n")
    skill(home / "mp" / "notes", "Run /x.\n")
    (home / "own").mkdir()
    write_config(
        'entries = ["mp/tdd", "mp/notes"]\n[sources.mp]\npath = "~/mp"\n'
        '[sources.own]\npath = "~/own"\n[bind]\n"mp/x" = "own/x"\n'
        '[patches]\n"mp/tdd" = ["patches/tdd.patch"]\n'
    )

    code, err = build(capsys)

    assert code == 1
    assert err.index("patches/tdd.patch") < err.index("own/x")


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads any file")
def test_copy_error_after_a_patch_failure(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    tdd_patched(home, tmp_path)
    (home / "mp" / "tdd" / "SKILL.md").write_text("# changed\n")
    notes = skill(home / "mp" / "notes", "# tdd\n")
    secret = notes / "data.bin"
    secret.write_text("x")
    secret.chmod(0)
    configure_patched(
        '"mp/tdd", "mp/notes"',
        '"mp/tdd" = ["patches/tdd.patch"]\n"mp/notes" = ["patches/tdd.patch"]',
    )

    try:
        code, err = build(capsys)
    finally:
        secret.chmod(0o644)

    assert code == 1
    assert err.index("patches/tdd.patch: SKILL.md: hunk") < err.index(str(secret))
    assert "skill-graft-" not in err


def test_reached_only_through_a_failed_skill(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    skill(home / "mp" / "tdd", "# changed\nRun /grilling.\n")
    skill(home / "mp" / "grilling")
    write_patch(
        "tdd.patch",
        make_patch(tmp_path, {"SKILL.md": "# tdd\n"}, {"SKILL.md": "# tdd\nmore\n"}),
    )
    configure_patched(
        '"mp/tdd"', '"mp/tdd" = ["patches/tdd.patch"]\n[rename]\n"mp/grilling" = "g"'
    )

    code, err = build(capsys)

    assert code == 1
    assert "patches/tdd.patch" in err
    assert "warning" not in err


def test_patch_outside_the_hull(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    write_patch("notes.patch", b"--- a/SKILL.md\n")
    write_patch("old.patch", b"--- a/SKILL.md\n")
    configure_patched('"mp/tdd"', '"mp/notes" = ["patches/notes.patch"]')

    code, err = build(capsys)

    assert code == 0
    assert err == (
        'skill-graft: warning: [patches] "mp/notes" patches no skill in the hull\n'
    )


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
