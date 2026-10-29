# Design

## Context

The import graph already respects the layers below: no infrastructure or pipeline module imports a command module. So
the move is mechanical; what needs deciding is where each module goes and what the narrowed interfaces look like.

Tests replace module attributes with `monkeypatch.setattr` (`vendor.vendor`, `lock.write`, `config.load`,
`cache._export`). That keeps working only while callers look these up through the module (`vendor.vendor(...)`), as they
do today; the move must not turn them into `from … import vendor`.

## Goals / Non-Goals

**Goals:**

- A reader finds the layer of a module from its path, and a wrong-way import fails pre-commit.
- One call computes the **Hull** from the config; no caller handles source folders or a work folder.

**Non-Goals:**

- Narrowing `Hull` itself. Its fields (`roots`, `upstream` for the lock; `occurrences` for rewrites) are a record read
  by several modules, not a behavior to hide.
- A shared edge-adjacency helper on `Hull`: `edit._reach`, `explain.why` and the tree each group edges differently (by
  source, by target deduplicated, prose kept when renamed), so one helper would be a pass-through.
- Making `known` read only its own **Source**: it checks out every declared one, so an unrelated **Source** without a
  ref fails it. Fixing that changes behavior; it belongs in its own change.
- Rewording messages or docstrings that say a config or **Hull** "resolves": user-facing text stays as it is.
- Removing the global state in `paths` (`paths.use`), or moving `warn` / `notice` out of `errors.py`.

## Decisions

- **Layers and placement.**

  | Layer                  | Modules                                                                                     |
  | ---------------------- | ------------------------------------------------------------------------------------------- |
  | `skill_graft.cli`      | `cli.py`                                                                                    |
  | `skill_graft.commands` | `edit`, `update`, `explain`, `init_package`                                                 |
  | `skill_graft.pipeline` | `config`, `discovery`, `references`, `hull`, `patch`, `rename`, `compute`, `lock`, `vendor` |
  | `skill_graft.infra`    | `paths`, `files`, `git`, `cache`, `apm`, `errors`                                           |

  `cli.py` stays where it is, so the entry point and the 17 test imports of `skill_graft.cli` stay too. `vendor` and
  `lock` are pipeline steps (a **Hull** in, files out), called by commands. Modules in one layer may import each other
  (`update` uses `edit`). The `__init__.py` files hold a docstring naming the layer and re-export nothing: re-exports
  would make a second name for every module. Alternative: subpackages by feature (`sources/`, `hull/`, `output/`).
  Rejected: the user asked for the layers, and features cut across them (`config` is read everywhere).

- **`compute_hull(config, cache=None, refs=None)`, a context manager yielding the `Hull`.** It reads every source (git
  ones at `refs`, else their ref), walks the **Hull**, checks names, and holds patched copies in a temporary folder it
  removes on exit. `cache` defaults to `Cache(paths.cache())`; only `update` passes one (its layered dry-run cache, and
  the cache it fetched into). `refs` defaults to none, every git source at its own ref. The lifetime rule is not gone
  but stated once, in its docstring: a patched skill's path in `hull.skills` is valid only inside the `with`. Callers
  that read files (`lock.render` hashing, `vendor`, `lock.skill_hashes`) do so inside it; `why` and `tree` read only the
  **Hull**'s data and may use it after, as they do now. Test helpers that return a **Hull** become fixtures or context
  managers that keep it open. Alternative: keep two functions and only rename them. Rejected: the temporary folder stays
  in five callers. Alternative: copy patched skills somewhere lasting. Rejected: something has to delete them. `known`
  keeps building its own cache: no caller varies it.

- **`resolve.py` becomes `pipeline/compute.py`.** "Resolve" stays the command's name and the glossary's verb for
  **References**; the module computes the **Hull**. `check_refs` and `known` stay public there (`update`, `edit`, `cli`
  call them).

