"""`text.ranges`: a character class of code point ranges."""

from skill_graft.infra import text


def test_ranges_match_exactly_their_code_points() -> None:
    pattern = text.ranges([(ord("A"), ord("C")), (ord("a"), ord("b"))])

    assert [char for char in "ABCDXab-[]" if pattern.fullmatch(char)] == [
        "A",
        "B",
        "C",
        "a",
        "b",
    ]
