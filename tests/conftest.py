import json
import sys
from pathlib import Path

import pytest

from skill_graft.cli import main

# Stands in for `apm`: logs its argv, and for `install -g <path>` adds the path to
# ~/.apm/apm.yml the way APM 0.33.0 does, unless told not to.
FAKE_APM = """\
import json, sys
from pathlib import Path

state_file = Path(__file__).with_name("state.json")
state = json.loads(state_file.read_text())
state["calls"].append(sys.argv[1:])
state_file.write_text(json.dumps(state))
args = sys.argv[1:]
print("fake apm: " + " ".join(args))
if state["register"] and args[:2] == ["install", "-g"] and len(args) > 2:
    manifest = Path.home() / ".apm" / "apm.yml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    text = manifest.read_text() if manifest.exists() else "dependencies:\\n  apm:\\n"
    line = f"    - {args[2]}\\n"
    if line not in text:
        text = text.replace("  apm:\\n", "  apm:\\n" + line, 1)
    manifest.write_text(text)
sys.exit(state["exit_code"])
"""


class FakeApm:
    def __init__(self, folder: Path) -> None:
        self._state = folder / "state.json"
        self._state.write_text(
            json.dumps({"calls": [], "exit_code": 0, "register": True})
        )

    def _get(self, key: str) -> object:
        return json.loads(self._state.read_text())[key]

    def _set(self, key: str, value: object) -> None:
        state = json.loads(self._state.read_text())
        state[key] = value
        self._state.write_text(json.dumps(state))

    @property
    def calls(self) -> list[list[str]]:
        calls = self._get("calls")
        assert isinstance(calls, list)
        return calls

    @property
    def exit_code(self) -> int:
        code = self._get("exit_code")
        assert isinstance(code, int)
        return code

    @exit_code.setter
    def exit_code(self, value: int) -> None:
        self._set("exit_code", value)

    @property
    def register(self) -> bool:
        return bool(self._get("register"))

    @register.setter
    def register(self, value: bool) -> None:
        self._set("register", value)


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def fake_apm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeApm:
    folder = tmp_path / "fake-apm"
    folder.mkdir()
    (folder / "fake_apm.py").write_text(FAKE_APM)
    script = folder / "apm"
    script.write_text(
        f'#!/bin/sh\nexec "{sys.executable}" "{folder}/fake_apm.py" "$@"\n'
    )
    script.chmod(0o755)
    monkeypatch.setenv("PATH", str(folder))
    return FakeApm(folder)


def write_config(text: str) -> Path:
    """Writes ~/.apm/skill-graft/skill-graft.toml and returns it."""
    path = Path.home() / ".apm" / "skill-graft" / "skill-graft.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def skill(folder: Path, text: str = "# skill\n") -> Path:
    """Writes a fixture skill: `folder` holding `SKILL.md`."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SKILL.md").write_text(text)
    return folder


def configure(entries: list[str], **sources: str) -> None:
    """Writes a config with these entries and `alias = path` sources."""
    text = f"entries = {json.dumps(entries)}\n"
    for alias, path in sources.items():
        text += f'[sources.{alias}]\npath = "{path}"\n'
    write_config(text)


def build(capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    """Runs `skill-graft build --no-install`; returns its exit code and stderr."""
    code = main(["build", "--no-install"])
    return code, capsys.readouterr().err


def vendored() -> set[str]:
    """The skill folders the last build left in `.apm/skills/`."""
    skills = Path.home() / ".apm" / "skill-graft" / ".apm" / "skills"
    return {p.name for p in skills.iterdir()} if skills.exists() else set()
