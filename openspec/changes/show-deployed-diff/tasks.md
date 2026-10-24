# Tasks

Apply with the `tdd` skill: each task red-green-refactor, one commit. `CONTEXT.md`'s **Hull diff**, **Deployed
diff** and **Hull digest** are this branch's first commit.

## 1. The deployed view

- [x] 1.1 In a new `pipeline/deployed.py`, `deployed_files(folder, overrides)`: each file's path, bytes (the override's
  where given) and executable bit, walked as `lock.folder_hash` walks (symlinks followed, `.git` skipped); rebuild
  `lock.folder_hash` on it. Test in `tests/pipeline/test_deployed.py` (an override replaces bytes, the bit is read, a
  symlink followed) and that `tests/pipeline/test_lock.py`'s hashes are unchanged; verify the tests fail first, then
  pass, `lint-imports` green

## 2. Summary and diff

- [x] 2.1 `deployed.quote(path, prefix)`: git's `core.quotePath`, the prefix inside the quotes, and a path holding a
  space quoted: letter escapes for `\a \b \t \n \v \f \r \" \\`, octal for other control and non-ASCII bytes, a space
  kept. Test a table of names (line break, tab, `"`, `\`, `é`, a zero-width space, U+2028) against real
  `git diff --no-index` header lines with `GIT_CONFIG_NOSYSTEM=1` and `HOME` in the test's folder, and `run.sh` with a
  trailing space quoted, unlike git; verify the tests fail first, then pass
- [x] 2.2 `deployed.summary(old, new)`, no diff: one line per differing file sorted by path, `(new, <n> bytes)`,
  `(removed)` or `(changed, <old> -> <new> bytes)`, then `(now executable)`, `(no longer executable)`; paths quoted and
  never cut; at most 20 lines then `… <n> more`. Tests for each file-line scenario of "Report the hull diff" ("File
  lines", "Made executable", "Many files", "Lookalike names", "Trailing space"); verify the tests fail first, then pass
- [x] 2.3 `deployed.diff(old, new, budget)`, the file hunks only (`update.py` writes each **Skill**'s own lines): a
  Myers diff over lines mapped to integers, keeping only the 2D + 1 live diagonals per D as `array('i')`, counting
  each diagonal tried, each snake comparison and each stored entry against the run's budget of 10⁷; a file
  past the budget or over 1 MB all removed and all added; hunks with 3 lines of context, `\ No newline at end of file`;
  every file as text, decoded as `hidden`'s decoding reads it, else lenient UTF-8 (make `_decode` public with an
  `errors` argument, the scan keeping `replace`, `tests/pipeline/test_hidden.py` still passing); undecodable bytes,
  control characters but tab, U+2028/U+2029 and `hidden`'s critical and warning characters escaped in a line; header
  paths quoted with their `a/`/`b/` prefix. Tests: hunks equal to `git diff --no-index`'s on ordinary edits, a new and
  a removed file, `old mode`/`new mode`, and every scenario of "Deployed diff content" on the diff body ("A file name
  holding a line break", "A file name holding a space", "A carriage return inside a line", "A line separator inside a
  line", "An invisible character", "A script with a stray byte", "A script with a NUL byte and a stray byte", "A
  crafted file" with its steps and stored entries counted under the budget, and a second crafted file in the same
  run shown linear once the budget is spent); verify the tests fail first, then pass

## 3. update

- [x] 3.1 Keep both **Hulls** open in `_update` (`_previous` a context manager that works out its reason inside its
  `try` and yields outside it); print each `+` and `~` **Skill**'s summary under its line, building views for those
  **Skills** only; reword "not cached";
  in a dry run without `--diff` that marks `+` or `~`, print the hint with the given aliases before `dry run:`. Update
  `tests/commands/test_update.py`'s expected output, and add tests for "File lines", "Skill dropped upstream" (no file
  lines), "Old ref not cached", "Hint", "No hint after a real update", "Nothing
  changed" (no hint), and an `OSError` raised in the `with` body propagating unchanged; verify the tests fail first,
  then pass
- [x] 3.2 `lock.read()`: the lock with `tomllib`, `version` 1, its `skills` array of tables as **Skill ID** to
  `hash`; `update` names each
  **Skill** the old **Hull** and the lock do not
  hold alike, every **Skill** of the old **Hull** when the lock is missing, unreadable or of another `version`. Change
  the lock's header and
  `docs/design.md`'s "never read back". Tests for "Path source edited since the lock", "Skill left since the lock",
  "Nothing edited since the lock" (a renamed **Skill** among them), and a missing lock; verify the tests fail first,
  then pass
- [x] 3.3 `--diff <file>` in `cli.py` and `update.update`: the path's folder resolved, its last part kept; refuse
  first, naming it, a name not ending in `.diff`, a resolved path inside a folder named `.apm` in any case or one
  holding a `SKILL.md`, an existing
  path that `lstat` says is not a regular file, or a regular file whose first bytes, read up to the header's first
  line's length, are not that line; then remove a file it wrote before; build the text before any write; write it with
  `files.atomic_write` last in a dry run, before any closing line, else before the TOML and the lock, removed if
  either fails; per **Skill** the mark line and the source line (**Source**, `ref`s, upstream folders quoted; edited
  since the lock), no command; with no previous **Hull**, the reason and every **Skill** as all added; the
  hull-unchanged file. Tests in
  `tests/commands/test_update.py` for every scenario of "Deployed diff file", and of "Deployed diff content" not
  covered by 2.3 ("Patch applied on both sides", "Renamed skill", "Source line", "A folder name holding a line
  separator", "A path source", "Edited since the lock", "Git configuration ignored" with a `HOME` whose git config sets
  `*.md binary` and an `orderFile`), and "Dry run with a diff file"; verify the tests fail first, then pass, and
  `pre-commit run --all-files`
- [x] 3.4 `lock.digest(hull, hashes)`: SHA-256 of the ASCII JSON of the sorted `[skill id, deployed name, hash]`
  triples. Tests in `tests/pipeline/test_lock.py`: equal for equal **Hulls** built in another order, different for a
  changed hash and for a changed **Deployed name** alone; verify the tests fail first, then pass
- [x] 3.5 `--expect <digest>` in `cli.py` and `update.update`: 64 lowercase hex checked before any fetch; once the
  **Hull diff** is printed and before any write, a mismatch exits non-zero naming both digests and the review command,
  writing neither the TOML, the lock nor `--diff`'s file; a dry run prints
  `apply: skill-graft update <aliases> --expect <digest>` after its diff file is written and before `dry run:`,
  exactly when it printed no hint and named no **Skill** as edited since the lock, the lock check skipped with no
  previous **Hull**; the hint also without a previous **Hull**. Tests
  for every scenario of "Update to the hull vetted", with a test git remote whose tip moves between the dry run and
  the update, and a path **Source**, a **Patch** and a **Rename** edited between them; verify the tests fail first,
  then pass, and `pre-commit run --all-files`

## 4. Docs

- [ ] 4.1 `README.md`'s `update` line and Config-free usage: `--diff <file>`, the review loop
  `update --dry-run --diff review.diff` then the `apply:` line's `update … --expect …`, never printing the file to a
  terminal; `docs/design.md`'s `update` entry and its two resolutions; `docs/security.md`: drop the Future work item,
  add "Verify the lock's hash at `build`" there and mention the **Deployed diff** under vetting **Sources** in Residual
  risks' "Deployed Skills"; the `update --help` text. Verify `pre-commit run --all-files`

## 5. Changelog

- [ ] 5.1 Add an entry to `CHANGELOG.md` under `[Unreleased]`: `update` names each changed file of each changed or
  added **Skill**; `--diff <file>` writes its **Deployed diff**;
  `update --expect <digest>` applies only the **Hull** vetted; a **Skill** edited since the lock was written is named;
  an old **Ref** gone from the cache's branches is named so. Per `AGENTS.md` it lands in the archive commit; check the
  box there; verify `pre-commit run --all-files`
