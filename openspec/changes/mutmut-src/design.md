# Design

## Context

`mutation/`, the regex harness (`linear-regexes`), mutates the tokens of the security-relevant patterns and runs the
tests of the modules holding each. Nothing mutates the rest of `src/skill_graft/`. A spike of mutmut 3.8.1 on this
repository, all eight CPUs, gave:

| Layer      | Survivors | Of which                                    |
| ---------- | --------: | ------------------------------------------- |
| `cli`      |       420 | 340 in `_parser`, the help texts            |
| `pipeline` |       272 | 82 message wording; 190 others              |
| `infra`    |       201 | 131 in `cache`                              |
| `commands` |       191 |                                             |
| all        |     1 084 | of 8 380 mutants; 7 291 killed, 5 timed out |

in about two hours (1.1 mutants per second). The tests read files outside `src/` and `tests/` (`skills/`, `evals/`,
`docs/` and more): mutmut copies the source into `mutants/` and runs the tests there, so a path it does not copy fails
its first run, on the unchanged code ("failed to collect stats"), as the spike's first two attempts did. A test that
starts `skill_graft` in a subprocess (`tests/cli/test_warnings.py`, `test_cli.py`'s `ON_WINDOWS` case,
`tests/test_mutation.py`) imports the checkout's `src/` through the editable install, not the mutant: what only those
tests would kill shows as a survivor.

## Goals / Non-Goals

**Goals:**

- A reproducible `uv run mutmut run` over `src/skill_graft/`, and a rerun of one module's mutants that takes minutes.
- `pipeline/` with no unexplained survivor.

**Non-Goals:**

- A gate: no exit code, threshold or CI job hangs on mutmut.
- Testing message wording, or killing survivors outside `pipeline/` (later changes, one per layer).
- Replacing `mutation/`, or teaching mutmut its regex operators.

## Decisions

### mutmut's own CLI, configured in `pyproject.toml`

`[tool.mutmut]`: `source_paths = ["src/skill_graft/"]` (`paths_to_mutate` is deprecated in 3.8), `also_copy` naming each
repository path the tests read, `type_check_command` running mypy on the mutated tree, so a mutant mypy refuses counts
as caught, and `pytest_add_cli_args = ["-m", "not linear_time"]`. mutmut runs pytest's `testpaths` itself; `tests_dir`
is deprecated and not set. The `linear_time` tests hold a one-second wall-clock limit, which a busy fork can miss: a
mutant would count as killed by load, or the run on the unchanged code would fail. They time regexes, which `mutation/`
already mutates and times, alone. A wrapper module like `mutation/` would add an equivalent-mutant list and an exit
code: neither is wanted while mutmut only reports. mutmut is pinned to a minor version in the `dev` group, as mypy is,
since its config keys moved within 3.x.

`type_check_command`: `mypy --strict` already refuses many mutants (`None` for a `str` argument, `key=None` where a
callable is required); counting them as caught keeps them out of the survivors, which is what the project's hooks would
do to such a change anyway. mutmut parses the command's output as JSON and maps each error to a mutant, so the command
is a list, run without a shell, `["mypy", "src/skill_graft", "--output", "json", "--no-warn-unused-ignores"]`: mutmut
marks every line it generates `# type: ignore`, which strict mode's `warn_unused_ignores` reports outside any mutant,
and mutmut then stops ("Could not find mutant for type error"). It checks the whole mutated tree on every run, before a
glob narrows the mutants: task 1.1's glob run already meets every mutant's type errors, so an error mypy reports outside
any mutant (a mutated value flowing into an unchanged caller) stops that run, not a later full one. If it proves slow,
or fails so, it is dropped and recorded here.

