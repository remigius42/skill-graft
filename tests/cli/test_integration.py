"""Runs the real `apm` from the dev group, with `HOME` a temporary directory."""

import shutil
from pathlib import Path

import pytest
from conftest import Upstream, skill

from skill_graft.cli import main

pytestmark = pytest.mark.skipif(shutil.which("apm") is None, reason="no apm on PATH")


def test_init_then_build_deploys_the_entry(home: Path) -> None:
    package = home / ".apm" / "skill-graft"
    skill(home / "src" / "chisel", "---\nname: chisel\ndescription: d\n---\nhi\n")

    assert main(["init"]) == 0
    (package / "skill-graft.toml").write_text(
        'entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n'
    )
    assert main(["build"]) == 0

    assert f"- {package}" in (home / ".apm" / "apm.yml").read_text()
    # No `targets:` in ~/.apm/apm.yml, so APM 0.33.0 deploys to ~/.agents/skills.
    assert (home / ".agents" / "skills" / "chisel" / "SKILL.md").exists()


def test_init_update_build_deploys_a_git_entry(home: Path, tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    upstream.commit({"skills/tdd/SKILL.md": "---\nname: tdd\ndescription: d\n---\n"})

    assert main(["init"]) == 0
    (home / ".apm" / "skill-graft" / "skill-graft.toml").write_text(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\n'
    )
    assert main(["update"]) == 0
    assert main(["build"]) == 0

    assert (home / ".agents" / "skills" / "tdd" / "SKILL.md").exists()


def test_init_project_then_build_deploys_it(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = home / "repo"
    (repo / ".claude").mkdir(parents=True)
    skill(repo / "src" / "chisel", "---\nname: chisel\ndescription: d\n---\nhi\n")
    monkeypatch.chdir(repo)
    assert main(["init", "--project"]) == 0
    (repo / ".apm" / "skill-graft" / "skill-graft.toml").write_text(
        'entries = ["own/chisel"]\n[sources.own]\npath = "../../src"\n'
    )
    monkeypatch.chdir(repo / "src")

    assert main(["build"]) == 0

    assert (repo / ".claude" / "skills" / "chisel" / "SKILL.md").exists()
    assert "- ./.apm/skill-graft" in (repo / "apm.yml").read_text()
    assert not (home / ".apm" / "skill-graft").exists()
    user_manifest = home / ".apm" / "apm.yml"
    assert not user_manifest.exists() or "skill-graft" not in user_manifest.read_text()
