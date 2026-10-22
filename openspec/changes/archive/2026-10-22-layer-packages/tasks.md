# Tasks

## 1. Narrow interfaces (flat layout)

- [x] 1.1 Add `compute_hull(config, cache=None, refs=None)` to `resolve.py`, a context manager owning the temporary
  folder; move `cli._resolve` (renamed `_hull`, still printing the config's warnings),
  `cli`'s `build`, `edit._finish`, `update._update`, `update._previous` and the four
  tests calling `resolve.folders` / `resolve.resolve` onto it; make `folders`, `indexes`, `roots` private; verify
  `grep -rn 'resolve\.\(folders\|resolve\)\b' src tests` finds nothing and `pre-commit run --all-files` is green
- [x] 1.2 Move `tree`, `suggestions`, `announce_suggestions`, `shown_edges`, `node_label`, `edge_label` from `lock.py`
  to `explain.py`, the last three private; update the module docstrings and callers; verify `lock.py` no longer
  imports `notice` or `Edge`, `explain.py` no longer imports `lock`, and pre-commit is green
- [x] 1.3 Make `discovery.skill_folders`, `paths.package_in`, `explain.outside` and `git.call` private; verify
  `grep` finds no use outside their modules and pre-commit is green

## 2. Layer packages

- [x] 2.1 `git mv` the modules into `commands/`, `pipeline/`, `infra/` as in design.md (`resolve.py` →
  `pipeline/compute.py`, `init.py` → `commands/init_package.py`), each `__init__.py` a docstring naming its layer;
  change only import lines in `src/` and `tests/`, plus the module name at call sites of the two renamed modules
  (`resolve.` → `compute.`, `init.init` → `init_package.init`), keeping module-attribute calls so
  `monkeypatch.setattr` still hits;
  verify pre-commit is green and the console script runs (`uv run skill-graft help`)
- [x] 2.2 `git mv` the test files into `tests/cli/`, `tests/commands/`, `tests/pipeline/`, `tests/infra/` as in
  design.md, renaming `test_init` and `test_git_apply`, and add `tests` to `mypy_path`; verify
  `pre-commit run mypy --files tests/cli/test_build.py` passes, and `pytest --collect-only -q` reports the same number of
  tests as before the move and pre-commit is green
- [x] 2.3 Add `import-linter` to the dev group, its exhaustive `layers` contract to `pyproject.toml`, a local
  pre-commit hook `uv run lint-imports` on `src/` and `pyproject.toml`, and `.import_linter_cache/` to `.gitignore`;
  verify the hook passes, fails when `infra/paths.py` imports `skill_graft.commands.edit`, fails when an empty
  `src/skill_graft/stray.py` is added (both reverted after), and `git status` shows no cache folder
- [x] 2.4 Name the layers and the import rule in `AGENTS.md` (Python section) and that `tests/` mirrors them (Tests
  section), and update module names in `docs/design.md`; add new words to `.cspell.yaml`; verify
  `pre-commit run --all-files` is green
