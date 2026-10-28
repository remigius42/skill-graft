# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor, one commit. Every existing test passes unchanged at
every commit, but those task 3.1 moves to the new warning position; `pre-commit run --all-files` stays green.

## 1. The Scope type

- [x] 1.1 Add `paths.Scope` (frozen dataclass, `root`; `package`, `user` as a `cached_property`, `lock_file`,
  `skills`) and replace `_root` and `_scope` with one module-level `Scope | None` that `use` sets and `in_use()`
  returns (a new `Scope(Path.home())` per call while `None`), `paths.package()`, `scope()`, `skills()` and
  `lock.write`'s and `lock.read`'s default file reading it; tests in a new `tests/infra/test_paths.py`:
  `in_use()` follows a changed `HOME` while unset, home root is user scope, any other root project scope,
  compared resolved (a symlink to the home folder is user scope), and each path under `root/.apm/skill-graft`;
  verify they fail first, then pass

## 2. One place builds the Scope

- [x] 2.1 Add `commands/scope.py`: `of(command, project)` context manager as design.md says, `WRITERS` and
  `_working_folder` moved from `cli`; `cli.main` enters it around dispatch instead of its `paths.use` calls and
  `package:` notice; tests in `tests/commands/test_scope.py`: `init` yields the home folder without reading the
  working folder (passes in a deleted one), `init --project` the working folder, `tree` the discovered package
  and prints no `package:`, `build` prints it, and the global is reset after the block, also when it raises;
  the existing `tests/cli/test_scope.py` passes unchanged

## 3. Warnings come last

- [x] 3.1 Add `errors.warnings_last()` as design.md says, printing each distinct warning once; `cli.main` enters
  it inside its `try`, around `scope.of`, and passes the list as the `warnings` parameter of `resolve`, `build`,
  `tree`, `why`, `update` and the edits, which append config and **Hull** warnings as soon as they have them
  instead of calling `warn` (`cli`'s inline `resolve`, `build`, `tree` and `why` too, until they move: inline
  `resolve` appends the **Hull**'s before writing the lock); an edit appends the edited config's warnings when it
  resolves, `edit.read`'s when it fails before that, none when it is a no-op; tests through `main`, one per
  scenario of the cli spec's "Warnings come last", plus a no-op `add` printing only its notice with a config
  warning present, each asserting the warning's position in stderr and, with `capfd` or a combined stream,
  against stdout and APM's output; verify they fail first, then pass. Update each existing test pinning the old
  position, naming it in the commit

## 4. The shared resolve-and-lock

- [ ] 4.1 Add `commands/resolve.py` with `resolving(...)`, `Resolution`, `show(hull)` and `load()` as design.md
  says, and move `resolve` there as `resolve(scope, warnings)`, `cli` dispatching to it; tests in
  `tests/commands/test_resolve.py` against `resolving` directly: nothing rendered or written when the block
  raises; `render` failing runs no write; a failing lock write restores the written files in reverse, a missing
  one by removing it; a `KeyboardInterrupt` raised by a write after it replaced its file restores it and the
  earlier ones; the restore puts back the bytes found right before the write, not those when the block began; a
  restore raising `OSError` prints a notice, the next still runs, and the original error is re-raised; the lock
  goes through `lock.write`; `skill_hashes` is not called when `hashes` is set; `write=False` renders and writes
  nothing; `hashes` set in the block is what the lock records; the **Hull**'s warnings are in the list though the
  lock write fails; verify they fail first, then pass. `tests/cli/test_resolve.py` passes unchanged
- [ ] 4.2 `edit._finish` uses `resolving`, appending `(the config file resolved, edit.write(document))`; the edit
  commands take the `Scope` and the list; test in `tests/commands/test_edit.py`: a `KeyboardInterrupt` from
  `lock.write` leaves `skill-graft.toml` byte for byte as before (the edit spec's "Lock write interrupted"; red
  today: only `OSError` restores); verify it fails first, then passes
- [ ] 4.3 `update._update` uses `resolving` (`refs=tips`, its `cache`, `hashes` set, `write=not dry_run`),
  appending `(the diff file, its atomic_write)` and `(the config file resolved, _write_refs(moved))`;
  `update.update` takes the `Scope` and the list and loads the config; tests in `tests/commands/test_update.py`:
  the spec's "Lock write fails" and "Lock write interrupted" scenarios, `lock.write` patched to raise `OSError`
  or `KeyboardInterrupt` after `_write_refs` ran (red today); verify they fail first, then pass. The existing
  tests patching `edit.write` and `files.atomic_write`, and the dry-run `--diff` tests, pass unchanged

## 5. Build

- [ ] 5.1 Move `build` to `commands/build.py` as `build(scope, warnings, into, no_install)` with `_check_into`,
  `_check_into_sources` and `_undo_into`, printing `into:` and checking first; vendoring and the vendored hashes
  inside a `resolving` block with `lock_file` for `--into`; `cli` keeps `_into` and dispatches; verify
  `tests/cli/test_build.py` (its `lock.write` patches included), `test_git_build.py` and
  `test_resolve.py::test_lock_hashes_what_was_vendored` pass unchanged (the move adds no behavior, so no new red
  test)

## 6. Tree and why

- [ ] 6.1 Move `tree` and `why` into `commands/explain.py` as `show_tree(scope, warnings, mermaid, link)` and
  `show_why(scope, warnings, text)`, `_explain` moved as is, appending to the list instead of `warn`; `cli` keeps
  the `--link` usage error and dispatches; verify `tests/commands/test_explain.py` and
  `tests/cli/test_hidden_characters.py` pass unchanged

## 7. cli only parses and dispatches

- [ ] 7.1 Add the forbidden contract from design.md to `pyproject.toml`; remove what `cli` no longer uses; check
  it bites: a temporary `from skill_graft.pipeline import config` in `cli.py` makes `lint-imports` fail, and so
  does `from skill_graft.infra import paths`, then revert; verify `lint-imports` passes. Update
  `docs/design.md`'s "Stack" entry: `cli.py` parses and dispatches, `commands/` lists `scope`, `resolve`,
  `build`, `edit`, `update`, `explain`, `init_package` and builds the `Scope`
