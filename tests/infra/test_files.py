"""`files.atomic_write`: a file replaced in one step."""

import os
from pathlib import Path

import pytest

from skill_graft.infra import files


def test_atomic_write_writes_beside_its_target_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "skill-graft.lock"
    replaced: list[tuple[str, str]] = []
    replace = os.replace

    def recording(src: str, dst: str) -> None:
        replaced.append((src, dst))
        replace(src, dst)

    monkeypatch.setattr(os, "replace", recording)

    files.atomic_write(target, b"data\n")

    # Beside it, on its file system, so the rename is atomic, and hidden.
    ((src, dst),) = replaced
    assert Path(src).parent == tmp_path and Path(dst) == target
    assert Path(src).name.startswith(".skill-graft.lock.")
    assert target.read_bytes() == b"data\n"