`also_copy` lists paths, not `.`: copying the whole checkout would copy `mutants/` and `.venv/` too. Directories and
top-level files only: mutmut copies a file entry without creating its parent folder. A path the tests need and the list
lacks fails the first run loudly; an entry that no longer exists mutmut skips silently, which is harmless. The spike's
working list: the folders `mutation/`, `tests/`, `scripts/`, `evals/`, `skills/`, `docs/`, `openspec/`, `.github/` and
the files `CONTEXT.md`, `CONTRIBUTING.md`, `README.md`, `SECURITY.md`, `CHANGELOG.md`, `AGENTS.md`,
`.pre-commit-config.yaml`, `uv.lock`. `tests/test_mutation.py` and `tests/test_check_pins.py` resolve the repository
root to `mutants/`, so `mutation/` and `scripts/` must be there.

### `mutants/` out of every tool

`.gitignore` gains `/mutants/`; pre-commit and ruff skip ignored files. mypy does not: `uv run mypy .` would check the
mutated copy, so `[tool.mypy]` excludes `^mutants/`. cspell's `ignorePaths` gains `mutants`, `[tool.pyright]` (editors)
gains `exclude = ["mutants"]`, and pytest's `norecursedirs` gains `mutants`: `testpaths` covers a bare `pytest`, not
`pytest .` or an editor's discovery from the root.

### Message wording is not mutated, or not counted

`def _parser` in `cli.py` carries `# pragma: no mutate block`: its 340 survivors are help text. Other messages
(`SkillGraftError` texts, **Vet** reasons, warnings) are scattered through expressions a pragma would cover too much of;
their mutants stay in the report as noise. A test already pins a message's key phrase where a user acts on it; pinning
exact wording would make every rewording a test change. `do_not_mutate_patterns` (a regex over source lines) was
considered and rejected: a line holding a message often holds logic too.

### An equivalent mutant: a pragma with its reason

`# pragma: no mutate, <reason>` on the line: mutmut reads the first word after `no mutate` (`block`, `start`, `end`,
else a bare line pragma), so the reason follows a comma. The pragma goes on the statement's first line, and its reason
is short enough that the line stays within ruff's 88 columns: ruff counts a `# pragma:` comment, and a statement it
splits keeps the pragma on one line only, as mutmut reads it, and the rest stay mutated. Inline keeps the reason next to
the code, where a reader of the line sees it, and survives line moves; a list like `equivalent.toml` needs a wrapper to
check it, and mutmut names mutants by function and number, which shift with every edit. A pragma silences every mutant
on its line, so it goes on the narrowest line, sparingly: a reviewer reads each.

### Killing `pipeline/` survivors

Per module, a rerun of its mutants (`uv run mutmut run "skill_graft.pipeline.<module>*"`), then for each survivor a test
in `tests/pipeline/test_<module>.py`, created for `compute`, which has none (its tests sit in `tests/commands/`),
test-first: the test fails against the mutant (`mutmut apply <mutant>`, reverted after) and passes on the code. A
survivor that is a bug gets the fix and, where a spec covers the behavior, a delta spec; its `Fixed` entry comes with
the archive commit. Timeouts (`hull.reach`, `deployed._blocks`, `deployed._myers`) count as killed.

### The baseline, in `CONTRIBUTING.md`

Survivors per layer, after this change, in the Mutation testing section, as the number to beat, with the commit it was
measured on. It goes stale too, but as a dated reference a reader compares a fresh run against, not data a tool reads: a
committed results file would look current and be wrong after the next source edit.

## Risks / Trade-offs

- [Two hours per full run discourages running it] → per-module globs and mutmut's cache of unchanged functions make the
  usual run, after a change to one module, take minutes.
- [A pragma hides a real gap] → one per line, with a reason, read in review; `block` only on `_parser`.
- [mutmut's config moves again within 3.x] → pinned minor version; a key it no longer reads warns at start.
- [A mutant only a subprocess test would kill shows as a survivor] → its triage finds the subprocess test and adds an
  in-process one, which the layer rule asks for anyway.
- [Message noise hides a real survivor in the report] → the per-module triage reads every survivor's diff once; later
  runs compare against the baseline.
- \[`type_check_command` counts as caught a mutant only mypy notices, not a test\] → the hooks run mypy on every commit,
  so such a change can never land either.

## Migration Plan

None: dev tooling, tests and docs; any bug fix found ships as an ordinary `Fixed` entry, written at archive.
