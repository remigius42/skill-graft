import io
import os
import sys

import pytest
from conftest import closed_stdout

from skill_graft.infra import errors
from skill_graft.infra.errors import SkillGraftError

WARNING = "skill-graft: warning: `own/tdd` calls `/foo`\n"


def test_closed_stdout_after_success_warns_then_fails(
    discards: list[object],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stdout = closed_stdout(monkeypatch)
    with pytest.raises(BrokenPipeError):
        with errors.warnings_last() as warnings:
            warnings.append("`own/tdd` calls `/foo`")
    assert capsys.readouterr().err == WARNING
    assert discards == [stdout]


def test_closed_stdout_keeps_the_commands_own_error(
    discards: list[object],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stdout = closed_stdout(monkeypatch)
    with pytest.raises(SkillGraftError, match="hidden characters"):
        with errors.warnings_last() as warnings:
            warnings.append("`own/tdd` calls `/foo`")
            raise SkillGraftError("hidden characters")
    assert capsys.readouterr().err == WARNING
    assert discards == [stdout]


def test_no_stdout_still_warns(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdout", None)
    with errors.warnings_last() as warnings:
        warnings.append("`own/tdd` calls `/foo`")
    assert capsys.readouterr().err == WARNING


def test_closed_stdout_reported_when_it_cannot_be_discarded(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(stdout: object) -> None:
        raise io.UnsupportedOperation("fileno")

    monkeypatch.setattr(errors, "_discard", fail)
    closed_stdout(monkeypatch)
    with pytest.raises(BrokenPipeError):
        with errors.warnings_last() as warnings:
            warnings.append("`own/tdd` calls `/foo`")
    assert capsys.readouterr().err == WARNING


def test_stdout_closed_by_python_still_warns(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stdout = io.TextIOWrapper(io.BytesIO())  # as Python's own: flushing it fails
    stdout.close()
    monkeypatch.setattr(sys, "stdout", stdout)
    with errors.warnings_last() as warnings:
        warnings.append("`own/tdd` calls `/foo`")
    assert capsys.readouterr().err == WARNING


def lowest_free_descriptor() -> int:
    descriptor = os.open(os.devnull, os.O_RDONLY)
    os.close(descriptor)
    return descriptor


def test_closed_stdout_without_a_descriptor_leaks_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed_stdout(monkeypatch)  # a StringIO: fileno() fails
    free = lowest_free_descriptor()
    with pytest.raises(BrokenPipeError):
        with errors.warnings_last():
            pass
    assert lowest_free_descriptor() == free
