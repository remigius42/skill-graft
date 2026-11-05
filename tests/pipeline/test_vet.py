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
