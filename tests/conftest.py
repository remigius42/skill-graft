import io
import json
import os
import shutil
import signal
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import FrameType

import pytest

from skill_graft.cli import main
from skill_graft.infra import errors, paths
from skill_graft.infra.cache import Cache

# Stands in for `apm`: logs its argv and working folder, and for `install -g <path>`
# adds the path to ~/.apm/apm.yml the way APM 0.33.0 does, or for `install <path>`
# to ./apm.yml, unless told not to.
FAKE_APM = """\
import json, sys
from pathlib import Path

state_file = Path(__file__).with_name("state.json")
state = json.loads(state_file.read_text())
state["calls"].append(sys.argv[1:])
state["working_folders"].append(str(Path.cwd()))
state_file.write_text(json.dumps(state))
args = sys.argv[1:]
print("fake apm: " + " ".join(args))
if args[:2] == ["install", "-g"] and len(args) > 2:
    manifest, package = Path.home() / ".apm" / "apm.yml", args[2]
elif args[:1] == ["install"] and len(args) == 2:
    manifest, package = Path("apm.yml"), args[1]
else:
    manifest = None
if state["register"] and manifest is not None:
    manifest.parent.mkdir(parents=True, exist_ok=True)
    text = manifest.read_text() if manifest.exists() else "dependencies:\\n  apm:\\n"
    line = f"    - {package}\\n"
    if line not in text:
        text = text.replace("  apm:\\n", "  apm:\\n" + line, 1)
    manifest.write_text(text)
sys.exit(state["exit_code"])
"""


class FakeApm:
    def __init__(self, folder: Path) -> None:
        self._state = folder / "state.json"
        self._state.write_text(
            json.dumps(
                {"calls": [], "working_folders": [], "exit_code": 0, "register": True}
            )
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
    def working_folders(self) -> list[str]:
        working_folders = self._get("working_folders")
        assert isinstance(working_folders, list)
        return working_folders

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
    # Discovery walks up from the working folder and stops at home; from anywhere
    # else it could reach the developer's real ~/.apm/skill-graft.
    monkeypatch.chdir(home)
    # No developer git config (signing, insteadOf, default branch) reaches a test,
    # and no GIT_DIR or GIT_INDEX_FILE from a git hook running pytest: with those,
    # a test's git commands would write to this repository.
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    gitconfig = tmp_path / "gitconfig"
    gitconfig.write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "test@example.com")
    return home


@pytest.fixture
def scope(home: Path) -> paths.Scope:
    """The user scope, at the temporary home folder."""
    return paths.Scope(home)


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
    git = shutil.which("git")
    if git:
        (folder / "git").symlink_to(git)
    monkeypatch.setenv("PATH", str(folder))
    return FakeApm(folder)


class Upstream:
    """A synthetic upstream repository on branch `main`; its URL is its path.

    It serves partial clones, as GitHub does, unless `filters` is false.
    """

    def __init__(self, path: Path, sha256: bool = False, filters: bool = True) -> None:
        self.path = path
        self.url = str(path)
        path.mkdir(parents=True)
        object_format = ["--object-format=sha256"] if sha256 else []
        self.git("init", "-q", "-b", "main", *object_format)
        if filters:
            self.git("config", "uploadpack.allowFilter", "true")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", self.url, *args], capture_output=True, text=True, check=True
        ).stdout.strip()

    def commit(self, files: dict[str, str]) -> str:
        """Writes `files` (relative path to text) and commits; returns the sha."""
        for name, text in files.items():
            file = self.path / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(text)
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", "commit")
        return self.git("rev-parse", "HEAD")


def git_version() -> tuple[int, ...]:
    """The installed git's version, as `(2, 44)` for `git version 2.44.0`."""
    out = subprocess.run(["git", "--version"], capture_output=True, text=True).stdout
    return tuple(int(part) for part in out.split()[2].split(".")[:2])


