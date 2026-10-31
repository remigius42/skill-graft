# Tasks

Apply with the `mp-tdd` skill: each task one red → green slice and one commit, tests only at the seam the task names,
those seams confirmed with the user before the first test. `CONTEXT.md`'s **Hull diff** and **Deployed diff** are in
this branch's proposal commit.

Seams, confirmed by the user: the CLI, `cli.main([...])` with its output and the files it leaves (catches what a user
sees; misses nothing a user can see); `explain.tree(hull, marks)` (catches the marked layout cheaply; misses its use in
the file); `review`'s old side built from a lock and a copies folder (catches the matching and the crafted-lock cases
without a whole command; misses the command's wiring, which the CLI seam covers).

## 1. Shared review code

- [x] 1.1 Move `HEADER`, `_diff_target`, `_fetch_hint`, the **Hull diff** lines and the file assembly out of
  `commands/update.py` into a new `commands/review.py`, which `update.py` imports. The old side becomes one object:
  hashes by **Skill ID**, a view on demand, an upstream folder for the source line; `update` builds it from its old
  **Hull**. The header splits into its shared first line and a per-command second line; `_diff_target` into its refusals
  and its removal of an earlier file; `_fetch_hint` takes the command line to name, `update`'s text unchanged. A move,
  no new test: `tests/commands/test_update.py` passes unchanged before and after, `lint-imports` green
- [x] 1.2 `explain.tree(hull, marks=None)`: each line prefixed with its target's mark or two spaces when `marks` is
  given, unchanged without. Tests at the `explain.tree` seam in `tests/commands/test_explain.py` (a marked entry, a
  marked child, a `(*)` repeat marked as its skill, no marks unchanged); verify each fails first, then passes
- [x] 1.3 The marked tree in every **Deployed diff** file: after the header, the new **Hull**'s tree commented, each
  line escaped as a diff line is, and marked from the **Hull diff**, then one `# - <skill id>` per removal. Tests at the
  CLI seam in `tests/commands/test_update.py` for "Marked hull", and "No previous hull" and "Skill removed" updated;
  verify each fails first, then passes

## 2. Edits and resolve

- [ ] 2.1 The old side from the lock and the copies: the lock's hashes, `upstream` folders and `[sources]` **Refs**, a
  copy's view read only through the entries of the folder `vendor.pending` names, matched by name to the lock's
  **Deployed names**, never a path joined from the lock; only a **Skill** with a copy on the old side, so one without is
  `+`, and `-` only with a copy; every one `+` with no lock; removed IDs quoted. Tests at the `review` seam in
  `tests/commands/test_review.py` ("Renamed skill" `~`, "First add", "A lock pointing outside the copies", "A removed ID
  holding a control character", a killed run's `skills.old` read); verify each fails first, then passes

- [ ] 2.2 `--dry-run` for `add`, `remove`, `rename`, `bind`, `unbind` in `cli.py` and `edit.py`: the `ExitStack` with
  the temporary folder and the layered cache at each command's top, before `compute.known`; `write=False`; the **Hull
  diff** before the tree, from `lock.skill_hashes`, set as `resolution.hashes`; the `review:` hint without `--diff`, its
  arguments `shlex.quote`d; the hint and the `dry run:` line registered on the stack only past the no-op check, so they
  print last on stdout and a no-op prints only its notices; `_fetch_hint` naming the command on a `PatchError`; no prune
  in `cli.py`; a plain edit's output unchanged. Tests at the CLI seam in `tests/commands/test_edit.py` for every
  scenario of "Edit dry run writes nothing" and "Edit reports the hull diff"; verify each fails first, then passes

- [ ] 2.3 `--diff <file>` for the five: `review`'s refusals before anything else; an earlier file removed past the no-op
  check, before resolving; the **Hull diff** printed as with `--dry-run`; the file built inside `resolving`, written
  last in a dry run, else a write before the TOML, undone with it; the header's second line, the marked tree escaped,
  each `+` and `~` **Skill**'s source line with the lock's and the new `ref`, `old -> new` when they differ, old and new
  upstream folder, and its diff. Tests at the CLI seam for every scenario of "Edit deployed diff file"; verify each
  fails first, then passes

- [ ] 2.4 `resolve --dry-run` and `--diff <file>` in `cli.py` and `resolve.resolve`, through the same code, with its own
  header line. Tests at the CLI seam in `tests/commands/test_resolve.py` for every scenario of "Resolve dry run and
  diff"; verify each fails first, then passes

- [ ] 2.5 Docs: `README.md`'s getting-started flow (`add mp/tdd --dry-run --diff review.diff`, read it in an editor,
  then `add mp/tdd`), its "Writing a patch" section (after writing a patch, `resolve --dry-run --diff review.diff` shows
  the patched skill as deployed; read it, then `resolve`); `docs/design.md`'s entries for the six commands;
  `docs/security.md`: the dry run under vetting **Sources**, and git's diff of the committed **Package** for what
  changed since the last `build`; each command's `--help`. Verify `pre-commit run --all-files`

- [ ] 2.6 `README.md`'s Commands section regrouped by role: one sentence that `resolve`, `update` and the editing
  commands resolve and stage (write the lock and `.apm/skills/` together, never deploy), and `build` checks the lock and
  deploys through APM; the table grouped as setup (`init`), staging (`resolve`, `add`, `remove`, `rename`, `bind`,
  `unbind`, `update`), deploying (`build`) and inspecting (`tree`, `why`, `help`); each row saying only what is its own,
  with no "as `rename`, `bind` and `unbind` do too"; `--dry-run` and `--diff <file>` explained once for every staging
  command, `--expect` for `update` alone, replacing the paragraph after the table; the Usage paragraph on hand edits
  pointing to `resolve --dry-run`. Verify `pre-commit run --all-files`

## 3. Changelog

- [ ] 3.1 Add an entry to `CHANGELOG.md` under `[Unreleased]`: `add`, `remove`, `rename`, `bind`, `unbind` and `resolve`
  take `--dry-run` and `--diff <file>`, showing what they would vendor before writing it; each **Deployed diff** opens
  with the marked **Hull**. Per `AGENTS.md` it lands in the archive commit; check the box there; verify
  `pre-commit run --all-files`
