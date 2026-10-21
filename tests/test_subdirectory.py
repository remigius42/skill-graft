"""A git source's `subdirectory`: the `config`, `git-sources`, `resolve` and `update`
specs, through the CLI."""

import tomllib
from pathlib import Path
from typing import Any, TypeAlias

import pytest
from conftest import Upstream, build, vendored, write_config

from skill_graft.cli import main

Capsys: TypeAlias = pytest.CaptureFixture[str]


def source(upstream: Upstream, ref: str, subdirectory: str, alias: str = "cp") -> str:
    return (
        f'[sources.{alias}]\ngit = "{upstream.url}"\nref = "{ref}"\n'
        f'subdirectory = "{subdirectory}"\n'
    )


def refused(capsys: Capsys, value: str) -> str:
    """`build`'s stderr for a git source with `subdirectory = <value>`, the TOML
    value as written; the source's URL names nothing, so git must never run."""
    write_config(
        'entries = ["cp/tdd"]\n'
        f'[sources.cp]\ngit = "/nowhere"\nref = "{"a" * 40}"\nsubdirectory = {value}\n'
    )
    code, err = build(capsys)
    assert code == 1
    assert not (Path.home() / ".cache").exists()
    return err


def test_subdirectory_not_a_string(capsys: Capsys) -> None:
    assert "'sources.cp.subdirectory' must be a string" in refused(capsys, "1")


@pytest.mark.parametrize(
    "value", ["../x", "a/../../x", "/etc", ".", "a/./b", "", "a//b", "a/"]
)
def test_subdirectory_leaving_the_repository(capsys: Capsys, value: str) -> None:
    assert "'sources.cp.subdirectory'" in refused(capsys, f'"{value}"')


@pytest.mark.parametrize("value", ['"a\\u0000b"', '"a\\nb"'])
def test_control_character(capsys: Capsys, value: str) -> None:
    err = refused(capsys, value)

    assert "'sources.cp.subdirectory'" in err and "Traceback" not in err


def test_subdirectory_into_a_package(capsys: Capsys) -> None:
    value = '"proj/.apm/skill-graft/.apm/skills"'

    assert "'sources.cp.subdirectory'" in refused(capsys, value)


def test_subdirectory_on_a_path_source(home: Path, capsys: Capsys) -> None:
    (home / "plugins").mkdir()
    write_config('[sources.own]\npath = "~/plugins"\nsubdirectory = "pstack/skills"\n')

    code, err = build(capsys)

    assert code == 1
    assert "'sources.own.subdirectory' is unsupported" in err


def not_at_the_ref(
    tmp_path: Path,
    capsys: Capsys,
    command: str,
    files: dict[str, str],
    subdirectory: str,
    link: tuple[str, str] | None = None,
) -> str:
    """`command`'s stderr for entry `cp/tdd` from a commit holding `files` (and the
    symlink `link`), read in `subdirectory`, after checking it failed and wrote
    nothing; the stderr names the alias and the sha."""
    upstream = Upstream(tmp_path / "up")
    upstream.commit(files)
    if link:
        (upstream.path / link[0]).symlink_to(link[1])
    sha = upstream.commit({})
    config = write_config(
        'entries = ["cp/tdd"]\n' + source(upstream, sha, subdirectory)
    )

    code = main([command] + (["--no-install"] if command == "build" else []))
    err = capsys.readouterr().err

    assert code == 1
    assert "'cp'" in err and f"'{subdirectory}'" in err and sha in err
    assert not (config.parent / "skill-graft.lock").exists()
    assert not (config.parent / ".apm").exists()
    return err


@pytest.mark.parametrize("command", ["build", "resolve"])
def test_missing_at_ref(tmp_path: Path, capsys: Capsys, command: str) -> None:
    files = {"pstack/tdd/SKILL.md": "x"}

    err = not_at_the_ref(tmp_path, capsys, command, files, "pstack/skills")

    assert "is not a folder" in err


def test_a_file_not_a_folder(tmp_path: Path, capsys: Capsys) -> None:
    files = {"pstack/skills": "a file"}

    err = not_at_the_ref(tmp_path, capsys, "build", files, "pstack/skills")

    assert "is not a folder" in err


def test_symlinked_subdirectory(tmp_path: Path, capsys: Capsys) -> None:
    files = {"plugins/pstack/tdd/SKILL.md": "x"}
    link = ("skills", "plugins")

    err = not_at_the_ref(tmp_path, capsys, "build", files, "skills/pstack", link)

    assert "runs through a symlink" in err


