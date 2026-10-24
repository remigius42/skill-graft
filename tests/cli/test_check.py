"""The `graft-check` skill this repository ships (the `check` spec): its front matter,
and that installing it pulls in nothing else."""

import json
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


def agent(name: str) -> dict[str, object]:
    """The agent `name` that `skills/graft-check/<name>.json` defines for `--agents`."""
    agents = json.loads((SKILLS / "graft-check" / f"{name}.json").read_text())
    assert list(agents) == [name]
    definition = agents[name]
    assert isinstance(definition, dict)
    assert definition["description"] and definition["prompt"]
    return definition


def test_reader_only_reads() -> None:
    reader = agent("reader")

    assert reader["tools"] == ["Read", "Grep", "Glob"]
    prompt = str(reader["prompt"])
    for kind in ("missed", "false", "rewrite", "link", "wrong target"):
        assert f"**{kind}**" in prompt
    assert "at most 200 characters" in prompt and "means:" in prompt
    assert "line of the `upstream` file" in prompt and "vendored: " in prompt


def test_reader_answers_the_probe() -> None:
    prompt = str(agent("reader")["prompt"])

    assert "`probe`" in prompt and "`reader-ok`" in prompt
    report = prompt.index("## Report")
    assert prompt.index("`reader-ok`") < report
    assert "In `full` and `uses` mode, reply" in prompt[report:]
    assert "## Uses\n\nIn `full` and `uses` mode, find" in prompt


def commands(start: str) -> list[str]:
    """Each `sh` block of the skill's `SKILL.md` that starts with `start`."""
    text = (SKILLS / "graft-check" / "SKILL.md").read_text()
    blocks = [block.split("```")[0] for block in text.split("```sh\n")[1:]]
    return [
        " ".join(block.split()) for block in blocks if block.lstrip().startswith(start)
    ]


def test_every_claude_has_a_turn_and_budget_cap() -> None:
    probe, reader, patcher = commands("claude -p")

    assert "--max-turns 30 --max-budget-usd 1.0" in probe
    assert "--max-turns <reader-turns> --max-budget-usd <reader-budget-usd>" in reader
    assert (
        "--max-turns <patcher-turns> --max-budget-usd <patcher-budget-usd>" in patcher
    )


def test_skill_names_where_its_limits_come_from() -> None:
    text = " ".join((SKILLS / "graft-check" / "SKILL.md").read_text().split())

    assert "`[check]` in `skill-graft.toml`" in text
    for key, default in [
        ("reader-turns", "30"),
        ("reader-budget-usd", "1.0"),
        ("patcher-turns", "10"),
        ("patcher-budget-usd", "0.5"),
        ("readers-at-once", "4"),
    ]:
        assert f"`<{key}>`, else {default}" in text


def test_readers_run_at_most_readers_at_once() -> None:
    text = " ".join((SKILLS / "graft-check" / "SKILL.md").read_text().split())
    read, report = text.index("## 4. Read"), text.index("## 5. Report")
    fixes = text.index("## 6. Fixes")

    assert "in parallel" not in text
    assert "At most `<readers-at-once>` readers run at once" in text[read:report]
    assert "in batches of at most `<readers-at-once>`" in text[read:report]
    assert "start the next when one ends" not in text
    assert "`uses` mode, at most `<readers-at-once>` at once" in text[report:fixes]


def test_patcher_only_edits() -> None:
    patcher = agent("patcher")

    assert patcher["tools"] == ["Read", "Edit", "Write"]
    assert "edited/" in str(patcher["prompt"]) and "name:" in str(patcher["prompt"])


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
