# Tasks

One commit per task. Group 2 is test-first: each test is red against its mutant, as the module's mutmut rerun shows it
killed, and passes on the code. Survivor counts are the spike's.

## 1. mutmut, set up

- [x] 1.1 `mutmut` (3.8.x) in the `dev` group of `pyproject.toml` and `uv.lock`, `[tool.mutmut]` with `source_paths`,
  `also_copy` (directories and top-level files), `type_check_command`
  (`["mypy", "src/skill_graft", "--output", "json", "--no-warn-unused-ignores"]`, dropped: see design) and
  `pytest_add_cli_args` (`-m "not linear_time"`); `/mutants/` in `.gitignore`, `^mutants/` excluded in `[tool.mypy]`,
  `mutants` in cspell's `ignorePaths`, pyright's `exclude` and pytest's `norecursedirs`; verify
  `uv run mutmut run "skill_graft.pipeline.rename*"` completes its run on unchanged code and reports, `uv run mypy .`
  ignores `mutants/`, and `git status` shows no `mutants/`. Time a glob run with and without `type_check_command`; if it
  fails or costs more than the mutants it removes, drop it and record why in `design.md`
- [x] 1.2 `cli._parser`'s help texts out of mutmut's reach: first a `# pragma: no mutate start` … `end` region, which
  the review found silenced the parser's structure too; then a module-level `_TEXT` table (4.1); verify a rerun of
  `skill_graft.cli.x__parser*` mutates no help text, and `uv run pytest` passes
- [x] 1.3 `CONTRIBUTING.md`'s Mutation testing section: which harness covers what, how to run mutmut (all, one module by
  glob, `mutmut results`, `mutmut show`), opt-in, about an hour, Linux and macOS only, never a gate; equivalent mutants
  as a bare `# pragma: no mutate`, its reason in a comment above; message wording and mutants mypy refuses as known
  noise. A line in `AGENTS.md`'s Tests section, a row in `docs/README.md`, new words in `.cspell.yaml`; verify the
  markdown and cspell hooks pass

## 2. `pipeline/` survivors

Per module: `uv run mutmut run "skill_graft.pipeline.<module>*"`; each survivor that is neither message wording nor
refused by mypy killed by a test in `tests/pipeline/test_<module>.py`, or marked equivalent with its reason. A survivor
that is a bug: its fix, and a delta spec if a spec covers the behavior; its `Fixed` entry comes with the archive commit.
Verify per task: the module's rerun leaves only those two kinds of survivor, and `uv run pytest` passes.

- [x] 2.1 `deployed` (74)
- [x] 2.2 `references` (34)
- [x] 2.3 `lock` (31)
- [x] 2.4 `vet` (30)
- [x] 2.5 `config` (27)
- [x] 2.6 `discovery` (20) and `hidden` (14)
- [x] 2.7 `patch` (16) and `rename` (8)
- [x] 2.8 `hull` (8), `compute` (6: wording and mutants mypy refuses, one equivalent; no test, so no
  `tests/pipeline/test_compute.py`) and `vendor` (4)

## 3. The baseline

- [x] 3.1 A full `uv run mutmut run`, then reruns of `cli` and `pipeline` after the review (4.1, 4.2); the survivors per
  layer into `CONTRIBUTING.md` as the baseline to beat; verify `pipeline` has no survivor but known noise (message
  wording, mypy refusals, import-time code), and the markdown hooks pass

## 4. After review

- [x] 4.1 `cli._parser`'s help texts into a module-level `_TEXT` table, the pragma region gone, so the parser's
  structure is mutated; tests that each text is shown, `tree --format`'s choices, the commands a usage error lists, no
  abbreviated option; verify `--help` prints the same text for every command, the rerun of `skill_graft.cli.x__parser*`
  leaves only usage wording, and `uv run pytest` passes
- [x] 4.2 Pragmas only on a line holding the equivalent expression alone, no regions; else the redundancy removed, the
  code restructured, or the value a module-level constant; `_inside`'s containment restored with a test for a name
  running past `Skill tool`, Myers bounded again; verify the rerun of `pipeline/` leaves only known noise, and
  `uv run pytest` passes
