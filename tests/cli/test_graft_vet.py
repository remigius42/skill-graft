"""The `graft-vet` skill this repository ships (the `graft-vet` spec): its runner,
reader, report filter and steps."""

from pathlib import Path

SKILLS = Path(__file__).parents[2] / "skills"
VET = SKILLS / "graft-vet"


def test_runner_is_graft_checks() -> None:
    # Each skill installs alone, so each ships its own copy; this keeps them one.
    check = (SKILLS / "graft-check" / "run-claude.sh").read_bytes()

    assert (VET / "run-claude.sh").read_bytes() == check
