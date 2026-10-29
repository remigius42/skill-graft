# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor, one commit. Red is a test calling the new signature (or the
new `Scope` property) failing. Every test under `tests/cli/` passes unchanged at every commit; tests below `cli` change
only to pass a `Scope` or `Cache`. `pre-commit run --all-files` stays green. No CHANGELOG entry.

## 1. Groundwork

- [x] 1.1 Add `config_file`, `manifest`, `deploy_folders` and `packages` to `paths.Scope`; the module functions of those
  names delegate to `in_use()`'s; tests in `tests/infra/test_paths.py` for each in user and project scope (project's
  `deploy_folders` and `packages` include the user scope's); verify they fail first, then pass
- [x] 1.2 Add the `scope` fixture (`paths.Scope(home)`) to `tests/conftest.py`; verify `pytest` stays green
- [x] 1.3 One way to load the config: move `show(hull)` from `commands/resolve.py` into `commands/explain.py`
  (`resolve.resolve` and `edit._finish` call `explain.show`; `resolve` and `explain` then import each other);
  `explain._explain` calls `resolve.load(warnings)` instead of its own `config.load()` and `warnings.extend`; verify
  `lint-imports` and `pytest` green and `grep -n 'config.load' src/skill_graft/commands/` finds only `resolve.py`

## 2. infra takes the Scope

- [x] 2.1 `apm.install(scope)`, `apm.registered(scope)`, `apm.command_line(scope)` (and `_command`) read the `Scope`;
  callers in `init_package` and `build` pass theirs; a test below `cli` calling `install` or `registered` with a project
  `Scope` against `fake_apm` fails first (signature), then passes

## 3. pipeline takes the Scope

- [x] 3.1 `config.load(scope)`, `config.text(scope)`, `config.parse(scope, text)` (no `file`), the source checks reading
  `scope.packages` and `scope.deploy_folders`; `edit.read` and `edit._finish` pass theirs;
  `tests/pipeline/test_config.py` passes the `scope` fixture, plus a test that a project `Scope` refuses a source
  overlapping the user scope's package; patches of `config.load` take the new signature; verify red, then green
- [x] 3.2 `discovery.index(scope, source, confined=False)` skips `scope.package`; `compute` passes its `Scope`
  (`compute_hull(scope, config, …)`, `known(scope, config, …)`), `commands` theirs; `tests/pipeline/test_discovery.py`
  and `test_hull.py` pass a `Scope`, plus a test that a project `Scope`'s package is skipped while the home folder's
  global fallback would not; verify red, then green
- [x] 3.3 `lock.render(scope, …)` passes it to `_source_path`; `lock.write(text, file)` and `lock.read(file)` lose their
  default; `resolving` and `update` pass `scope.lock_file`; `tests/pipeline/test_lock.py` passes a `Scope`, plus a
  project-scope `render` giving a source path relative to the package; patches of `lock.write` and `lock.render` take
  the new signatures; verify red, then green
- [x] 3.4 `vendor.vendor(hull, skills)` loses its default; `build` passes `scope.skills` or `--into`'s folder; patches
  of `vendor.vendor` updated; verify `pytest` green and mypy refuses a call without `skills`

## 4. One Cache per command

- [x] 4.1 `compute_hull(scope, config, cache, refs=None)` and `known(scope, config, cache, where, text)` take a required
  `Cache`; `resolving` takes it required; `resolve`, `build`, the edits and `_explain` each build `Cache(paths.cache())`
  once and pass it to every `compute_hull`, `known` and `repositories` call; `show_tree` drops its second `Cache`;
  pipeline tests pass `Cache(paths.cache())`; verify `grep -rn 'Cache(' src/skill_graft/pipeline src/skill_graft/infra`
  finds only `cache.py`'s own reference layering, and `pytest` green
- [x] 4.2 `update.update` writes its `_update` call once: the arguments both branches share bound once (a
  `functools.partial`, or one call with `git_cache` and `write` chosen per branch), the dry run keeping its temporary
  cache, its `PatchError` hint and its closing line; no behavior change; verify `tests/commands/test_update.py` green
  unchanged and `grep -c '_update(' src/skill_graft/commands/update.py` counts the definition and one call

## 5. commands read the Scope they hold

- [x] 5.1 `init_package.init(scope, project=False)` reads `scope.user`, `scope.root`, `scope.package`,
  `scope.config_file` (`_exists`, `_listed` take it too); `cli` passes `current`; `edit.read(scope)`,
  `edit.write(scope, document)` and the config file in `_finish` read `scope.config_file`; `update` likewise;
  `tests/commands/test_init_package.py` drives `init` with a `Scope` below `cli`; verify red, then green, and no module
  but `paths.py` reads the global (`grep -rn 'paths\.[a-z_]*()' src/` finds only `paths.cache()`)

## 6. Delete the global

- [x] 6.1 `scope.of(command, project) -> Scope` becomes a plain function, without `paths.use`; `cli.main` assigns
  `current = scope.of(...)` inside `warnings_last()`; delete `test_reset_after_the_block` and
  `test_reset_when_the_block_raises`, the others dropping the `with`; verify `pytest` green
- [x] 6.2 Delete `paths.use`, `_in_use`, `in_use`, `root`, `scope`, `package`, `config_file`, `skills`,
  `deploy_folders`, `packages`, `manifest` and `test_in_use_follows_home_while_unset`; the module docstring says the
  `Scope` derives every path; verify `grep -rn 'in_use\|paths\.use' src tests` is empty, `mypy --strict` and
  `pre-commit run --all-files` green
- [x] 6.3 `docs/design.md`'s "Stack" entry says `pipeline` and `infra` take the `Scope` and `commands` build the
  `Cache`, if it names where the scope comes from; verify by reading it
