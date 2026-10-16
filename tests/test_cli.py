import subprocess


def test_help_lists_commands() -> None:
    result = subprocess.run(
        ["skill-graft", "--help"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0
    assert "init" in result.stdout
    assert "build" in result.stdout