# For tests of lookups never fetching: git honors GIT_NO_LAZY_FETCH from 2.44,
# and the git macOS ships is older.
no_lazy_fetch = pytest.mark.skipif(
    git_version() < (2, 44), reason="GIT_NO_LAZY_FETCH needs git 2.44"
)


def protocol_v0(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every git command speaks protocol v0, whose server refuses objects asked
    by name unless `uploadpack.allowAnySHA1InWant`."""
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.version")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "0")


def seed(upstream: Upstream, url: str, blobless: bool = False) -> Path:
    """Clones `upstream` into the cache as `url`'s repository, so `url` needs no
    fetch; whole, or `blobless`, with commits and trees only."""
    repo = Cache.default().repository(url)
    repo.parent.mkdir(parents=True, exist_ok=True)
    partial = ["--no-local", "--filter=blob:none"] if blobless else []
    upstream.git("clone", "-q", "--bare", *partial, upstream.url, str(repo))
    return repo


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


def make_patch(tmp_path: Path, before: dict[str, str], after: dict[str, str]) -> bytes:
    """`diff -ruN base/ edited/` for two folders holding these files."""
    for name, files in (("base", before), ("edited", after)):
        folder = tmp_path / "diff" / name
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)
        for path, text in files.items():
            (folder / path).parent.mkdir(parents=True, exist_ok=True)
            (folder / path).write_text(text)
    result = subprocess.run(
        ["diff", "-ruN", "base/", "edited/"],
        cwd=tmp_path / "diff",
        capture_output=True,
    )
    assert result.returncode == 1, result.stderr
    return result.stdout


def write_patch(name: str, data: bytes) -> None:
    """Writes `patches/<name>` in the package."""
    folder = Path.home() / ".apm" / "skill-graft" / "patches"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(data)


def configure(entries: list[str], **sources: str) -> None:
    """Writes a config with these entries and `alias = path` sources."""
    text = f"entries = {json.dumps(entries)}\n"
    for alias, path in sources.items():
        text += f'[sources.{alias}]\npath = "{path}"\n'
    write_config(text)


def build(capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    """Runs `skill-graft build --no-install`; returns its exit code and stderr,
    without the package line (`test_scope.py` checks that)."""
    code = main(["build", "--no-install"])
    return code, after_package_line(capsys.readouterr().err)


def after_package_line(err: str) -> str:
    """`err` without the `skill-graft: package: …` line a writing command starts
    with."""
    first, _, rest = err.partition("\n")
    return rest if first.startswith("skill-graft: package: ") else err


def vendored() -> set[str]:
    """The skill folders the last build left in `.apm/skills/`."""
    skills = Path.home() / ".apm" / "skill-graft" / ".apm" / "skills"
    return {p.name for p in skills.iterdir()} if skills.exists() else set()


class Blocked(Exception):
    """Not an `OSError`, so no handler in skill-graft can swallow it."""


@contextmanager
def deadline(seconds: int = 5) -> Iterator[None]:
    """Fails the block, rather than hanging, if it runs `seconds` (a FIFO, a device)."""

    def expire(signum: int, frame: FrameType | None) -> None:
        raise Blocked(f"still running after {seconds} s")

    previous = signal.signal(signal.SIGALRM, expire)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


class ClosedStdout(io.StringIO):
    """A stdout whose reader has closed it, its buffer too small for what is printed:
    every write and flush fails."""

    def write(self, text: str) -> int:
        raise BrokenPipeError(32, "Broken pipe")

    def flush(self) -> None:
        raise BrokenPipeError(32, "Broken pipe")


def closed_stdout(monkeypatch: pytest.MonkeyPatch) -> ClosedStdout:
    """Replaces stdout, in the test itself: `capsys` resets it once the test starts."""
    stdout = ClosedStdout()
    monkeypatch.setattr(sys, "stdout", stdout)
    return stdout


@pytest.fixture
def discards(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """Each stream a failed flush pointed at `os.devnull`; none really is."""
    streams: list[object] = []
    monkeypatch.setattr(errors, "_discard", streams.append)
    return streams
