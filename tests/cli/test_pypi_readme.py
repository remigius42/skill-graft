"""The README PyPI shows: the build points its relative links at the release's tag."""

import email
import re
import subprocess
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[2]
REPO = "remigius42/skill-graft"
SCHEME = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*:")
# Wider than the build's substitutions, so a form they miss shows up here.
TARGET = re.compile(
    r"\]\(<?([^)\s>]+)|^ {0,3}\[[^\]]+\]:\s*<?([^\s>]+)|(?:src|href)=[\"']([^\"']+)",
    re.MULTILINE,
)
TAGGED = re.compile(
    rf"https://(?:github\.com/{REPO}/blob|raw\.githubusercontent\.com/{REPO})"
    r"/v([^/]+)/([^)\s\"#]+)"
)


def built_description(out: Path) -> str:
    subprocess.run(
        [
            "uv",
            "build",
            "--wheel",
            "--no-sources",
            "--quiet",
            "-o",
            str(out),
            str(ROOT),
        ],
        check=True,
    )
    (wheel,) = out.glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        (name,) = (n for n in archive.namelist() if n.endswith(".dist-info/METADATA"))
        payload = email.message_from_bytes(archive.read(name)).get_payload()
    assert isinstance(payload, str)
    return payload


def test_pypi_readme_links_name_the_release_and_files_it_holds(tmp_path: Path) -> None:
    description = built_description(tmp_path)
    with (ROOT / "pyproject.toml").open("rb") as f:
        version = tomllib.load(f)["project"]["version"]

    targets = ["".join(groups) for groups in TARGET.findall(description)]
    relative = [t for t in targets if not SCHEME.match(t) and not t.startswith("#")]
    tagged = TAGGED.findall(description)

    assert relative == []
    assert tagged, "no link names the release"
    assert {v for v, _ in tagged} == {version}
    assert [p for _, p in tagged if not (ROOT / p).exists()] == []
