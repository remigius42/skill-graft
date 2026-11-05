"""The opt-in mutation harness, `mutation/`: its tokenizer, operators, plugin and
verdict. The harness itself never runs in hooks or CI; these tests do."""

import importlib
import pkgutil
import re

import pytest

import skill_graft
from mutation import operators


def texts(pattern: str) -> list[str]:
    return [token.text for token in operators.tokenize(pattern)]


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        (r"a\.b\\", ["a", r"\.", "b", r"\\"]),
        (r"\bx\Z", [r"\b", "x", r"\Z"]),
        (r"[]a]b", ["[]a]", "b"]),
        (r"[^]\]-]c", [r"[^]\]-]", "c"]),
        (r"(?:a)(?P<n>b)(?P=n)", ["(?:", "a", ")", "(?P<n>", "b", ")", "(?P=n)"]),
        (
            r"(?=a)(?!b)(?<=c)(?<!d)(?>e)",
            [
                "(?=",
                "a",
                ")",
                "(?!",
                "b",
                ")",
                "(?<=",
                "c",
                ")",
                "(?<!",
                "d",
                ")",
                "(?>",
                "e",
                ")",
            ],
        ),
        ("a*?b++c?+", ["a", "*?", "b", "++", "c", "?+"]),
        (
            "a{3}b{2,5}?c{1,}+d{,4}",
            ["a", "{3}", "b", "{2,5}?", "c", "{1,}+", "d", "{,4}"],
        ),
        ("a{x}", ["a", "{", "x", "}"]),
        ("a|b|c", ["a", "|", "b", "|", "c"]),
        ("^a$", ["^", "a", "$"]),
    ],
)
def test_tokenize(pattern: str, expected: list[str]) -> None:
    assert texts(pattern) == expected


def test_token_kinds_and_offsets() -> None:
    tokens = operators.tokenize(r"(?<!x)[a-z]+\b|y")

    assert [(t.kind, t.offset) for t in tokens] == [
        ("lookaround", 0),
        ("literal", 4),
        ("close", 5),
        ("class", 6),
        ("quantifier", 11),
        ("anchor", 12),
        ("alternation", 14),
        ("literal", 15),
    ]


def every_string_pattern() -> list[str]:
    """Every compiled string pattern of a `skill_graft` module, and each string
    pattern of `vet._PATTERNS`: a superset of the harness's targets."""
    found = []
    for info in pkgutil.walk_packages(skill_graft.__path__, "skill_graft."):
        module = importlib.import_module(info.name)
        found += [
            value.pattern
            for value in vars(module).values()
            if isinstance(value, re.Pattern) and isinstance(value.pattern, str)
        ]
    vet = importlib.import_module("skill_graft.pipeline.vet")
    found += [test for test in vet._PATTERNS.values() if isinstance(test, str)]
    return found


def test_tokens_join_back_to_every_pattern() -> None:
    patterns = every_string_pattern()

    assert len(patterns) > 50
    for pattern in patterns:
        assert "".join(texts(pattern)) == pattern


def mutated(pattern: str, operator: str) -> list[tuple[int, str]]:
    return [
        (m.offset, m.text)
        for m in operators.mutants(re.compile(pattern))
        if m.operator == operator
    ]


@pytest.mark.parametrize(
    ("pattern", "operator", "expected"),
    [
        ("a+b*", "plus-to-star", [(1, "a*b*")]),
        ("a+b*", "star-to-plus", [(3, "a+b+")]),
        ("ab?c", "drop-optional", [(2, "abc")]),
        ("a++b", "plus-to-star", [(1, "a*+b")]),
        ("a{3}", "min-1", [(1, "a{2}")]),
        ("a{3}", "min+1", [(1, "a{4}")]),
        ("a{0}b", "min-1", []),
        ("a*+b", "drop-possessive", [(1, "a*b")]),
        ("(?>ab)c", "plain-atomic", [(0, "(?:ab)c")]),
        ("[a-cx]", "drop-class-item", [(1, "[x]"), (4, "[a-c]")]),
        ("[^a-cx]", "drop-class-item", [(2, "[^x]"), (5, "[^a-c]")]),
        ("[a-c]x", "negate-class", [(0, "[^a-c]x")]),
        ("[^a-c]x", "negate-class", [(0, "[a-c]x")]),
        ("[a-c-x]", "drop-class-item", [(1, "[-x]"), (4, "[a-cx]"), (5, "[a-c-]")]),
        (r"^a\bb$", "drop-anchor", [(0, r"a\bb$"), (2, "^ab$"), (5, r"^a\bb")]),
        ("(?<!x)a(?=b)", "drop-lookaround", [(0, "a(?=b)"), (7, "(?<!x)a")]),
        ("a|b|c", "drop-branch", [(0, "b|c"), (2, "a|c"), (4, "a|b")]),
        ("x(?:a|b)", "drop-branch", [(4, "x(?:b)"), (6, "x(?:a)")]),
    ],
)
def test_operator(pattern: str, operator: str, expected: list[tuple[int, str]]) -> None:
    assert mutated(pattern, operator) == expected


def test_both_bounds_moved_and_dropped() -> None:
    found = [m.text for m in operators.mutants(re.compile("a{3,4}"))]

    assert found == ["a{2,4}", "a{4,4}", "a{3,3}", "a{3,5}", "a{3,}"]


def test_mutants_that_do_not_compile_or_repeat_are_dropped() -> None:
    # `[]|a|a` does not compile; dropping either last branch gives `[a]|a`.
    found = [(m.operator, m.text) for m in operators.mutants(re.compile("[a]|a|a"))]

    assert found == [
        ("negate-class", "[^a]|a|a"),
        ("drop-branch", "a|a"),
        ("drop-branch", "[a]|a"),
    ]


def test_mutant_keeps_the_original_flags() -> None:
    (mutant,) = operators.mutants(re.compile("a+", re.IGNORECASE))

    assert mutant.compile().flags & re.IGNORECASE
    assert mutant.compile().fullmatch("")
