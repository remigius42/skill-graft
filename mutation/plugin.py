"""A pytest plugin, `-p mutation.plugin`: patches one mutant in, and writes
which tests failed.

`MUTANT` holds the mutant, as JSON `{"target": ..., "text": ...}`; without it
nothing is patched. `REPORT` names the file the report goes to, as JSON
`{"failed": [node IDs], "timing_only": true when every failure is a
linear_time test}`.
"""

import json
import os
import re
from pathlib import Path

import pytest

from mutation import targets

MUTANT = "MUTATION_MUTANT"
REPORT = "MUTATION_REPORT"

# Each failed test or collection, and whether it carries `linear_time`.
_failed: list[tuple[str, bool]] = []


def patch(target: str, text: str) -> None:
    """Puts `text`, compiled with the original's flags, wherever the original
    of `target` is bound in a `skill_graft` module, or in its `vet._COMPILED`
    entry."""
    original = targets.resolve(target)
    mutant = re.compile(text, original.flags)
    if target.startswith(targets.PATTERNS):
        flag = target.removeprefix(targets.PATTERNS)
        compiled = targets.module("vet")._COMPILED
        compiled[[name for name, _ in compiled].index(flag)] = (flag, mutant.search)
        return
    for module in targets.all_modules():
        for attribute, value in list(vars(module).items()):
            if value is original:
                setattr(module, attribute, mutant)


def pytest_configure(config: pytest.Config) -> None:
    if raw := os.environ.get(MUTANT):
        mutant = json.loads(raw)
        patch(mutant["target"], mutant["text"])


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if report.failed:
        _failed.append((report.nodeid, "linear_time" in report.keywords))


def pytest_collectreport(report: pytest.CollectReport) -> None:
    if report.failed:
        _failed.append((report.nodeid, False))


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if path := os.environ.get(REPORT):
        failed = list(dict.fromkeys(node for node, _ in _failed))
        timing_only = bool(_failed) and all(timed for _, timed in _failed)
        Path(path).write_text(
            json.dumps({"failed": failed, "timing_only": timing_only})
        )
