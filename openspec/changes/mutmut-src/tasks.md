# Tasks

One commit per task. Group 2 is test-first: each test fails against its mutant (`mutmut apply <mutant>`, reverted after)
before it passes on the code. Survivor counts are the spike's.

## 1. mutmut, set up

- [x] 1.1 `mutmut` (3.8.x) in the `dev` group of `pyproject.toml` and `uv.lock`, `[tool.mutmut]` with `source_paths`,
  `also_copy` (directories and top-level files), `type_check_command`
  (`["mypy", "src/skill_graft", "--output", "json", "--no-warn-unused-ignores"]`, dropped: see design) and
  `pytest_add_cli_args` (`-m "not linear_time"`); `/mutants/` in `.gitignore`, `^mutants/` excluded in `[tool.mypy]`,
  `mutants` in cspell's `ignorePaths`, pyright's `exclude` and pytest's `norecursedirs`; verify
  `uv run mutmut run "skill_graft.pipeline.rename*"` completes its run on unchanged code and reports, `uv run mypy .`
  ignores `mutants/`, and `git status` shows no `mutants/`. Time a glob run with and without `type_check_command`; if it
  fails or costs more than the mutants it removes, drop it and record why in `design.md`
- [x] 1.2 `# pragma: no mutate start` and `end` around `def _parser` in `cli.py`; verify a rerun of
  `skill_graft.cli.x__parser*` reports no mutants of it, and `uv run pytest` passes
- [x] 1.3 `CONTRIBUTING.md`'s Mutation testing section: which harness covers what, how to run mutmut (all, one module by
  glob, `mutmut results`, `mutmut show`), opt-in, about two hours, Linux and macOS only, never a gate; equivalent
  mutants as a bare `# pragma: no mutate`, its reason in a comment above; message wording and mutants mypy refuses as
  known noise. A line in `AGENTS.md`'s Tests section, a row in `docs/README.md`, new words in `.cspell.yaml`; verify the
  markdown and cspell hooks pass

## 2. `pipeline/` survivors

Per module: `uv run mutmut run "skill_graft.pipeline.<module>*"`; each survivor that is neither message wording nor
refused by mypy killed by a test in `tests/pipeline/test_<module>.py`, or marked equivalent with its reason. A survivor
that is a bug: its fix, and a delta spec if a spec covers the behavior; its `Fixed` entry comes with the archive commit.
Verify per task: the module's rerun leaves only those two kinds of survivor, and `uv run pytest` passes.

- [x] 2.1 `deployed` (74)
- [x] 2.2 `references` (34)
- [ ] 2.3 `lock` (31)
- [ ] 2.4 `vet` (30)
- [ ] 2.5 `config` (27)
- [ ] 2.6 `discovery` (20) and `hidden` (14)
- [ ] 2.7 `patch` (16) and `rename` (8)
- [ ] 2.8 `hull` (8), `compute` (6, in a new `tests/pipeline/test_compute.py`) and `vendor` (4)

## 3. The baseline

- [ ] 3.1 A full `uv run mutmut run`; the survivors per layer into `CONTRIBUTING.md` as the baseline to beat; verify
  `pipeline` has no survivor but those two kinds, and the markdown hooks pass
