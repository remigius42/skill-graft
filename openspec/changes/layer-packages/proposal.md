# Proposal

## Why

All 20 modules of `src/skill_graft/` sit side by side, so nothing shows which ones are entry points, which hold the
logic and which only wrap the file system, `git` and `apm`. Some modules also do not do what their names say:
`lock.py` draws the terminal tree as well as writing the lock, and `resolve.py` is named after the glossary's verb
for **References** although it computes the **Hull**. And every caller has to know two
steps (`resolve.folders`, then `resolve.resolve`) plus a
temporary folder that must outlive the **Hull**, where one would do.

## What Changes

- Group the modules into packages by layer, each layer importing only the layers below it:
  `cli.py` (stays at the top, the console entry point), `commands/`, `pipeline/`, `infra/`. An `import-linter`
  contract, run as a pre-commit hook, refuses an import that goes up a layer.
- Replace `resolve.folders` + `resolve.resolve` and the temporary folder every caller opens with one context manager,
  `compute_hull(config, cache=None, refs=None)`, in `pipeline/compute.py` (formerly `resolve.py`). Module and
  function names stop calling that step "resolve"; messages and docstrings keep their wording.
- Move the tree views (`tree`, `suggestions`, `announce_suggestions` and their label helpers) from `lock.py` into
  `explain.py`; `lock.py` keeps rendering, hashing and writing the lock.
- Make private what nothing outside its module uses: the source folders, indexes and roots behind `compute_hull`,
  `discovery.skill_folders`, `paths.package_in`, `explain.outside`, `git.call`, and the moved label helpers.
- Rename `init.py` to `commands/init_package.py`, so it no longer reads as a package's `__init__.py`.
- Mirror the layers in `tests/`: `tests/<layer>/test_<module>.py`, and the end-to-end tests driven through `main()`
  under `tests/cli/`.

No behavior changes: same commands, output, config, lock and errors.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None: a pure refactor (`skip_specs: true`).

## Impact

- Every module under `src/skill_graft/` moves or changes its imports; `pyproject.toml`'s entry point
  (`skill_graft.cli:main`) stays.
- Tests: every file moves into `tests/cli/`, `tests/commands/`, `tests/pipeline/` or `tests/infra/`; imports of moved
  modules change, and the four that call `resolve.folders` / `resolve.resolve` use `compute_hull`.
- New dev dependency `import-linter`, a pre-commit hook and its contract in `pyproject.toml`. Runtime dependencies
  unchanged.
- `AGENTS.md` and `docs/design.md` name the layers; `.cspell.yaml` for new words.
