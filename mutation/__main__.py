"""`uv run python -m mutation [target...]`, from the repository root: mutates
each target pattern, runs its tests against each mutant, and exits 1 on a
surviving mutant `equivalent.toml` does not list, or on a listed one that no
longer survives or exists; 2 if the harness cannot run."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from mutation import operators, plugin, targets

ROOT = Path(__file__).parents[1]
EQUIVALENT = Path(__file__).with_name("equivalent.toml")
REGISTRY = "tests/cli/test_linear_time.py"
CASE = f"{REGISTRY}::test_pumped_input_takes_linear_time"


@dataclass(frozen=True)
class Run:
    """One pytest run: the tests that failed, None if it timed out; whether
    every failure is a `linear_time` test; how long it took."""

    failed: list[str] | None
    timing_only: bool
    seconds: float


@dataclass(frozen=True)
class Outcome:
    """What one mutant's run came to: killed, survived, timed out or timing
    only; for the last two, whether a run on its own confirmed the kill."""

    target: str
    mutant: operators.Mutant
    status: str
    confirmed: bool | None = None

    @property
    def killed(self) -> bool:
        return self.status == "killed" or bool(self.confirmed)


def _registry() -> set[str]:
    """The entries of the linear-time registry."""
    spec = importlib.util.spec_from_file_location("_linear_time", ROOT / REGISTRY)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.REGISTRY)


def _names(name: str) -> list[str]:
    """Every name target `name`'s pattern is bound to, as `<module>.<name>`."""
    if name.startswith(targets.PATTERNS):
        return [name]
    pattern = targets.resolve(name)
    return [
        f"{holder.rsplit('.', 1)[1]}.{attribute}"
        for holder in targets.holders(name)
        for attribute, value in vars(importlib.import_module(holder)).items()
        if value is pattern
    ]


def select(target: targets.Target) -> list[str]:
    """The tests a target's mutants run against: the test file of each module
    holding it, those that exist, as `tests/` mirrors the layers; its extra
    files; its own cases in the linear-time registry, by node ID."""
    files = []
    for holder in targets.holders(target.name):
        parts = holder.split(".")[1:]
        path = f"tests/{parts[0]}/test_{parts[-1]}.py"
        if (ROOT / path).is_file():
            files.append(path)
    registry = _registry()
    cases = [f"{CASE}[{n}]" for n in _names(target.name) if n in registry]
    return list(dict.fromkeys(sorted(files) + list(target.extra) + cases))


def run_pytest(
    tests: list[str], mutant: tuple[str, str] | None, timeout: float | None
) -> Run:
    """pytest over `tests`, with `mutant` (target, text) patched in, stopped
    after `timeout` seconds."""
    with tempfile.TemporaryDirectory() as folder:
        report = Path(folder) / "report.json"
        env = {**os.environ, plugin.REPORT: str(report)}
        env.pop(plugin.MUTANT, None)
        if mutant is not None:
            env[plugin.MUTANT] = json.dumps({"target": mutant[0], "text": mutant[1]})
        command = [sys.executable, "-m", "pytest", "-q", "-p", "mutation.plugin"]
        command += ["-p", "no:cacheprovider", f"--basetemp={folder}/tmp", *tests]
        start = time.perf_counter()
        try:
            done = subprocess.run(
                command,
                check=False,
                cwd=ROOT,
                env=env,
                capture_output=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return Run(None, False, time.perf_counter() - start)
        seconds = time.perf_counter() - start
        if not report.is_file():
            output = done.stdout.decode(errors="replace")[-2000:]
            print(
                f"pytest wrote no report ({done.returncode}):\n{output}",
                file=sys.stderr,
            )
            raise SystemExit(2)
        result = json.loads(report.read_text())
        if done.returncode not in (0, 1) and not result["failed"]:
            result["failed"] = [f"pytest exit code {done.returncode}"]
        return Run(result["failed"], result["timing_only"], seconds)


def _status(run: Run) -> str:
    if run.failed is None:
        return "timed out"
    if not run.failed:
        return "survived"
    return "timing only" if run.timing_only else "killed"


def verdict(
    outcomes: list[Outcome],
    equivalent: dict[str, list[dict[str, object]]],
    ran: set[str],
) -> tuple[list[str], int]:
    """The report's lines, and the exit code: 1 on a survivor not listed, or a
    listed mutant that is killed or does not exist, of a target in `ran` or of
    no target at all."""
    listed = {
        (name, str(entry["operator"]), int(str(entry["offset"])))
        for name, entries in equivalent.items()
        for entry in entries
    }
    by_key = {(o.target, o.mutant.operator, o.mutant.offset): o for o in outcomes}
    lines = [
        f"survived: {o.target} {o.mutant.operator} at {o.mutant.offset}: "
        f"{o.mutant.text!a}"
        for o in outcomes
        if not o.killed and (o.target, o.mutant.operator, o.mutant.offset) not in listed
    ]
    survivors = len(lines)
    known = {target.name for target in targets.TARGETS}
    for name, operator, offset in sorted(listed, key=str):
        if name not in ran and name in known:
            continue
        found = by_key.get((name, operator, offset))
        if found is None:
            lines.append(f"stale: {name} {operator} at {offset}: no such mutant")
        elif found.killed:
            lines.append(f"stale: {name} {operator} at {offset}: killed")
    killed = sum(o.killed for o in outcomes)
    equivalents = len(outcomes) - killed - survivors
    lines.append(
        f"{len(outcomes)} mutants: {killed} killed, {equivalents} equivalent, "
        f"{survivors} survived"
    )
    return lines, int(len(lines) > 1)


def main(argv: list[str]) -> int:
    known = {target.name: target for target in targets.TARGETS}
    if unknown := [name for name in argv if name not in known]:
        print(f"no such target: {', '.join(unknown)}", file=sys.stderr)
        return 2
    chosen = [known[name] for name in argv] or list(targets.TARGETS)
    equivalent = tomllib.loads(EQUIVALENT.read_text())
    start = time.perf_counter()
    jobs = []
    for target in chosen:
        tests = select(target)
        baseline = run_pytest(tests, None, None)
        if baseline.failed:
            failed = ", ".join(baseline.failed)
            print(f"unpatched run of {target.name} failed: {failed}", file=sys.stderr)
            return 2
        timeout = max(30.0, 10 * baseline.seconds)
        for mutant in operators.mutants(targets.resolve(target.name)):
            jobs.append((target.name, mutant, tests, timeout))
    print(f"{len(jobs)} mutants of {len(chosen)} targets", file=sys.stderr)

    def first(job: tuple[str, operators.Mutant, list[str], float]) -> Outcome:
        name, mutant, tests, timeout = job
        run = run_pytest(tests, (name, mutant.text), timeout)
        return Outcome(name, mutant, _status(run))

    with ThreadPoolExecutor(os.cpu_count()) as pool:
        outcomes = list(pool.map(first, jobs))
    for index, (outcome, job) in enumerate(zip(outcomes, jobs)):
        if outcome.status in ("timed out", "timing only"):
            again = run_pytest(job[2], (job[0], job[1].text), job[3])
            confirmed = again.failed is None or bool(again.failed)
            outcomes[index] = Outcome(outcome.target, job[1], outcome.status, confirmed)
    lines, code = verdict(outcomes, equivalent, {t.name for t in chosen})
    print("\n".join(lines))
    print(f"{time.perf_counter() - start:.0f} s", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
