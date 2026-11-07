"""`git.apply`: a patch applied to a folder, strictly, whatever git config is around."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from conftest import Upstream, make_patch, no_lazy_fetch

from skill_graft.infra import git
from skill_graft.infra.errors import SkillGraftError


def folder_with(tmp_path: Path, files: dict[str, str]) -> Path:
    folder = tmp_path / "work" / "copy"
    folder.mkdir(parents=True)
    for path, text in files.items():
        (folder / path).parent.mkdir(parents=True, exist_ok=True)
        (folder / path).write_text(text)
    return folder


def home_in(tmp_path: Path) -> Path:
    home = tmp_path / "work" / "home"
    home.mkdir(parents=True, exist_ok=True)
    return home


LINES = "".join(f"line {i}\n" for i in range(1, 11))


def test_applies(tmp_path: Path) -> None:
    patch = make_patch(
        tmp_path,
        {"SKILL.md": LINES},
        {"SKILL.md": LINES.replace("line 5\n", "line five\n")},
    )
    folder = folder_with(tmp_path, {"SKILL.md": LINES})

    ok, _ = git.apply(folder, patch, home_in(tmp_path))

    assert ok
    assert (folder / "SKILL.md").read_text() == LINES.replace("line 5\n", "line five\n")


def test_context_moved(tmp_path: Path) -> None:
    patch = make_patch(
        tmp_path,
        {"SKILL.md": LINES},
        {"SKILL.md": LINES.replace("line 8\n", "line eight\n")},
    )
    folder = folder_with(tmp_path, {"SKILL.md": "new 1\nnew 2\nnew 3\n" + LINES})

    ok, _ = git.apply(folder, patch, home_in(tmp_path))

    assert ok
    assert "line eight\n" in (folder / "SKILL.md").read_text()


def test_anchored_at_the_start(tmp_path: Path) -> None:
    patch = make_patch(
        tmp_path,
        {"SKILL.md": LINES},
        {"SKILL.md": LINES.replace("line 2\n", "line two\n")},
    )
    folder = folder_with(tmp_path, {"SKILL.md": "new\n" + LINES})

    ok, _ = git.apply(folder, patch, home_in(tmp_path))

    assert not ok
    assert (folder / "SKILL.md.rej").exists()


def test_config_in_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "apply.ignoreWhitespace")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "change")
    assert_whitespace_strict(tmp_path)

    monkeypatch.delenv("GIT_CONFIG_COUNT")
    monkeypatch.setenv("GIT_CONFIG_PARAMETERS", "'apply.ignorewhitespace'='change'")
    assert_whitespace_strict(tmp_path)


def test_user_git_config(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = "[apply]\n\tignoreWhitespace = change\n[core]\n\tautocrlf = true\n"
    (home / ".gitconfig").write_text(config)
    (home / ".config" / "git").mkdir(parents=True)
    (home / ".config" / "git" / "config").write_text(config)
    (tmp_path / "global").write_text(config)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "global"))

    assert_whitespace_strict(tmp_path)
    assert b"\r" not in (tmp_path / "work" / "copy" / "SKILL.md").read_bytes()


def test_enclosing_repository(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "apply.ignoreWhitespace", "change"],
        check=True,
    )

    assert_whitespace_strict(tmp_path)


def test_no_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = folder_with(tmp_path, {"SKILL.md": LINES})
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    with pytest.raises(SkillGraftError, match=r"\[patches\] needs git"):
        git.apply(folder, b"", home_in(tmp_path))


def test_failure_without_a_subcommand() -> None:
    with pytest.raises(SkillGraftError, match="^mp: `git ` failed"):
        git.run("-c", "a.b=c", "--literal-pathspecs", context="mp")


@no_lazy_fetch
def test_lookup_never_fetches(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    upstream.commit({"a.md": "a\n"})
    repo = tmp_path / "clone.git"
    upstream.git("clone", "-q", "--bare", "--filter=blob:none", upstream.url, str(repo))
    later = upstream.commit({"b.md": "b\n"})

    with pytest.raises(SkillGraftError):
        git.run("cat-file", "-e", f"{later}^{{commit}}", repo=repo, context="mp")

    lookup = subprocess.run(
        ["git", "--git-dir", str(repo), "cat-file", "-e", later],
        env=os.environ | {"GIT_NO_LAZY_FETCH": "1"},
        check=False,
    )
    assert lookup.returncode != 0


def assert_whitespace_strict(tmp_path: Path) -> None:
    """A hunk whose context differs only in spacing fails; added spaces stay."""
    shutil.rmtree(tmp_path / "work", ignore_errors=True)
    spaced = LINES.replace("line 5\n", "line five   \n")
    patch = make_patch(tmp_path, {"SKILL.md": LINES}, {"SKILL.md": spaced})
    folder = folder_with(tmp_path, {"SKILL.md": LINES})
    assert git.apply(folder, patch, home_in(tmp_path))[0]
    assert (folder / "SKILL.md").read_text() == spaced

    shutil.rmtree(tmp_path / "work")
    folder = folder_with(tmp_path, {"SKILL.md": LINES.replace("line 4\n", "line  4\n")})
    assert not git.apply(folder, patch, home_in(tmp_path))[0]


def test_failure_of_several_lines_is_one(tmp_path: Path) -> None:
    with pytest.raises(SkillGraftError) as failed:
        git.run("ls-remote", str(tmp_path / "missing"), context="mp")

    assert failed.value.lines == [str(failed.value)]
    assert "\n" not in str(failed.value)
    assert "fatal: " in str(failed.value) and "; " in str(failed.value)


def test_run_without_a_repository_uses_the_working_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"a.md": "a\n"})
    monkeypatch.chdir(upstream.path)

    assert git.run("rev-parse", "HEAD", context="mp").decode().strip() == sha


@no_lazy_fetch
def test_run_without_a_repository_lets_git_fetch_lazily(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"a.md": "a\n"})
    clone = tmp_path / "clone"
    upstream.git(
        "clone",
        "-q",
        "--no-checkout",
        "--no-local",
        "--filter=blob:none",
        upstream.url,
        str(clone),
    )
    monkeypatch.chdir(clone)

    assert git.run("cat-file", "-p", f"{sha}:a.md", context="mp") == b"a\n"


def test_failure_names_the_subcommand_past_options() -> None:
    with pytest.raises(SkillGraftError, match="^mp: `git no-such` failed"):
        git.run("--literal-pathspecs", "-c", "a.b=c", "no-such", context="mp")


def test_failure_of_undecodable_output(tmp_path: Path) -> None:
    repo = Path(os.fsdecode(os.fsencode(tmp_path) + b"/\xff"))

    with pytest.raises(SkillGraftError, match="�"):
        git.run("rev-parse", "HEAD", repo=repo, context="mp")


def test_apply_failure_of_undecodable_output(tmp_path: Path) -> None:
    patch = b"--- a/\xff.md\n+++ b/\xff.md\n@@ -1 +1 @@\n-a\n+b\n"
    folder = folder_with(tmp_path, {})

    ok, message = git.apply(folder, patch, home_in(tmp_path))

    assert not ok and "�" in message


def test_apply_says_nothing_of_whitespace(tmp_path: Path) -> None:
    patch = make_patch(
        tmp_path,
        {"SKILL.md": LINES},
        {"SKILL.md": LINES.replace("line 5\n", "line five   \n")},
    )
    folder = folder_with(tmp_path, {"SKILL.md": LINES})

    ok, message = git.apply(folder, patch, home_in(tmp_path))

    assert ok and "whitespace" not in message


def test_apply_reads_no_xdg_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    xdg = tmp_path / "xdg"
    (xdg / "git").mkdir(parents=True)
    (xdg / "git" / "config").write_text("[broken\n")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))

    assert_whitespace_strict(tmp_path)


def test_apply_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    envs: list[dict[str, str]] = []
    run = subprocess.run

    def recording(*args: Any, **kwargs: Any) -> Any:
        envs.append(kwargs["env"])
        return run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", recording)
    home = home_in(tmp_path)

    git.apply(folder_with(tmp_path, {}), b"", home)

    # Neither the system's config and attributes, which a test cannot write,
    # nor the user's, which `home` standing in for them would hide.
    (env,) = envs
    assert env["HOME"] == env["XDG_CONFIG_HOME"] == str(home)
    assert env["GIT_CONFIG_NOSYSTEM"] == env["GIT_ATTR_NOSYSTEM"] == "1"
