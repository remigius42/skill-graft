"""The `edit` spec: `add`, `remove` and `rename` change skill-graft.toml in place."""

import tomllib
from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import skill, write_config

from skill_graft.cli import main

Capsys: TypeAlias = pytest.CaptureFixture[str]


def package(home: Path) -> Path:
    return home / ".apm" / "skill-graft"


def entries(home: Path) -> list[str]:
    data = tomllib.loads((package(home) / "skill-graft.toml").read_text())
    result = data.get("entries", [])
    assert isinstance(result, list)
    return result


def test_add_succeeds(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "mp" / "notes")
    write_config('entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n')

    assert main(["add", "mp/notes"]) == 0

    assert entries(home) == ["mp/tdd", "mp/notes"]
    assert 'id = "mp/notes"' in (package(home) / "skill-graft.lock").read_text()
    assert capsys.readouterr().out == "mp/tdd\nmp/notes\n"
    assert not (package(home) / ".apm").exists()


def mp_skills(home: Path, *names: str) -> None:
    for name in names:
        skill(home / "mp" / name)


SOURCES = '[sources.mp]\npath = "~/mp"\n'


def test_add_appends_in_order(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd", "notes", "chisel")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)

    assert main(["add", "mp/chisel", "mp/notes", "mp/chisel"]) == 0

    assert entries(home) == ["mp/tdd", "mp/chisel", "mp/notes"]


def test_add_to_a_multi_line_array(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd", "grilling", "notes")
    config = write_config(
        'entries = [\n  "mp/tdd",  # first\n  "mp/grilling",\n]\n' + SOURCES
    )

    assert main(["add", "mp/notes"]) == 0

    assert config.read_text() == (
        'entries = [\n  "mp/tdd",  # first\n  "mp/grilling",\n  "mp/notes",\n]\n'
        + SOURCES
    )


def test_add_without_entries(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd")
    config = write_config("# my skills\n" + SOURCES)

    assert main(["add", "mp/tdd"]) == 0

    assert config.read_text() == '# my skills\nentries = ["mp/tdd"]\n\n' + SOURCES


@pytest.mark.parametrize(
    ("skill_id", "named"),
    [("mp/nope", "nope"), ("zz/tdd", "'zz'"), ("no-alias", "no-alias")],
)
def test_add_refuses(home: Path, capsys: Capsys, skill_id: str, named: str) -> None:
    mp_skills(home, "tdd", "notes")
    config = write_config('entries = ["mp/tdd"]\n' + SOURCES)
    before = config.read_bytes()

    assert main(["add", "mp/notes", skill_id]) == 1

    out, err = capsys.readouterr()
    assert (out, config.read_bytes()) == ("", before)
    assert named in err


def test_add_an_entry_again(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd")
    config = write_config('entries = ["mp/tdd"]\n' + SOURCES)
    before = (config.read_bytes(), config.stat().st_mtime_ns)

    assert main(["add", "mp/tdd"]) == 0

    out, err = capsys.readouterr()
    assert out == ""  # nothing resolved, nothing printed
    assert "`mp/tdd` is already an entry" in err
    assert (config.read_bytes(), config.stat().st_mtime_ns) == before
    assert not (package(home) / "skill-graft.lock").exists()


def test_add_partly_again(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd", "notes")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)

    assert main(["add", "mp/tdd", "mp/notes"]) == 0

    out, err = capsys.readouterr()
    assert entries(home) == ["mp/tdd", "mp/notes"]
    assert "`mp/tdd` is already an entry" in err
    assert out == "mp/tdd\nmp/notes\n"


def test_add_already_reachable(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    mp_skills(home, "grilling")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)

    assert main(["add", "mp/grilling"]) == 0

    assert entries(home) == ["mp/tdd", "mp/grilling"]
    assert "`mp/grilling` was already in the hull, via `mp/tdd`" in (
        capsys.readouterr().err
    )


def test_add_together(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd", "b")
    skill(home / "mp" / "a", "/b\n")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)

    assert main(["add", "mp/a", "mp/b"]) == 0

    out, err = capsys.readouterr()
    assert entries(home) == ["mp/tdd", "mp/a", "mp/b"]
    assert err == ""
    assert "already" not in out


def test_add_reached_only_through_itself(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "see `x`\n")
    skill(home / "mp" / "x", "/y\n")
    skill(home / "mp" / "y", "/x\n")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)

    assert main(["add", "mp/x"]) == 0

    assert entries(home) == ["mp/tdd", "mp/x"]
    assert capsys.readouterr().err == ""


def test_remove(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd", "notes")
    write_config('entries = ["mp/tdd", "mp/notes"]\n' + SOURCES)

    assert main(["remove", "mp/notes"]) == 0

    assert entries(home) == ["mp/tdd"]
    assert capsys.readouterr().out == "mp/tdd\n"


def test_remove_not_an_entry(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    mp_skills(home, "grilling")
    config = write_config('entries = ["mp/tdd"]\n' + SOURCES)
    before = config.read_bytes()

    assert main(["remove", "mp/grilling"]) == 1

    out, err = capsys.readouterr()
    assert (out, config.read_bytes()) == ("", before)
    assert "`mp/grilling` is no entry" in err


def test_remove_still_reachable(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    mp_skills(home, "grilling")
    write_config('entries = ["mp/tdd", "mp/grilling"]\n' + SOURCES)

    assert main(["remove", "mp/grilling"]) == 0

    assert entries(home) == ["mp/tdd"]
    assert "`mp/grilling` stays in the hull, via `mp/tdd`" in capsys.readouterr().err


def test_remove_names_no_circular_parent(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/y\n")
    skill(home / "mp" / "y", "/x\n")
    skill(home / "mp" / "x", "/z\n")
    skill(home / "mp" / "z", "/x\n")
    write_config('entries = ["mp/tdd", "mp/x"]\n' + SOURCES)

    assert main(["remove", "mp/x"]) == 0

    assert "`mp/x` stays in the hull, via `mp/y`" in capsys.readouterr().err


def test_remove_the_last_entry(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)

    assert main(["remove", "mp/tdd"]) == 0

    assert entries(home) == []
    lock = tomllib.loads((package(home) / "skill-graft.lock").read_text())
    assert lock.get("skills", []) == []
    assert capsys.readouterr().out == ""


def test_remove_keeps_other_comments(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "a", "b", "c")
    config = write_config(
        "# mine\n"
        'entries = [\n  "mp/a",  # keep a\n  "mp/b",  # goes\n  "mp/c",  # keep c\n]\n'
        + SOURCES
    )

    assert main(["remove", "mp/b"]) == 0

    text = config.read_text()
    assert entries(home) == ["mp/a", "mp/c"]
    assert "# mine" in text and "# keep a" in text and "# keep c" in text


def test_rename_new(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/code-review\n")
    mp_skills(home, "code-review")
    config = write_config('entries = ["mp/tdd"]\n' + SOURCES)

    assert main(["rename", "mp/code-review", "mp-code-review"]) == 0

    assert config.read_text() == (
        'entries = ["mp/tdd"]\n'
        + SOURCES
        + '\n[rename]\n"mp/code-review" = "mp-code-review"\n'
    )
    assert capsys.readouterr().out == (
        "mp/tdd\n└── mp/code-review as mp-code-review (/code-review)\n"
    )


@pytest.mark.parametrize(
    ("argv", "named"),
    [
        (["mp/nope", "x"], "mp/nope"),
        (["zz/tdd", "x"], "'zz'"),
        (["mp/tdd", "a/b"], "a/b"),
    ],
)
def test_rename_refuses(
    home: Path, capsys: Capsys, argv: list[str], named: str
) -> None:
    mp_skills(home, "tdd")
    config = write_config('entries = ["mp/tdd"]\n' + SOURCES)
    before = config.read_bytes()

    assert main(["rename", *argv]) == 1

    out, err = capsys.readouterr()
    assert (out, config.read_bytes()) == ("", before)
    assert named in err


def test_rename_to_the_current_name(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd")
    config = write_config(
        'entries = ["mp/tdd"]\n' + SOURCES + '[rename]\n"mp/tdd" = "mp-tdd"\n'
    )
    before = (config.read_bytes(), config.stat().st_mtime_ns)

    assert main(["rename", "mp/tdd", "mp-tdd"]) == 0

    out, err = capsys.readouterr()
    assert out == ""
    assert "`mp/tdd` already deploys as `mp-tdd`" in err
    assert (config.read_bytes(), config.stat().st_mtime_ns) == before


def test_rename_undone(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "code-review")
    config = write_config(
        'entries = ["mp/code-review"]\n'
        + SOURCES
        + '[rename]\n"mp/code-review" = "mp-code-review"  # avoid the built-in\n'
    )

    assert main(["rename", "mp/code-review", "code-review"]) == 0

    out, err = capsys.readouterr()
    assert (
        config.read_text() == 'entries = ["mp/code-review"]\n' + SOURCES + "[rename]\n"
    )
    assert out == "mp/code-review\n"
    assert "`code-review`, a name the harness already uses" in err


def test_rename_keeps_comments(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd")
    text = (
        "# my skills\n"
        'entries = ["mp/tdd"]  # one\n'
        + SOURCES
        + '\n[rename]\n"mp/tdd" = "mp-tdd"  # clashes otherwise\n'
    )
    config = write_config(text)

    assert main(["rename", "mp/tdd", "mp-tdd2"]) == 0

    assert config.read_text() == text.replace('"mp-tdd"', '"mp-tdd2"')


def test_rename_outside_the_hull(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd", "notes")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)

    assert main(["rename", "mp/notes", "n"]) == 0

    err = capsys.readouterr().err
    assert '"mp/notes" = "n"' in (package(home) / "skill-graft.toml").read_text()
    assert "warning" in err and "mp/notes" in err


@pytest.mark.parametrize(
    ("extra", "argv", "named"),
    [
        ("", ["own/x", "tdd"], "mp/tdd"),
        ('reserved = ["review"]\n', ["mp/check", "review"], "review"),
    ],
)
def test_rename_clashes(
    home: Path, capsys: Capsys, extra: str, argv: list[str], named: str
) -> None:
    mp_skills(home, "tdd", "check")
    skill(home / "own" / "x")
    config = write_config(
        extra
        + 'entries = ["mp/tdd", "mp/check", "own/x"]\n'
        + SOURCES
        + '[sources.own]\npath = "~/own"\n'
    )
    before = config.read_bytes()

    assert main(["rename", *argv]) == 1

    out, err = capsys.readouterr()
    assert (out, config.read_bytes()) == ("", before)
    assert named in err


def test_rename_onto_a_shipped_reserved_name(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "check")
    write_config('entries = ["mp/check"]\n' + SOURCES)

    assert main(["rename", "mp/check", "code-review"]) == 0

    toml = (package(home) / "skill-graft.toml").read_text()
    assert '"mp/check" = "code-review"' in toml
    assert "`code-review`, a name the harness already uses" in capsys.readouterr().err


def test_rename_missing_argument(home: Path, capsys: Capsys) -> None:
    with pytest.raises(SystemExit) as exit:
        main(["rename", "mp/tdd"])

    assert exit.value.code == 2
    assert "name" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("text", "argv", "named"),
    [
        (b"entries = [\n", ["add", "mp/tdd"], "skill-graft.toml"),
        (b"\xff\n", ["remove", "mp/tdd"], "skill-graft.toml"),
        (b'entries = "mp/tdd2"\n', ["add", "mp/tdd"], "entries"),
        (b'entries = "mp/tdd2"\n', ["remove", "mp/tdd"], "entries"),
    ],
)
def test_edit_refuses_a_broken_config(
    home: Path, capsys: Capsys, text: bytes, argv: list[str], named: str
) -> None:
    config = write_config("")
    config.write_bytes(text)

    assert main(argv) == 1

    out, err = capsys.readouterr()
    assert (out, config.read_bytes()) == ("", text)
    assert named in err and "Traceback" not in err


def test_edit_without_a_config(home: Path, capsys: Capsys) -> None:
    assert main(["add", "mp/tdd"]) == 1

    assert "run `skill-graft init`" in capsys.readouterr().err


def test_edit_keeps_the_config_when_the_lock_fails(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd", "notes")
    config = write_config('entries = ["mp/tdd"]\n' + SOURCES)
    before = config.read_bytes()
    (package(home) / "skill-graft.lock").mkdir()  # the lock cannot be replaced

    assert main(["add", "mp/notes"]) == 1

    assert config.read_bytes() == before


def test_edit_fails_to_resolve(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "mp" / "notes", "/x\n")
    for alias in ("a", "b"):
        skill(home / alias / "x")
    config = write_config(
        'entries = ["mp/tdd"]\n'
        '[sources.mp]\npath = "~/mp"\n[sources.a]\npath = "~/a"\n'
        '[sources.b]\npath = "~/b"\n'
    )
    assert main(["resolve"]) == 0
    before = (config.read_bytes(), (package(home) / "skill-graft.lock").read_bytes())
    capsys.readouterr()

    assert main(["add", "mp/notes"]) == 1

    after = (config.read_bytes(), (package(home) / "skill-graft.lock").read_bytes())
    assert after == before
    assert capsys.readouterr().out == ""


def test_symlinked_config(home: Path, capsys: Capsys) -> None:
    skill(home / "dotfiles" / "skills" / "tdd")
    skill(home / "dotfiles" / "skills" / "notes")
    package(home).mkdir(parents=True)
    target = home / "dotfiles" / "skill-graft.toml"
    # Relative to ~/.apm/skill-graft/, as `load` reads it, not to the link's target.
    target.write_text(
        'entries = ["s/tdd"]\n[sources.s]\npath = "../../dotfiles/skills"\n'
    )
    link = package(home) / "skill-graft.toml"
    link.symlink_to(target)

    assert main(["add", "s/notes"]) == 0

    assert link.is_symlink()
    assert 'entries = ["s/tdd", "s/notes"]' in target.read_text()