- **Tree views move to `explain.py`.** It already draws `why` and Mermaid from the lock's label helpers; with `tree`,
  `suggestions` and `announce_suggestions` it holds every view of the **Hull**, and the helpers become private.

- **`init.py` becomes `commands/init_package.py`.** The command creates a **Package**; the module name says so and no
  longer echoes `__init__.py`.

- **Tests mirror the layers.** A test file sits in the layer of the module it is named after; the end-to-end files,
  named after a command `cli.py` runs itself or a cross-cutting concern, go under `tests/cli/`. `test_fixtures.py` and
  `conftest.py` stay in `tests/`.

  | Folder            | Files                                                                                                                                           |
  | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
  | `tests/cli/`      | `test_cli`, `test_build`, `test_resolve`, `test_scope`, `test_integration`, `test_check`, `test_patches`, `test_subdirectory`, `test_git_build` |
  | `tests/commands/` | `test_edit`, `test_update`, `test_explain`, `test_init_package` (was `test_init`)                                                               |
  | `tests/pipeline/` | `test_config`, `test_discovery`, `test_references`, `test_hull`, `test_patch`, `test_rename`, `test_lock`                                       |
  | `tests/infra/`    | `test_cache`, `test_git` (was `test_git_apply`)                                                                                                 |

  A test keeps the surface it uses: one driving `main()` stays an end-to-end test wherever its file lands. Splitting
  mixed files by surface is out of scope. The folders get no `__init__.py`; `pytest`'s default import mode puts `tests/`
  on `sys.path` for `conftest.py`, so `from conftest import …` keeps working under pytest; mypy gets `tests` in its
  `mypy_path` for the same import. No two files share a basename. Alternative: group by spec capability. Rejected: the
  user asked for the source's structure.

- **`import-linter`, an exhaustive `layers` contract** in `pyproject.toml`: container `skill_graft`, layers `cli` >
  `commands` > `pipeline` > `infra`, `exhaustive = true`, so a module added beside them belongs to no layer and fails
  the contract instead of slipping past it. Run by a local pre-commit hook `uv run lint-imports` whose `files` covers
  `src/` and `pyproject.toml`, so a commit editing only the contract runs it too. Its cache, `.import_linter_cache/`,
  goes in `.gitignore`. Dev dependency only.

- **`cli._resolve` becomes `cli._hull`**, keeping its `_load()` call so the config's warnings still print before the
  **Hull** is computed: `with _hull() as (loaded, hull):`.

## Risks / Trade-offs

- [A large diff hides an accidental behavior change] → the move happens in its own task, with no edit beyond import
  lines and the two renamed modules' names at their call sites; the narrowing tasks run first, in the flat layout, each
  with the full test suite green.
- \[`monkeypatch.setattr` on a module the caller no longer looks up silently patches nothing\] → those tests assert the
  effect of the patch (a failure, an interruption), so a dead patch fails them; checked in the move task.
- \[Moved test files are silently not collected, or `from conftest import` fails\] → compare the number of tests
  `pytest --collect-only -q` reports before and after the move.
- \[`mypy` on a commit touching only `tests/cli/test_x.py` no longer finds `conftest`, as pre-commit passes only the
  staged files\] → add `tests` to `mypy_path` in `pyproject.toml`; check it by running the hook on one moved file.
- \[`build` now loads the config before the temporary folder exists\] → the folder held nothing before the load, so only
  the order of creating and removing an empty folder changes; `test_build.py`'s `--into` cases cover it.
  `_check_into_sources` stays before the `with`: a `TMPDIR` inside `into` (`test_build.py`'s TMPDIR case) puts the
  temporary folder there, so `into` must be checked before it exists and undone only after it is gone.
- \[`tests` on `mypy_path` makes `cli`, `commands`, `pipeline`, `infra` look like top-level namespace packages to mypy\]
  → no test imports them by those names; task 2.2 runs mypy on one moved file and on all files, so a module found under
  two names fails there.
