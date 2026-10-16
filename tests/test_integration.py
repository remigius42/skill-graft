"""Runs the real `apm` from the dev group, with `HOME` a temporary directory."""

import shutil
from pathlib import Path

import pytest
from conftest import skill

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
