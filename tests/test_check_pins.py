import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "check_pins.py"

HOOKS = """\
default_language_version:
  node: 24.22.2
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: ad26ebfa797fcb9b8f83275937c1c1d6e126719c  # frozen: v2.4.1
    hooks:
      - id: mypy
        additional_dependencies:
          - pytest==9.1.1
          - tomlkit==0.15.2
  - repo: https://github.com/alessandrojcm/commitlint-pre-commit-hook
    rev: 1f1ac45c93d1c2ce36b71330252c489a5f4f2724  # frozen: v9.27.0
    hooks:
      - id: commitlint
        additional_dependencies:
          - "@commitlint/config-conventional@21.2.4"
"""

PYPROJECT = """\
[dependency-groups]
dev = [
  "apm-cli==0.35.0",
  "mypy==2.4.1",
  "pytest",
]
"""

README = """\
skill-graft runs APM, so `apm` must be on `PATH`, in version 0.35.0: the folders were
measured on it. Install it with `uv tool install apm-cli==0.35.0` or
`pipx install apm-cli==0.35.0`.
"""

UV_LOCK = """\
version = 1

[[package]]
name = "mypy"
version = "2.4.1"

[[package]]
name = "pytest"
version = "9.1.1"

[[package]]
name = "tomlkit"
version = "0.15.2"
"""

CI = """\
jobs:
  commitlint:
    steps:
      - uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0
        with:
          node-version: 24.22.2
"""

LOCK = {
    "packages": {
        "": {},
        "node_modules/@commitlint/config-conventional": {"version": "21.2.4"},
    }
}


def repository(root: Path) -> Path:
    """Writes a repository whose pins all match."""
    (root / ".github" / "commitlint").mkdir(parents=True)
    (root / ".github" / "workflows").mkdir()
    (root / ".pre-commit-config.yaml").write_text(HOOKS)
    (root / "pyproject.toml").write_text(PYPROJECT)
    (root / "README.md").write_text(README)
    (root / "uv.lock").write_text(UV_LOCK)
    (root / ".github" / "workflows" / "ci.yml").write_text(CI)
    lock = root / ".github" / "commitlint" / "package-lock.json"
    lock.write_text(json.dumps(LOCK))
    return root


def check(root: Path) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, SCRIPT, root], capture_output=True, text=True, check=False
    )
    return result.returncode, result.stdout + result.stderr


def edit(file: Path, old: str, new: str) -> None:
    text = file.read_text()
    assert old in text
    file.write_text(text.replace(old, new))


def test_matching_pins_pass(tmp_path: Path) -> None:
    assert check(repository(tmp_path)) == (0, "")


@pytest.mark.parametrize(
    ("file", "old", "new", "line"),
    [
        (
            "pyproject.toml",
            '"mypy==2.4.1"',
            '"mypy==2.4.0"',
            "mypy: 2.4.1 in the mypy hook's rev, 2.4.0 in pyproject.toml's dev group",
        ),
        (
            "uv.lock",
            'version = "9.1.1"',
            'version = "9.2.0"',
            "pytest: 9.1.1 in the mypy hook, 9.2.0 in uv.lock",
        ),
        (
            "uv.lock",
            'version = "0.15.2"',
            'version = "0.16.0"',
            "tomlkit: 0.15.2 in the mypy hook, 0.16.0 in uv.lock",
        ),
        (
            ".github/commitlint/package-lock.json",
            '"version": "21.2.4"',
            '"version": "21.3.0"',
            (
                "@commitlint/config-conventional: 21.2.4 in the commitlint hook,"
                " 21.3.0 in .github/commitlint/package-lock.json"
            ),
        ),
        (
            ".github/workflows/ci.yml",
            "node-version: 24.22.2",
            "node-version: 24.23.0",
            (
                "node: 24.22.2 in default_language_version,"
                " 24.23.0 in the commitlint job of .github/workflows/ci.yml"
            ),
        ),
        (
            ".pre-commit-config.yaml",
            "rev: ad26ebfa797fcb9b8f83275937c1c1d6e126719c  # frozen: v2.4.1",
            "rev: v2.5.0",
            "mypy: 2.5.0 in the mypy hook's rev, 2.4.1 in pyproject.toml's dev group",
        ),
        (
            "README.md",
            "in version 0.35.0",
            "in version 0.36.0",
            (
                "apm-cli: 0.36.0, 0.35.0, 0.35.0 in README.md,"
                " 0.35.0 in pyproject.toml's dev group"
            ),
        ),
        (
            "README.md",
            "pipx install apm-cli==0.35.0",
            "pipx install apm-cli==0.36.0",
            (
                "apm-cli: 0.35.0, 0.35.0, 0.36.0 in README.md,"
                " 0.35.0 in pyproject.toml's dev group"
            ),
        ),
        (
            "pyproject.toml",
            '"apm-cli==0.35.0"',
            '"apm-cli==0.36.0"',
            (
                "apm-cli: 0.35.0, 0.35.0, 0.35.0 in README.md,"
                " 0.36.0 in pyproject.toml's dev group"
            ),
        ),
    ],
)
def test_a_pin_that_differs_fails_naming_both(
    tmp_path: Path, file: str, old: str, new: str, line: str
) -> None:
    root = repository(tmp_path)
    edit(root / file, old, new)

    assert check(root) == (1, line + "\n")


