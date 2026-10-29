"""Finding hidden characters in a skill's files and names (the `hidden-characters`
spec)."""

from pathlib import Path

import pytest
from conftest import skill

from skill_graft.pipeline import hidden


def test_tag_character_in_text(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd", "a\n" * 6 + "run \U000e0041 now\n")

    found, warnings = hidden.scan(folder)

    assert found == ["SKILL.md:7: U+E0041 (tag character)"]
    assert warnings == []


@pytest.mark.parametrize(
    ("char", "kind"),
    [
        (0xE0001, "tag character"),
        (0xE007F, "tag character"),
        (0x202A, "bidi control"),
        (0x202E, "bidi control"),
        (0x2066, "bidi control"),
        (0x2069, "bidi control"),
        (0xE0100, "variation selector"),
        (0xE01EF, "variation selector"),
    ],
)
def test_each_critical_class(tmp_path: Path, char: int, kind: str) -> None:
    folder = skill(tmp_path / "tdd", f"x{chr(char)}y\n")

    found, _ = hidden.scan(folder)

    assert found == [f"SKILL.md:1: U+{char:04X} ({kind})"]


@pytest.mark.parametrize("char", [0x202F, 0x2065, 0x206A, 0xE0080, 0xE00FF, 0xE01F0])
def test_neighbors_are_not_critical(tmp_path: Path, char: int) -> None:
    folder = skill(tmp_path / "tdd", f"x{chr(char)}y\n")

    found, _ = hidden.scan(folder)

    assert found == []


def test_in_a_nested_file(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd")
    (folder / "scripts").mkdir()
    (folder / "scripts" / "run.sh").write_text("echo \u202eok\n")

    found, _ = hidden.scan(folder)

    assert found == ["scripts/run.sh:1: U+202E (bidi control)"]


def test_in_a_file_name_shown_escaped(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd")
    (folder / "a\u202e-b.md").write_text("plain\n")

    found, _ = hidden.scan(folder)

    assert found == ["a\\u202e-b.md: its name holds U+202E (bidi control)"]


def test_in_a_folder_name_once(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd")
    (folder / "d\U000e0041").mkdir()
    (folder / "d\U000e0041" / "x\u202e.txt").write_text("plain\n")

    found, _ = hidden.scan(folder)

    assert found == [
        "d\\U000e0041: its name holds U+E0041 (tag character)",
        "d\\U000e0041/x\\u202e.txt: its name holds U+202E (bidi control)",
    ]


def test_text_of_an_escaped_path(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd")
    (folder / "x\u202e.txt").write_text("\U000e0041\n")

    found, _ = hidden.scan(folder)

    assert found == [
        "x\\u202e.txt: its name holds U+202E (bidi control)",
        "x\\u202e.txt:1: U+E0041 (tag character)",
    ]


def test_debris_warns_once_per_file(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd", "a\nb\nc\u200bd\ne\u200bf\n")

    found, warnings = hidden.scan(folder)

    assert found == []
    assert warnings == ["SKILL.md:3: 2 invisible characters, the first U+200B"]


@pytest.mark.parametrize(
    "char",
    [0x200B, 0x200D, 0x2060, 0x00AD, 0xFE00, 0xFE0E, 0x200E, 0x200F, 0x061C]
    + [0x2061, 0x2064, 0xFFF9, 0xFFFB, 0x206A, 0x206F],
)
def test_each_debris_class_warns(tmp_path: Path, char: int) -> None:
    folder = skill(tmp_path / "tdd", f"x{chr(char)}y\n")

    found, warnings = hidden.scan(folder)

    assert found == []
    assert warnings == [f"SKILL.md:1: 1 invisible character, the first U+{char:04X}"]


@pytest.mark.parametrize("char", [0xFE0F, 0x00A0, 0x2065, 0xFFFC, 0x2010])
def test_neighbors_do_not_warn(tmp_path: Path, char: int) -> None:
    folder = skill(tmp_path / "tdd", f"x{chr(char)}y\n")

    assert hidden.scan(folder) == ([], [])


TAG = "\U000e0041"


@pytest.mark.parametrize("data", [b"ok \xff\n", "\U000e0041\n".encode("utf-16")])
def test_markdown_not_utf8(tmp_path: Path, data: bytes) -> None:
    folder = skill(tmp_path / "tdd")
    (folder / "Guide.MD").write_bytes(data)

    found, _ = hidden.scan(folder)

    assert found == ["Guide.MD: not UTF-8, so its references cannot be read"]


@pytest.mark.parametrize(
    "codec", ["utf-16", "utf-16-le", "utf-16-be", "utf-32", "utf-32-le", "utf-32-be"]
)
def test_byte_order_mark(tmp_path: Path, codec: str) -> None:
    folder = skill(tmp_path / "tdd")
    (folder / "guide.txt").write_bytes(
        ("\ufeff" * (codec[-1] == "e") + f"a\n{TAG}\n").encode(codec)
    )

    found, _ = hidden.scan(folder)

    assert found == ["guide.txt:2: U+E0041 (tag character)"]


@pytest.mark.parametrize("name", ["SKILL.md", "data.txt"])
def test_nul_byte_does_not_switch_the_scan_off(tmp_path: Path, name: str) -> None:
    folder = skill(tmp_path / "tdd")
    (folder / name).write_bytes(f"a\0b\n{TAG}\n".encode())

    found, _ = hidden.scan(folder)

    assert found == [f"{name}:2: U+E0041 (tag character)"]


def test_one_invalid_byte_hides_nothing(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd")
    (folder / "notes.txt").write_bytes(b"\xff\n" + TAG.encode())

    found, _ = hidden.scan(folder)

    assert found == ["notes.txt:2: U+E0041 (tag character)"]


def test_binary_skipped(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd")
    (folder / "image.png").write_bytes(b"\x89PNG\0\xff" + "\u202e".encode())

    assert hidden.scan(folder) == ([], [])


def test_git_left_out(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd")
    (folder / ".git").mkdir()
    (folder / ".git" / f"x{TAG}").write_text(TAG)
    (folder / "sub").mkdir()
    (folder / "sub" / ".git").write_text(TAG)

    assert hidden.scan(folder) == ([], [])


def test_patch_with_a_nul_and_a_bad_byte(tmp_path: Path) -> None:
    data = b"\0 \xff\n+" + "\N{RIGHT-TO-LEFT OVERRIDE}".encode() + b"\n"

    found, _ = hidden.scan_patch("p.patch", data)

    assert found == ["p.patch:2: U+202E (bidi control)"]
