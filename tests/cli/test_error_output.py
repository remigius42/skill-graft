"""The `cli` spec's "Error output shows no hidden characters" end to end: file
names a skill's author chose reach stderr escaped, whichever error names them."""

from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import configure, deploy, make_patch, skill, write_config, write_patch

Capsys: TypeAlias = pytest.CaptureFixture[str]


def patched(entries: str, patches: str) -> None:
    write_config(
        f'entries = [{entries}]\n[sources.mp]\npath = "~/mp"\n[patches]\n{patches}\n'
    )


def test_terminal_escape_in_a_link_name(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    (home / "secret").write_text("secret\n")
    (home / "mp" / "tdd" / "a\n\x1b[31mok").symlink_to(home / "secret")
    configure(["mp/tdd"], mp="~/mp")

    code, err = deploy(capsys)

    assert code == 1
    assert "/tdd/a\\n\\x1b[31mok points outside the skill" in err
    assert "\x1b" not in err and err.count("\n") == 1


@pytest.mark.needs_permissions
def test_unreadable_file_named_with_a_line_break(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    unreadable = home / "mp" / "tdd" / "a\nskill-graft: done"
    unreadable.write_text("x\n")
    unreadable.chmod(0)
    configure(["mp/tdd"], mp="~/mp")

    code, err = deploy(capsys)

    assert code == 1
    assert "a\\nskill-graft: done" in err
    assert not any(line.startswith("skill-graft: done") for line in err.splitlines())
    assert err.count("\n") == 1, repr(err)


def test_gits_message_holds_no_escape(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    skill(home / "mp" / "tdd")
    name = "gone\x1b[31m.md"
    write_patch("tdd.patch", make_patch(tmp_path, {name: "a\n"}, {name: "b\n"}))
    patched('"mp/tdd"', '"mp/tdd" = ["patches/tdd.patch"]')

    code, err = deploy(capsys)

    assert code == 1
    assert "patches/tdd.patch: git apply refused it" in err
    assert "\x1b" not in err


def test_lines_of_one_message_kept(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    lines = [f"line {n}\n" for n in range(1, 21)]
    before = "".join(lines)
    after = before.replace("line 2\n", "line 2b\n").replace("line 19\n", "line 19b\n")
    skill(home / "mp" / "tdd", before.replace("line 1\n", "x\n").replace("20", "y"))
    write_patch(
        "tdd.patch",
        make_patch(tmp_path, {"SKILL.md": before}, {"SKILL.md": after}),
    )
    patched('"mp/tdd"', '"mp/tdd" = ["patches/tdd.patch"]')

    code, err = deploy(capsys)

    assert code == 1
    shown = err.splitlines()
    assert shown[0] == "skill-graft: patches do not apply:"
    hunks = [line for line in shown if line.startswith("  mp/tdd: patches/tdd.patch")]
    assert len(hunks) == 2 and all("hunk @@" in line for line in hunks)


def test_safe_names_unchanged(home: Path, capsys: Capsys) -> None:
    skill(home / "My Skills" / "tdd")
    (home / "secret").write_text("secret\n")
    (home / "My Skills" / "tdd" / "notes.md").symlink_to(home / "secret")
    configure(["mp/tdd"], mp="~/My Skills")

    code, err = deploy(capsys)

    assert code == 1
    assert f"{home / 'My Skills' / 'tdd' / 'notes.md'} points outside the skill" in err
