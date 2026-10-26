# Tasks

Apply with the `tdd` skill: each task red-green-refactor, one commit.

## 1. Name every source without a ref

- [x] 1.1 Make `compute.check_refs` name every git **Source** without `ref` not in `given` (`source 'b' has no ref`
  for one, `sources 'b', 'c' have no ref` for several) and suggest `skill-graft update` with the aliases in `given`
  plus those, each once, in config order; test: the git-sources spec's "Several new git sources" in
  `tests/cli/test_git_build.py`; `test_git_source_without_ref` still passes unchanged; verify the new test fails
  first, then passes
- [x] 1.2 Through `update`, which passes its selection as `given`; tests in `tests/commands/test_update.py`:
  "Several sources without a ref" (exit 1, `'b'` and `skill-graft update a b` in stderr, no cache; then
  `update a b` exits 0), and `test_other_source_without_a_ref` changed to expect `skill-graft update a b`; verify
  they fail first, then pass

## 2. Update's flags

- [x] 2.1 Give `check_refs` a `flags` suffix, which `update` fills: `--dry-run` when given or `--expect` was,
  `--diff <file>` as given and shell-quoted, `--expect` dropped; tests: "Hint keeps the review", both forms, and
  `skill-graft.toml` unchanged; verify they fail first, then pass

## 3. Archive

- [ ] 3.1 In the archive commit, add a `### Fixed` entry under `[Unreleased]` in `CHANGELOG.md`: with git
  **Sources** without `ref`, every command names all of them, and `update` suggests the command run again with
  them added, keeping a dry run a dry run, instead of hints that send the user back and forth; verify
  `pre-commit run --all-files`
