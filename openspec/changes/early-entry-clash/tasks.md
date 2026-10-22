# Tasks

## 1. Report an Entry clash before reading Sources

- [ ] 1.1 Red: in `tests/cli/test_git_build.py` add the "Entries clash before any fetch" scenario: an `Upstream`
  with `tdd/SKILL.md`, `own/tdd` in a path **Source**, `[sources.mp]` at that commit's `ref`, uncached; assert
  `build` exits 1, `err` names `mp/tdd` and `own/tdd`, and `home / ".cache"` does not exist; verify it fails today
  (the fetch creates the cache). Green: in `compute_hull` move the entries-only `rename.check_unique` call before
  the `TemporaryDirectory` and `_folders`, and say so in its docstring ("before any source is read"); verify the
  new test and the existing clash tests pass and `pre-commit run --all-files` is green
