"""The `graft-check` skill this repository ships (the `check` spec): its front matter,
and that installing it pulls in nothing else."""

import shutil
import tomllib
from pathlib import Path

import pytest
from conftest import Upstream, write_config

from skill_graft.cli import main

SKILLS = Path(__file__).parents[2] / "skills"


def front_matter() -> dict[str, str]:
    """The `key: value` lines between the `---` fences opening the skill's `SKILL.md`."""
    text = (SKILLS / "graft-check" / "SKILL.md").read_text()
    opening, block, _ = text.split("---\n", 2)
    assert opening == ""
    return dict(line.split(": ", 1) for line in block.splitlines())


def test_front_matter() -> None:
    fields = front_matter()

    assert fields["name"] == "graft-check"
    assert fields["disable-model-invocation"] == "true"
    assert "only when the user asks" in fields["description"]
    assert "<alias>/<name>" in fields["argument-hint"]


def test_alone_in_its_hull(
    home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A commit of the working tree's `skills/`, as a git source installs it: a
    # `SKILL.md` not yet staged counts, and discovery stays within the commit.
    upstream = Upstream(tmp_path / "sg")
    shutil.copytree(SKILLS, upstream.path / "skills")
    sha = upstream.commit({})
    write_config(
        'entries = ["sg/graft-check"]\n'
        f'[sources.sg]\ngit = "{upstream.url}"\nref = "{sha}"\nsubdirectory = "skills"\n'
    )

    code = main(["resolve"])

    out, err = capsys.readouterr()
    assert code == 0, err
    assert out == "sg/graft-check\n"
    assert "warning" not in err
    lock = tomllib.loads(
        (home / ".apm" / "skill-graft" / "skill-graft.lock").read_text()
    )
    assert [s["id"] for s in lock["skills"]] == ["sg/graft-check"]
    assert lock["suggestions"] == []
