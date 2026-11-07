"""The `edit` spec: `add`, `remove`, `rename`, `bind` and `unbind` change
skill-graft.toml in place."""

import tomllib
from pathlib import Path
from typing import Any, TypeAlias, cast

import pytest
import tomlkit
from conftest import (
    Upstream,
    after_package_line,
    make_patch,
    skill,
    snapshot,
    write_config,
    write_patch,
)

from skill_graft.cli import main
from skill_graft.commands import explain
from skill_graft.infra import paths
from skill_graft.infra.cache import Cache
from skill_graft.pipeline import lock

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
    notes = package(home) / ".apm" / "skills" / "notes" / "SKILL.md"
    assert notes.read_bytes() == (home / "mp" / "notes" / "SKILL.md").read_bytes()


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
    assert after_package_line(err) == ""
    assert "already" not in out


def test_add_reached_only_through_itself(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "see `x`\n")
    skill(home / "mp" / "x", "/y\n")
    skill(home / "mp" / "y", "/x\n")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)

    assert main(["add", "mp/x"]) == 0

    assert entries(home) == ["mp/tdd", "mp/x"]
    assert after_package_line(capsys.readouterr().err) == ""


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


PREFIXED = '[sources.mp]\npath = "~/mp"\nprefix = "mp-"\n'


