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
repository path the tests read, and `pytest_add_cli_args = ["-m", "not linear_time"]`. mutmut runs pytest's `testpaths`
itself; `tests_dir` is deprecated and not set. The `linear_time` tests hold a one-second wall-clock limit, which a busy
fork can miss: a mutant would count as killed by load, or the run on the unchanged code would fail. They time regexes,
which `mutation/` already mutates and times, alone. A wrapper module like `mutation/` would add an equivalent-mutant
list and an exit code: neither is wanted while mutmut only reports. mutmut is pinned to a minor version in the `dev`
group, as mypy is, since its config keys moved within 3.x.

No `type_check_command`. It was meant to count a mutant `mypy --strict` refuses (`None` for a `str` argument) as caught,
with `["mypy", "src/skill_graft", "--output", "json", "--no-warn-unused-ignores"]`: JSON is what mutmut parses, and
mutmut marks its own lines `# type: ignore`. Task 1.1's first glob run stopped on it: a mutant in `lock.py` changed an
inferred type, and mypy reported the error on a generated line outside any mutant ("Could not find mutant for type
error", `lock.py:18601`). mutmut type-checks the whole tree before a glob narrows the mutants, so any such mutant
anywhere stops every run. Mutants mypy would refuse stay among the survivors, as known noise like message wording: no
pragma, which would silence the line's other mutants too.

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

`def _parser` in `cli.py` sits between `# pragma: no mutate start` and `# pragma: no mutate end`, each on its own line:
its 340 survivors are help text. Not `block`: on its own line at module level it silences every statement after it to
the module's end, and after the `def` line it would push that line past 88 columns. Other messages (`SkillGraftError`
texts, **Vet** reasons, warnings) are scattered through expressions a pragma would cover too much of; their mutants stay
in the report as noise. A test already pins a message's key phrase where a user acts on it; pinning exact wording would
make every rewording a test change. `do_not_mutate_patterns` (a regex over source lines) was considered and rejected: a
line holding a message often holds logic too.

### An equivalent mutant: a pragma with its reason

A bare `# pragma: no mutate` on the line, its reason in a comment above, `# Equivalent mutants: <reason>`. ruff counts a
`# pragma:` comment toward its 88 columns, and wraps a statement it pushes past them: the pragma then sits on the
closing line, where mutmut does not read it for the mutated expression. Task 2.1 found a reason on the line itself,
after a comma, pushed most lines past 88; the bare pragma, 21 characters, fits all but two. A line that cannot take it
sits in a `# pragma: no mutate start, <reason>` … `# pragma: no mutate end` region, each on its own line, the `end`
before the next statement of the same block: mutmut scans a module's top level before the functions' bodies, so a region
cannot end outside the block it starts in. Next to the code, the reason is where a reader of the line sees it, and
survives line moves; a list like `equivalent.toml` needs a wrapper to check it, and mutmut names mutants by function and
number, which shift with every edit. A pragma silences every mutant on its line, so it goes on the narrowest line,
sparingly: a reviewer reads each.

### Killing `pipeline/` survivors

Per module, a rerun of its mutants (`uv run mutmut run "skill_graft.pipeline.<module>*"`), then for each survivor a test
in `tests/pipeline/test_<module>.py` (`compute` needed none: its survivors are noise but one equivalent), test-first:
the test fails against the mutant (`mutmut apply <mutant>`, reverted after) and passes on the code. A survivor that is a
bug gets the fix and, where a spec covers the behavior, a delta spec; its `Fixed` entry comes with the archive commit.
Timeouts (`hull.reach`, `deployed._blocks`, `deployed._myers`) count as killed.

### The baseline, in `CONTRIBUTING.md`

Survivors per layer, after this change, in the Mutation testing section, as the number to beat, with the commit it was
measured on. It goes stale too, but as a dated reference a reader compares a fresh run against, not data a tool reads: a
committed results file would look current and be wrong after the next source edit.

## Risks / Trade-offs

- [Two hours per full run discourages running it] → a per-module glob runs in about two minutes (`rename`, 122 s, most
  of it the unchanged run and the test-to-function map mutmut builds first).
- [A pragma hides a real gap] → one per line, with a reason, read in review; a region only around `_parser`.
- [mutmut's config moves again within 3.x] → pinned minor version; a key it no longer reads warns at start.
- [A mutant only a subprocess test would kill shows as a survivor] → its triage finds the subprocess test and adds an
  in-process one, which the layer rule asks for anyway.
- [Message noise hides a real survivor in the report] → the per-module triage reads every survivor's diff once; later
  runs compare against the baseline.
- [Survivors mypy would refuse inflate the report] → the triage counts them as noise: the hooks run mypy on every
  commit, so such a change can never land.

## Migration Plan

None: dev tooling, tests and docs; any bug fix found ships as an ordinary `Fixed` entry, written at archive.
