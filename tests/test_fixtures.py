import subprocess
from pathlib import Path

from conftest import FakeApm


def test_home_is_temporary(tmp_path: Path) -> None:
    assert Path.home().is_relative_to(tmp_path)


def test_fake_apm_records_argv_and_exits_with_chosen_code(fake_apm: FakeApm) -> None:
    fake_apm.exit_code = 3
    result = subprocess.run(["apm", "install", "-g"], check=False)
    assert result.returncode == 3
    assert fake_apm.calls == [["install", "-g"]]


def test_fake_apm_registers_the_path_it_is_given(fake_apm: FakeApm) -> None:
    package = Path.home() / ".apm" / "skill-graft"
    subprocess.run(["apm", "install", "-g", str(package)], check=True)
    manifest = (Path.home() / ".apm" / "apm.yml").read_text()
    assert f"    - {package}\n" in manifest


def test_fake_apm_can_skip_registering(fake_apm: FakeApm) -> None:
    fake_apm.register = False
    subprocess.run(["apm", "install", "-g", "/x"], check=True)
    assert not (Path.home() / ".apm" / "apm.yml").exists()
