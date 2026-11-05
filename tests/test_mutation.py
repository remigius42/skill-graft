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
