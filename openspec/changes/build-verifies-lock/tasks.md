# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor, one commit. `pre-commit run --all-files` stays green, and
every commit passes `pytest`.

## 1. Lock checks

- [x] 1.1 `pipeline/lock.py`: `copy_problems(skills, locked)` returns one line per folder of `skills` whose
  `folder_hash` differs from the lock's for the **Skill** deployed under that name, per folder no lock **Skill** is
  deployed under, and per file at its top level; empty when they match, for a missing copy, and for a missing `skills`.
  Tests in `tests/pipeline/test_lock.py`: `test_copies_match`, `test_copy_edited`, `test_copy_unknown`,
  `test_top_level_file_unknown`, `test_copy_missing`, `test_renamed_copy_checked_by_deployed_name`,
  `test_stray_file_is_a_difference`; and `test_copy_hash_is_skill_hash`, pinning
  `folder_hash(copy) == skill_hashes(hull)[skill]` for a renamed, patched skill with a symlink and an executable file.
  Verify red, then green
- [x] 1.2 `pipeline/lock.py`: `drift(new, old, path_aliases)` returns the path **Source** **Skills** whose `hash`
  differs, and a refusal (`None` when nothing else differs), comparing the parsed locks with each path **Source**'s
  `path`, and the `hash` of its **Skills** with no `patches` in either lock, dropped: it names each other **Skill**
  whose hash differs, each joining or leaving, each other field of a **Skill**, **Source**, edge and suggestion that
  differs (edges and suggestions as `<from> → <to> (<kind>)`), else that the lock differs in what it records; an `old`
  of `None` or of another `version` is refused. Tests in `tests/pipeline/test_lock.py`: `test_no_drift`,
  `test_path_hash_only`, `test_path_folder_is_no_drift`, `test_patched_path_skill_refused`, `test_git_hash_refused`,
  `test_skill_joins_refused`, `test_skill_leaves_refused`, `test_edge_change_refused`,
  `test_path_skill_new_edge_refused`, `test_path_skill_new_suggestion_refused`, `test_deployed_name_change_refused`,
  `test_ref_change_refused`, `test_unnamed_difference_refused`, `test_no_old_lock_refused`,
  `test_other_version_refused`, `test_comment_is_no_drift`. Verify red, then green

## 2. Vendoring with the lock

- [ ] 2.1 `pipeline/vendor.py`: `vendor` splits into `pending(skills, keep_old)`, `recover(skills, keep_old)`,
  `stage(hull, skills)` (writes `skills.new`), `swap(skills)`, `swap_back(skills)` and `clear_old(skills)`. `pending`
  names, touching nothing, the folder recovery leaves as `skills`: a lone `skills.old`; with both, `skills.old` if
  `keep_old(skills.old)`, else `skills`. `recover` makes it so and deletes `skills.new`. `build` calls them in order
  with `keep_old` always false, behavior unchanged. Tests in a new `tests/pipeline/test_vendor.py`:
  `test_swap_back_restores_previous`, `test_clear_old_removes_previous`, `test_pending_touches_nothing`,
  `test_recover_lone_old`, `test_recover_keeps_old_that_matches`, `test_recover_drops_old_that_does_not`,
  `test_recover_drops_new`, `test_swap_back_without_previous` (no `skills` before the swap: undoing it deletes the new
  `skills`); `tests/commands/test_build.py`'s vendoring tests stay green. Verify red, then green
- [ ] 2.2 `commands/transaction.py`: `check_copies(skills, locked)` checks the folder `vendor.pending` names, with
  `keep_old` true when that folder holds exactly the lock's copies, none missing, and raises a `SkillGraftError` with
  `copy_problems`' lines, a **Patch** and deleting the folder; with no lock, an unreadable one or one of another
  `version` beside a non-empty `skills`, it raises the "cannot be checked" error instead.
  `resolving(..., skills=None, checked=False)` runs it first unless `checked`, writing or not; in the block, after the
  caller's body, renders `lock_text`, runs `verify(lock_text)` if set, then, given `write`, `vendor.recover` and
  `stage`; after the block, the caller's `writes`, `.apm/skill-graft/.gitattributes` if missing (one of the writes,
  restored on failure), `swap` and the lock, undoing the swap (a failing undo a notice, the TOML still restored and the
  original error reported) and removing `skills.new` before restoring the TOML on any failure; then `clear_old`
  best-effort, outside the undo. `build` stops vendoring and hashing itself; `resolve`, `update` and the editing
  commands now vendor. Tests in `tests/commands/test_transaction.py`: `test_writes_copies_with_the_lock`,
  `test_lock_write_fails_restores_copies`, `test_interrupt_restores_copies`,
  `test_swap_back_failure_still_restores_the_toml`, `test_clear_old_failure_keeps_lock_and_copies`,
  `test_edited_copy_refused_before_any_write`, `test_unreadable_lock_cannot_check`, `test_dry_run_checks_copies`,
  `test_dry_run_leaves_a_killed_run`, `test_verify_refusal_touches_nothing`, `test_killed_before_lock_recovered`,
  `test_killed_after_lock_recovered`, `test_killed_after_lock_adding_only_recovered`,
  `test_gitattributes_written_if_missing`, `test_own_gitattributes_kept`, `test_into_writes_no_gitattributes`,
  `test_first_resolve_lock_write_fails_leaves_no_copies`, `test_checked_skips_the_check`; tests that list a
  **Package**'s files now expect `.gitattributes` once it was resolved; in `test_resolve.py`, `test_edit.py` and
  `test_update.py`, the scenarios "Resolve succeeds", "Lock write fails", "Edit succeeds", "Lock write interrupted" and
  "No deploy" now expect `.apm/skills/` written, restored or untouched as the specs say. Verify red, then green