def test_a_pin_not_found_fails(tmp_path: Path) -> None:
    root = repository(tmp_path)
    edit(root / ".pre-commit-config.yaml", "          - pytest==9.1.1\n", "")

    assert check(root) == (1, "pytest: not found in the mypy hook\n")


def test_a_pair_not_found_on_either_side_names_both(tmp_path: Path) -> None:
    root = repository(tmp_path)
    edit(root / "pyproject.toml", '  "mypy==2.4.1",\n', "")
    edit(root / ".pre-commit-config.yaml", "    rev: ad26", "    nope: ad26")

    assert check(root) == (
        1,
        "mypy: not found in the mypy hook's rev and pyproject.toml's dev group\n",
    )


def test_only_the_paired_hook_and_job_count(tmp_path: Path) -> None:
    root = repository(tmp_path)
    decoy = """\
  - repo: https://example.com/other
    rev: v1.0.0
    hooks:
      - id: other
        additional_dependencies:
          - pytest==8.0.0
"""
    edit(root / ".pre-commit-config.yaml", "repos:\n", "repos:\n" + decoy)
    other_job = """\
  docs:
    steps:
      - uses: actions/setup-node@0000000000000000000000000000000000000000
        with:
          node-version: 22
"""
    edit(root / ".github/workflows/ci.yml", "jobs:\n", "jobs:\n" + other_job)

    assert check(root) == (0, "")


def test_quotes_comments_and_other_keys_are_read_past(tmp_path: Path) -> None:
    root = repository(tmp_path)
    hooks = root / ".pre-commit-config.yaml"
    edit(
        hooks,
        "default_language_version:\n",
        "default_language_version:\n  python: python3.11\n",
    )
    edit(hooks, "- pytest==9.1.1\n", "- pytest==9.1.1  # uv.lock's\n")
    ci = root / ".github/workflows/ci.yml"
    edit(ci, "node-version: 24.22.2", "node-version: '24.22.2' # the hooks'")
    edit(root / "pyproject.toml", "dev = [\n", 'dev = [\n  {include-group = "lint"},\n')

    assert check(root) == (0, "")


def test_a_readme_requirement_wrapped_onto_two_lines_is_compared(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    edit(root / "README.md", "`PATH`, in version ", "`PATH`,\nin version 9.")

    code, out = check(root)

    assert code == 1 and out.startswith("apm-cli: 9.")


def test_a_period_after_the_readme_version_is_not_part_of_it(tmp_path: Path) -> None:
    root = repository(tmp_path)
    edit(root / "README.md", "`.\n", ".\n")

    assert check(root) == (0, "")


def test_every_version_uv_lock_holds_is_compared(tmp_path: Path) -> None:
    root = repository(tmp_path)
    fork = '\n[[package]]\nname = "pytest"\nversion = "9.2.0"\n'
    (root / "uv.lock").write_text(UV_LOCK + fork)

    assert check(root) == (
        1,
        "pytest: 9.1.1 in the mypy hook, 9.1.1, 9.2.0 in uv.lock\n",
    )


def test_the_repository_root_is_the_default(tmp_path: Path) -> None:
    root = repository(tmp_path)
    result = subprocess.run(
        [sys.executable, SCRIPT], cwd=root, capture_output=True, check=False
    )

    assert result.returncode == 0
