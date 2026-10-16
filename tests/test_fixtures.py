from pathlib import Path


def test_home_is_temporary(tmp_path: Path) -> None:
    assert Path.home().is_relative_to(tmp_path)
