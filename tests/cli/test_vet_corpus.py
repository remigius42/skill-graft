"""graft-vet's corpus (the `graft-vet` spec, A corpus measures the Vet): `vet` over
its synthetic skills flags what their records say, and `score` reads a report file."""

import importlib.util
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from types import ModuleType

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
    total = len(corpus.SKILLS)
    assert lines[-1].startswith(f"total skills {total} labels ")
