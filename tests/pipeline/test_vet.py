"""The `vet` spec's patterns: one skill's deployed files in, its flags out."""

from skill_graft.pipeline import vet


def flags(text: str, name: str = "SKILL.md") -> set[tuple[str, int, str]]:
    """The flags of a skill holding `text` in file `name`."""
    return {
        (flag.file, flag.line, flag.pattern)
        for flag in vet.scan({name: (text.encode(), False)})
    }


def test_categories_and_their_owasp_ids() -> None:
    assert vet.OWASP == {
        "read": ("LLM02",),
        "write": ("ASI02",),
        "send": ("LLM02", "ASI02"),
        "run": ("ASI05",),
        "privilege": ("ASI03",),
        "persistence": ("ASI06",),
        "permission": ("ASI02",),
        "unreviewable": ("LLM03",),
    }


def test_plain_prose_flags_nothing() -> None:
    assert flags("# tdd\n\nWrite the test first.\n") == set()


def test_binary_file() -> None:
    view = {"SKILL.md": (b"# x\n", False), "bin/tool": (b"\x7fELF\0\0\xff\xfe", False)}

    assert vet.scan(view) == [vet.Flag("bin/tool", 0, "unreviewable.binary")]


def test_utf16_file() -> None:
    view = {"notes.txt": ("plain\n".encode("utf-16"), False)}

    assert vet.scan(view) == [vet.Flag("notes.txt", 0, "unreviewable.encoding")]


def test_lenient_utf8_file() -> None:
    view = {"notes.txt": (b"caf\xe9\n", False)}

    assert vet.scan(view) == [vet.Flag("notes.txt", 0, "unreviewable.encoding")]
