"""The opt-in mutation harness, `mutation/`: its tokenizer, operators, plugin and
verdict. The harness itself never runs in hooks or CI; these tests do."""

import importlib
import json
import os
import pkgutil
import re
import subprocess
import sys
from pathlib import Path

import pytest

import skill_graft
from mutation import __main__ as harness
from mutation import operators, plugin, targets


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


ROOT = Path(__file__).parents[1]


def run_plugin(
    tmp_path: Path, source: str, target: str | None = None, text: str = ""
) -> dict[str, object]:
    """The plugin's report of pytest run on `source`, with `text` patched in as
    `target`'s mutant, or nothing patched."""
    probe = tmp_path / "test_probe.py"
    probe.write_text(source)
    report = tmp_path / "report.json"
    env = {**os.environ, plugin.REPORT: str(report)}
    env.pop(plugin.MUTANT, None)
    if target is not None:
        env[plugin.MUTANT] = json.dumps({"target": target, "text": text})
    command = [sys.executable, "-m", "pytest", "-q", "-p", "mutation.plugin"]
    command += ["-p", "no:cacheprovider", str(probe)]
    subprocess.run(command, cwd=ROOT, env=env, capture_output=True, check=False)
    result: dict[str, object] = json.loads(report.read_text())
    return result


NAME_PROBE = """\
from skill_graft.pipeline import config, discovery

def test_dot():
    assert discovery.NAME.fullmatch("a.b")

def test_same_object():
    assert discovery.NAME is config.NAME
"""


def test_plugin_patches_a_pattern_under_every_name(tmp_path: Path) -> None:
    dropped_dot = "[A-Za-z0-9][A-Za-z0-9_-]*"

    assert run_plugin(tmp_path, NAME_PROBE)["failed"] == []
    assert run_plugin(tmp_path, NAME_PROBE, "config.NAME", dropped_dot) == {
        "failed": ["test_probe.py::test_dot"],
        "timing_only": False,
    }


WEB_TOOL_PROBE = """\
from skill_graft.pipeline import vet

def test_web_fetch():
    assert "send.web-tool" in vet._line("use WebFetch")
"""


def test_plugin_patches_a_vet_pattern(tmp_path: Path) -> None:
    target = "vet._PATTERNS:send.web-tool"

    assert run_plugin(tmp_path, WEB_TOOL_PROBE)["failed"] == []
    assert run_plugin(tmp_path, WEB_TOOL_PROBE, target, r"\bWeb(?:Search)\b") == {
        "failed": ["test_probe.py::test_web_fetch"],
        "timing_only": False,
    }


TIMING_PROBE = """\
import pytest
from skill_graft.pipeline import config

@pytest.mark.linear_time
def test_timed():
    assert config.NAME.fullmatch("a.b")
"""


def test_plugin_tells_a_kill_by_timing_tests_alone(tmp_path: Path) -> None:
    report = run_plugin(tmp_path, TIMING_PROBE, "config.NAME", "[A-Za-z0-9]*")

    assert report == {"failed": ["test_probe.py::test_timed"], "timing_only": True}


def test_every_target_resolves() -> None:
    for target in targets.TARGETS:
        assert isinstance(targets.resolve(target.name), re.Pattern), target.name
        assert all((ROOT / extra).is_file() for extra in target.extra), target.name


def test_targets_are_the_security_relevant_patterns() -> None:
    names = {target.name for target in targets.TARGETS}

    assert {"discovery.COMMENT", "config.NAME", "config.SCP"} <= names
    assert {"references.REFERENCE", "vet._TOKEN", "text.CRITICAL_CHARS"} <= names
    assert {"vet._PATTERNS:send.url", "hidden.WARNING_CHARS"} <= names
    assert not names & {"config.COUNT", "patch.HUNK", "apm.COMMENT", "discovery.NAME"}


CASE = "tests/cli/test_linear_time.py::test_pumped_input_takes_linear_time"


def target(name: str) -> targets.Target:
    return next(t for t in targets.TARGETS if t.name == name)


def test_selection_for_a_pattern_imported_by_name() -> None:
    assert harness.select(target("config.NAME")) == [
        "tests/commands/test_explain.py",
        "tests/pipeline/test_config.py",
        "tests/pipeline/test_discovery.py",
        "tests/commands/test_edit.py",
        f"{CASE}[config.NAME]",
    ]