def resolved_lock(tmp_path: Path, capsys: Capsys) -> dict[str, Any]:
    """The lock `resolve` writes for `cp` read in `pstack/skills`, `pl` in
    `plugins/chisel`, a skill itself, and `mp` from the root, all of one commit."""
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit(
        {
            "pstack/skills/tdd/SKILL.md": "# tdd\n",
            "plugins/chisel/SKILL.md": "---\nname: chisel\n---\n",
            "skills/notes/SKILL.md": "# notes\n",
        }
    )
    config = write_config(
        'entries = ["cp/tdd", "pl/chisel", "mp/notes"]\n'
        + source(upstream, sha, "pstack/skills")
        + source(upstream, sha, "plugins/chisel", alias="pl")
        + f'[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
    )
    assert main(["resolve"]) == 0, capsys.readouterr().err
    return tomllib.loads((config.parent / "skill-graft.lock").read_text())


def test_subdirectory_recorded(tmp_path: Path, capsys: Capsys) -> None:
    sources = resolved_lock(tmp_path, capsys)["sources"]

    assert sources["cp"]["subdirectory"] == "pstack/skills"
    assert sources["pl"]["subdirectory"] == "plugins/chisel"
    assert "subdirectory" not in sources["mp"]


def test_upstream_under_a_subdirectory(tmp_path: Path, capsys: Capsys) -> None:
    skills = resolved_lock(tmp_path, capsys)["skills"]

    assert {s["id"]: s["upstream"] for s in skills} == {
        "cp/tdd": "pstack/skills/tdd",
        "pl/chisel": "plugins/chisel",
        "mp/notes": "skills/notes",
    }


@pytest.mark.parametrize("dry_run", [[], ["--dry-run"]])
def test_subdirectory_gone_upstream(
    tmp_path: Path, capsys: Capsys, dry_run: list[str]
) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"pstack/skills/tdd/SKILL.md": "# tdd\n"})
    upstream.git("rm", "-rq", "pstack")
    tip = upstream.commit({"other/skills/tdd/SKILL.md": "# tdd\n"})
    config = write_config(
        'entries = ["cp/tdd"]\n' + source(upstream, sha, "pstack/skills")
    )
    assert main(["resolve"]) == 0
    text, lock = config.read_text(), (config.parent / "skill-graft.lock").read_text()
    capsys.readouterr()

    code = main(["update", *dry_run])
    out, err = capsys.readouterr()

    assert code == 1
    assert tip in out
    assert "'cp'" in err and "'pstack/skills'" in err and tip in err
    assert config.read_text() == text
    assert (config.parent / "skill-graft.lock").read_text() == lock


def test_skill_outside_the_subdirectory(tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit(
        {"skills/a/SKILL.md": "Run /b.\n", ".claude/skills/b/SKILL.md": "# b\n"}
    )
    write_config('entries = ["x/a"]\n' + source(upstream, sha, "skills", alias="x"))

    code, err = build(capsys)

    assert code == 0 and vendored() == {"a"}
    assert "`x/a` calls `/b`: no declared source has a skill `b`" in err


def test_link_out_of_the_subdirectory(tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    upstream.commit({"skills/a/SKILL.md": "# a\n", "other/c/SKILL.md": "# c\n"})
    (upstream.path / "skills" / "more").symlink_to("../other")
    sha = upstream.commit({})
    write_config('entries = ["x/c"]\n' + source(upstream, sha, "skills", alias="x"))

    code, err = build(capsys)

    assert code == 1 and "x/c" in err and vendored() == set()


def test_shared_export(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit(
        {"x/skills/one/SKILL.md": "# one\n", "y/skills/two/SKILL.md": "# two\n"}
    )
    both = source(upstream, sha, "x/skills", alias="a") + source(
        upstream, sha, "y/skills", alias="b"
    )

    write_config('entries = ["a/one", "b/two"]\n' + both)
    assert build(capsys) == (0, "")
    assert vendored() == {"one", "two"}
    assert len(list((home / ".cache" / "skill-graft" / "trees").glob("*/*"))) == 1

    write_config('entries = ["a/two"]\n' + both)
    code, err = build(capsys)
    assert code == 1 and "a/two" in err


def test_why_names_the_upstream_folder(tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"pstack/skills/tdd/SKILL.md": "# tdd\n"})
    write_config('entries = ["cp/tdd"]\n' + source(upstream, sha, "pstack/skills"))

    assert main(["why", "cp/tdd"]) == 0
    last = capsys.readouterr().out.splitlines()[-1]

    folder = Path(last.removeprefix("upstream: "))
    assert folder.is_absolute() and folder.parts[-3:] == ("pstack", "skills", "tdd")
    assert (folder / "SKILL.md").read_text() == "# tdd\n"


def test_one_plugin_of_many(tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit(
        {
            "pstack/skills/tdd/SKILL.md": "# pstack tdd\n",
            "harness/skills/tdd/SKILL.md": "# harness tdd\n",
        }
    )
    config = write_config(
        'entries = ["cp/tdd"]\n' + source(upstream, sha, "pstack/skills")
    )

    assert build(capsys) == (0, "")

    assert vendored() == {"tdd"}
    tdd = config.parent / ".apm" / "skills" / "tdd" / "SKILL.md"
    assert tdd.read_text() == "# pstack tdd\n"