def test_rename_opts_out_of_the_prefix(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd")
    config = write_config('entries = ["mp/tdd"]\n' + PREFIXED)

    assert main(["rename", "mp/tdd", "tdd"]) == 0

    assert config.read_text() == (
        'entries = ["mp/tdd"]\n' + PREFIXED + '\n[rename]\n"mp/tdd" = "tdd"\n'
    )
    assert capsys.readouterr().out == "mp/tdd\n"


def test_rename_back_to_the_prefix(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd")
    config = write_config(
        'entries = ["mp/tdd"]\n' + PREFIXED + '[rename]\n"mp/tdd" = "tdd"\n'
    )

    assert main(["rename", "mp/tdd", "mp-tdd"]) == 0

    assert config.read_text() == 'entries = ["mp/tdd"]\n' + PREFIXED + "[rename]\n"
    assert capsys.readouterr().out == "mp/tdd as mp-tdd\n"


def test_rename_to_the_prefixed_name(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd")
    config = write_config('entries = ["mp/tdd"]\n' + PREFIXED)
    before = config.read_bytes()

    assert main(["rename", "mp/tdd", "mp-tdd"]) == 0

    assert "`mp/tdd` already deploys as `mp-tdd`" in capsys.readouterr().err
    assert config.read_bytes() == before


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


def test_lock_write_interrupted(
    home: Path, capsys: Capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    mp_skills(home, "tdd", "notes")
    config = write_config('entries = ["mp/tdd"]\n' + SOURCES)
    assert main(["resolve"]) == 0
    lock_file = package(home) / "skill-graft.lock"
    skills = package(home) / ".apm" / "skills"
    before = (config.read_bytes(), lock_file.read_bytes())

    def interrupt(text: str, file: Path) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(lock, "write", interrupt)

    with pytest.raises(KeyboardInterrupt):
        main(["add", "mp/notes"])

    assert (config.read_bytes(), lock_file.read_bytes()) == before
    assert sorted(p.name for p in skills.iterdir()) == ["tdd"]
    assert sorted(p.name for p in skills.parent.iterdir()) == ["skills"]


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
    skills = package(home) / ".apm" / "skills"
    before = (config.read_bytes(), (package(home) / "skill-graft.lock").read_bytes())
    vendored = sorted(p.name for p in skills.iterdir())
    capsys.readouterr()

    assert main(["add", "mp/notes"]) == 1

    after = (config.read_bytes(), (package(home) / "skill-graft.lock").read_bytes())
    assert after == before
    assert sorted(p.name for p in skills.iterdir()) == vendored == ["tdd"]
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


TWO_SOURCES = SOURCES + '[sources.own]\npath = "~/own"\n'


def test_bind_new(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    mp_skills(home, "grilling")
    skill(home / "own" / "grill")
    config = write_config('entries = ["mp/tdd"]\n' + TWO_SOURCES)

    assert main(["bind", "mp/grilling", "own/grill"]) == 0

    assert config.read_text() == (
        'entries = ["mp/tdd"]\n'
        + TWO_SOURCES
        + '\n[bind]\n"mp/grilling" = "own/grill"\n'
    )
    assert capsys.readouterr().out == "mp/tdd\n└── own/grill (/grilling, bind)\n"


def test_bind_to_nothing(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/tmp\n")
    config = write_config('entries = ["mp/tdd"]\n' + SOURCES)
    assert main(["resolve"]) == 0
    assert "no declared source has a skill `tmp`" in capsys.readouterr().err

    assert main(["bind", "mp/tmp", "false"]) == 0

    assert tomllib.loads(config.read_text())["bind"] == {"mp/tmp": False}
    assert "tmp" not in after_package_line(capsys.readouterr().err)


def test_bind_replaced(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    mp_skills(home, "grilling")
    skill(home / "own" / "grill")
    text = 'entries = ["mp/tdd"]\n' + TWO_SOURCES + "[bind]\n"
    config = write_config(text + '"mp/grilling" = "own/grill"  # mine\n')

    assert main(["bind", "mp/grilling", "false"]) == 0

    assert config.read_text() == text + '"mp/grilling" = false  # mine\n'


@pytest.mark.parametrize(
    ("value", "target"), [('"own/grill"', "own/grill"), ("false", "false")]
)
def test_bind_already_so(home: Path, capsys: Capsys, value: str, target: str) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    skill(home / "own" / "grill")
    config = write_config(
        'entries = ["mp/tdd"]\n' + TWO_SOURCES + f'[bind]\n"mp/grilling" = {value}\n'
    )
    before = (config.read_bytes(), config.stat().st_mtime_ns)

    assert main(["bind", "mp/grilling", target]) == 0

    out, err = capsys.readouterr()
    assert out == ""
    assert f"`mp/grilling` is already bound to `{target}`" in err
    assert (config.read_bytes(), config.stat().st_mtime_ns) == before


def test_bind_already_so_but_gone(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    (home / "own").mkdir()
    config = write_config(
        'entries = ["mp/tdd"]\n' + TWO_SOURCES + '[bind]\n"mp/grilling" = "own/grill"\n'
    )
    before = config.read_bytes()

    assert main(["bind", "mp/grilling", "own/grill"]) == 1

    out, err = capsys.readouterr()
    assert (out, config.read_bytes()) == ("", before)
    assert "own/grill" in err and "already bound" not in err


@pytest.mark.parametrize(
    ("argv", "named"),
    [
        (["mp/grilling", "own/nope"], "own/nope"),
        (["zz/grilling", "own/grill"], "'zz'"),
        (["mp/grilling", "true"], "'true'"),
        (["mp", "own/grill"], "'mp'"),
    ],
)
def test_bind_refuses(home: Path, capsys: Capsys, argv: list[str], named: str) -> None:
    mp_skills(home, "tdd")
    skill(home / "own" / "grill")
    config = write_config('entries = ["mp/tdd"]\n' + TWO_SOURCES)
    before = config.read_bytes()

    assert main(["bind", *argv]) == 1

    out, err = capsys.readouterr()
    assert (out, config.read_bytes()) == ("", before)
    assert named in err


def test_bind_unused(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd")
    skill(home / "own" / "grill")
    config = write_config('entries = ["mp/tdd"]\n' + TWO_SOURCES)

    assert main(["bind", "mp/grill", "own/grill"]) == 0

    assert tomllib.loads(config.read_text())["bind"] == {"mp/grill": "own/grill"}
    assert '[bind] "mp/grill" binds no reference' in capsys.readouterr().err


def test_unbind(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    mp_skills(home, "grilling")
    skill(home / "own" / "grill")
    text = 'entries = ["mp/tdd"]\n' + TWO_SOURCES + "[bind]\n"
    config = write_config(text + '"mp/grilling" = "own/grill"\n')

    assert main(["unbind", "mp/grilling"]) == 0

    assert config.read_text() == text
    assert capsys.readouterr().out == "mp/tdd\n└── mp/grilling (/grilling)\n"


@pytest.mark.parametrize(
    ("key", "named", "bind"),
    [
        ("mp/grilling", "`mp/grilling` is not bound", ""),
        ("mp/grilling", "`mp/grilling` is not bound", '[bind]\n"mp/x" = false\n'),
        ("zz/grilling", "no source 'zz' is declared", ""),
        ("mp", "'mp' is not", ""),
    ],
)
def test_unbind_refuses(
    home: Path, capsys: Capsys, key: str, named: str, bind: str
) -> None:
    mp_skills(home, "tdd")
    config = write_config('entries = ["mp/tdd"]\n' + SOURCES + bind)
    before = config.read_bytes()

    assert main(["unbind", key]) == 1

    out, err = capsys.readouterr()
    assert (out, config.read_bytes()) == ("", before)
    assert named in err


def test_unbind_breaks_resolution(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/x\n")
    skill(home / "own" / "x")
    skill(home / "other" / "x")
    config = write_config(
        'entries = ["mp/tdd"]\n'
        + TWO_SOURCES
        + '[sources.other]\npath = "~/other"\n[bind]\n"mp/x" = "own/x"\n'
    )
    assert main(["resolve"]) == 0
    lock = package(home) / "skill-graft.lock"
    before = (config.read_bytes(), lock.read_bytes())

    assert main(["unbind", "mp/x"]) == 1

    assert "several sources" in capsys.readouterr().err
    assert (config.read_bytes(), lock.read_bytes()) == before


def other(tmp_path: Path, ref: bool = False) -> str:
    """A git source `other` whose remote does not exist: any fetch of it fails."""
    pinned = f'ref = "{"0" * 40}"\n' if ref else ""
    return f'[sources.other]\ngit = "{tmp_path / "nowhere"}"\n{pinned}'


@pytest.mark.parametrize("ref", [False, True], ids=["no ref", "unreachable"])
def test_rename_unknown_before_another_source(
    home: Path, tmp_path: Path, capsys: Capsys, ref: bool
) -> None:
    mp_skills(home, "tdd")
    config = write_config('entries = ["mp/tdd"]\n' + SOURCES + other(tmp_path, ref))
    before = config.read_bytes()

    assert main(["rename", "mp/nope", "x"]) == 1

    err = capsys.readouterr().err
    assert "mp/nope" in err and "'other'" not in err
    assert config.read_bytes() == before


@pytest.mark.parametrize("ref", [False, True], ids=["no ref", "unreachable"])
def test_bind_unknown_before_another_source(
    home: Path, tmp_path: Path, capsys: Capsys, ref: bool
) -> None:
    mp_skills(home, "tdd")
    skill(home / "own" / "grill")
    config = write_config('entries = ["mp/tdd"]\n' + TWO_SOURCES + other(tmp_path, ref))
    before = config.read_bytes()

    assert main(["bind", "mp/grilling", "own/nope"]) == 1

    err = capsys.readouterr().err
    assert "own/nope" in err and "'other'" not in err
    assert config.read_bytes() == before


def test_rename_known_but_another_without_ref(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    mp_skills(home, "tdd", "notes")
    config = write_config('entries = ["mp/tdd"]\n' + SOURCES + other(tmp_path))
    before = config.read_bytes()

    assert main(["rename", "mp/notes", "n"]) == 1

    err = capsys.readouterr().err
    assert "source 'other' has no ref: run `skill-graft update other`" in err
    assert config.read_bytes() == before


def test_rename_in_a_source_without_ref(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    config = write_config(
        'entries = ["mp/tdd"]\n'
        f'[sources.mp]\ngit = "{tmp_path / "mp-nowhere"}"\n' + other(tmp_path)
    )
    before = config.read_bytes()

    assert main(["rename", "mp/tdd", "t"]) == 1

    err = capsys.readouterr().err
    assert "sources 'mp', 'other' have no ref: run `skill-graft update mp other`" in err
    assert config.read_bytes() == before


def test_bind_already_so_ignores_another_missing_ref(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    mp_skills(home, "tdd")
    skill(home / "own" / "grill")
    config = write_config(
        'entries = ["mp/tdd"]\n'
        + TWO_SOURCES
        + other(tmp_path)
        + '[bind]\n"mp/grilling" = "own/grill"\n'
    )
    before = config.read_bytes()

    assert main(["bind", "mp/grilling", "own/grill"]) == 0

    assert "`mp/grilling` is already bound to `own/grill`" in capsys.readouterr().err
    assert config.read_bytes() == before


def fetchable(tmp_path: Path) -> tuple[str, Path]:
    """A git source `other` at a commit its reachable remote has but the cache
    lacks, and the cache repository a fetch of it would create."""
    upstream = Upstream(tmp_path / "other")
    sha = upstream.commit({"x/SKILL.md": "# x\n"})
    source = f'[sources.other]\ngit = "{upstream.url}"\nref = "{sha}"\n'
    return source, Cache.default().repository(upstream.url)


def test_rename_to_the_current_name_fetches_no_other_source(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    mp_skills(home, "tdd")
    source, repository = fetchable(tmp_path)
    config = write_config('entries = ["mp/tdd"]\n' + SOURCES + source)
    before = config.read_bytes()

    assert main(["rename", "mp/tdd", "tdd"]) == 0

    assert "`mp/tdd` already deploys as `tdd`" in capsys.readouterr().err
    assert config.read_bytes() == before
    assert not repository.exists()


def test_rename_reads_its_source_then_entries_clash(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    mp_skills(home, "tdd", "notes")
    skill(home / "own" / "tdd")
    source, repository = fetchable(tmp_path)
    config = write_config('entries = ["mp/tdd", "own/tdd"]\n' + TWO_SOURCES + source)
    before = config.read_bytes()

    assert main(["rename", "mp/notes", "n"]) == 1

    err = capsys.readouterr().err
    assert "mp/tdd" in err and "own/tdd" in err and "'other'" not in err
    assert config.read_bytes() == before
    assert not repository.exists()


def test_rename_reads_a_git_source_in_its_subdirectory(
    tmp_path: Path, capsys: Capsys
) -> None:
    upstream = Upstream(tmp_path / "cp")
    sha = upstream.commit(
        {"skills/tdd/SKILL.md": "# tdd\n", "outside/notes/SKILL.md": "# notes\n"}
    )
    config = write_config(
        'entries = ["cp/tdd"]\n'
        f'[sources.cp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
        'subdirectory = "skills"\n'
    )
    before = config.read_bytes()

    assert main(["rename", "cp/notes", "n"]) == 1
    assert "cp/notes" in capsys.readouterr().err
    assert config.read_bytes() == before

    assert main(["rename", "cp/tdd", "t"]) == 0
    assert tomllib.loads(config.read_text())["rename"] == {"cp/tdd": "t"}


DRY_RUN = "dry run: skill-graft.toml, skill-graft.lock and .apm/skills/ not written"


def test_dry_run_of_an_add(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    mp_skills(home, "grilling", "notes")
    write_config('entries = ["mp/notes"]\n' + SOURCES)
    assert main(["resolve"]) == 0
    before = snapshot(package(home))
    capsys.readouterr()

    assert main(["add", "mp/tdd", "--dry-run"]) == 0

    assert capsys.readouterr().out.splitlines() == [
        "hull (+ added, - removed, ~ changed):",
        "+ mp/grilling",
        "  SKILL.md (new, 8 bytes)",
        "+ mp/tdd",
        "  SKILL.md (new, 10 bytes)",
        "mp/notes",
        "mp/tdd",
        "└── mp/grilling (/grilling)",
        "review: skill-graft add mp/tdd --dry-run --diff-file <file>",
        DRY_RUN,
    ]
    assert snapshot(package(home)) == before


AMBIGUOUS = SOURCES + '[sources.a]\npath = "~/a"\n[sources.b]\npath = "~/b"\n'


def test_dry_run_of_a_failing_edit(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd")
    skill(home / "mp" / "notes", "/x\n")
    skill(home / "a" / "x")
    skill(home / "b" / "x")
    write_config('entries = ["mp/tdd"]\n' + AMBIGUOUS)
    assert main(["resolve"]) == 0
    before = snapshot(package(home))

    assert main(["add", "mp/notes", "--dry-run"]) == 1

    assert snapshot(package(home)) == before


def test_dry_run_with_an_edited_copy(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    mp_skills(home, "grilling")
    skill(home / "cp" / "grilling")
    write_config('entries = ["mp/tdd"]\n' + SOURCES + '[sources.cp]\npath = "~/cp"\n')
    assert main(["resolve"]) == 0
    (package(home) / ".apm" / "skills" / "tdd" / "SKILL.md").write_text("edited\n")
    capsys.readouterr()

    assert main(["bind", "mp/grilling", "cp/grilling", "--dry-run"]) == 1

    assert ".apm/skills/tdd" in capsys.readouterr().err


def uncached(tmp_path: Path, alias: str, files: dict[str, str]) -> str:
    """A git source `alias` at a commit its remote has but the cache lacks."""
    upstream = Upstream(tmp_path / alias)
    sha = upstream.commit(files)
    return f'[sources.{alias}]\ngit = "{upstream.url}"\nref = "{sha}"\n'


def test_dry_run_with_an_uncached_ref(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    write_config(uncached(tmp_path, "mp", {"tdd/SKILL.md": "# tdd\n"}))

    assert main(["add", "mp/tdd", "--dry-run"]) == 0

    assert "+ mp/tdd" in capsys.readouterr().out
    assert snapshot(paths.cache()) == {}


def test_dry_run_checking_its_target_first(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    mp_skills(home, "grilling")
    cp = uncached(tmp_path, "cp", {"grilling/SKILL.md": "# g\n"})
    write_config('entries = ["mp/tdd"]\n' + SOURCES + cp)

    assert main(["bind", "mp/grilling", "cp/grilling", "--dry-run"]) == 0

    assert snapshot(paths.cache()) == {}


def test_dry_run_already_in_the_hull(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "notes", "/tdd\n")
    mp_skills(home, "tdd")
    write_config('entries = ["mp/notes"]\n' + SOURCES)
    assert main(["resolve"]) == 0
    capsys.readouterr()

    assert main(["add", "mp/tdd", "--dry-run"]) == 0

    out, err = capsys.readouterr()
    assert "`mp/tdd` was already in the hull, via `mp/notes`" in err
    assert out.splitlines()[0] == "hull unchanged"
    assert out.splitlines()[-1] == DRY_RUN and "review:" not in out


def test_no_op_dry_run(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)

    assert main(["add", "mp/tdd", "--dry-run"]) == 0

    out, err = capsys.readouterr()
    assert out == "" and "`mp/tdd` is already an entry" in err


def test_patch_failing_in_a_dry_run(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    source = uncached(tmp_path, "mp", {"tdd/SKILL.md": "# changed\n"})
    write_patch(
        "tdd.patch",
        make_patch(tmp_path, {"SKILL.md": "# x\n"}, {"SKILL.md": "# x\nmore\n"}),
    )
    write_config(source + '[patches]\n"mp/tdd" = ["patches/tdd.patch"]\n')

    assert main(["add", "mp/tdd", "--dry-run"]) == 1

    err = capsys.readouterr().err
    keep = "run `skill-graft add mp/tdd` without `--dry-run` to keep what it fetched"
    assert f"mp/tdd: {keep}" in err and "update" not in err


def test_dry_run_of_a_bind_changing_text(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    mp_skills(home, "grilling")
    skill(home / "cp" / "grilling")
    write_config(
        'entries = ["mp/tdd"]\n' + SOURCES + '[sources.cp]\npath = "~/cp"\n'
        'prefix = "cp-"\n'
    )
    assert main(["resolve"]) == 0
    capsys.readouterr()

    assert main(["bind", "mp/grilling", "cp/grilling", "--dry-run"]) == 0

    assert capsys.readouterr().out.splitlines()[:6] == [
        "hull (+ added, - removed, ~ changed):",
        "+ cp/grilling",
        "  SKILL.md (new, 34 bytes)",
        "- mp/grilling",
        "~ mp/tdd",
        "  SKILL.md (changed, 10 -> 13 bytes)",
    ]


def test_dry_run_of_a_rename(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "---\nname: tdd\n---\n")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)
    assert main(["resolve"]) == 0
    capsys.readouterr()

    assert main(["rename", "mp/tdd", "mp-tdd", "--dry-run"]) == 0

    assert capsys.readouterr().out.splitlines()[:3] == [
        "hull (+ added, - removed, ~ changed):",
        "~ mp/tdd",
        "  SKILL.md (changed, 18 -> 21 bytes)",
    ]


def test_dry_run_of_a_first_add(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    mp_skills(home, "grilling")
    write_config(SOURCES)

    assert main(["add", "mp/tdd", "--dry-run"]) == 0

    assert capsys.readouterr().out.splitlines()[:5] == [
        "hull (+ added, - removed, ~ changed):",
        "+ mp/grilling",
        "  SKILL.md (new, 8 bytes)",
        "+ mp/tdd",
        "  SKILL.md (new, 10 bytes)",
    ]
    assert not (package(home) / ".apm").exists()


def test_plain_edit_prints_no_hull_diff(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd")
    write_config(SOURCES)

    assert main(["add", "mp/tdd"]) == 0

    assert capsys.readouterr().out == "mp/tdd\n"


def test_dry_run_quotes_a_removed_id(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd", "notes")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)
    assert main(["resolve"]) == 0
    copy = skill(package(home) / ".apm" / "skills" / "x")
    file = package(home) / "skill-graft.lock"
    document = tomlkit.parse(file.read_text())
    item = {"id": "mp/x\n\x1b", "entry": False, "deployed": "x", "upstream": "x"}
    cast(Any, document["skills"]).append(item | {"hash": lock.folder_hash(copy)})
    file.write_text(tomlkit.dumps(document))
    capsys.readouterr()

    assert main(["add", "mp/notes", "--dry-run"]) == 0

    assert '- "mp/x\\n\\033"' in capsys.readouterr().out.splitlines()
    assert main(["add", "mp/notes", "--dry-run", "--diff-file", "review.diff"]) == 0
    assert '# - "mp/x\\n\\033"\n' in (home / "review.diff").read_text()


HEADER = (
    "# skill-graft Deployed diff: each Skill's text as deployed, Patches and Renames"
    " applied,\n"
    "# the Vendored copies against what the edited config would vendor. Not what the"
    " Sources changed upstream. Untrusted text:\n"
    "# read it in an editor, not by printing it to a terminal.\n"
)


def test_diff_file(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    mp_skills(home, "grilling", "notes")
    write_config('entries = ["mp/notes"]\n' + SOURCES)
    assert main(["resolve"]) == 0
    capsys.readouterr()

    assert main(["add", "mp/tdd", "--dry-run", "--diff-file", "review.diff"]) == 0

    out = capsys.readouterr().out
    assert "+ mp/tdd" in out and "review:" not in out
    assert out.splitlines()[-1] == DRY_RUN
    assert (home / "review.diff").read_text() == HEADER + (
        "#   mp/notes\n"
        "# + mp/tdd\n"
        "# + └── mp/grilling (/grilling)\n"
        "# + mp/grilling\n"
        "# source mp: a path source\n"
        "diff --git a/SKILL.md b/SKILL.md\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/SKILL.md\n"
        "@@ -0,0 +1 @@\n"
        "+# skill\n"
        "# + mp/tdd\n"
        "# source mp: a path source\n"
        "diff --git a/SKILL.md b/SKILL.md\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/SKILL.md\n"
        "@@ -0,0 +1 @@\n"
        "+/grilling\n"
    )


def test_diff_file_of_a_removal(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "tdd's own text\n")
    mp_skills(home, "notes")
    write_config('entries = ["mp/notes", "mp/tdd"]\n' + SOURCES)
    assert main(["resolve"]) == 0

    assert main(["remove", "mp/tdd", "--dry-run", "--diff-file", "review.diff"]) == 0

    text = (home / "review.diff").read_text()
    assert text == HEADER + "#   mp/notes\n# - mp/tdd\n"


def test_diff_file_it_did_not_write(
    home: Path, capsys: Capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = home / "repo" / ".apm" / "skill-graft"
    package.mkdir(parents=True)
    (package / "skill-graft.toml").write_text("")
    (home / "repo" / "apm.yml").write_text("name: repo\n")
    monkeypatch.chdir(home / "repo")

    assert main(["add", "mp/tdd", "--dry-run", "--diff-file", "apm.yml"]) == 1

    err = capsys.readouterr().err
    assert "apm.yml" in err and "'mp'" not in err  # refused before resolving
    assert (home / "repo" / "apm.yml").read_text() == "name: repo\n"


def test_failed_edit_leaves_no_diff_file(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd")
    skill(home / "mp" / "notes", "/x\n")
    skill(home / "a" / "x")
    skill(home / "b" / "x")
    write_config('entries = ["mp/tdd"]\n' + AMBIGUOUS)
    (home / "review.diff").write_text(HEADER)

    assert main(["add", "mp/notes", "--dry-run", "--diff-file", "review.diff"]) == 1

    assert not (home / "review.diff").exists()


def test_refused_edit_leaves_no_diff_file(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)
    (home / "review.diff").write_text(HEADER)

    assert main(["remove", "mp/typo", "--diff-file", "review.diff"]) == 1

    assert "`mp/typo` is no entry" in capsys.readouterr().err
    assert not (home / "review.diff").exists()


def test_failure_after_the_writes_keeps_the_diff_file(
    home: Path, capsys: Capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    mp_skills(home, "tdd", "notes")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)
    assert main(["resolve"]) == 0

    def broken_pipe(hull: object) -> None:  # as `… | head -1` would
        raise BrokenPipeError

    monkeypatch.setattr(explain, "show", broken_pipe)

    assert main(["add", "mp/notes", "--diff-file", "review.diff"]) == 1

    assert entries(home) == ["mp/tdd", "mp/notes"]
    assert (home / "review.diff").read_text().startswith(HEADER)


def test_no_op_edit_keeps_the_diff_file(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)
    (home / "review.diff").write_text(HEADER + "earlier\n")

    assert main(["add", "mp/tdd", "--diff-file", "review.diff"]) == 0

    out, err = capsys.readouterr()
    assert out == "" and "`mp/tdd` is already an entry" in err
    assert (home / "review.diff").read_text() == HEADER + "earlier\n"


def test_diff_with_a_real_edit(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd", "notes")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)
    assert main(["resolve"]) == 0
    assert main(["add", "mp/notes", "--diff-file", "review.diff"]) == 0
    text = (home / "review.diff").read_text()
    assert text.startswith(HEADER + "#   mp/tdd\n# + mp/notes\n# + mp/notes\n")
    assert entries(home) == ["mp/tdd", "mp/notes"]


def test_diff_with_a_failing_lock_write(
    home: Path, capsys: Capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    mp_skills(home, "tdd", "notes")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)
    assert main(["resolve"]) == 0
    before = {p: content for p, (_, content, _) in snapshot(package(home)).items()}

    def fail(text: str, file: Path) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(lock, "write", fail)

    assert main(["add", "mp/notes", "--diff-file", "review.diff"]) == 1

    after = {p: content for p, (_, content, _) in snapshot(package(home)).items()}
    assert after == before
    assert not (home / "review.diff").exists()


def test_diff_file_with_a_lock_pointing_outside(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd", "notes")
    write_config('entries = ["mp/tdd"]\n' + SOURCES)
    assert main(["resolve"]) == 0
    skills = package(home) / ".apm" / "skills"
    (skills / "tdd").rename(skills.parent.parent / "outside")
    file = package(home) / "skill-graft.lock"
    document = tomlkit.parse(file.read_text())
    cast(Any, document["skills"])[0]["deployed"] = "../../outside"
    file.write_text(tomlkit.dumps(document))
    capsys.readouterr()

    assert main(["add", "mp/notes", "--dry-run", "--diff-file", "review.diff"]) == 0

    assert "+ mp/tdd" in capsys.readouterr().out.splitlines()


def git_tdd(tmp_path: Path) -> str:
    """Entry `mp/tdd` of a git source, resolved; its ref."""
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"tdd/SKILL.md": "---\nname: tdd\n---\n"})
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
    )
    assert main(["resolve"]) == 0
    return sha


def test_diff_file_quotes_the_locks_ref(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    sha = git_tdd(tmp_path)
    file = package(home) / "skill-graft.lock"
    file.write_text(file.read_text().replace(f'"{sha}"', '"X\\n+evil\\u001b"'))

    assert (
        main(["rename", "mp/tdd", "t", "--dry-run", "--diff-file", "review.diff"]) == 0
    )

    lines = (home / "review.diff").read_text().splitlines()
    assert f'# source mp: "X\\n+evil\\033" -> {sha}; upstream folder tdd' in lines


def test_diff_file_without_the_locks_ref(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    sha = git_tdd(tmp_path)
    file = package(home) / "skill-graft.lock"
    file.write_text(file.read_text().replace(f'ref = "{sha}"\n', ""))

    assert (
        main(["rename", "mp/tdd", "t", "--dry-run", "--diff-file", "review.diff"]) == 0
    )

    lines = (home / "review.diff").read_text().splitlines()
    assert f"# source mp: {sha}; upstream folder tdd" in lines


def bound_and_resolved(home: Path, bind: str = "") -> None:
    """Entries `mp/tdd`, which runs `/grilling`, and `mp/notes`; `own/grill`
    beside them; then `bind`; resolved."""
    skill(home / "mp" / "tdd", "/grilling\n")
    mp_skills(home, "grilling", "notes")
    skill(home / "own" / "grill")
    write_config('entries = ["mp/tdd", "mp/notes"]\n' + TWO_SOURCES + bind)
    assert main(["resolve"]) == 0


BOUND = '[bind]\n"mp/grilling" = "own/grill"\n'


@pytest.mark.parametrize(
    ("argv", "bind"),
    [
        (["remove", "mp/notes"], ""),
        (["rename", "mp/tdd", "t"], ""),
        (["bind", "mp/grilling", "own/grill"], ""),
        (["unbind", "mp/grilling"], BOUND),
    ],
)
def test_dry_run_hint_names_the_edit(
    home: Path, capsys: Capsys, argv: list[str], bind: str
) -> None:
    bound_and_resolved(home, bind)
    # A `~` for each: the hint follows a skill added or changed, not one removed.
    skill(home / "mp" / "tdd", "/grilling, edited\n")
    capsys.readouterr()

    assert main([*argv, "--dry-run"]) == 0

    hint = f"review: skill-graft {' '.join(argv)} --dry-run --diff-file <file>"
    assert hint in capsys.readouterr().out.splitlines()


@pytest.mark.parametrize(
    ("argv", "bind"),
    [(["bind", "mp/grilling", "own/grill"], ""), (["unbind", "mp/grilling"], BOUND)],
)
def test_diff_file_of_a_bind(home: Path, argv: list[str], bind: str) -> None:
    bound_and_resolved(home, bind)

    assert main([*argv, "--dry-run", "--diff-file", "review.diff"]) == 0

    assert (home / "review.diff").read_text().startswith(HEADER)


def test_remove_without_entries(home: Path, capsys: Capsys) -> None:
    mp_skills(home, "tdd")
    write_config(SOURCES)

    assert main(["remove", "mp/tdd"]) == 1

    assert "`mp/tdd` is no entry" in capsys.readouterr().err
