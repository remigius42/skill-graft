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
    with pytest.raises(BrokenPipeError), errors.warnings_last() as warnings:
        warnings.append("`own/tdd` calls `/foo`")
    assert capsys.readouterr().err == WARNING
    assert discards == [stdout]


def test_closed_stdout_keeps_the_commands_own_error(
    discards: list[object],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stdout = closed_stdout(monkeypatch)
    with (
        pytest.raises(SkillGraftError, match="hidden characters"),
        errors.warnings_last() as warnings,
    ):
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
    with pytest.raises(BrokenPipeError), errors.warnings_last() as warnings:
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


@pytest.mark.parametrize("failure", [ValueError, OSError])
def test_closed_stdout_reported_whatever_discarding_raises(
    monkeypatch: pytest.MonkeyPatch, failure: type[Exception]
) -> None:
    def fail(stdout: object) -> None:
        raise failure("no descriptor")

    monkeypatch.setattr(errors, "_discard", fail)
    closed_stdout(monkeypatch)

    with pytest.raises(BrokenPipeError):
        errors.flush_stdout()


def test_failed_flush_points_stdout_at_devnull(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    read, write = os.pipe()
    os.close(read)  # the reader gone
    with open(write, "w") as stdout:  # closing writes its rest to os.devnull
        stdout.write("lost")
        monkeypatch.setattr(sys, "stdout", stdout)

        with pytest.raises(BrokenPipeError):
            errors.flush_stdout()

        assert os.path.samestat(os.fstat(write), os.stat(os.devnull))


def lowest_free_descriptor() -> int:
    descriptor = os.open(os.devnull, os.O_RDONLY)
    os.close(descriptor)
    return descriptor


def test_closed_stdout_without_a_descriptor_leaks_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed_stdout(monkeypatch)  # a StringIO: fileno() fails
    free = lowest_free_descriptor()
    with pytest.raises(BrokenPipeError), errors.warnings_last():
        pass
    assert lowest_free_descriptor() == free


def test_error_keeps_its_lines() -> None:
    error = SkillGraftError("patches do not apply:", "  own/tdd: p.patch failed")

    assert error.lines == ["patches do not apply:", "  own/tdd: p.patch failed"]
    assert str(error) == "patches do not apply:\n  own/tdd: p.patch failed"


def test_error_of_one_message_is_one_line() -> None:
    error = SkillGraftError("own/tdd: gone")

    assert error.lines == ["own/tdd: gone"]
    assert str(error) == "own/tdd: gone"


def test_error_printed_with_hidden_characters_escaped(
    capsys: pytest.CaptureFixture[str],
) -> None:
    errors.print_error(SkillGraftError("own/tdd: a\n\x1b[31mok points outside", "hint"))

    assert capsys.readouterr().err == (
        "skill-graft: own/tdd: a\\n\\x1b[31mok points outside\nhint\n"
    )


def test_os_error_printed_as_one_escaped_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    errors.print_error(OSError("cannot read x\u202e\n.md"))

    assert capsys.readouterr().err == "skill-graft: cannot read x\\u202e\\n.md\n"


def test_warning_printed_on_one_escaped_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    errors.warn(["`own/a\nskill-graft: done` calls `/\x1b[2J foo`"])

    assert capsys.readouterr().err == (
        "skill-graft: warning: `own/a\\nskill-graft: done` calls `/\\x1b[2J foo`\n"
    )


def test_notice_printed_on_one_escaped_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    errors.notice("package: /tmp/a\n\x1b[31mb")

    assert capsys.readouterr().err == "skill-graft: package: /tmp/a\\n\\x1b[31mb\n"
