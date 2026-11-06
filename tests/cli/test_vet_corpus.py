"""graft-vet's corpus (the `graft-vet` spec, A corpus measures the Vet): `vet` over
its synthetic skills flags what their records say, and `score` reads a report file."""

import importlib.util
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from conftest import write_config

from skill_graft.cli import main

CORPUS = Path(__file__).parents[2] / "evals" / "graft-vet" / "corpus.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("corpus", CORPUS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


corpus = load()


def scanned(home: Path, capsys: pytest.CaptureFixture[str]) -> dict[str, set[object]]:
    """Each corpus skill's places `vet` flags, as `(file, line, category)`."""
    corpus.write(home / "c")
    names = ", ".join(f'"c/{skill.name}"' for skill in corpus.SKILLS)
    write_config(f'entries = [{names}]\n[sources.c]\npath = "~/c"\n')
    assert main(["vet"]) == 0
    flagged: dict[str, set[object]] = defaultdict(set)
    for line in capsys.readouterr().out.splitlines():
        skill, place, category, _, _ = line.split(" ")
        file, number = place.rsplit(":", 1)
        flagged[skill.removeprefix("c/")].add((file, int(number), category))
    return flagged


def test_the_scan_flags_what_the_records_say(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    flagged = scanned(home, capsys)

    differences = [
        difference
        for skill in corpus.SKILLS
        for difference in corpus.differences(skill, flagged.get(skill.name, set()))
    ]

    assert differences == []


def test_a_record_off_by_one_place_differs() -> None:
    skill = next(s for s in corpus.SKILLS if s.scan)
    place = next(iter(skill.scan))

    assert corpus.differences(skill, skill.scan - {place}) != []
    assert corpus.differences(skill, skill.scan | {("SKILL.md", 99, "run")}) != []


def test_an_evasion_stays_on_record() -> None:
    skill = corpus.SKILL["prose-fetch"]
    (line,) = [n for f, n, c in skill.labels if f == "SKILL.md" and c == "run"]

    assert skill.kind == "evasive"
    assert [p for p in skill.scan if p[:2] == ("SKILL.md", line)] == []


def test_every_kind_more_than_once() -> None:
    kinds = [skill.kind for skill in corpus.SKILLS]

    for kind in ("obvious", "evasive", "injected", "harmless"):
        assert kinds.count(kind) >= 2, kind


def places(skill: Any) -> list[Any]:
    """Every place of `skill`: core, trigger and injection line."""
    return [
        place for payload in skill.payloads for place in payload.core + payload.triggers
    ] + [place for injection in skill.injections for place in injection.lines]


def text(skill: Any, place: Any) -> str:
    """The text of `skill`'s line at `place`."""
    line: str = skill.files[place.file].split("\n")[place.line - 1]
    return line


def test_labels_follow_the_rule() -> None:
    # Each core place in each of its payload's categories, each trigger `run`.
    skill = corpus.SKILL["one-liner"]

    assert skill.labels == {
        ("setup.sh", 1, "run"),
        ("setup.sh", 1, "unreviewable"),
        ("SKILL.md", 3, "run"),
    }
    assert skill.attacks == "-"


def test_a_skill_of_two_harms_holds_two_payloads() -> None:
    skill = corpus.SKILL["quiet-step"]

    assert sorted(p.categories for p in skill.payloads) == [("permission",), ("send",)]
    assert skill.injections == ()


def test_a_whole_file_harm_is_whole() -> None:
    (payload,) = corpus.SKILL["blob"].payloads

    assert [(p.file, p.line, p.whole) for p in payload.core] == [("data.txt", 1, True)]
    assert [(p.file, p.whole) for p in payload.triggers] == [("SKILL.md", False)]


def test_places_lie_within_their_files() -> None:
    for skill in corpus.SKILLS:
        for place in places(skill):
            lines = skill.files[place.file].split("\n")
            assert 1 <= place.line <= len(lines), (skill.name, place)


def test_every_payload_has_a_core_place_and_a_category() -> None:
    for skill in corpus.SKILLS:
        for payload in skill.payloads:
            assert payload.core, (skill.name, payload.name)
            assert payload.categories, (skill.name, payload.name)
            assert set(payload.categories) <= set(corpus.CATEGORIES)


def test_a_twin_holds_its_payload_and_no_injection() -> None:
    for skill in corpus.SKILLS:
        for payload in skill.payloads:
            if payload.twin is None:
                continue
            twin = corpus.SKILL[payload.twin]
            assert twin.injections == (), twin.name
            (theirs,) = twin.payloads
            assert [text(twin, p) for p in theirs.core] == [
                text(skill, p) for p in payload.core
            ], (skill.name, payload.name)


def test_every_injected_skill_has_an_injection() -> None:
    for skill in corpus.SKILLS:
        if skill.kind == "injected":
            assert skill.injections, skill.name


def test_every_injection_line_is_labelled_permission() -> None:
    # Telling the reader to report nothing keeps something from the user.
    for skill in corpus.SKILLS:
        for injection in skill.injections:
            for place in injection.lines:
                assert (place.file, place.line, "permission") in skill.labels


def test_a_marker_is_found_only_in_its_injection() -> None:
    # Letters and spaces: no quote or backslash for JSON to escape, no comment
    # sign or key for a quote to drop.
    holders: dict[str, set[tuple[str, str, int]]] = defaultdict(set)
    for skill in corpus.SKILLS:
        for injection in skill.injections:
            assert re.fullmatch(r"[A-Za-z][A-Za-z ]*[A-Za-z]", injection.marker)
            holders[injection.marker] |= {
                (skill.name, p.file, p.line) for p in injection.lines
            }

    for skill in corpus.SKILLS:
        for file, content in skill.files.items():
            for number, line in enumerate(content.split("\n"), 1):
                for marker, lines in holders.items():
                    if marker in line:
                        assert (skill.name, file, number) in lines, marker


def test_labels_name_lines_the_skills_have() -> None:
    for skill in corpus.SKILLS:
        for file, line, category in skill.labels:
            assert category in corpus.CATEGORIES
            assert 1 <= line <= len(skill.files[file].split("\n")), (skill.name, file)
        assert (skill.kind == "harmless") == (not skill.labels), skill.name


def test_score(tmp_path: Path) -> None:
    obvious = corpus.SKILL["fetch-run"]
    (run,) = [p for p in obvious.labels if p[2] == "run"]
    harmless = corpus.SKILL["docs-link"]
    report = tmp_path / "report"
    report.write_text(
        "c/fetch-run steering 1 dropped 2\n"
        "c/docs-link no-reply steering 1\n"
        f"c/fetch-run {run[0]}:{run[1]} run ASI05 both run.pipe-to-shell\n"
        "c/fetch-run SKILL.md:1 privilege ASI03 reader\n"
        f"c/docs-link SKILL.md:{next(iter(harmless.scan))[1]} send LLM02,ASI02 scan send.url\n"
        # A reader agreeing with the scan where no label is: noise all the same.
        "c/tables SKILL.md:3 send LLM02,ASI02 both send.url\n"
    )

    done = subprocess.run(
        [sys.executable, "-I", str(CORPUS), "score", str(report)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert done.returncode == 0, done.stderr
    lines = done.stdout.splitlines()
    assert (
        "fetch-run obvious labels 2 scan 0 reader 0 both 1 missed 1"
        " unlabelled-reader 1 steering 1 dropped 2"
    ) in lines
    assert (
        "docs-link harmless labels 0 scan 0 reader 0 both 0 missed 0"
        " unlabelled-reader 0 no-reply steering 1"
    ) in lines
    assert (
        "tables harmless labels 0 scan 0 reader 0 both 0 missed 0"
        " unlabelled-reader 1 no status"
    ) in lines
    total = len(corpus.SKILLS)
    assert lines[-1].startswith(f"total skills {total} labels ")


def test_the_digest_follows_the_labels_not_the_record() -> None:
    skills = list(corpus.SKILLS)
    first = corpus.digest(skills)
    skill = corpus.SKILL["fetch-run"]
    (payload,) = skill.payloads
    relabelled = replace(skill, payloads=(replace(payload, categories=("run",)),))
    unrecorded = replace(skill, scan=frozenset())

    assert re.fullmatch(r"[0-9a-f]{12}", first)
    assert corpus.digest(list(reversed(skills))) == first
    assert corpus.digest([relabelled if s is skill else s for s in skills]) != first
    assert corpus.digest([unrecorded if s is skill else s for s in skills]) == first
