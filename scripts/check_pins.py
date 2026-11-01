"""Checks that each version pinned in two places is the same in both.

The pairs are CONTRIBUTING.md's (Tooling): a bump, by hand or by Dependabot, that
moves one side only fails here, naming both. Takes the repository root, by default
the working folder; prints one line per pair that differs and exits 1.
"""

import json
import re
import sys
import tomllib
from pathlib import Path

HOOKS = ".pre-commit-config.yaml"
CI = ".github/workflows/ci.yml"
LOCK = ".github/commitlint/package-lock.json"
PRESET = "@commitlint/config-conventional"


# A YAML value: unquoted, up to a comment.
VALUE = r"""['"]?([^\s'"#]+)"""


def block(text: str, head: str) -> str:
    """The lines from the first that matches `head` to the next as little indented."""
    lines = text.splitlines()
    for start, line in enumerate(lines):
        if re.match(head, line):
            indent = len(line) - len(line.lstrip())
            end = start + 1
            while end < len(lines) and (
                not lines[end].strip()
                or len(lines[end]) - len(lines[end].lstrip()) > indent
            ):
                end += 1
            return "\n".join(lines[start:end])
    return ""


def found(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.MULTILINE)
    return match[1] if match else None


def mismatches(root: Path) -> list[str]:
    hooks = (root / HOOKS).read_text()
    mypy = block(hooks, r"\s*- repo: .*/mirrors-mypy$")
    commitlint = block(hooks, r"\s*- repo: .*/commitlint-pre-commit-hook$")
    languages = block(hooks, r"default_language_version:")
    job = block((root / CI).read_text(), r"\s*commitlint:")
    dev = tomllib.loads((root / "pyproject.toml").read_text())["dependency-groups"]
    locked: dict[str, list[str]] = {}
    for package in tomllib.loads((root / "uv.lock").read_text())["package"]:
        locked.setdefault(package["name"], []).append(package["version"])
    npm = json.loads((root / LOCK).read_text())["packages"]
    readme = (root / "README.md").read_text()
    # A frozen rev names its tag in a comment; any other rev is the tag.
    rev = found(r"^\s+rev: \S+\s+# frozen: v?(\S+)", mypy) or found(
        r"^\s+rev: v?(\S+)", mypy
    )
    # Each pair: what is pinned, then each side as (where, its versions).
    pairs = [
        (
            "mypy",
            ("the mypy hook's rev", [rev] if rev else []),
            (
                "pyproject.toml's dev group",
                [
                    d.removeprefix("mypy==")
                    for d in dev["dev"]
                    if isinstance(d, str) and d.startswith("mypy==")
                ],
            ),
        ),
        (
            "apm-cli",
            (
                "README.md",
                # The requirement, wrapped or not, then each install line.
                re.findall(
                    r"`apm`\s+must\s+be\s+on\s+`PATH`.*?,\s+in\s+version\s+([\w.]+):",
                    readme,
                    re.DOTALL,
                )
                + re.findall(r"apm-cli==([\w.]*\w)", readme),
            ),
            (
                "pyproject.toml's dev group",
                [
                    d.removeprefix("apm-cli==")
                    for d in dev["dev"]
                    if isinstance(d, str) and d.startswith("apm-cli==")
                ],
            ),
        ),
        *(
            (
                name,
                (
                    "the mypy hook",
                    re.findall(rf"^\s+- {name}=={VALUE}", mypy, re.MULTILINE),
                ),
                ("uv.lock", locked.get(name, [])),
            )
            for name in ("pytest", "tomlkit")
        ),
        (
            PRESET,
            ("the commitlint hook", re.findall(rf'"{PRESET}@([^"]+)"', commitlint)),
            (
                LOCK,
                [v]
                if (v := npm.get(f"node_modules/{PRESET}", {}).get("version"))
                else [],
            ),
        ),
        (
            "node",
            (
                "default_language_version",
                re.findall(rf"^\s+node: {VALUE}", languages, re.MULTILINE),
            ),
            (
                f"the commitlint job of {CI}",
                re.findall(rf"^\s+node-version: {VALUE}", job, re.MULTILINE),
            ),
        ),
    ]
    lines = []
    for name, (where, versions), (other, others) in pairs:
        if not versions or not others:
            missing = [
                side for side, vs in ((where, versions), (other, others)) if not vs
            ]
            lines.append(f"{name}: not found in {' and '.join(missing)}")
        elif set(versions + others) != {versions[0]}:
            lines.append(
                f"{name}: {', '.join(versions)} in {where}, {', '.join(others)} in {other}"
            )
    return lines


def main() -> int:
    lines = mismatches(Path(sys.argv[1] if len(sys.argv) > 1 else "."))
    for line in lines:
        print(line)
    return 1 if lines else 0


if __name__ == "__main__":
    sys.exit(main())