- [ ] 2.3 `commands/update.py`: calls `transaction.check_copies` before listing remotes, and passes `checked=True` to
  `resolving`. Test in `tests/commands/test_update.py`, `test_edited_copy_refused_before_any_remote` (also with
  `--dry-run`): exits 1 naming `.apm/skills/tdd`, with no sha line printed and the cache folder unchanged. Verify red,
  then green

## 3. Build deploys the lock

- [ ] 3.1 `commands/build.py`: sets `verify` to `drift` against the **Package**'s lock (for `--into` too), refusing with
  the refusal and `skill-graft resolve`; once `resolving` has written the lock, prints the path **Source** notice for
  each **Skill** `drift` returned. `pipeline/lock.py`'s header becomes
  `# Written by skill-graft, which reads it back. Do not edit.` `tests/conftest.py`'s `build` helper runs `resolve`
  first, and so does each test that builds from a hand-written config and expects success.
  `tests/commands/test_resolve.py`'s `test_lock_edited_by_hand`, the removed "The lock is output only", becomes
  `test_lock_edited_by_hand_refused`: `build` exits 1 naming `skill-graft resolve`. Tests in
  `tests/commands/test_build.py` for every scenario of "Build deploys the lock", "Changed path Source deployed",
  "Vendored copies match the lock" and "Vendored copies keep their bytes in git" (the last through a real clone with
  `core.autocrlf=true`), and `--into`'s "Config edited by hand" and "Package never built". Verify each new test red
  first, then the whole suite green
- [ ] 3.2 `cli.py`: `build`'s help says it deploys what `skill-graft.lock` records, and `resolve`'s that it vendors;
  `tests/cli/test_cli.py`'s `test_command_help` checks both. Verify red, then green
- [ ] 3.3 `commands/init_package.py`: when APM fails after registering, the message says
  `fix that, then run: skill-graft resolve, then skill-graft build`. Test in `tests/commands/test_init_package.py`, the
  "APM fails after registering" scenario's test asserting it. Verify red, then green

## 4. graft-check

- [ ] 4.1 `skills/graft-check/SKILL.md`: step 6 runs `skill-graft resolve` after appending a **Patch** to `[patches]`,
  before the throwaway build; a failed `resolve` or build undoes the fix, then runs `skill-graft resolve` again if the
  first `resolve` succeeded. Step 7 drops "the commands that edit config write the lock and leave the vendored copies
  behind", and with nothing to build says the copies are as the config builds them, and to run `skill-graft build` if it
  has not run since the last change. `evals/graft-check/run.sh` runs `skill-graft resolve` before its
  `skill-graft build --no-install`, and its scenarios without a build `skill-graft resolve` alone. Tests in
  `tests/cli/test_check.py`: `test_patch_fix_resolves_before_building` and `test_undone_patch_resolves_again`, on the
  skill's text. Verify red, then green; the eval is not run unless asked

## 5. Docs

- [ ] 5.1 `docs/design.md`: the files table (`.apm/skills/<name>/` written by `resolve`, `build`, `update` and the
  editing commands, and `.gitattributes`), "The lock is output only" replaced, and the `build`, `resolve`, `update`,
  `init` and editing-command entries; `docs/security.md`: the LLM03 row says `build` checks the lock's hashes, and the
  Future work bullet goes; `README.md`: the workflow runs `resolve` after a hand edit, the commands table says which
  commands vendor, and committing `.apm/skill-graft/` includes `.gitattributes`. Verify by reading, and
  `pre-commit run --all-files` green

## 6. Archive prep

- [ ] 6.1 At archive, `CHANGELOG.md` `[Unreleased]`: under Changed, that `build` deploys only what `skill-graft.lock`
  records and refuses otherwise, naming `resolve`; that `resolve`, `update` and the editing commands write the
  **Vendored copies** and `.gitattributes`; that no command overwrites an edited **Vendored copy**, a stray file
  included; that `graft-check` runs `resolve` after a **Patch** fix; and how to recover a **Package** whose lock is
  newer than its copies, a clone whose copies were already converted, and after an upgrade that rewrites differently. In
  the main `check` spec, rename the scenario "Lock current, vendored copies behind" to "Added but not built". Verify by
  reading
