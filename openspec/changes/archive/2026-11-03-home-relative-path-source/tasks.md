# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor, one commit. `pre-commit run --all-files` stays green, and
every commit passes `pytest`.

## 1. Lock records a home path as written

- [x] 1.1 `pipeline/config.py`: `PathSource` keeps the `path` as written beside `folder`; one helper expands `~` for
  `path` and `[patches]` files, turning `expanduser`'s `RuntimeError` into a `SkillGraftError` naming the path (and the
  alias for a source). Tests in `tests/pipeline/test_config.py`: `test_path_kept_as_written`,
  `test_unknown_user_home_is_an_error`, `test_unknown_user_home_in_a_patch_is_an_error`. Verify red, then green
- [x] 1.2 `pipeline/lock.py`: `portable_path(scope, source)` returns, in project scope, the path relative to the
  **Package** when the folder is inside the project root, else for a `path` of `~/<rest>` with no `..` segment that path
  with empty and `.` segments of `<rest>` dropped, else `None`; `None` in user scope. `render` writes its result or the
  absolute folder. Tests in `tests/pipeline/test_lock.py`: `test_portable_inside_the_project`,
  `test_portable_home_path`, `test_portable_home_path_normalized` (`~/skills/`, `~//skills`, `~///skills`,
  `~/./skills`), `test_dot_dot_segment_not_portable` (`~/x/../skills`, `~/../shared`),
  `test_dot_dot_prefixed_name_portable` (`~/..skills`), `test_named_user_home_not_portable`,
  `test_absolute_and_relative_outside_not_portable`, `test_home_folder_written_out_not_portable`,
  `test_user_scope_not_portable`. In `tests/commands/test_scope.py`: `test_project_source_outside_the_project` now
  expects `~/skills`; new `test_project_source_under_a_symlinked_home_folder`,
  `test_project_source_inside_the_project_written_with_home`. Verify red, then green
- [x] 1.3 `tests/commands/test_scope.py`: `test_same_lock_on_another_machine` adds a path **Source** `path = "~/skills"`
  under each `HOME`; `tests/commands/test_deploy.py`: `test_path_source_elsewhere_on_another_machine` uses an absolute
  `path` outside the project and home; new `test_home_path_source_on_another_machine` (lock written under one `HOME`,
  `deploy` under another leaves it byte-equal) and `test_lock_from_before_home_paths` (a lock recording the absolute
  folder is rewritten to `~/skills`). Verify they pass with 1.2's code; red first only if one fails
- [x] 1.4 `pipeline/lock.py`: `without_paths(data, path_aliases)`, taken out of `drift`'s `shape`, which calls it;
  `commands/update.py`: the nothing-to-apply comparison applies it to both locks; it leaves a lock whose `sources` are
  not a table of tables as it is, so that compares as today. `config.path_aliases` serves `update` and `deploy`. Tests
  in `tests/commands/test_update.py`: `test_nothing_to_apply_with_another_path_recorded` (the lock records `own` at
  another absolute folder; `update --dry-run` prints `nothing to apply`), `test_malformed_lock_without_sources_applies`
  (no crash, an `apply:` line). `drift`'s tests stay green. Verify red, then green
- [x] 1.5 `README.md`: the paragraph on committing a project **Package** names `~/` paths as recorded as written, so a
  path outside both the project and `~/` is recorded absolute and warned of; `docs/design.md` likewise wherever it
  describes the lock's `path`. Verify: `pre-commit run` on the changed files

## 2. Warn of a machine-specific project path source

- [x] 2.1 `commands/transaction.py`: `resolving`, when no `lock_file` is given (the package's own lock), adds a warning
  per path **Source** whose `lock.portable_path` is `None` in project scope:
  `source '<alias>': skill-graft.lock records <folder> absolute, so other machines need it at the same place;`
  (`would record` in a dry run) `a path inside the project, or ~/ without .., reads the same on every machine`. Tests in
  `tests/commands/test_transaction.py`: `test_absolute_project_path_warns`,
  `test_dry_run_warns_of_what_it_would_record`, `test_portable_project_path_does_not_warn`,
  `test_user_scope_does_not_warn`, `test_own_lock_file_does_not_warn`. Verify red, then green
- [x] 2.2 Tests in `tests/cli/test_warnings.py`, with `path = "/opt/skills"`-like folder outside project and home:
  `resolve`, `resolve --dry-run`, `deploy`, `add` and `update --dry-run` print the warning on standard error and exit 0;
  `deploy --into` and `tree` print none. Verify they pass with 2.1's code; red first only if one fails