def test_selection_skips_a_missing_test_file_and_adds_extras() -> None:
    # No `tests/infra/test_text.py`: `hidden` holds the pattern too.
    assert harness.select(target("text.CRITICAL_CHARS")) == [
        "tests/pipeline/test_hidden.py",
        "tests/pipeline/test_deployed.py",
        "tests/cli/test_hidden_characters.py",
        f"{CASE}[text.CRITICAL_CHARS]",
    ]


def test_selection_for_a_vet_pattern() -> None:
    assert harness.select(target("vet._PATTERNS:send.url")) == [
        "tests/pipeline/test_vet.py",
        "tests/cli/test_vet_corpus.py",
        f"{CASE}[vet._PATTERNS:send.url]",
    ]


def outcome(offset: int, status: str, confirmed: bool | None = None) -> harness.Outcome:
    mutant = operators.Mutant("drop-anchor", offset, f"m{offset}\u202e", 0)
    return harness.Outcome("config.NAME", mutant, status, confirmed)


def entry(offset: int) -> dict[str, object]:
    return {"operator": "drop-anchor", "offset": offset, "reason": "same"}


def test_verdict() -> None:
    outcomes = [
        outcome(1, "killed"),
        outcome(2, "timed out", confirmed=True),
        outcome(3, "timed out", confirmed=False),
        outcome(4, "timing only", confirmed=True),
        outcome(5, "timing only", confirmed=False),
        outcome(6, "survived"),
        outcome(7, "survived"),
    ]
    equivalent = {"config.NAME": [entry(6), entry(1), entry(9)]}

    lines, code = harness.verdict(outcomes, equivalent, {"config.NAME"})

    assert code == 1
    assert lines == [
        "survived: config.NAME drop-anchor at 3: 'm3\\u202e'",
        "survived: config.NAME drop-anchor at 5: 'm5\\u202e'",
        "survived: config.NAME drop-anchor at 7: 'm7\\u202e'",
        "stale: config.NAME drop-anchor at 1: killed",
        "stale: config.NAME drop-anchor at 9: no such mutant",
        "7 mutants: 3 killed, 1 equivalent, 3 survived",
    ]


def test_verdict_passes_when_every_survivor_is_listed() -> None:
    outcomes = [outcome(1, "killed"), outcome(6, "survived")]
    equivalent = {"config.NAME": [entry(6)], "config.SCP": [entry(1)]}

    lines, code = harness.verdict(outcomes, equivalent, {"config.NAME"})

    assert (lines, code) == (["2 mutants: 1 killed, 1 equivalent, 0 survived"], 0)


def test_verdict_counts_an_entry_of_no_target_or_no_mutants_stale() -> None:
    equivalent = {"config.GONE": [entry(1)], "config.REF": [entry(2)]}

    lines, code = harness.verdict([], equivalent, {"config.REF"})

    assert code == 1
    assert lines[:2] == [
        "stale: config.GONE drop-anchor at 1: no such mutant",
        "stale: config.REF drop-anchor at 2: no such mutant",
    ]


def test_failing_unpatched_run_stops_the_harness(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = []

    def run(tests: list[str], mutant: object, timeout: object) -> harness.Run:
        calls.append(mutant)
        return harness.Run(["tests/x.py::test_x"], False, 0.1)

    monkeypatch.setattr(harness, "run_pytest", run)

    assert harness.main(["config.REF"]) == 2
    assert calls == [None]
    assert "config.REF" in capsys.readouterr().err


def test_a_kill_by_timing_alone_is_run_again_alone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "equivalent.toml").write_text("")
    monkeypatch.setattr(harness, "EQUIVALENT", tmp_path / "equivalent.toml")
    runs: dict[object, int] = {}

    def run(tests: list[str], mutant: object, timeout: object) -> harness.Run:
        runs[mutant] = runs.get(mutant, 0) + 1
        if mutant is None:
            return harness.Run([], False, 0.1)
        return harness.Run(["t::timed"], True, 0.1)

    monkeypatch.setattr(harness, "run_pytest", run)

    assert harness.main(["config.REF"]) == 0
    mutants = [m for m in runs if m is not None]
    assert mutants and all(runs[m] == 2 for m in mutants)


def test_unknown_target(capsys: pytest.CaptureFixture[str]) -> None:
    assert harness.main(["config.NOPE"]) == 2
    assert "config.NOPE" in capsys.readouterr().err


def test_a_run_writing_no_report_stops_the_harness_with_2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def crashed(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(command, 3, b"crashed", b"")

    monkeypatch.setattr(subprocess, "run", crashed)

    with pytest.raises(SystemExit) as stopped:
        harness.run_pytest(["tests/x.py"], None, None)

    assert stopped.value.code == 2
