# Design

## Context

See proposal.md for why. Today, after `commands-own-orchestration`:

- `commands/scope.of` is a context manager: it builds the `Scope`, calls `paths.use(scope.root)`, yields, and
  resets with `paths.use(None)`. `paths.in_use()` returns the global, or `Scope(Path.home())` while unset, so
  tests that never enter `scope.of` (all of `tests/pipeline/`) act on the redirected `HOME`.
- Readers of the global (`grep -rn 'paths\.' src/`), all through `in_use()` or a module function over it:
  - `infra/apm.py`: `_command`, `install`, `registered` (`scope()`, `package()`, `root()`, `manifest()`).
  - `pipeline/config.py`: `load`, `text` (`config_file()`, `scope()`, `package()`, `root()`); `parse`, through
    `_source_folder` (`packages()`) and `_overlap_warnings` (`deploy_folders()`).
  - `pipeline/lock.py`: `_source_path`, under `render` (`scope()`, `root()`, `package()`); `write`, `read`
    (`in_use().lock_file` by default).
  - `pipeline/discovery.py`: `_skill_folders`, under `index` (`package()`).
  - `pipeline/vendor.py`: `vendor` (`skills()` by default).
  - `commands/init_package.py` (`scope()`, `root()`, `package()`, `config_file()`), `commands/edit.py` (`read`,
    `write`, `_finish`: `config_file()`), `commands/update.py` (`config_file()`).
- Ad hoc `Cache(paths.cache())`: `compute.compute_hull` (when given none), `compute.known` (always), and in
  `commands`: `explain.show_tree` (a second one for `--format mermaid`), `update` (one per run, already).
- Pure helpers read no scope: `discover`, `in_package`, `folded`, `overlap`, `cache` (from `XDG_CACHE_HOME` and
  `HOME`, input per ADR 0008). `Scope.user` reads `HOME` too.

## Goals / Non-Goals

**Goals:**

- No module-level scope state; every function that depends on the **Scope** says so in its signature, checked by
  mypy.
- Byte-identical stdout, stderr, files and exit codes: every test under `tests/cli/` and every `main(...)`-driven
  test passes unchanged, but for the one that calls `config.load` itself (see the tests decision).

**Non-Goals:**

- No new import-linter contract: the dependency is now a parameter, which the existing layers contract already
  covers.
- `compute.known` still checks out the **Source** again after the **Hull** was computed (the follow-up named in
  `commands-own-orchestration`); it only stops building its own `Cache`.
- `paths.cache()` stays a module function: the cache belongs to no **Scope** (ADR 0008).

## Decisions

- **The `Scope` comes first in every signature**, as in `commands`: `config.load(scope)`, `config.text(scope)`,
  `config.parse(scope, text)`, `lock.render(scope, config, refs, hull, hashes=None)`,
  `discovery.index(scope, source, confined=False)`, `compute.compute_hull(scope, config, cache, refs=None)`,
  `compute.known(scope, config, cache, where, text)`, `apm.install(scope)`, `apm.registered(scope)`,
  `apm.command_line(scope)`, `init_package.init(scope, project=False)`. One rule, so a reader never looks it up.
  `config.parse` drops its `file` argument: its three callers (`config.load`, `edit.read`, `edit._finish`) pass
  the config file, which is `scope.config_file`.

- **Where a function only needs one path, it takes that path, not the `Scope`.** `lock.write(text, file)` and
  `lock.read(file)` lose their default (`build --into` writes another file; the callers hold the `Scope`);
  `vendor.vendor(hull, skills)` likewise (`build --into` vendors elsewhere). Alternative, taking the `Scope` plus an
  optional override: two ways to name the file for one call site each. `discovery.index` takes the `Scope`, not
  the **Package**, since ADR 0008 has every module reading the **Package**'s location take the `Scope`, and it
  keeps the signatures uniform with `compute`, which passes it on.

- **`Scope` absorbs the module functions it derives**, as properties: `config_file`, `manifest`
  (`root/apm.yml` in project scope, `~/.apm/apm.yml` in user scope), `deploy_folders` and `packages` (both include
  the user scope's, from `Path.home()`). `paths.scope()`, which returned `"user"`/`"project"`, goes; callers test
  `scope.user`. `use`, `_in_use`, `in_use`, `root`, `scope`, `package`, `config_file`, `skills`,
  `deploy_folders`, `packages` and `manifest` are deleted. While a reader remains, the module functions delegate
  to `in_use()` and the new properties, so each task stays green; the last task deletes them.

- **`scope.of(command, project) -> Scope` becomes a plain function.** With no global there is nothing to reset,
  so no `with`. It still reads the working folder only when needed and prints the `package:` notice for
  `WRITERS`. `cli.main` assigns `current = scope.of(...)` inside `warnings_last()`. The tests of the reset go;
  the others drop the `with`.

- **One `Cache` per command, built in `commands`, required below.** `compute_hull` and `known` take it with no
  default. `resolving(scope, loaded, warnings, cache, …)` takes it required too. Each command builds
  `Cache(paths.cache())` once at its start: `resolve`, `build`, the edits (passed to `known` in `rename` and `bind`
  and to `resolving`), `_explain` (passed to `compute_hull`, `known` for `why`, and `repositories` for
  `tree --format mermaid`, which drops its second one); `update` keeps its own, layered over a temporary one in a
  dry run. `Cache.__init__` touches no files, so building one for a config without git **Sources** costs nothing.

- **One `resolve.load`, before it takes the `Scope`.** `_explain` copies it (`config.load()` and its warnings)
  because `resolve` imports `explain`, only for `show`, which prints `explain.tree` and `explain.suggestions`.
  `show` moves into `explain`, its natural home, and `_explain` calls `resolve.load`; `resolve.resolve` still
  calls `explain.show`, so the two import each other, which Python and the layers contract allow, and task
  3.1 changes one copy, not two. Alternative, a new module holding `load`: a module for one function.

- **Tests below `cli` take a `scope` fixture**: `paths.Scope(home)` in `tests/conftest.py`, `home` being the
  autouse fixture's temporary folder that `HOME` points at; user scope, as the global's fallback gave them. Tests
  needing project scope build `paths.Scope(tmp_path / "project")`. Pipeline tests that compute a **Hull** pass
  `Cache(paths.cache())`. Monkeypatched replacements (`lock.write`, `lock.render`, `vendor.vendor`,
  `config.load`, `apm.require`) take the new signatures. `HOME` and `XDG_*` stay redirected by the `home`
  fixture. `test_in_use_follows_home_while_unset` goes with `in_use`. One test under `tests/cli/`,
  `test_remove_the_skill_holding_one`, reads the config with `config.load` after `main`, so it takes the `scope`
  fixture too; its assertion stays.

## Risks / Trade-offs

- [Many signatures change at once] → One task per module, bottom-up, each with the full suite green; module
  functions delegate to `in_use()` until the last task, so no commit has a half-migrated caller.
- [A test's replacement for a function keeps the old signature and silently stops matching] → mypy does not check
  lambdas in `monkeypatch.setattr`; each task greps its function's patches and updates them in the same commit.
- \[`scope.of` printing `package:` without a `with` could print before `warnings_last` is entered\] → `cli` calls it
  inside the `with warnings_last()` block, as today.

## Migration Plan

Internal only. Rollback is reverting the branch.
